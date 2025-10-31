import sys
import xbmc
import xbmcgui
import xbmcplugin
import xbmcaddon
import urllib.parse
import requests
import json
import os
import re

# Import helper modules
from lib import youtube_api
from lib import cache

# Get addon info
addon = xbmcaddon.Addon()
addon_id = addon.getAddonInfo('id')
addon_name = addon.getAddonInfo('name')
import xbmcvfs
# Translate addon path for filesystem usage
addon_path = xbmcvfs.translatePath(addon.getAddonInfo('path'))
# Get addon data directory
addon_data_path = xbmcvfs.translatePath(f'special://profile/addon_data/{addon_id}/')

# Ensure addon data directory exists
if not xbmcvfs.exists(addon_data_path):
    xbmcvfs.mkdirs(addon_data_path)

# Base URL for the plugin
BASE_URL = sys.argv[0]
# Get the handle for the plugin
HANDLE = int(sys.argv[1])
# Get the query parameters
URL_PARAMS = dict(urllib.parse.parse_qsl(sys.argv[2][1:]))

def build_url(query):
    """Create a URL for the plugin with the specified query parameters."""
    return BASE_URL + '?' + urllib.parse.urlencode(query)


def ensure_youtube_plugin():
    """Check if plugin.video.youtube is installed; notify user if missing."""
    try:
        if xbmc.getCondVisibility('System.HasAddon(plugin.video.youtube)'):
            return True
    except Exception:
        pass
    xbmcgui.Dialog().ok('YouTube necesar', 'Instaleaza pluginul "YouTube" (plugin.video.youtube) pentru a reda videoclipurile.')
    return False


def fetch_online_catube_data():
    """Fetch CaTube data from online source"""
    try:
        # Using the pastebin raw URL
        url = 'https://pastebin.com/raw/Ppu52MY6'
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        data = json.loads(response.text)
        return data
    except Exception as e:
        xbmc.log(f'Error fetching online CaTube data: {str(e)}', xbmc.LOGERROR)
        return None


def list_online_catube_categories():
    """Display the categories from CaTube_DATA."""
    use_online = addon.getSetting('use_online_lists') == 'true'
    data = fetch_online_catube_data() if use_online else None
    if not data:
        # Fallback silently to local data
        list_catube_categories()
        return
    
    for category_name in data:
        url = build_url({'action': 'list_online_catube_items', 'category_name': category_name})
        li = xbmcgui.ListItem(label=category_name.replace('List', '')) # Display name without 'List'
        
        # Use a relevant icon based on category name
        icon_map = {
            'RONewsList': 'channels.png',
            'WorldNewsList': 'channels.png',
            'MusicList': 'playlist.png',
            'SportList': 'playlist.png',
            'DocuList': 'playlist.png',
            'MovieList': 'playlist.png'
        }
        icon_file = icon_map.get(category_name, 'channels.png')
        li.setArt({'thumb': os.path.join(addon_path, 'lib', 'media', icon_file), 
                  'icon': os.path.join(addon_path, 'lib', 'media', icon_file),
                  'fanart': os.path.join(addon_path, 'resources', 'fanart.jpg')})
        xbmcplugin.addDirectoryItem(handle=HANDLE, url=url, listitem=li, isFolder=True)
    xbmcplugin.setContent(HANDLE, 'videos')
    xbmcplugin.endOfDirectory(HANDLE)


def list_online_catube_items(category_name):
    """Display items within a selected CaTube category."""
    data = fetch_online_catube_data()
    if not data:
        xbmcgui.Dialog().notification('Error', 'Could not fetch online data')
        return

    items = data.get(category_name, [])

    for item_data in items:
        if len(item_data) < 6:
            continue  # Skip malformed entries
            
        name, item_id, thumbnail, description, item_type, fanart = item_data
        
        # Normalize item_type to match existing functionality
        if item_type.lower() in ['canal', 'channel']:
            normalized_type = 'channel'
        elif item_type.lower() in ['playlist']:
            normalized_type = 'playlist'
        elif item_type.lower() in ['cautare', 'search']:
            normalized_type = 'search'
        else:
            normalized_type = 'channel'  # default to channel
            
        # Clean name from color codes for display in info labels
        clean_name = re.sub(r'\[COLOR .*?\](.*?)\[/COLOR]', r'\1', name)

        if normalized_type == 'channel':
            url = build_url({'action': 'list_channel_content_from_search', 'channel_id': item_id})
            li = xbmcgui.ListItem(label=name)
            li.setInfo('video', {'title': clean_name, 'plot': description})
            if thumbnail:
                li.setArt({'thumb': thumbnail, 'icon': thumbnail, 'fanart': fanart if fanart else os.path.join(addon_path, 'resources', 'fanart.jpg')})
            else:
                li.setArt({'thumb': os.path.join(addon_path, 'lib', 'media', 'channels.png'), 
                          'icon': os.path.join(addon_path, 'lib', 'media', 'channels.png'),
                          'fanart': os.path.join(addon_path, 'resources', 'fanart.jpg')})
            xbmcplugin.addDirectoryItem(handle=HANDLE, url=url, listitem=li, isFolder=True)
        elif normalized_type == 'playlist':
            url = build_url({'action': 'list_playlist_videos_from_search', 'playlist_id': item_id})
            li = xbmcgui.ListItem(label=name)
            li.setInfo('video', {'title': clean_name, 'plot': description})
            if thumbnail:
                li.setArt({'thumb': thumbnail, 'icon': thumbnail, 'fanart': fanart if fanart else os.path.join(addon_path, 'resources', 'fanart.jpg'), 'poster': thumbnail})
            else:
                li.setArt({'thumb': os.path.join(addon_path, 'lib', 'media', 'playlist.png'), 
                          'icon': os.path.join(addon_path, 'lib', 'media', 'playlist.png'),
                          'fanart': os.path.join(addon_path, 'resources', 'fanart.jpg'),
                          'poster': os.path.join(addon_path, 'lib', 'media', 'playlist.png')})
            xbmcplugin.addDirectoryItem(handle=HANDLE, url=url, listitem=li, isFolder=True)
        elif normalized_type == 'search':
            url = build_url({'action': 'search', 'query': item_id})
            li = xbmcgui.ListItem(label=name)
            li.setInfo('video', {'title': clean_name, 'plot': description})
            if thumbnail:
                li.setArt({'thumb': thumbnail, 'icon': thumbnail, 'fanart': fanart if fanart else os.path.join(addon_path, 'resources', 'fanart.jpg')})
            else:
                li.setArt({'thumb': os.path.join(addon_path, 'lib', 'media', 'search.png'), 
                          'icon': os.path.join(addon_path, 'lib', 'media', 'search.png'),
                          'fanart': os.path.join(addon_path, 'resources', 'fanart.jpg')})
            xbmcplugin.addDirectoryItem(handle=HANDLE, url=url, listitem=li, isFolder=True)

    xbmcplugin.setContent(HANDLE, 'videos')
    xbmcplugin.endOfDirectory(HANDLE)


def format_duration_string(duration_seconds):
    """Format duration in seconds to a human-readable string."""
    if duration_seconds <= 0:
        return ''
    
    hours = duration_seconds // 3600
    minutes = (duration_seconds % 3600) // 60
    seconds = duration_seconds % 60
    
    if hours > 0:
        return f'{hours}h {minutes}m'
    elif minutes > 0:
        return f'{minutes}m'
    else:
        return f'{seconds}s'

def clean_video_title(title):
    """Sanitize title for Kodi: remove emojis/symbols, preserve connectors like [], {}, -, +, :, &, /."""
    import re

    if not title or title == 'N/A':
        return title

    # Allow letters, digits, whitespace and selected punctuation/connectors
    allowed_pattern = r"[^\w\s\-\+\[\]\{\}\(\)\'\.,?!:&/|]"
    cleaned_title = re.sub(allowed_pattern, '', title)

    # Remove common clutter keywords
    clutter_keywords = [
        'film complet', 'subtitrat in romana', 'full movie', 'official video',
        'video oficial', 'hd', 'full hd', '1080p', '720p', '4k', 'subtitrat',
        'romana', 'film', 'movie'
    ]
    for keyword in clutter_keywords:
        cleaned_title = re.sub(r'\b' + re.escape(keyword) + r'\b', '', cleaned_title, flags=re.IGNORECASE)
        
    # Normalize whitespace
    cleaned_title = re.sub(r'\s+', ' ', cleaned_title).strip()
    
    # Capitalize the first letter
    if cleaned_title:
        cleaned_title = cleaned_title[0].upper() + cleaned_title[1:]
        
    return cleaned_title

def get_categories():
    """Return the list of categories."""
    categories = [
        {'name': 'Filme', 'query': 'film complet subtitrat'},
        {'name': 'Acțiune', 'query': 'film de acțiune complet subtitrat'},
        {'name': 'Comedie', 'query': 'comedie film complet subtitrat'},
        {'name': 'Groază', 'query': 'film de groază complet subtitrat'},
        {'name': 'Romantic', 'query': 'film romantic complet subtitrat'},
        {'name': 'Dramă', 'query': 'dramă film complet subtitrat'},
        {'name': 'Familie', 'query': 'film de familie complet subtitrat'},
        {'name': 'Desene animate', 'query': 'desen animat complet subtitrat'},
        {'name': 'Romanesc', 'query': 'film full romanesc'},
        {'name': 'Documentare', 'query': 'film documentar complet subtitrat'},
        {'name': 'Thriller', 'query': 'thriller film complet subtitrat'},
        {'name': 'SF', 'query': 'film SF complet subtitrat'},
        {'name': 'Fantezie', 'query': 'film fantezie complet subtitrat'},
        {'name': 'Aventură', 'query': 'film de aventură complet subtitrat'},
        {'name': 'Istoric', 'query': 'film istoric complet subtitrat'},
        {'name': 'Polițist', 'query': 'film polițist complet subtitrat'},
        {'name': 'Crimă', 'query': 'film criminal complet subtitrat'},
    ]
    return categories

def search_videos(query, event_type=None, page_token=None, search_type=None):
    """Search for videos on YouTube using the API with caching."""
    if page_token:
        # Don't cache paginated results
        return youtube_api.search_videos(query, event_type=event_type, max_results=20, page_token=page_token, search_type=search_type)
    
    # Try to get cached results first
    cached_results = cache.get_cached_results(query)
    if cached_results:
        xbmc.log(f'Using cached results for query: {query}', xbmc.LOGINFO)
        return cached_results
    
    # Get fresh results from API
    results = youtube_api.search_videos(query, event_type=event_type, max_results=20, page_token=page_token, search_type=search_type)
    
    # Cache the results if successful
    if results and 'items' in results:
        cache.save_cached_results(query, results)
        xbmc.log(f'Saved results to cache for query: {query}', xbmc.LOGINFO)
    
    return results

def list_categories():
    """Display the list of categories."""
    # Add an option to show trending videos
    trending_url = build_url({'action': 'search', 'query': 'filme subtitrate', 'search_type': 'video_only', 'apply_duration_filter': True})
    trending_item = xbmcgui.ListItem(label='Filme Subtitrate Trending')
    trending_item.setInfo('video', {'title': 'Filme Subtitrate Trending'})
    trending_item.setArt({'thumb': os.path.join(addon_path, 'lib', 'media', 'trending.png'), 
                         'icon': os.path.join(addon_path, 'lib', 'media', 'trending.png'),
                         'fanart': os.path.join(addon_path, 'resources', 'fanart.jpg'),
                         'poster': os.path.join(addon_path, 'lib', 'media', 'trending.png')})
    xbmcplugin.addDirectoryItem(handle=HANDLE, url=trending_url, listitem=trending_item, isFolder=True)
    
    categories = get_categories()
    
    for category in categories:
        name = category['name']
        query = category['query']
        
        url = build_url({'action': 'search', 'query': query, 'search_type': 'video_only', 'apply_duration_filter': True})
        li = xbmcgui.ListItem(label=name)
        li.setInfo('video', {'title': name})
        # Use a relevant icon based on category name
        icon_map = {
            'Acțiune': 'home.png',
            'Comedie': 'home.png', 
            'Groază': 'home.png',
            'Romantic': 'home.png',
            'Dramă': 'home.png',
            'Familie': 'home.png',
            'Desene animate': 'home.png',
            'Romanesc': 'home.png',
            'Documentare': 'home.png',
            'Thriller': 'home.png',
            'SF': 'home.png',
            'Fantezie': 'home.png',
            'Aventură': 'home.png',
            'Istoric': 'home.png',
            'Polițist': 'home.png',
            'Crimă': 'home.png'
        }
        icon_file = icon_map.get(name, 'home.png')
        li.setArt({'thumb': os.path.join(addon_path, 'lib', 'media', icon_file), 
                  'icon': os.path.join(addon_path, 'lib', 'media', icon_file),
                  'fanart': os.path.join(addon_path, 'resources', 'fanart.jpg'),
                  'poster': os.path.join(addon_path, 'lib', 'media', icon_file)})
        xbmcplugin.addDirectoryItem(handle=HANDLE, url=url, listitem=li, isFolder=True)
    
    # Add search option
    search_url = build_url({'action': 'search'})
    search_item = xbmcgui.ListItem(label='Căutare liberă')
    search_item.setInfo('video', {'title': 'Căutare liberă'})
    search_item.setArt({'thumb': os.path.join(addon_path, 'lib', 'media', 'new_search.png'), 
                       'icon': os.path.join(addon_path, 'lib', 'media', 'new_search.png'),
                       'fanart': os.path.join(addon_path, 'resources', 'fanart.jpg'),
                       'poster': os.path.join(addon_path, 'lib', 'media', 'new_search.png')})
    xbmcplugin.addDirectoryItem(handle=HANDLE, url=search_url, listitem=search_item, isFolder=True)
    
    xbmcplugin.setContent(HANDLE, 'videos')
    xbmcplugin.endOfDirectory(HANDLE)

def list_trending_videos(page_token=None):
    """List trending videos for Romania."""
    # Show progress dialog for large lists
    dp = xbmcgui.DialogProgressBG()
    dp.create('Se încarcă', 'Trending Romania')
    try:
        # Use cached trending results when not paginating
        cache_key = f"trending:RO:{page_token or 'first'}"
        if not page_token:
            cached = cache.get_cached_json(cache_key, namespace='trending')
            if cached:
                results = cached
            else:
                results = youtube_api.get_trending_videos('RO', page_token=page_token)
                if results and 'items' in results:
                    cache.save_cached_json(cache_key, results, namespace='trending')
        else:
            results = youtube_api.get_trending_videos('RO', page_token=page_token)
    finally:
        try:
            dp.close()
        except Exception:
            pass

    if not results or 'items' not in results or not results['items']:
        xbmcgui.Dialog().ok('Info', 'Nu s-au găsit videoclipuri în trending.')
        return

    video_ids = [item['id'] for item in results['items']]
    details_data = youtube_api.get_video_details(video_ids)
    video_details_map = {item['id']: item for item in details_data.get('items', [])}

    for item in results['items']:
        video_id = item['id']
        if video_id not in video_details_map:
            continue

        video_details = video_details_map[video_id]
        title = video_details['snippet']['title']
        cleaned_title = clean_video_title(title)
        thumbnail = video_details['snippet']['thumbnails'].get('medium', {}).get('url', '')
        description = video_details['snippet']['description']
        duration_seconds = youtube_api.parse_duration_to_seconds(video_details.get('contentDetails', {}).get('duration', ''))

        url = build_url({'action': 'play', 'video_id': video_id})
        li = xbmcgui.ListItem(label=cleaned_title)
        li.setInfo('video', {'title': cleaned_title, 'plot': description, 'duration': duration_seconds})
        if thumbnail:
            li.setArt({'thumb': thumbnail, 'icon': thumbnail, 'fanart': thumbnail})
        else:
            li.setArt({'thumb': os.path.join(addon_path, 'lib', 'media', 'trending.png'), 
                      'icon': os.path.join(addon_path, 'lib', 'media', 'trending.png'),
                      'fanart': os.path.join(addon_path, 'resources', 'fanart.jpg')})
        li.setProperty('IsPlayable', 'true')

        add_url = build_url({'action': 'add_to_favorites', 'video_id': video_id})
        li.addContextMenuItems([('Adaugă la favorite', f'RunPlugin({add_url})')])

        xbmcplugin.addDirectoryItem(handle=HANDLE, url=url, listitem=li, isFolder=False)

    if 'nextPageToken' in results:
        next_page_url = build_url({'action': 'list_trending', 'page_token': results['nextPageToken']})
        next_page_item = xbmcgui.ListItem(label='Mai multe rezultate...')
        next_page_item.setArt({'thumb': os.path.join(addon_path, 'lib', 'media', 'trending.png'), 
                              'icon': os.path.join(addon_path, 'lib', 'media', 'trending.png'),
                              'fanart': os.path.join(addon_path, 'resources', 'fanart.jpg')})
        xbmcplugin.addDirectoryItem(handle=HANDLE, url=next_page_url, listitem=next_page_item, isFolder=True)

    xbmcplugin.setContent(HANDLE, 'videos')
    xbmcplugin.endOfDirectory(HANDLE)

