import os
import time
from urllib.parse import quote_plus

import xbmc
import xbmcaddon
import xbmcgui
import xbmcplugin
import xbmcvfs

from hublive_backend import (
    _normalize_mac,
    clear_failed_mac,
    fetch_series_categories,
    fetch_vod_categories,
    get_fetch_status,
    get_portal_url_for_server,
    get_server_auth,
    get_session,
    invalidate_server_auth,
    iter_server_auth_candidates,
    note_failed_mac,
    set_fetch_status,
)
from playback_state import clear_playback_state

_BROWSE_CACHE_TTL = 300
_browse_cache = {}


def _get_browse_cache_file():
    addon = xbmcaddon.Addon()
    profile_path = addon.getAddonInfo("profile")
    try:
        resolved = xbmcvfs.translatePath(profile_path)
    except Exception:
        resolved = xbmc.translatePath(profile_path)

    if not os.path.exists(resolved):
        os.makedirs(resolved)
    return os.path.join(resolved, "vod_series_cache.json")


def _load_persisted_browse_cache():
    cache_file = _get_browse_cache_file()
    try:
        if not os.path.exists(cache_file):
            return
        import json

        with open(cache_file, "r", encoding="utf-8") as handle:
            payload = json.load(handle)
        if not isinstance(payload, dict):
            return
        now = time.time()
        for key, entry in payload.items():
            if not isinstance(entry, dict):
                continue
            timestamp = float(entry.get("timestamp", 0) or 0)
            if not timestamp or (now - timestamp) >= _BROWSE_CACHE_TTL:
                continue
            _browse_cache[key] = entry
    except Exception as exc:
        xbmc.log(f"[BrowseCache] Failed to load persisted cache: {exc}", level=xbmc.LOGWARNING)


def _persist_browse_cache():
    cache_file = _get_browse_cache_file()
    try:
        import json

        payload = {}
        now = time.time()
        for key, entry in list(_browse_cache.items()):
            timestamp = float(entry.get("timestamp", 0) or 0)
            if not timestamp or (now - timestamp) >= _BROWSE_CACHE_TTL:
                _browse_cache.pop(key, None)
                continue
            payload[key] = entry
        with open(cache_file, "w", encoding="utf-8") as handle:
            json.dump(payload, handle, ensure_ascii=True)
    except Exception as exc:
        xbmc.log(f"[BrowseCache] Failed to persist cache: {exc}", level=xbmc.LOGWARNING)


_load_persisted_browse_cache()


def _build_cache_key(*parts):
    return ":".join(str(part) for part in parts)


def _get_cached_value(*parts):
    cache_key = _build_cache_key(*parts)
    entry = _browse_cache.get(cache_key)
    if not entry:
        return None
    if (time.time() - entry.get("timestamp", 0)) >= _BROWSE_CACHE_TTL:
        _browse_cache.pop(cache_key, None)
        _persist_browse_cache()
        return None
    return entry.get("value")


def _set_cached_value(value, *parts):
    cache_key = _build_cache_key(*parts)
    _browse_cache[cache_key] = {"value": value, "timestamp": time.time()}
    _persist_browse_cache()
    return value


def clear_vod_series_cache(server=None):
    if server is None:
        _browse_cache.clear()
        _persist_browse_cache()
        return

    prefix = f"{server}:"
    for cache_key in list(_browse_cache):
        if cache_key.startswith(prefix):
            _browse_cache.pop(cache_key, None)
    _persist_browse_cache()


def _get_cached_or_fetch(cache_parts, fetch_fn):
    cached_value = _get_cached_value(*cache_parts)
    if cached_value is not None:
        xbmc.log(
            f"[BrowseCache] Using cached data for {'/'.join(map(str, cache_parts))}",
            level=xbmc.LOGDEBUG,
        )
        return cached_value

    fetched_value = fetch_fn()
    if fetched_value:
        return _set_cached_value(fetched_value, *cache_parts)
    return fetched_value


