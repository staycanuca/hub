import xbmc
import sys
import xbmcvfs
import xbmcaddon
import xbmcgui
import xbmcplugin
import urllib.parse
import requests
import resolveurl
import json
import re
import os
import time
import base64
from bs4 import BeautifulSoup

# Get the addon ID
ADDON_ID = xbmcaddon.Addon().getAddonInfo('id')
ADDON = xbmcaddon.Addon(ADDON_ID)
HANDLE = int(sys.argv[1])
BASE_URL = 'https://veziaici.net/'
CACHE_DIR = xbmcvfs.translatePath(os.path.join(xbmcaddon.Addon().getAddonInfo('profile'), 'cache'))
if not os.path.exists(CACHE_DIR):
    os.makedirs(CACHE_DIR)

# Dictionary for custom show images
CUSTOM_IMAGES = {
    'insula iubirii': 'https://www.fanatik.ro/wp-content/uploads/2024/08/insula-iubirii-2025.jpg',
    'las fierbinti': 'https://upload.wikimedia.org/wikipedia/en/0/0d/Las_Fierbin%C8%9Bi_logo.png',
    'asia express': 'https://cdn.adh.reperio.news/image-e/e410c82f-f849-4953-94fa-ed9ee2ba49bf/index.jpeg',
    'masterchef': 'https://static4.libertatea.ro/wp-content/uploads/2024/02/masterchef-romania-revine-la-pro-tv.jpg',
    'the ticket': 'https://static4.libertatea.ro/wp-content/uploads/2025/07/the-ticket.jpg',
    'vocea romaniei': 'https://upload.wikimedia.org/wikipedia/ro/thumb/8/83/Vocea_Rom%C3%A2niei_-_compila%C8%9Bie.jpg/250px-Vocea_Rom%C3%A2niei_-_compila%C8%9Bie.jpg',
    'ana mi-ai fost scrisa in adn': 'https://static4.libertatea.ro/wp-content/uploads/2024/11/ana-mi-ai-fost-scrisa-in-adn-serial-antena-1.jpg',
    'camera 609': 'https://static.cinemagia.ro/img/resize/db/movie/33/10/231/lasa-ma-imi-place-camera-609-729239l-600x0-w-09e9e09b.jpg',
    'clanul': 'https://cmero-ott-images-svod.ssl.cdn.cra.cz/r800x1160n/ad802c4a-901f-4700-9948-39361f41a677',
    'seriale': 'https://upload.wikimedia.org/wikipedia/en/0/0d/Las_Fierbin%C8%9Bi_logo.png',
    'iubire cu': 'https://dcasting.ro/wp-content/uploads/2025/02/Iubire-cu-parfum-de-lavanda.jpg',
    'sotia sotului': 'https://onemagia.com/upload/images/e7mDxkP6Qgbo735USy5telMF1wF.jpg',
    'scara b': 'https://static4.libertatea.ro/wp-content/uploads/2024/08/scara-b-scaled.jpg',
    'tatutu': 'https://image.stirileprotv.ro/media/images/1920x1080/Jun2025/62556367.jpg'
}

def get_main_menu_items():
    try:
        response = requests.get(BASE_URL)
        response.raise_for_status()
        html_content = response.text
    except requests.exceptions.RequestException as e:
        xbmcgui.Dialog().ok(ADDON.getAddonInfo('name'), f"Failed to fetch main page: {e}")
        return []
    
    soup = BeautifulSoup(html_content, 'html.parser')
    categories = []
    
    for top_li in soup.select('ul#main-menu > li.menu-item-has-children'):
        category_title_element = top_li.find('span')
        if not category_title_element:
            continue
        
        category_title = category_title_element.text.strip()
        sub_menu = top_li.find('ul', class_='sub-menu')
        
        if category_title and sub_menu:
            shows = []
            for sub_li in sub_menu.find_all('li'):
                link = sub_li.find('a')
                if link and 'href' in link.attrs:
                    title = link.text.strip()
                    url = link['href']
                    if title and url:
                        shows.append({'title': title, 'url': url})
            if shows:
                categories.append({'title': category_title, 'shows': shows})
                        
    return categories

