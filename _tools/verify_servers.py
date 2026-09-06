import json
import os
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from typing import Optional

import requests
import urllib3
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

SERVERS_URL = os.environ.get(
    "SERVERS_URL",
    "https://raw.githubusercontent.com/staycanuca/hub/refs/heads/main/_tools/servers.json",
)
OUTPUT_FILE = os.environ.get("OUTPUT_FILE", "servers.json")
GITHUB_OUTPUT = os.environ.get("GITHUB_OUTPUT")

CONNECT_TIMEOUT = float(os.environ.get("CONNECT_TIMEOUT", "3"))
READ_TIMEOUT = float(os.environ.get("READ_TIMEOUT", "7"))
MAX_WORKERS = max(1, int(os.environ.get("MAX_WORKERS", "8")))
VERIFY_TLS = os.environ.get("VERIFY_TLS", "false").lower() in {"1", "true", "yes", "on"}
KEEP_UNREACHABLE = os.environ.get("KEEP_UNREACHABLE", "true").lower() in {
    "1", "true", "yes", "on"
}

DEFAULT_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (QtEmbedded; U; Linux; C) AppleWebKit/533.3 "
        "(KHTML, like Gecko) MAG200 stbapp ver: 2 rev: 250 Safari/533.3"
    ),
    "Accept-Encoding": "identity",
    "Accept": "*/*",
    "Connection": "keep-alive",
}

PORTAL_PATHS = (
    "",
    "c/",
    "portal.php",
    "server/load.php",
    "stalker_portal/c/",
    "stalker_portal/server/load.php",
)


@dataclass
class PortalResult:
    ok: bool
    status_code: Optional[int] = None
    checked_url: Optional[str] = None
    error: Optional[str] = None
    elapsed: float = 0.0


def build_session() -> requests.Session:
    retry = Retry(
        total=1,
        connect=1,
        read=0,
        status=1,
        backoff_factor=0.2,
        status_forcelist=(429, 500, 502, 503, 504),
        allowed_methods=frozenset({"GET", "HEAD"}),
        raise_on_status=False,
    )

    adapter = HTTPAdapter(
        max_retries=retry,
        pool_connections=MAX_WORKERS * 2,
        pool_maxsize=MAX_WORKERS * 2,
    )

    session = requests.Session()
    session.headers.update(DEFAULT_HEADERS)
    session.mount("http://", adapter)
    session.mount("https://", adapter)
    return session


def candidate_urls(base_url: str):
    base = base_url.rstrip("/")
    seen = set()

    for suffix in PORTAL_PATHS:
        url = base if not suffix else f"{base}/{suffix}"
        if url not in seen:
            seen.add(url)
            yield url


def check_portal(portal_url: str) -> PortalResult:
    started = time.monotonic()
    last_error = None
    last_status = None

    with build_session() as session:
        for url in candidate_urls(portal_url):
            try:
                response = session.get(
                    url,
                    timeout=(CONNECT_TIMEOUT, READ_TIMEOUT),
                    verify=VERIFY_TLS,
                    allow_redirects=True,
                    stream=True,
                )
                last_status = response.status_code

                # We only need HTTP reachability, not the entire response body.
                response.close()

                if 200 <= response.status_code < 400:
                    return PortalResult(
                        ok=True,
                        status_code=response.status_code,
                        checked_url=url,
                        elapsed=time.monotonic() - started,
                    )

            except requests.RequestException as exc:
                last_error = f"{type(exc).__name__}: {exc}"

    return PortalResult(
        ok=False,
        status_code=last_status,
        error=last_error,
        elapsed=time.monotonic() - started,
    )


def verify_server(index: int, server: dict):
    name = server.get("name") or f"server-{index + 1}"
    portal_url = str(server.get("portal_url") or "").strip()

    if not portal_url:
        return index, server, PortalResult(ok=False, error="missing portal_url")

    result = check_portal(portal_url)
    return index, server, result


def fetch_input() -> dict:
    with build_session() as session:
        response = session.get(
            SERVERS_URL,
            timeout=(5, 20),
            verify=VERIFY_TLS,
        )
        response.raise_for_status()
        return response.json()


def main() -> bool:
    print(f"Fetching servers from: {SERVERS_URL}", flush=True)
    data = fetch_input()

    servers = data.get("servers", [])
    if not isinstance(servers, list):
        raise ValueError("'servers' must be a list")

    print(
        f"Checking {len(servers)} portals "
        f"(workers={MAX_WORKERS}, timeout={CONNECT_TIMEOUT}/{READ_TIMEOUT}s, "
        f"keep_unreachable={KEEP_UNREACHABLE})...",
        flush=True,
    )

    results = [None] * len(servers)

    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        futures = {
            executor.submit(verify_server, index, server): index
            for index, server in enumerate(servers)
        }

        for future in as_completed(futures):
            index = futures[future]
            try:
                _, server, result = future.result()
            except Exception as exc:
                server = servers[index]
                result = PortalResult(
                    ok=False,
                    error=f"{type(exc).__name__}: {exc}",
                )

            results[index] = (server, result)

            name = server.get("name") or f"server-{index + 1}"
            portal_url = server.get("portal_url", "")
            if result.ok:
                print(
                    f"[OK]   {name} - {portal_url} "
                    f"({result.status_code}, {result.elapsed:.1f}s)",
                    flush=True,
                )
            else:
                reason = result.error or f"HTTP {result.status_code}"
                print(
                    f"[FAIL] {name} - {portal_url} "
                    f"({reason}, {result.elapsed:.1f}s)",
                    flush=True,
                )

    reachable = []
    unreachable = []

    for server, result in results:
        if result.ok:
            reachable.append(server)
        else:
            unreachable.append(server)

    # Safety/reliability default:
    # do not delete entries merely because they had one transient network failure.
    if KEEP_UNREACHABLE:
        data["servers"] = servers
    else:
        data["servers"] = reachable

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)
        f.write("\n")

    print(
        f"\nFinished: {len(reachable)}/{len(servers)} portals reachable; "
        f"{len(unreachable)} unreachable.",
        flush=True,
    )

    if GITHUB_OUTPUT:
        with open(GITHUB_OUTPUT, "a", encoding="utf-8") as f:
            f.write(f"reachable_servers={len(reachable)}\n")
            f.write(f"unreachable_servers={len(unreachable)}\n")
            f.write(f"total_servers={len(servers)}\n")

    # Network failures should not make the whole workflow fail.
    # Input/download/JSON errors still raise and fail the job.
    return True


if __name__ == "__main__":
    try:
        success = main()
    except Exception as exc:
        print(f"Fatal error: {type(exc).__name__}: {exc}", file=sys.stderr, flush=True)
        sys.exit(1)

    sys.exit(0 if success else 1)