def search_action(query=None, page_token=None, event_type=None, search_type=None, apply_duration_filter=False):
    """Handle the search action."""
    if not query:
        keyboard = xbmc.Keyboard('', 'Introduceți termenul de căutare')
        keyboard.doModal()
        if not keyboard.isConfirmed():
            return
        query = keyboard.getText()
        if not query:
            return

    results = search_videos(query, event_type=event_type, page_token=page_token)
    if not results or 'items' not in results or not results['items']:
        xbmcgui.Dialog().ok('Info', 'Nu s-au găsit rezultate.')
        return

    video_ids_to_fetch_details = []
    items_to_process = []

    for item in results['items']:
        kind = item['id'].get('kind')
        if search_type == 'video_only' and kind != 'youtube#video':
            continue # Skip non-video items for video_only search
        
        if kind == 'youtube#video':
            video_ids_to_fetch_details.append(item['id']['videoId'])
            items_to_process.append(item)
        elif kind == 'youtube#channel':
            # For channels, we don't need video details immediately, just display the channel
            items_to_process.append(item)
        elif kind == 'youtube#playlist':
            # For playlists, we don't need video details immediately, just display the playlist
            items_to_process.append(item)

    video_details_map = {}
    if video_ids_to_fetch_details:
        details_data = youtube_api.get_video_details(video_ids_to_fetch_details)
        video_details_map = {item['id']: item for item in details_data.get('items', [])}

    is_live_search = event_type == 'live'

    # Apply duration filtering only when requested (for Filme and Concerte sections)
    max_duration_enabled = False
    max_duration_seconds = 0
    min_duration_enabled = False
    min_duration_seconds = 0
    
    if apply_duration_filter:
        max_duration_enabled = addon.getSetting('max_duration_enabled') == 'true'
        max_duration_seconds = int(addon.getSetting('max_duration_minutes')) * 60 if max_duration_enabled else 0
        min_duration_enabled = addon.getSetting('min_duration_enabled') == 'true'
        min_duration_seconds = int(addon.getSetting('min_duration_minutes')) * 60 if min_duration_enabled else 0
        
        # For movies and concerts, if the user hasn't enabled min duration filter, set a default of 20 minutes
        if not min_duration_enabled:
            # Check if we're in the movies or concerts context by examining the query
            current_query = query.lower() if query else ""
            # Check for movie-related queries (from get_categories function) and concert-related queries
            is_movie_query = any(movie_term in current_query for movie_term in 
                               ['film complet subtitrat', 'filme subtitrate', 'film de acțiune complet subtitrat', 
                                'comedie film complet subtitrat', 'film de groază complet subtitrat', 
                                'film romantic complet subtitrat', 'dramă film complet subtitrat', 
                                'film de familie complet subtitrat', 'desen animat complet subtitrat', 
                                'film full romanesc', 'film documentar complet subtitrat', 
                                'thriller film complet subtitrat', 'film sf complet subtitrat', 
                                'film fantezie complet subtitrat', 'film de aventură complet subtitrat', 
                                'film istoric complet subtitrat', 'film polițist complet subtitrat', 
                                'film criminal complet subtitrat'])
            
            is_concert_query = 'concert' in current_query or current_query == 'concert integral full concert'
            
            if is_movie_query or is_concert_query:
                min_duration_seconds = 20 * 60  # 20 minutes default for movies and concerts

    # Reorder: channels, then playlists, then videos
    ordered = []
    ordered.extend([it for it in items_to_process if it['id'].get('kind') == 'youtube#channel'])
    ordered.extend([it for it in items_to_process if it['id'].get('kind') == 'youtube#playlist'])
    ordered.extend([it for it in items_to_process if it['id'].get('kind') == 'youtube#video'])

    for item in ordered:
        kind = item['id'].get('kind')
        title = item['snippet']['title']
        thumbnail = item['snippet']['thumbnails'].get('medium', {}).get('url', '')
        description = item['snippet']['description']

        if kind == 'youtube#video':
            video_id = item['id']['videoId']
            video_details = video_details_map.get(video_id, {})
            duration_seconds = 0
            if not is_live_search:
                duration_seconds = youtube_api.parse_duration_to_seconds(video_details.get('contentDetails', {}).get('duration', ''))
                
                # Apply duration filtering only when requested (for Filme and Concerte sections)
                if apply_duration_filter:
                    if max_duration_enabled and duration_seconds > max_duration_seconds:
                        continue
                    if min_duration_enabled and duration_seconds < min_duration_seconds:
                        continue

            cleaned_title = clean_video_title(title)
            if is_live_search:
                cleaned_title += ' [COLOR red](Live)[/COLOR]'

            url = build_url({'action': 'play', 'video_id': video_id})
            li = xbmcgui.ListItem(label=cleaned_title)
            li.setInfo('video', {'title': cleaned_title, 'plot': description, 'duration': duration_seconds})
            if thumbnail:
                li.setArt({'thumb': thumbnail, 'icon': thumbnail, 'fanart': thumbnail, 'poster': thumbnail})
            else:
                li.setArt({'thumb': os.path.join(addon_path, 'lib', 'media', 'home.png'), 
                          'icon': os.path.join(addon_path, 'lib', 'media', 'home.png'),
                          'fanart': os.path.join(addon_path, 'resources', 'fanart.jpg'),
                          'poster': os.path.join(addon_path, 'lib', 'media', 'home.png')})
            li.setProperty('IsPlayable', 'true')
            
            add_url = build_url({'action': 'add_to_favorites', 'video_id': video_id, 'content_type': 'video', 'title': cleaned_title})
            li.addContextMenuItems([('Adaugă la favorite', f'RunPlugin({add_url})')])
            
            xbmcplugin.addDirectoryItem(handle=HANDLE, url=url, listitem=li, isFolder=False)

        elif kind == 'youtube#channel':
            channel_id = item['id']['channelId']
            cleaned_title = f'[COLOR blue]Canal:[/COLOR] {clean_video_title(title)}'
            url = build_url({'action': 'list_channel_content_from_search', 'channel_id': channel_id})
            li = xbmcgui.ListItem(label=cleaned_title)
            li.setInfo('video', {'title': cleaned_title, 'plot': description})
            if thumbnail:
                li.setArt({'thumb': thumbnail, 'icon': thumbnail, 'fanart': thumbnail, 'poster': thumbnail})
            else:
                li.setArt({'thumb': os.path.join(addon_path, 'lib', 'media', 'channels.png'), 
                          'icon': os.path.join(addon_path, 'lib', 'media', 'channels.png'),
                          'fanart': os.path.join(addon_path, 'resources', 'fanart.jpg'),
                          'poster': os.path.join(addon_path, 'lib', 'media', 'channels.png')})
            
            # Context menu with both options
            context_menu_items = []
            
            # Add to Custom List
            add_to_custom_url = build_url({'action': 'add_to_custom_list_from_search', 'list_type': 'channel', 'list_id': channel_id, 'list_title': title})
            context_menu_items.append(('Adaugă la Custom List', f'RunPlugin({add_to_custom_url})'))
            
            # Add to Favorites
            add_to_favorites_url = build_url({'action': 'add_to_favorites', 'video_id': channel_id, 'content_type': 'channel', 'title': clean_video_title(title)})
            context_menu_items.append(('Adaugă la favorite', f'RunPlugin({add_to_favorites_url})'))
            
            li.addContextMenuItems(context_menu_items)

            xbmcplugin.addDirectoryItem(handle=HANDLE, url=url, listitem=li, isFolder=True)

        elif kind == 'youtube#playlist':
            playlist_id = item['id']['playlistId']
            cleaned_title = f'[COLOR green]Playlist:[/COLOR] {clean_video_title(title)}'
            url = build_url({'action': 'list_playlist_videos_from_search', 'playlist_id': playlist_id})
            li = xbmcgui.ListItem(label=cleaned_title)
            li.setInfo('video', {'title': cleaned_title, 'plot': description})
            if thumbnail:
                li.setArt({'thumb': thumbnail, 'icon': thumbnail, 'fanart': thumbnail, 'poster': thumbnail})
            else:
                li.setArt({'thumb': os.path.join(addon_path, 'lib', 'media', 'playlist.png'), 
                          'icon': os.path.join(addon_path, 'lib', 'media', 'playlist.png'),
                          'fanart': os.path.join(addon_path, 'resources', 'fanart.jpg'),
                          'poster': os.path.join(addon_path, 'lib', 'media', 'playlist.png')})
            
            # Context menu with both options
            context_menu_items = []
            
            # Add to Custom List
            add_to_custom_url = build_url({'action': 'add_to_custom_list_from_search', 'list_type': 'playlist', 'list_id': playlist_id, 'list_title': title})
            context_menu_items.append(('Adaugă la Custom List', f'RunPlugin({add_to_custom_url})'))
            
            # Add to Favorites
            add_to_favorites_url = build_url({'action': 'add_to_favorites', 'video_id': playlist_id, 'content_type': 'playlist', 'title': clean_video_title(title)})
            context_menu_items.append(('Adaugă la favorite', f'RunPlugin({add_to_favorites_url})'))
            
            li.addContextMenuItems(context_menu_items)

            xbmcplugin.addDirectoryItem(handle=HANDLE, url=url, listitem=li, isFolder=True)

    if 'nextPageToken' in results:
        next_page_url = build_url({'action': 'search', 'query': query, 'page_token': results['nextPageToken'], 'event_type': event_type, 'search_type': search_type, 'apply_duration_filter': apply_duration_filter})
        next_page_item = xbmcgui.ListItem(label='Mai multe rezultate...')
        next_page_item.setArt({'thumb': os.path.join(addon_path, 'lib', 'media', 'new_search.png'), 
                              'icon': os.path.join(addon_path, 'lib', 'media', 'new_search.png'),
                              'fanart': os.path.join(addon_path, 'resources', 'fanart.jpg'),
                              'poster': os.path.join(addon_path, 'lib', 'media', 'new_search.png')})
        xbmcplugin.addDirectoryItem(handle=HANDLE, url=next_page_url, listitem=next_page_item, isFolder=True)

    xbmcplugin.setContent(HANDLE, 'videos')
    xbmcplugin.endOfDirectory(HANDLE)

def list_channel_content_from_search(channel_id, page_token=None):
    """List complete content (videos and playlists) from a channel found in search results."""
    # First, get channel details to show channel info
    channel_data = youtube_api.get_channel_details(channel_id)
    if not channel_data or 'items' not in channel_data or not channel_data['items']:
        xbmcgui.Dialog().ok('Info', 'Nu s-au găsit informații pentru acest canal.')
        return

    channel_info = channel_data['items'][0]
    channel_title = channel_info['snippet']['title']
    channel_description = channel_info['snippet']['description']
    channel_thumbnail = channel_info['snippet']['thumbnails'].get('medium', {}).get('url', '')

    # Add channel header/info item
    header_item = xbmcgui.ListItem(label=f'[COLOR gold]{channel_title}[/COLOR]')
    header_item.setInfo('video', {'title': channel_title, 'plot': channel_description})
    if channel_thumbnail:
        header_item.setArt({'thumb': channel_thumbnail, 'icon': channel_thumbnail, 'fanart': channel_thumbnail})
    else:
        header_item.setArt({'thumb': os.path.join(addon_path, 'lib', 'media', 'channels.png'), 
                           'icon': os.path.join(addon_path, 'lib', 'media', 'channels.png'),
                           'fanart': os.path.join(addon_path, 'resources', 'fanart.jpg')})
    header_item.setProperty('IsPlayable', 'false')
    xbmcplugin.addDirectoryItem(handle=HANDLE, url='', listitem=header_item, isFolder=False)

    # Get videos from the channel
    videos_results = youtube_api.get_channel_videos(channel_id, page_token=page_token)
    video_items = []
    if videos_results and 'items' in videos_results and videos_results['items']:
        video_items = videos_results['items']

    # Get playlists from the channel
    playlists_results = youtube_api.get_channel_playlists(channel_id, page_token=page_token)
    playlist_items = []
    if playlists_results and 'items' in playlists_results and playlists_results['items']:
        playlist_items = playlists_results['items']

    # First playlists, then videos (channels header already added)
    video_ids = [item['snippet']['resourceId']['videoId'] for item in video_items if 'resourceId' in item.get('snippet', {}) and 'videoId' in item['snippet'].get('resourceId', {})]
    video_details_map = {}
    if video_ids:
        details_data = youtube_api.get_video_details(video_ids)
        video_details_map = {item['id']: item for item in details_data.get('items', [])}

    # List playlists first
    for item in playlist_items:
        playlist_id = item['id']
        title = item['snippet']['title']
        description = item['snippet'].get('description', '')
        thumbnail = item['snippet']['thumbnails'].get('medium', {}).get('url', '')
        cleaned_title = f'[COLOR green]Playlist:[/COLOR] {clean_video_title(title)}'
        url = build_url({'action': 'list_playlist_videos_from_search', 'playlist_id': playlist_id})
        li = xbmcgui.ListItem(label=cleaned_title)
        li.setInfo('video', {'title': cleaned_title, 'plot': description})
        if thumbnail:
            li.setArt({'thumb': thumbnail, 'icon': thumbnail, 'fanart': thumbnail, 'poster': thumbnail})
        else:
            li.setArt({'thumb': os.path.join(addon_path, 'lib', 'media', 'playlist.png'), 
                      'icon': os.path.join(addon_path, 'lib', 'media', 'playlist.png'),
                      'fanart': os.path.join(addon_path, 'resources', 'fanart.jpg'),
                      'poster': os.path.join(addon_path, 'lib', 'media', 'playlist.png')})
        xbmcplugin.addDirectoryItem(handle=HANDLE, url=url, listitem=li, isFolder=True)

    # Then videos
    for video_id in video_ids:
        if video_id not in video_details_map:
            continue

        video_details = video_details_map[video_id]
        title = video_details['snippet']['title']
        cleaned_title = clean_video_title(title)
        thumbnail = video_details['snippet']['thumbnails'].get('medium', {}).get('url', '')
        description = video_details['snippet']['description']
        duration_seconds = youtube_api.parse_duration_to_seconds(video_details.get('contentDetails', {}).get('duration', ''))

        url = build_url({'action': 'play', 'video_id': video_id})
        li = xbmcgui.ListItem(label=f'[COLOR white]▶[/COLOR] {cleaned_title}')
        li.setInfo('video', {'title': cleaned_title, 'plot': description, 'duration': duration_seconds})
        if thumbnail:
            li.setArt({'thumb': thumbnail, 'icon': thumbnail, 'fanart': thumbnail})
        else:
            li.setArt({'thumb': os.path.join(addon_path, 'lib', 'media', 'home.png'), 
                      'icon': os.path.join(addon_path, 'lib', 'media', 'home.png'),
                      'fanart': os.path.join(addon_path, 'resources', 'fanart.jpg')})
        li.setProperty('IsPlayable', 'true')

        add_url = build_url({'action': 'add_to_favorites', 'video_id': video_id})
        li.addContextMenuItems([('Adaugă la favorite', f'RunPlugin({add_url})')])

        xbmcplugin.addDirectoryItem(handle=HANDLE, url=url, listitem=li, isFolder=False)

    # (Playlists already listed above to prioritize them)
    for playlist_item in []:
        playlist_id = playlist_item['id']
        title = playlist_item['snippet']['title']
        cleaned_title = clean_video_title(title)
        thumbnail = playlist_item['snippet']['thumbnails'].get('medium', {}).get('url', '')
        description = playlist_item['snippet']['description']

        url = build_url({'action': 'list_playlist_videos_from_search', 'playlist_id': playlist_id})
        li = xbmcgui.ListItem(label=f'[COLOR green] Playlist:[/COLOR] {cleaned_title}')
        li.setInfo('video', {'title': cleaned_title, 'plot': description})
        if thumbnail:
            li.setArt({'thumb': thumbnail, 'icon': thumbnail, 'fanart': thumbnail, 'poster': thumbnail})
        else:
            li.setArt({'thumb': os.path.join(addon_path, 'lib', 'media', 'playlist.png'), 
                      'icon': os.path.join(addon_path, 'lib', 'media', 'playlist.png'),
                      'fanart': os.path.join(addon_path, 'resources', 'fanart.jpg'),
                      'poster': os.path.join(addon_path, 'lib', 'media', 'playlist.png')})

        add_to_custom_url = build_url({'action': 'add_to_custom_list_from_search', 'list_type': 'playlist', 'list_id': playlist_id, 'list_title': title})
        li.addContextMenuItems([('Adaugă la Custom List', f'RunPlugin({add_to_custom_url})')])

        xbmcplugin.addDirectoryItem(handle=HANDLE, url=url, listitem=li, isFolder=True)

    # Handle pagination - for simplicity, we'll use the videos token
    if videos_results and 'nextPageToken' in videos_results:
        next_page_url = build_url({'action': 'list_channel_content_from_search', 'channel_id': channel_id, 'page_token': videos_results['nextPageToken']})
        next_page_item = xbmcgui.ListItem(label='Mai multe rezultate...')
        next_page_item.setArt({'thumb': os.path.join(addon_path, 'lib', 'media', 'channels.png'), 
                              'icon': os.path.join(addon_path, 'lib', 'media', 'channels.png'),
                              'fanart': os.path.join(addon_path, 'resources', 'fanart.jpg')})
        xbmcplugin.addDirectoryItem(handle=HANDLE, url=next_page_url, listitem=next_page_item, isFolder=True)

    xbmcplugin.setContent(HANDLE, 'videos')
    xbmcplugin.endOfDirectory(HANDLE)