def list_main_menu():
    # Add a static search item
    list_item = xbmcgui.ListItem('Cauta')
    search_icon = "https://i.imgur.com/dvqhLCI.png"
    list_item.setArt({'icon': search_icon, 'thumb': search_icon})
    url = sys.argv[0] + '?' + urllib.parse.urlencode({'mode': 'search'})
    xbmcplugin.addDirectoryItem(handle=HANDLE, url=url, listitem=list_item, isFolder=True)

    categories = get_main_menu_items()
    for category in categories:
        list_item = xbmcgui.ListItem(category['title'])
        category_icon = ADDON.getAddonInfo('icon')  # Initialize with default
        
        if 'emisiuni' in category['title'].lower():
            category_icon = CUSTOM_IMAGES.get('asia express', category_icon)
            url = sys.argv[0] + '?' + urllib.parse.urlencode({'mode': 'list_show_categories', 'shows': json.dumps(category['shows']), 'name': category['title'], 'latest_url': 'https://veziaici.net/category/a-emisiuni-romanesti/'})
        elif 'seriale' in category['title'].lower():
            category_icon = CUSTOM_IMAGES.get('las fierbinti', category_icon)
            url = sys.argv[0] + '?' + urllib.parse.urlencode({'mode': 'list_show_categories', 'shows': json.dumps(category['shows']), 'name': category['title'], 'latest_url': 'https://veziaici.net/category/a-seriale-romanesti/'})
        else:
            url = sys.argv[0] + '?' + urllib.parse.urlencode({'mode': 'list_shows', 'shows': json.dumps(category['shows']), 'name': category['title']})

        list_item.setArt({'icon': category_icon, 'thumb': category_icon})
        xbmcplugin.addDirectoryItem(handle=HANDLE, url=url, listitem=list_item, isFolder=True)

    # Add a static folder for Seriale Turcesti
    list_item = xbmcgui.ListItem('Seriale Turcesti')
    turk_icon = "https://fuzzy.ro/wp-content/uploads/2023/01/seriale-turcesti.jpg"
    list_item.setArt({'icon': turk_icon, 'thumb': turk_icon})
    url = sys.argv[0] + '?' + urllib.parse.urlencode({'mode': 'list_turkish_series_categories'})
    xbmcplugin.addDirectoryItem(handle=HANDLE, url=url, listitem=list_item, isFolder=True)

    # Add a static folder for Seriale Coreene
    list_item = xbmcgui.ListItem('Seriale Coreene')
    korean_icon = "https://fericitazi.com/wp-content/uploads/Seriale-coreene-de-dragoste-780x450.jpg"
    list_item.setArt({'icon': korean_icon, 'thumb': korean_icon})
    url = sys.argv[0] + '?' + urllib.parse.urlencode({'mode': 'list_korean_series_categories'})
    xbmcplugin.addDirectoryItem(handle=HANDLE, url=url, listitem=list_item, isFolder=True)

    # Add a static folder for Seriale Chinezesti
    list_item = xbmcgui.ListItem('Seriale Chinezesti')
    list_item.setArt({'icon': korean_icon, 'thumb': korean_icon})
    url_params = {
        'mode': 'list_korean_series',
        'url': 'https://blogul-lui-atanase.ro/categorie/serialefilme-chinezesti/',
        'name': 'Seriale Chinezesti'
    }
    xbmcplugin.addDirectoryItem(handle=HANDLE, url=sys.argv[0] + '?' + urllib.parse.urlencode(url_params), listitem=list_item, isFolder=True)

    # Add a static folder for Seriale Japoneze
    list_item = xbmcgui.ListItem('Seriale Japoneze')
    list_item.setArt({'icon': korean_icon, 'thumb': korean_icon})
    url_params = {
        'mode': 'list_korean_series',
        'url': 'https://blogul-lui-atanase.ro/categorie/seriale-japoneze/',
        'name': 'Seriale Japoneze'
    }
    xbmcplugin.addDirectoryItem(handle=HANDLE, url=sys.argv[0] + '?' + urllib.parse.urlencode(url_params), listitem=list_item, isFolder=True)

    # Add a static folder for Seriale Thailandeze
    list_item = xbmcgui.ListItem('Seriale Thailandeze')
    list_item.setArt({'icon': korean_icon, 'thumb': korean_icon})
    url_params = {
        'mode': 'list_korean_series',
        'url': 'https://blogul-lui-atanase.ro/categorie/seriale-thailandeze/',
        'name': 'Seriale Thailandeze'
    }
    xbmcplugin.addDirectoryItem(handle=HANDLE, url=sys.argv[0] + '?' + urllib.parse.urlencode(url_params), listitem=list_item, isFolder=True)

    # Add a static folder for Seriale Taiwan
    list_item = xbmcgui.ListItem('Seriale Taiwan')
    list_item.setArt({'icon': korean_icon, 'thumb': korean_icon})
    url_params = {
        'mode': 'list_korean_series',
        'url': 'https://blogul-lui-atanase.ro/categorie/serialefilme-taiwanezethailandeze/',
        'name': 'Seriale Taiwan'
    }
    xbmcplugin.addDirectoryItem(handle=HANDLE, url=sys.argv[0] + '?' + urllib.parse.urlencode(url_params), listitem=list_item, isFolder=True)

    # Add a static folder for Filme
    list_item = xbmcgui.ListItem('Filme')
    filme_icon = "https://1.bp.blogspot.com/-5utXzUd3Wk0/XcatUqtM9pI/AAAAAAAACTU/8Jbt1d8gO8Y7XVLGQnjHYYnJ9ou1_kTLACLcBGAsYHQ/s1600/www.tvnowstream.de.jpg"
    list_item.setArt({'icon': filme_icon, 'thumb': filme_icon})
    url = sys.argv[0] + '?' + urllib.parse.urlencode({'mode': 'list_movies_categories'})
    xbmcplugin.addDirectoryItem(handle=HANDLE, url=url, listitem=list_item, isFolder=True)

    xbmcplugin.endOfDirectory(HANDLE)

def list_show_categories(shows_json, name, latest_url):
    # Add "Ultimile adaugate" item
    list_item = xbmcgui.ListItem('Ultimile adaugate')
    url_params = {'mode': 'list_latest', 'url': latest_url, 'name': 'Ultimile adaugate'}
    xbmcplugin.addDirectoryItem(handle=HANDLE, url=sys.argv[0] + '?' + urllib.parse.urlencode(url_params), listitem=list_item, isFolder=True)

    # Add the rest of the shows
    shows = json.loads(shows_json)
    for show in shows:
        list_item = xbmcgui.ListItem(show['title'])
        
        # Default icon
        show_icon = ADDON.getAddonInfo('icon')
        # Check for custom image
        for keyword, image_url in CUSTOM_IMAGES.items():
            if keyword in show['title'].lower():
                show_icon = image_url
                break

        list_item.setArt({'icon': show_icon, 'thumb': show_icon})
        url = sys.argv[0] + '?' + urllib.parse.urlencode({'mode': 'list_episodes', 'url': show['url'], 'name': show['title']})
        xbmcplugin.addDirectoryItem(handle=HANDLE, url=url, listitem=list_item, isFolder=True)
    xbmcplugin.endOfDirectory(HANDLE)

def list_shows(shows_json):
    shows = json.loads(shows_json)
    for show in shows:
        list_item = xbmcgui.ListItem(show['title'])
        
        # Default icon
        show_icon = ADDON.getAddonInfo('icon')
        # Check for custom image
        for keyword, image_url in CUSTOM_IMAGES.items():
            if keyword in show['title'].lower():
                show_icon = image_url
                break

        list_item.setArt({'icon': show_icon, 'thumb': show_icon})
        url = sys.argv[0] + '?' + urllib.parse.urlencode({'mode': 'list_episodes', 'url': show['url'], 'name': show['title']})
        xbmcplugin.addDirectoryItem(handle=HANDLE, url=url, listitem=list_item, isFolder=True)
    xbmcplugin.endOfDirectory(HANDLE)

