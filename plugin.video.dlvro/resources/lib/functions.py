import sys
import json
import re
import traceback
import time
import base64
from urllib.parse import quote_plus, urlparse, urljoin
from datetime import datetime, date
from typing import Union
import requests
from requests import Response
from bs4 import BeautifulSoup
from tzlocal import get_localzone
import pytz
import xbmc
import xbmcgui
import xbmcplugin
import xbmcvfs
from . import variables as var
from .models import Item


class proxydt(datetime):

    @classmethod
    def strptime(cls, date_string, _format):
        return datetime(*(time.strptime(date_string, _format)[:6]))


datetime = proxydt


def log(message: str):
    return xbmc.log(str(message), xbmc.LOGINFO)

def get(url: str, referer: str='') -> Response:
        headers = var.headers.copy()
        if referer:
            headers['Referer'] = headers['Origin'] = referer
        try:
            return requests.get(url, headers=headers, timeout=10)
        except:
            return requests.get(url, headers=headers, timeout=10, verify=False)

def get_soup(response: str) -> BeautifulSoup:
    return BeautifulSoup(response, 'html.parser')

def set_info(liz: xbmcgui.ListItem, infolabels: dict, cast: list=None):
    cast = cast or []
    i = liz.getVideoInfoTag()
    i.setMediaType(infolabels.get("mediatype", "video"))
    i.setTitle(infolabels.get("title", "Unknown"))
    i.setPlot(infolabels.get("plot", infolabels.get("title", "")))
    i.setTagLine(infolabels.get("tagline", ""))
    i.setPremiered(infolabels.get("premiered", ""))
    i.setGenres(infolabels.get("genre", []))
    i.setMpaa(infolabels.get("mpaa", ""))
    i.setDirectors(infolabels.get("director", []))
    i.setWriters(infolabels.get("writer", []))
    i.setRating(infolabels.get("rating", 0))
    i.setVotes(infolabels.get("votes", 0))
    i.setStudios(infolabels.get("studio", []))
    i.setCountries(infolabels.get("country", []))
    i.setSet(infolabels.get("set", ""))
    i.setTvShowStatus(infolabels.get("status", ""))
    i.setDuration(infolabels.get("duration", 0))
    i.setTrailer(infolabels.get("trailer", ""))

    cast_list = []
    for actor in cast:
        cast_list.append(xbmc.Actor(
            name=actor.get("name", ""),
            role=actor.get("role", ""),
            thumbnail=actor.get("thumbnail", "")
        ))
    i.setCast(cast_list)

def create_listitem(item: Union[Item, dict]):
    if isinstance(item, dict):
        item = Item(**item)
    is_folder = item.type == 'dir'
    title = item.title
    thumbnail = item.thumbnail
    fanart = item.fanart
    description = item.summary or title
    list_item = xbmcgui.ListItem(label=title)
    list_item.setArt({'thumb': thumbnail, 'icon': thumbnail, 'poster': thumbnail, 'fanart': fanart})
    
    infolabels = item.infolabels or {
        'mediatype': 'video',
        'title': title,
        'plot': description,
    }
    cast = item.cast or []
    set_info(list_item, infolabels, cast=cast)
    if is_folder is False:
        list_item.setProperty('IsPlayable', 'true')
    plugin_url = f'{sys.argv[0]}?{item.url_encode()}'
    xbmcplugin.addDirectoryItem(var.handle, plugin_url, list_item, is_folder)

def ok_dialog(text: str):
    xbmcgui.Dialog().ok(var.addon_name, text)

def get_multilink(lists):
        labels = []
        links = []
        counter = 1
        for _list in lists:
            if isinstance(_list, list) and len(_list) == 2:
                if len(lists) == 1:
                    return _list[1]
                labels.append(_list[0])
                links.append(_list[1])
            elif isinstance(_list, str):
                if len(lists) == 1:
                    return _list
                if _list.strip().endswith(')'):
                    labels.append(_list.split('(')[-1].replace(')', ''))
                    links.append(_list.rsplit('(')[0].strip())
                else:
                    labels.append('Link ' + str(counter))
                    links.append(_list)
            else:
                return
            counter += 1
        dialog = xbmcgui.Dialog()
        ret = dialog.select('Choose a Link', labels)
        if ret == -1:
            return
        if isinstance(lists[ret], str) and lists[ret].endswith(')'):
            link = lists[ret].split('(')[0].strip()
            return link
        elif isinstance(lists[ret], list):
            return lists[ret][1]
        return lists[ret]

def write_file(file_path, string):
    with open(file_path, 'w', encoding='utf-8', errors='ignore') as f:
        f.write(string)

def read_file(file_path):
    with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
        return f.read()

def write_schedule():
    if not xbmcvfs.exists(var.profile_path):
        xbmcvfs.mkdirs(var.profile_path)
    response = get(var.schedule_url)
    write_file(var.schedule_path, response.text)

def read_schedule() -> dict:
    if not xbmcvfs.exists(var.schedule_path):
        write_schedule()
    return json.loads(read_file(var.schedule_path))

def write_cat_schedule(string):
    write_file(var.cat_schedule_path, string)

def read_cat_schedule() -> list:
    return json.loads(read_file(var.cat_schedule_path))

def convert_utc_time_to_local(utc_time_str):
        today = date.today()
        datetime_str = f"{today} {utc_time_str}"
        utc_datetime = datetime.strptime(datetime_str, "%Y-%m-%d %H:%M")
        utc_datetime = utc_datetime.replace(tzinfo=pytz.utc)
        local_tz = get_localzone()
        local_time = utc_datetime.astimezone(local_tz)
        return local_time.strftime("%I:%M %p").lstrip('0')