def fetch_stalker_paginated(type_param, category_id, server="server1", timeouts=None):
    """Fetch all pages for a VOD/series category."""
    cache_parts = (server, type_param, "category", category_id)
    cached_items = _get_cached_value(*cache_parts)
    if cached_items is not None:
        return cached_items

    token, headers, cookies, portal_url = get_server_auth(server)
    if not token or not portal_url:
        return []

    base_url = f"{portal_url}/portal.php"
    param_key = "category" if type_param in ["vod", "series"] else "genre"

    all_items = []
    current_page = 1
    total_pages = 1
    request_timeout = (timeouts or {}).get("channels", 20)

    while current_page <= total_pages:
        params = {
            "type": type_param,
            "action": "get_ordered_list",
            param_key: category_id,
            "JsHttpRequest": "1-xml",
            "p": current_page,
        }

        try:
            response = get_session().get(
                base_url,
                params=params,
                headers=headers,
                cookies=cookies,
                timeout=request_timeout,
            )
            response.raise_for_status()
            data = response.json()
            js_data = data.get("js", {})

            if current_page == 1:
                total_items = int(js_data.get("total_items", 0))
                items_first_page = js_data.get("data", [])
                if not items_first_page:
                    break

                items_per_page = len(items_first_page)
                if items_per_page > 0:
                    total_pages = (total_items + items_per_page - 1) // items_per_page

                xbmc.log(
                    f"[Stalker] Total items: {total_items}, Pages: {total_pages} for {type_param} cat {category_id}",
                    level=xbmc.LOGINFO,
                )

            page_items = js_data.get("data", [])
            if not page_items:
                break

            all_items.extend(page_items)
            current_page += 1

            if current_page > 100:
                break

        except Exception as exc:
            xbmc.log(
                f"[Stalker] Pagination error at page {current_page}: {exc}",
                level=xbmc.LOGERROR,
            )
            break

    if all_items:
        _set_cached_value(all_items, *cache_parts)
    return all_items


def fetch_vod_items(category_id, server="server1", timeouts=None):
    return fetch_stalker_paginated("vod", category_id, server, timeouts=timeouts)


def fetch_series_items(category_id, server="server1", timeouts=None):
    return fetch_stalker_paginated("series", category_id, server, timeouts=timeouts)


def list_vod_items(base_url, handle, category_id, server="server1", timeouts=None):
    items = fetch_vod_items(category_id, server, timeouts=timeouts)
    if not items:
        xbmcgui.Dialog().notification(
            "Informații", "Nu există filme în această categorie."
        )
        xbmcplugin.endOfDirectory(handle, succeeded=False)
        return

    for item in items:
        name = item.get("name", "Unknown")
        movie_id = item.get("id")
        li = xbmcgui.ListItem(label=name)
        li.setInfo(
            "video",
            {"title": name, "plot": item.get("description"), "year": item.get("year")},
        )
        li.setProperty("IsPlayable", "true")
        url = f"{base_url}?mode=play_vod&movie_id={movie_id}&server={server}"
        xbmcplugin.addDirectoryItem(handle=handle, url=url, listitem=li, isFolder=False)

    xbmcplugin.endOfDirectory(handle)


def list_series_items(base_url, handle, category_id, server="server1", timeouts=None):
    items = fetch_series_items(category_id, server, timeouts=timeouts)
    if not items:
        xbmcgui.Dialog().notification(
            "Informații", "Nu există seriale în această categorie."
        )
        xbmcplugin.endOfDirectory(handle, succeeded=False)
        return

    for item in items:
        name = item.get("name", "Unknown")
        series_id = item.get("id")
        li = xbmcgui.ListItem(label=name)
        li.setInfo(
            "video",
            {"title": name, "plot": item.get("description"), "year": item.get("year")},
        )
        movie_id = str(series_id).split(":")[0]
        url = f"{base_url}?mode=list_seasons&movie_id={movie_id}&server={server}"
        xbmcplugin.addDirectoryItem(handle=handle, url=url, listitem=li, isFolder=True)

    xbmcplugin.endOfDirectory(handle)