def list_episodes(url, name=""):
    cache_file = os.path.join(CACHE_DIR, name.replace(' ', '_') + '.json')
    cache_expiry = 24 * 3600 # 24 hours

    all_episodes = []

    # Try to load from cache first
    if os.path.exists(cache_file) and (time.time() - os.path.getmtime(cache_file)) < cache_expiry:
        with open(cache_file, 'r') as f:
            all_episodes = json.load(f)
    else:
        # If cache is invalid or missing, scrape all pages
        current_url = url
        while current_url:
            try:
                response = requests.get(current_url)
                response.raise_for_status()
                soup = BeautifulSoup(response.text, 'html.parser')
            except requests.exceptions.RequestException:
                break

            for item_container in soup.find_all('div', class_='rb-col-m12'):
                title_element = item_container.find('h2', class_='entry-title')
                if title_element and title_element.find('a'):
                    link_element = title_element.find('a')
                    item_url = link_element['href']
                    title = link_element.text.strip()
                    if item_url and title:
                        all_episodes.append({'title': title, 'url': item_url, 'name': name})

            next_page_link = soup.find('a', class_='next page-numbers')
            if next_page_link and next_page_link.has_attr('href'):
                current_url = next_page_link['href']
            else:
                current_url = None
        
        # Save to cache
        with open(cache_file, 'w') as f:
            json.dump(all_episodes, f)

    # --- The rest of the function remains the same, processing 'all_episodes' ---

    # Extract seasons from episode titles
    seasons = {}
    no_season_episodes = []
    for episode in all_episodes:
        match = re.search(r'sez(?:onul|on|\.)\s*(\d+)', episode['title'], re.IGNORECASE)
        if match:
            season_num = int(match.group(1))
            if season_num not in seasons:
                seasons[season_num] = []
            seasons[season_num].append(episode)
        else:
            no_season_episodes.append(episode)

    # If only one season is found and no episodes without a season, list them directly
    if len(seasons) == 1 and not no_season_episodes:
        season_num = list(seasons.keys())[0]
        list_episodes_for_season(json.dumps(seasons[season_num]), season_num, name)
        return

    # Create folders for each season
    for season_num in sorted(seasons.keys(), reverse=True):
        list_item = xbmcgui.ListItem(f"Sezonul {season_num}")
        season_icon = ADDON.getAddonInfo('icon')
        for keyword, image_url in CUSTOM_IMAGES.items():
            if keyword in name.lower():
                season_icon = image_url
                break
        list_item.setArt({'icon': season_icon, 'thumb': season_icon})
        url_params = {'mode': 'list_episodes_for_season', 'episodes': json.dumps(seasons[season_num]), 'season': season_num, 'name': name}
        xbmcplugin.addDirectoryItem(handle=HANDLE, url=sys.argv[0] + '?' + urllib.parse.urlencode(url_params), listitem=list_item, isFolder=True)

    if no_season_episodes:
        list_item = xbmcgui.ListItem("Fara Sezon")
        list_item.setArt({'icon': ADDON.getAddonInfo('icon'), 'thumb': ADDON.getAddonInfo('icon')})
        url_params = {'mode': 'list_episodes_for_season', 'episodes': json.dumps(no_season_episodes), 'season': '0', 'name': name}
        xbmcplugin.addDirectoryItem(handle=HANDLE, url=sys.argv[0] + '?' + urllib.parse.urlencode(url_params), listitem=list_item, isFolder=True)

    xbmcplugin.endOfDirectory(HANDLE)

def list_episodes_for_season(episodes_json, season, name=""):
    episodes = json.loads(episodes_json)
    custom_image_found = None
    for keyword, image_url in CUSTOM_IMAGES.items():
        if keyword in name.lower():
            custom_image_found = image_url
            break

    for episode in episodes:
        list_item = xbmcgui.ListItem(episode['title'])
        image_to_use = custom_image_found if custom_image_found else ADDON.getAddonInfo('icon')
        list_item.setArt({'thumb': image_to_use, 'icon': image_to_use, 'fanart': ADDON.getAddonInfo('fanart')})
        list_item.setInfo('video', {'title': episode['title']})
        url_params = {'mode': 'list_sources', 'url': episode['url']}
        xbmcplugin.addDirectoryItem(handle=HANDLE, url=sys.argv[0] + '?' + urllib.parse.urlencode(url_params), listitem=list_item, isFolder=True)
    xbmcplugin.endOfDirectory(HANDLE)

def list_sources(url):
    try:
        response = requests.get(url)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')
    except requests.exceptions.RequestException as e:
        xbmcgui.Dialog().ok(ADDON.getAddonInfo('name'), f"Failed to fetch source page: {e}")
        return

    iframes = soup.find_all('iframe', attrs={'data-lazy-src': True})
    for iframe in iframes:
        video_url = iframe['data-lazy-src']
        
        if 'player3.funny-cats.org' in video_url:
            continue

        if video_url.startswith('//'):
            video_url = 'https:' + video_url
        
        domain = urllib.parse.urlparse(video_url).netloc.replace('www.', '')
        
        list_item = xbmcgui.ListItem(f"Sursa: {domain}")
        list_item.setInfo('video', {'title': f"Sursa: {domain}"})
        list_item.setProperty('IsPlayable', 'true')
        url_params = {'mode': 'play_source', 'url': video_url}
        context_menu_items = [('Download', f'RunPlugin({sys.argv[0]}?mode=download_source&url={urllib.parse.quote_plus(video_url)})')]
        list_item.addContextMenuItems(context_menu_items)
        xbmcplugin.addDirectoryItem(handle=HANDLE, url=sys.argv[0] + '?' + urllib.parse.urlencode(url_params), listitem=list_item, isFolder=False)
    
    xbmcplugin.endOfDirectory(HANDLE)

def play_source(url):
    resolved_url = resolveurl.resolve(url)
    if resolved_url:
        list_item = xbmcgui.ListItem(path=resolved_url)
        xbmcplugin.setResolvedUrl(HANDLE, True, list_item)
    else:
        xbmcgui.Dialog().ok(ADDON.getAddonInfo('name'), "Could not resolve video URL.")

def list_search_results(url):
    try:
        response = requests.get(url)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')
    except requests.exceptions.RequestException as e:
        xbmcgui.Dialog().ok(ADDON.getAddonInfo('name'), f"Failed to fetch search results: {e}")
        return

    for item in soup.select('div.rb-p20-gutter.rb-col-m12.rb-col-t4'):
        title_element = item.select_one('h3.entry-title a.p-url')
        if title_element:
            title = title_element.get('title')
            item_url = title_element.get('href')
            
            show_icon = ADDON.getAddonInfo('icon')
            for keyword, image_url in CUSTOM_IMAGES.items():
                if keyword in title.lower():
                    show_icon = image_url
                    break

            list_item = xbmcgui.ListItem(title)
            list_item.setArt({'thumb': show_icon, 'icon': show_icon})
            
            # We assume search results lead directly to sources
            url_params = {'mode': 'list_sources', 'url': item_url, 'name': title}
            xbmcplugin.addDirectoryItem(handle=HANDLE, url=sys.argv[0] + '?' + urllib.parse.urlencode(url_params), listitem=list_item, isFolder=True)

    # Handle pagination
    next_page_link = soup.select_one('a.page-numbers')
    if next_page_link:
        next_page_url = next_page_link.get('href')
        if next_page_url:
            list_item = xbmcgui.ListItem('Next Page >>')
            url_params = {'mode': 'list_search_results', 'url': next_page_url}
            xbmcplugin.addDirectoryItem(handle=HANDLE, url=sys.argv[0] + '?' + urllib.parse.urlencode(url_params), listitem=list_item, isFolder=True)

    xbmcplugin.endOfDirectory(HANDLE)

