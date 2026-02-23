import os
import sqlite3
import json
import requests
import re
from urllib.parse import urlparse, parse_qs
from datetime import datetime
import concurrent.futures

# Configuration
XC_FILE_URL = "https://raw.githubusercontent.com/staycanuca/hub/refs/heads/main/_tools/xc.txt"
TMDB_API_KEY = "304ca56b1b7b57ca7a47d9b59946be94"
DB_FILE = "iptv_aggregator.db"
TIMEOUT = 10
MAX_WORKERS = 20  # For parallel processing

# Create/Connect to SQLite DB
def create_db():
    if os.path.exists(DB_FILE):
        os.remove(DB_FILE)
    
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    # Servers table
    cursor.execute("""
        CREATE TABLE servers (
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
    
    # Movies table
    cursor.execute("""
        CREATE TABLE movies (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            stream_id INTEGER NOT NULL,
            server_id INTEGER NOT NULL,
            name TEXT NOT NULL,
            name_normalized TEXT,
            stream_type TEXT DEFAULT 'movie',
            stream_icon TEXT,
            plot TEXT,
            cast TEXT,
            director TEXT,
            genre TEXT,
            releaseDate TEXT,
            rating TEXT,
            duration TEXT,
            age TEXT,
            tmdb_id INTEGER,
            imdb_id TEXT,
            tmdb_popularity REAL DEFAULT 0,
            tmdb_vote_average REAL DEFAULT 0,
            tmdb_vote_count INTEGER DEFAULT 0,
            container_extension TEXT,
            direct_source TEXT,
            added_at TEXT DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
            last_tmdb_sync TEXT,
            UNIQUE(stream_id, server_id)
        )
    """)
    
    # Series table
    cursor.execute("""
        CREATE TABLE series (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            series_id INTEGER NOT NULL,
            server_id INTEGER NOT NULL,
            name TEXT NOT NULL,
            name_normalized TEXT,
            cover TEXT,
            plot TEXT,
            cast TEXT,
            director TEXT,
            genre TEXT,
            releaseDate TEXT,
            rating TEXT,
            tmdb_id INTEGER,
            imdb_id TEXT,
            tmdb_popularity REAL DEFAULT 0,
            tmdb_vote_average REAL DEFAULT 0,
            tmdb_vote_count INTEGER DEFAULT 0,
            num_seasons INTEGER,
            last_modified TEXT,
            added_at TEXT DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
            last_tmdb_sync TEXT,
            UNIQUE(series_id, server_id)
        )
    """)
    
    # Live channels table
    cursor.execute("""
        CREATE TABLE live_channels (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            stream_id INTEGER NOT NULL,
            server_id INTEGER NOT NULL,
            name TEXT NOT NULL,
            stream_type TEXT DEFAULT 'live',
            stream_icon TEXT,
            epg_channel_id TEXT,
            category_id TEXT,
            container_extension TEXT,
            direct_source TEXT,
            added_at TEXT DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(stream_id, server_id)
        )
    """)
    
    # Categories table
    cursor.execute("""
        CREATE TABLE categories (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            category_id INTEGER NOT NULL,
            server_id INTEGER NOT NULL,
            category_name TEXT NOT NULL,
            parent_id INTEGER,
            content_type TEXT NOT NULL,
            tmdb_category TEXT,
            added_at TEXT DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(category_id, server_id, content_type)
        )
    """)

    # Indexes
    cursor.execute("CREATE INDEX idx_movies_name ON movies(name)")
    cursor.execute("CREATE INDEX idx_movies_name_normalized ON movies(name_normalized)")
    cursor.execute("CREATE INDEX idx_movies_tmdb_popularity ON movies(tmdb_popularity DESC)")
    cursor.execute("CREATE INDEX idx_series_name_normalized ON series(name_normalized)")
    
    conn.commit()
    return conn

def normalize_name(name):
    if not name:
        return ""
    normalized = name.lower()
    normalized = re.sub(r"[^\w\s]", " ", normalized)
    normalized = re.sub(r"\s+", " ", normalized).strip()
    return normalized

def parse_servers_from_url():
    print(f"Fetching servers from {XC_FILE_URL}...")
    response = requests.get(XC_FILE_URL)
    response.raise_for_status()
    
    servers = []
    lines = response.text.splitlines()
    for line in lines:
        line = line.strip()
        if not line or line.startswith('#'):
            continue
            
        if 'username=' in line and 'password=' in line:
            try:
                parsed = urlparse(line)
                q_params = parse_qs(parsed.query)
                user = q_params.get('username', [''])[0]
                pw = q_params.get('password', [''])[0]
                if user and pw:
                    server_url = f"{parsed.scheme}://{parsed.netloc}"
                    servers.append({"url": server_url, "user": user, "pass": pw})
            except:
                pass
    
    print(f"Found {len(servers)} potential servers.")
    # Deduplicate
    unique_servers = {f"{s['url']}_{s['user']}": s for s in servers}.values()
    print(f"Unique servers to check: {len(unique_servers)}")
    return list(unique_servers)

def validate_and_fetch_server(server_data):
    """Worker function to validate server and fetch categories/streams"""
    url = server_data['url']
    user = server_data['user']
    pw = server_data['pass']
    
    auth_url = f"{url}/player_api.php?username={user}&password={pw}"
    headers = {'User-Agent': 'VLC/3.0.20 (Windows; x86_64)'}
    
    try:
        resp = requests.get(auth_url, headers=headers, timeout=TIMEOUT)
        data = resp.json()
        
        if "user_info" in data and data["user_info"].get("status") == "Active":
            # Server is valid, let's fetch its content!
            user_info = data["user_info"]
            
            # 1. Fetch Categories
            cats_live = requests.get(f"{auth_url}&action=get_live_categories", headers=headers, timeout=TIMEOUT).json() if isinstance(requests.get(f"{auth_url}&action=get_live_categories", headers=headers, timeout=TIMEOUT).json(), list) else []
            cats_vod = requests.get(f"{auth_url}&action=get_vod_categories", headers=headers, timeout=TIMEOUT).json() if isinstance(requests.get(f"{auth_url}&action=get_vod_categories", headers=headers, timeout=TIMEOUT).json(), list) else []
            cats_series = requests.get(f"{auth_url}&action=get_series_categories", headers=headers, timeout=TIMEOUT).json() if isinstance(requests.get(f"{auth_url}&action=get_series_categories", headers=headers, timeout=TIMEOUT).json(), list) else []
            
            # 2. Fetch Streams
            live = requests.get(f"{auth_url}&action=get_live_streams", headers=headers, timeout=TIMEOUT).json() if isinstance(requests.get(f"{auth_url}&action=get_live_streams", headers=headers, timeout=TIMEOUT).json(), list) else []
            vods = requests.get(f"{auth_url}&action=get_vod_streams", headers=headers, timeout=TIMEOUT).json() if isinstance(requests.get(f"{auth_url}&action=get_vod_streams", headers=headers, timeout=TIMEOUT).json(), list) else []
            series = requests.get(f"{auth_url}&action=get_series", headers=headers, timeout=TIMEOUT).json() if isinstance(requests.get(f"{auth_url}&action=get_series", headers=headers, timeout=TIMEOUT).json(), list) else []
            
            return {
                "status": "success",
                "server": server_data,
                "info": user_info,
                "categories": {"live": cats_live, "movie": cats_vod, "series": cats_series},
                "streams": {"live": live, "movie": vods, "series": series}
            }
    except Exception as e:
        return {"status": "failed", "server": server_data, "error": str(e)}
        
    return {"status": "invalid", "server": server_data}

# ---------- TMDB CACHING & FETCHING ----------
# To avoid spamming TMDB with 100000 requests, we download the popular lists once
# and match against them locally.
TMDB_CACHE = {"movies": {}, "series": {}}

def pre_fetch_tmdb_popular():
    print("Pre-fetching TMDB Popular/Top-Rated lists for fast matching...")
    # Fetch top 10 pages (200 items) of popular movies and series
    for page in range(1, 11):
        try:
            m_resp = requests.get(f"https://api.themoviedb.org/3/movie/popular?api_key={TMDB_API_KEY}&page={page}").json()
            for m in m_resp.get('results', []):
                norm = normalize_name(m.get('title', ''))
                TMDB_CACHE['movies'][norm] = m
                
            s_resp = requests.get(f"https://api.themoviedb.org/3/tv/popular?api_key={TMDB_API_KEY}&page={page}").json()
            for s in s_resp.get('results', []):
                norm = normalize_name(s.get('name', ''))
                TMDB_CACHE['series'][norm] = s
        except:
            pass
    print(f"Cached {len(TMDB_CACHE['movies'])} TMDB movies and {len(TMDB_CACHE['series'])} TMDB series.")

def main():
    conn = create_db()
    cursor = conn.cursor()
    
    servers_to_check = parse_servers_from_url()
    pre_fetch_tmdb_popular()
    
    print(f"Starting parallel validation and sync of {len(servers_to_check)} servers using {MAX_WORKERS} threads...")
    
    valid_count = 0
    total_movies = 0
    
    with concurrent.futures.ThreadPoolRequest(max_workers=MAX_WORKERS) as executor:
        # Submit all tasks
        future_to_server = {executor.submit(validate_and_fetch_server, s): s for s in servers_to_check}
        
        for i, future in enumerate(concurrent.futures.as_completed(future_to_server), 1):
            res = future.result()
            s_data = res['server']
            
            if res['status'] == 'success':
                valid_count += 1
                server_name = urlparse(s_data['url']).netloc
                
                # 1. Insert Server
                cursor.execute("""
                    INSERT INTO servers (server_url, username, password, server_name, status, active_cons, max_connections)
                    VALUES (?, ?, ?, ?, 'active', ?, ?)
                """, (s_data['url'], s_data['user'], s_data['pass'], server_name, 
                      res['info'].get('active_cons', 0), res['info'].get('max_connections', 0)))
                server_id = cursor.lastrowid
                
                print(f"[{i}/{len(servers_to_check)}] ✅ VALID: {server_name} (Got {len(res['streams']['movie'])} movies)")
                
                # 2. Insert Categories
                cat_batch = []
                for c_type, cats in res['categories'].items():
                    for c in cats:
                        cat_batch.append((c.get('category_id'), server_id, c.get('category_name'), c_type))
                
                if cat_batch:
                    cursor.executemany("INSERT OR IGNORE INTO categories (category_id, server_id, category_name, content_type) VALUES (?, ?, ?, ?)", cat_batch)
                
                # 3. Insert Movies (with local TMDB matching)
                movie_batch = []
                for m in res['streams']['movie']:
                    name = m.get('name', '')
                    name_norm = normalize_name(name)
                    
                    # Quick TMDB Match
                    tmdb_data = TMDB_CACHE['movies'].get(name_norm, {})
                    
                    movie_batch.append((
                        m.get('stream_id'), server_id, name, name_norm, m.get('stream_icon'),
                        m.get('container_extension'),
                        tmdb_data.get('id'),
                        tmdb_data.get('overview', m.get('plot')),
                        tmdb_data.get('vote_average', m.get('rating')),
                        tmdb_data.get('popularity', 0),
                        tmdb_data.get('vote_count', 0),
                        tmdb_data.get('release_date', m.get('releaseDate'))
                    ))
                
                if movie_batch:
                    cursor.executemany("""
                        INSERT OR IGNORE INTO movies 
                        (stream_id, server_id, name, name_normalized, stream_icon, container_extension,
                         tmdb_id, plot, rating, tmdb_popularity, tmdb_vote_count, releaseDate)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, movie_batch)
                    total_movies += len(movie_batch)
                
                # 4. Insert Series
                series_batch = []
                for s in res['streams']['series']:
                    name = s.get('name', '')
                    name_norm = normalize_name(name)
                    tmdb_data = TMDB_CACHE['series'].get(name_norm, {})
                    
                    series_batch.append((
                        s.get('series_id'), server_id, name, name_norm, s.get('cover'),
                        tmdb_data.get('id'), tmdb_data.get('overview', s.get('plot')),
                        tmdb_data.get('vote_average', s.get('rating')), tmdb_data.get('popularity', 0),
                        tmdb_data.get('release_date', s.get('releaseDate'))
                    ))
                    
                if series_batch:
                    cursor.executemany("""
                        INSERT OR IGNORE INTO series 
                        (series_id, server_id, name, name_normalized, cover,
                         tmdb_id, plot, rating, tmdb_popularity, releaseDate)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, series_batch)
                    
                # 5. Insert Live Channels
                live_batch = []
                for l in res['streams']['live']:
                    live_batch.append((
                        l.get('stream_id'), server_id, l.get('name', ''), l.get('stream_icon'), 
                        l.get('epg_channel_id'), l.get('category_id')
                    ))
                if live_batch:
                    cursor.executemany("""
                        INSERT OR IGNORE INTO live_channels 
                        (stream_id, server_id, name, stream_icon, epg_channel_id, category_id)
                        VALUES (?, ?, ?, ?, ?, ?)
                    """, live_batch)

                conn.commit()
                
            else:
                print(f"[{i}/{len(servers_to_check)}] ❌ FAILED: {s_data['url']}")

    conn.close()
    
    print("=" * 50)
    print(f"BUILD COMPLETE! Saved to {DB_FILE}")
    print(f"Valid Servers: {valid_count}/{len(servers_to_check)}")
    print(f"Total Movies Indexed: {total_movies}")
    print("=" * 50)

if __name__ == "__main__":
    main()