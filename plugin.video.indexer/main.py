import sys
import urllib.parse
import requests
from bs4 import BeautifulSoup
from ftplib import FTP
import xbmcgui
import xbmcplugin
import xbmc
import xbmcaddon
import xbmcvfs
import os
import json
import re
import time
from contextlib import closing
from queue import Queue, Empty
from concurrent.futures import ThreadPoolExecutor
import threading

# --- Settings ---
PAGE_SIZE = 50
VIDEO_EXTENSIONS = ['.mkv', '.mp4', '.avi', '.mov', '.flv', '.wmv', '.ts', '.vob', '.mpg', '.mpeg', '.3gp', '.webm']
TMDB_BASE_URL = "https://api.themoviedb.org/3"
TMDB_IMG_URL = "https://image.tmdb.org/t/p/w500"
# --- End Settings ---

_BASE_URL = sys.argv[0]
_HANDLE = int(sys.argv[1])

ADDON = xbmcaddon.Addon()
ADDON_PROFILE_DIR = ADDON.getAddonInfo('profile')
PROFILES_FILE = os.path.join(ADDON_PROFILE_DIR, 'profiles.json')

# --- Profile Management ---
if not xbmcvfs.exists(ADDON_PROFILE_DIR):
    xbmcvfs.mkdirs(ADDON_PROFILE_DIR)

def read_profiles():
    if not xbmcvfs.exists(PROFILES_FILE):
        return []
    with closing(xbmcvfs.File(PROFILES_FILE, 'r')) as f:
        content = f.read()
    try:
        return json.loads(content)
    except json.JSONDecodeError:
        return []

def write_profiles(profiles):
    with closing(xbmcvfs.File(PROFILES_FILE, 'w')) as f:
        f.write(json.dumps(profiles, indent=4))

def get_profile_by_id(profile_id):
    for p in read_profiles():
        if p['id'] == profile_id:
            return p
    return None

# --- TMDb API Logic ---
def get_tmdb_api_key():
    return ADDON.getSetting('tmdb_api_key')

def fetch_metadata(title, year, media_type):
    api_key = get_tmdb_api_key()
    if not api_key: return None

    search_type = 'tv' if media_type == 'tv_show' else 'movie'
    params = {'api_key': api_key, 'query': title, 'language': 'en-US'}
    if year: params['year'] = year

    try:
        response = requests.get(f"{TMDB_BASE_URL}/search/{search_type}", params=params, timeout=15)
        response.raise_for_status()
        results = response.json().get('results', [])
        if not results: return None
        
        tmdb_id = results[0]['id']
        details_response = requests.get(f"{TMDB_BASE_URL}/{search_type}/{tmdb_id}", params={'api_key': api_key, 'language': 'en-US'}, timeout=15)
        details_response.raise_for_status()
        details = details_response.json()

        # --- Start of trailer logic ---
        trailer_url = ''
        youtube_id = ''
        videos_response = None
        if search_type == 'movie':
            videos_response = requests.get(f"{TMDB_BASE_URL}/movie/{tmdb_id}/videos", params={'api_key': api_key}, timeout=15)
        elif search_type == 'tv':
            videos_response = requests.get(f"{TMDB_BASE_URL}/tv/{tmdb_id}/videos", params={'api_key': api_key}, timeout=15)

        if videos_response and videos_response.status_code == 200:
            videos = videos_response.json().get('results', [])
            for video in videos:
                if video['site'] == 'YouTube' and video['type'] == 'Trailer':
                    youtube_id = video['key']
                    break

        trailer_preference = ADDON.getSetting('trailer_playback') # Returns "0" or "1"

        # Option 1: TMDb Helper
        if trailer_preference == '1':
            trailer_url = f"plugin://plugin.video.themoviedb.helper/play/?type=trailer&tmdb_type={search_type}&tmdb_id={tmdb_id}"
        
        # Option 0 (default): YouTube Addon
        else:
            if youtube_id:
                trailer_url = f"plugin://plugin.video.youtube/play/?video_id={youtube_id}"
            else:
                trailer_url = f"plugin://plugin.video.themoviedb.helper/play/?type=trailer&tmdb_type={search_type}&tmdb_id={tmdb_id}"

        # --- End of trailer logic ---

        date_str = details.get('release_date') or details.get('first_air_date') or ''
        release_year = 0
        if date_str and '-' in date_str:
            try: release_year = int(date_str.split('-')[0])
            except (ValueError, IndexError): release_year = 0

        info = {
            'title': details.get('title') or details.get('name'),
            'originaltitle': details.get('original_title') or details.get('original_name'),
            'year': release_year,
            'plot': details.get('overview'),
            'rating': details.get('vote_average'),
            'genre': ' / '.join([g['name'] for g in details.get('genres', [])]),
            'mediatype': search_type,
            'tmdb_id': tmdb_id,
            'trailer': trailer_url
        }
        art = {
            'poster': f"{TMDB_IMG_URL}{details.get('poster_path')}" if details.get('poster_path') else '',
            'fanart': f"https://image.tmdb.org/t/p/original{details.get('backdrop_path')}" if details.get('backdrop_path') else ''
        }
        return {'info': info, 'art': art, 'tmdb_id': tmdb_id}

    except requests.RequestException: return None

# --- Core Logic ---
def build_url(query):
    return _BASE_URL + "?" + urllib.parse.urlencode(query)