def search(query=None):
    if not query:
        keyboard = xbmcgui.Dialog().input('Cauta', type=xbmcgui.INPUT_ALPHANUM)
        if not keyboard:
            return
        query = keyboard

    search_url = BASE_URL + '?s=' + urllib.parse.quote_plus(query)
    list_search_results(search_url)

def list_latest(url, name=""):
    all_items = []
    current_url = url
    page_count = 0

    while current_url and page_count < 3:
        try:
            response = requests.get(current_url)
            response.raise_for_status()
            soup = BeautifulSoup(response.text, 'html.parser')
        except requests.exceptions.RequestException:
            break

        for item_container in soup.find_all('div', class_='rb-col-m12'):
            title_element = item_container.find('h2', class_='entry-title')
            if title_element and title_element.find('a'):
                link_element = title_element.find('a')
                item_url = link_element['href']
                title = link_element.text.strip()

                show_icon = ADDON.getAddonInfo('icon')
                for keyword, image_url in CUSTOM_IMAGES.items():
                    if keyword in title.lower():
                        show_icon = image_url
                        break

                if item_url and title:
                    all_items.append({'title': title, 'url': item_url, 'thumbnail': show_icon})

        next_page_link = soup.find('a', class_='next page-numbers')
        if next_page_link and next_page_link.has_attr('href'):
            current_url = next_page_link['href']
        else:
            current_url = None
        
        page_count += 1

    for item in all_items:
        list_item = xbmcgui.ListItem(item['title'])
        list_item.setArt({'thumb': item['thumbnail'], 'icon': item['thumbnail']})
        list_item.setInfo('video', {'title': item['title']})
        url_params = {'mode': 'list_sources', 'url': item['url']}
        xbmcplugin.addDirectoryItem(handle=HANDLE, url=sys.argv[0] + '?' + urllib.parse.urlencode(url_params), listitem=list_item, isFolder=True)

    if current_url:
        list_item = xbmcgui.ListItem('Next Page >>')
        url_params = {'mode': 'list_latest', 'url': current_url, 'name': name}
        xbmcplugin.addDirectoryItem(handle=HANDLE, url=sys.argv[0] + '?' + urllib.parse.urlencode(url_params), listitem=list_item, isFolder=True)

    xbmcplugin.endOfDirectory(HANDLE)

def list_turkish_series(url, mode, page='1'):
    try:
        response = requests.get(url)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')
    except requests.exceptions.RequestException as e:
        xbmcgui.Dialog().ok(ADDON.getAddonInfo('name'), f"Failed to fetch Turkish series: {e}")
        return
    all_series = []
    for figure in soup.find_all('figure', class_='wp-block-image'):
        link = figure.find('a')
        img = figure.find('img')
        if link and img and 'href' in link.attrs and 'src' in img.attrs:
            series_url = link['href']
            thumb = img['src']   
            # Extract name from URL
            name_part = series_url.strip('/').split('/')[-1]
            name = ' '.join(word.capitalize() for word in name_part.split('-'))
            all_series.append({'name': name, 'url': series_url, 'thumb': thumb})
    page = int(page)
    items_per_page = 20
    start_index = (page - 1) * items_per_page
    end_index = start_index + items_per_page
    page_items = all_series[start_index:end_index]
    for series in page_items:
        list_item = xbmcgui.ListItem(series['name'])
        list_item.setArt({'thumb': series['thumb'], 'icon': series['thumb']})
        url_params = {'mode': 'list_turkish_episodes', 'url': series['url'], 'name': series['name']}
        xbmcplugin.addDirectoryItem(handle=HANDLE, url=sys.argv[0] + '?' + urllib.parse.urlencode(url_params), listitem=list_item, isFolder=True)
    if end_index < len(all_series):
        next_page = page + 1
        list_item = xbmcgui.ListItem('Next Page >>')
        url_params = {'mode': mode, 'url': url, 'page': str(next_page)}
        xbmcplugin.addDirectoryItem(handle=HANDLE, url=sys.argv[0] + '?' + urllib.parse.urlencode(url_params), listitem=list_item, isFolder=True)
    xbmcplugin.endOfDirectory(HANDLE)


def list_turkish_episodes(url, name):
    try:
        response = requests.get(url)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')
    except requests.exceptions.RequestException as e:
        xbmcgui.Dialog().ok(ADDON.getAddonInfo('name'), f"Failed to fetch episodes for {name}: {e}")
        return
    for article in soup.find_all('article'):
        thumb_link = article.find('a', class_='post-thumbnail')
        if thumb_link:
            episode_url = thumb_link['href']
            img = thumb_link.find('img')
            thumb = img['src'] if img and 'src' in img.attrs else ''
            title = img['alt'].replace('&#8211;', '-').strip() if img and 'alt' in img.attrs else 'Episode'
            list_item = xbmcgui.ListItem(title)
            list_item.setArt({'thumb': thumb, 'icon': thumb})
            list_item.setInfo('video', {'title': title})
            url_params = {'mode': 'list_turkish_sources', 'url': episode_url}
            xbmcplugin.addDirectoryItem(handle=HANDLE, url=sys.argv[0] + '?' + urllib.parse.urlencode(url_params), listitem=list_item, isFolder=True)
    # Handle pagination
    next_page_link = soup.find('a', class_='next page-numbers')
    if next_page_link and 'href' in next_page_link.attrs:
        next_page_url = next_page_link['href']
        list_item = xbmcgui.ListItem('Next Page >>')
        url_params = {'mode': 'list_turkish_episodes', 'url': next_page_url, 'name': name}
        xbmcplugin.addDirectoryItem(handle=HANDLE, url=sys.argv[0] + '?' + urllib.parse.urlencode(url_params), listitem=list_item, isFolder=True)
    xbmcplugin.endOfDirectory(HANDLE)