def fetch_seasons(movie_id, server="server1", timeouts=None):
    def _fetch():
        token, headers, cookies, portal_url = get_server_auth(server)
        if not token or not portal_url:
            return []

        url = f"{portal_url}/portal.php?type=series&action=get_ordered_list&movie_id={movie_id}&JsHttpRequest=1-xml"
        try:
            response = get_session().get(
                url,
                headers=headers,
                cookies=cookies,
                timeout=(timeouts or {}).get("channels", 20),
            )
            response.raise_for_status()
            data = response.json()
            return data.get("js", {}).get("data", [])
        except Exception as exc:
            xbmc.log(f"[Series] Failed to fetch seasons: {exc}", level=xbmc.LOGERROR)
            return []

    return _get_cached_or_fetch((server, "series", "seasons", movie_id), _fetch)


def list_seasons(base_url, handle, movie_id, server="server1", timeouts=None):
    seasons = fetch_seasons(movie_id, server, timeouts=timeouts)
    if not seasons:
        xbmcgui.Dialog().notification(
            "Informații", "Nu există sezoane pentru acest serial."
        )
        xbmcplugin.endOfDirectory(handle, succeeded=False)
        return

    for season in seasons:
        li = xbmcgui.ListItem(label=season.get("name", "Unknown Season"))
        url = (
            f"{base_url}?mode=list_episodes&movie_id={movie_id}"
            f"&season_id={season.get('id')}&server={server}"
        )
        xbmcplugin.addDirectoryItem(handle=handle, url=url, listitem=li, isFolder=True)

    xbmcplugin.endOfDirectory(handle)


def fetch_episodes(movie_id, season_id, server="server1", timeouts=None):
    def _fetch():
        token, headers, cookies, portal_url = get_server_auth(server)
        if not token or not portal_url:
            return []

        url = f"{portal_url}/portal.php?type=series&action=get_ordered_list&movie_id={movie_id}&season_id={season_id}&JsHttpRequest=1-xml"
        try:
            response = get_session().get(
                url,
                headers=headers,
                cookies=cookies,
                timeout=(timeouts or {}).get("channels", 20),
            )
            response.raise_for_status()
            data = response.json()
            return data.get("js", {}).get("data", [])
        except Exception as exc:
            xbmc.log(f"[Series] Failed to fetch episodes: {exc}", level=xbmc.LOGERROR)
            return []

    return _get_cached_or_fetch(
        (server, "series", "episodes", movie_id, season_id), _fetch
    )


def list_episodes(
    base_url, handle, movie_id, season_id, server="server1", timeouts=None
):
    episodes_data = fetch_episodes(movie_id, season_id, server, timeouts=timeouts)
    if not episodes_data or not isinstance(episodes_data, list):
        xbmcgui.Dialog().notification(
            "Informații", "Nu există episoade pentru acest sezon."
        )
        xbmcplugin.endOfDirectory(handle, succeeded=False)
        return

    season_info = episodes_data[0]
    episodes_list = season_info.get("series", [])
    season_cmd = season_info.get("cmd")

    for ep_num in episodes_list:
        label = f"Episodul {ep_num}"
        li = xbmcgui.ListItem(label=label)
        li.setProperty("IsPlayable", "true")
        url = (
            f"{base_url}?mode=play_series&cmd={quote_plus(str(season_cmd))}"
            f"&episode={ep_num}&server={server}"
        )
        xbmcplugin.addDirectoryItem(handle=handle, url=url, listitem=li, isFolder=False)

    xbmcplugin.endOfDirectory(handle)