def clean_and_get_year(filename):
    title = os.path.splitext(filename)[0]
    title = title.replace('.', ' ').replace('_', ' ')
    year = None
    match = re.search(r'(\b(19|20)\d{2}\b)', title)
    if match:
        year = match.group(1)
        title = title[:match.start()]
    junk_keywords = ['4k', '2160p', '1080p', '720p', 'hdr', 'web', 'hd', 'sd', 'dvd', 'rip', 'x264', 'x265', 'h264', 'h265', 'dolores', 'bluray', 'webrip', 'hdrip', 'dvdrip', 'brrip', 'truehd', 'atmos']
    for keyword in junk_keywords:
        title = re.sub(r'\b' + re.escape(keyword) + r'\b', '', title, flags=re.IGNORECASE)
    return ' '.join(title.split()).strip(), year

def get_all_media(media_type):
    aggregated_media = {}
    profiles = read_profiles()
    for profile in profiles:
        cache_file = os.path.join(ADDON_PROFILE_DIR, f"cache_{profile['id']}.json")
        if xbmcvfs.exists(cache_file):
            with closing(xbmcvfs.File(cache_file, 'r')) as f:
                media = json.loads(f.read())
            
            if media_type == 'movies' and isinstance(media.get('movies'), dict):
                for tmdb_id, movie_data in media.get('movies', {}).items():
                    if tmdb_id not in aggregated_media:
                        aggregated_media[tmdb_id] = {
                            'info': movie_data.get('info'),
                            'art': movie_data.get('art'),
                            'sources': []
                        }
                    for source in movie_data.get('sources', []):
                        source_copy = source.copy()
                        source_copy['profile_id'] = profile['id']
                        aggregated_media[tmdb_id]['sources'].append(source_copy)
            elif media_type == 'tv_shows' and isinstance(media.get('tv_shows'), dict):
                 for tmdb_id, show_data in media.get('tv_shows', {}).items():
                    if tmdb_id not in aggregated_media:
                        aggregated_media[tmdb_id] = show_data
                    aggregated_media[tmdb_id]['profile_id'] = profile['id']

    return list(aggregated_media.values())

# --- Scanning Logic ---
def scan_library(profile_id, scan_mode):
    profile = get_profile_by_id(profile_id)
    if not profile: return

    api_key = get_tmdb_api_key()
    if not api_key:
        xbmcgui.Dialog().ok("API Key Missing", "Please enter your TMDb API key in the addon settings.")
        ADDON.openSettings()
        return

    dialog = xbmcgui.DialogProgress()
    dialog.create(f"Scanning Profile: {profile['name']}", 'Initializing...')

    cancel_event = threading.Event()
    results_container = {'paths': None}
    progress_queue = Queue()

    def _scan_runner():
        profile_type = profile.get('type', 'ftp')
        max_workers = int(ADDON.getSetting('parallel_connections'))
        
        paths = []
        try:
            if profile_type == 'ftp':
                paths = scan_ftp_parallel(profile, scan_mode, max_workers, cancel_event, progress_queue)
            elif profile_type == 'http':
                paths = scan_http_parallel(profile, scan_mode, max_workers, cancel_event, progress_queue)
            
            if not cancel_event.is_set():
                results_container['paths'] = paths
        except Exception as e:
            xbmc.log(f"Error in scan runner thread: {e}", level=xbmc.LOGERROR)
            results_container['paths'] = None 

    scan_thread = threading.Thread(target=_scan_runner)
    scan_thread.start()

    while scan_thread.is_alive():
        if dialog.iscanceled():
            cancel_event.set()
        try:
            progress = progress_queue.get(timeout=0.1)
            dialog.update(progress['percent'], f"{progress.get('line1', '')}\n{progress.get('line2', '')}")
        except Empty:
            pass
        time.sleep(0.1)
    
    scan_thread.join()

    if cancel_event.is_set():
        dialog.close()
        return

    all_video_paths_on_server = results_container['paths']
    if all_video_paths_on_server is None:
        dialog.close()
        xbmcgui.Dialog().ok("Scan Failed", "Could not connect to the server. Check logs for details.")
        return

    dialog.update(50, 'Fetching metadata for new items...')
    cache_file = os.path.join(ADDON_PROFILE_DIR, f"cache_{profile['id']}.json")
    media = {'movies': {}, 'tv_shows': {}}
    if scan_mode == 'incremental' and xbmcvfs.exists(cache_file):
        with closing(xbmcvfs.File(cache_file, 'r')) as f:
            media = json.loads(f.read())

    new_files_count = 0
    processed_files = 0
    total_files = len(all_video_paths_on_server)
    max_workers = int(ADDON.getSetting('parallel_connections'))

    def metadata_worker(path):
        # 1. Check for season folder structure
        match = re.search(r'/(Season|Sezon|Sezonul|S|SO)[\s._]?(\d+)/', path, re.IGNORECASE)
        if match:
            show_folder_path = path[:match.start(0)]
            show_name, year = clean_and_get_year(os.path.basename(urllib.parse.unquote(show_folder_path)))
            metadata = fetch_metadata(show_name, year, 'tv_show')
            # Pass the match object through
            if metadata:
                return path, metadata, 'tv_show', {'folder_match': match}

        filename = os.path.basename(urllib.parse.unquote(path))
        # 2. Check for filename patterns (e.g., S01E01, 1x01)
        tv_match = re.search(r'(?:[._\s-]|^)(?:S(\d{1,2})E(\d{1,2})|(\d{1,2})x(\d{1,2}))', filename, re.IGNORECASE)
        if tv_match:
            # Show name is the parent directory
            show_name, year = clean_and_get_year(os.path.basename(os.path.dirname(path)))
            metadata = fetch_metadata(show_name, year, 'tv_show')
            
            season_num = tv_match.group(1) or tv_match.group(3)
            episode_num = tv_match.group(2) or tv_match.group(4)
            
            # Pass the extracted numbers through if metadata was found
            if metadata:
                return path, metadata, 'tv_show', {'season': season_num, 'episode': episode_num}

        # 3. Fallback to movie
        title, year = clean_and_get_year(filename)
        if title:
            metadata = fetch_metadata(title, year, 'movie')
            return path, metadata, 'movie', None
            
        return path, None, None, None

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        from concurrent.futures import as_completed
        future_to_path = {executor.submit(metadata_worker, path): path for path in all_video_paths_on_server}
        for future in as_completed(future_to_path):
            if cancel_event.is_set() or dialog.iscanceled():
                for f in future_to_path:
                    f.cancel()
                break

            path, metadata, media_type, context = future.result()
            processed_files += 1
            percentage = 50 + int((processed_files / total_files) * 50) if total_files > 0 else 50
            dialog.update(percentage, f"Processing: {os.path.basename(path)}")

            if not metadata or not metadata.get('tmdb_id'):
                continue

            tmdb_id = str(metadata['tmdb_id'])

            if media_type == 'tv_show':
                if tmdb_id not in media['tv_shows']:
                    media['tv_shows'][tmdb_id] = {'seasons': {}, 'info': metadata['info'], 'art': metadata['art']}

                season_name = None
                if context and 'folder_match' in context:
                    match = context['folder_match']
                    season_group = match.group(1)
                    season_number = match.group(2)
                    if season_group.upper() in ['S', 'SO']:
                        season_name = f"Season {season_number.zfill(2)}"
                    else:
                        season_name = f"{season_group.capitalize()} {season_number.zfill(2)}"
                
                elif context and 'season' in context:
                    season_number = context['season']
                    season_name = f"Season {str(season_number).zfill(2)}"

                if season_name:
                    if season_name not in media['tv_shows'][tmdb_id]['seasons']:
                        media['tv_shows'][tmdb_id]['seasons'][season_name] = []
                    
                    if path not in media['tv_shows'][tmdb_id]['seasons'][season_name]:
                        media['tv_shows'][tmdb_id]['seasons'][season_name].append(path)
                        new_files_count += 1
            
            elif media_type == 'movie':
                source_entry = {'path': path, 'filename': os.path.basename(path)}
                if tmdb_id not in media['movies']:
                    media['movies'][tmdb_id] = {'info': metadata['info'], 'art': metadata['art'], 'sources': [source_entry]}
                    new_files_count += 1
                else:
                    if not any(s['path'] == path for s in media['movies'][tmdb_id]['sources']):
                        media['movies'][tmdb_id]['sources'].append(source_entry)
                        new_files_count += 1

    dialog.close()

    if not cancel_event.is_set():
        with closing(xbmcvfs.File(cache_file, 'w')) as f:
            f.write(json.dumps(media, indent=4))
        
        msg = f"Added/Updated {new_files_count} files." if scan_mode == 'incremental' else f"Library built successfully."
        xbmcgui.Dialog().ok('Scan Complete', msg)
        xbmc.executebuiltin('Container.Refresh')