def list_turkish_sources(url):
    try:
        response = requests.get(url)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')
    except requests.exceptions.RequestException as e:
        xbmcgui.Dialog().ok(ADDON.getAddonInfo('name'), f"Failed to fetch source page: {e}")
        return

    iframe_placeholders = soup.find_all('div', class_='iframe-placeholder')
    
    if not iframe_placeholders:
        xbmcgui.Dialog().ok(ADDON.getAddonInfo('name'), "No playable source found.")
        xbmcplugin.endOfDirectory(HANDLE)
        return

    for placeholder in iframe_placeholders:
        if 'data-encoded' in placeholder.attrs:
            encoded_iframe = placeholder['data-encoded']
            try:
                decoded_iframe = base64.b64decode(encoded_iframe).decode('utf-8')
                src_match = re.search(r'src="([^"]+)"', decoded_iframe)
                if src_match:
                    video_url = src_match.group(1)

                    if 'player3.funny-cats.org' in video_url:
                        continue

                    if video_url.startswith('//'):
                        video_url = 'https:' + video_url
                    
                    domain = urllib.parse.urlparse(video_url).netloc.replace('www.', '')
                    
                    list_item = xbmcgui.ListItem(f"Sursa: {domain}")
                    list_item.setInfo('video', {'title': f"Sursa: {domain}"})
                    list_item.setProperty('IsPlayable', 'true')
                    url_params = {'mode': 'play_source', 'url': video_url}
                    context_menu_items = [('Download', f'RunPlugin({sys.argv[0]}?mode=download_source&url={urllib.parse.quote_plus(video_url)})')]
                    list_item.addContextMenuItems(context_menu_items)
                    xbmcplugin.addDirectoryItem(handle=HANDLE, url=sys.argv[0] + '?' + urllib.parse.urlencode(url_params), listitem=list_item, isFolder=False)
            except Exception:
                continue
    
    xbmcplugin.endOfDirectory(HANDLE)

def list_korean_series_categories():
    icon = "https://kdrama.ro/wp-content/uploads/2023/06/image7-1016x1024.jpg"

    # "Dupa Ani" item
    list_item = xbmcgui.ListItem('Dupa Ani')
    list_item.setArt({'icon': icon, 'thumb': icon})
    url_params = {'mode': 'list_korean_series_years'}
    xbmcplugin.addDirectoryItem(handle=HANDLE, url=sys.argv[0] + '?' + urllib.parse.urlencode(url_params), listitem=list_item, isFolder=True)

    # "Seriale Coreene de Familie" item
    list_item = xbmcgui.ListItem('Seriale Coreene de Familie')
    list_item.setArt({'icon': icon, 'thumb': icon})
    url_params = {
        'mode': 'list_korean_series',
        'url': 'https://blogul-lui-atanase.ro/categorie/seriale-coreene-de-familie-50-ep/',
        'name': 'Seriale Coreene de Familie'
    }
    xbmcplugin.addDirectoryItem(handle=HANDLE, url=sys.argv[0] + '?' + urllib.parse.urlencode(url_params), listitem=list_item, isFolder=True)

    # "Seriale Coreene Contemporane" item
    list_item = xbmcgui.ListItem('Seriale Coreene Contemporane')
    list_item.setArt({'icon': icon, 'thumb': icon})
    url_params = {
        'mode': 'list_korean_series',
        'url': 'https://blogul-lui-atanase.ro/categorie/seriale-coreene-contemporane/',
        'name': 'Seriale Coreene Contemporane'
    }
    xbmcplugin.addDirectoryItem(handle=HANDLE, url=sys.argv[0] + '?' + urllib.parse.urlencode(url_params), listitem=list_item, isFolder=True)

    # "Seriale Coreene Istorice" item
    list_item = xbmcgui.ListItem('Seriale Coreene Istorice')
    list_item.setArt({'icon': icon, 'thumb': icon})
    url_params = {
        'mode': 'list_korean_series',
        'url': 'https://blogul-lui-atanase.ro/categorie/seriale-coreene-istorice/',
        'name': 'Seriale Coreene Istorice'
    }
    xbmcplugin.addDirectoryItem(handle=HANDLE, url=sys.argv[0] + '?' + urllib.parse.urlencode(url_params), listitem=list_item, isFolder=True)

    # "Mini-Seriale Coreene" item
    list_item = xbmcgui.ListItem('Mini-Seriale Coreene')
    list_item.setArt({'icon': icon, 'thumb': icon})
    url_params = {
        'mode': 'list_korean_series',
        'url': 'https://blogul-lui-atanase.ro/categorie/miniseriale-coreene/',
        'name': 'Mini-Seriale Coreene'
    }
    xbmcplugin.addDirectoryItem(handle=HANDLE, url=sys.argv[0] + '?' + urllib.parse.urlencode(url_params), listitem=list_item, isFolder=True)

    xbmcplugin.endOfDirectory(HANDLE)

def list_korean_series_years():
    try:
        response = requests.get('https://blogul-lui-atanase.ro/')
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')
    except requests.exceptions.RequestException as e:
        xbmcgui.Dialog().ok(ADDON.getAddonInfo('name'), f"Failed to fetch Korean series categories: {e}")
        return

    menu_item = soup.find('li', id='menu-item-15749')
    if menu_item:
        sub_menu = menu_item.find('ul', class_='sub-menu')
        if sub_menu:
            for item in sub_menu.find_all('li'):
                link = item.find('a')
                if link and link.has_attr('href'):
                    title = link.text.strip()
                    url = link['href']
                    list_item = xbmcgui.ListItem(title)
                    url_params = {'mode': 'list_korean_series', 'url': url, 'name': title}
                    xbmcplugin.addDirectoryItem(handle=HANDLE, url=sys.argv[0] + '?' + urllib.parse.urlencode(url_params), listitem=list_item, isFolder=True)
    
    xbmcplugin.endOfDirectory(HANDLE)