def list_user_content_from_search(username, page_token=None):
    """List complete content (videos and playlists) from a user found in search results."""
    # First, get user channel details to show user info
    # Check if username is a handle (starts with @)
    if username.startswith('@'):
        user_data = youtube_api.get_channel_details_by_handle(username)
    else:
        user_data = youtube_api.get_channel_details_by_username(username)
    
    if not user_data or 'items' not in user_data or not user_data['items']:
        xbmcgui.Dialog().ok('Info', 'Nu s-au găsit informații pentru acest utilizator.')
        return

    user_info = user_data['items'][0]
    user_title = user_info['snippet']['title']
    user_description = user_info['snippet']['description']
    user_thumbnail = user_info['snippet']['thumbnails'].get('medium', {}).get('url', '')

    # Add user header/info item
    header_item = xbmcgui.ListItem(label=f'[COLOR gold]{user_title}[/COLOR]')
    header_item.setInfo('video', {'title': user_title, 'plot': user_description})
    if user_thumbnail:
        header_item.setArt({'thumb': user_thumbnail, 'icon': user_thumbnail, 'fanart': user_thumbnail})
    else:
        header_item.setArt({'thumb': os.path.join(addon_path, 'lib', 'media', 'user.png'), 
                           'icon': os.path.join(addon_path, 'lib', 'media', 'user.png'),
                           'fanart': os.path.join(addon_path, 'resources', 'fanart.jpg')})
    header_item.setProperty('IsPlayable', 'false')
    xbmcplugin.addDirectoryItem(handle=HANDLE, url='', listitem=header_item, isFolder=False)

    # Get videos from the user
    if username.startswith('@'):
        videos_results = youtube_api.get_user_videos_by_handle(username, page_token=page_token)
    else:
        videos_results = youtube_api.get_user_videos(username, page_token=page_token)
    video_items = []
    if videos_results and 'items' in videos_results and videos_results['items']:
        video_items = videos_results['items']

    # Get playlists from the user
    if username.startswith('@'):
        playlists_results = youtube_api.get_user_playlists_by_handle(username, page_token=page_token)
    else:
        playlists_results = youtube_api.get_user_playlists(username, page_token=page_token)
    playlist_items = []
    if playlists_results and 'items' in playlists_results and playlists_results['items']:
        playlist_items = playlists_results['items']

    # First playlists, then videos (user header already added)
    video_ids = [item['snippet']['resourceId']['videoId'] for item in video_items if 'resourceId' in item.get('snippet', {}) and 'videoId' in item['snippet'].get('resourceId', {})]
    video_details_map = {}
    if video_ids:
        details_data = youtube_api.get_video_details(video_ids)
        video_details_map = {item['id']: item for item in details_data.get('items', [])}

    # List playlists first
    for item in playlist_items:
        playlist_id = item['id']
        title = item['snippet']['title']
        description = item['snippet'].get('description', '')
        thumbnail = item['snippet']['thumbnails'].get('medium', {}).get('url', '')
        cleaned_title = f'[COLOR green]Playlist:[/COLOR] {clean_video_title(title)}'
        url = build_url({'action': 'list_playlist_videos_from_search', 'playlist_id': playlist_id})
        li = xbmcgui.ListItem(label=cleaned_title)
        li.setInfo('video', {'title': cleaned_title, 'plot': description})
        if thumbnail:
            li.setArt({'thumb': thumbnail, 'icon': thumbnail, 'fanart': thumbnail, 'poster': thumbnail})
        else:
            li.setArt({'thumb': os.path.join(addon_path, 'lib', 'media', 'playlist.png'), 
                      'icon': os.path.join(addon_path, 'lib', 'media', 'playlist.png'),
                      'fanart': os.path.join(addon_path, 'resources', 'fanart.jpg'),
                      'poster': os.path.join(addon_path, 'lib', 'media', 'playlist.png')})
        xbmcplugin.addDirectoryItem(handle=HANDLE, url=url, listitem=li, isFolder=True)

    # Then videos
    for video_id in video_ids:
        if video_id not in video_details_map:
            continue

        video_details = video_details_map[video_id]
        title = video_details['snippet']['title']
        cleaned_title = clean_video_title(title)
        thumbnail = video_details['snippet']['thumbnails'].get('medium', {}).get('url', '')
        description = video_details['snippet']['description']
        duration_seconds = youtube_api.parse_duration_to_seconds(video_details.get('contentDetails', {}).get('duration', ''))

        url = build_url({'action': 'play', 'video_id': video_id})
        li = xbmcgui.ListItem(label=f'[COLOR white]▶[/COLOR] {cleaned_title}')
        li.setInfo('video', {'title': cleaned_title, 'plot': description, 'duration': duration_seconds})
        if thumbnail:
            li.setArt({'thumb': thumbnail, 'icon': thumbnail, 'fanart': thumbnail})
        else:
            li.setArt({'thumb': os.path.join(addon_path, 'lib', 'media', 'home.png'), 
                      'icon': os.path.join(addon_path, 'lib', 'media', 'home.png'),
                      'fanart': os.path.join(addon_path, 'resources', 'fanart.jpg')})
        li.setProperty('IsPlayable', 'true')

        add_url = build_url({'action': 'add_to_favorites', 'video_id': video_id})
        li.addContextMenuItems([('Adaugă la favorite', f'RunPlugin({add_url})')])

        xbmcplugin.addDirectoryItem(handle=HANDLE, url=url, listitem=li, isFolder=False)

    # Process playlists
    for playlist_item in playlist_items:
        playlist_id = playlist_item['id']
        title = playlist_item['snippet']['title']
        cleaned_title = clean_video_title(title)
        thumbnail = playlist_item['snippet']['thumbnails'].get('medium', {}).get('url', '')
        description = playlist_item['snippet']['description']

        url = build_url({'action': 'list_playlist_videos_from_search', 'playlist_id': playlist_id})
        li = xbmcgui.ListItem(label=f'[COLOR green] Playlist:[/COLOR] {cleaned_title}')
        li.setInfo('video', {'title': cleaned_title, 'plot': description})
        if thumbnail:
            li.setArt({'thumb': thumbnail, 'icon': thumbnail, 'fanart': thumbnail, 'poster': thumbnail})
        else:
            li.setArt({'thumb': os.path.join(addon_path, 'lib', 'media', 'playlist.png'), 
                      'icon': os.path.join(addon_path, 'lib', 'media', 'playlist.png'),
                      'fanart': os.path.join(addon_path, 'resources', 'fanart.jpg'),
                      'poster': os.path.join(addon_path, 'lib', 'media', 'playlist.png')})

        add_to_custom_url = build_url({'action': 'add_to_custom_list_from_search', 'list_type': 'playlist', 'list_id': playlist_id, 'list_title': title})
        li.addContextMenuItems([('Adaugă la Custom List', f'RunPlugin({add_to_custom_url})')])

        xbmcplugin.addDirectoryItem(handle=HANDLE, url=url, listitem=li, isFolder=True)

    # Handle pagination - for simplicity, we'll use the videos token
    if videos_results and 'nextPageToken' in videos_results:
        next_page_url = build_url({'action': 'list_user_content_from_search', 'username': username, 'page_token': videos_results['nextPageToken']})
        next_page_item = xbmcgui.ListItem(label='Mai multe rezultate...')
        next_page_item.setArt({'thumb': os.path.join(addon_path, 'lib', 'media', 'user.png'), 
                              'icon': os.path.join(addon_path, 'lib', 'media', 'user.png'),
                              'fanart': os.path.join(addon_path, 'resources', 'fanart.jpg')})
        xbmcplugin.addDirectoryItem(handle=HANDLE, url=next_page_url, listitem=next_page_item, isFolder=True)

    xbmcplugin.setContent(HANDLE, 'videos')
    xbmcplugin.endOfDirectory(HANDLE)


def list_channel_videos_from_search(channel_id, page_token=None):
    """List videos from a channel found in search results."""
    results = youtube_api.get_channel_videos(channel_id, page_token=page_token)
    if not results or 'items' not in results or not results['items']:
        xbmcgui.Dialog().ok('Info', 'Nu s-au găsit videoclipuri pentru acest canal.')
        return

    video_ids = [item['snippet']['resourceId']['videoId'] for item in results['items'] if 'resourceId' in item.get('snippet', {}) and 'videoId' in item['snippet'].get('resourceId', {})]
    if not video_ids:
        xbmcgui.Dialog().ok('Info', 'Nu s-au găsit videoclipuri valide pentru acest canal.')
        return

    details_data = youtube_api.get_video_details(video_ids)
    video_details_map = {item['id']: item for item in details_data.get('items', [])}

    for video_id in video_ids:
        if video_id not in video_details_map:
            continue

        video_details = video_details_map[video_id]
        title = video_details['snippet']['title']
        cleaned_title = clean_video_title(title)
        thumbnail = video_details['snippet']['thumbnails'].get('medium', {}).get('url', '')
        description = video_details['snippet']['description']
        duration_seconds = youtube_api.parse_duration_to_seconds(video_details.get('contentDetails', {}).get('duration', ''))

        url = build_url({'action': 'play', 'video_id': video_id})
        li = xbmcgui.ListItem(label=cleaned_title)
        li.setInfo('video', {'title': cleaned_title, 'plot': description, 'duration': duration_seconds})
        if thumbnail:
            li.setArt({'thumb': thumbnail, 'icon': thumbnail, 'fanart': thumbnail})
        else:
            li.setArt({'thumb': os.path.join(addon_path, 'lib', 'media', 'channels.png'), 
                      'icon': os.path.join(addon_path, 'lib', 'media', 'channels.png'),
                      'fanart': os.path.join(addon_path, 'resources', 'fanart.jpg')})
        li.setProperty('IsPlayable', 'true')

        add_url = build_url({'action': 'add_to_favorites', 'video_id': video_id})
        li.addContextMenuItems([('Adaugă la favorite', f'RunPlugin({add_url})')])

        xbmcplugin.addDirectoryItem(handle=HANDLE, url=url, listitem=li, isFolder=False)

    if 'nextPageToken' in results:
        next_page_url = build_url({'action': 'list_channel_videos_from_search', 'channel_id': channel_id, 'page_token': results['nextPageToken']})
        next_page_item = xbmcgui.ListItem(label='Mai multe rezultate...')
        next_page_item.setArt({'thumb': os.path.join(addon_path, 'lib', 'media', 'channels.png'), 
                              'icon': os.path.join(addon_path, 'lib', 'media', 'channels.png'),
                              'fanart': os.path.join(addon_path, 'resources', 'fanart.jpg')})
        xbmcplugin.addDirectoryItem(handle=HANDLE, url=next_page_url, listitem=next_page_item, isFolder=True)

    xbmcplugin.setContent(HANDLE, 'videos')
    xbmcplugin.endOfDirectory(HANDLE)

def list_playlist_videos_from_search(playlist_id, page_token=None):
    """List videos from a playlist found in search results."""
    results = youtube_api.get_playlist_videos(playlist_id, page_token=page_token)
    if not results or 'items' not in results or not results['items']:
        xbmcgui.Dialog().ok('Info', 'Nu s-au găsit videoclipuri pentru acest playlist.')
        xbmcplugin.endOfDirectory(HANDLE)
        return

    video_ids = [item['snippet']['resourceId']['videoId'] for item in results['items'] if 'resourceId' in item.get('snippet', {}) and 'videoId' in item['snippet'].get('resourceId', {})]
    if not video_ids:
        xbmcgui.Dialog().ok('Info', 'Nu s-au găsit videoclipuri valide pentru acest playlist.')
        xbmcplugin.endOfDirectory(HANDLE)
        return

    details_data = youtube_api.get_video_details(video_ids)
    video_details_map = {item['id']: item for item in details_data.get('items', [])}

    for video_id in video_ids:
        if video_id not in video_details_map:
            continue

        video_details = video_details_map[video_id]
        title = video_details['snippet']['title']
        cleaned_title = clean_video_title(title)
        thumbnail = video_details['snippet']['thumbnails'].get('medium', {}).get('url', '')
        description = video_details['snippet']['description']
        duration_seconds = youtube_api.parse_duration_to_seconds(video_details.get('contentDetails', {}).get('duration', ''))

        url = build_url({'action': 'play', 'video_id': video_id})
        li = xbmcgui.ListItem(label=cleaned_title)
        li.setInfo('video', {'title': cleaned_title, 'plot': description, 'duration': duration_seconds})
        if thumbnail:
            li.setArt({'thumb': thumbnail, 'icon': thumbnail, 'fanart': thumbnail})
        else:
            li.setArt({'thumb': os.path.join(addon_path, 'lib', 'media', 'playlist.png'), 
                      'icon': os.path.join(addon_path, 'lib', 'media', 'playlist.png'),
                      'fanart': os.path.join(addon_path, 'resources', 'fanart.jpg')})
        li.setProperty('IsPlayable', 'true')

        add_url = build_url({'action': 'add_to_favorites', 'video_id': video_id})
        li.addContextMenuItems([('Adaugă la favorite', f'RunPlugin({add_url})')])

        xbmcplugin.addDirectoryItem(handle=HANDLE, url=url, listitem=li, isFolder=False)

    if 'nextPageToken' in results:
        next_page_url = build_url({'action': 'list_playlist_videos_from_search', 'playlist_id': playlist_id, 'page_token': results['nextPageToken']})
        next_page_item = xbmcgui.ListItem(label='Mai multe rezultate...')
        next_page_item.setArt({'thumb': os.path.join(addon_path, 'lib', 'media', 'playlist.png'), 
                              'icon': os.path.join(addon_path, 'lib', 'media', 'playlist.png'),
                              'fanart': os.path.join(addon_path, 'resources', 'fanart.jpg')})
        xbmcplugin.addDirectoryItem(handle=HANDLE, url=next_page_url, listitem=next_page_item, isFolder=True)

    xbmcplugin.setContent(HANDLE, 'videos')
    xbmcplugin.endOfDirectory(HANDLE)

def play_video(video_id):
    """Play a YouTube video."""
    if not video_id:
        return

    # Close any existing busy dialogs
    xbmc.executebuiltin('Dialog.Close(busydialog)')
    
    # Ensure YouTube plugin is available
    if not ensure_youtube_plugin():
        return
    
    # Create the YouTube URL using plugin protocol
    url = f'plugin://plugin.video.youtube/play/?video_id={video_id}'
    
    # Create a playable item
    play_item = xbmcgui.ListItem(path=url)
    play_item.setProperty('IsPlayable', 'true')
    
    # Use the player to play the video
    xbmcplugin.setResolvedUrl(HANDLE, True, play_item)