def get_existing_paths_from_cache(cache_file):
    existing_paths = set()
    if xbmcvfs.exists(cache_file):
        with closing(xbmcvfs.File(cache_file, 'r')) as f:
            media = json.loads(f.read())
        for movie_data in media.get('movies', {}).values():
            for source in movie_data.get('sources',[]): existing_paths.add(source['path'])
        for show_data in media.get('tv_shows', {}).values():
            for season in show_data.get('seasons', {}).values(): existing_paths.update(season)
    return existing_paths

def scan_ftp_parallel(profile, scan_mode, max_workers, cancel_event, progress_queue):
    results = []
    results_lock = threading.Lock()
    q = Queue()
    q.put(profile['path'])
    scanned_paths = {profile['path']}
    scanned_paths_lock = threading.Lock()
    
    connection_errors = 0
    connection_errors_lock = threading.Lock()

    def worker():
        nonlocal connection_errors
        ftp = None
        try:
            user = 'anonymous' if profile['anonymous'] else profile['user']
            password = '' if profile['anonymous'] else profile['pass']
            ftp = FTP(profile['host'], timeout=30)
            ftp.login(user, password)
        except Exception as e:
            with connection_errors_lock:
                connection_errors += 1
            xbmc.log(f"FTP worker failed to connect: {e}", level=xbmc.LOGERROR)
            return

        while not cancel_event.is_set():
            try:
                current_path = q.get(timeout=1)
            except Empty:
                break

            try:
                with scanned_paths_lock:
                    total_discovered = len(scanned_paths)
                    scanned_count = total_discovered - q.qsize()
                    if total_discovered > 0:
                        percentage = int((scanned_count / total_discovered) * 49)
                        with results_lock:
                            line1 = f"Found {len(results)} video files..."
                        line2 = f"Scanning: {current_path}"
                        progress_queue.put({'percent': percentage, 'line1': line1, 'line2': line2})

                items = ftp.nlst(current_path)
                for item_name in items:
                    if cancel_event.is_set(): break
                    full_path = os.path.join(current_path, os.path.basename(item_name)).replace('\\', '/')
                    if any(full_path.lower().endswith(ext) for ext in VIDEO_EXTENSIONS):
                        with results_lock:
                            results.append(full_path)
                    elif '.' not in os.path.basename(item_name):
                        with scanned_paths_lock:
                            if full_path not in scanned_paths:
                                scanned_paths.add(full_path)
                                q.put(full_path)
            except Exception as e:
                xbmc.log(f"FTP scan error in path {current_path}: {e}", level=xbmc.LOGWARNING)
            finally:
                q.task_done()
        if ftp:
            try:
                ftp.quit()
            except:
                pass

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = [executor.submit(worker) for _ in range(max_workers)]
        for future in futures:
            future.result() 
    
    q.join()

    if not cancel_event.is_set() and connection_errors == max_workers:
        raise ConnectionError(f"All scanning threads failed to connect to {profile['host']}.")

    if cancel_event.is_set(): return None

    if scan_mode == 'incremental':
        cache_file = os.path.join(ADDON_PROFILE_DIR, f"cache_{profile['id']}.json")
        existing_paths = get_existing_paths_from_cache(cache_file)
        results = [p for p in results if p not in existing_paths]

    return results

