import xbmc
import xbmcgui
import requests
import json
import xbmcaddon
import zlib
import base64
import time

# Get addon info
addon = xbmcaddon.Addon()

ENCODED_API_KEYS = [
    '==QBQoflAUgqX58cNQ3D3jcK34ECNaNMIcbNIniDMlC90WLL3InqN6kD05KDKxK9yBlUySVrOpsVryJe',
    '==AURIrrAUgqW5STMF/dz/CDsKLj3+4iy7yzpoCrNKdDK4qS2gSi3jiq05KDKxK9yBlUySVrOpsVryJe',
    '==QWQ0glAUgqX9CLLLXdNc9yo0oc2zCjLTvsMbrDyvQMq4YNsITL1sC905KDKxK9yBlUySVrOpsVryJe',
    '==gCQIrjAUgqWps8I8YzMwK8I4qNL0g9MJXi05sNwMfLpcjSKRHizKnd05KDKxK9yBlUySVrOpsVryJe',
    '==gaRcftAUgqQRLDLuQS30McI4ySNp8jswIrIoITsiU9vsk82/gLK5qz05KDKxK9yBlUySVrOpsVryJe',
    '==QYQ8joAUgqUJP8IyIM3oAKysczRzcdOsw8P1Y0KhKqp0yLy7I92qSc05KDKxK9yBlUySVrOpsVryJe',
    '==wZQA/nAUgqWtSSwRzLws69JJTN2dHDMNfdrsC9JNHSMogLx4CcMusL05KDKxK9yBlUySVrOpsVryJe',
    '==gePEaiAUgqURXS1zsNx8ALNLd8PdHjMK783QnipgU81IHNL081vIji05KDKxK9yBlUySVrOpsVryJe',
    '==wZQA/nAUgqWtSSwRzLws69JJTN2dHDMNfdrsC9JNHSMogLx4CcMusL05KDKxK9yBlUySVrOpsVryJe'
]

current_key_index = 0

# Request configuration
REQUEST_TIMEOUT = 10

def _requests_get(url, params=None, retries=2):
    """Wrapper around requests.get with a default timeout and basic retry."""
    # Use a modern Firefox User-Agent to mimic a browser client
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:130.0) Gecko/20100101 Firefox/130.0'
    }
    last_exc = None
    for attempt in range(retries + 1):
        try:
            return requests.get(url, params=params, timeout=REQUEST_TIMEOUT, headers=headers)
        except requests.exceptions.RequestException as e:
            last_exc = e
            # Do not busy-loop; short backoff
            time.sleep(0.7)
    # Re-raise last exception if all retries exhausted
    raise last_exc

def _should_rotate_key(exc):
    """Return True if the error suggests rotating the API key (e.g., HTTP 403)."""
    try:
        resp = getattr(exc, 'response', None)
        status = resp.status_code if resp is not None else None
    except Exception:
        status = None
    return status == 403

def decode_key(encoded_key):
    """Decodes the API key."""
    try:
        reversed_data = encoded_key.encode('utf-8')
        encoded_data = reversed_data[::-1]
        compressed_data = base64.b64decode(encoded_data)
        json_data = zlib.decompress(compressed_data)
        data = json.loads(json_data)
        return data['key']
    except Exception as e:
        xbmc.log(f'Error decoding API key: {str(e)}', xbmc.LOGERROR)
        return None

def get_next_api_key():
    """Gets the next available API key."""
    global current_key_index
    
    if current_key_index >= len(ENCODED_API_KEYS):
        current_key_index = 0  # Reset to the beginning
        return None # All keys have been tried

    key = decode_key(ENCODED_API_KEYS[current_key_index])
    current_key_index += 1
    return key

