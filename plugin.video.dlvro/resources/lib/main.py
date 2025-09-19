import json
from html.parser import unescape
import sys
from urllib.parse import parse_qsl
from . import variables as var
from . import functions as func
from .models import Item

def main_menu():
    items = [
        Item(
            title='Channels',
            type='dir',
            mode='channels'
        ),
        Item(
            title='Sport TV RO',
            type='dir',
            mode='romania_sports'
        )
    ]
    func.write_schedule()
    for key in func.read_schedule():
        items.append(
            Item(
                title=key.split(' -')[0].strip(),
                type='dir',
                mode='categories',
                title2=key
            )
        )
    for item in items:
        func.create_listitem(item)

def get_channels():
    item_list = []
    password = var.get_setting('adult_pw')
    response = func.get(var.channels_url)
    soup = func.get_soup(response.text)
    channels = []
    for a in soup.find_all('a')[8:]:
        title = a.text
        if title in channels:
            continue
        channels.append(title)
        if '18+' in title and password != 'xxXXxx':
            continue
        link = json.dumps([[title, f"{var.base_url2}{a['href']}"]])
        
        func.create_listitem(
            Item(
                title=title,
                mode='play',
                link=link,
                summary=title
            )
        )
    return item_list

def get_romania_sports():
    events = func.get_romanian_sports_events()
    for event in events:
        func.create_listitem(event)

def get_categories(date):
    for key in func.read_schedule()[date].keys():
        func.create_listitem(
            Item(
                title=key,
                title2=date,
                type='dir',
                mode='matches'
            )
        )

def get_matches(category, date):
    schedule = func.read_schedule()[date][category]
    func.write_cat_schedule(json.dumps(schedule))
    for match in schedule:
        title = match['event']
        clean_title = unescape(title)
        start_time = match.get('time', '')
        clean_title = f'{func.convert_utc_time_to_local(start_time)} - {clean_title}' if start_time else clean_title
        
        func.create_listitem(
            Item(
                title=clean_title,
                mode='play',
                title2=title,
                summary=clean_title
            )
        )

def play_video(name: str, url: str, icon: str, description, match):
    if match is not None:
        url = func.get_match_links(match)
    url = json.loads(url) if isinstance(url, str) else url
    if len(url) > 1:
        url = func.get_multilink(url)
    else:
        url = url[0][1]
    if not url:
        var.system_exit()
    url = func.resolve_link(url)

    list_item = var.list_item(name, path=url)
    func.set_info(list_item, {'title': name, 'plot': description})
    list_item.setArt({'thumb': icon, 'icon': icon, 'poster': icon})
    list_item.setProperty('inputstream', 'inputstream.ffmpegdirect')
    list_item.setMimeType('application/x-mpegURL')
    list_item.setProperty('inputstream.ffmpegdirect.is_realtime_stream', 'true')
    if var.get_setting_bool('timeshift') is True:
        list_item.setProperty('inputstream.ffmpegdirect.stream_mode', 'timeshift')
    list_item.setProperty('inputstream.ffmpegdirect.manifest_type', 'hls')
    var.set_resolved_url(var.handle, True, listitem=list_item)


def router(params: dict):
    mode = params.get('mode')
    title = params.get('title')
    title2 = params.get('title2')
    link = params.get('link', '')
    thumbnail = params.get('thumbnail')
    summary = params.get('summary')
    
    if mode is None:
        main_menu()
    
    elif mode == 'channels':
        get_channels()

    elif mode == 'romania_sports':
        get_romania_sports()
    
    elif mode == 'categories':
        get_categories(title2)
    
    elif mode == 'matches':
        get_matches(title, title2)
    
    elif mode == 'play':
        play_video(title, link, thumbnail, summary, title2)
    
    var.set_content(var.handle, 'videos')
    var.set_category(var.handle, title)
    var.end_directory(var.handle)

def main():
    router(dict(parse_qsl(sys.argv[2].lstrip('?'))))