CATUBE_DATA = {
"RONewsList" :    [
            [ "[COLOR goldenrod]Știrile ProTV[/COLOR]", "UCEJf5cGtkBdZS8Jh2uSW9xw", "https://yt3.googleusercontent.com/QL_9MGrdG0rjl3VnepUexm62El9hFfBBIEeSpv6ObxuHbtZW1va6Gc7t4fUnKGyMipKq_Bo64qg=s900-c-k-c0x00ffffff-no-rj", "De luni pana vineri Andreea Esca si in week-end Oana Andoni aduc telespectatorilor cele mai importante evenimente ale zilei, la Știrile Pro TV. Reportaje speciale, interviuri în exclusivitate, subiecte fierbinţi, corespondenţe din mijlocul evenimentelor, unele neîncheiate inca, toate sunt prezentate in premiera într-o maniera unica si inconfundabila care continuă zilnic.", "channel", "https://image.stirileprotv.ro/media/images/1920x1080/Aug2017/61905284.jpg"],
            [ "[COLOR goldenrod]Prima TV[/COLOR]", "UU6Sn1XzRBCBl8UMyAb8_5PA", "https://yt3.googleusercontent.com/wNjbMThSuIgzXehMvqKya_yJpKxw1KCHRYu6ubw4V3KtprIqupo4a9KrP_5lUjWhKoRi2vlzvQ=s900-c-k-c0x00ffffff-no-rj", "Prima TV Romania - post de televiziune de divertisment. Focus Știri Recente", "playlist","https://i0.1616.ro/media/581/3181/38712/19647434/56/900x600focus.png"],
            [ "[COLOR goldenrod]Stirile Kanal D[/COLOR]", "PLvC_Gs1fsycQvURdN2uj2oWLtHT6GnuYe", "https://static.wikia.nocookie.net/logopedia/images/f/f0/%C8%98tirile_Kanal_D_2020.png", "Principalul jurnal informativ al Kanal D, atât în timpul săptămânii, cât şi în weekend, şi-a consolidat poziţia de pilon important al informării responsabile şi obiective a telespectatorilor şi îşi continuă această misiune nobilă de a informa corect publicul larg.", "playlist","https://i.ytimg.com/vi/4W292GgtLo0/maxresdefault.jpg"],
            [ "[COLOR goldenrod]Observator News[/COLOR]", "UCDhQYbT-x0GzRLbdWKeK2XA", "https://yt3.googleusercontent.com/F-bIRxdRmS49azCWeAt9XO3n5q3-rXEfnGaaTjFuwkinhpS6Dv3X2sCXEKY8KzknsOQ3lKE5ElY=s900-c-k-c0x00ffffff-no-rj", "Observatorul Antena 1 face un salt imens spre viitor, cu o nouă identitate atât la nivel vizual, cât și la nivel editorial. Redacția de știri a Antena 1 devine o platformă de news 360 de grade ce vă aduce cele mai importante știri. Suntem MEREU CU TINE și punem interesul tău în prim plan.", "channel","https://img.observatornews.ro/0/2020/4/19/356676/aplicatia-observatornews-020025b4.jpg"],
            [ "[COLOR goldenrod]Digi24[/COLOR]", "UCbvKamSrJkwT6ed2BMMZXwg", "https://yt3.googleusercontent.com/ytc/AIdro_mbP2NrnPDJjX-PFo2oHs3hRZwquSGDanPalEYSah3RdQ=s900-c-k-c0x00ffffff-no-rj", "Digi24 HD este un post de televiziune de informație non-stop, parte a companiei de telecomunicații RCS & RDS, independent din punct de vedere politic, care își propune să promoveze jurnalismul imparțial, sursa pentru dezbaterea de idei bazată pe rațiune și respect.", "channel", "https://pbs.twimg.com/media/GAQJ2MLWoAAlFVj.jpg"],
            [ "[COLOR goldenrod]Antena 3 CNN[/COLOR]", "UCw9Hc3CD8hbqP-Y9XOJS--Q", "https://pbs.twimg.com/profile_images/1591670289192067074/M1pBMuMF_400x400.jpg", "Canalul oficial de YouTube al postului TV Antena 3 CNN.", "channel", "https://advertising.antena3.ro/wp-content/uploads/2022/12/vlcsnap-2022-12-15-14h14m24s297.png"],
            [ "[COLOR goldenrod]TVR INFO[/COLOR]", "UCfH7r-E65QAbNCthar7d7xA", "https://yt3.googleusercontent.com/xy0YjhX2lrKzRB9CmXcRQ-uCGj5h5kJL4DzLrDRINMCEt4Ac1-0FVDrDzOnZ_ZFRitmUPfwQzg=s900-c-k-c0x00ffffff-no-rj", "Știri de încredere", "channel", "https://i.ytimg.com/vi/8_26NLE18Jk/maxresdefault.jpg"],
            [ "[COLOR goldenrod]Romania TV[/COLOR]", "UC5Bb0itu0pB46xykW32ck0g", "https://yt3.googleusercontent.com/ytc/AIdro_lDFHjeGyp5uCG3lfgbIjlHBCs7kTd8psuLPkfdCHhpiA=s900-c-k-c0x00ffffff-no-rj", "Știri de încredere", "channel", "https://media.evz.ro/wp-content/uploads/2024/01/Romania-TV.jpg"],
            [ "[COLOR goldenrod]Euronews Romania[/COLOR]", "UCbATDExtWstHnwWELZnXNZA", "https://yt3.googleusercontent.com/7hnqtKR6SvzlcptaN0OSJlB-usROZ2_6VgAEOjuDvo0AdFalync5z4bQHRe2eqeuic_QndyWXLE=s900-c-k-c0x00ffffff-no-rj", "Branded affiliate Euronews, principala televiziune de ṣtiri a Europe", "channel", "https://cdn.romania-insider.com/sites/default/files/styles/article_large_image/public/2022-05/euronews_romania_-_photo_euronews_romania_on_fb.jpeg"],
            [ "[COLOR goldenrod]ROMANIA, TE IUBESC![/COLOR]", "UC5zAAr-aeX6fYCVDlzjjiWQ", "https://yt3.googleusercontent.com/ytc/AIdro_m6VjT_CCyskMADZS5-_fFb3IosMi3n4RjnVJ8WL6UvtQ=s160-c-k-c0x00ffffff-no-rj", "“România, te iubesc!”, un program marca Ştirile PRO TV, s-a lansat în 2008 şi de atunci, în fiecare duminică, scrie istorie în televiziune. Paula Herlo, Alex Dima, Rareş Năstase, Cosmin Savu, Paul Angelescu şi gazdă emisiunii, Cristian Leonte aduc în faţă telespectatorilor reportaje şi investigaţii care au schimbat legi, sisteme şi mentalităţi.", "channel", "https://image.stirileprotv.ro/media/images/1920x1080/Mar2020/62116459.jpg"],
            [ "[COLOR goldenrod]Kanal D Romania[/COLOR]", "UCD_R9fKyrQLxlDJsOwvGKyg", "https://i.ibb.co/g6YW2X0/KanalD.png", "Kanal D Romania: un carusel al emotiilor, umorului, povestilor de viata inspirationale si al informatiilor pertinente si relevante. Kanal D continua sa va ofere entertainment de calitate, formate TV unice pe piata din Romania, informatie pura, livrata cu responsabilitate voua, milioanelor de romani care ne urmariti zilnic la TV.", "channel", "https://mir-s3-cdn-cf.behance.net/project_modules/1400_opt_1/ddc36246773021.5bd038a9f3c63.jpg"],
            [ "[COLOR goldenrod]Asta-i Romania[/COLOR]", "PLvC_Gs1fsycRYkbUCkWKxoukDqBlC3YY-", "https://static.wikia.nocookie.net/logopedia/images/f/f0/Asta-i_Rom%C3%A2nia%21_2017.png", "Emisiunea “Asta-i România!”, prezentata de Mihai Ghita, va prezinta in fiecare duminica, de la ora 14:30, situatii la limita rabdarii, dar si povestile unor romani deosebiti care fac ca tara noastra sa fie vazuta si cu ochi buni.", "playlist", "https://i.ytimg.com/vi/8jdnlzGzhRQ/maxresdefault.jpg"],
            [ "[COLOR goldenrod]Românii au talent[/COLOR]", "UC870eIJ80uX6yiTLRZhunNw", "https://yt3.googleusercontent.com/pQVNiD1aAdrKcjlrkJMpdTcEzEZ6n_MbWh7RBvYzO-9IBN5xK5Ye_EiF8kITgYda9DlApEg5vQ=s900-c-k-c0x00ffffff-no-rj", "Românii au talent este o emisiune difuzata de PRO TV în prime time, la ora 20.30. Show-ul de televiziune a debutat la postul PRO TV, în februarie 2011, timp în care a stabilit recorduri de audiență. Emisiunea îi are drept prezentatori pe Smiley și Paveș Bartoș. Din juriul emisiunii Românii au talent fac parte nume importante din showbiz: Andra, Andi Moisescu, Mihai Bobonete și Dragoș Bucur.", "channel", "https://image.stirileprotv.ro/media/images/1920x1080/May2022/62260854.jpg"],

            [ "[COLOR goldenrod]Starea Natiei[/COLOR]", "UCtK5Oe8sHjp6WPcwWuHUVpQ", "https://pbs.twimg.com/media/FwWEJcYWAAYdpPM.jpg", "Bine-ați venit pe canalul oficial Starea Nației, alături de Dragoș Pătraru & friends. Într-o lume în care presa are destule momente în care se abate de la statutul de câine de pază al democrației, lucrurile trebuie rezolvate tot din interiorul breslei. Astfel de emisiuni, care să sancționeze deopotrivă derapajele politicienilor și ale presei, pot contribui serios la însănătoșirea presei.", "channel", "https://i.ytimg.com/vi/jTIsuT9C_vU/maxresdefault.jpg"],
            [ "[COLOR goldenrod]Recorder[/COLOR]", "UChDQ6nYN6XyRU-8IEgbym1g", "https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcS5om7sxeQrDNhqeAgxzS_tSrkaUBeb6DKAnw&s", "Recorder este o publicație online construită în jurul acestor principii: jurnalism onest, făcut cu pasiune și pus în serviciul public.", "channel", "https://recorder.ro/wp-content/uploads/2024/05/Main-2-1920x900.png"],
            [ "[COLOR goldenrod]Știrile zilei. Pe scurt, de la Recorder[/COLOR]", "UC7TCKBwQemiKA4q1srZkeBg", "https://yt3.googleusercontent.com/I8doNivhmGI1hYEhuh3pEuju0ZHV4a74APt-GTAoudfw2tbW8dVPV0PuvMj96syWMoxzpnM2qA=s900-c-k-c0x00ffffff-no-rj", "Cele mai importante știri ale zilei, selecționate de Recorder. De luni până vineri.", "channel", "https://i.ytimg.com/vi/4iE9USHjYJA/hqdefault.jpg"],

            [ "[COLOR goldenrod]TVR[/COLOR]", "UChdrIsYOHZXgEyCLaOHc2Ew", "https://w7.pngwing.com/pngs/1023/287/png-transparent-romanian-television-tvr1-tvr-cluj-bookmaker-television-angle-orange.png", "TVR înseamnă televiziune de calitate pentru întreaga familie. Ştiri echilibrate, programe de divertisment pentru toate gusturile, cele mai bune seriale şi filme ale momentului şi o echipă pe care o simţi aproape de fiecare dată când ai nevoie de ajutor.", "channel", "https://romanialibera.ro/wp-content/uploads/2022/01/tvr-scaled.jpg"]
],


"WorldNewsList" :    [ 
            [ "[COLOR goldenrod]Fox News[/COLOR]  [US]", "UCXIJgqnII2ZOINSWNOGFThA", "https://encrypted-tbn0.gstatic.com/images?q=tbn%3AANd9GcTSterQopokt37dESk7e7fsukVfvm_SHyKfSA&usqp=CAU.png", "FOX News Channel (FNC) is a 24-hour all-encompassing news service dedicated to delivering breaking news as well as political and business news. A top cable network in both total viewers and Adults 25-54, FNC has been the most-watched news channel in the country for almost two decades and according to Public Policy Polling is the most trusted television news source in the country. FNC is available in more than 89 million homes and dominates the cable news landscape, routinely notching 12 of the top 15 programs in the genre.", "channel", "https://a57.foxnews.com/static.foxnews.com/foxnews.com/content/uploads/2022/02/1024/512/Fox-News-daytime-Line-up-ratings.jpg"],
            ["[COLOR goldenrod]CNN[/COLOR]  [US]", "UCupvZG-5ko_eiXAupbDfxWw", "https://pbs.twimg.com/profile_images/1605686372421062657/wxirbves_400x400.jpg", "CNN is the world leader in news and information and seeks to inform, engage and empower the world. Staffed 24 hours, seven days a week by a dedicated team in CNN bureaus around the world, CNN delivers news from almost 4,000 journalists in every corner of the globe.", "channel", "https://www.hollywoodreporter.com/wp-content/uploads/2024/02/GettyImages-1442284708-3.jpg"],
            ["[COLOR goldenrod]MSNBC[/COLOR]  [US]", "UCaXkIU1QidjPwiAYu6GcHjg", "https://yt3.googleusercontent.com/ytc/AKedOLQhAREYb8vSKigSn2-v33vVpvPAcSp1XXzYbup2XJM=s88-c-k-c0x00ffffff-no-rj", "The official MSNBC YouTube Channel. MSNBC  is the premier destination for in-depth analysis of daily headlines, insightful political commentary and informed perspectives. Reaching more than 95 million households worldwide, MSNBC  offers a full schedule of live news coverage, political opinions and award-winning documentary programming -- 24 hours a day, 7 days a week.", "channel", "https://www.clickspringdesign.com/wp-content/uploads/2022/07/MSNBC-3A_0011.jpg"],
            ["[COLOR goldenrod]NBC News[/COLOR]  [US]", "UCeY0bbntWzzVIaj2z3QigXg", "https://logoeps.com/wp-content/uploads/2012/04/nbc-logo-vector-01.png", "NBC News Digital is a collection of innovative and powerful news brands that deliver compelling, diverse and engaging news stories. NBC News Digital features NBCNews.com, MSNBC.com, TODAY.com, Nightly News, Meet the Press, Dateline, and the existing apps and digital extensions of these respective properties.  We deliver the best in breaking news, live video coverage, original journalism and segments from your favorite NBC News Shows.", "channel", "https://media12.s-nbcnews.com/i/mpx/2704722219/2024_05/nn_netcast_240520-avausd.jpg"],
            ["[COLOR goldenrod]ABC News[/COLOR]  [US]", "UCBi2mrWuNuyYy4gbM6fU18Q", "https://childrenshealthwatch.org/wp-content/uploads/ABC-NEws.jpg", "ABC News is your daily source for breaking national and world news, exclusive interviews and 24/7 live streaming coverage that will help you stay up to date on the events shaping our world. https://abcnews.go.com", "channel", "https://s.abcnews.com/images/Live/NEWS_LIVE_LOGO_hpMain_16x9_1600.jpg"],
            ["[COLOR goldenrod]PBS NewsHour[/COLOR]  [US]", "UC6ZFN9Tx6xh-skXCuRHCDpQ", "https://i.ibb.co/rvCSkb4/PBS-News-H.png", "PBS NewsHour is one of the most trusted news programs in television and online.", "channel", "https://www.ucf.edu/wp-content/blogs.dir/20/files/2011/12/News_Hour_final-copy.jpg"],

            ["[COLOR goldenrod]OAN[/COLOR]  [US]", "UCNbIDJNNgaRrXOD7VllIMRQ", "https://images-na.ssl-images-amazon.com/images/I/71RaD2tNr2L.png", "One America News is a national TV news network. OAN is a credible source for national and international headlines. An independent, cutting edge platform for political discussions. Watch all of our content on our streaming platform OAN Live, on Vidgo, on GCI and on KlowdTV.", "channel", "https://variety.com/wp-content/uploads/2020/11/OANN-One-America-News-Network.png"],
            ["[COLOR goldenrod]NewsMax[/COLOR]  [US]", "UCx6h-dWzJ5NpAlja1YsApdg", "https://yt3.googleusercontent.com/xjxmYwEWSbA78QQKTTtAOlbiGWqT3F1yGl1WoGDy0YXruTrtde9LtrJ_zqo9MPvWVJ8REjD_Qg=s900-c-k-c0x00ffffff-no-rj", "NEWSMAX, America’s fastest-growing cable news channel in more than 100 million homes, gives you the latest breaking news from Washington, New York, Hollywood and from capitals around the world, with top-rated shows featuring Rob Schmitt, Greg Kelly, Greta Van Susteren, Eric Bolling, Chris Salcedo, Carl Higbie and more.", "channel", "https://i.ytimg.com/vi/PjNNZmXIENU/hq720_live.jpg"],

            ["[COLOR goldenrod]France 24[/COLOR]  [FR]", "UCQfwfsi5VrQ8yKZ-UWmAEFg", "https://upload.wikimedia.org/wikipedia/commons/thumb/8/8a/France24.png/509px-France24.png", "Official FRANCE 24's YouTube channel, international news 24/7. Watch international video news from around the world !", "channel", "https://s.france24.com/media/display/99f8a93a-e6c1-11ee-9116-005056bf30b7/w:1280/p:16x9/img-default-F24.jpg"],
            ["[COLOR goldenrod]DW News[/COLOR]  [DE]", "UCknLrEdhRCp1aegoMqRaCZg", "https://yt3.googleusercontent.com/ytc/AIdro_my-wkI-EixtX3Qej_4pEo8tn13DB1aI6elK7Q4yyZZd4pl=s900-c-k-c0x00ffffff-no-rj", "Journalism that’s Made for Minds. Follow us for global news and analysis from the heart of Europe. DW News delivers the world's breaking news while going deep beneath the surface of what's going on. Correspondents on the ground and in the studio provide their detailed analysis and insights on issues that affect our viewers.", "channel", "https://static.dw.com/image/47222913_6.jpg"],
            ["[COLOR goldenrod]TRT World[/COLOR]  [TR]", "UC7fWeaHhqgM4Ry-RMpM2YYw", "https://yt3.googleusercontent.com/ytc/AIdro_lyQp8wXS6hhiPoHXKeqDeTyYTCUG6cXfEyzhK8_hq9ZHg=s900-c-k-c0x00ffffff-no-rj", "At TRT World we're building a global community focused around change. We’re looking beyond the headlines to drive meaningful conversations that empower. We want to connect people across the globe to issues that matter. We explore the reality behind the hashtags and the people behind the statistics. We will seek to unpack the issues behind each story.", "channel", "https://s.wsj.net/public/resources/images/BN-PJ118_TURKTV_J_20160811155616.jpg"],
            ["[COLOR goldenrod]Al Jazeera[/COLOR]  [QA]", "UCNye-wNBqNL5ZzHSJj3l8Bg", "https://m.media-amazon.com/images/I/31TqBcQUlcL.png", "#AlJazeeraEnglish, we focus on people and events that affect people's lives. We bring topics to light that often go under-reported, listening to all sides of the story and giving a 'voice to the voiceless. Reaching more than 282 million households in over 140 countries across the globe, our viewers trust #AlJazeeraEnglish to keep them informed, inspired, and entertained.", "channel", "https://www.newscaststudio.com/wp-content/gallery/al-jazeera-studio-5-set-2/Al-Jazeera-Arabic_Studio-5_Set-2_2_12.jpg"],
            ["[COLOR goldenrod]Reuters[/COLOR]  [UK]", "UChqUTb7kYRX8-EiaN3XFrSQ", "https://cdn.theorg.com/40222450-8ce4-455a-9829-6776179c5203_medium.jpg", "Reuters brings you the latest breaking news, business and finance video from around the world. Since our founding in 1851, we have been known globally for unparalleled accuracy and impartiality.", "channel", "https://cloudfront-us-east-2.images.arcpublishing.com/reuters/TDM2WP7ZJNMIRGGVQ4VEDJY2WU.jpg"],
            ["[COLOR goldenrod]Sky News[/COLOR]  [UK]", "UCoMdktPbSTixAyNGwb-UYkQ", "https://archive.org/download/sky-news-logo//sky-news-logo.jpg", "The full story, first. Free, wherever you get your news.", "channel", "https://e3.365dm.com/23/02/1600x900/skynews-logo-livestream_6066509.jpg"],
            ["[COLOR goldenrod]BBC News[/COLOR]  [UK]", "UC16niRr50-MSBwiO3YDb3RA", "https://yt3.googleusercontent.com/v4JamQ9B-PUiJHjmZQs9UwTaoLQW8vijJMMpV5QvA2wHQ6iwWM8Q1s6O4jgTl0dtDigVWAi7SA=s900-c-k-c0x00ffffff-no-rj", "Interested in global news with an impartial perspective? Want to see behind-the-scenes footage directly from the front-line? Our YouTube channel has all this and more, bringing you specially selected clips from the world's most trusted news source.", "channel", "https://ichef.bbci.co.uk/images/ic/1200x675/p0g6j1tq.jpg"],
            ["[COLOR goldenrod]SKY NEWS[/COLOR]  [AU]", "UCO0akufu9MOzyz3nvGIXAAw", "https://yt3.googleusercontent.com/Jt1pqs1ELrNgWh7r4b3NHazkg0gEQOdeFM7qrhgZtq5fNGk-zd9qg81MTt3n4tjBBsw1lDW=s900-c-k-c0x00ffffff-no-rj", "The best award-winning journalists with unique and exclusive insights. Fearless opinions from the big names who are passionate about the country we live in.", "channel", "https://ichef.bbci.co.uk/ace/standard/976/cpsprodpb/71BF/production/_119891192_sky_news_alamy.jpg"],
            ["[COLOR goldenrod]Euronews[/COLOR]  [EU]", "UCSrZ3UV4jOidv8ppoVuvW9Q", "https://yt3.googleusercontent.com/8MyE7rxMBfLZOpYkJVJFm1C8I9jxbceBbOJS9OhrepZMVGxGV-OEJU-UdLOew_qR_l-knETWeu4=s900-c-k-c0x00ffffff-no-rj", "Around the clock, our team of 500 journalists of more than 30 different nationalities gathers news with impartial perspective, beyond the headlines content and voices from across Europe and the world. Our YouTube channel has all this and more, bringing you selected and original content from the world's most trusted news source.", "channel", "https://www.newscaststudio.com/wp-content/uploads/2016/06/euronews-logo.jpg"],

            ["[COLOR goldenrod]Forbes Breaking News[/COLOR]   ***Independent Media***", "UUg40OxZ1GYh3u3jBntB6DLg", "https://yt3.googleusercontent.com/ytc/AIdro_mQDv3YYtwrEY-oFDf_zzH-iLoSFxmjDh2GhAG5CFyMNfY=s900-c-k-c0x00ffffff-no-rj", "ForbesBreakingNews", "playlist", "https://media.licdn.com/dms/image/v2/D4E22AQEEpHZNnCy1Xg/feedshare-shrink_800/feedshare-shrink_800/0/1706818003179?e=2147483647&v=beta&t=Wx_d112KwVPFxmrBKWH2JxyAHIkEYmxprYxcdqjz2s0"],
            ["[COLOR goldenrod]The Daily Show[/COLOR]   ***Independent Media***", "UCwWhs_6x42TyRM4Wstoq8HA", "https://yt3.googleusercontent.com/clBZ7D-wYk_ysfU_X0U2GAN3lAxkP5drwADfpuqvSrbPzkcemCXx9XQV8XEXqjSK3uMYiReJPQ=s900-c-k-c0x00ffffff-no-rj", "on Stewart and The Best F**king News Team host The Daily Show, an Emmy and Peabody Award-winning program analyzing the biggest stories in news, politics, and culture through a sharp, satirical lens.", "channel", "https://m.media-amazon.com/images/S/pv-target-images/eebe5e46e0b2d671f4dbe9249fd229add2270acdebc3bb8f10023296afbc7331.jpg"],



            ["[COLOR goldenrod]Democracy Now![/COLOR]   ***Independent Media***", "UCzuqE7-t13O4NIDYJfakrhw", "https://yt3.googleusercontent.com/ytc/AIdro_k13evyGyej3TcaRYOEUzR4OSYdCEHnHeQipbK13evyGyej3TcaRYOEUzR4OSYdCEHnHeQipbK1lJZOs5o=s900-c-k-c0x00ffffff-no-rj", "Democracy Now! is an independent, global weekday news hour anchored by award-winning journalists Amy Goodman and Juan González. The show is broadcast on nearly 1,400 TV, radio and Internet stations. Stream the show live Monday through Friday at 8AM ET at http://www.democracynow.org.", "channel", "https://lh3.googleusercontent.com/Z8cJpewg8uCqALhsieR3zLTDhDEhVy6gzB5IXeYFhaZWbdaerLemqwZ-JrQph6PfDvMjI12Uh8tpDg=w1440-ns-nd-rj"],
            ["[COLOR goldenrod]Tucker Carlson Network[/COLOR]   ***Independent Media***", "UCGttrUON87gWfU6dMWm1fcA", "https://pbs.twimg.com/profile_images/1734226736093528064/qpPX7owf_400x400.jpg", "This is the official Tucker Carlson YouTube page. Watch exclusive content on TuckerCarlson.com.", "channel", "https://imageio.forbes.com/specials-images/imageserve/64e66c4cb71f30fb3d4af6bb/2022-FOX-Nation-Patriot-Awards/0x0.jpg"],
            ["[COLOR goldenrod]Megyn Kelly[/COLOR]   ***Independent Media***", "UCzJXNzqz6VMHSNInQt_7q6w", "https://images.squarespace-cdn.com/content/v1/5f57d5d5c83f9e7bb09b6e66/1601416075947-EM6Q9331PAVCRZ6LFC87/MKSHOW_LOGO_SQ_1400X1400.jpg", "The Megyn Kelly Show is your home for open, honest and provocative conversations with the most interesting and important political, legal and cultural figures today. No BS. No agenda. And no fear.", "channel", "https://i.ytimg.com/vi/xAXsYIvG2lE/hq720.jpg"],
            ["[COLOR goldenrod]Kim Iversen[/COLOR]   ***Independent Media***", "UCoJTOwZxbvq8Al8Qat2zgTA", "https://podcast-api-images.s3.amazonaws.com/corona/show/668280/logo.jpeg", "Independent analysis of today's politics. Foreign Policy, Pandemic, Elections and More. I don't fall in line when the line leads to Bull. ", "channel", "https://c104216-ucdn.mp.lura.live/expiretime=2082787200/2af0f21d30c70eac135db526225faad1d5d664b45145382ed59b2a64129e6924/iupl_lin/9CF/B73/9CFB732300C55D22796069C11D935401.jpg"],

            ["[COLOR goldenrod]APT[/COLOR]   ***Independent Media***", "UCpLEtz3H0jSfEneSdf1YKnw", "https://yt3.googleusercontent.com/jGrZVILfltTMc_WGdU0LaCgWkdz6lykWsMyP8A265ubDpfk8mvahhFxW6DGTbjMw9oqxTYgTjQ=s900-c-k-c0x00ffffff-no-rj", "Accurate, Powerful, Timely international news coverage. We deliver in-depth reports, breaking news, and insightful analysis on global events, from politics and conflicts to culture and climate. Our mission is to provide unbiased, fact-driven stories that empower viewers to understand the world.", "channel", "https://images.news18.com/ibnlive/uploads/2025/09/World-News-AI-Blog-2025-07-71d087050940689d8621058405992e8c-16x9.jpg"],

            ["[COLOR goldenrod]Breaking Points[/COLOR]   ***Independent Media***", "UCDRIjKy6eZOvKtOELtTdeUA", "https://supercast-storage-assets.b-cdn.net/channel/1697/artwork/medium-4000fd7e678b5690d751c645b07576c1.jpg", "Breaking Points with Krystal and Saagar is a fearless anti-establishment Youtube show and podcast.", "channel", "https://pbs.twimg.com/ext_tw_video_thumb/1531321302698676230/pu/img/YIa8-JZdN79jyF9W.jpg"],
            ["[COLOR goldenrod]The Hill[/COLOR]   ***Independent Media***", "UCPWXiRWZ29zrxPFIQT7eHSA", "https://yt3.googleusercontent.com/OVrZq3dq-TKbW_zFYkE9snaGBVmKZu4PnXmDgV4G6_DCDyPkGefp0dMEQK8Krdr4kk8e_Pqe3kA=s900-c-k-c0x00ffffff-no-rj", "The Hill is the premier source for policy and political news. Tune into The Hill's news commentary show, *Rising*, on weekdays, starting at 11:00am ET. Mon-Thurs: Briahna Joy Gray & Robby Soave, Friday: Jessica Burbank & Amber Athey ", "channel", "https://m104216-ucdn.mp.lura.live/iupl_lin/A36/92F/A3692F690973160C93F2797C18A84B6F.jpg"],
            ["[COLOR goldenrod]Judge Napolitano[/COLOR]   ***Independent Media***", "UCDkEYb-TXJVWLvOokshtlsw", "https://yt3.googleusercontent.com/K7XNEgK1VRHxhtM1Mu-lhVoE4gnfPemt0EH8CoOYcdZ9ZMpiVXvVcnkJz9n_RnOsUjMZ9XxoDw=s900-c-k-c0x00ffffff-no-rj", "Hard hitting legal/political news from a man who knows and respects the Constitution and the importance of defending individual freedoms. Judge Andrew P. Napolitano.", "channel", "https://i.ytimg.com/vi/73FG1nZhtXI/maxresdefault.jpg"],
            ["[COLOR goldenrod]The Duran[/COLOR]   ***Independent Media***", "UCdeMVChrumySxV9N1w0Au-w", "https://img.rephonic.com/artwork/the-duran-podcast.jpg", "#1 Geopolitics podcast in the world. New shows drop daily.", "channel", "https://i.ytimg.com/vi/VLaxRmIxWso/hq720.jpg"],
            ["[COLOR goldenrod]Alex Christoforou[/COLOR]   ***Independent Media***", "UULF6cF_2V1vNKx-nFdGd8cOcA", "https://yt3.googleusercontent.com/ytc/AIdro_mEeY1s8ADjl4261qSezvaKMMvex9Olm4zovQq2_A=s900-c-k-c0x00ffffff-no-rj", "Cypriot journalist. He writes and produces video interviews for The Duran, which are published on Odysee, Rumble and YouTube.", "playlist", "https://archive.org/download/odysee_-_alex_christoforou_202303/20230301%20-%2092b5bc3a87be27b73a5bd4cd4d6f78dd4e799dd2%20-%20Greece%20train%20tragedy.%20TikTok%20ban.%20More%20units%20into%20Bakhmut.%20MSNBC%20journalist%20on%20Peacemaker%20list.%20U%E2%A7%B81/20230301%20-%2092b5bc3a87be27b73a5bd4cd4d6f78dd4e799dd2%20-%20Greece%20train%20tragedy.%20TikTok%20ban.%20More%20units%20into%20Bakhmut.%20MSNBC%20journalist%20on%20Peacemaker%20list.%20U%E2%A7%B81.jpg"],
            ["[COLOR goldenrod]Alexander Mercouris[/COLOR]   ***Independent Media***", "UULFwGpHa6rMLjSSCBlckm5khw", "https://pbs.twimg.com/profile_images/1719747557759275009/LiHVqjoA_400x400.jpg", "He is a London based analyst. He writes and produces video interviews for The Duran.", "playlist", "https://i.ytimg.com/vi/VLaxRmIxWso/hq720.jpg"],
            ["[COLOR goldenrod]Russell Brand[/COLOR]   ***Independent Media***", "UCswH8ovgUp5Bdg-0_JTYFNw", "https://yt3.googleusercontent.com/z5B1yrrc-Vs-lrgl6RZQP0n9gwfxfSgX7yHcA2mT-celq0zHbOvsIYMkrDdwvurWRDXzEYlmkA=s900-c-k-c0x00ffffff-no-rj", " Hello You Awakening Wonder. Thanks for reading this when you could be obediently consuming propaganda. We are living through a time of incredible change and opportunity. Many of the old systems are corrupted and broken and yet a New Spirit is being born among us.", "channel", "https://pbs.twimg.com/ext_tw_video_thumb/1793300392719097856/pu/img/D8j-PRhhYFON6xaG.jpg"],
            ["[COLOR goldenrod]Military Updates[/COLOR] [UA-RU War]   ***Independent Media***", "UCUnc496-PPmFZVKlYxUnToA", "https://global.unc.edu/wp-content/uploads/sites/982/2023/01/Ukraine-peace-hero-1200-x-675-e1673647426722.jpg", "This channel provides objective information about the military conflict between Ukraine and the Russian Federation. We condemn any aggression in Ukraine.", "channel", "https://images.livemint.com/img/2022/03/08/original/istockphoto-477701615-612x612_1646725249499.jpg"],
            ["[COLOR goldenrod]ShanghaiEye[/COLOR]  [CN] (EN)", "UCaxIsKnhxr6bfaJFQc67-rg", "https://yt3.ggpht.com/ytc/AKedOLTA5-gvlffRGEokmZMPoGivPBotKjqGc05H2cyGw=s88-c-k-c0x00ffffff-no-rj", "BRINGING STORIES TO LIFE, ShanghaiEye is a multi-platform media brand focusing on high-quality videos", "channel", "https://i.ytimg.com/vi/ZfIPtrY-brE/maxresdefault.jpg"]
],




"MusicList" :    [ 
            [ "[COLOR goldenrod]Cat Romantico Selection[/COLOR]",  "PLAbsUyTwxMgmLUqLVjnj1cbFDla6IGPQo", "https://www.logobee.com/recent-projects/logos/1010-l.png", "A Perfect Blend of Love and Tranquility.", "playlist", "https://i.ytimg.com/vi/a6XkDc-ZV8g/maxresdefault.jpg"],
            [ "[COLOR goldenrod]RadioUtopia[/COLOR]", "UC8bX_BM3oc-IcIy0zPRH2QA", "https://yt3.googleusercontent.com/_wBKYaFGSXbvIoG1WIrkuqGCP9qFZx63d1FoQdLTl3I5UFWT8aijTcrp_4jJXvKDuCvo5X52=s900-c-k-c0x00ffffff-no-rj", "Video Creations", "channel", "https://i.ytimg.com/vi/xW34yNLCz00/hq720.jpg?sqp=-oaymwEXCK4FEIIDSFryq4qpAwkIARUAAIhCGAE=&rs=AOn4CLAPsLn7XOTLvEo4R9LedAfehK8IyQ"],
            [ "[COLOR goldenrod]Relaxing Jazz Piano[/COLOR]",  "UC84t1K5ri-7u9bFCaUKTXDA", "https://yt3.googleusercontent.com/hU8Ora-2LvI9zedx0K-ducdU4o8kW4eZfzvi6x5VR_B_qJJ08_1j906klQjFF2iZQBQ5FA5t-Q=s900-c-k-c0x00ffffff-no-rj", "I am an interior architect who create Coffee Shop scenes with Jazz music.", "channel", "https://i.ytimg.com/vi/MYPVQccHhAQ/maxresdefault.jpg"],
            [ "[COLOR goldenrod]Relax Jazz Cafe[/COLOR]",  "UCZR3-lM6Z-n5_UGHlwx_Rpw", "https://yt3.googleusercontent.com/ch7-gru5HaQqKEkGHQwCP4hmVmjD08v6u6Zl-S5lBJiZKskbpbwBIb1jTgm4xJWS4gxt5NMieA=s160-c-k-c0x00ffffff-no-rj", "All music in this video and on this channel is original music by Relax Jazz Cafe.", "channel", "https://i.ytimg.com/vi/RIjGi5NgWuo/hq720.jpg?v=687a968b&sqp=-oaymwEhCK4FEIIDSFryq4qpAxMIARUAAAAAGAElAADIQj0AgKJD&rs=AOn4CLDcDIJi2BJMdyaIMr2npI18Op-pYQ"],

            [ "[COLOR goldenrod]Cat Music[/COLOR]",  "UCCTR5nIFvWBW9MeGEGPNG4g", "https://yt3.googleusercontent.com/5Q8qo3tDyqrUcHssbeZ2qhKzpHgfwqBrOXgNMyV7N2B1ox6GNqvL0bmCOUcoci3S2g4SbLag41E=s900-c-k-c0x00ffffff-no-rj", "Cat Music is the most important label in Romania, with over 9,000 songs published. The music label has the strongest YouTube channel in Central, Eastern Europe and Russia, with over 7 million subscribers and over 7 billion views. With dozens of artists signed and more than 50 music channels in the Multichannel Cat Music network.", "channel", "https://i.ytimg.com/vi/DGmrfMEUy-0/hqdefault.jpg"],
            [ "[COLOR goldenrod]HaHaHa Production[/COLOR]",  "UCZFZH5uzK8RVRE1lrP7L2yQ", "https://yt3.googleusercontent.com/QT-vd2801wqgoc_nJ4ckC4lTcsg6KVFu99CU0jOgERlaMMwhnMzNfz-EXWDHD5mDD6n-TqC=s900-c-k-c0x00ffffff-no-rj", "In a few years, HaHaHa Production became one of the most influential independent labels in Romania and succeeded to own 25% of the music in Top 100 most popular Romanian songs (most of them ranking Top 50). Nowadays, the label has become also an important brand on the international music market and covers the entire music production process, from creative ideas to recording, mixing, post-production, and mastering", "channel", "https://i.ytimg.com/vi/nb7gRAPzcjI/maxresdefault.jpg"],
            [ "[COLOR goldenrod]Teatru Radiofonic[/COLOR]",  "UCi-keQw95kZ_BFMdYK6y8dA", "https://yt3.googleusercontent.com/o1TwVb7ZfMHik3jWKaynAYKxp-v9CWbM67NqDYuaADUBLq40VZOUPv9vEaxBUTepTlRVNKnd=s900-c-k-c0x00ffffff-no-rj", "Canalul teatrului radiofonic. Aici vom pune cele mai frumoase piese de teatru.", "channel", "https://editiadedimineata.ro/wp-content/uploads/2022/10/teatru-radiofonic.jpg"],
            [ "Muzica de petrecere",  "muzica de petrecere veche", "RobertaGym.jpg", "Muzica de petrecere", "search", ""],
            [ "Manele", "manele in trend", "RobertaGym.jpg", "Muzica de pe Youtube", "search", ""]
],




"SportList" :   [
            [ "[COLOR goldenrod]FOX Soccer[/COLOR]", "UCooTLkxcpnTNx6vfOovfBFA", "https://yt3.googleusercontent.com/aveASTfRd2GwIdpThrMH4_3KPakK0i7V8LID2hKrg5Xw7qNZecSFvZdJIsDYTRpiC8yfrAQV=s900-c-k-c0x00ffffff-no-rj", "Official US home for the biggest international tournaments the world has to offer, including 2022 FIFA Men's World Cup, the 2023 FIFA Women’s World Cup, the CONCACAF Gold Cup, Copa America.  [COLOR red][B]EURO2024[/B][/COLOR]", "channel", "https://foxsports-wordpress-www-prsupports-prod.s3.amazonaws.com/uploads/sites/2/2022/06/FOX_SOCCER.png"],
            [ "[COLOR goldenrod]FIFA[/COLOR]", "UCpcTrCXblq78GZrTUTLWeBw", "https://yt3.googleusercontent.com/8btjbwmMijz7TARR4uRFDFaZOFbyfcrxiUe3VOTaMdf656D5aTdyosLKcU7-RpCBSfX-cHiK=s900-c-k-c0x00ffffff-no-rj", "FIFA on YouTube brings you the best in football videos, including FIFA World Cup and FIFA Women's World Cup highlights, full matches, classic stories, exclusive interviews, famous goals, documentaries and behind the scenes coverage of all FIFA tournaments and events", "channel", "https://lh3.googleusercontent.com/yYJWhuaAKknZyHjlu5fT9NMnb-mlsQJDQFFYL4mCm40wP-D-4E5znDrMwX2DMOIVeWtPzMPNjJHN=w1440-ns-nd-rj"],
            [ "[COLOR goldenrod]Major League Soccer[/COLOR]", "UCSZbXT5TLLW_i-5W8FZpFsg", "https://upload.wikimedia.org/wikipedia/commons/thumb/7/76/MLS_crest_logo_RGB_gradient.svg/800px-MLS_crest_logo_RGB_gradient.svg.png", "MLS features stars from around the world, including one from Argentina. We score bangers only. Watch them here.", "channel", "https://images.mlssoccer.com/image/private/t_landscape_tablet/prd-league/yvf4uwhbw3rg8rpcitrj.png"],
            [ "[COLOR goldenrod]FC Barcelona[/COLOR]", "UC14UlmYlSNiQCBe9Eookf_A", "https://yt3.googleusercontent.com/obnnFvh_OSUvbvEiHR8bW1W5z7fxmGBh3AWWXCoeH_iyB7gVjqA20NK4f1RWZgGaFzva7M_Wb3Q=s900-c-k-c0x00ffffff-no-rj", " Welcome to FC Barcelona official YouTube channel! Highlights, challenges, interviews, vlogs, live shows and much more.", "channel", "https://i.ytimg.com/vi/EC269OT2c1s/maxresdefault.jpg"],
            [ "[COLOR goldenrod]CBS Sports Golazo[/COLOR]", "UCET00YnetHT7tOpu12v8jxg", "https://yt3.googleusercontent.com/YGHhK_6Q5Lll7Y7K9o1BKx8Ugb4OU21hyTziSRIfUxMj3GMcCrp9fIN6HQ3418vwuaP2f_SERIY=s900-c-k-c0x00ffffff-no-rj", "", "channel", "https://i.ytimg.com/vi/B6KnTleUZYM/sddefault.jpg"],
            [ "[COLOR goldenrod]TUDN USA[/COLOR]", "UCSo19KhHogXxu3sFsOpqrcQ", "https://yt3.googleusercontent.com/OuKve41J-tBfaAWWfruNhofwhO3xCqMwwCHDSGWfPJasAeuLh7UoZweSMU57BsrHcnMumUbVEw=s900-c-k-c0x00ffffff-no-rj", "TUDN USA te ofrece la cobertura más completa del mundo deportivo con lo mejor del fútbol mexicano, de Estados Unidos y del mundo, boxeo, UFC, las grandes personalidades del deporte y mucho más.", "channel", "https://pbs.twimg.com/amplify_video_thumb/1651031535578152962/img/BnkjdS2MfSSkSucX.jpg"],
            [ "[COLOR goldenrod]NBA[/COLOR]", "UCWJ2lWNubArHWmf3FIHbfcQ", "https://www.sportstravelmagazine.com/wp-content/uploads/2016/07/NBA-logo.png", "The NBA is the premier professional basketball league in the United States and Canada. The league is truly global, with games and programming in 215 countries and territories in 47 languages. The NBA consists of 30 teams.", "channel", "https://i0.wp.com/michael-weinstein.com/wp-content/uploads/2023/07/NBALogoRedesigns-All.png"]
],


"DocuList" :   [
            [ "[COLOR goldenrod]Biography Channel[/COLOR]", "UCiCPv2sV_D3FqMRzzUFA2Fg", "https://yt3.googleusercontent.com/ytc/AIdro_moqRjxI5MXz1L56vGkuLb4QuiK3zZ-VyJRWb3Xwwh6Us=s900-c-k-c0x00ffffff-no-rj", "Biography highlights newsworthy personalities and events with compelling and surprising points-of-view, telling the true stories from some of the most accomplished non-fiction storytellers of our time.", "channel", "https://m.media-amazon.com/images/S/pv-target-images/cfb5266026fe27d4282f66393118f6321b1968fd9334898369665270b23edc8d.jpg"], 
            [ "[COLOR goldenrod]OverSimplified[/COLOR]", "UCNIuvl7V8zACPpTmmNIqP2A", "https://yt3.googleusercontent.com/ytc/AIdro_nbHJmmJigQKWgdRGLBfVXYqRAsc1QMp3SfVEAwjMp9o-o=s900-c-k-c0x00ffffff-no-rj", "Explaining things in an OverSimplified way", "channel", "https://d3dbooq5a0yc71.cloudfront.net/2020/09/Asset_1_2048x2048.png"],
            [ "[COLOR goldenrod]Real Responders[/COLOR]", "UCbMJuChLfqeXCgEmmciKZxA", "https://yt3.googleusercontent.com/ytc/AIdro_lGjjDULMEJLVgSfsonc8KM8hpBX_VaoOerfdS6nYAgL24=s900-c-k-c0x00ffffff-no-rj", "Bringing you all the action that comes with blue lights. Crime, justice, law, and order, Real Responders is the perfect place to get your emergency rescue fix. We've got all kinds of documentary content from cops to doctors, firefighters to air rescue.", "channel", "https://i.ytimg.com/vi/zgu499flL5U/maxresdefault.jpg"],
            [ "[COLOR goldenrod]60 Minutes[/COLOR]", "UCsN32BtMd0IoByjJRNF12cw", "https://yt3.googleusercontent.com/TqABNUxcOZskunKayOizy6ge4RekSFL7cCNxGO9Ct-J8sYOthNd5Lc6m4hrfzeHQikTFCFi3pQ=s900-c-k-c0x00ffffff-no-rj", "The most successful television broadcast in history. Offering hard-hitting investigative reports, interviews, feature segments and profiles of people in the news, the broadcast began in 1968 and is still a hit, over 50 seasons later, regularly making Nielsen's Top 10.", "channel", "https://www.usatoday.com/gcdn/authoring/authoring-images/2023/09/18/USAT/70887748007-ap-23256574246290.jpg"],
            [ "[COLOR goldenrod]The FBI Files[/COLOR]", "UCwxod2w5NT4qMWfMgZivCYQ", "https://yt3.googleusercontent.com/ytc/AIdro_nZiEWsgdYUIgcD6HU60vDRuHKEsAaqizSv074ueuPeEYk=s900-c-k-c0x00ffffff-no-rj", "The FBI Files is an American docudrama that takes a look behind the scenes of the Federal Bureau of Investigation's crime laboratory. [COLOR red]FULL EPISODE every Saturday[/COLOR]", "channel", "https://pbs.twimg.com/media/CPhGjtPWwAAm5KA.png"],
            [ "[COLOR goldenrod]RealLifeLore[/COLOR]", "UCP5tjEmvPItGyLhmjdwP7Ww", "https://yt3.googleusercontent.com/ytc/AIdro_lK3FQppzWeqpXhyk8SpqvzzlrKr-pqjpRtY3PUfeF9poY=s900-c-k-c0x00ffffff-no-rj", "Answers to questions that you've never asked. Welcome to the RealLifeLore community", "channel", "https://miro.medium.com/v2/resize:fit:1080/0*aTAqV6x8AsK0v4Gr"],
            [ "[COLOR goldenrod]DW Documentary[/COLOR]", "UCW39zufHfsuGgpLviKh297Q", "https://yt3.googleusercontent.com/rgphL4c6DGPlwzkxIzE5tH0DPe1yuynH0nTdOAecCVIX5gUjJGsCwXtp9wnxjcsfqboL6C5aFg=s900-c-k-c0x00ffffff-no-rj", "DW Documentary gives you information beyond the headlines. Watch top documentaries from German broadcasters and international production companies. Meet intriguing people, travel to distant lands, get a look behind the complexities of daily life and build a deeper understanding of current affairs and global events.", "channel", "https://i.ytimg.com/vi/1MZFrJPPIQ8/maxresdefault.jpg"],
            [ "[COLOR goldenrod]DW Planet A[/COLOR]", "UCb72Gn5LXaLEcsOuPKGfQOg", "https://yt3.googleusercontent.com/rgphL4c6DGPlwzkxIzE5tH0DPe1yuynH0nTdOAecCVIX5gUjJGsCwXtp9wnxjcsfqboL6C5aFg=s900-c-k-c0x00ffffff-no-rj", "DW Documentary gives you information beyond the headlines. Watch top documentaries from German broadcasters and international production companies. Meet intriguing people, travel to distant lands, get a look behind the complexities of daily life and build a deeper understanding of current affairs and global events.", "channel", "https://i.ytimg.com/vi/ldU3NJmDeMU/hq720.jpg"],
            [ "[COLOR goldenrod]DW Food[/COLOR]", "UCb72Gn5LXaLEcsOuPKGfQOg", "https://yt3.googleusercontent.com/rgphL4c6DGPlwzkxIzE5tH0DPe1yuynH0nTdOAecCVIX5gUjJGsCwXtp9wnxjcsfqboL6C5aFg=s900-c-k-c0x00ffffff-no-rj", "DW Food gives you the perfect blend of culinary trends, DIY recipes, exciting food secrets and a look behind the scenes of Europe’s culinary culture.", "channel", "https://i.ytimg.com/vi/1NJWc1K9tjU/hq720.jpg"],
            [ "[COLOR goldenrod]DW History and Culture[/COLOR]", "UCXD5-f9urX1Foas68AL_HHQ", "https://yt3.googleusercontent.com/rgphL4c6DGPlwzkxIzE5tH0DPe1yuynH0nTdOAecCVIX5gUjJGsCwXtp9wnxjcsfqboL6C5aFg=s900-c-k-c0x00ffffff-no-rj", "DW History and Culture takes a deep dive into both the big and small questions around art and culture, bringing to life the historical moments which shape our present and future. Subscribe to DW History and Culture and dig deeper. ", "channel", "https://i.ytimg.com/vi/ltoEsUxWTsA/hq720.jpg"],
            [ "[COLOR goldenrod]BBC Select[/COLOR]", "UCMTx_OGd-g4dVvhRKVUu9aQ", "https://yt3.googleusercontent.com/fbyYzAWBSE16KhqcK3tl6Dru8LCBzgnHyr1MPzYegQHalM4pmnwIDd48e6h29T5iZ3H7sl7GLA=s900-c-k-c0x00ffffff-no-rj", "BBC Select is the home for documentaries. From history and nature to royalty and biographies, you will find a range of acclaimed shows to stream from the BBC and beyond.", "channel", "https://i.ytimg.com/vi/wa6ZnOrDbrM/maxresdefault.jpg"],
            [ "[COLOR goldenrod]HISTORY Channel[/COLOR]", "UC9MAhZQQd9egwWCxrwSIsJQ", "https://yt3.googleusercontent.com/PuK25BOIG4MnfQL68iXXMaI_AbJ1vACxdE_seCkpTeD3hftaEOhdl-i0LYBBoWelxWUZNvWi=s900-c-k-c0x00ffffff-no-rj", "The HISTORY® Channel, a division of A+E Networks, is the premier destination for historical storytelling. From best-in-class documentary events, to a signature slate of industry leading nonfiction series and premium fact-based scripted programming, The HISTORY® Channel serves as the most trustworthy source of informational entertainment in media. The HISTORY® channel has been named the #1 U.S. TV network in buzz for seven consecutive years by YouGov BrandIndex, and a top favorite TV network by Beta Research Corporation.", "channel", "https://cropper.watch.aetnd.com/cdn.watch.aetnd.com/sites/2/2020/10/historys-greatest-mysteries-s4b-2048x1152-promo-16x9-1.jpg"],
            [ "[COLOR goldenrod]Timeline - World History Documentaries[/COLOR]", "UC88lvyJe7aHZmcvzvubDFRg", "https://yt3.googleusercontent.com/ytc/AIdro_ngqGmRD-_rfV3e6Qx71XqIo2RxPSfO7Z3cRMem4kkMCLg=s900-c-k-c0x00ffffff-no-rj", "Welcome to Timeline - the home of world history. Every week we'll be bringing you one-off documentaries and series from the world's top broadcasters, including the BBC, Channel 4, Discovery and PBS.", "channel", "https://i.ytimg.com/vi/tHvxyuQQtKQ/hq720.jpg"],
            [ "[COLOR goldenrod]National Geographic[/COLOR]", "UCpVm7bg6pXKo1Pr6k5kxG9A", "https://yt3.googleusercontent.com/PpXnS_GVZeQbZgvdnj68a159gpQf6AIlocsZmJb2SDMcUMZ_JzOI-R6PYtA7omcdtJIWOIqBg=s900-c-k-c0x00ffffff-no-rj", "Welcome to the National Geographic community, where we bring our stories, images and video to the world in real-time, inviting followers along on our ongoing 135-year journey. Our yellow border is a portal to the world, showcasing all of the wonder and beauty that it has to offer. This page allows our fans to join us while promoting an enriching and supportive climate for our community.", "channel", "https://i.pinimg.com/736x/4a/d3/f4/4ad3f4c1f7731a344bb00aff827d9b72.jpg"],
            [ "[COLOR goldenrod]Free Documentary[/COLOR]", "UCijcd0GR0fkxCAZwkiuWqtXQ", "https://yt3.googleusercontent.com/xKTkbX06Be5s6Kt6Ff28SIvDp4zyhJcZEJzmqjM12eKAfUEsSz-wvMhR0rx0Q7bc2dxFdiT4PA=s900-c-k-c0x00ffffff-no-rj", "Free Documentary is dedicated to bringing high-class documentaries to you on YouTube for free with the latest camera equipment used by well-known filmmakers working for famous production studios. You will see fascinating shots from the deep seas and up in the air, capturing great stories and pictures of everything our extraordinary planet offers.", "channel", "https://i.ytimg.com/vi/qTkHD55kcaw/maxresdefault.jpg"],
            [ "[COLOR goldenrod]Free Documentary - History[/COLOR]", "UCsgPO6cNV0wBG-Og3bUZoFA", "https://yt3.googleusercontent.com/6hWDuDiU1dh0rnHVPAAeloPb2YOUoU2yNMS0wx0sNagU8SDMxP-nozVcJgCcurIgEIU87Mb1c=s900-c-k-c0x00ffffff-no-rj", "Free Documentary - History is dedicated to bringing you high-class documentaries on YouTube for free. You will see fascinating documentaries showing the past from a new perspective and explanations by renowned historians that make history come alive.", "channel", "https://i.ytimg.com/vi/1KilaQUTCPQ/hq720.jpg"],
            [ "[COLOR goldenrod]WELT Documentary[/COLOR]", "UCBAeFXaLV1ZqKqc-Uf3pKaA", "https://yt3.googleusercontent.com/OMieFw8mcvZSH6UROWUzFWgR4F-jdx7nKCre-AA23jtkSC-bFUMq_ACC3iIkl4akA334YAAQ=s900-c-k-c0x00ffffff-no-rj", "WELT Documentary gives you deep information beyond the headlines. The WELT Group is part of the german Mediahouse Axel Springer SE and our reporters, storytellers and well-known filmmakers provides  a insight-view of german engineering skills, craftsmenship, security forces and lifestile to you.", "channel", "https://i.ytimg.com/vi/pNnbcEYPPdE/maxresdefault.jpg"],
            [ "[COLOR goldenrod]I Love Docs[/COLOR]", "UCRo0IHGf-9dR83zzlUdq1OQ", "https://yt3.googleusercontent.com/ytc/AIdro_lt1dp58YcvAc8ynygExcXKZUsxcnq_aMBLAe7ZbUV75w=s900-c-k-c0x00ffffff-no-rj", "I Love Docs features hundreds of curated award winning documentaries from around the world.", "channel", "https://i.ytimg.com/vi/5TmdEgChFjA/hq720.jpg"],
            [ "[COLOR goldenrod]Real Stories[/COLOR]", "UCu4XcDBdnZkV6-5z2f16M0g", "https://yt3.googleusercontent.com/XVsObJGPeyedzNW9FNh5p1nbbxSVy9sjD5nrRnClicpVAAzIqWl0YaQY3QkIi32hOm3zccFXTQ=s900-c-k-c0x00ffffff-no-rj", "For immersive documentaries that delve into the depths of human experiences, Real Stories is your ultimate destination.", "channel", "https://i.ytimg.com/vi/08xP6a888cI/hq720.jpg"],
            [ "[COLOR goldenrod]FRONTLINE PBS[/COLOR]", "UC3ScyryU9Oy9Wse3a8OAmYQ", "https://yt3.googleusercontent.com/ytc/AIdro_lCJYg4RvwOCx-s2Luyy1PP1yfGqV7bqsHXj1B21RIwPkI=s900-c-k-c0x00ffffff-no-rj", "FRONTLINE is investigative journalism that questions, explains and changes our world.", "channel", "https://i.ytimg.com/vi/K0UEY1PVRVY/hq720.jpg"]
],


"MovieList" :   [
            ["[COLOR goldenrod]SparkTV: Light & Love[/COLOR]", "PLMcPBANe-Un7MlkSyLSCO7nvX4kvp4Hrg", "https://yt3.googleusercontent.com/9tnKI0IPFO4s6pNDzbE6v_kuNLJaGhGkEhyzHY2Zz36iNlu9pGhOvJNZCp5dmnWRxRinSB-Ssg=s900-c-k-c0x00ffffff-no-rj", "SparkTV", "playlist", "https://i.ytimg.com/vi/wG8C6GCEGvg/hq720.jpg?sqp=-oaymwEhCK4FEIIDSFryq4qpAxMIARUAAAAAGAElAADIQj0AgKJD&rs=AOn4CLAxpJ3Urm9zReQDwCxEWmtG6ykEJw"],
            [ "[COLOR goldenrod]Romance Movie Central[/COLOR]", "UC_hYEii6T191kKGx-4YljGQ", "https://yt3.googleusercontent.com/XqFbPY9IMvhtekiErKf7vl5dut7QM6DZQ9Y4zv2fu7_8ez8X5x3KhKau33LMl2CLf_DpXHnkAw=s900-c-k-c0x00ffffff-no-rj", "Are you a hopeless romantic? Romance Movie Central is your one-stop shop for love, laughter, and a whole lot of heart.", "channel", "https://i.ytimg.com/vi/9IcNokU6Y7Q/maxresdefault.jpg"],
            [ "[COLOR goldenrod]Heartfelt Movies[/COLOR]", "UCnhMhgCgChraM1VEPBkvRKg", "https://yt3.googleusercontent.com/r2pdVo3TU7Uyo1OLU68kLkV8RBfD3KlWdSVt_ZDbunagj8mnEsrbA-sEo7UwZYbWuTWC1CNoXg=s900-c-k-c0x00ffffff-no-rj", "Heartfelt Movies is YouTube's home for premium movies that'll make you laugh, make you cry, and most importantly, keep you entertained! Subscribe for your comfort movie fix!", "channel", "https://i.ytimg.com/vi/-fkl6WYvnSA/hq720.jpg?sqp=-oaymwEXCK4FEIIDSFryq4qpAwkIARUAAIhCGAE=&rs=AOn4CLCeRmmbtcxiThmHqF3fjWNyJ9xlgQ"],
            [ "[COLOR goldenrod]Romance Channel Movies[/COLOR]", "UCcdihRgVRhuId2D5byp8YsQ", "https://yt3.googleusercontent.com/nipLOANRHOSqjeM_RuMiO5E--KxZvfPWI6qM63ZJ-k-yRq1_PaOL1gaCgJ5qqopOH9Z38cSjNg=s900-c-k-c0x00ffffff-no-rj", "Your go-to destination for a diverse collection of love stories. From heart-racing first crushes and forbidden romances to inspiring tales of resilience, friendship, and second chances, we celebrate love in all its forms.", "channel", "https://i.ytimg.com/vi/OkNuvwXh2PM/hq720.jpg?sqp=-oaymwEhCK4FEIIDSFryq4qpAxMIARUAAAAAGAElAADIQj0AgKJD&rs=AOn4CLA-S7-GznCWMgjxx0TsAdbo2Gwppg"],
           [ "[COLOR goldenrod]Movie Surf[/COLOR]", "UCc_4jvYRZ9vzj3_oSSCe6LQ", "https://yt3.googleusercontent.com/QrQzxC3nsw0nClETuRBEn903kkJMrJgaLr6mmG4806NqvxIUJEazDTRvWpDpvOZIJQOxppq3dQ=s900-c-k-c0x00ffffff-no-rj", "Movie Surf - English | Romantic and Comedy Movies in English!", "channel", "https://i.ytimg.com/vi/IjTrxu-4JpY/hq720.jpg?sqp=-oaymwEhCK4FEIIDSFryq4qpAxMIARUAAAAAGAElAADIQj0AgKJD&rs=AOn4CLDBEB04kI5FnXhirXER730pkLisWg"],
           [ "[COLOR goldenrod]Kinopower[/COLOR]", "UCTfOoI30RSVYaTnuCZY_Esg", "https://yt3.googleusercontent.com/XulbWE_8LpmL7Ez9xPC46kYqR6JsTsHPwl3rtoys9P8koL1X5fHCU8zD7ClfPOuJk3iPKR7pKw=s900-c-k-c0x00ffffff-no-rj", "KINOPOWER is an incredible YouTube channel where we strive to bring you the most exciting cinematic experiences across a wide range of genres. Whatever your mood and preferences, we have something special for every viewer.", "channel", "https://i.ytimg.com/vi/-IP0vqtEKEc/maxresdefault.jpg"]
]
}

