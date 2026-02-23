#!/usr/bin/env python3
"""
Optimized IPTV DB builder

Key optimizations vs original:
- Incremental DB updates (no delete/recreate daily)
- SQLite PRAGMA tuning + single commit per server + WAL
- Avoid duplicate HTTP calls (your original code called requests.get(...).json() twice per endpoint)
- Truncate large text fields (plot) to keep DB size small
- Optional: skip live channels to massively reduce DB size (default ON)
- Optional: keep only TMDB-matched titles (default OFF)
- Smaller, configurable TMDB prefetch pages
- Batched inserts and fewer indexes (indexes are big)

Config via env vars:
  SKIP_LIVE=1                  (default: 1)
  TMDB_PAGES=5                 (default: 5)
  PLOT_MAXLEN=200              (default: 200)
  ONLY_TMDB_MATCHED=0          (default: 0)
  MAX_WORKERS=20               (default: 20)
"""

import os
import sqlite3
import requests
import re
from urllib.parse import urlparse, parse_qs
import concurrent.futures

# ---------------- CONFIG ----------------
XC_FILE_URL = "https://raw.githubusercontent.com/staycanuca/hub/refs/heads/main/_tools/xc.txt"
TMDB_API_KEY = "304ca56b1b7b57ca7a47d9b59946be94"

DB_FILE = "iptv_aggregator.db"
TIMEOUT = 10

MAX_WORKERS = int(os.getenv("MAX_WORKERS", "20"))
SKIP_LIVE = os.getenv("SKIP_LIVE", "1") == "1"
TMDB_PAGES = int(os.getenv("TMDB_PAGES", "5"))
PLOT_MAXLEN = int(os.getenv("PLOT_MAXLEN", "200"))
ONLY_TMDB_MATCHED = os.getenv("ONLY_TMDB_MATCHED", "0") == "1"

HEADERS = {"User-Agent": "VLC/3.0.20 (Windows; x86_64)"}

TMDB_CACHE = {"movies": {}, "series": {}}


# ---------------- DB ----------------
def connect_db():
    conn = sqlite3.connect(DB_FILE)
    cur = conn.cursor()

    # Pragmas: smaller/faster and more stable for repeated writes
    cur.execute("PRAGMA journal_mode=WAL;")
    cur.execute("PRAGMA synchronous=NORMAL;")
    cur.execute("PRAGMA temp_store=MEMORY;")
    cur.execute("PRAGMA cache_size=-200000;")  # ~200MB cache (adjust if needed)
    cur.execute("PRAGMA foreign_keys=ON;")

    # Tables (IF NOT EXISTS) for incremental updates
    cur.execute("""
        CREATE TABLE IF NOT EXISTS servers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            server_url TEXT NOT NULL,
            username TEXT NOT NULL,
            password TEXT NOT NULL,
            server_name TEXT,
            is_active INTEGER DEFAULT 1,
            last_checked TEXT,
            status TEXT,
            expiration_date TEXT,
            active_cons INTEGER,
            max_connections INTEGER,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(server_url, username)
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS movies (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            stream_id INTEGER NOT NULL,
            server_id INTEGER NOT NULL,
            name TEXT NOT NULL,
            name_normalized TEXT,
            stream_icon TEXT,
            plot TEXT,
            releaseDate TEXT,
            rating TEXT,
            tmdb_id INTEGER,
            imdb_id TEXT,
            tmdb_popularity REAL DEFAULT 0,
            tmdb_vote_average REAL DEFAULT 0,
            tmdb_vote_count INTEGER DEFAULT 0,
            container_extension TEXT,
            added_at TEXT DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(stream_id, server_id)
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS series (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            series_id INTEGER NOT NULL,
            server_id INTEGER NOT NULL,
            name TEXT NOT NULL,
            name_normalized TEXT,
            cover TEXT,
            plot TEXT,
            releaseDate TEXT,
            rating TEXT,
            tmdb_id INTEGER,
            imdb_id TEXT,
            tmdb_popularity REAL DEFAULT 0,
            tmdb_vote_average REAL DEFAULT 0,
            tmdb_vote_count INTEGER DEFAULT 0,
            added_at TEXT DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(series_id, server_id)
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS live_channels (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            stream_id INTEGER NOT NULL,
            server_id INTEGER NOT NULL,
            name TEXT NOT NULL,
            stream_icon TEXT,
            epg_channel_id TEXT,
            category_id TEXT,
            added_at TEXT DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(stream_id, server_id)
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS categories (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            category_id INTEGER NOT NULL,
            server_id INTEGER NOT NULL,
            category_name TEXT NOT NULL,
            parent_id INTEGER,
            content_type TEXT NOT NULL,
            added_at TEXT DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(category_id, server_id, content_type)
        )
    """)

    # Indexes: keep minimal. Indexes can bloat DB a lot.
    # If you need more search performance, add them back carefully.
    cur.execute("CREATE INDEX IF NOT EXISTS idx_movies_name_norm ON movies(name_normalized);")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_series_name_norm ON series(name_normalized);")

    conn.commit()
    return conn