def scan_http_parallel(profile, scan_mode, max_workers, cancel_event, progress_queue):
    results = []
    results_lock = threading.Lock()
    q = Queue()
    base_url = profile['host']
    start_path = profile['path']
    start_url = base_url.rstrip('/') + '/' + start_path.lstrip('/')
    q.put(start_url)
    scanned_urls = {start_url}
    scanned_urls_lock = threading.Lock()

    connection_errors = 0
    connection_errors_lock = threading.Lock()

    def worker():
        nonlocal connection_errors
        auth = None
        if not profile['anonymous']:
            auth = requests.auth.HTTPBasicAuth(profile['user'], profile['pass'])

        try:
            with requests.Session() as session:
                session.auth = auth
                response = session.get(start_url, timeout=30)
                response.raise_for_status()
        except requests.RequestException as e:
            with connection_errors_lock:
                connection_errors += 1
            xbmc.log(f"HTTP worker failed to connect: {e}", level=xbmc.LOGERROR)
            return

        with requests.Session() as session:
            session.auth = auth
            while not cancel_event.is_set():
                try:
                    current_url = q.get(timeout=1)
                except Empty:
                    break

                try:
                    with scanned_urls_lock:
                        total_discovered = len(scanned_urls)
                        scanned_count = total_discovered - q.qsize()
                        if total_discovered > 0:
                            percentage = int((scanned_count / total_discovered) * 49)
                            with results_lock:
                                line1 = f"Found {len(results)} video files..."
                            line2 = f"Scanning: {urllib.parse.unquote(current_url)}"
                            progress_queue.put({'percent': percentage, 'line1': line1, 'line2': line2})

                    response = session.get(current_url, timeout=30)
                    response.raise_for_status()
                    soup = BeautifulSoup(response.text, 'html.parser')
                    
                    file_table = soup.find('table', {'id': 'fileTable'})
                    if file_table:
                        for a_tag in file_table.find_all('a'):
                            if cancel_event.is_set(): break
                            href = a_tag.get('href')
                            if not href or href.startswith('?') or '/../' in href or a_tag.get_text(strip=True) == '../ (Parent Directory)': continue
                            
                            full_url = urllib.parse.urljoin(current_url, href)
                            
                            if any(full_url.lower().endswith(ext) for ext in VIDEO_EXTENSIONS):
                                path = urllib.parse.urlparse(full_url).path
                                with results_lock:
                                    if path not in results:
                                        results.append(path)
                            elif href.endswith('/'):
                                with scanned_urls_lock:
                                    if full_url not in scanned_urls:
                                        scanned_urls.add(full_url)
                                        q.put(full_url)
                    else:
                        for a_tag in soup.find_all('a'):
                            if cancel_event.is_set(): break
                            href = a_tag.get('href')
                            if not href or href.startswith('?') or '/../' in href or a_tag.get_text(strip=True) == 'Parent Directory': continue
                            
                            full_url = urllib.parse.urljoin(current_url, href)
                            
                            if any(full_url.lower().endswith(ext) for ext in VIDEO_EXTENSIONS):
                                path = urllib.parse.urlparse(full_url).path
                                with results_lock:
                                    if path not in results:
                                        results.append(path)
                            elif href.endswith('/'):
                                with scanned_urls_lock:
                                    if full_url not in scanned_urls:
                                        scanned_urls.add(full_url)
                                        q.put(full_url)
                except requests.RequestException as e:
                    xbmc.log(f"HTTP scan error in url {current_url}: {e}", level=xbmc.LOGWARNING)
                finally:
                    q.task_done()

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = [executor.submit(worker) for _ in range(max_workers)]
        for future in futures:
            future.result()

    q.join()

    if not cancel_event.is_set() and connection_errors == max_workers:
        raise ConnectionError(f"All scanning threads failed to connect to {profile['host']}.")

    if cancel_event.is_set(): return None

    if scan_mode == 'incremental':
        cache_file = os.path.join(ADDON_PROFILE_DIR, f"cache_{profile['id']}.json")
        existing_paths = get_existing_paths_from_cache(cache_file)
        results = [p for p in results if p not in existing_paths]

    return results


# --- UI Functions ---
def set_view():
    try:
        view_type_index = int(ADDON.getSetting('view_type'))
        # Corresponds to the enum in settings.xml: "List|Big List|Thumbnails|Poster Wrap|Wall|Shift"
        view_ids = [50, 51, 54, 500, 501, 502, 503] 
        if 0 <= view_type_index < len(view_ids):
            view_id = view_ids[view_type_index]
            xbmc.executebuiltin(f'Container.SetViewMode({view_id})')
    except Exception as e:
        xbmc.log(f"Error setting view type: {e}", level=xbmc.LOGERROR)

