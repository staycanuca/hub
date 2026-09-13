#!/usr/bin/env python3
import json
import logging
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
RETRIES = int(os.environ.get("RETRIES", "1"))
LOG_LEVEL = os.environ.get("LOG_LEVEL", "INFO").upper()

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

logger = logging.getLogger(__name__)


@dataclass
class PortalResult:
    ok: bool
    status_code: Optional[int] = None
    checked_url: Optional[str] = None
    error: Optional[str] = None
    elapsed: float = 0.0


def build_session() -> requests.Session:
    # Configure retries (connect/read/status) with small backoff
    retry = Retry(
        total=RETRIES,
        connect=RETRIES,
        read=0,
        status=RETRIES,
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


def check_portal(session: requests.Session, portal_url: str) -> PortalResult:
    started = time.monotonic()
    last_error = None
    last_status = None

    # Try candidate URLs; prefer HEAD (lightweight), fallback to GET
    for url in candidate_urls(portal_url):
        try:
            # First try HEAD to avoid downloading content
            try:
                head_resp = session.head(
                    url,
                    timeout=(CONNECT_TIMEOUT, READ_TIMEOUT),
                    verify=VERIFY_TLS,
                    allow_redirects=True,
                )
                last_status = head_resp.status_code
                # treat 200-399 as success
                if 200 <= head_resp.status_code < 400:
                    return PortalResult(
                        ok=True,
                        status_code=head_resp.status_code,
                        checked_url=url,
                        elapsed=time.monotonic() - started,
                    )
                # Some servers reply 405 Method Not Allowed for HEAD; try GET below
                if head_resp.status_code in (405,):
                    pass
            except requests.RequestException as exc:
                # HEAD may fail for some servers — we will attempt GET next
                last_error = f"{type(exc).__name__}: {exc}"

            # Now try GET but avoid downloading whole body: stream=True and close immediately
            try:
                resp = session.get(
                    url,
                    timeout=(CONNECT_TIMEOUT, READ_TIMEOUT),
                    verify=VERIFY_TLS,
                    allow_redirects=True,
                    stream=True,
                )
                last_status = resp.status_code
                resp.close()
                if 200 <= resp.status_code < 400:
                    return PortalResult(
                        ok=True,
                        status_code=resp.status_code,
                        checked_url=url,
                        elapsed=time.monotonic() - started,
                    )
            except requests.RequestException as exc:
                last_error = f"{type(exc).__name__}: {exc}"

        except Exception as exc:
            # Catch-all to avoid killing the whole run for one bad candidate
            last_error = f"{type(exc).__name__}: {exc}"

    return PortalResult(
        ok=False,
        status_code=last_status,
        error=last_error,
        elapsed=time.monotonic() - started,
    )


def verify_server(index: int, server: dict, session: requests.Session):
    name = server.get("name") or f"server-{index + 1}"
    portal_url = str(server.get("portal_url") or "").strip()

    if not portal_url:
        return index, server, PortalResult(ok=False, error="missing portal_url")

    result = check_portal(session, portal_url)
    return index, server, result


def fetch_input(session: requests.Session) -> dict:
    # Support HTTP(S) or local file paths (file:// or plain path)
    if SERVERS_URL.startswith(("http://", "https://")):
        resp = session.get(SERVERS_URL, timeout=(5, 20), verify=VERIFY_TLS)
        resp.raise_for_status()
        try:
            return resp.json()
        except ValueError as exc:
            raise ValueError(f"Failed to parse JSON from {SERVERS_URL}: {exc}")
    else:
        # treat SERVERS_URL as local path
        path = SERVERS_URL
        if path.startswith("file://"):
            path = path[7:]
        if not os.path.exists(path):
            raise FileNotFoundError(f"Local servers file not found: {path}")
        with open(path, "r", encoding="utf-8") as f:
            try:
                return json.load(f)
            except ValueError as exc:
                raise ValueError(f"Failed to parse JSON from {path}: {exc}")


def main() -> bool:
    logging.basicConfig(
        level=getattr(logging, LOG_LEVEL, logging.INFO),
        format="%(asctime)s %(levelname)-5s %(message)s",
    )

    logger.info("Fetching servers from: %s", SERVERS_URL)
    session = build_session()

    try:
        data = fetch_input(session)
    except Exception:
        logger.exception("Failed to fetch/parse servers input")
        raise

    servers = data.get("servers", [])
    if not isinstance(servers, list):
        raise ValueError("'servers' must be a list")

    logger.info(
        "Checking %d portals (workers=%d, timeout=%ss/%ss, keep_unreachable=%s)...",
        len(servers),
        MAX_WORKERS,
        CONNECT_TIMEOUT,
        READ_TIMEOUT,
        KEEP_UNREACHABLE,
    )

    results = [None] * len(servers)

    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        futures = {
            executor.submit(verify_server, index, server, session): index
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
                logger.info("[OK]   %s - %s (%s, %.1fs)", name, portal_url, result.status_code, result.elapsed)
            else:
                reason = result.error or f"HTTP {result.status_code}"
                logger.warning("[FAIL] %s - %s (%s, %.1fs)", name, portal_url, reason, result.elapsed)

    reachable = []
    unreachable = []

    for server, result in results:
        if result.ok:
            reachable.append(server)
        else:
            unreachable.append(server)

    if KEEP_UNREACHABLE:
        data["servers"] = servers
    else:
        data["servers"] = reachable

    # Write output file
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)
        f.write("\n")

    logger.info(
        "Finished: %d/%d portals reachable; %d unreachable.",
        len(reachable),
        len(servers),
        len(unreachable),
    )

    if GITHUB_OUTPUT:
        try:
            with open(GITHUB_OUTPUT, "a", encoding="utf-8") as f:
                f.write(f"reachable_servers={len(reachable)}\n")
                f.write(f"unreachable_servers={len(unreachable)}\n")
                f.write(f"total_servers={len(servers)}\n")
        except Exception:
            logger.exception("Failed to write to GITHUB_OUTPUT file")

    # Close shared session
    try:
        session.close()
    except Exception:
        logger.debug("Error closing session", exc_info=True)

    return True


if __name__ == "__main__":
    try:
        success = main()
    except Exception as exc:
        # Log full traceback to stderr for CI visibility
        logger.exception("Fatal error")
        print(f"Fatal error: {type(exc).__name__}: {exc}", file=sys.stderr, flush=True)
        sys.exit(1)

    sys.exit(0 if success else 1)