def list_main_menu():
    """Display the main menu."""
    # Place Favorites first if enabled
    show_fav_first = addon.getSetting('show_favorites_first') == 'true'
    # Search menu
    search_url = build_url({'action': 'search'})
    search_item = xbmcgui.ListItem(label='Căutare')
    search_item.setArt({'thumb': os.path.join(addon_path, 'lib', 'media', 'search.png'), 
                       'icon': os.path.join(addon_path, 'lib', 'media', 'search.png'),
                       'fanart': os.path.join(addon_path, 'resources', 'fanart.jpg'),
                       'poster': os.path.join(addon_path, 'lib', 'media', 'search.png')})
    xbmcplugin.addDirectoryItem(handle=HANDLE, url=search_url, listitem=search_item, isFolder=True)

    # Favorites menu
    favorites_url = build_url({'action': 'list_favorites'})
    favorites_item = xbmcgui.ListItem(label='Favorite')
    favorites_item.setArt({'thumb': os.path.join(addon_path, 'lib', 'media', 'bookmarks.png'), 
                          'icon': os.path.join(addon_path, 'lib', 'media', 'bookmarks.png'),
                          'fanart': os.path.join(addon_path, 'resources', 'fanart.jpg'),
                          'poster': os.path.join(addon_path, 'lib', 'media', 'bookmarks.png')})
    if show_fav_first:
        xbmcplugin.addDirectoryItem(handle=HANDLE, url=favorites_url, listitem=favorites_item, isFolder=True)

    # Trending Romania menu
    trending_url = build_url({'action': 'list_trending'})
    trending_item = xbmcgui.ListItem(label='Trending Romania')
    trending_item.setArt({'thumb': os.path.join(addon_path, 'lib', 'media', 'trending.png'), 
                         'icon': os.path.join(addon_path, 'lib', 'media', 'trending.png'),
                         'fanart': os.path.join(addon_path, 'resources', 'fanart.jpg'),
                         'poster': os.path.join(addon_path, 'lib', 'media', 'trending.png')})
    xbmcplugin.addDirectoryItem(handle=HANDLE, url=trending_url, listitem=trending_item, isFolder=True)

    # Live Romania menu
    live_url = build_url({'action': 'search_live', 'query': 'live romania', 'event_type': 'live'})
    live_item = xbmcgui.ListItem(label='Live Romania')
    live_item.setArt({'thumb': os.path.join(addon_path, 'lib', 'media', 'live.png'), 
                     'icon': os.path.join(addon_path, 'lib', 'media', 'live.png'),
                     'fanart': os.path.join(addon_path, 'resources', 'fanart.jpg'),
                     'poster': os.path.join(addon_path, 'lib', 'media', 'live.png')})
    xbmcplugin.addDirectoryItem(handle=HANDLE, url=live_url, listitem=live_item, isFolder=True)

    # CaTube menu (online)
    catube_url = build_url({'action': 'list_online_catube_categories'})
    catube_item = xbmcgui.ListItem(label='CaTube')
    catube_item.setArt({'thumb': os.path.join(addon_path, 'lib', 'media', 'channels.png'), 
                        'icon': os.path.join(addon_path, 'lib', 'media', 'channels.png'),
                        'fanart': os.path.join(addon_path, 'resources', 'fanart.jpg'),
                        'poster': os.path.join(addon_path, 'lib', 'media', 'channels.png')})
    xbmcplugin.addDirectoryItem(handle=HANDLE, url=catube_url, listitem=catube_item, isFolder=True)

    # Custom Lists menu
    custom_lists_url = build_url({'action': 'list_custom_lists'})
    custom_lists_item = xbmcgui.ListItem(label='Custom Lists')
    custom_lists_item.setArt({'thumb': os.path.join(addon_path, 'lib', 'media', 'playlist.png'), 
                            'icon': os.path.join(addon_path, 'lib', 'media', 'playlist.png'),
                            'fanart': os.path.join(addon_path, 'resources', 'fanart.jpg'),
                            'poster': os.path.join(addon_path, 'lib', 'media', 'playlist.png')})
    xbmcplugin.addDirectoryItem(handle=HANDLE, url=custom_lists_url, listitem=custom_lists_item, isFolder=True)

    # Filme menu
    filme_url = build_url({'action': 'list_categories'})
    filme_item = xbmcgui.ListItem(label='Filme')
    filme_item.setArt({'thumb': os.path.join(addon_path, 'lib', 'media', 'home.png'), 
                      'icon': os.path.join(addon_path, 'lib', 'media', 'home.png'),
                      'fanart': os.path.join(addon_path, 'resources', 'fanart.jpg'),
                      'poster': os.path.join(addon_path, 'lib', 'media', 'home.png')})
    xbmcplugin.addDirectoryItem(handle=HANDLE, url=filme_url, listitem=filme_item, isFolder=True)

    # Concerte menu
    concerte_url = build_url({'action': 'search', 'query': 'concert integral full concert', 'search_type': 'video_only', 'apply_duration_filter': True})
    concerte_item = xbmcgui.ListItem(label='Concerte')
    concerte_item.setArt({'thumb': os.path.join(addon_path, 'lib', 'media', 'shorts.png'), 
                         'icon': os.path.join(addon_path, 'lib', 'media', 'shorts.png'),
                         'fanart': os.path.join(addon_path, 'resources', 'fanart.jpg'),
                         'poster': os.path.join(addon_path, 'lib', 'media', 'shorts.png')})
    xbmcplugin.addDirectoryItem(handle=HANDLE, url=concerte_url, listitem=concerte_item, isFolder=True)

    # Muzica Românească menu
    muzica_romaneasca_url = build_url({'action': 'list_romanian_music_categories'})
    muzica_romaneasca_item = xbmcgui.ListItem(label='Muzica Românească')
    muzica_romaneasca_item.setArt({'thumb': os.path.join(addon_path, 'lib', 'media', 'home.png'), 
                                  'icon': os.path.join(addon_path, 'lib', 'media', 'home.png'),
                                  'fanart': os.path.join(addon_path, 'resources', 'fanart.jpg'),
                                  'poster': os.path.join(addon_path, 'lib', 'media', 'home.png')})
    xbmcplugin.addDirectoryItem(handle=HANDLE, url=muzica_romaneasca_url, listitem=muzica_romaneasca_item, isFolder=True)

    # Add Favorites last when not first
    if not show_fav_first:
        xbmcplugin.addDirectoryItem(handle=HANDLE, url=favorites_url, listitem=favorites_item, isFolder=True)
    xbmcplugin.setContent(HANDLE, 'videos')
    xbmcplugin.endOfDirectory(HANDLE)