def list_main_menu():
    xbmcplugin.addDirectoryItem(handle=_HANDLE, url=build_url({'action': 'list_media_type_menu', 'type': 'movies'}), listitem=xbmcgui.ListItem(label='Movies'), isFolder=True)
    xbmcplugin.addDirectoryItem(handle=_HANDLE, url=build_url({'action': 'list_media_type_menu', 'type': 'tv_shows'}), listitem=xbmcgui.ListItem(label='TV Shows'), isFolder=True)
    xbmcplugin.addDirectoryItem(handle=_HANDLE, url=build_url({'action': 'get_search_query'}), listitem=xbmcgui.ListItem(label='[COLOR cyan]Search...[/COLOR]'), isFolder=False)
    xbmcplugin.addDirectoryItem(handle=_HANDLE, url=build_url({'action': 'manage_profiles'}), listitem=xbmcgui.ListItem(label='[COLOR yellow]Profile Manager[/COLOR]'), isFolder=True)
    set_view()
    xbmcplugin.endOfDirectory(_HANDLE)

def check_and_install_youtube_addon():
    if not xbmc.getCondVisibility("System.HasAddon(plugin.video.youtube)"):
        dialog = xbmcgui.Dialog()
        if dialog.yesno("YouTube Addon Missing", "The official YouTube addon is recommended for playing trailers. Would you like to install it now?"):
            xbmc.executebuiltin("InstallAddon(plugin.video.youtube)")

def list_media_type_menu(media_type):
    if media_type == 'movies':
        check_and_install_youtube_addon()
    label = media_type.replace('_', ' ').title()
    xbmcplugin.addDirectoryItem(handle=_HANDLE, url=build_url({'action': 'list_filtered_media', 'type': media_type, 'filter_by': 'all', 'page': '1'}), listitem=xbmcgui.ListItem(label=f"All {label}"), isFolder=True)
    xbmcplugin.addDirectoryItem(handle=_HANDLE, url=build_url({'action': 'list_filtered_media', 'type': media_type, 'filter_by': 'popular', 'page': '1'}), listitem=xbmcgui.ListItem(label="Popular"), isFolder=True)
    xbmcplugin.addDirectoryItem(handle=_HANDLE, url=build_url({'action': 'list_by_alphabet', 'type': media_type}), listitem=xbmcgui.ListItem(label="Alphabetic"), isFolder=True)
    xbmcplugin.addDirectoryItem(handle=_HANDLE, url=build_url({'action': 'list_years', 'type': media_type}), listitem=xbmcgui.ListItem(label="By Year"), isFolder=True)
    xbmcplugin.addDirectoryItem(handle=_HANDLE, url=build_url({'action': 'list_genres', 'type': media_type}), listitem=xbmcgui.ListItem(label="By Genre"), isFolder=True)
    set_view()
    xbmcplugin.endOfDirectory(_HANDLE)

def list_by_alphabet(media_type):
    letters = '#ABCDEFGHIJKLMNOPQRSTUVWXYZ'
    for letter in letters:
        li = xbmcgui.ListItem(label=letter)
        url = build_url({'action': 'list_filtered_media', 'type': media_type, 'filter_by': 'alpha', 'filter_value': letter, 'page': '1'})
        xbmcplugin.addDirectoryItem(handle=_HANDLE, url=url, listitem=li, isFolder=True)
    set_view()
    xbmcplugin.endOfDirectory(_HANDLE)

def list_years(media_type):
    all_media = get_all_media(media_type)
    years = sorted(list(set(item['info'].get('year', 0) for item in all_media if item.get('info'))), reverse=True)
    for year in years:
        if year == 0: continue
        li = xbmcgui.ListItem(label=str(year))
        url = build_url({'action': 'list_filtered_media', 'type': media_type, 'filter_by': 'year', 'filter_value': year, 'page': '1'})
        xbmcplugin.addDirectoryItem(handle=_HANDLE, url=url, listitem=li, isFolder=True)
    set_view()
    xbmcplugin.endOfDirectory(_HANDLE)

def list_genres(media_type):
    all_media = get_all_media(media_type)
    genres = set()
    for item in all_media:
        if item.get('info', {}).get('genre'):
            for genre in item['info']['genre'].split(' / '):
                genres.add(genre.strip())
    for genre in sorted(list(genres)):
        li = xbmcgui.ListItem(label=genre)
        url = build_url({'action': 'list_filtered_media', 'type': media_type, 'filter_by': 'genre', 'filter_value': genre, 'page': '1'})
        xbmcplugin.addDirectoryItem(handle=_HANDLE, url=url, listitem=li, isFolder=True)
    set_view()
    xbmcplugin.endOfDirectory(_HANDLE)