def _play_with_auth_candidates(
    handle,
    server,
    title,
    kind,
    success_message,
    build_request_url_fn,
    resolve_stream_url_fn,
    finalize_playback_failure_fn,
    timeouts=None,
):
    clear_playback_state()
    portal_url = get_portal_url_for_server(server)
    if not portal_url:
        finalize_playback_failure_fn(
            server,
            portal_url,
            0,
            "Portal URL is not configured.",
            title,
            kind=kind,
        )
        return

    attempted_macs = set()
    attempts = 0
    last_error = "Nu s-a putut genera link-ul de redare."
    dp = xbmcgui.DialogProgress()
    dp.create("Se caută stream valid...", "Se testează streamul...")
    dp.update(0)

    try:
        for token, headers, cookies, portal_url, mac in iter_server_auth_candidates(
            server=server,
            use_cached=True,
            exclude_macs=attempted_macs,
            max_attempts=4,
        ):
            if dp.iscanceled():
                clear_playback_state()
                return

            attempts += 1
            dp.update(int(((attempts - 1) / 4) * 100), "Se încearcă conectarea...")
            norm_mac = _normalize_mac(mac)
            if norm_mac:
                attempted_macs.add(norm_mac)

            try:
                request_url = build_request_url_fn(portal_url, mac)
                response = get_session().get(
                    request_url,
                    headers=headers,
                    cookies=cookies,
                    timeout=(timeouts or {}).get("play", 15),
                )
                response.raise_for_status()
                final_url = resolve_stream_url_fn(
                    response.json(), portal_url, mac, headers
                )

                clear_failed_mac(server, mac)
                set_fetch_status(
                    "playback",
                    server,
                    status="ok",
                    message=f"{success_message} cu MAC {mac}",
                    portal_online=True,
                    attempts=attempts,
                    used_cache=False,
                    stale_cache=False,
                    item_count=1,
                )
                xbmc.log(f"[{kind.upper()}] Playing URL: {final_url}", level=xbmc.LOGINFO)
                clear_playback_state()
                li = xbmcgui.ListItem(path=final_url)
                xbmcplugin.setResolvedUrl(handle, True, listitem=li)
                return
            except Exception as exc:
                last_error = str(exc) or last_error
                note_failed_mac(server, mac)
                invalidate_server_auth(server, mac=mac)
                xbmc.log(
                    f"[{kind.upper()}] Attempt {attempts} failed for MAC {mac}: {last_error}",
                    level=xbmc.LOGWARNING,
                )
    finally:
        dp.close()

    finalize_playback_failure_fn(
        server, portal_url, attempts, last_error, title, kind=kind
    )


def _resolve_vod_stream_url(
    data,
    portal_url,
    mac,
    movie_id,
    normalize_playback_url_fn,
    probe_stream_url_fn,
    headers,
):
    returned_url = data.get("js", {}).get("cmd")
    if not returned_url:
        raise ValueError("Serverul nu a returnat comanda de redare pentru film.")

    final_url = normalize_playback_url_fn(returned_url)
    if "play_token=" in final_url:
        try:
            play_token = final_url.split("play_token=")[1].split("&")[0]
            final_url = f"{portal_url}/play/movie.php?mac={mac}&stream={movie_id}.mkv&play_token={play_token}&type=movie"
        except IndexError:
            raise ValueError(
                "Raspunsul de redare pentru film nu contine play_token valid."
            )

    is_valid, probe_reason = probe_stream_url_fn(final_url, headers=headers)
    if not is_valid:
        raise ValueError(f"Linkul filmului a picat la verificare: {probe_reason}")
    return final_url


def _resolve_series_stream_url(
    data,
    normalize_playback_url_fn,
    probe_stream_url_fn,
    headers,
):
    stream_url = normalize_playback_url_fn(data.get("js", {}).get("cmd"))
    if not stream_url:
        raise ValueError("Serverul nu a returnat comanda de redare pentru episod.")

    is_valid, probe_reason = probe_stream_url_fn(stream_url, headers=headers)
    if not is_valid:
        raise ValueError(f"Linkul episodului a picat la verificare: {probe_reason}")
    return stream_url


def play_vod(
    handle,
    movie_id,
    server="server1",
    normalize_playback_url_fn=None,
    probe_stream_url_fn=None,
    finalize_playback_failure_fn=None,
    timeouts=None,
):
    cmd = f"movie {movie_id}"
    _play_with_auth_candidates(
        handle=handle,
        server=server,
        title="Redarea filmului",
        kind="vod",
        success_message="Film pornit",
        build_request_url_fn=lambda portal_url, mac: (
            f"{portal_url}/portal.php?type=vod&action=create_link&cmd={quote_plus(cmd)}&JsHttpRequest=1-xml"
        ),
        resolve_stream_url_fn=lambda data, portal_url, mac, headers: _resolve_vod_stream_url(
            data,
            portal_url,
            mac,
            movie_id,
            normalize_playback_url_fn,
            probe_stream_url_fn,
            headers,
        ),
        finalize_playback_failure_fn=finalize_playback_failure_fn,
        timeouts=timeouts,
    )