# ---------------- UTILS ----------------
def normalize_name(name: str) -> str:
    if not name:
        return ""
    normalized = name.lower()
    normalized = re.sub(r"[^\w\s]", " ", normalized)
    normalized = re.sub(r"\s+", " ", normalized).strip()
    return normalized


def safe_trunc(s: str | None, maxlen: int) -> str | None:
    if not s:
        return None
    if len(s) <= maxlen:
        return s
    return s[:maxlen]


def fetch_json(url: str, timeout: int = TIMEOUT):
    r = requests.get(url, headers=HEADERS, timeout=timeout)
    r.raise_for_status()
    return r.json()


def fetch_list(url: str) -> list:
    # ensure we only do ONE network call
    try:
        data = fetch_json(url)
        return data if isinstance(data, list) else []
    except Exception:
        return []


# ---------------- INPUT SERVERS ----------------
def parse_servers_from_url():
    print(f"Fetching servers from {XC_FILE_URL}...")
    resp = requests.get(XC_FILE_URL, timeout=TIMEOUT)
    resp.raise_for_status()

    servers = []
    for line in resp.text.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue

        if "username=" in line and "password=" in line:
            try:
                parsed = urlparse(line)
                q = parse_qs(parsed.query)
                user = q.get("username", [""])[0]
                pw = q.get("password", [""])[0]
                if user and pw:
                    server_url = f"{parsed.scheme}://{parsed.netloc}"
                    servers.append({"url": server_url, "user": user, "pass": pw})
            except Exception:
                pass

    unique = {f"{s['url']}_{s['user']}": s for s in servers}.values()
    unique_list = list(unique)
    print(f"Found {len(servers)} potential servers. Unique: {len(unique_list)}")
    return unique_list


# ---------------- TMDB CACHE ----------------
def pre_fetch_tmdb_popular(pages: int = TMDB_PAGES):
    if not TMDB_API_KEY:
        print("TMDB key missing; skipping TMDB cache.")
        return

    print(f"Pre-fetching TMDB popular lists (pages={pages})...")
    for page in range(1, pages + 1):
        try:
            m = fetch_json(f"https://api.themoviedb.org/3/movie/popular?api_key={TMDB_API_KEY}&page={page}")
            for item in m.get("results", []):
                norm = normalize_name(item.get("title", ""))
                if norm:
                    TMDB_CACHE["movies"][norm] = item
        except Exception:
            pass

        try:
            s = fetch_json(f"https://api.themoviedb.org/3/tv/popular?api_key={TMDB_API_KEY}&page={page}")
            for item in s.get("results", []):
                norm = normalize_name(item.get("name", ""))
                if norm:
                    TMDB_CACHE["series"][norm] = item
        except Exception:
            pass

    print(f"TMDB cache: movies={len(TMDB_CACHE['movies'])} series={len(TMDB_CACHE['series'])}")


# ---------------- WORKER (NETWORK) ----------------
def validate_and_fetch_server(server_data):
    url = server_data["url"]
    user = server_data["user"]
    pw = server_data["pass"]

    base = f"{url}/player_api.php?username={user}&password={pw}"

    try:
        auth = fetch_json(base)
        if "user_info" not in auth or auth["user_info"].get("status") != "Active":
            return {"status": "invalid", "server": server_data}

        user_info = auth["user_info"]

        # Categories
        cats_live = [] if SKIP_LIVE else fetch_list(f"{base}&action=get_live_categories")
        cats_vod = fetch_list(f"{base}&action=get_vod_categories")
        cats_series = fetch_list(f"{base}&action=get_series_categories")

        # Streams
        live = [] if SKIP_LIVE else fetch_list(f"{base}&action=get_live_streams")
        vods = fetch_list(f"{base}&action=get_vod_streams")
        series = fetch_list(f"{base}&action=get_series")

        return {
            "status": "success",
            "server": server_data,
            "info": user_info,
            "categories": {"live": cats_live, "movie": cats_vod, "series": cats_series},
            "streams": {"live": live, "movie": vods, "series": series},
        }

    except Exception as e:
        return {"status": "failed", "server": server_data, "error": str(e)}