def list_filtered_media(media_type, filter_by, page, filter_value=None):
    all_items = get_all_media(media_type)
    
    if filter_by == 'year':
        all_items = [i for i in all_items if i.get('info', {}).get('year') == int(filter_value)]
    elif filter_by == 'genre':
        all_items = [i for i in all_items if filter_value in i.get('info', {}).get('genre', '')]
    elif filter_by == 'alpha':
        if filter_value == '#':
            all_items = [i for i in all_items if not i.get('info',{}).get('title',' ')[0].isalpha()]
        else:
            all_items = [i for i in all_items if i.get('info',{}).get('title','').upper().startswith(filter_value)]

    if filter_by == 'popular':
        all_items.sort(key=lambda x: x.get('info', {}).get('rating', 0), reverse=True)
    elif media_type == 'movies':
        all_items.sort(key=lambda x: x.get('info', {}).get('title', ''))
    elif media_type == 'tv_shows':
        all_items.sort(key=lambda x: x.get('info', {}).get('title', ''))

    total_items = len(all_items)
    start_index = (page - 1) * PAGE_SIZE
    end_index = start_index + PAGE_SIZE
    items_to_display = all_items[start_index:end_index]

    for item in items_to_display:
        info = item.get('info', {})
        art = item.get('art', {})
        tmdb_id = info.get('tmdb_id')
        info_for_kodi = info.copy()
        info_for_kodi.pop('tmdb_id', None)

        if media_type == 'movies':
            li = xbmcgui.ListItem(label=info.get('title', 'Unknown Movie'))
            li.setInfo('video', info_for_kodi)
            li.setArt(art)
            li.setProperty("IsPlayable", "true")
            # Add context menu for trailer
            if info.get('trailer'):
                li.addContextMenuItems([('Play Trailer', f'RunPlugin({build_url({"action": "play_trailer", "trailer_url": info["trailer"]})})')])
            url = build_url({'action': 'play_movie', 'tmdb_id': tmdb_id})
            xbmcplugin.addDirectoryItem(handle=_HANDLE, url=url, listitem=li, isFolder=False)
        elif media_type == 'tv_shows':
            li = xbmcgui.ListItem(label=info.get('title', 'Unknown Show'))
            li.setInfo('video', info_for_kodi)
            li.setArt(art)
            # Add context menu for trailer
            if info.get('trailer'):
                li.addContextMenuItems([('Play Trailer', f'RunPlugin({build_url({"action": "play_trailer", "trailer_url": info["trailer"]})})')])
            url = build_url({'action': 'list_seasons', 'tmdb_id': tmdb_id, 'page': '1'})
            xbmcplugin.addDirectoryItem(handle=_HANDLE, url=url, listitem=li, isFolder=True)

    if end_index < total_items:
        next_page_li = xbmcgui.ListItem(label='[COLOR yellow]Next Page >>[/COLOR]')
        url = build_url({'action': 'list_filtered_media', 'type': media_type, 'filter_by': filter_by, 'filter_value': filter_value, 'page': str(page + 1)})
        xbmcplugin.addDirectoryItem(handle=_HANDLE, url=url, listitem=next_page_li, isFolder=True)
    
    content_type = 'tvshows' if media_type == 'tv_shows' else 'movies'
    xbmcplugin.setContent(_HANDLE, content_type)
    set_view()
    xbmcplugin.endOfDirectory(_HANDLE)


def play_movie(tmdb_id):
    all_movies = get_all_media('movies')
    movie_to_play = None
    for movie in all_movies:
        if str(movie.get('info', {}).get('tmdb_id')) == tmdb_id:
            movie_to_play = movie
            break

    if not movie_to_play or not movie_to_play.get('sources'):
        xbmcgui.Dialog().ok("No Sources", "Could not find any playable sources for this movie.")
        return

    sources = movie_to_play['sources']
    if len(sources) == 1:
        play_video(sources[0]['profile_id'], sources[0]['path'])
        return

    source_labels = []
    for source in sources:
        profile = get_profile_by_id(source['profile_id'])
        profile_name = profile['name'] if profile else 'Unknown'
        label = f"[{profile_name}] {source['filename']}"
        source_labels.append(label)

    dialog = xbmcgui.Dialog()
    choice = dialog.select(movie_to_play['info']['title'], source_labels)

    if choice >= 0:
        selected_source = sources[choice]
        play_video(selected_source['profile_id'], selected_source['path'])

def play_trailer(trailer_url):
    if trailer_url:
        xbmc.log(f"[plugin.video.indexer] Attempting to play trailer: {trailer_url}", level=xbmc.LOGINFO)
        xbmc.Player().play(trailer_url)
    else:
        xbmc.log("[plugin.video.indexer] No trailer URL found.", level=xbmc.LOGWARNING)
        xbmcgui.Dialog().notification("No Trailer", "No trailer URL was found for this item.")


def play_movie(tmdb_id):
    all_movies = get_all_media('movies')
    movie_to_play = None
    for movie in all_movies:
        if str(movie.get('info', {}).get('tmdb_id')) == tmdb_id:
            movie_to_play = movie
            break

    if not movie_to_play or not movie_to_play.get('sources'):
        xbmcgui.Dialog().ok("No Sources", "Could not find any playable sources for this movie.")
        return

    sources = movie_to_play['sources']
    if len(sources) == 1:
        play_video(sources[0]['profile_id'], sources[0]['path'])
        return

    source_labels = []
    for source in sources:
        profile = get_profile_by_id(source['profile_id'])
        profile_name = profile['name'] if profile else 'Unknown'
        label = f"[{profile_name}] {source['filename']}"
        source_labels.append(label)

    dialog = xbmcgui.Dialog()
    choice = dialog.select(movie_to_play['info']['title'], source_labels)

    if choice >= 0:
        selected_source = sources[choice]
        play_video(selected_source['profile_id'], selected_source['path'])

def get_search_query():
    dialog = xbmcgui.Dialog()
    query = dialog.input("Search Library")
    if query:
        url = build_url({'action': 'show_search_results', 'query': query})
        xbmc.executebuiltin(f'Container.Update({url})')