def list_korean_series(url, name, page='1'):
    page_url = f"{url}page/{page}/" if int(page) > 1 else url
    try:
        response = requests.get(page_url)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')
    except requests.exceptions.RequestException as e:
        xbmcgui.Dialog().ok(ADDON.getAddonInfo('name'), f"Failed to fetch Korean series for {name}: {e}")
        return

    for article in soup.find_all('article', class_='home-post'):
        thumb_div = article.find('div', class_='post-thumb')
        title_h2 = article.find('h2', class_='post-title')
        
        if thumb_div and title_h2:
            title_link = title_h2.find('a')
            thumb_img = thumb_div.find('img')
            if title_link:
                series_url = title_link['href']
                title = title_link['title']
                
                thumb = ''
                if thumb_img:
                    thumb = thumb_img.get('data-src', thumb_img.get('src', ''))

                description_div = article.find('div', class_='entry-content')
                description = description_div.text.strip() if description_div else ''

                list_item = xbmcgui.ListItem(title)
                list_item.setArt({'thumb': thumb, 'icon': thumb})
                list_item.setInfo('video', {'title': title, 'plot': description})
                url_params = {'mode': 'list_korean_episodes_and_sources', 'url': series_url}
                xbmcplugin.addDirectoryItem(handle=HANDLE, url=sys.argv[0] + '?' + urllib.parse.urlencode(url_params), listitem=list_item, isFolder=True)

    # Pagination
    pagination = soup.find('div', id='post-navigator')
    if pagination:
        current_page_span = pagination.find('span', class_='current')
        if current_page_span:
            next_page_link = current_page_span.find_next_sibling('a')
            if next_page_link and next_page_link.has_attr('href'):
                next_page_num = int(page) + 1
                list_item = xbmcgui.ListItem('Next Page >>')
                url_params = {'mode': 'list_korean_series', 'url': url, 'name': name, 'page': str(next_page_num)}
                xbmcplugin.addDirectoryItem(handle=HANDLE, url=sys.argv[0] + '?' + urllib.parse.urlencode(url_params), listitem=list_item, isFolder=True)

    xbmcplugin.endOfDirectory(HANDLE)

def list_movies(url, name, page='1'):
    page_url = f"{url}page/{page}/" if int(page) > 1 else url
    try:
        response = requests.get(page_url)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')
    except requests.exceptions.RequestException as e:
        xbmcgui.Dialog().ok(ADDON.getAddonInfo('name'), f"Failed to fetch movies for {name}: {e}")
        return

    for article in soup.find_all('article', class_='home-post'):
        thumb_div = article.find('div', class_='post-thumb')
        title_h2 = article.find('h2', class_='post-title')
        
        if thumb_div and title_h2:
            title_link = title_h2.find('a')
            thumb_img = thumb_div.find('img')
            if title_link:
                series_url = title_link['href']
                title = title_link['title']
                
                thumb = ''
                if thumb_img:
                    thumb = thumb_img.get('data-src', thumb_img.get('src', ''))

                description_div = article.find('div', class_='entry-content')
                description = description_div.text.strip() if description_div else ''

                is_series = False
                keywords = ['serial', 'sezon', 'episod', 'episoade']
                if any(keyword in title.lower() for keyword in keywords) or any(keyword in description.lower() for keyword in keywords):
                    is_series = True

                list_item = xbmcgui.ListItem(title)
                list_item.setArt({'thumb': thumb, 'icon': thumb})
                list_item.setInfo('video', {'title': title, 'plot': description})

                if is_series:
                    url_params = {'mode': 'list_series_episodes', 'url': series_url, 'name': title}
                else:
                    url_params = {'mode': 'list_movie_sources', 'url': series_url}
                
                xbmcplugin.addDirectoryItem(handle=HANDLE, url=sys.argv[0] + '?' + urllib.parse.urlencode(url_params), listitem=list_item, isFolder=True)

    # Pagination
    pagination = soup.find('div', id='post-navigator')
    if pagination:
        current_page_span = pagination.find('span', class_='current')
        if current_page_span:
            next_page_link = current_page_span.find_next_sibling('a')
            if next_page_link and next_page_link.has_attr('href'):
                next_page_num = int(page) + 1
                list_item = xbmcgui.ListItem('Next Page >>')
                url_params = {'mode': 'list_movies', 'url': url, 'name': name, 'page': str(next_page_num)}
                xbmcplugin.addDirectoryItem(handle=HANDLE, url=sys.argv[0] + '?' + urllib.parse.urlencode(url_params), listitem=list_item, isFolder=True)

    xbmcplugin.endOfDirectory(HANDLE)

def list_movie_sources(url):
    try:
        response = requests.get(url)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')
    except requests.exceptions.RequestException as e:
        xbmcgui.Dialog().ok(ADDON.getAddonInfo('name'), f"Failed to fetch source page: {e}")
        return

    sources_found = False

    # Find sources in <a> tags
    for a_tag in soup.find_all('a', href=True):
        video_url = a_tag['href']
        if 'netu.ac' in video_url or 'vidmoly.me' in video_url or 'waaw.ac' in video_url or 'streamtape.com' in video_url or 'ok.ru' in video_url or 'waaw.to' in video_url or 'uqload.cx' in video_url or 'vk.com' in video_url or 'sibnet.ru' in video_url or 'my.mail.ru' in video_url:
            domain = urllib.parse.urlparse(video_url).netloc.replace('www.', '')
            list_item = xbmcgui.ListItem(f"Sursa: {domain}")
            list_item.setInfo('video', {'title': f"Sursa: {domain}"})
            list_item.setProperty('IsPlayable', 'true')
            url_params = {'mode': 'play_source', 'url': video_url}
            context_menu_items = [('Download', f'RunPlugin({sys.argv[0]}?mode=download_source&url={urllib.parse.quote_plus(video_url)})')]
            list_item.addContextMenuItems(context_menu_items)
            xbmcplugin.addDirectoryItem(handle=HANDLE, url=sys.argv[0] + '?' + urllib.parse.urlencode(url_params), listitem=list_item, isFolder=False)
            sources_found = True

    # Find sources in <iframe> tags
    iframes = soup.find_all('iframe')
    for iframe in iframes:
        if iframe.has_attr('src'):
            video_url = iframe['src']
            if video_url.startswith('//'):
                video_url = 'https:' + video_url
            
            domain = urllib.parse.urlparse(video_url).netloc.replace('www.', '')
            
            list_item = xbmcgui.ListItem(f"Sursa: {domain}")
            list_item.setInfo('video', {'title': f"Sursa: {domain}"})
            list_item.setProperty('IsPlayable', 'true')
            url_params = {'mode': 'play_source', 'url': video_url}
            xbmcplugin.addDirectoryItem(handle=HANDLE, url=sys.argv[0] + '?' + urllib.parse.urlencode(url_params), listitem=list_item, isFolder=False)
            sources_found = True

    if not sources_found:
        xbmcgui.Dialog().ok(ADDON.getAddonInfo('name'), "No sources found on this page.")

    xbmcplugin.endOfDirectory(HANDLE)