# ---------------- MAIN ----------------
def upsert_server(cur, s_data, info):
    server_name = urlparse(s_data["url"]).netloc

    # SQLite upsert via ON CONFLICT (requires SQLite 3.24+; GitHub runners have this)
    cur.execute(
        """
        INSERT INTO servers (server_url, username, password, server_name, status, active_cons, max_connections, last_checked)
        VALUES (?, ?, ?, ?, 'active', ?, ?, datetime('now'))
        ON CONFLICT(server_url, username) DO UPDATE SET
            password=excluded.password,
            server_name=excluded.server_name,
            status=excluded.status,
            active_cons=excluded.active_cons,
            max_connections=excluded.max_connections,
            last_checked=excluded.last_checked
        """,
        (
            s_data["url"],
            s_data["user"],
            s_data["pass"],
            server_name,
            info.get("active_cons", 0),
            info.get("max_connections", 0),
        ),
    )

    # Find server_id
    cur.execute(
        "SELECT id FROM servers WHERE server_url=? AND username=?",
        (s_data["url"], s_data["user"]),
    )
    row = cur.fetchone()
    return row[0], server_name


def main():
    conn = connect_db()
    cur = conn.cursor()

    servers_to_check = parse_servers_from_url()
    pre_fetch_tmdb_popular()

    print(
        f"Starting parallel validation of {len(servers_to_check)} servers "
        f"(workers={MAX_WORKERS}, skip_live={int(SKIP_LIVE)}, only_tmdb={int(ONLY_TMDB_MATCHED)}, plot_maxlen={PLOT_MAXLEN})"
    )

    valid_count = 0
    total_movies = 0
    total_series = 0
    total_live = 0

    with concurrent.futures.ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        futures = {executor.submit(validate_and_fetch_server, s): s for s in servers_to_check}

        for i, future in enumerate(concurrent.futures.as_completed(futures), 1):
            res = future.result()
            s_data = res["server"]

            if res["status"] != "success":
                print(f"[{i}/{len(servers_to_check)}] ❌ {s_data['url']} ({res['status']})")
                continue

            valid_count += 1

            # Upsert server and get server_id
            server_id, server_name = upsert_server(cur, s_data, res["info"])

            # --- Categories ---
            cat_batch = []
            for c_type, cats in res["categories"].items():
                for c in cats:
                    cat_batch.append(
                        (c.get("category_id"), server_id, c.get("category_name"), c_type)
                    )
            if cat_batch:
                cur.executemany(
                    """
                    INSERT INTO categories (category_id, server_id, category_name, content_type, updated_at)
                    VALUES (?, ?, ?, ?, datetime('now'))
                    ON CONFLICT(category_id, server_id, content_type) DO UPDATE SET
                        category_name=excluded.category_name,
                        updated_at=excluded.updated_at
                    """,
                    cat_batch,
                )

            # --- Movies ---
            movie_batch = []
            for m in res["streams"]["movie"]:
                name = m.get("name", "")
                if not name:
                    continue
                name_norm = normalize_name(name)

                tmdb = TMDB_CACHE["movies"].get(name_norm)
                if ONLY_TMDB_MATCHED and not tmdb:
                    continue

                plot = safe_trunc((tmdb or {}).get("overview") or m.get("plot"), PLOT_MAXLEN)

                movie_batch.append(
                    (
                        m.get("stream_id"),
                        server_id,
                        name,
                        name_norm,
                        m.get("stream_icon"),
                        plot,
                        (tmdb or {}).get("release_date") or m.get("releaseDate"),
                        str((tmdb or {}).get("vote_average") or m.get("rating") or ""),
                        (tmdb or {}).get("id"),
                        None,  # imdb_id not available in this fast path
                        float((tmdb or {}).get("popularity") or 0),
                        float((tmdb or {}).get("vote_average") or 0),
                        int((tmdb or {}).get("vote_count") or 0),
                        m.get("container_extension"),
                    )
                )

            if movie_batch:
                cur.executemany(
                    """
                    INSERT INTO movies
                    (stream_id, server_id, name, name_normalized, stream_icon, plot, releaseDate, rating,
                     tmdb_id, imdb_id, tmdb_popularity, tmdb_vote_average, tmdb_vote_count, container_extension, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, datetime('now'))
                    ON CONFLICT(stream_id, server_id) DO UPDATE SET
                        name=excluded.name,
                        name_normalized=excluded.name_normalized,
                        stream_icon=excluded.stream_icon,
                        plot=excluded.plot,
                        releaseDate=excluded.releaseDate,
                        rating=excluded.rating,
                        tmdb_id=excluded.tmdb_id,
                        imdb_id=excluded.imdb_id,
                        tmdb_popularity=excluded.tmdb_popularity,
                        tmdb_vote_average=excluded.tmdb_vote_average,
                        tmdb_vote_count=excluded.tmdb_vote_count,
                        container_extension=excluded.container_extension,
                        updated_at=excluded.updated_at
                    """,
                    movie_batch,
                )
                total_movies += len(movie_batch)

            # --- Series ---
            series_batch = []
            for s in res["streams"]["series"]:
                name = s.get("name", "")
                if not name:
                    continue
                name_norm = normalize_name(name)

                tmdb = TMDB_CACHE["series"].get(name_norm)
                if ONLY_TMDB_MATCHED and not tmdb:
                    continue

                plot = safe_trunc((tmdb or {}).get("overview") or s.get("plot"), PLOT_MAXLEN)

                series_batch.append(
                    (
                        s.get("series_id"),
                        server_id,
                        name,
                        name_norm,
                        s.get("cover"),
                        plot,
                        (tmdb or {}).get("first_air_date") or s.get("releaseDate"),
                        str((tmdb or {}).get("vote_average") or s.get("rating") or ""),
                        (tmdb or {}).get("id"),
                        None,
                        float((tmdb or {}).get("popularity") or 0),
                        float((tmdb or {}).get("vote_average") or 0),
                        int((tmdb or {}).get("vote_count") or 0),
                    )
                )

            if series_batch:
                cur.executemany(
                    """
                    INSERT INTO series
                    (series_id, server_id, name, name_normalized, cover, plot, releaseDate, rating,
                     tmdb_id, imdb_id, tmdb_popularity, tmdb_vote_average, tmdb_vote_count, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, datetime('now'))
                    ON CONFLICT(series_id, server_id) DO UPDATE SET
                        name=excluded.name,
                        name_normalized=excluded.name_normalized,
                        cover=excluded.cover,
                        plot=excluded.plot,
                        releaseDate=excluded.releaseDate,
                        rating=excluded.rating,
                        tmdb_id=excluded.tmdb_id,
                        imdb_id=excluded.imdb_id,
                        tmdb_popularity=excluded.tmdb_popularity,
                        tmdb_vote_average=excluded.tmdb_vote_average,
                        tmdb_vote_count=excluded.tmdb_vote_count,
                        updated_at=excluded.updated_at
                    """,
                    series_batch,
                )
                total_series += len(series_batch)

            # --- Live Channels (optional) ---
            if not SKIP_LIVE:
                live_batch = []
                for l in res["streams"]["live"]:
                    name = l.get("name", "")
                    if not name:
                        continue
                    live_batch.append(
                        (
                            l.get("stream_id"),
                            server_id,
                            name,
                            l.get("stream_icon"),
                            l.get("epg_channel_id"),
                            l.get("category_id"),
                        )
                    )

                if live_batch:
                    cur.executemany(
                        """
                        INSERT INTO live_channels
                        (stream_id, server_id, name, stream_icon, epg_channel_id, category_id, updated_at)
                        VALUES (?, ?, ?, ?, ?, ?, datetime('now'))
                        ON CONFLICT(stream_id, server_id) DO UPDATE SET
                            name=excluded.name,
                            stream_icon=excluded.stream_icon,
                            epg_channel_id=excluded.epg_channel_id,
                            category_id=excluded.category_id,
                            updated_at=excluded.updated_at
                        """,
                        live_batch,
                    )
                    total_live += len(live_batch)

            # Commit once per valid server (keeps memory stable, DB consistent)
            conn.commit()

            print(
                f"[{i}/{len(servers_to_check)}] ✅ {server_name} | "
                f"movies+{len(movie_batch)} series+{len(series_batch)}"
                + (f" live+{len(res['streams']['live'])}" if not SKIP_LIVE else " live(skipped)")
            )

    # Vacuum occasionally helps reclaim space (especially if you removed lots of rows in old runs).
    # It can take time on big DBs; keep enabled if size is priority.
    try:
        cur.execute("VACUUM;")
        conn.commit()
    except Exception:
        pass

    conn.close()

    print("=" * 60)
    print(f"BUILD COMPLETE: {DB_FILE}")
    print(f"Valid Servers: {valid_count}/{len(servers_to_check)}")
    print(f"Movies indexed: {total_movies} | Series indexed: {total_series} | Live indexed: {total_live}")
    print("=" * 60)


if __name__ == "__main__":
    main()
