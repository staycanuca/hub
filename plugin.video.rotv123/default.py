import sys
import os
import urllib.parse
import xbmcgui
import xbmcplugin
import xbmc
import xbmcvfs
import xbmcaddon
from datetime import datetime

# Adaugam calea pentru modulele noastre
ADDON = xbmcaddon.Addon()
ADDON_DIR = xbmcvfs.translatePath(ADDON.getAddonInfo('path'))
sys.path.append(os.path.join(ADDON_DIR, 'resources', 'lib'))

import scraper

# Constante Plugin
URL = sys.argv[0]
HANDLE = int(sys.argv[1])
BASE_URL = scraper.BASE_URL # Folosim constanta din scraper
EPG_SOURCE_XML = 'https://www.open-epg.com/files/romania1.xml'

_EPG_CACHE = {}

def clean_name(text):
    """Normalizeaza numele pentru a face match intre site si EPG"""
    import re
    if not text: return ""
    text = text.lower()
    text = re.sub(r'\.ro|\.com|\.tv|hd|sd|fhd|romania|online', '', text)
    text = re.sub(r'[^a-z0-9]', '', text)
    return text.strip()

def load_epg():
    """Citeste EPG-ul din GitHub si gaseste emisiunea de la ora curenta"""
    global _EPG_CACHE
    if _EPG_CACHE: return _EPG_CACHE
    
    # Importam re aici sau sus
    import re

    xbmc.log("Rotv123: Citire EPG din GitHub...", xbmc.LOGINFO)
    data = scraper.get_data(EPG_SOURCE_XML)
    if not data: return {}

    try:
        # data vine deja decodat din scraper.get_data (string), dar verificam
        if isinstance(data, bytes):
            xml = data.decode('utf-8', errors='ignore')
        else:
            xml = data
            
        now_str = datetime.utcnow().strftime('%Y%m%d%H%M%S')
        pattern = re.compile(r'<programme start="([^"]+)" stop="([^"]+)" channel="([^"]+)">.*?<title[^>]*>([^<]+)</title>', re.DOTALL)
        
        for start, stop, channel, title in pattern.findall(xml):
            if start[:14] <= now_str <= stop[:14]:
                key = clean_name(channel)
                _EPG_CACHE[key] = title
    except Exception as e:
        xbmc.log(f"Rotv123 EPG Error: {str(e)}", xbmc.LOGERROR)
    
    return _EPG_CACHE

def main_menu():
    import re
    data = scraper.get_data(BASE_URL)
    if not data: return
    html = data
    xbmcplugin.setContent(HANDLE, 'genres')
    
    pattern = re.compile(r'href="([^"]*categoria\.php\?cat=[^"]*)"[^>]*class="[^"]*main-category[^"]*"[^>]*>.*?category-title">([^<]+)</div>', re.DOTALL)
    for link, title in pattern.findall(html):
        url = build_url({'mode': 'category', 'url': link})
        list_item = xbmcgui.ListItem(label=title.strip())
        list_item.setArt({'icon': 'DefaultVideoPlaylists.png'})
        xbmcplugin.addDirectoryItem(handle=HANDLE, url=url, listitem=list_item, isFolder=True)
    xbmcplugin.endOfDirectory(HANDLE)

def list_category(category_url):
    import re
    data = scraper.get_data(category_url)
    if not data: return
    html = data
    
    epg_data = load_epg()
    xbmcplugin.setContent(HANDLE, 'videos')
    
    blocks = re.findall(r'<a[^>]+class="channel-card"[^>]*>.*?</a>', html, re.DOTALL)
    for block in blocks:
        name_m = re.search(r'class="channel-name">([^<]+)</span>', block)
        link_m = re.search(r'href="([^"]+)"', block)
        img_m = re.search(r'src="([^"]+)"', block)
        
        if name_m and link_m:
            name = name_m.group(1).strip()
            link = link_m.group(1)
            
            key = clean_name(name)
            program = epg_data.get(key, "")
            
            if not program:
                for k, v in epg_data.items():
                    if k in key or key in k:
                        program = v
                        break

            logo_orig = urllib.parse.urljoin(BASE_URL, img_m.group(1)) if img_m else ""
            clean_img = logo_orig.replace('https://', '').replace('http://', '')
            poster = f"https://images.weserv.nl/?url={clean_img}&w=320&h=450&fit=contain&bg=transparent"
            
            label = name
            if program:
                label = f"{name} [COLOR gold]• {program}[/COLOR]"

            url = build_url({'mode': 'play', 'url': link, 'name': name, 'logo': poster})
            list_item = xbmcgui.ListItem(label=label)
            list_item.setArt({'thumb': poster, 'icon': poster, 'poster': poster})
            list_item.setInfo('video', {'title': name, 'plot': program if program else "Fara EPG"})
            list_item.setProperty('IsPlayable', 'true')
            xbmcplugin.addDirectoryItem(handle=HANDLE, url=url, listitem=list_item, isFolder=False)
            
    xbmcplugin.endOfDirectory(HANDLE)

def play_video(video_url, name, logo):
    # 1. Obtinem lista de stream-uri disponibile
    streams = scraper.get_all_streams(video_url)
    
    selected_label = None
    
    if len(streams) > 1:
        # Formatam etichetele pentru utilizator
        labels = [s[0] for s in streams]
        idx = xbmcgui.Dialog().select(f"Alege sursa pentru {name}", labels)
        
        if idx > -1:
            # Luam raw_label al stream-ului selectat
            # streams[idx] = (Pretty Label, URL, Raw Label)
            selected_label = streams[idx][2]
        else:
            # Utilizatorul a anulat dialogul
            return
    elif streams:
        # Doar un stream, il luam pe acela (optional putem trimite label-ul pt consistenta)
        selected_label = streams[0][2]

    # 2. Construim URL-ul catre PROXY
    # Citim portul dinamic setat de service.py
    port = xbmcgui.Window(10000).getProperty('rotv123.proxy_port')
    if not port:
        port = "12345" # Fallback in caz ca service-ul nu a pornit inca
        
    proxy_base = f"http://127.0.0.1:{port}/play"
    
    # URL encoding pentru video_url
    params = {'url': video_url}
    if selected_label:
        params['label'] = selected_label
        
    query_string = urllib.parse.urlencode(params)
    proxy_url = f"{proxy_base}?{query_string}"
    
    xbmc.log(f"Rotv123: Redirecting play to proxy {proxy_url}", xbmc.LOGINFO)
    
    play_item = xbmcgui.ListItem(label=name)
    if logo: play_item.setArt({'thumb': logo, 'icon': logo})
    play_item.setPath(proxy_url)
    
    xbmcplugin.setResolvedUrl(HANDLE, True, listitem=play_item)

def build_url(query):
    return URL + '?' + urllib.parse.urlencode(query)

def router(param_string):
    params = dict(urllib.parse.parse_qsl(param_string))
    mode = params.get('mode')
    if mode == 'category': list_category(params.get('url'))
    elif mode == 'play': play_video(params.get('url'), params.get('name'), params.get('logo'))
    else: main_menu()

if __name__ == '__main__':
    router(sys.argv[2][1:])