def search_videos(query, event_type=None, max_results=20, page_token=None, search_type=None):
    """Search for videos on YouTube using the API."""
    global current_key_index
    current_key_index = 0 # Reset for each new search

    while True:
        api_key = get_next_api_key()
        if not api_key:
            xbmc.log('All API keys failed.', xbmc.LOGERROR)
            return None

        search_url = 'https://www.googleapis.com/youtube/v3/search'
        params = {
            'part': 'snippet',
            'maxResults': max_results,
            'q': query,
            'key': api_key
        }

        # Determine search type - if search_type is provided, use it; otherwise use default logic
        if search_type:
            params['type'] = search_type
        elif event_type == 'live':
            params['type'] = 'video'
        else:
            params['type'] = 'video,channel,playlist'

        if event_type:
            params['eventType'] = event_type
        
        if page_token:
            params['pageToken'] = page_token
        
        try:
            response = _requests_get(search_url, params=params)
            response.raise_for_status()
            data = response.json()
            return data
        except requests.exceptions.RequestException as e:
            xbmc.log(f'Error searching YouTube with key index {current_key_index - 1}: {str(e)}', xbmc.LOGWARNING)
            if _should_rotate_key(e):
                continue
            return None

def get_video_details(video_ids):
    """Get detailed information about a specific video."""
    global current_key_index
    current_key_index = 0 # Reset for each new request

    while True:
        api_key = get_next_api_key()
        if not api_key:
            xbmc.log('All API keys failed.', xbmc.LOGERROR)
            return None

        details_url = 'https://www.googleapis.com/youtube/v3/videos'
        params = {
            'part': 'snippet,contentDetails,statistics',
            'id': ','.join(video_ids),
            'key': api_key
        }
        
        try:
            response = _requests_get(details_url, params=params)
            response.raise_for_status()
            data = response.json()
            return data
        except requests.exceptions.RequestException as e:
            xbmc.log(f'Error getting video details with key index {current_key_index - 1}: {str(e)}', xbmc.LOGWARNING)
            if _should_rotate_key(e):
                continue
            return None

def get_trending_videos(region_code, page_token=None, max_results=20):
    """Get trending videos for a specific region."""
    global current_key_index
    current_key_index = 0 # Reset for each new request

    while True:
        api_key = get_next_api_key()
        if not api_key:
            xbmc.log('All API keys failed.', xbmc.LOGERROR)
            return None

        videos_url = 'https://www.googleapis.com/youtube/v3/videos'
        params = {
            'part': 'snippet,contentDetails,statistics',
            'chart': 'mostPopular',
            'regionCode': region_code,
            'maxResults': max_results,
            'key': api_key
        }

        if page_token:
            params['pageToken'] = page_token
        
        try:
            response = _requests_get(videos_url, params=params)
            response.raise_for_status()
            data = response.json()
            return data
        except requests.exceptions.RequestException as e:
            xbmc.log(f'Error getting trending videos with key index {current_key_index - 1}: {str(e)}', xbmc.LOGWARNING)
            if _should_rotate_key(e):
                continue
            return None

def get_playlist_details(playlist_id):
    """Get detailed information about a specific playlist."""
    global current_key_index
    current_key_index = 0 # Reset for each new request

    while True:
        api_key = get_next_api_key()
        if not api_key:
            xbmc.log('All API keys failed.', xbmc.LOGERROR)
            return None

        details_url = 'https://www.googleapis.com/youtube/v3/playlists'
        params = {
            'part': 'snippet',
            'id': playlist_id,
            'key': api_key
        }
        
        try:
            response = _requests_get(details_url, params=params)
            response.raise_for_status()
            data = response.json()
            return data
        except requests.exceptions.RequestException as e:
            xbmc.log(f'Error getting playlist details with key index {current_key_index - 1}: {str(e)}', xbmc.LOGWARNING)
            if _should_rotate_key(e):
                continue
            return None