def list_catube_categories():
    """Display the categories from local CaTube_DATA."""
    for category_name in CATUBE_DATA:
        url = build_url({'action': 'list_catube_items', 'category_name': category_name})
        li = xbmcgui.ListItem(label=category_name.replace('List', '')) # Display name without 'List'
        
        # Use a relevant icon based on category name
        icon_map = {
            'RONewsList': 'channels.png',
            'WorldNewsList': 'channels.png',
            'MusicList': 'playlist.png',
            'SportList': 'playlist.png',
            'DocuList': 'playlist.png',
            'MovieList': 'playlist.png'
        }
        icon_file = icon_map.get(category_name, 'channels.png')
        li.setArt({'thumb': os.path.join(addon_path, 'lib', 'media', icon_file), 
                  'icon': os.path.join(addon_path, 'lib', 'media', icon_file),
                  'fanart': os.path.join(addon_path, 'resources', 'fanart.jpg')})
        xbmcplugin.addDirectoryItem(handle=HANDLE, url=url, listitem=li, isFolder=True)
    xbmcplugin.setContent(HANDLE, 'videos')
    xbmcplugin.endOfDirectory(HANDLE)

def list_catube_items(category_name):
    """Display items within a selected CaTube category."""
    items = CATUBE_DATA.get(category_name, [])

    for item_data in items:
        name, item_id, thumbnail, description, item_type, fanart = item_data
        
        # Clean name from color codes for display in info labels
        clean_name = re.sub(r'\[COLOR .*?\](.*?)\[/COLOR]', r'\1', name)

        if item_type == 'channel':
            url = build_url({'action': 'list_channel_content_from_search', 'channel_id': item_id})
            li = xbmcgui.ListItem(label=name)
            li.setInfo('video', {'title': clean_name, 'plot': description})
            if thumbnail:
                li.setArt({'thumb': thumbnail, 'icon': thumbnail, 'fanart': fanart if fanart else os.path.join(addon_path, 'resources', 'fanart.jpg')})
            else:
                li.setArt({'thumb': os.path.join(addon_path, 'lib', 'media', 'channels.png'), 
                          'icon': os.path.join(addon_path, 'lib', 'media', 'channels.png'),
                          'fanart': os.path.join(addon_path, 'resources', 'fanart.jpg')})
            xbmcplugin.addDirectoryItem(handle=HANDLE, url=url, listitem=li, isFolder=True)
        elif item_type == 'playlist':
            url = build_url({'action': 'list_playlist_videos_from_search', 'playlist_id': item_id})
            li = xbmcgui.ListItem(label=name)
            li.setInfo('video', {'title': clean_name, 'plot': description})
            if thumbnail:
                li.setArt({'thumb': thumbnail, 'icon': thumbnail, 'fanart': fanart if fanart else os.path.join(addon_path, 'resources', 'fanart.jpg')})
            else:
                li.setArt({'thumb': os.path.join(addon_path, 'lib', 'media', 'playlist.png'), 
                          'icon': os.path.join(addon_path, 'lib', 'media', 'playlist.png'),
                          'fanart': os.path.join(addon_path, 'resources', 'fanart.jpg')})
            xbmcplugin.addDirectoryItem(handle=HANDLE, url=url, listitem=li, isFolder=True)
        elif item_type == 'search':
            url = build_url({'action': 'search', 'query': item_id})
            li = xbmcgui.ListItem(label=name)
            li.setInfo('video', {'title': clean_name, 'plot': description})
            if thumbnail:
                li.setArt({'thumb': thumbnail, 'icon': thumbnail, 'fanart': fanart if fanart else os.path.join(addon_path, 'resources', 'fanart.jpg'), 'poster': thumbnail})
            else:
                li.setArt({'thumb': os.path.join(addon_path, 'lib', 'media', 'search.png'), 
                          'icon': os.path.join(addon_path, 'lib', 'media', 'search.png'),
                          'fanart': os.path.join(addon_path, 'resources', 'fanart.jpg'),
                          'poster': os.path.join(addon_path, 'lib', 'media', 'search.png')})
            xbmcplugin.addDirectoryItem(handle=HANDLE, url=url, listitem=li, isFolder=True)

    xbmcplugin.setContent(HANDLE, 'videos')
    xbmcplugin.endOfDirectory(HANDLE)

