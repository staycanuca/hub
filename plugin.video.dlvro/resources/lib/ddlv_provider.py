import re
import json
import base64
import traceback
from datetime import datetime, date
import time
from urllib.parse import quote_plus, unquote_plus, urljoin
import requests
from bs4 import BeautifulSoup
from tzlocal import get_localzone
import pytz

from .modules.common import get_setting

# --- Configurare Provider ---
BASE_URL = 'https://daddylive.dad'
USER_AGENT = 'Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Mobile Safari/537.36'
SCHEDULE_URL = urljoin(BASE_URL, '/schedule/schedule-generated.php')
CHANNELS_URL = f'{BASE_URL}/24-7-channels.php'

# --- Funcții Helper pentru Request-uri ---

def _get_request(url: str, referer: str = '') -> requests.Response:
    """Funcție internă pentru a efectua cereri GET."""
    headers = {"User-Agent": USER_AGENT, "Referer": f'{BASE_URL}/', "Origin": f'{BASE_URL}/'}
    if referer:
        headers['Referer'] = headers['Origin'] = referer
    try:
        return requests.get(url, headers=headers, timeout=10)
    except requests.exceptions.RequestException:
        # Reîncercare fără verificare SSL în caz de eroare
        return requests.get(url, headers=headers, timeout=10, verify=False)

# --- Funcții de Extragere Date (GET) ---

def get_main_list() -> str:
    """Obține lista principală de evenimente/categorii."""
    response = _get_request(SCHEDULE_URL)
    return response.text

def get_specific_list(url_param: str) -> str:
    """Obține date pentru o listă specifică (canale, evenimente, etc.)."""
    if url_param == 'channels':
        return _get_request(CHANNELS_URL).text
    elif url_param.startswith('cats/'):
        return unquote_plus(url_param.replace('cats/', ''))
    elif url_param.startswith('events/'):
        return unquote_plus(url_param.replace('events/', ''))
    return ""

# --- Funcții de Parsare Date (PARSE) ---

def parse_main_list(response: str) -> list:
    """Parsează JSON-ul principal și creează meniul inițial."""
    schedule = json.loads(response)
    itemlist = [{
        'type': 'dir',
        'title': 'Channels',
        'link': 'list/channels',
    }]
    for key, value in schedule.items():
        itemlist.append({
            'type': 'dir',
            'title': key.split(' -')[0],
            'link': f'list/cats/{quote_plus(json.dumps(value))}',
        })
    return itemlist

def parse_specific_list(url_param: str, response: str) -> list:
    """Parsează răspunsul pentru o listă specifică."""
    if url_param == 'channels':
        return _parse_channels(response)
    
    response_data = json.loads(response)
    
    if url_param.startswith('cats/'):
        return _parse_categories(response_data)
    elif url_param.startswith('events/'):
        return _parse_events(response_data)
    return []

def _parse_channels(html_content: str) -> list:
    """Helper pentru a parsa pagina de canale."""
    itemlist = []
    password = get_setting('adult_pw')
    soup = BeautifulSoup(html_content, 'html.parser')
    
    for a in soup.find_all('a')[8:]: # Primele link-uri sunt de navigare
        title = a.text
        if '18+' in title and password != 'xxXXxx':
            continue
            
        # Creează un link JSON-serializat pentru a fi compatibil cu funcția de redare
        video_link_data = [[title, f"{BASE_URL}{a['href'].replace('/stream/', '/cast/')}"]]
        
        itemlist.append({
            'type': 'item',
            'title': title,
            'link': json.dumps(video_link_data)
        })
    return itemlist

def _parse_categories(response_data: dict) -> list:
    """Helper pentru a parsa sub-categoriile."""
    itemlist = []
    for key, value in response_data.items():
        itemlist.append({
            'type': 'dir',
            'title': key.rstrip('</span>'),
            'link': f'list/events/{quote_plus(json.dumps(value))}',
        })
    return itemlist