def list_series_episodes(url, name):
    try:
        response = requests.get(url)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')
    except requests.exceptions.RequestException as e:
        xbmcgui.Dialog().ok(ADDON.getAddonInfo('name'), f"Failed to fetch episodes for {name}: {e}")
        return

    content = soup.find('div', class_='entry-content')
    if not content:
        return

    all_elements = content.find_all(['h3', 'p'])
    for element in all_elements:
        element_text = element.text.strip()
        if 'episodul' in element_text.lower() or 'episod' in element_text.lower():
            episode_title = element_text
            
            # Look for source links in the same element (for Korean-style formatting)
            source_links = element.find_all('a', href=True)
            if source_links:
                for source_link in source_links:
                    source_url = source_link['href']
                    source_name = source_link.text.strip()
                    if source_name and 'episodul' not in source_name.lower() and 'episod' not in source_name.lower():
                        display_title = f"{episode_title} - {source_name}"
                        list_item = xbmcgui.ListItem(display_title)
                        list_item.setProperty('IsPlayable', 'true')
                        list_item.setInfo('video', {'title': display_title})
                        url_params = {'mode': 'play_source', 'url': source_url}
                        context_menu_items = [('Download', f'RunPlugin({sys.argv[0]}?mode=download_source&url={urllib.parse.quote_plus(source_url)})')]
                        list_item.addContextMenuItems(context_menu_items)
                        xbmcplugin.addDirectoryItem(handle=HANDLE, url=sys.argv[0] + '?' + urllib.parse.urlencode(url_params), listitem=list_item, isFolder=False)

    xbmcplugin.endOfDirectory(HANDLE)

def list_korean_episodes_and_sources(url):
    try:
        response = requests.get(url)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')
    except requests.exceptions.RequestException as e:
        xbmcgui.Dialog().ok(ADDON.getAddonInfo('name'), f"Failed to fetch episode page: {e}")
        return

    content = soup.find('div', class_='entry-content')
    if not content:
        return

    # Check for season headers (h2, h3 or h4)
    season_headers = content.find_all(['h2', 'h3', 'h4'], string=re.compile(r'SEZONUL', re.IGNORECASE))

    if season_headers:
        for i, header in enumerate(season_headers):
            season_title = header.text.strip()
            # Pass the entire content and the start element index to the next function
            url_params = {
                'mode': 'list_korean_season_episodes',
                'url': url, # Pass the page URL
                'season_title': season_title
            }
            list_item = xbmcgui.ListItem(season_title)
            xbmcplugin.addDirectoryItem(handle=HANDLE, url=sys.argv[0] + '?' + urllib.parse.urlencode(url_params), listitem=list_item, isFolder=True)
        xbmcplugin.endOfDirectory(HANDLE)
        return

    # Original logic for pages without seasons
    # First check for h3 tags with episode information (for Korean historical/family series)
    elements = content.find_all(['h3', 'p'])  # Look for both h3 and p tags
    current_episode_title = ""
    
    for element in elements:
        element_text = element.text.strip()
        
        # Check for episode title in h3 or p tags
        if 'episodul' in element_text.lower() or 'episod' in element_text.lower():
            current_episode_title = re.split(r'–|-', element_text)[0].strip()
            continue
            
        # Look for links in h3 and p tags that might contain sources
        source_links = element.find_all('a', href=True)
        if source_links and current_episode_title:
            for link in source_links:
                source_url = link['href']
                source_name = link.text.strip()
                if not source_name or 'episodul' in source_name.lower() or 'episod' in source_name.lower():
                    continue
                display_title = f"{current_episode_title} - {source_name}"
                list_item = xbmcgui.ListItem(display_title)
                list_item.setProperty('IsPlayable', 'true')
                list_item.setInfo('video', {'title': display_title})
                url_params = {'mode': 'play_source', 'url': source_url}
                context_menu_items = [('Download', f'RunPlugin({sys.argv[0]}?mode=download_source&url={urllib.parse.quote_plus(source_url)})')]
                list_item.addContextMenuItems(context_menu_items)
                xbmcplugin.addDirectoryItem(handle=HANDLE, url=sys.argv[0] + '?' + urllib.parse.urlencode(url_params), listitem=list_item, isFolder=False)

    xbmcplugin.endOfDirectory(HANDLE)

def list_korean_season_episodes(url, season_title):
    try:
        response = requests.get(url)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')
    except requests.exceptions.RequestException as e:
        xbmcgui.Dialog().ok(ADDON.getAddonInfo('name'), f"Failed to fetch episode page: {e}")
        return

    content = soup.find('div', class_='entry-content')
    if not content:
        return

    start_element = content.find(['h2', 'h3', 'h4'], string=re.compile(season_title, re.IGNORECASE))
    if not start_element:
        return

    current_episode_title = ""
    for element in start_element.find_next_siblings():
        if element.name in ['h2', 'h3', 'h4'] and 'SEZONUL' in element.text.upper():
            break  # Stop when the next season starts

        if element.name in ['p', 'h3']:
            element_text = element.text.strip()
            if 'episodul' in element_text.lower() or 'episod' in element_text.lower():
                current_episode_title = re.split(r'–|-', element_text)[0].strip()
            
            source_links = element.find_all('a', href=True)
            if source_links and current_episode_title:
                for link in source_links:
                    source_url = link['href']
                    source_name = link.text.strip()
                    if not source_name or 'episodul' in source_name.lower() or 'episod' in source_name.lower():
                        continue
                    
                    display_title = f"{current_episode_title} - {source_name}"
                    list_item = xbmcgui.ListItem(display_title)
                    list_item.setProperty('IsPlayable', 'true')
                    list_item.setInfo('video', {'title': display_title})
                    url_params = {'mode': 'play_source', 'url': source_url}
                    context_menu_items = [('Download', f'RunPlugin({sys.argv[0]}?mode=download_source&url={urllib.parse.quote_plus(source_url)})')]
                    list_item.addContextMenuItems(context_menu_items)
                    xbmcplugin.addDirectoryItem(handle=HANDLE, url=sys.argv[0] + '?' + urllib.parse.urlencode(url_params), listitem=list_item, isFolder=False)

    xbmcplugin.endOfDirectory(HANDLE)