def list_custom_lists():
    """Display the list of custom lists from custom_lists.txt"""
    # First check the addon data directory (user's custom lists)
    user_custom_lists_file = os.path.join(addon_data_path, 'custom_lists.txt')
    # Also check the plugin directory for reference lists
    plugin_custom_lists_file = os.path.join(addon_path, 'resources/custom_lists.txt')
    
    # Add option to add a new custom list first
    add_url = build_url({'action': 'add_custom_list'})
    add_item = xbmcgui.ListItem(label='Add New Custom List')
    add_item.setArt({'thumb': os.path.join(addon_path, 'lib', 'media', 'playlist.png'), 
                    'icon': os.path.join(addon_path, 'lib', 'media', 'playlist.png'),
                    'fanart': os.path.join(addon_path, 'resources', 'fanart.jpg')})
    xbmcplugin.addDirectoryItem(handle=HANDLE, url=add_url, listitem=add_item, isFolder=True)

    # Collect all entries - first from user file, then from plugin file if it exists
    all_lines = []
    
    # Add user custom lists
    if xbmcvfs.exists(user_custom_lists_file):
        with xbmcvfs.File(user_custom_lists_file, 'r') as f:
            content = f.read()
            if content:
                user_lines = content.strip().split('\n')
                for line in user_lines:
                    line = line.strip()
                    if line:  # Only add non-empty lines
                        all_lines.append(('user', line))
    
    # Add plugin custom lists if they exist and haven't been overridden by user
    if xbmcvfs.exists(plugin_custom_lists_file):
        with xbmcvfs.File(plugin_custom_lists_file, 'r') as f:
            content = f.read()
            if content:
                plugin_lines = content.strip().split('\n')
                for line in plugin_lines:
                    line = line.strip()
                    if line:  # Only add non-empty lines
                        # Check if this entry already exists in user's list to avoid duplicates
                        line_exists = False
                        for _, user_line in all_lines:
                            if user_line == line:
                                line_exists = True
                                break
                        
                        if not line_exists:
                            all_lines.append(('plugin', line))

    # Prioritize channel, then playlist, then user
    def _key(lp):
        lt = lp[0] if isinstance(lp, tuple) else 'plugin'
        linep = lp[1]
        typ = (linep.split(':',2)[0] if ':' in linep else 'channel').lower()
        order = {'channel': 0, 'playlist': 1, 'user': 2}
        return (order.get(typ, 3), lt != 'user', linep)

    for list_source, line in sorted(all_lines, key=_key):
        if not line:
            continue
            
        # Format in custom_lists.txt is: type:id:display_name
        parts = line.split(':', 2)  # Split into at most 3 parts
        if len(parts) < 3:
            continue
            
        list_type = parts[0]  # 'channel', 'playlist', 'user'
        list_id = parts[1]
        display_name = parts[2]
        display_title = clean_video_title(display_name)
        
        # Create context menu to remove the list (only for user lists, not plugin lists)
        context_menu = []
        if list_source == 'user':  # Only allow removal for user-created lists
            remove_url = build_url({'action': 'remove_custom_list', 'entry_to_remove': line, 'file_type': 'user'})
            context_menu = [('Remove from Custom Lists', f'RunPlugin({remove_url})')]
        
        if list_type == 'channel':
            # For channels, show complete content (videos and playlists)
            url = build_url({'action': 'list_channel_content_from_search', 'channel_id': list_id})
            li = xbmcgui.ListItem(label=display_title)
            li.setInfo('video', {'title': display_title})
            li.setArt({'thumb': os.path.join(addon_path, 'lib', 'media', 'channels.png'), 
                      'icon': os.path.join(addon_path, 'lib', 'media', 'channels.png'),
                      'fanart': os.path.join(addon_path, 'resources', 'fanart.jpg')})
            li.addContextMenuItems(context_menu)
            xbmcplugin.addDirectoryItem(handle=HANDLE, url=url, listitem=li, isFolder=True)
        elif list_type == 'playlist':
            url = build_url({'action': 'list_playlist_videos_from_search', 'playlist_id': list_id})
            li = xbmcgui.ListItem(label=display_title)
            li.setInfo('video', {'title': display_title})
            li.setArt({'thumb': os.path.join(addon_path, 'lib', 'media', 'playlist.png'), 
                      'icon': os.path.join(addon_path, 'lib', 'media', 'playlist.png'),
                      'fanart': os.path.join(addon_path, 'resources', 'fanart.jpg')})
            li.addContextMenuItems(context_menu)
            xbmcplugin.addDirectoryItem(handle=HANDLE, url=url, listitem=li, isFolder=True)
        elif list_type == 'user':
            # For users, we'll show complete content (videos and playlists)
            url = build_url({'action': 'list_user_content_from_search', 'username': list_id})
            li = xbmcgui.ListItem(label=display_title)
            li.setInfo('video', {'title': display_title})
            li.setArt({'thumb': os.path.join(addon_path, 'lib', 'media', 'user.png'), 
                      'icon': os.path.join(addon_path, 'lib', 'media', 'user.png'),
                      'fanart': os.path.join(addon_path, 'resources', 'fanart.jpg')})
            li.addContextMenuItems(context_menu)
            xbmcplugin.addDirectoryItem(handle=HANDLE, url=url, listitem=li, isFolder=True)

    xbmcplugin.setContent(HANDLE, 'videos')
    xbmcplugin.endOfDirectory(HANDLE)

def add_custom_list():
    """Add a new custom list to custom_lists.txt"""
    # Ask user for list type
    list_types = ['Channel', 'Playlist', 'User']
    type_selection = xbmcgui.Dialog().select('Select List Type', list_types)
    
    if type_selection == -1:  # User cancelled
        return

    list_type = list_types[type_selection].lower()
    
    # Ask for list ID
    kb = xbmc.Keyboard('', f'Enter {list_types[type_selection]} ID')
    kb.doModal()
    if not kb.isConfirmed():
        return
    
    list_id = kb.getText().strip()
    if not list_id:
        return

    # Ask for display name
    kb = xbmc.Keyboard('', 'Enter Display Name')
    kb.doModal()
    if not kb.isConfirmed():
        return
    
    display_name = kb.getText().strip()
    if not display_name:
        return

    # Format the entry
    entry = f'{list_type}:{list_id}:{display_name}'
    
    # Append to custom_lists.txt in user data directory
    custom_lists_file = os.path.join(addon_data_path, 'custom_lists.txt')
    
    # Read existing entries and add the new one
    existing_lines = []
    if xbmcvfs.exists(custom_lists_file):
        with xbmcvfs.File(custom_lists_file, 'r') as f:
            content = f.read()
            if content:
                existing_lines = content.strip().split('\n')
    
    all_lines = existing_lines + [entry]
    with xbmcvfs.File(custom_lists_file, 'w') as f:
        f.write('\n'.join(all_lines) + '\n')
    
    xbmcgui.Dialog().notification('Success', f'Added {display_name} to custom lists.')
    xbmc.executebuiltin('Container.Refresh')

def remove_custom_list(entry_to_remove, file_type='user'):
    """Remove a custom list from custom_lists.txt"""
    if not entry_to_remove:
        return

    # Use the user data file for removal
    custom_lists_file = os.path.join(addon_data_path, 'custom_lists.txt')
    
    if not xbmcvfs.exists(custom_lists_file):
        return

    # Read all lines
    content_lines = []
    with xbmcvfs.File(custom_lists_file, 'r') as f:
        content = f.read()
        if content:
            content_lines = content.strip().split('\n')

    # Remove the specified entry
    updated_lines = [line for line in content_lines if line.strip() != entry_to_remove]

    # Write the updated content back to the file
    with xbmcvfs.File(custom_lists_file, 'w') as f:
        if updated_lines:
            f.write('\n'.join(updated_lines) + '\n')
        # If no lines left, file will be empty, which is correct
    
    xbmcgui.Dialog().notification('Success', 'Removed from custom lists.')
    xbmc.executebuiltin('Container.Refresh')

def add_to_custom_list_from_search(list_type, list_id, list_title):
    """Add a channel or playlist to custom lists from search results"""
    if not list_type or not list_id or not list_title:
        return

    # Format the entry
    entry = f'{list_type}:{list_id}:{list_title}'
    
    # Append to custom_lists.txt in user data directory
    custom_lists_file = os.path.join(addon_data_path, 'custom_lists.txt')
    
    # Read existing entries to check for duplicates and prepare to append
    existing_lines = []
    if xbmcvfs.exists(custom_lists_file):
        with xbmcvfs.File(custom_lists_file, 'r') as f:
            content = f.read()
            if content:
                existing_lines = content.strip().split('\n')
        
        # Check if entry already exists
        if entry in existing_lines:
            xbmcgui.Dialog().notification('Info', 'This list is already in your custom lists.')
            return
    
    # Add the new entry and write all lines back to file
    all_lines = existing_lines + [entry]
    with xbmcvfs.File(custom_lists_file, 'w') as f:
        f.write('\n'.join(all_lines) + '\n')
    
    xbmcgui.Dialog().notification('Success', f'Added {list_title} to custom lists.')

