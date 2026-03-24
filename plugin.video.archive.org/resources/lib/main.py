"""
    Internet Archive Kodi Addon
    Copyright (C) 2024 gujal

    This program is free software: you can redistribute and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation, either version 2 of the License, or
    (at your option) any later version.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with this program.  If not, see <http://www.gnu.org/licenses/>.
"""

import json
import random
import re
import sys
import urllib.parse
import xbmc
import xbmcgui
import xbmcplugin
import xbmcaddon
import xbmcvfs
from html import unescape
from resources.lib import client, cache

_addon = xbmcaddon.Addon()
_addonID = _addon.getAddonInfo('id')
_plugin = _addon.getAddonInfo('name')
_version = _addon.getAddonInfo('version')
_icon = _addon.getAddonInfo('icon')
_fanart = _addon.getAddonInfo('fanart')
_language = _addon.getLocalizedString
_settings = _addon.getSetting
_addonpath = 'special://profile/addon_data/{}/'.format(_addonID)
_kodiver = float(xbmcaddon.Addon('xbmc.addon').getAddonInfo('version')[:4])
# DEBUG
DEBUG = _settings("DebugMode") == "true"

if not xbmcvfs.exists(_addonpath):
    xbmcvfs.mkdir(_addonpath)

cache_duration = int(_settings('timeout'))

if not xbmcvfs.exists(_addonpath + 'settings.xml'):
    _addon.openSettings()


# --- CONSTANTS & CONFIGURATION ---
BASE_URL = 'https://archive.org/'
ADVANCED_SEARCH_URL = BASE_URL + 'advancedsearch.php'
IMG_PATH = BASE_URL + 'services/img/'

# Defined Categories with their specific queries
MENU_STRUCTURE = [
    {
        'title': '[B]Video Library[/B]',
        'type': 'folder',
        'items': [
                        {'title': 'Feature Films', 'query': 'mediatype:movies AND collection:feature_films', 'content_type': 'video'},
                        {'title': 'Short Films', 'query': 'mediatype:movies AND collection:short_films', 'content_type': 'video'},
                        {'title': 'Animation & Cartoons', 'query': 'mediatype:movies AND collection:animationandcartoons', 'content_type': 'video'},
                        {'title': 'Silent Films', 'query': 'mediatype:movies AND collection:silent_films', 'content_type': 'video'},
                        {'title': 'Television', 'query': 'mediatype:movies AND collection:television', 'content_type': 'video'},
                        {'title': 'Music Videos', 'query': 'mediatype:movies AND subject:"music video"', 'content_type': 'video'},
                        {'title': 'Sci-Fi / Horror', 'query': 'mediatype:movies AND (subject:"sci-fi" OR subject:"horror")', 'content_type': 'video'},
                        {'title': 'Film Noir', 'query': 'mediatype:movies AND subject:"film noir"', 'content_type': 'video'},
        ]
    },
    {
        'title': '[B]Audio Library[/B]',
        'type': 'folder',
        'items': [
            {'title': 'Live Music Archive', 'query': 'mediatype:etree AND collection:etree', 'content_type': 'audio'},
            {'title': 'Audio Books & Poetry', 'query': 'mediatype:audio AND collection:audio_bookspoetry', 'content_type': 'audio'},
            {'title': 'Old Time Radio', 'query': 'mediatype:audio AND collection:radioprograms', 'content_type': 'audio'},
            {'title': '78 RPMs & Cylinder Recordings', 'query': 'mediatype:audio AND collection:78rpm', 'content_type': 'audio'},
            {'title': 'Grateful Dead', 'query': 'collection:GratefulDead', 'content_type': 'audio'},
            {'title': 'Podcasts', 'query': 'mediatype:audio AND collection:podcasts', 'content_type': 'audio'},
        ]
    },
    {
        'title': '[B]Search Archive.org[/B]',
        'type': 'action',
        'action': 'search_menu',
        'is_folder': True
    },
    {
        'title': 'Clear Cache',
        'type': 'action',
        'action': 'clear_cache',
        'is_folder': False
    }
]