def show_search_results(query):
    query = query.lower()
    all_media = get_all_media('movies') + get_all_media('tv_shows')
    
    search_results = []
    for item in all_media:
        title = item.get('info', {}).get('title', '').lower()
        if query in title:
            search_results.append(item)
    
    for item in sorted(search_results, key=lambda x: x.get('info', {}).get('title')):
        info = item.get('info', {})
        art = item.get('art', {})
        tmdb_id = info.get('tmdb_id')
        info_for_kodi = info.copy()
        info_for_kodi.pop('tmdb_id', None)

        li = xbmcgui.ListItem(label=info.get('title', 'Search Result'))
        li.setInfo('video', info_for_kodi)
        li.setArt(art)
        if info.get('mediatype') == 'movie':
            li.setProperty("IsPlayable", "true")
            url = build_url({'action': 'play_movie', 'tmdb_id': tmdb_id})
            xbmcplugin.addDirectoryItem(handle=_HANDLE, url=url, listitem=li, isFolder=False)
        else:
            url = build_url({'action': 'list_seasons', 'tmdb_id': tmdb_id, 'page': '1'})
            xbmcplugin.addDirectoryItem(handle=_HANDLE, url=url, listitem=li, isFolder=True)

    xbmcplugin.setContent(_HANDLE, 'videos')
    set_view()
    xbmcplugin.endOfDirectory(_HANDLE)

def manage_profiles():
    profiles = read_profiles()
    for profile in profiles:
        profile_type = profile.get('type', 'ftp')
        movie_count = 0
        show_count = 0
        cache_file = os.path.join(ADDON_PROFILE_DIR, f"cache_{profile['id']}.json")
        if xbmcvfs.exists(cache_file):
            try:
                with closing(xbmcvfs.File(cache_file, 'r')) as f:
                    media = json.loads(f.read())
                movie_count = len(media.get('movies', {}))
                show_count = len(media.get('tv_shows', {}))
            except Exception: pass

        label = f"{profile['name']} ({profile_type.upper()}) [COLOR gray]({movie_count} Movies, {show_count} Shows)[/COLOR]"
        li = xbmcgui.ListItem(label=label)
        context_menu = []
        context_menu.append(('[COLOR yellow]Update Library (Fast)[/COLOR]', f"RunPlugin({build_url({'action': 'scan', 'profile_id': profile['id'], 'mode': 'incremental'})})"))
        context_menu.append(('[COLOR orange]Rebuild Library (Full)[/COLOR]', f"RunPlugin({build_url({'action': 'scan', 'profile_id': profile['id'], 'mode': 'full'})})"))
        context_menu.append(('Edit Profile', f"RunPlugin({build_url({'action': 'edit_profile', 'profile_id': profile['id']})})"))
        context_menu.append(('[COLOR red]Delete Profile[/COLOR]', f"RunPlugin({build_url({'action': 'delete_profile', 'profile_id': profile['id']})})"))
        li.addContextMenuItems(context_menu)
        xbmcplugin.addDirectoryItem(handle=_HANDLE, url="", listitem=li, isFolder=False)

    li = xbmcgui.ListItem(label='[COLOR lightgreen]Add New Profile...[/COLOR]')
    url = build_url({'action': 'add_profile'})
    xbmcplugin.addDirectoryItem(handle=_HANDLE, url=url, listitem=li, isFolder=False)
    set_view()
    xbmcplugin.endOfDirectory(_HANDLE)

def add_or_edit_profile(profile_id=None):
    profiles = read_profiles()
    dialog = xbmcgui.Dialog()
    profile_data = get_profile_by_id(profile_id) if profile_id else {}

    if not profile_id:
        profile_type_idx = dialog.select("Select Profile Type", ["FTP", "HTTP"])
        if profile_type_idx < 0: return
        profile_type = ["ftp", "http"][profile_type_idx]
    else:
        profile_type = profile_data.get('type', 'ftp')

    name = dialog.input("Profile Name", defaultt=profile_data.get('name', ""))
    if not name: return
    host = dialog.input(f"{profile_type.upper()} Host/Address (e.g., ftp.server.com or http://server.com)", defaultt=profile_data.get('host', ""))
    if not host: return
    path = dialog.input("Start Path (e.g., /movies/)", defaultt=profile_data.get('path', "/"))
    if not path: return
    is_anonymous = dialog.yesno("Login", "Use Anonymous / No Login?", yeslabel="Yes", nolabel="Username/Password")
    user, password = "", ""
    if not is_anonymous:
        user = dialog.input("Username", defaultt=profile_data.get('user', ""))
        password = dialog.input("Password", option=xbmcgui.INPUT_PASSWORD)

    new_profile = {
        'id': profile_id or str(int(time.time())),
        'name': name, 'type': profile_type, 'host': host, 'path': path, 
        'anonymous': is_anonymous, 'user': user, 'pass': password
    }

    if profile_id:
        profiles = [p for p in profiles if p['id'] != profile_id]
    profiles.append(new_profile)
    write_profiles(profiles)

    if not profile_id:
        scan_library(new_profile['id'], 'full')
    xbmc.executebuiltin('Container.Refresh')

def delete_profile(profile_id):
    if xbmcgui.Dialog().yesno("Confirm Delete", "Are you sure you want to delete this profile and its library?"):
        profiles = [p for p in read_profiles() if p['id'] != profile_id]
        write_profiles(profiles)
        cache_file = os.path.join(ADDON_PROFILE_DIR, f"cache_{profile_id}.json")
        if xbmcvfs.exists(cache_file):
            xbmcvfs.delete(cache_file)
        xbmc.executebuiltin('Container.Refresh')