def get_channel_details(channel_id):
    """Get detailed information about a specific channel."""
    global current_key_index
    current_key_index = 0 # Reset for each new request

    while True:
        api_key = get_next_api_key()
        if not api_key:
            xbmc.log('All API keys failed.', xbmc.LOGERROR)
            return None

        details_url = 'https://www.googleapis.com/youtube/v3/channels'
        params = {
            'part': 'snippet',
            'id': channel_id,
            'key': api_key
        }
        
        try:
            response = _requests_get(details_url, params=params)
            response.raise_for_status()
            data = response.json()
            return data
        except requests.exceptions.RequestException as e:
            xbmc.log(f'Error getting channel details with key index {current_key_index - 1}: {str(e)}', xbmc.LOGWARNING)
            if _should_rotate_key(e):
                continue
            return None

def get_channel_details_by_username(username):
    """Get detailed information about a channel by username."""
    global current_key_index
    current_key_index = 0 # Reset for each new request

    while True:
        api_key = get_next_api_key()
        if not api_key:
            xbmc.log('All API keys failed.', xbmc.LOGERROR)
            return None

        details_url = 'https://www.googleapis.com/youtube/v3/channels'
        params = {
            'part': 'snippet',
            'forUsername': username,
            'key': api_key
        }
        
        try:
            response = _requests_get(details_url, params=params)
            response.raise_for_status()
            data = response.json()
            return data
        except requests.exceptions.RequestException as e:
            xbmc.log(f'Error getting channel details by username with key index {current_key_index - 1}: {str(e)}', xbmc.LOGWARNING)
            if _should_rotate_key(e):
                continue
            return None

def resolve_handle_to_channel_id(handle):
    """Resolve a YouTube handle to a channel ID using search API."""
    if not handle:
        return None
    # Normalize handle, ensure it starts with '@'
    h = handle if handle.startswith('@') else f'@{handle}'
    data = search_videos(h, search_type='channel', max_results=5)
    try:
        items = data.get('items', []) if data else []
        if not items:
            return None
        # Pick the first result
        first = items[0]
        return first.get('id', {}).get('channelId')
    except Exception:
        return None

def get_channel_details_by_handle(handle):
    """Get detailed information about a channel by handle via channelId resolution."""
    channel_id = resolve_handle_to_channel_id(handle)
    if not channel_id:
        return None
    return get_channel_details(channel_id)

def get_channel_playlists(channel_id, page_token=None, max_results=20):
    """Get playlists from a channel."""
    global current_key_index
    current_key_index = 0  # Reset for each new request

    while True:
        api_key = get_next_api_key()
        if not api_key:
            xbmc.log('All API keys failed.', xbmc.LOGERROR)
            return None

        search_url = 'https://www.googleapis.com/youtube/v3/playlists'
        params = {
            'part': 'snippet',
            'channelId': channel_id,
            'maxResults': max_results,
            'key': api_key
        }
        if page_token:
            params['pageToken'] = page_token

        try:
            response = _requests_get(search_url, params=params)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            xbmc.log(f'Error getting channel playlists: {str(e)}', xbmc.LOGWARNING)
            if _should_rotate_key(e):
                continue
            return None


def get_user_playlists(username, page_token=None, max_results=20):
    """Get playlists from a user's channel."""
    # First, get the channel ID for the username
    channel_data = get_channel_details_by_username(username)
    if not channel_data or 'items' not in channel_data or not channel_data['items']:
        xbmc.log(f'Could not find channel for username {username}', xbmc.LOGERROR)
        return None
        
    channel_id = channel_data['items'][0]['id']
    return get_channel_playlists(channel_id, page_token, max_results)


def get_playlist_videos(playlist_id, page_token=None, max_results=20):
    """Get videos from a playlist."""
    global current_key_index
    current_key_index = 0  # Reset for each new request

    while True:
        api_key = get_next_api_key()
        if not api_key:
            xbmc.log('All API keys failed.', xbmc.LOGERROR)
            return None

        playlist_items_url = 'https://www.googleapis.com/youtube/v3/playlistItems'
        params = {
            'part': 'snippet',
            'playlistId': playlist_id,
            'maxResults': max_results,
            'key': api_key
        }
        if page_token:
            params['pageToken'] = page_token

        try:
            response = _requests_get(playlist_items_url, params=params)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            xbmc.log(f'Error getting playlist videos: {str(e)}', xbmc.LOGWARNING)
            if _should_rotate_key(e):
                continue
            return None