SORT_OPTIONS = [
    {'title': 'Most Popular (Downloads)', 'sort': 'downloads desc'},
    {'title': 'Most Recent (Date Added)', 'sort': 'publicdate desc'},
    {'title': 'Oldest (Date Added)', 'sort': 'publicdate asc'},
    {'title': 'Highest Rated', 'sort': 'avg_rating desc'},
    {'title': 'Alphabetical (A-Z)', 'sort': 'titleSorter asc'},
    {'title': 'Date Published (Newest)', 'sort': 'date desc'},
]


class Main(object):
    def __init__(self):
        self.headers = {'Referer': BASE_URL}
        
        # Parse arguments
        args = urllib.parse.parse_qs(sys.argv[2][1:])
        action = args.get('action', [None])[0]
        
        # Route actions
        if action is None:
            self.main_menu()
        elif action == 'browse_folder':
            folder_idx = int(args.get('index', ['0'])[0])
            self.browse_folder(folder_idx)
        elif action == 'sort_menu':
            query = args.get('query', [''])[0]
            content_type = args.get('content_type', ['video'])[0]
            self.sort_menu(query, content_type)
        elif action == 'list_content':
            query = args.get('query', [''])[0]
            sort = args.get('sort', ['downloads desc'])[0]
            page = int(args.get('page', ['1'])[0])
            content_type = args.get('content_type', ['video'])[0]
            self.list_content(query, sort, page, content_type)
        elif action == 'play':
            item_id = args.get('target', [''])[0]
            content_type = args.get('content_type', ['video'])[0]
            self.play(item_id, content_type)
        elif action == 'search_menu':
            self.search_menu()
        elif action == 'perform_search':
            keyword = args.get('keyword', [''])[0]
            self.sort_menu(keyword, 'video', is_search=True)
        elif action == 'clear_cache':
            self.clear_cache()

    def main_menu(self):
        if DEBUG:
            self.log('main_menu')
        
        for idx, item in enumerate(MENU_STRUCTURE):
            listitem = xbmcgui.ListItem(item['title'])
            listitem.setArt({'thumb': _icon, 'fanart': _fanart, 'icon': _icon})
            
            if item['type'] == 'folder':
                url = self.build_url({'action': 'browse_folder', 'index': idx})
                xbmcplugin.addDirectoryItem(int(sys.argv[1]), url, listitem, True)
            elif item['type'] == 'action':
                url = self.build_url({'action': item['action']})
                is_folder = item.get('is_folder', False)
                xbmcplugin.addDirectoryItem(int(sys.argv[1]), url, listitem, is_folder)

        xbmcplugin.setContent(int(sys.argv[1]), 'addons')
        xbmcplugin.endOfDirectory(int(sys.argv[1]), True)

    def browse_folder(self, index):
        if DEBUG:
            self.log('browse_folder({})'.format(index))
        
        category = MENU_STRUCTURE[index]
        for item in category['items']:
            listitem = xbmcgui.ListItem(item['title'])
            listitem.setArt({'thumb': _icon, 'fanart': _fanart, 'icon': _icon})
            
            # Go to Sort Menu first
            url = self.build_url({
                'action': 'sort_menu',
                'query': item['query'],
                'content_type': item.get('content_type', 'video')
            })
            xbmcplugin.addDirectoryItem(int(sys.argv[1]), url, listitem, True)
            
        xbmcplugin.endOfDirectory(int(sys.argv[1]), True)

    def sort_menu(self, query, content_type, is_search=False):
        if DEBUG:
            self.log('sort_menu query="{}"'.format(query))
        
        # If it's a search, construct the query properly
        final_query = query
        if is_search:
            # Search in title, description, creator AND ensure playable media types
            # Strip quotes to prevent syntax errors, wrapped in query
            safe_kw = query.replace('"', '')
            base_query = '(title:"{0}" OR description:"{0}" OR creator:"{0}")'.format(safe_kw)
            # Filter for video and audio types supported by Kodi
            media_filter = ' AND (mediatype:movies OR mediatype:audio OR mediatype:etree)'
            final_query = base_query + media_filter

        for option in SORT_OPTIONS:
            listitem = xbmcgui.ListItem(option['title'])
            listitem.setArt({'thumb': _icon, 'fanart': _fanart, 'icon': _icon})
            
            url = self.build_url({
                'action': 'list_content',
                'query': final_query,
                'sort': option['sort'],
                'page': 1,
                'content_type': content_type
            })
            xbmcplugin.addDirectoryItem(int(sys.argv[1]), url, listitem, True)
            
        xbmcplugin.endOfDirectory(int(sys.argv[1]), True)

    def list_content(self, query, sort, page, content_type):
        if DEBUG:
            self.log('list_content q="{}" s="{}" p={}'.format(query, sort, page))

        # Use cache for API calls
        data = cache.get(self.get_advanced_items, cache_duration, query, sort, page)
        
        items_list = []
        
        if data:
            items = data.get('response', {}).get('docs', [])
            total_found = int(data.get('response', {}).get('numFound', 0))
            
            for item in items:
                identifier = item.get('identifier')
                if not identifier:
                    continue

                title = item.get('title', identifier)
                if isinstance(title, list): title = title[0]
                
                plot = item.get('description', '')
                if isinstance(plot, list): plot = plot[0]
                if plot: plot = unescape(plot)[:500] # Limit plot length
                
                thumb = IMG_PATH + identifier
                
                # Determine specific content type for this item
                item_mediatype = item.get('mediatype', '')
                if item_mediatype == 'movies':
                    item_type = 'video'
                elif item_mediatype in ['audio', 'etree']:
                    item_type = 'audio'
                else:
                    item_type = content_type # Fallback to the category default
                
                labels = {
                    'title': title,
                    'plot': plot,
                    'mediatype': 'video' if item_type == 'video' else 'music'
                }
                
                # Add extra info
                if 'downloads' in item:
                    labels['code'] = 'Downloads: {:,}'.format(item['downloads'])
                if 'year' in item:
                    labels['year'] = int(item['year']) if str(item['year']).isdigit() else 0
                
                listitem = self.make_listitem(labels, item_type)
                listitem.setArt({
                    'icon': thumb,
                    'thumb': thumb,
                    'fanart': _fanart
                })
                listitem.setProperty('IsPlayable', 'true')
                
                url = self.build_url({
                    'action': 'play',
                    'target': identifier,
                    'content_type': item_type
                })
                items_list.append((url, listitem, False))

            # Pagination
            rows = 30
            if page * rows < total_found:
                next_page = page + 1
                label = '[COLOR lime]Next Page >>[/COLOR] ({}/{})'.format(next_page, (total_found // rows) + 1)
                listitem = xbmcgui.ListItem(label)
                listitem.setArt({'icon': _icon, 'thumb': _icon})
                
                url = self.build_url({
                    'action': 'list_content',
                    'query': query,
                    'sort': sort,
                    'page': next_page,
                    'content_type': content_type
                })
                items_list.append((url, listitem, True))

            xbmcplugin.setContent(int(sys.argv[1]), 'videos' if content_type == 'video' else 'songs')
            xbmcplugin.addDirectoryItems(int(sys.argv[1]), items_list)
            xbmcplugin.endOfDirectory(int(sys.argv[1]), cacheToDisc=True)

    def get_advanced_items(self, query, sort, page):
        # Build the Advanced Search URL
        rows = 30
        params = {
            'q': query,
            'sort[]': sort,
            'rows': rows,
            'page': page,
            'output': 'json',
            'fl[]': ['identifier', 'title', 'description', 'downloads', 'year', 'mediatype', 'format'],
        }
        
        # Manually encode to handle lists correctly (doseq=True)
        # client.request handles dicts without doseq=True by default which breaks lists
        encoded_params = urllib.parse.urlencode(params, doseq=True)
        
        if DEBUG:
            self.log('Requesting: {}?{}'.format(ADVANCED_SEARCH_URL, encoded_params))

        return client.request(ADVANCED_SEARCH_URL, params=encoded_params)

    def search_menu(self):
        keyboard = xbmc.Keyboard()
        keyboard.setHeading("Search Archive.org")
        keyboard.doModal()
        if keyboard.isConfirmed():
            search_text = keyboard.getText()
            if len(search_text) > 0: # Changed from > 1 to > 0 to allow single char searches if needed
                self.sort_menu(search_text, 'video', is_search=True)
            else:
                xbmcgui.Dialog().notification(_plugin, "Search too short", _icon)

    def play(self, item_id, content_type):
        if DEBUG:
            self.log('play("{}") {}'.format(item_id, content_type))

        # Metadata API
        url = BASE_URL + 'metadata/' + item_id
        jd = client.request(url)

        if not jd or not isinstance(jd, dict):
            xbmcgui.Dialog().notification(_plugin, "Could not get metadata", _icon)
            return

        files = jd.get('files', [])
        workable_servers = jd.get('workable_servers', [])
        if not workable_servers:
            if jd.get('d1'):
                workable_servers.append(jd.get('d1'))

        if not workable_servers:
            xbmcgui.Dialog().notification(_plugin, "No servers found", _icon)
            return

        # Optimize: Prefer direct servers (starting with 'ia') over 'd1', 'd2' to avoid redirects
        workable_servers.sort(key=lambda s: 0 if s.startswith('ia') else 1)
        
        directory = jd.get('dir')
        server = workable_servers[0] # Pick the best one directly

        if content_type == 'video':
            self.play_video(files, server, directory, item_id)
        elif content_type == 'audio':
            self.play_audio(files, server, directory, content_type)

    def play_video(self, files, server, directory, item_id):
        def is_video(f):
            name = f.get('name', '').lower()
            fmt = f.get('format', '').lower()
            
            # Exclude non-video files
            if any(name.endswith(ext) for ext in ['.jpg', '.png', '.gif', '.thumb', '.xml', '.txt', '.nfo', '.srt', '.torrent', '.sqlite']):
                return False
            if 'image' in fmt or 'metadata' in fmt or 'torrent' in fmt:
                return False
            
            # Check for video metadata
            if f.get('height'):
                return True
            
            # Check for video formats (including old formats)
            video_formats = ['mpeg', 'h.264', 'h264', 'mpeg4', 'cinepak', 'theora', 'vp8', 'vp9', 'av1']
            if any(vf in fmt for vf in video_formats):
                return True
            
            # Check file extensions (including old formats)
            video_extensions = ['.mp4', '.avi', '.mkv', '.mov', '.mpg', '.mpeg', '.m4v', '.flv', '.wmv', '.ogv', '.webm', '.3gp', '.divx']
            if any(name.endswith(ext) for ext in video_extensions):
                return True
            
            return False

        sources = [i for i in files if is_video(i)]

        if not sources:
            if DEBUG:
                self.log('No video sources found in {} files'.format(len(files)))
            xbmcgui.Dialog().notification(_plugin, "No video sources found", _icon, 3000)
            xbmcplugin.setResolvedUrl(int(sys.argv[1]), False, xbmcgui.ListItem())
            return

        # Sort by resolution, then by 'original', then by size
        sources.sort(key=lambda item: (
            int(item.get('height', 0) or 0),
            1 if item.get('source') == 'original' else 0,
            int(item.get('size', 0) or 0)
        ), reverse=True)

        # Auto-select the best quality to speed up start
        selected = sources[0]
        
        if DEBUG:
            self.log('Playing: {} (format: {})'.format(selected.get('name'), selected.get('format')))

        surl = 'https://{0}{1}/{2}'.format(server, directory, urllib.parse.quote(selected.get('name')))

        li = xbmcgui.ListItem(item_id)
        li.setPath(surl)
        li.setContentLookup(False) # Faster resolving
        
        # Set MIME type based on file format for faster streaming
        fmt = selected.get('format', '').lower()
        name = selected.get('name', '').lower()
        
        # Modern formats
        if 'mp4' in fmt or 'h.264' in fmt or 'h264' in fmt or 'mpeg4' in fmt or name.endswith('.mp4'):
            li.setMimeType('video/mp4')
        elif 'webm' in fmt or name.endswith('.webm'):
            li.setMimeType('video/webm')
        elif 'mkv' in fmt or name.endswith('.mkv'):
            li.setMimeType('video/x-matroska')
        # Legacy formats for old films
        elif 'mpeg' in fmt or name.endswith(('.mpg', '.mpeg')):
            li.setMimeType('video/mpeg')
        elif 'avi' in fmt or name.endswith('.avi'):
            li.setMimeType('video/x-msvideo')
        elif 'ogv' in fmt or 'theora' in fmt or name.endswith('.ogv'):
            li.setMimeType('video/ogg')
        elif name.endswith('.mov'):
            li.setMimeType('video/quicktime')
        
        xbmcplugin.setResolvedUrl(int(sys.argv[1]), True, listitem=li)

    def play_audio(self, files, server, directory, content_type):
        def is_audio(f):
            fmt = f.get('format', '').lower()
            if any(x in fmt for x in ['mp3', 'ogg', 'flac', 'wav', 'aac', 'm4a']):
                return True
            if f.get('length') and not f.get('height'):
                return True
            return False

        def get_fmt_score(f):
            # Lower is better
            fmt = f.get('format', '').lower()
            if 'mp3' in fmt: return 1
            if 'aac' in fmt or 'm4a' in fmt: return 2
            if 'flac' in fmt: return 3
            if 'ogg' in fmt: return 4 # OGG caused timeouts
            return 5

        def get_track_num(f):
            t = f.get('track')
            if not t: return 9999
            try:
                if isinstance(t, str) and '/' in t:
                    t = t.split('/')[0]
                # Filter out non-digit chars if any (e.g. "A1")
                if isinstance(t, str):
                    t = ''.join(filter(str.isdigit, t))
                return int(t)
            except:
                return 9999

        sources = [i for i in files if is_audio(i)]
        
        # Sort by Track, then Title, then Format Score (Best format first)
        sources.sort(key=lambda x: (
            get_track_num(x), 
            x.get('title', x.get('name')),
            get_fmt_score(x)
        ))

        if not sources:
            xbmcgui.Dialog().notification(_plugin, "No audio sources found", _icon)
            return

        playlist = xbmc.PlayList(xbmc.PLAYLIST_MUSIC)
        playlist.clear()

        seen_tracks = set()
        count = 0

        for i in sources:
            # Deduplicate logic
            t_num = get_track_num(i)
            t_title = i.get('title', i.get('name'))
            # Normalize title (strip extension if it's a filename)
            if t_title == i.get('name'):
                 t_title = t_title.rsplit('.', 1)[0]
            
            uid = (t_num, t_title)
            if uid in seen_tracks:
                continue
            seen_tracks.add(uid)
            count += 1
            
            # Limit playlist size to prevent timeouts on huge collections
            if count > 50:
                break

            title = i.get('title', i.get('name'))
            if title == i.get('name'):
                title = title.replace('_', ' ').replace('.mp3', '').replace('.ogg', '')
            
            url = 'https://{0}{1}/{2}'.format(server, directory, urllib.parse.quote(i.get('name')))
            li = xbmcgui.ListItem(title)
            li.setInfo(type='music', infoLabels={'title': title, 'artist': i.get('creator', 'Archive.org')})
            
            # Set MIME type for faster audio streaming
            fmt = i.get('format', '').lower()
            if 'mp3' in fmt:
                li.setMimeType('audio/mpeg')
            elif 'flac' in fmt:
                li.setMimeType('audio/flac')
            elif 'ogg' in fmt:
                li.setMimeType('audio/ogg')
            elif 'aac' in fmt or 'm4a' in fmt:
                li.setMimeType('audio/aac')
            
            playlist.add(url=url, listitem=li)

        xbmcgui.Dialog().notification(_plugin, "Playing {} tracks".format(count), _icon)
        xbmc.Player().play(playlist)

    def clear_cache(self):
        cache.cache_clear()
        xbmcgui.Dialog().notification(_plugin, "Cache Cleared", _icon)

    def build_url(self, query):
        return sys.argv[0] + '?' + urllib.parse.urlencode(query)

    def format_bytes(self, size):
        n = 0
        slabels = {0: 'B', 1: 'KB', 2: 'MB', 3: 'GB', 4: 'TB'}
        while size > 1024:
            size /= 1024
            n += 1
        return '{0:.2f} {1}'.format(size, slabels[n])

    def make_listitem(self, labels, content_type):
        li = xbmcgui.ListItem(labels.get('title'))
        # Standard InfoTag setting for Kodi 19+
        if _kodiver > 18.9:
            vtag = li.getVideoInfoTag() if content_type == 'video' else li.getMusicInfoTag()
            vtag.setTitle(labels.get('title'))
            
            if labels.get('plot'):
                if content_type == 'video':
                    vtag.setPlot(labels.get('plot'))
                else:
                    vtag.setComment(labels.get('plot'))
                    
            if labels.get('year'):
                vtag.setYear(labels.get('year'))
        else:
            li.setInfo(type='video' if content_type == 'video' else 'music', infoLabels=labels)
        return li

    def log(self, description):
        xbmc.log("[ADD-ON] '{} v{}': {}".format(_plugin, _version, description), xbmc.LOGINFO)

if __name__ == '__main__':
    Main()