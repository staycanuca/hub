
import sys
import re
import json
import base64
import traceback
from urllib.parse import quote_plus, urlparse
import xbmc
import xbmcgui
import xbmcplugin
from bs4 import BeautifulSoup

from . import ddlv_provider  # Pentru a refolosi funcția de request și User-Agent
from . import kodi_utils     # Pentru a afișa dialoguri
from .modules.common import ownAddon

ADDON_ICON = ownAddon.getAddonInfo('icon')
ADDON_HANDLE = int(sys.argv[1])

def play_video(item: dict):
    """
    Funcția principală pentru redarea unui video.
    Preia datele item-ului, extrage link-ul M3U8 și îl redă.
    """
    links_data = item.get("link", "")
    title = item.get("title", "Stream")

    if not links_data:
        kodi_utils.show_ok_dialog("Nu s-a găsit niciun link pentru acest item.", "Eroare")
        return

    # Link-ul este un JSON string, trebuie să-l parsăm
    links = json.loads(links_data)

    # Dacă există mai multe link-uri, afișăm un dialog de selecție
    if isinstance(links, list) and len(links) > 1:
        labels = [link[0] for link in links]
        choice = kodi_utils.show_select_dialog(labels, title="Alege un stream")
        if choice == -1:
            return # Utilizatorul a anulat
        final_url = links[choice][1]
    elif isinstance(links, list) and len(links) == 1:
        final_url = links[0][1]
    else:
        kodi_utils.show_ok_dialog(f"Format de link necunoscut: {links_data}", "Eroare")
        return

    try:
        # Obține stream-ul M3U8
        m3u8_url = _resolve_stream(final_url)
        if not m3u8_url:
            raise ValueError("Extragerea link-ului M3U8 a eșuat.")

        # Creează ListItem pentru player
        liz = xbmcgui.ListItem(title, path=m3u8_url)
        liz.setInfo('video', {'title': title, 'plot': title})
        liz.setArt({'icon': ADDON_ICON, 'thumb': ADDON_ICON})
        liz.setProperty('inputstream', 'inputstream.ffmpegdirect')
        liz.setMimeType('application/x-mpegURL')
        liz.setProperty('inputstream.ffmpegdirect.is_realtime_stream', 'true')
        liz.setProperty('inputstream.ffmpegdirect.stream_mode', 'timeshift')
        liz.setProperty('inputstream.ffmpegdirect.manifest_type', 'hls')

        # Setează URL-ul rezolvat și pornește redarea
        xbmcplugin.setResolvedUrl(ADDON_HANDLE, True, liz)
        
    except Exception as e:
        error_details = traceback.format_exc()
        kodi_utils.show_ok_dialog(f"Eroare la încărcarea stream-ului:\n{e}\n\nDetalii:\n{error_details}", "Eroare Redare")

def _resolve_stream(url: str) -> str:
    """
    Extrage link-ul final M3U8 dintr-un URL de pe daddylive.
    Aceasta este logica complexă de parsare a paginii și a script-urilor.
    """
    # Pas 1: Obține pagina principală a stream-ului
    response = ddlv_provider._get_request(url)
    soup = BeautifulSoup(response.text, 'html.parser')
    
    # Caută iframe-ul care conține player-ul
    iframe = soup.find('iframe', attrs={'id': 'thatframe'})
    if not iframe:
        # Încercare alternativă dacă primul iframe nu e găsit
        url = url.replace('/cast/', '/stream/')
        response = ddlv_provider._get_request(url)
        soup = BeautifulSoup(response.text, 'html.parser')
        iframe = soup.find('iframe', attrs={'id': 'thatframe'})
    
    if not iframe:
        raise ValueError("Nu s-a putut găsi iframe-ul player-ului.")
        
    iframe_src = iframe['src']
    
    # Pas 2: Logica diferă în funcție de sursa din iframe
    if 'wikisport.best' in iframe_src:
        # Logica pentru stream-urile wikisport
        match = re.search(r'/.+?(\d+)\.php', iframe_src)
        if not match: raise ValueError("ID-ul stream-ului wikisport nu a fost găsit.")
        
        player_url = f"https://stellarthread.com/wiki.php?player=mobile&live=t{match.group(1)}"
        response = ddlv_provider._get_request(player_url, referer=iframe_src)
        
        match = re.search(r'return\((\[.*?\])\.join', response.text, re.S)
        if not match: raise ValueError("Nu s-a putut extrage M3U8 din script-ul wikisport.")
        
        raw_list = match.group(1)
        elements = json.loads(raw_list)
        m3u8 = ''.join(elements).replace('////', '//')
        return f'{m3u8}|Referer=https://stellarthread.com&Origin=https://stellarthread.com&User-Agent={ddlv_provider.USER_AGENT}'
        
    else:
        # Logica pentru stream-urile standard daddylive
        response = ddlv_provider._get_request(iframe_src)
        page_content = response.text
        
        channel_key_match = re.search(r'const\s+CHANNEL_KEY\s*=\s*"([^"]+)"', page_content)
        bundle_match = re.search(r'const\s+XJZ\s*=\s*"([^"]+)"', page_content)
        
        if not channel_key_match or not bundle_match:
            raise ValueError("Nu s-au putut extrage cheile necesare din pagina player-ului.")
            
        channel_key = channel_key_match.group(1)
        bundle = bundle_match.group(1)
        
        # Decodare bundle
        parts = json.loads(base64.b64decode(bundle).decode("utf-8"))
        for k, v in parts.items():
            parts[k] = base64.b64decode(v).decode("utf-8")
            
        # Generare URL de autorizare
        bx = [40, 60, 61, 33, 103, 57, 33, 57]
        sc = ''.join(chr(b ^ 73) for b in bx)
        host = "https://top2new.newkso.ru/"
        auth_url = (
            f'{host}{sc}'
            f'?channel_id={quote_plus(channel_key)}&'
            f'ts={quote_plus(parts["b_ts"])}&'
            f'rnd={quote_plus(parts["b_rnd"])}&'
            f'sig={quote_plus(parts["b_sig"])}'
        )
        ddlv_provider._get_request(auth_url, referer=iframe_src)
        
        # Obținere server M3U8
        server_lookup_url = f"https://{urlparse(iframe_src).netloc}/server_lookup.php?channel_id={channel_key}"
        response = ddlv_provider._get_request(server_lookup_url, referer=iframe_src).json()
        server_key = response['server_key']
        
        if server_key == "top1/cdn":
            m3u8 = f"https://top1.newkso.ru/top1/cdn/{channel_key}/mono.m3u8"
        else:
            m3u8 = f"https://{server_key}new.newkso.ru/{server_key}/{channel_key}/mono.m3u8"
        
        referer = f'https://{urlparse(iframe_src).netloc}'
        return f'{m3u8}|Referer={referer}/&Origin={referer}&Connection=Keep-Alive&User-Agent={ddlv_provider.USER_AGENT}'