def get_match_links(match):
    item = {}
    schedule = read_cat_schedule()
    for event in schedule:
        if event['event'] == match:
            item = event
            break
    links = []
    channels = item.get('channels', [])
    for channel in channels:
        if isinstance(channel, dict):
            links.append(
                [
                    channel.get('channel_name'),
                    f"https://dlhd.dad/stream/stream-{channel.get('channel_id')}.php"
                ]
            )
    channels2 = item.get('channels2')
    for channel in channels2:
        if isinstance(channel, dict):
            links.append(
                [
                    channel.get('channel_name'),
                    f"{var.base_url2}/stream/bet.php?id=bet{channel.get('channel_id')}"
                ]
            )
    return links

def get_romanian_sports_events() -> list:
    """
    Downloads the full schedule and returns a filtered list
    of events from Romanian channels.
    """
    romanian_channels = [
        'digi sport',
        'prima sport',
        'romania'
    ]
    
    filtered_events = []
    processed_event_titles = set()

    try:
        full_schedule_json = get(var.schedule_url).text
        full_schedule = json.loads(full_schedule_json)

        for category_events in full_schedule.values():
            for events in category_events.values():
                for event in events:
                    event_title = event.get('event', '')
                    if event_title in processed_event_titles:
                        continue

                    channels1 = event.get('channels', [])
                    channels2 = event.get('channels2', [])
                    
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
                            local_time_str = convert_utc_time_to_local(start_time)
                            display_title = f'{local_time_str} - {event_title}'
                        except Exception:
                            display_title = f'{start_time} - {event_title}' if start_time else event_title
                        
                        stream_links = []
                        for ch in channels1:
                             if isinstance(ch, dict):
                                channel_id = ch.get('channel_id', '')
                                ch_name = ch.get('channel_name')
                                stream_links.append([ch_name, f"{var.base_url2}/stream/stream-{channel_id}.php"])
                        
                        for ch in channels2:
                            if isinstance(ch, dict):
                                channel_id = ch.get('channel_id', '')
                                ch_name = ch.get('channel_name')
                                stream_links.append([ch_name, f"{var.base_url2}/stream/bet.php?id=bet{channel_id}"])

                        # Create an Item object directly
                        item = Item(
                            title=display_title,
                            mode='play',
                            link=json.dumps(stream_links),
                            summary=display_title
                        )
                        filtered_events.append(item)
                        processed_event_titles.add(event_title)

    except Exception:
        log(f'Error in get_romanian_sports_events:\n{traceback.format_exc()}')
        return []
        
    return filtered_events

def resolve_link(url):
    try:
        response = get(url)
        soup = get_soup(response.text)
        iframe = soup.find('iframe', attrs={'id': 'thatframe'})
        if iframe is None:
            url = url.replace('/cast/', '/stream/')
            response = get(url)
            soup = get_soup(response.text)
            iframe = soup.find('iframe', attrs={'id': 'thatframe'})
            
        url2 = iframe['src']
        
        if 'wikisport.best' in url2:
            match =  re.search(r'/.+?(\d+)\.php', url2)
            url3 = f"https://stellarthread.com/wiki.php?player=mobile&live=t{match.group(1)}"
            response = get(url3, referer=url2)
            match = re.search(r'return\((\[.*?\])\.join', response.text, re.S)
            raw_list = match.group(1)
            elements = json.loads(raw_list)
            m3u8 = ''.join(elements).replace('////', '//')
            m3u8 = f'{m3u8}|Referer=https://stellarthread.com&Origin=https://stellarthread.com&User-Agent={var.user_agent}'
            
        else:
            response = get(url2)
            channel_key = re.search(r'const\s+CHANNEL_KEY\s*=\s*"([^"]+)"', response.text).group(1)
            bundle = re.search(r'const\s+XJZ\s*=\s*"([^"]+)"', response.text).group(1)
            parts = json.loads(base64.b64decode(bundle).decode("utf-8"))
            for k, v in parts.items():
                parts[k] = base64.b64decode(v).decode("utf-8")
            bx = [40, 60, 61, 33, 103, 57, 33, 57]
            sc = ''.join(chr(b ^ 73) for b in bx)
            host = "https://top2new.newkso.ru/"
            auth_url = (
                f'{host}{sc}'
                f'?channel_id={quote_plus(channel_key)}&'
                f'ts={quote_plus(parts["b_ts"])}&'
                f'rnd={quote_plus(parts["b_rnd"]) }&'
                f'sig={quote_plus(parts["b_sig"])}'
            )
            get(auth_url, referer=url2)
            
            server_lookup_url = f"https://{urlparse(url2).netloc}/server_lookup.php?channel_id={channel_key}"
            response = get(server_lookup_url, referer=url2).json()
            server_key = response['server_key']
            if server_key == "top1/cdn":
                m3u8 = f"https://top1.newkso.ru/top1/cdn/{channel_key}/mono.m3u8"
            else:
                m3u8 = f"https://{server_key}new.newkso.ru/{server_key}/{channel_key}/mono.m3u8"
            
            referer = f'https://{urlparse(url2).netloc}'
            m3u8 = f'{m3u8}|Referer={referer}/&Origin={referer}&Connection=Keep-Alive&User-Agent={var.user_agent}'
            
    except Exception:
        ok_dialog(f'Error loading stream:\n{traceback.format_exc()}')
        log(f'Error loading stream:\n{traceback.format_exc()}')
        var.system_exit()
        
    return m3u8