def list_favorites():
    """Display the list of favorite videos, channels, and playlists from favorites.txt"""
    favorites_file = os.path.join(addon_data_path, 'favorites.txt')
    
    if not xbmcvfs.exists(favorites_file):
        xbmcgui.Dialog().notification('Info', 'No favorites found.')
        xbmcplugin.endOfDirectory(HANDLE)
        return

    lines = []
    with xbmcvfs.File(favorites_file, 'r') as f:
        content = f.read()
        if content:
            lines = content.strip().split('\n')

    entries = []
    for line in lines:
        line = line.strip()
        if not line:
            continue
            
        # Format in favorites.txt should be: type:id:title (new format) or id:title (old format for backward compatibility)
        # First check for new format (with type prefix)
        parts = line.split(':', 2)  # Split into max 3 parts (type, id, title)
        
        content_type = 'video'  # default
        content_id = None
        title = None
        
        if len(parts) == 3:
            # New format: type:id:title
            content_type, content_id, title = parts
        elif len(parts) >= 2:
            # Old format or just id:title: assume it's a video
            content_id, title = parts[0], parts[1]
            if parts[0] in ['video', 'channel', 'playlist']:
                # This is likely a new format entry but with title containing colons
                content_type, content_id = parts[0], parts[1]
                if len(parts) > 2:
                    title = ':'.join(parts[2:])  # Join remaining parts for title
            else:
                # Old format: id:title
                content_type = 'video'
                content_id = parts[0]
                title = parts[1]
        else:
            continue  # Skip invalid entries
        
        entries.append((content_type, content_id, title))

    # Sort entries: channel, playlist, video
    order_index = {'channel': 0, 'playlist': 1, 'video': 2}
    for content_type, content_id, title in sorted(entries, key=lambda e: order_index.get(e[0], 3)):
        safe_title = clean_video_title(title)
        # Create context menu to remove from favorites
        remove_url = build_url({'action': 'remove_from_favorites', 'video_id': content_id})
        context_menu = [('Remove from Favorites', f'RunPlugin({remove_url})')]
        
        # Determine the action and create appropriate list item
        if content_type == 'video':
            url = build_url({'action': 'play', 'video_id': content_id})
            li = xbmcgui.ListItem(label=safe_title)
            li.setInfo('video', {'title': safe_title})
            li.setArt({'thumb': os.path.join(addon_path, 'lib', 'media', 'bookmarks.png'), 
                      'icon': os.path.join(addon_path, 'lib', 'media', 'bookmarks.png'),
                      'fanart': os.path.join(addon_path, 'resources', 'fanart.jpg')})
            li.setProperty('IsPlayable', 'true')
        elif content_type == 'channel':
            url = build_url({'action': 'list_channel_content_from_search', 'channel_id': content_id})
            li = xbmcgui.ListItem(label=f'[COLOR blue]Canal:[/COLOR] {safe_title}')
            li.setInfo('video', {'title': safe_title})
            li.setArt({'thumb': os.path.join(addon_path, 'lib', 'media', 'channels.png'), 
                      'icon': os.path.join(addon_path, 'lib', 'media', 'channels.png'),
                      'fanart': os.path.join(addon_path, 'resources', 'fanart.jpg')})
        elif content_type == 'playlist':
            url = build_url({'action': 'list_playlist_videos_from_search', 'playlist_id': content_id})
            li = xbmcgui.ListItem(label=f'[COLOR green]Playlist:[/COLOR] {safe_title}')
            li.setInfo('video', {'title': safe_title})
            li.setArt({'thumb': os.path.join(addon_path, 'lib', 'media', 'playlist.png'), 
                      'icon': os.path.join(addon_path, 'lib', 'media', 'playlist.png'),
                      'fanart': os.path.join(addon_path, 'resources', 'fanart.jpg')})
        else:
            # Unknown type, skip
            continue
        
        li.addContextMenuItems(context_menu)
        xbmcplugin.addDirectoryItem(handle=HANDLE, url=url, listitem=li, isFolder=(content_type != 'video'))

    xbmcplugin.setContent(HANDLE, 'videos')
    xbmcplugin.endOfDirectory(HANDLE)

def add_to_favorites(content_id, content_type='video', title=None):
    """Add a video, channel, or playlist to favorites.txt"""
    if not content_id:
        return

    # Handle backward compatibility - if only video_id is passed as first parameter
    # In older versions, video_id was the first (and only) parameter
    # If content_id looks like a video_id and content_type is default, treat as video
    if content_type == 'video' and title is None and ':' not in str(content_id) and len(str(content_id)) > 10:
        # This looks like an old-style call with just video_id
        video_id = content_id
        # Get video details to save with the video ID
        details_data = youtube_api.get_video_details([video_id])
        video_details = details_data.get('items', [{}])[0] if details_data and 'items' in details_data else {}
        
        if video_details:
            title = video_details.get('snippet', {}).get('title', f'Video {video_id}')
        else:
            title = f'Video {video_id}'
        
        # Format the entry - include type so we know how to handle it later
        entry = f'{content_type}:{video_id}:{title}'
    elif content_type == 'video':
        video_id = content_id
        if title is None:
            details_data = youtube_api.get_video_details([video_id])
            video_details = details_data.get('items', [{}])[0] if details_data and 'items' in details_data else {}
            
            if video_details:
                title = video_details.get('snippet', {}).get('title', f'Video {video_id}')
            else:
                title = f'Video {video_id}'
        
        # Format the entry - include type so we know how to handle it later
        entry = f'{content_type}:{video_id}:{title}'
        
    elif content_type == 'channel':
        channel_id = content_id
        if title is None:
            title = f'Channel {channel_id}'
        entry = f'{content_type}:{channel_id}:{title}'
        
    elif content_type == 'playlist':
        playlist_id = content_id
        if title is None:
            title = f'Playlist {playlist_id}'
        entry = f'{content_type}:{playlist_id}:{title}'
    else:
        xbmcgui.Dialog().notification('Error', 'Invalid content type')
        return

    # Append to favorites.txt
    favorites_file = os.path.join(addon_data_path, 'favorites.txt')
    
    # Read existing entries to check for duplicates and prepare to append
    existing_lines = []
    if xbmcvfs.exists(favorites_file):
        with xbmcvfs.File(favorites_file, 'r') as f:
            content = f.read()
            if content:
                existing_lines = content.strip().split('\n')
        
        # Check if entry already exists (check for the exact combination)
        content_identifier = f'{content_type}:{content_id}:'
        if any(line.startswith(content_identifier) for line in existing_lines):
            xbmcgui.Dialog().notification('Info', f'This {content_type} is already in favorites.')
            return
    
    # Add the new entry and write all lines back to file
    all_lines = existing_lines + [entry]
    with xbmcvfs.File(favorites_file, 'w') as f:
        f.write('\n'.join(all_lines) + '\n')
    
    xbmcgui.Dialog().notification('Success', f'Added {content_type} to favorites.')

def remove_from_favorites(video_id):
    """Remove a video from favorites.txt"""
    if not video_id:
        return

    favorites_file = os.path.join(addon_data_path, 'favorites.txt')
    
    if not xbmcvfs.exists(favorites_file):
        return

    # Read all lines
    content_lines = []
    with xbmcvfs.File(favorites_file, 'r') as f:
        content = f.read()
        if content:
            content_lines = content.strip().split('\n')

    # Remove the line that starts with the video_id (it could be video, channel, or playlist)
    updated_lines = []
    for line in content_lines:
        if line:
            # Check if this line starts with the ID in any format: type:id: or just id:
            if not (line.startswith(f'video:{video_id}:') or 
                    line.startswith(f'channel:{video_id}:') or 
                    line.startswith(f'playlist:{video_id}:') or
                    line.startswith(f'{video_id}:')):  # For backward compatibility
                updated_lines.append(line)

    # Write the updated content back to the file
    with xbmcvfs.File(favorites_file, 'w') as f:
        if updated_lines:
            f.write('\n'.join(updated_lines) + '\n')
        # If no lines left, file will be empty, which is correct
    
    xbmcgui.Dialog().notification('Success', 'Removed from favorites.')
    xbmc.executebuiltin('Container.Refresh')

def list_romanian_music_categories():
    """Display categories for Romanian music"""
    categories = load_romanian_music_content()
    
    if not categories:
        xbmcgui.Dialog().notification('Info', 'No Romanian music content found.')
        xbmcplugin.endOfDirectory(HANDLE)
        return
    
    # Add each category
    for category_name in categories:
        url = build_url({'action': 'list_romanian_music_items', 'category': category_name})
        li = xbmcgui.ListItem(label=category_name)
        li.setArt({'thumb': os.path.join(addon_path, 'lib', 'media', 'home.png'), 
                  'icon': os.path.join(addon_path, 'lib', 'media', 'home.png'),
                  'fanart': os.path.join(addon_path, 'resources', 'fanart.jpg')})
        xbmcplugin.addDirectoryItem(handle=HANDLE, url=url, listitem=li, isFolder=True)
    
    xbmcplugin.setContent(HANDLE, 'videos')
    xbmcplugin.endOfDirectory(HANDLE)

def list_romanian_music_items(category_name):
    """Display items in a Romanian music category"""
    categories = load_romanian_music_content()
    
    if category_name not in categories:
        xbmcgui.Dialog().notification('Info', 'Category not found.')
        xbmcplugin.endOfDirectory(HANDLE)
        return
    
    items = categories[category_name]
    
    # Prioritize channels, then playlists, then videos
    items_ordered = []
    items_ordered.extend([i for i in items if i['type'] in ['channel', 'handle']])
    items_ordered.extend([i for i in items if i['type'] == 'playlist'])
    items_ordered.extend([i for i in items if i['type'] == 'video'])

    for item in items_ordered:
        title = item['title']
        content_id = item['id']
        content_type = item['type']
        
        # Color-coded titles based on content type
        if content_type in ['channel', 'handle']:
            display_title = f'[COLOR blue]Canal:[/COLOR] {title}' if content_type == 'channel' else f'[COLOR blue]Canal:[/COLOR] {title}'
            thumb_icon = 'channels.png'
            is_folder = True
        elif content_type == 'playlist':
            display_title = f'[COLOR green]Playlist:[/COLOR] {title}'
            thumb_icon = 'playlist.png'
            is_folder = True
        else:  # video
            display_title = title
            thumb_icon = 'home.png'
            is_folder = False
            
        # Route handles to user content function, others to appropriate functions
        if content_type == 'handle':
            url_params = {'action': 'list_user_content_from_search', 'username': content_id}
        else:
            url_params = {'action': 'list_channel_content_from_search' if content_type == 'channel' else 
                                 'list_playlist_videos_from_search' if content_type == 'playlist' else 'play',
                         f'{content_type}_id' if content_type in ['channel', 'playlist'] else 'video_id': content_id}
        
        url = build_url(url_params)
        li = xbmcgui.ListItem(label=display_title)
        li.setInfo('video', {'title': title})
        li.setArt({'thumb': os.path.join(addon_path, 'lib', 'media', thumb_icon), 
                  'icon': os.path.join(addon_path, 'lib', 'media', thumb_icon),
                  'fanart': os.path.join(addon_path, 'resources', 'fanart.jpg')})
        
        if content_type == 'video':
            li.setProperty('IsPlayable', 'true')
            
        # Add context menu for adding to favorites/custom lists
        context_menu = []
        
        if content_type in ['channel', 'handle']:
            add_to_custom_url = build_url({'action': 'add_to_custom_list_from_search', 'list_type': 'channel' if content_type == 'channel' else 'user', 'list_id': content_id, 'list_title': title})
            context_menu.append(('Adaugă la Custom List', f'RunPlugin({add_to_custom_url})'))
            add_to_favorites_url = build_url({'action': 'add_to_favorites', 'video_id': content_id, 'content_type': 'channel' if content_type == 'channel' else 'user', 'title': title})
            context_menu.append(('Adaugă la favorite', f'RunPlugin({add_to_favorites_url})'))
        elif content_type == 'playlist':
            add_to_custom_url = build_url({'action': 'add_to_custom_list_from_search', 'list_type': 'playlist', 'list_id': content_id, 'list_title': title})
            context_menu.append(('Adaugă la Custom List', f'RunPlugin({add_to_custom_url})'))
            add_to_favorites_url = build_url({'action': 'add_to_favorites', 'video_id': content_id, 'content_type': 'playlist', 'title': title})
            context_menu.append(('Adaugă la favorite', f'RunPlugin({add_to_favorites_url})'))
        else:  # video
            add_to_favorites_url = build_url({'action': 'add_to_favorites', 'video_id': content_id, 'content_type': 'video', 'title': title})
            context_menu.append(('Adaugă la favorite', f'RunPlugin({add_to_favorites_url})'))
            
        li.addContextMenuItems(context_menu)
        xbmcplugin.addDirectoryItem(handle=HANDLE, url=url, listitem=li, isFolder=is_folder)
    
    xbmcplugin.setContent(HANDLE, 'videos')
    xbmcplugin.endOfDirectory(HANDLE)

# Parse YouTube URL to extract ID
def parse_youtube_url(url):
    """Extract YouTube ID from URL"""
    import re
    
    # Match different YouTube URL formats
    patterns = [
        r'(?:https?://)?(?:www\.)?youtube\.com/playlist\?list=([a-zA-Z0-9_-]+)',
        r'(?:https?://)?(?:www\.)?youtube\.com/watch\?v=([a-zA-Z0-9_-]+)',
        r'(?:https?://)?(?:www\.)?youtube\.com/@([a-zA-Z0-9_-]+)(?:/.*)?',  # Handle format with optional suffix
        r'(?:https?://)?(?:www\.)?youtube\.com/user/([a-zA-Z0-9_-]+)(?:/.*)?',  # Legacy user format
        r'(?:https?://)?(?:www\.)?youtube\.com/channel/([a-zA-Z0-9_-]+)(?:/.*)?',  # Channel ID format
        r'(?:https?://)?youtu\.be/([a-zA-Z0-9_-]+)'
    ]
    
    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1)
    
    return None

# Determine content type from URL
def determine_content_type_from_url(url):
    """Determine content type from YouTube URL"""
    if 'playlist?list=' in url:
        return 'playlist'
    elif '/@' in url:
        return 'handle'  # Special type for handles
    elif '/channel/' in url:
        return 'channel'
    elif '/user/' in url:
        return 'channel'
    elif 'watch?v=' in url or 'youtu.be/' in url:
        return 'video'
    else:
        return 'video'

# Load Romanian music content
def load_romanian_music_content():
    """Load Romanian music content from rom.txt"""
    rom_file = os.path.join(addon_path, 'resources/rom.txt')
    
    if not xbmcvfs.exists(rom_file):
        return {}
    
    categories = {}
    current_category = None
    
    with xbmcvfs.File(rom_file, 'r') as f:
        content = f.read()
        lines = content.strip().split('\n') if content else []
    
    for line in lines:
        line = line.strip()
        if not line:
            continue
            
        # Check if it's a category header (Tip:)
        if line.startswith('Tip:'):
            category_name = line.replace('Tip:', '').strip()
            current_category = category_name
            categories[category_name] = []
        elif current_category and 'youtube.com/' in line:
            # Extract title and URL
            parts = line.split(': https://')
            if len(parts) >= 2:
                title = parts[0].strip()
                url = 'https://' + parts[1].strip()
                
                # Extract YouTube identifier
                youtube_identifier = parse_youtube_url(url)
                if youtube_identifier:
                    # Determine content type based on URL
                    content_type = determine_content_type_from_url(url)
                    
                    # For handles, we keep the full handle (including @)
                    if content_type == 'handle':
                        identifier = '@' + youtube_identifier
                    else:
                        identifier = youtube_identifier
                    
                    categories[current_category].append({
                        'title': title,
                        'id': identifier,
                        'type': content_type,
                        'url': url
                    })
    
    return categories

def router(paramstring):
    """Route the plugin to the correct function."""
    params = dict(urllib.parse.parse_qsl(paramstring.lstrip('?')))
    
    action = params.get('action')
    
    if action == 'search':
        query = params.get('query', '')
        page_token = params.get('page_token', None)
        event_type = params.get('event_type', None)
        search_type = params.get('search_type', None)
        apply_duration_filter = params.get('apply_duration_filter', 'False').lower() == 'true'
        search_action(query=query, page_token=page_token, event_type=event_type, search_type=search_type, apply_duration_filter=apply_duration_filter)
    elif action == 'search_live':
        query = params.get('query', '')
        page_token = params.get('page_token', None)
        event_type = params.get('event_type', None)
        search_type = params.get('search_type', None)
        apply_duration_filter = params.get('apply_duration_filter', 'False').lower() == 'true'
        search_action(query=query, page_token=page_token, event_type=event_type, search_type=search_type, apply_duration_filter=apply_duration_filter)
    elif action == 'play':
        play_video(params.get('video_id', ''))
    elif action == 'list_categories':
        list_categories()
    elif action == 'list_favorites':
        list_favorites()
    elif action == 'add_to_favorites':
        video_id = params.get('video_id')
        content_type = params.get('content_type', 'video')
        title = params.get('title')
        add_to_favorites(video_id, content_type, title)
    elif action == 'remove_from_favorites':
        remove_from_favorites(params.get('video_id'))
    elif action == 'list_trending':
        page_token = params.get('page_token', None)
        list_trending_videos(page_token=page_token)
    elif action == 'list_channel_videos_from_search':
        channel_id = params.get('channel_id')
        page_token = params.get('page_token', None)
        list_channel_videos_from_search(channel_id, page_token=page_token)
    elif action == 'list_channel_content_from_search':
        channel_id = params.get('channel_id')
        page_token = params.get('page_token', None)
        list_channel_content_from_search(channel_id, page_token=page_token)
    
    elif action == 'list_playlist_videos_from_search':
        playlist_id = params.get('playlist_id')
        page_token = params.get('page_token', None)
        list_playlist_videos_from_search(playlist_id, page_token=page_token)
    elif action == 'list_custom_lists':
        list_custom_lists()
    elif action == 'list_romanian_music_categories':
        list_romanian_music_categories()
    elif action == 'list_romanian_music_items':
        category_name = params.get('category')
        list_romanian_music_items(category_name)
    elif action == 'list_user_content_from_search':
        username = params.get('username')
        page_token = params.get('page_token', None)
        list_user_content_from_search(username, page_token=page_token)
    elif action == 'add_custom_list':
        add_custom_list()
    elif action == 'remove_custom_list':
        remove_custom_list(params.get('entry_to_remove'), params.get('file_type', 'user'))
    elif action == 'play_custom_list':
        list_id = params.get('list_id')
        list_type = params.get('list_type')
        page_token = params.get('page_token', None)
        pass  # play_custom_list function not implemented
    elif action == 'add_to_custom_list_from_search':
        list_type = params.get('list_type')
        list_id = params.get('list_id')
        list_title = params.get('list_title')
        add_to_custom_list_from_search(list_type, list_id, list_title)
    elif action == 'list_catube_categories':
        list_catube_categories()
    elif action == 'list_catube_items':
        category_name = params.get('category_name')
        list_catube_items(category_name)
    elif action == 'list_online_catube_categories':
        list_online_catube_categories()
    elif action == 'list_online_catube_items':
        category_name = params.get('category_name')
        list_online_catube_items(category_name)
    else:
        # Show the main menu
        list_main_menu()

if __name__ == '__main__':
    router(sys.argv[2])