def get_channel_videos(channel_id, page_token=None, max_results=20):
    """Get videos from a channel."""
    global current_key_index
    current_key_index = 0

    while True:
        api_key = get_next_api_key()
        if not api_key:
            xbmc.log('All API keys failed.', xbmc.LOGERROR)
            return None

        search_url = 'https://www.googleapis.com/youtube/v3/channels'
        params = {
            'part': 'contentDetails',
            'id': channel_id,
            'key': api_key
        }
        try:
            response = _requests_get(search_url, params=params)
            response.raise_for_status()
            data = response.json()
            uploads_playlist_id = data['items'][0]['contentDetails']['relatedPlaylists']['uploads']
            return get_playlist_videos(uploads_playlist_id, page_token, max_results)
        except requests.exceptions.RequestException as e:
            xbmc.log(f'Error getting channel uploads playlist: {str(e)}', xbmc.LOGWARNING)
            if _should_rotate_key(e):
                continue
            return None
        except (IndexError, KeyError):
            xbmc.log(f'Could not find uploads playlist for channel {channel_id}', xbmc.LOGERROR)
            return None

def get_user_videos(username, page_token=None, max_results=20):
    """Get videos from a user's channel by username."""
    global current_key_index
    current_key_index = 0

    while True:
        api_key = get_next_api_key()
        if not api_key:
            xbmc.log('All API keys failed.', xbmc.LOGERROR)
            return None

        search_url = 'https://www.googleapis.com/youtube/v3/channels'
        params = {
            'part': 'contentDetails',
            'forUsername': username,
            'key': api_key
        }
        try:
            response = _requests_get(search_url, params=params)
            response.raise_for_status()
            data = response.json()
            if not data.get('items'):
                xbmc.log(f'Could not find channel for username {username}', xbmc.LOGERROR)
                return None
            uploads_playlist_id = data['items'][0]['contentDetails']['relatedPlaylists']['uploads']
            return get_playlist_videos(uploads_playlist_id, page_token, max_results)
        except requests.exceptions.RequestException as e:
            xbmc.log(f'Error getting channel for username: {str(e)}', xbmc.LOGWARNING)
            if _should_rotate_key(e):
                continue
            return None
        except (IndexError, KeyError):
            xbmc.log(f'Could not find uploads playlist for user {username}', xbmc.LOGERROR)
            return None

def get_user_videos_by_handle(handle, page_token=None, max_results=20):
    """Get videos from a user's channel by handle using search resolution."""
    channel_id = resolve_handle_to_channel_id(handle)
    if not channel_id:
        xbmc.log(f'Could not resolve handle {handle} to channel ID', xbmc.LOGERROR)
        return None
    return get_channel_videos(channel_id, page_token, max_results)


def get_user_playlists_by_handle(handle, page_token=None, max_results=20):
    """Get playlists from a user's channel by handle using search resolution."""
    channel_id = resolve_handle_to_channel_id(handle)
    if not channel_id:
        xbmc.log(f'Could not resolve handle {handle} to channel ID', xbmc.LOGERROR)
        return None
    return get_channel_playlists(channel_id, page_token, max_results)


def parse_duration_to_seconds(duration):
    """Convert YouTube duration format (PT#H#M#S) to seconds."""
    import re
    hours = 0
    minutes = 0
    seconds = 0
    
    # Using regex to find hours, minutes, and seconds
    match = re.match(r'PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?', duration)
    if not match:
        return 0
        
    parts = match.groups()
    if parts[0]:
        hours = int(parts[0])
    if parts[1]:
        minutes = int(parts[1])
    if parts[2]:
        seconds = int(parts[2])
        
    return hours * 3600 + minutes * 60 + seconds
