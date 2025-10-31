import xbmc
import xbmcvfs
import json
import time
import os
import xbmcaddon
import hashlib

def get_cache_duration():
    """Get cache duration from settings (in seconds)."""
    addon = xbmcaddon.Addon()
    cache_setting = addon.getSetting('cache_duration')
    
    # Default to 5 minutes if setting not found
    if not cache_setting or not cache_setting.isdigit():
        return 300  # 5 minutes
    
    # Convert setting index to seconds
    # 0: 5 minutes, 1: 10 minutes, 2: 15 minutes, 3: 30 minutes, 4: 1 hour
    cache_durations = [300, 600, 900, 1800, 3600]
    index = int(cache_setting)
    
    if 0 <= index < len(cache_durations):
        return cache_durations[index]
    else:
        return 300  # Default to 5 minutes

def get_cache_path():
    """Get the cache directory path for the addon."""
    profile_path = xbmcvfs.translatePath(xbmcaddon.Addon().getAddonInfo('profile'))
    cache_path = os.path.join(profile_path, 'cache')
    
    # Create cache directory if it doesn't exist
    if not xbmcvfs.exists(cache_path):
        xbmcvfs.mkdirs(cache_path)
    
    return cache_path

def get_cache_filename(query):
    """Generate a cache filename based on the query."""
    query_hash = hashlib.md5(query.encode('utf-8')).hexdigest()
    return os.path.join(get_cache_path(), f"{query_hash}.json")

def get_cached_results(query):
    """Get cached search results if they exist and are not expired."""
    cache_file = get_cache_filename(query)
    
    if xbmcvfs.exists(cache_file):
        try:
            # Get file modification time
            mod_time = xbmcvfs.Stat(cache_file).st_mtime()
            current_time = time.time()
            
            # Check if cache is still valid based on settings
            cache_duration = get_cache_duration()
            if current_time - mod_time < cache_duration:
                with xbmcvfs.File(cache_file, 'r') as f:
                    content = f.read()
                return json.loads(content.decode('utf-8'))
        except Exception as e:
            xbmc.log(f'Error reading cache for {query}: {str(e)}', xbmc.LOGERROR)
    
    return None

def save_cached_results(query, results):
    """Save search results to cache."""
    cache_file = get_cache_filename(query)
    
    try:
        with xbmcvfs.File(cache_file, 'w') as f:
            f.write(json.dumps(results).encode('utf-8'))
    except Exception as e:
        xbmc.log(f'Error saving cache for {query}: {str(e)}', xbmc.LOGERROR)

def get_cached_json(key, namespace='generic'):
    """Get cached JSON by key within a namespace."""
    composite = f"{namespace}:{key}"
    cache_file = get_cache_filename(composite)
    if xbmcvfs.exists(cache_file):
        try:
            mod_time = xbmcvfs.Stat(cache_file).st_mtime()
            current_time = time.time()
            cache_duration = get_cache_duration()
            if current_time - mod_time < cache_duration:
                with xbmcvfs.File(cache_file, 'r') as f:
                    content = f.read()
                return json.loads(content.decode('utf-8'))
        except Exception as e:
            xbmc.log(f'Error reading cache for {composite}: {str(e)}', xbmc.LOGERROR)
    return None

def save_cached_json(key, data, namespace='generic'):
    """Save generic JSON under a namespace+key."""
    composite = f"{namespace}:{key}"
    cache_file = get_cache_filename(composite)
    try:
        with xbmcvfs.File(cache_file, 'w') as f:
            f.write(json.dumps(data).encode('utf-8'))
    except Exception as e:
        xbmc.log(f'Error saving cache for {composite}: {str(e)}', xbmc.LOGERROR)