def _parse_events(response_data: list) -> list:
    """Helper pentru a parsa evenimentele."""
    itemlist = []
    for event in response_data:
        title = event.get('event', '')
        start_time = event.get('time', '')
        
        try:
            # Formatează ora locală
            local_time_str = _convert_utc_time_to_local(start_time)
            display_title = f'{local_time_str} - {title}'
        except Exception:
            display_title = f'{start_time} - {title}' if start_time else title
            
        # Colectează toate link-urile de stream pentru eveniment
        all_channels = []
        channels1 = event.get('channels', [])
        channels2 = event.get('channels2', [])
        
        # Asigură-te că ambele sunt liste înainte de a le combina
        if isinstance(channels1, dict): channels1 = list(channels1.values())
        if isinstance(channels2, dict): channels2 = list(channels2.values())

        for channel in channels1 + channels2:
            if isinstance(channel, dict):
                channel_id = channel.get('channel_id', '')
                channel_name = channel.get('channel_name')
                if 'stream-' in channel_id:
                    all_channels.append([channel_name, urljoin(BASE_URL, f"/cast/{channel_id}.php")])
                else:
                    all_channels.append([channel_name, urljoin(BASE_URL, f"/cast/stream-{channel_id}.php")])

        itemlist.append({
            'type': 'item',
            'title': display_title,
            'link': json.dumps(all_channels)
        })
    return itemlist

# --- Funcții Utilitare de Timp ---

def _convert_utc_time_to_local(utc_time_str: str) -> str:
    """Convertește ora UTC (string) în ora locală formatată."""
    today = date.today()
    datetime_str = f"{today} {utc_time_str}"
    
    utc_datetime = datetime.strptime(datetime_str, "%Y-%m-%d %H:%M")
    utc_datetime = utc_datetime.replace(tzinfo=pytz.utc)
    
    local_tz = get_localzone()
    local_time = utc_datetime.astimezone(local_tz)
    
    return local_time.strftime("%I:%M %p").lstrip('0')

# --- Funcții Specifice pentru Filtrare (VERSIUNE CORECTATĂ) ---

def get_romanian_sports_events() -> list:
    """
    Descarcă programul complet și returnează o listă filtrată
    doar cu evenimentele de pe canale românești.
    """
    # Listă actualizată pe baza log-urilor
    romanian_channels = [
        'digi sport', # Termen generic pentru a prinde "Digi Sport 1", "Digi Sport 2", etc.
        'prima sport', # Termen generic pentru a prinde "Prima Sport 1", "Prima Sport 4", etc.
        'romania'
    ]
    
    filtered_events = []
    processed_event_titles = set()

    try:
        full_schedule_json = get_main_list()
        full_schedule = json.loads(full_schedule_json)

        for category_events in full_schedule.values():
            for events in category_events.values():
                for event in events:
                    event_title = event.get('event', '')
                    if event_title in processed_event_titles:
                        continue

                    channels1 = event.get('channels', [])
                    channels2 = event.get('channels2', [])
                    
                    # CORECȚIE: Asigurăm că ambele variabile sunt liste înainte de concatenare
                    if isinstance(channels1, dict): channels1 = list(channels1.values())
                    if isinstance(channels2, dict): channels2 = list(channels2.values())
                    all_event_channels = channels1 + channels2
                    
                    found_romanian_channel = False
                    for channel in all_event_channels:
                        if isinstance(channel, dict):
                            channel_name = channel.get('channel_name', '').lower()
                            for ro_channel in romanian_channels:
                                if ro_channel in channel_name:
                                    found_romanian_channel = True
                                    break
                        if found_romanian_channel:
                            break
                    
                    if found_romanian_channel:
                        start_time = event.get('time', '')
                        try:
                            local_time_str = _convert_utc_time_to_local(start_time)
                            display_title = f'{local_time_str} - {event_title}'
                        except Exception:
                            display_title = f'{start_time} - {event_title}' if start_time else event_title
                        
                        stream_links = []
                        for ch in all_event_channels:
                             if isinstance(ch, dict):
                                channel_id = ch.get('channel_id', '')
                                ch_name = ch.get('channel_name')
                                if 'stream-' in channel_id:
                                     stream_links.append([ch_name, urljoin(BASE_URL, f"/cast/{channel_id}.php")])
                                else:
                                    stream_links.append([ch_name, urljoin(BASE_URL, f"/cast/stream-{channel_id}.php")])

                        filtered_events.append({
                            'type': 'item',
                            'title': display_title,
                            'link': json.dumps(stream_links)
                        })
                        processed_event_titles.add(event_title)

    except Exception:
        # În caz de eroare, returnăm o listă goală.
        return []
        
    return filtered_events