def play_video(profile_id, path):
    profile = get_profile_by_id(profile_id)
    profile_type = profile.get('type', 'ftp')

    if profile_type == 'ftp':
        user = 'anonymous' if profile['anonymous'] else profile['user']
        password = '' if profile['anonymous'] else profile['pass']
        playable_url = f"ftp://{user}:{password}@{profile['host']}{path}"
    elif profile_type == 'http':
        user_pass = ""
        if not profile['anonymous']:
            user_pass = f"{profile['user']}:{profile['pass']}@"
        host = profile['host'].rstrip('/')
        path = path.lstrip('/')
        base_url_parts = urllib.parse.urlparse(host)
        playable_url = f"{base_url_parts.scheme}://{user_pass}{base_url_parts.netloc}/{path}"

    li = xbmcgui.ListItem(path=playable_url)
    xbmcplugin.setResolvedUrl(_HANDLE, True, listitem=li)

# --- Router and other UI functions ---
def list_seasons(tmdb_id, page):
    all_shows = get_all_media('tv_shows')
    show = next((s for s in all_shows if str(s.get('info',{}).get('tmdb_id')) == tmdb_id), None)
    if not show: return

    all_seasons = sorted(show['seasons'].keys())
    total_items = len(all_seasons)
    start_index = (page - 1) * PAGE_SIZE
    end_index = start_index + PAGE_SIZE
    seasons_to_display = all_seasons[start_index:end_index]
    for season_name in seasons_to_display:
        li = xbmcgui.ListItem(label=season_name)
        url = build_url({'action': 'list_episodes', 'tmdb_id': tmdb_id, 'season': season_name, 'page': '1'})
        xbmcplugin.addDirectoryItem(handle=_HANDLE, url=url, listitem=li, isFolder=True)
    if end_index < total_items:
        next_page_li = xbmcgui.ListItem(label='[COLOR yellow]Next Page >>[/COLOR]')
        url = build_url({'action': 'list_seasons', 'tmdb_id': tmdb_id, 'page': str(page + 1)})
        xbmcplugin.addDirectoryItem(handle=_HANDLE, url=url, listitem=next_page_li, isFolder=True)
    xbmcplugin.setContent(_HANDLE, 'seasons')
    set_view()
    xbmcplugin.endOfDirectory(_HANDLE)

def list_episodes(tmdb_id, season_name, page):
    all_shows = get_all_media('tv_shows')
    show = next((s for s in all_shows if str(s.get('info',{}).get('tmdb_id')) == tmdb_id), None)
    if not show: return

    all_episodes = sorted(show['seasons'][season_name])
    total_items = len(all_episodes)
    start_index = (page - 1) * PAGE_SIZE
    end_index = start_index + PAGE_SIZE
    episodes_to_display = all_episodes[start_index:end_index]
    for episode_path in episodes_to_display:
        source_profile_id = show.get('profile_id')
        if not source_profile_id: continue

        li = xbmcgui.ListItem(label=os.path.basename(episode_path))
        li.setProperty("IsPlayable", "true")
        url = build_url({'action': 'play', 'profile_id': source_profile_id, 'path': episode_path})
        xbmcplugin.addDirectoryItem(handle=_HANDLE, url=url, listitem=li, isFolder=False)
    if end_index < total_items:
        next_page_li = xbmcgui.ListItem(label='[COLOR yellow]Next Page >>[/COLOR]')
        url = build_url({'action': 'list_episodes', 'tmdb_id': tmdb_id, 'season': season_name, 'page': str(page + 1)})
        xbmcplugin.addDirectoryItem(handle=_HANDLE, url=url, listitem=next_page_li, isFolder=True)
    xbmcplugin.setContent(_HANDLE, 'episodes')
    set_view()
    xbmcplugin.endOfDirectory(_HANDLE)

def router(paramstring):
    params = dict(urllib.parse.parse_qsl(paramstring))
    action = params.get('action')
    page = int(params.get('page', '1'))
    profile_id = params.get('profile_id')
    tmdb_id = params.get('tmdb_id')

    if not action:
        list_main_menu()
    elif action == 'list_media_type_menu':
        list_media_type_menu(params['type'])
    elif action == 'list_filtered_media':
        list_filtered_media(params['type'], params['filter_by'], page, params.get('filter_value'))
    elif action == 'list_years':
        list_years(params['type'])
    elif action == 'list_genres':
        list_genres(params['type'])
    elif action == 'list_by_alphabet':
        list_by_alphabet(params['type'])
    elif action == 'manage_profiles':
        manage_profiles()
    elif action == 'add_profile':
        add_or_edit_profile()
    elif action == 'edit_profile':
        add_or_edit_profile(profile_id)
    elif action == 'delete_profile':
        delete_profile(profile_id)
    elif action == 'scan':
        scan_library(profile_id, params.get('mode', 'full'))
    elif action == 'get_search_query':
        get_search_query()
    elif action == 'show_search_results':
        show_search_results(params['query'])
    elif action == 'play_movie':
        play_movie(tmdb_id)
    elif action == 'play_trailer':
        play_trailer(params.get('trailer_url'))
    elif action == 'list_seasons':
        list_seasons(tmdb_id, page)
    elif action == 'list_episodes':
        list_episodes(tmdb_id, params['season'], page)
    elif action == 'play':
        play_video(profile_id, params['path'])

if __name__ == '__main__':
    router(sys.argv[2][1:])