def play_series(
    handle,
    cmd,
    episode_num,
    server="server1",
    normalize_playback_url_fn=None,
    probe_stream_url_fn=None,
    finalize_playback_failure_fn=None,
    timeouts=None,
):
    _play_with_auth_candidates(
        handle=handle,
        server=server,
        title="Redarea episodului",
        kind="series",
        success_message="Episod pornit",
        build_request_url_fn=lambda portal_url, mac: (
            f"{portal_url}/portal.php?type=vod&action=create_link&cmd={quote_plus(str(cmd))}&series={episode_num}&JsHttpRequest=1-xml"
        ),
        resolve_stream_url_fn=lambda data, portal_url, mac, headers: _resolve_series_stream_url(
            data,
            normalize_playback_url_fn,
            probe_stream_url_fn,
            headers,
        ),
        finalize_playback_failure_fn=finalize_playback_failure_fn,
        timeouts=timeouts,
    )


def list_vod_categories(base_url, handle, server="server1"):
    categories = _get_cached_or_fetch(
        (server, "vod", "categories"), lambda: fetch_vod_categories(server)
    )
    if not categories:
        status = get_fetch_status("vod_categories", server)
        if status.get("portal_online") is False:
            message = "Portalul serverului pare indisponibil."
        elif status.get("attempts", 0) > 0:
            message = (
                f"Nu s-au putut încărca categoriile după {status['attempts']} MAC-uri."
            )
        else:
            message = "Nu există categorii VOD."
        xbmcgui.Dialog().notification("Informații", message)
        xbmcplugin.endOfDirectory(handle, succeeded=False)
        return

    xbmcplugin.setPluginCategory(handle, "Filme")
    xbmcplugin.setContent(handle, "videos")

    search_button = xbmcgui.ListItem(label="[COLOR yellow]Cauta Film[/COLOR]")
    search_button.setArt(
        {"thumb": "DefaultAddonsSearch.png", "icon": "DefaultAddonsSearch.png"}
    )
    search_button.setProperty("IsPlayable", "false")
    search_button_url = f"{base_url}?mode=search_input_vod&server={server}"
    xbmcplugin.addDirectoryItem(
        handle=handle,
        url=search_button_url,
        listitem=search_button,
        isFolder=False,
    )

    for cat in categories:
        li = xbmcgui.ListItem(label=cat.get("title", "Unknown"))
        url = f"{base_url}?mode=list_vod_items&category_id={cat.get('id')}&server={server}"
        xbmcplugin.addDirectoryItem(handle=handle, url=url, listitem=li, isFolder=True)

    xbmcplugin.endOfDirectory(handle)


def list_series_categories(base_url, handle, server="server1"):
    categories = _get_cached_or_fetch(
        (server, "series", "categories"), lambda: fetch_series_categories(server)
    )
    if not categories:
        status = get_fetch_status("series_categories", server)
        if status.get("portal_online") is False:
            message = "Portalul serverului pare indisponibil."
        elif status.get("attempts", 0) > 0:
            message = (
                f"Nu s-au putut încărca categoriile după {status['attempts']} MAC-uri."
            )
        else:
            message = "Nu există categorii pentru seriale."
        xbmcgui.Dialog().notification("Informații", message)
        xbmcplugin.endOfDirectory(handle, succeeded=False)
        return

    xbmcplugin.setPluginCategory(handle, "Seriale")
    xbmcplugin.setContent(handle, "videos")

    search_button = xbmcgui.ListItem(label="[COLOR yellow]Cauta Serial[/COLOR]")
    search_button.setArt(
        {"thumb": "DefaultAddonsSearch.png", "icon": "DefaultAddonsSearch.png"}
    )
    search_button.setProperty("IsPlayable", "false")
    search_button_url = f"{base_url}?mode=search_input_series&server={server}"
    xbmcplugin.addDirectoryItem(
        handle=handle,
        url=search_button_url,
        listitem=search_button,
        isFolder=False,
    )

    for cat in categories:
        li = xbmcgui.ListItem(label=cat.get("title", "Unknown"))
        url = f"{base_url}?mode=list_series_items&category_id={cat.get('id')}&server={server}"
        xbmcplugin.addDirectoryItem(handle=handle, url=url, listitem=li, isFolder=True)

    xbmcplugin.endOfDirectory(handle)