def list_movies_categories():
    movies_categories = [
        {'title': 'Filme de epoca', 'url': 'https://blogul-lui-atanase.ro/categorie/nostalgia/'},
        {'title': 'Filme de Craciun', 'url': 'https://blogul-lui-atanase.ro/categorie/filme-de-craciun/'},
        {'title': 'Filme Coreene', 'url': 'https://blogul-lui-atanase.ro/categorie/filme-coreene/'},
        {'title': 'Filme Chinezesti', 'url': 'https://blogul-lui-atanase.ro/categorie/filme-chinezesti/'},
        {'title': 'Filme Japoneze', 'url': 'https://blogul-lui-atanase.ro/categorie/serialefilme-japoneze/'},
        {'title': 'Filme Indiene', 'url': 'https://blogul-lui-atanase.ro/categorie/filme-indiene/'},
        {'title': 'Filme Turcesti', 'url': 'https://blogul-lui-atanase.ro/categorie/filme-turcesti/'}
    ]

    for category in movies_categories:
        list_item = xbmcgui.ListItem(category['title'])
        icon = "https://1.bp.blogspot.com/-5utXzUd3Wk0/XcatUqtM9pI/AAAAAAAACTU/8Jbt1d8gO8Y7XVLGQnjHYYnJ9ou1_kTLACLcBGAsYHQ/s1600/www.tvnowstream.de.jpg"
        list_item.setArt({'icon': icon, 'thumb': icon})
        url_params = {
            'mode': 'list_movies',
            'url': category['url'],
            'name': category['title']
        }
        xbmcplugin.addDirectoryItem(handle=HANDLE, url=sys.argv[0] + '?' + urllib.parse.urlencode(url_params), listitem=list_item, isFolder=True)

    xbmcplugin.endOfDirectory(HANDLE)

def list_turkish_series_categories():
    # Item for "Seriale Turcesti (Toate)"
    list_item = xbmcgui.ListItem('Seriale Turcesti (Toate)')
    turk_icon = "https://fuzzy.ro/wp-content/uploads/2023/01/seriale-turcesti.jpg"
    list_item.setArt({'icon': turk_icon, 'thumb': turk_icon})
    url_params = {
        'mode': 'list_turkish_series',
        'url': 'https://www.terasacucarti.com/n-toate-serialele-turcesti-subtitrate/'
    }
    xbmcplugin.addDirectoryItem(handle=HANDLE, url=sys.argv[0] + '?' + urllib.parse.urlencode(url_params), listitem=list_item, isFolder=True)

    # Item for "Seriale Turcesti Finalizate"
    list_item = xbmcgui.ListItem('Seriale turcesti finalizate')
    turk_final_icon = "https://fuzzy.ro/wp-content/uploads/2023/01/seriale-turcesti.jpg"
    list_item.setArt({'icon': turk_final_icon, 'thumb': turk_final_icon})
    url_params_finished = {
        'mode': 'list_finished_turkish_series',
        'url': 'https://www.terasacucarti.com/a-seriale-turcesti-finalizate-terasa-cu-carti/'
    }
    xbmcplugin.addDirectoryItem(handle=HANDLE, url=sys.argv[0] + '?' + urllib.parse.urlencode(url_params_finished), listitem=list_item, isFolder=True)

    # Item for "Alte Seriale"
    list_item = xbmcgui.ListItem('Alte Seriale')
    alte_icon = "https://fuzzy.ro/wp-content/uploads/2023/01/seriale-turcesti.jpg"
    list_item.setArt({'icon': alte_icon, 'thumb': alte_icon})
    url_params_alte = {
        'mode': 'list_alte_seriale',
        'url': 'https://www.terasacucarti.com/alte-seriale-subtitrate-in-romana/'
    }
    xbmcplugin.addDirectoryItem(handle=HANDLE, url=sys.argv[0] + '?' + urllib.parse.urlencode(url_params_alte), listitem=list_item, isFolder=True)
    
    xbmcplugin.endOfDirectory(HANDLE)

def download_source(url):
    resolved_url = resolveurl.resolve(url)
    if resolved_url:
        # The most reliable way to handle downloads in Kodi for external URLs
        # is to use the Download builtin with the resolved URL
        xbmc.executebuiltin(f'Download("{resolved_url}")')
    else:
        xbmcgui.Dialog().ok(ADDON.getAddonInfo('name'), "Could not resolve video URL for download.")

def router(paramstring):
    params = dict(urllib.parse.parse_qsl(paramstring))
    mode = params.get('mode')
    name = params.get('name')
    url = params.get('url')
    shows = params.get('shows')
    episodes = params.get('episodes')
    season = params.get('season')
    latest_url = params.get('latest_url')
    page = params.get('page', '1')
    season_title = params.get('season_title')

    if mode is None:
        list_main_menu()
    elif mode == 'list_show_categories':
        list_show_categories(shows, name, latest_url)
    elif mode == 'list_latest':
        list_latest(url, name)
    elif mode == 'list_episodes':
        list_episodes(url, name)
    elif mode == 'list_episodes_for_season':
        list_episodes_for_season(episodes, season, name)
    elif mode == 'list_search_results':
        list_search_results(url)
    elif mode == 'list_sources':
        list_sources(url)
    elif mode == 'play_source':
        play_source(url)
    elif mode == 'search':
        search()
    elif mode == 'list_turkish_series_categories':
        list_turkish_series_categories()
    elif mode == 'list_turkish_series' or mode == 'list_finished_turkish_series' or mode == 'list_alte_seriale':
        list_turkish_series(url, mode, page)
    elif mode == 'list_turkish_episodes':
        list_turkish_episodes(url, name)
    elif mode == 'list_turkish_sources':
        list_turkish_sources(url)
    elif mode == 'list_korean_series_categories':
        list_korean_series_categories()
    elif mode == 'list_korean_series_years':
        list_korean_series_years()
    elif mode == 'list_korean_series':
        list_korean_series(url, name, page)
    elif mode == 'list_korean_episodes_and_sources':
        list_korean_episodes_and_sources(url)
    elif mode == 'list_korean_season_episodes':
        list_korean_season_episodes(url, season_title)
    elif mode == 'list_movies_categories':
        list_movies_categories()
    elif mode == 'list_movies':
        list_movies(url, name, page)
    elif mode == 'list_movie_sources':
        list_movie_sources(url)
    elif mode == 'list_series_episodes':
        list_series_episodes(url, name)
    elif mode == 'download_source':
        download_source(url)

if __name__ == '__main__':
    router(sys.argv[2][1:])
