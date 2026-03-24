'''
    Dailymotion_com

    This program is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with this program.  If not, see <http://www.gnu.org/licenses/>.
'''

import six
from kodi_six import xbmcplugin, xbmcaddon, xbmcgui, xbmc, xbmcvfs
import sys
import re
import json
import datetime
import tempfile
import requests
from six.moves import urllib_parse, html_parser

pluginhandle = int(sys.argv[1])
addon = xbmcaddon.Addon()
addonID = addon.getAddonInfo('id')
_icon = addon.getAddonInfo('icon')
_fanart = addon.getAddonInfo('fanart')
_path = addon.getAddonInfo('path')
_ipath = '{0}/resources/images/'.format(_path)
_kodiver = float(xbmcaddon.Addon('xbmc.addon').getAddonInfo('version')[:4])

if hasattr(xbmcvfs, "translatePath"):
    translate_path = xbmcvfs.translatePath
else:
    translate_path = xbmc.translatePath
channelFavsFile = translate_path("special://profile/addon_data/{0}/{0}.favorites".format(addonID))
HistoryFile = translate_path("special://profile/addon_data/{0}/{0}.history".format(addonID))
cookie_file = translate_path("special://profile/addon_data/{0}/cookies".format(addonID))
pDialog = xbmcgui.DialogProgress()
familyFilter = '1'

if not xbmcvfs.exists('special://profile/addon_data/' + addonID + '/settings.xml'):
    addon.openSettings()

if addon.getSetting('family_filter') == 'false':
    familyFilter = '0'

force_mode = addon.getSetting("forceViewMode") == "true"
if force_mode:
    menu_mode = addon.getSetting("MenuMode")
    video_mode = addon.getSetting("VideoMode")

maxVideoQuality = addon.getSetting("maxVideoQuality")
downloadDir = addon.getSetting("downloadDir")
qual = ['240', '380', '480', '720', '1080', '1440', '2160']
maxVideoQuality = qual[int(maxVideoQuality)]
language = addon.getSetting("language")
languages = ["ar_ES", "br_PT", "ca_EN", "ca_FR", "de_DE", "es_ES", "fr_FR",
             "in_EN", "id_ID", "it_IT", "ci_FR", "my_MS", "mx_ES", "pk_EN",
             "ph_EN", "tr_TR", "en_GB", "en_US", "vn_VI", "kr_KO", "tw_TW"]
language = languages[int(language)]
dmUser = addon.getSetting("dmUser")
enablePlaylistImport = addon.getSetting('enable_playlist_import') == 'true'
enableUserImport = addon.getSetting('enable_user_import') == 'true'
itemsPerPage = addon.getSetting("itemsPerPage")
itemsPage = ["25", "50", "75", "100"]
itemsPerPage = itemsPage[int(itemsPerPage)]
urlMain = "https://api.dailymotion.com"
_UA = 'Mozilla/5.0 (Linux; Android 7.1.1; Pixel Build/NMF26O) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/55.0.2883.91 Mobile Safari/537.36'


class MLStripper(html_parser.HTMLParser):
    def __init__(self):
        self.reset()
        self.fed = []

    def handle_data(self, d):
        self.fed.append(d)

    def get_data(self):
        return ''.join(self.fed)


def strip_tags(html):
    parser = html_parser.HTMLParser()
    html = parser.unescape(html)
    s = MLStripper()
    s.feed(html)
    return s.get_data()


def strip_tags2(text):
    clean = re.compile('<.*?>')
    return re.sub(clean, '', text)


def index():
    addDir(translation(30025), "{0}/videos?fields=description,duration,id,owner.username,taken_time,thumbnail_large_url,title,views_total&list=what-to-watch&no_live=1&limit={1}&family_filter={2}&localization={3}&page=1".format(urlMain, itemsPerPage, familyFilter, language), 'listVideos', "{0}what_to_watch.png".format(_ipath))
    addDir("Seriale", "seriale", 'seriale_menu', "{0}channels.png".format(_ipath))
    addDir(translation(30015), "{0}/videos?fields=description,duration,id,owner.username,taken_time,thumbnail_large_url,title,views_total&sort=trending&no_live=1&limit={1}&family_filter={2}&localization={3}&page=1".format(urlMain, itemsPerPage, familyFilter, language), 'listVideos', "{0}trending.png".format(_ipath))
    addDir(translation(30016), "{0}/videos?fields=description,duration,id,owner.username,taken_time,thumbnail_large_url,title,views_total&featured=1&no_live=1&limit={1}&family_filter={2}&localization={3}&page=1".format(urlMain, itemsPerPage, familyFilter, language), 'listVideos', "{0}featured.png".format(_ipath))
    addDir(translation(30003), "{0}/videos?fields=id,thumbnail_large_url,title,views_last_hour&availability=1&live_onair=1&sort=visited-month&limit={1}&family_filter={2}&localization={3}&page=1".format(urlMain, itemsPerPage, familyFilter, language), 'listLive', "{0}live.png".format(_ipath))
    addDir(translation(30006), "", 'listChannels', "{0}channels.png".format(_ipath))
    addDir(translation(30007), "{0}/users?fields=username,avatar_large_url,videos_total,views_total&sort=popular&limit={1}&family_filter={2}&localization={3}&page=1".format(urlMain, itemsPerPage, familyFilter, language), 'listUsers', "{0}users.png".format(_ipath))
    addDir(translation(30002), "{0}/videos?fields=description,duration,id,owner.username,taken_time,thumbnail_large_url,title,views_total&search=&sort=relevance&limit={1}&family_filter={2}&localization={3}&page=1".format(urlMain, itemsPerPage, familyFilter, language), 'search', "{0}search.png".format(_ipath))
    addDir("{0} {1}".format(translation(30002), translation(30003)), "", 'livesearch', "{0}search_live.png".format(_ipath))
    addDir("{0} {1}".format(translation(30002), translation(30007)), "", 'usersearch', "{0}search_users.png".format(_ipath))
    addDir(translation(30115), "", "History", "{0}search.png".format(_ipath))
    if dmUser:
        addDir(translation(30034), "", "personalMain", "{0}my_stuff.png".format(_ipath))
    else:
        addFavDir(translation(30024), "", "favouriteUsers", "{0}favourite_users.png".format(_ipath))
    xbmcplugin.endOfDirectory(pluginhandle)
    xbmcplugin.setContent(pluginhandle, "addons")
    if force_mode:
        xbmc.executebuiltin('Container.SetViewMode({0})'.format(menu_mode))


def update_listitem(li, infoLabels):
    if isinstance(infoLabels, dict):
        labels = infoLabels.copy()
        if _kodiver > 19.8:
            vtag = li.getVideoInfoTag()
            if labels.get('Title'):
                vtag.setTitle(labels['Title'])
            if labels.get('Plot'):
                vtag.setPlot(labels['Plot'])
            if labels.get('Duration'):
                vtag.setDuration(labels['Duration'])
            if labels.get('Aired'):
                vtag.setFirstAired(labels['Aired'])
            if labels.get('Episode'):
                vtag.setEpisode(int(labels['Episode']))
        else:
            li.setInfo(type='Video', infoLabels=labels)

    return


def make_listitem(name='', labels=None, path=''):
    if _kodiver >= 18.0:  # Include Kodi version 18 in the condition
        offscreen = True
        if name:
            li = xbmcgui.ListItem(name, offscreen=offscreen)
        else:
            li = xbmcgui.ListItem(path=path, offscreen=offscreen)
    else:
        if name:
            li = xbmcgui.ListItem(name)
        else:
            li = xbmcgui.ListItem(path=path)

    if isinstance(labels, dict):
        update_listitem(li, labels)
    return li


def personalMain():
    addDir(translation(30041), "{0}/user/{1}/videos?fields=description,duration,id,owner.username,taken_time,thumbnail_large_url,title,views_total&sort=recent&limit={2}&family_filter={3}&localization={4}&page=1".format(urlMain, dmUser, itemsPerPage, familyFilter, language), 'listVideos', "{0}videos.png".format(_ipath))
    addDir(translation(30035), "{0}/user/{1}/following?fields=username,avatar_large_url,videos_total,views_total&sort=popular&limit={2}&family_filter={3}&localization={4}&page=1".format(urlMain, dmUser, itemsPerPage, familyFilter, language), 'listUsers', "{0}contacts.png".format(_ipath))
    addDir(translation(30036), "{0}/user/{1}/subscriptions?fields=description,duration,id,owner.username,taken_time,thumbnail_large_url,title,views_total&sort=recent&limit={2}&family_filter={3}&localization={4}&page=1".format(urlMain, dmUser, itemsPerPage, familyFilter, language), 'listVideos', "{0}following.png".format(_ipath))
    addDir(translation(30037), "{0}/user/{1}/favorites?fields=description,duration,id,owner.username,taken_time,thumbnail_large_url,title,views_total&sort=recent&limit={2}&family_filter={3}&localization={4}&page=1".format(urlMain, dmUser, itemsPerPage, familyFilter, language), 'listVideos', "{0}favourites.png".format(_ipath))
    addDir(translation(30038), "{0}/user/{1}/playlists?fields=id,name,videos_total&sort=recent&limit={2}&family_filter={3}&localization={4}&page=1".format(urlMain, dmUser, itemsPerPage, familyFilter, language), 'listUserPlaylists', "{0}playlists.png".format(_ipath))
    xbmcplugin.endOfDirectory(pluginhandle)
    xbmcplugin.setContent(pluginhandle, 'addons')
    if force_mode:
        xbmc.executebuiltin('Container.SetViewMode({0})'.format(menu_mode))


def listUserPlaylists(url):
    content = getUrl2(url)
    content = json.loads(content)
    for item in content['list']:
        vid = item['id']
        title = item['name'].encode('utf-8') if six.PY2 else item['name']
        vids = item['videos_total']
        addDir("{0} ({1})".format(title, vids), urllib_parse.quote_plus("{0}_{1}_{2}".format(vid, dmUser, title)), 'showPlaylist', "{0}playlists.png".format(_ipath))
    if content['has_more']:
        currentPage = content['page']
        nextPage = currentPage + 1
        addDir("{0} ({1})".format(translation(30001), nextPage), url.replace("page={0}".format(currentPage), "page={0}".format(nextPage)), 'listUserPlaylists', "{0}next_page2.png".format(_ipath))
    xbmcplugin.setContent(pluginhandle, "episodes")
    xbmcplugin.endOfDirectory(pluginhandle)


def showPlaylist(pid):
    url = "{0}/playlist/{1}/videos?fields=description,duration,id,owner.username,taken_time,thumbnail_large_url,title,views_total&sort=recent&limit={2}&family_filter={3}&localization={4}&page=1".format(urlMain, pid, itemsPerPage, familyFilter, language)
    listVideos(url)


def favouriteUsers():
    xbmcplugin.addSortMethod(pluginhandle, xbmcplugin.SORT_METHOD_LABEL)
    if xbmcvfs.exists(channelFavsFile):
        with open(channelFavsFile, 'r') as fh:
            content = fh.read()
            match = re.compile('###USER###=(.+?)###THUMB###=(.*?)###END###', re.DOTALL).findall(content)
            for user, thumb in match:
                addUserFavDir(user, 'owner:{0}'.format(user), 'sortVideos1', thumb)
    xbmcplugin.endOfDirectory(pluginhandle)
    xbmcplugin.setContent(pluginhandle, "addons")
    if force_mode:
        xbmc.executebuiltin('Container.SetViewMode({0})'.format(menu_mode))


def listChannels():
    content = getUrl2("{0}/channels?family_filter={1}&localization={2}".format(urlMain, familyFilter, language))
    content = json.loads(content)
    for item in content['list']:
        cid = item['id']
        title = item['name'].encode('utf-8') if six.PY2 else item['name']
        desc = item['description'].encode('utf-8') if six.PY2 else item['description']
        addDir(title, 'channel:{0}'.format(cid), 'sortVideos1', '{0}channels.png'.format(_ipath), desc)
    xbmcplugin.endOfDirectory(pluginhandle)


def sortVideos1(url):
    item_type = url[:url.find(":")]
    gid = url[url.find(":") + 1:]
    if item_type == "group":
        url = "{0}/group/{1}/videos?fields=description,duration,id,owner.username,taken_time,thumbnail_large_url,title,views_total&sort=recent&limit={2}&family_filter={3}&localization={4}&page=1".format(urlMain, gid, itemsPerPage, familyFilter, language)
    else:
        url = "{0}/videos?fields=description,duration,id,owner.username,taken_time,thumbnail_large_url,title,views_total&{1}={2}&sort=recent&limit={3}&family_filter={4}&localization={5}&page=1".format(urlMain, item_type, gid, itemsPerPage, familyFilter, language)
    addDir(translation(30015), url.replace("sort=recent", "sort=trending"), 'listVideos', "{0}trending.png".format(_ipath))
    addDir(translation(30008), url, 'listVideos', "{0}most_recent.png".format(_ipath))
    addDir(translation(30009), url.replace("sort=recent", "sort=visited"), 'sortVideos2', "{0}most_viewed.png".format(_ipath))
    if item_type == "owner":
        addDir("- {0}".format(translation(30038)), "{0}/user/{1}/playlists?fields=id,name,videos_total&sort=recent&limit={2}&family_filter={3}&localization={4}&page=1".format(urlMain, gid, itemsPerPage, familyFilter, language), 'listUserPlaylists', "{0}playlists.png".format(_ipath))
    xbmcplugin.endOfDirectory(pluginhandle)
    xbmcplugin.setContent(pluginhandle, 'addons')
    if force_mode:
        xbmc.executebuiltin('Container.SetViewMode({0})'.format(menu_mode))


def sortVideos2(url):
    addDir(translation(30010), url.replace("sort=visited", "sort=visited-hour"), "listVideos", "{0}most_viewed.png".format(_ipath))
    addDir(translation(30011), url.replace("sort=visited", "sort=visited-today"), "listVideos", "{0}most_viewed.png".format(_ipath))
    addDir(translation(30012), url.replace("sort=visited", "sort=visited-week"), "listVideos", "{0}most_viewed.png".format(_ipath))
    addDir(translation(30013), url.replace("sort=visited", "sort=visited-month"), "listVideos", "{0}most_viewed.png".format(_ipath))
    addDir(translation(30014), url, 'listVideos', "{0}most_viewed.png".format(_ipath))
    xbmcplugin.endOfDirectory(pluginhandle)
    xbmcplugin.setContent(pluginhandle, 'addons')
    if force_mode:
        xbmc.executebuiltin('Container.SetViewMode({0})'.format(menu_mode))


def sortUsers1():
    url = "{0}/users?fields=username,avatar_large_url,videos_total,views_total&sort=popular&limit={1}&family_filter={2}&localization={3}&page=1".format(urlMain, itemsPerPage, familyFilter, language)
    addDir(translation(30040), url, 'sortUsers2', "")
    addDir(translation(30016), "{0}&filters=featured".format(url), 'sortUsers2', "")
    addDir(translation(30017), "{0}&filters=official".format(url), 'sortUsers2', "")
    addDir(translation(30018), "{0}&filters=creative".format(url), 'sortUsers2', "")
    xbmcplugin.endOfDirectory(pluginhandle)


def sortUsers2(url):
    addDir(translation(30019), url, 'listUsers', "")
    addDir(translation(30020), url.replace("sort=popular", "sort=commented"), 'listUsers', "")
    addDir(translation(30021), url.replace("sort=popular", "sort=rated"), 'listUsers', "")
    xbmcplugin.endOfDirectory(pluginhandle)


def listVideos(url):
    xbmcplugin.setContent(pluginhandle, 'episodes')
    content = getUrl2(url)
    content = json.loads(content)
    count = 1
    for item in content['list']:
        vid = item['id']
        title = item['title'].encode('utf-8') if six.PY2 else item['title']
        desc = strip_tags(item['description']).encode('utf-8') if six.PY2 else strip_tags2(item['description'])
        duration = item['duration']
        user = item['owner.username']
        date = item['taken_time']
        thumb = item['thumbnail_large_url']
        views = item['views_total']
        try:
            date = datetime.datetime.fromtimestamp(int(date)).strftime('%Y-%m-%d')
        except:
            date = ""
        temp = ("User: {0}  |  {1} Views  |  {2}".format(user, views, date))
        temp = temp.encode('utf-8') if six.PY2 else temp
        try:
            desc = "{0}\n{1}".format(temp, desc)
        except:
            desc = ""
        if user == "hulu":
            pass
        elif user == "cracklemovies":
            pass
        elif user == "ARTEplus7":
            addLink(title, vid, 'playArte', thumb.replace("\\", ""), user, desc, duration, date, count)
            count += 1
        else:
            addLink(title, vid, 'playVideo', thumb.replace("\\", ""), user, desc, duration, date, count)
            count += 1
    if content['has_more']:
        currentPage = content['page']
        nextPage = currentPage + 1
        addDir("{0} ({1})".format(translation(30001), nextPage), url.replace("page={0}".format(currentPage), "page={0}".format(nextPage)), 'listVideos', "{0}next_page2.png".format(_ipath))
    xbmcplugin.endOfDirectory(pluginhandle)
    xbmcplugin.setContent(pluginhandle, "episodes")
    if force_mode:
        xbmc.executebuiltin('Container.SetViewMode({0})'.format(video_mode))


def listUsers(url):
    content = getUrl2(url)
    content = json.loads(content)
    for item in content['list']:
        if item['username']:
            user = item['username'].encode('utf-8') if six.PY2 else item['username']
            thumb = item['avatar_large_url']
            videos = item['videos_total']
            views = item['views_total']
            addUserDir(user, 'owner:{0}'.format(user), 'sortVideos1', thumb.replace("\\", ""), "Views: {0}\nVideos: {1}".format(views, videos))
    if content['has_more']:
        currentPage = content['page']
        nextPage = currentPage + 1
        addDir("{0} ({1})".format(translation(30001), nextPage), url.replace("page={0}".format(currentPage), "page={0}".format(nextPage)), 'listUsers', "{0}next_page.png".format(_ipath))
    xbmcplugin.endOfDirectory(pluginhandle)
    xbmcplugin.setContent(pluginhandle, "addons")
    if force_mode:
        xbmc.executebuiltin('Container.SetViewMode({0})'.format(menu_mode))


def listLive(url):
    content = getUrl2(url)
    content = json.loads(content)
    for item in content['list']:
        title = item['title'].encode('utf-8') if six.PY2 else item['title']
        vid = item['id']
        thumb = item['thumbnail_large_url']
        views = item['views_last_hour']
        addLiveLink(title, vid, 'playLiveVideo', thumb.replace("\\", ""), 'Views: {}'.format(views))
    if content['has_more']:
        currentPage = content['page']
        nextPage = currentPage + 1
        addDir("{0} ({1})".format(translation(30001), nextPage), url.replace("page={0}".format(currentPage), "page={0}".format(nextPage)), 'listLive', "{0}next_page2.png".format(_ipath))
    xbmcplugin.endOfDirectory(pluginhandle)
    xbmcplugin.setContent(pluginhandle, "episodes")
    if force_mode:
        xbmc.executebuiltin('Container.SetViewMode({0})'.format(menu_mode))


def playVideo(vid, live=False):
    if live:
        url = getStreamUrl(vid, live=True)
    else:
        url = getStreamUrl(vid)
    xbmc.log("DAILYMOTION - FinalUrl = {0}".format(url), xbmc.LOGDEBUG)

    if url:
        subs = []
        if isinstance(url, tuple):
            url, subs = url
        listitem = xbmcgui.ListItem(path=url)
        if subs:
            listitem.setSubtitles(subs)
        if '.m3u8' in url:
            listitem.setMimeType("application/x-mpegURL")
        else:
            listitem.setMimeType("video/mp4")
        listitem.setContentLookup(False)
        xbmcplugin.setResolvedUrl(pluginhandle, True, listitem=listitem)
    else:
        xbmcgui.Dialog().notification('Info:', translation(30022), _icon, 5000, False)


def s(elem):
    if elem[0] == "auto":
        return 1
    else:
        return int(elem[0].split("@")[0])


def getStreamUrl(vid, live=False):
    xbmc.log('DAILYMOTION - url is {0}'.format(url), xbmc.LOGDEBUG)
    headers = {'User-Agent': _UA,
               'Origin': 'https://www.dailymotion.com',
               'Referer': 'https://www.dailymotion.com/'}
    cookie = {'lang': language,
              'ff': "on" if familyFilter == "1" else "off"}
    r = requests.get("https://www.dailymotion.com/player/metadata/video/{0}".format(vid), headers=headers, cookies=cookie)
    content = r.json()
    if content.get('error'):
        Error = (content['error']['type'])
        xbmcgui.Dialog().notification('Info:', Error, _icon, 5000, False)
        return
    else:
        cc = content['qualities']
        cc = list(cc.items())
        cc = sorted(cc, key=s, reverse=True)
        subs = content.get('subtitles', {}).get('data')
        if subs:
            subs = [subs[x].get('urls')[0] for x in subs.keys()]
        m_url = ''
        other_playable_url = []

        for source, json_source in cc:
            source = source.split("@")[0]
            for item in json_source:
                m_url = item.get('url', None)
                xbmc.log("DAILYMOTION - m_url = {0}".format(m_url), xbmc.LOGDEBUG)
                if m_url:
                    if not live:
                        if source == "auto":
                            mbtext = requests.get(m_url, headers=headers).text
                            mb = re.findall('NAME="([^"]+)",PROGRESSIVE-URI="([^"]+)"', mbtext)
                            if not mb or checkUrl(mb[-1][1].split('#cell')[0]) is False:
                                mb = re.findall(r'NAME="([^"]+)".*\n([^\n]+)', mbtext)
                            mb = sorted(mb, key=s, reverse=True)
                            for quality, strurl in mb:
                                quality = quality.split("@")[0]
                                if int(quality) <= int(maxVideoQuality):
                                    strurl = '{0}|{1}'.format(strurl.split('#cell')[0], urllib_parse.urlencode(headers))
                                    xbmc.log('Selected URL is: {0}'.format(strurl), xbmc.LOGDEBUG)
                                    return (strurl, subs) if subs else strurl

                        elif int(source) <= int(maxVideoQuality):
                            if 'video' in item.get('type', None):
                                return '{0}|{1}'.format(m_url, urllib_parse.urlencode(headers))

                    else:
                        m_url = m_url.replace('dvr=true&', '')
                        if '.m3u8?sec' in m_url:
                            m_url1 = m_url.split('?sec=')
                            the_url = '{0}?redirect=0&sec={1}'.format(m_url1[0], urllib_parse.quote(m_url1[1]))
                            rr = requests.get(the_url, cookies=r.cookies.get_dict(), headers=headers)
                            if rr.status_code > 200:
                                rr = requests.get(m_url, cookies=r.cookies.get_dict(), headers=headers)
                            mb = re.findall('NAME="([^"]+)"\n(.+)', rr.text)
                            mb = sorted(mb, key=s, reverse=True)
                            for quality, strurl in mb:
                                quality = quality.split("@")[0]
                                if int(quality) <= int(maxVideoQuality):
                                    if not strurl.startswith('http'):
                                        strurl1 = re.findall('(.+/)', the_url)[0]
                                        strurl = strurl1 + strurl
                                    strurl = '{0}|{1}'.format(strurl.split('#cell')[0], urllib_parse.urlencode(headers))
                                    xbmc.log('Selected URL is: {0}'.format(strurl), xbmc.LOGDEBUG)
                                    return strurl
                    if type(m_url) is list:
                        m_url = '?sec='.join(m_url)
                    other_playable_url.append(m_url)

        if len(other_playable_url) > 0:  # probably not needed, only for last resort
            for m_url in other_playable_url:
                xbmc.log("DAILYMOTION - other m_url = {0}".format(m_url), xbmc.LOGDEBUG)
                m_url = m_url.replace('dvr=true&', '')
                if '.m3u8?sec' in m_url:
                    rr = requests.get(m_url, cookies=r.cookies.get_dict(), headers=headers)
                    mburl = re.findall('(http.+)', rr.text)[0].split('#cell')[0]
                    if rr.headers.get('set-cookie'):
                        xbmc.log('DAILYMOTION - adding cookie to url', xbmc.LOGDEBUG)
                        strurl = '{0}|Cookie={1}'.format(mburl, rr.headers['set-cookie'])
                    else:
                        mb = requests.get(mburl, headers=headers).text
                        mb = re.findall('NAME="([^"]+)"\n(.+)', mb)
                        mb = sorted(mb, key=s, reverse=True)
                        for quality, strurl in mb:
                            quality = quality.split("@")[0]
                            if int(quality) <= int(maxVideoQuality):
                                if not strurl.startswith('http'):
                                    strurl1 = re.findall('(.+/)', mburl)[0]
                                    strurl = strurl1 + strurl
                                break

                    xbmc.log("DAILYMOTION - Calculated url = {0}".format(strurl), xbmc.LOGDEBUG)
                    return strurl


def queueVideo(url, name):
    playlist = xbmc.PlayList(xbmc.PLAYLIST_VIDEO)
    listitem = xbmcgui.ListItem(name)
    playlist.add(url, listitem)


def downloadVideo(title, vid):
    global downloadDir
    if not downloadDir:
        xbmcgui.Dialog().notification('Download:', translation(30110), _icon, 5000, False)
        return
    url, hstr = getStreamUrl(vid).split('|')
    if six.PY2:
        vidfile = xbmc.makeLegalFilename((downloadDir + title.decode('utf-8') + '.mp4').encode('utf-8'))
    else:
        vidfile = xbmcvfs.makeLegalFilename(downloadDir + title + '.mp4')
    if not xbmcvfs.exists(vidfile):
        tmp_file = tempfile.mktemp(dir=downloadDir, suffix='.mp4')
        if six.PY2:
            tmp_file = xbmc.makeLegalFilename(tmp_file)
        else:
            tmp_file = xbmcvfs.makeLegalFilename(tmp_file)
        pDialog.create('Dailymotion', '{0}[CR]{1}'.format(translation(30044), title))
        dfile = requests.get(url, headers=dict(urllib_parse.parse_qsl(hstr)), stream=True)
        totalsize = float(dfile.headers['content-length'])
        handle = open(tmp_file, "wb")
        chunks = 0
        for chunk in dfile.iter_content(chunk_size=2097152):
            if chunk:  # filter out keep-alive new chunks
                handle.write(chunk)
                chunks += 1
                percent = int(float(chunks * 209715200) / totalsize)
                pDialog.update(percent)
                if pDialog.iscanceled():
                    handle.close()
                    xbmcvfs.delete(tmp_file)
                    break
        handle.close()
        try:
            xbmcvfs.rename(tmp_file, vidfile)
            return vidfile
        except:
            return tmp_file
    else:
        xbmcgui.Dialog().notification('Download:', translation(30109), _icon, 5000, False)


def playArte(aid):
    try:
        content = getUrl2("http://www.dailymotion.com/video/{0}".format(aid))
        match = re.compile(r'<a\s*class="link"\s*href="http://videos.arte.tv/(.+?)/videos/(.+?).html">', re.DOTALL).findall(content)
        lang = match[0][0]
        vid = match[0][1]
        url = "http://videos.arte.tv/{0}/do_delegate/videos/{1},view,asPlayerXml.xml".format(lang, vid)
        content = getUrl2(url)
        match = re.compile(r'<video\s*lang="{0}"\s*ref="(.+?)"'.format(lang), re.DOTALL).findall(content)
        url = match[0]
        content = getUrl2(url)
        match1 = re.compile(r'<url\s*quality="hd">(.+?)</url>', re.DOTALL).findall(content)
        match2 = re.compile(r'<url\s*quality="sd">(.+?)</url>', re.DOTALL).findall(content)
        urlNew = ""
        if match1:
            urlNew = match1[0]
        elif match2:
            urlNew = match2[0]
        urlNew = urlNew.replace("MP4:", "mp4:")
        base = urlNew[:urlNew.find("mp4:")]
        playpath = urlNew[urlNew.find("mp4:"):]
        listitem = xbmcgui.ListItem(path="{0} playpath={1} swfVfy=1 swfUrl=http://videos.arte.tv/blob/web/i18n/view/player_24-3188338-data-5168030.swf".format(base, playpath))
        xbmcplugin.setResolvedUrl(pluginhandle, True, listitem)
    except:
        xbmcgui.Dialog().notification('Info:', translation(30110) + ' (Arte)!', _icon, 5000, False)


def addFav():
    keyboard = xbmc.Keyboard('', translation(30033))
    keyboard.doModal()
    if keyboard.isConfirmed() and keyboard.getText():
        user = keyboard.getText()
        channelEntry = "###USER###={0}###THUMB###=###END###".format(user)
        if xbmcvfs.exists(channelFavsFile):
            with open(channelFavsFile, 'r') as fh:
                content = fh.read()
            if content.find(channelEntry) == -1:
                with open(channelFavsFile, 'a') as fh:
                    fh.write(channelEntry + "\n")
        else:
            with open(channelFavsFile, 'a') as fh:
                fh.write(channelEntry + "\n")
        xbmcgui.Dialog().notification('Info:', translation(30030), _icon, 5000, False)


def favourites(param):
    mode = param[param.find("###MODE###=") + 11:]
    mode = mode[:mode.find("###")]
    channelEntry = param[param.find("###USER###="):]
    user = param[11 + param.find("###USER###="):param.find("###THUMB###")]
    user = user.encode('utf8') if six.PY2 else user
    if mode == "ADD":
        if xbmcvfs.exists(channelFavsFile):
            with open(channelFavsFile, 'r') as fh:
                content = fh.read()
            if content.find(channelEntry) == -1:
                with open(channelFavsFile, 'a') as fh:
                    fh.write(channelEntry + "\n")
        else:
            with open(channelFavsFile, 'a') as fh:
                fh.write(channelEntry + "\n")
            fh.close()
        xbmcgui.Dialog().notification('Info:', '{0} {1}!'.format(user, translation(30030)), _icon, 5000, False)
    elif mode == "REMOVE":
        refresh = param[param.find("###REFRESH###=") + 14:]
        refresh = refresh[:refresh.find("###USER###=")]
        with open(channelFavsFile, 'r') as fh:
            content = fh.read()
        # entry = content[content.find(channelEntry):]
        with open(channelFavsFile, 'w') as fh:
            fh.write(content.replace(channelEntry + "\n", ""))
        if refresh == "TRUE":
            xbmc.executebuiltin("Container.Refresh")


def translation(lid):
    return addon.getLocalizedString(lid).encode('utf-8') if six.PY2 else addon.getLocalizedString(lid)


def getUrl2(url):
    xbmc.log('DAILYMOTION - The url is {0}'.format(url), xbmc.LOGDEBUG)
    headers = {'User-Agent': _UA}
    cookie = {'lang': language,
              'ff': "on" if familyFilter == "1" else "off"}
    r = requests.get(url, headers=headers, cookies=cookie)
    return r.text


def checkUrl(url):
    xbmc.log('DAILYMOTION - Check url is {0}'.format(url), xbmc.LOGDEBUG)
    headers = {'User-Agent': _UA,
               'Referer': 'https://www.dailymotion.com/',
               'Origin': 'https://www.dailymotion.com'}
    cookie = {'lang': language,
              'ff': "on" if familyFilter == "1" else "off"}
    r = requests.head(url, headers=headers, cookies=cookie)
    status = r.status_code == 200
    return status


def parameters_string_to_dict(parameters):
    paramDict = {}
    if parameters:
        paramPairs = parameters[1:].split("&")
        for paramsPair in paramPairs:
            paramSplits = paramsPair.split('=')
            if (len(paramSplits)) == 2:
                paramDict[paramSplits[0]] = paramSplits[1]
    return paramDict


def addLink(name, url, mode, iconimage, user, desc, duration, date, nr):
    u = "{0}?url={1}&mode={2}".format(sys.argv[0], urllib_parse.quote_plus(url), mode)
    ok = True
    liz = make_listitem(name=name, labels={"Title": name, "Plot": desc, "Aired": date, "Duration": duration, "Episode": nr})
    liz.setArt({'thumb': iconimage,
                'icon': _icon,
                'poster': iconimage,
                'fanart': _fanart})
    liz.setProperty('IsPlayable', 'true')
    entries = []
    entries.append((translation(30044), 'RunPlugin(plugin://{0}/?mode=downloadVideo&name={1}&url={2})'.format(addonID, urllib_parse.quote_plus(name), urllib_parse.quote_plus(url)),))
    entries.append((translation(30043), 'RunPlugin(plugin://{0}/?mode=queueVideo&url={1}&name={2})'.format(addonID, urllib_parse.quote_plus(u), urllib_parse.quote_plus(name)),))
    entries.append(('Salveaza date video', 'RunPlugin(plugin://{0}/?mode=save_video_data&name={1}&url={2})'.format(addonID, urllib_parse.quote_plus(name), urllib_parse.quote_plus(url))))
    if dmUser == "":
        playListInfos = "###MODE###=ADD###USER###={0}###THUMB###=DefaultVideo.png###END###".format(user)
        entries.append((translation(30028), 'RunPlugin(plugin://{0}/?mode=favourites&url={1})'.format(addonID, urllib_parse.quote_plus(playListInfos)),))
    liz.addContextMenuItems(entries)
    ok = xbmcplugin.addDirectoryItem(handle=int(sys.argv[1]), url=u, listitem=liz)
    return ok


def addLiveLink(name, url, mode, iconimage, desc):
    u = "{0}?url={1}&mode={2}".format(sys.argv[0], urllib_parse.quote_plus(url), mode)
    ok = True
    liz = make_listitem(name=name, labels={"Title": name, "Plot": desc})
    liz = xbmcgui.ListItem(name)
    liz.setArt({'thumb': iconimage,
                'icon': _icon,
                'poster': iconimage,
                'fanart': _fanart})
    liz.setProperty('IsPlayable', 'true')
    ok = xbmcplugin.addDirectoryItem(handle=int(sys.argv[1]), url=u, listitem=liz)
    return ok


def addDir(name, url, mode, iconimage, desc=""):
    u = "{0}?url={1}&mode={2}".format(sys.argv[0], urllib_parse.quote_plus(url), mode)
    ok = True
    liz = make_listitem(name=name, labels={"Title": name, "Plot": desc})
    liz.setArt({'thumb': iconimage,
                'icon': _icon,
                'poster': iconimage,
                'fanart': _fanart})
    ok = xbmcplugin.addDirectoryItem(handle=int(sys.argv[1]), url=u, listitem=liz, isFolder=True)
    return ok


def addUserDir(name, url, mode, iconimage, desc):
    u = "{0}?url={1}&mode={2}".format(sys.argv[0], urllib_parse.quote_plus(url), mode)
    ok = True
    liz = make_listitem(name=name, labels={"Title": name, "Plot": desc})
    liz.setArt({'thumb': iconimage,
                'icon': _icon,
                'poster': iconimage,
                'fanart': _fanart})
    if dmUser == "":
        playListInfos = "###MODE###=ADD###USER###={0}###THUMB###={1}###END###".format(name, iconimage)
        liz.addContextMenuItems([(translation(30028), 'RunPlugin(plugin://{0}/?mode=favourites&url={1})'.format(addonID, urllib_parse.quote_plus(playListInfos)),)])
    ok = xbmcplugin.addDirectoryItem(handle=int(sys.argv[1]), url=u, listitem=liz, isFolder=True)
    return ok


def addFavDir(name, url, mode, iconimage):
    u = "{0}?url={1}&mode={2}".format(sys.argv[0], urllib_parse.quote_plus(url), mode)
    ok = True
    liz = make_listitem(name=name, labels={"Title": name})
    liz.setArt({'thumb': iconimage,
                'icon': _icon,
                'poster': iconimage,
                'fanart': _fanart})
    liz.addContextMenuItems([(translation(30033), 'RunPlugin(plugin://{0}/?mode=addFav)'.format('addonID'),)])
    ok = xbmcplugin.addDirectoryItem(handle=int(sys.argv[1]), url=u, listitem=liz, isFolder=True)
    return ok


def addUserFavDir(name, url, mode, iconimage):
    u = "{0}?url={1}&mode={2}".format(sys.argv[0], urllib_parse.quote_plus(url), mode)
    ok = True
    liz = make_listitem(name=name, labels={"Title": name})
    liz.setArt({'thumb': iconimage,
                'icon': _icon,
                'poster': iconimage,
                'fanart': _fanart})
    if dmUser == "":
        playListInfos = "###MODE###=REMOVE###REFRESH###=TRUE###USER###={0}###THUMB###={1}###END###".format(name, iconimage)
        liz.addContextMenuItems([(translation(30029), 'RunPlugin(plugin://{0}/?mode=favourites&url={1})'.format(addonID, urllib_parse.quote_plus(playListInfos)),)])
    ok = xbmcplugin.addDirectoryItem(handle=int(sys.argv[1]), url=u, listitem=liz, isFolder=True)
    return ok


def seriale_menu(url):
    addDir("[COLOR cyan]Actualizare serialele[/COLOR]", "", 'auto_update_from_users_file', "{0}featured.png".format(_ipath))
    if enablePlaylistImport:
        addDir("[COLOR yellow]Importa Playlist[/COLOR]", "", 'import_playlist_prompt', "{0}playlists.png".format(_ipath))
    if enableUserImport:
        addDir("[COLOR yellow]Importa User (Rapid)[/COLOR]", "", 'import_user_prompt', "{0}users.png".format(_ipath))
        addDir("[COLOR red]Importa User (Complet)[/COLOR]", "", 'import_user_prompt_full', "{0}users.png".format(_ipath))
        addDir("[COLOR orange]Scaneaza User (Rapid)[/COLOR]", "", 'scan_user_for_all_series', "{0}users.png".format(_ipath))
        addDir("[COLOR red]Scaneaza User (Complet)[/COLOR]", "", 'scan_user_for_all_series_full', "{0}users.png".format(_ipath))
        addDir("[COLOR red]Actualizare Completa (useri.txt)[/COLOR]", "", 'auto_update_from_users_file_full', "{0}featured.png".format(_ipath))


    # Dynamically added shows from JSON
    saved_data, _ = _read_saved_videos()
    if saved_data:
        json_shows = sorted(list(set([item['serial'] for item in saved_data if 'serial' in item])))
        for show_name in json_shows:
            addDir(show_name, show_name, 'list_saved_seasons', "{0}channels.png".format(_ipath))

    xbmcplugin.endOfDirectory(pluginhandle)


def _scan_user_and_sort(user_id, series_list, pDialog, full_scan=False):
    # Step 1: Fetch new videos
    real_user_id = user_id
    try:
        api_lookup_url = "{0}/user/{1}?fields=id".format(urlMain, user_id)
        content = getUrl2(api_lookup_url)
        data = json.loads(content)
        if data.get('id'): real_user_id = data['id']
    except Exception: pass

    clean_data, existing_video_ids = _read_saved_videos()
    saved_lookup = OrderedDict(( (item['serial'], str(item['sezon']), str(item['episod'])), item) for item in clean_data)
    
    all_videos = []
    page, has_more, stop_fetching = 1, True, False
    while has_more and not stop_fetching:
        if pDialog.iscanceled(): return None
        api_url = "{0}/videos?owner={1}&fields=id,title&sort=recent&limit=100&page={2}".format(urlMain, real_user_id, page)
        try:
            content = getUrl2(api_url)
            data = json.loads(content)
            if data.get('list'):
                page_videos = data['list']
                if not full_scan: # Only apply early-exit if not a full scan
                    for video in page_videos:
                        if video['id'] in existing_video_ids:
                            stop_fetching = True
                            break
                
                if stop_fetching:
                    for video in page_videos:
                        if video['id'] in existing_video_ids: break
                        all_videos.append(video)
                else:
                    all_videos.extend(page_videos)
                has_more = data.get('has_more', False)
                page += 1
            else: has_more = False
        except Exception: has_more = False

    if not all_videos:
        return {'error': 'Nu s-au gasit videoclipuri noi.'}

    # Step 2: Sort videos by matching series name
    pDialog.update(70, 'Se sorteaza {0} videoclipuri...'.format(len(all_videos)))
    
    sorted_videos = {}
    unmatched_count = 0
    normalized_series_list = {s: _normalize_romanian(s) for s in series_list}

    for video in all_videos:
        matched_series = None
        normalized_title = _normalize_romanian(video['title'])
        for series_name, normalized_series_name in normalized_series_list.items():
            if _is_series_match_for_title(normalized_series_name, normalized_title):
                matched_series = series_name
                break
        
        if matched_series:
            sezon, episod = _parse_season_episode(video['title'])
            if sezon and episod:
                if matched_series not in sorted_videos:
                    sorted_videos[matched_series] = []
                sorted_videos[matched_series].append({
                    "video_id": video['id'], "video_title": video['title'],
                    "serial": matched_series, "sezon": sezon, "episod": episod
                })
            else:
                unmatched_count += 1
        else:
            unmatched_count += 1

    if not sorted_videos:
        return {'error': 'Nu s-a putut asocia niciun video nou cu serialele cunoscute.'}

    # Step 3: Merge with existing data and generate summary
    pDialog.update(90, 'Se actualizeaza baza de date...')
    
    summary_details = {}
    for series_name, videos in sorted_videos.items():
        summary_details[series_name] = {'new': 0, 'updated': 0}
        for video in videos:
            lookup_key = (video['serial'], video['sezon'], video['episod'])
            if lookup_key in saved_lookup:
                if saved_lookup[lookup_key]['video_id'] != video['video_id']:
                    saved_lookup[lookup_key].update(video)
                    summary_details[series_name]['updated'] += 1
            else:
                saved_lookup[lookup_key] = video
                summary_details[series_name]['new'] += 1
    
    final_data = list(saved_lookup.values())
    if _write_saved_videos(final_data):
        return {'summary': summary_details, 'unmatched': unmatched_count}
    else:
        return {'error': 'Salvarea datelor a esuat.'}


def scan_user_for_all_series(full_scan=False):
    # Step 1: Get the master list of series names
    users_file = translate_path('{0}/resources/files/useri.txt'.format(_path))
    if not xbmcvfs.exists(users_file):
        xbmcgui.Dialog().notification('Eroare', 'Fisierul useri.txt nu a fost gasit.', _icon, 3000, False)
        return
    with xbmcvfs.File(users_file, 'r') as f: content = f.read()
    
    series_list = set()
    lines = [line.strip() for line in content.split('\n') if line.strip() and not line.strip().startswith('#')]
    for line in lines:
        parts = line.split('|')
        if len(parts) == 3:
            series_list.add(parts[2].strip())

    if not series_list:
        xbmcgui.Dialog().notification('Info', 'Nu sunt definite seriale in useri.txt.', _icon, 3000, False)
        return

    # Step 2: Get user to scan
    user_id = get_key("Introdu numele de utilizator Dailymotion de scanat")
    if not user_id: return

    # Step 3: Run the scan and sort process
    dialog_title = 'Scanare Completa' if full_scan else 'Scanare Utilizator'
    pDialog.create(dialog_title, 'Se preiau datele pentru {0}...'.format(user_id))
    result = _scan_user_and_sort(user_id, list(series_list), pDialog, full_scan=full_scan)
    pDialog.close()

    # Step 4: Display summary
    if result:
        if result.get('error'):
            xbmcgui.Dialog().notification('Info', result['error'], _icon, 4000, False)
        elif result.get('summary'):
            summary_message = "Scanare finalizata!\n"
            total_new, total_updated = 0, 0
            for series, counts in result['summary'].items():
                if counts['new'] > 0 or counts['updated'] > 0:
                    summary_message += "\n[B]{0}:[/B] {1} noi, {2} actualizate".format(series, counts['new'], counts['updated'])
                    total_new += counts['new']
                    total_updated += counts['updated']
            
            summary_message += "\n\n[B]Total gasit:[/B] {0} episoade noi, {1} actualizate.".format(total_new, total_updated)
            summary_message += "\nVideoclipuri neasociate: {0}".format(result['unmatched'])
            
            xbmcgui.Dialog().ok('Rezumat Scanare', summary_message)
            # Refresh the series menu without re-triggering the scan script
            xbmc.executebuiltin("Container.Update(plugin://{0}/?url=seriale&mode=seriale_menu)".format(addonID))
    elif not pDialog.iscanceled():
        xbmcgui.Dialog().notification('Eroare', 'A aparut o eroare neasteptata.', _icon, 3000, False)

def scan_user_for_all_series_full():
    scan_user_for_all_series(full_scan=True)

def auto_update_from_users_file(full_scan=False, silent=False):
    users_file = translate_path('{0}/resources/files/useri.txt'.format(_path))
    if not xbmcvfs.exists(users_file):
        if not silent:
            xbmcgui.Dialog().notification('Eroare', 'Fisierul useri.txt nu a fost gasit.', _icon, 3000, False)
        xbmc.log('Dailymotion: useri.txt nu a fost gasit', xbmc.LOGERROR)
        return

    with xbmcvfs.File(users_file, 'r') as f:
        content = f.read()
    
    lines = [line.strip() for line in content.split('\n') if line.strip() and not line.strip().startswith('#')]

    if not lines:
        if not silent:
            xbmcgui.Dialog().notification('Info', 'Fisierul useri.txt este gol.', _icon, 3000, False)
        xbmc.log('Dailymotion: useri.txt este gol', xbmc.LOGINFO)
        return

    dialog_title = 'Actualizare Completa' if full_scan else 'Actualizare Automata'
    if not silent:
        pDialog.create(dialog_title, 'Initializare...')
    total_new, total_updated, total_ignored = 0, 0, 0
    
    for i, line in enumerate(lines):
        progress = int((i / float(len(lines))) * 100)
        
        parts = line.split('|')
        if len(parts) != 3:
            xbmc.log("Dailymotion: Skipping malformed line in useri.txt: {0}".format(line), xbmc.LOGWARNING)
            continue

        source_type, source_id, series_name = parts[0].strip(), parts[1].strip(), parts[2].strip()
        
        if not silent:
            pDialog.update(progress, 'Se actualizeaza {0}/{1}: {2}...'.format(i+1, len(lines), series_name))
        
        if not silent and pDialog.iscanceled():
            break
        
        summary = None
        if source_type == 'user':
            summary = _import_videos_for_user(source_id, series_name, pDialog, full_scan=full_scan)
        elif source_type == 'playlist':
            # For auto-update, we always auto-detect season from title
            summary = _import_videos_from_playlist(source_id, series_name, "auto", pDialog, full_scan=full_scan)
        else:
            xbmc.log("Dailymotion: Unknown source type '{0}' in useri.txt".format(source_type), xbmc.LOGWARNING)
            continue

        if summary and not summary.get('error'):
            total_new += summary['new']
            total_updated += summary['updated']
            total_ignored += summary['ignored']

    if not silent:
        pDialog.close()
    
    summary_message = "Actualizare finalizata!\nTotal episoade noi: {0}\nTotal episoade actualizate: {1}\nTotal titluri ignorate: {2}".format(
        total_new, total_updated, total_ignored)
    xbmc.log('Dailymotion: ' + summary_message.replace('\n', ' | '), xbmc.LOGINFO)
    if not silent and addon.getSetting('auto_update_notify') == 'true':
        xbmcgui.Dialog().ok('Rezumat Actualizare', summary_message)
    # Refresh the series menu without re-triggering the update script
    xbmc.executebuiltin("Container.Update(plugin://{0}/?url=seriale&mode=seriale_menu)".format(addonID))

def auto_update_from_users_file_full():
    auto_update_from_users_file(full_scan=True)


def list_saved_seasons(show_name):
    saved_data, _ = _read_saved_videos()
    seasons = set()
    if saved_data:
        for item in saved_data:
            if item.get('serial') == show_name and item.get('sezon'):
                try:
                    seasons.add(int(item['sezon']))
                except (ValueError, TypeError):
                    continue # Ignore non-integer season numbers

    if seasons:
        for season_num in sorted(list(seasons), reverse=True):
            url_param = "{0}|{1}".format(show_name, season_num)
            addDir("Sezonul {0}".format(season_num), url_param, 'list_saved_episodes', "{0}channels.png".format(_ipath))

    xbmcplugin.endOfDirectory(pluginhandle)


def list_saved_episodes(url):
    show_name, season_num_str = url.split('|')
    
    saved_data, _ = _read_saved_videos()
    episodes = []
    if saved_data:
        for item in saved_data:
            # Ensure consistent type comparison
            if item.get('serial') == show_name and str(item.get('sezon')) == season_num_str:
                episodes.append(item)

    if episodes:
        # Sort episodes by episode number, handling potential non-integer values
        sorted_episodes = sorted(episodes, key=lambda x: int(x.get('episod', 0)) if str(x.get('episod', 0)).isdigit() else 0)
        for episode_data in sorted_episodes:
            vid_id = episode_data.get('video_id')
            ep_num_str = str(episode_data.get('episod', 'N/A'))
            title = episode_data.get('video_title', "{0} - episodul {1}".format(show_name, ep_num_str))
            
            u = "{0}?url={1}&mode=playVideo".format(sys.argv[0], urllib_parse.quote_plus(vid_id))
            liz = make_listitem(name=title)
            liz.setArt({'thumb': "{0}videos.png".format(_ipath)})
            liz.setProperty('IsPlayable', 'true')
            xbmcplugin.addDirectoryItem(handle=int(sys.argv[1]), url=u, listitem=liz, isFolder=False)

    xbmcplugin.endOfDirectory(pluginhandle)

def search_episode(search_query):
    search_url = "{0}/videos?fields=description,duration,id,owner.username,taken_time,thumbnail_large_url,title,views_total&search={1}&sort=relevance&limit=20&family_filter={2}&localization={3}&page=1".format(urlMain, urllib_parse.quote_plus(search_query), familyFilter, language)
    listVideos(search_url)


def tmdb_search(query):
    search_url = "{0}/videos?fields=description,duration,id,owner.username,taken_time,thumbnail_large_url,title,views_total&search={1}&sort=relevance&limit=20&family_filter={2}&localization={3}&page=1".format(urlMain, urllib_parse.quote_plus(query), familyFilter, language)
    plugin_url = "{0}?url={1}&mode=listVideos".format(sys.argv[0], urllib_parse.quote_plus(search_url))
    xbmc.executebuiltin("Container.Update({0})".format(plugin_url))

def tmdb_play(query):
    pDialog.create('Dailymotion', 'Cautare TMDBHelper...\n' + query)
    
    search_url = "{0}/videos?fields=id&search={1}&sort=relevance&limit=1&family_filter={2}&localization={3}&page=1".format(urlMain, urllib_parse.quote_plus(query), familyFilter, language)
    
    try:
        content = getUrl2(search_url)
        data = json.loads(content)
        
        if pDialog.iscanceled():
            return

        if data.get('list'):
            vid = data['list'][0]['id']
            pDialog.update(50, 'Video gasit, se incearca redarea...')
            playVideo(vid)
        else:
            pDialog.close()
            xbmcgui.Dialog().notification('Eroare', 'Nu s-a gasit niciun video.', _icon, 3000, False)

    except Exception as e:
        if pDialog.iscanceled() is False:
            pDialog.close()
        xbmc.log("Error in tmdb_play: {0}".format(e), xbmc.LOGERROR)
        xbmcgui.Dialog().notification('Eroare', 'A aparut o eroare la cautare.', _icon, 3000, False)

def save_video_data(name, vid):
    serial_name = get_key("Introdu numele serialului")
    if not serial_name: return
    
    sezon_num = get_key("Introdu numarul sezonului")
    if not sezon_num: return

    episod_num = get_key("Introdu numarul episodului")
    if not episod_num: return

    data_to_save = {
        "video_id": vid,
        "video_title": name,
        "serial": serial_name,
        "sezon": str(sezon_num),
        "episod": str(episod_num)
    }

    saved_data, _ = _read_saved_videos()
    saved_data.append(data_to_save)

    if _write_saved_videos(saved_data):
        xbmcgui.Dialog().notification('Succes', 'Datele video au fost salvate.', _icon, 3000, False)
    else:
        xbmcgui.Dialog().notification('Eroare', 'Salvarea datelor a esuat.', _icon, 3000, False)


def get_key(heading):
    keyboard = xbmc.Keyboard('', heading)
    keyboard.doModal()
    if keyboard.isConfirmed():
        return keyboard.getText()


from collections import OrderedDict

def _read_saved_videos():
    save_file = translate_path('{0}/resources/files/saved_videos.json'.format(_path))
    saved_data = []
    if xbmcvfs.exists(save_file):
        try:
            with xbmcvfs.File(save_file, 'r') as f:
                content = f.read()
                if content:
                    saved_data = json.loads(content)
        except Exception as e:
            xbmc.log("Error reading saved_videos.json: {0}".format(e), xbmc.LOGERROR)
            return [], set() # Return empty values on error

    # Use OrderedDict to keep the last found unique entry, effectively de-duplicating
    unique_entries = OrderedDict()
    existing_video_ids = set()

    for item in saved_data:
        # Force string type for season and episode to ensure consistent keys
        serial = item.get('serial')
        sezon = str(item.get('sezon')) if item.get('sezon') is not None else None
        episod = str(item.get('episod')) if item.get('episod') is not None else None
        
        if serial and sezon and episod:
            unique_key = (serial, sezon, episod)
            unique_entries[unique_key] = item
        
        if item.get('video_id'):
            existing_video_ids.add(item['video_id'])

    # The final clean list is the values from our de-duplicated dictionary
    clean_data = list(unique_entries.values())
    
    return clean_data, existing_video_ids


def _write_saved_videos(data):
    save_dir = translate_path('{0}/resources/files/'.format(_path))
    save_file = translate_path('{0}/resources/files/saved_videos.json'.format(_path))
    if not xbmcvfs.exists(save_dir):
        xbmcvfs.mkdirs(save_dir)
    
    try:
        with xbmcvfs.File(save_file, 'w') as f:
            f.write(json.dumps(data, indent=4))
        return True
    except Exception as e:
        xbmc.log("Error writing saved_videos.json: {0}".format(e), xbmc.LOGERROR)
        return False


def import_playlist_prompt():
    playlist_id = get_key("Introdu ID-ul playlist-ului Dailymotion")
    if not playlist_id: return

    serial_name = get_key("Introdu numele serialului")
    if not serial_name: return
    
    # Season is now optional, it will be parsed from titles if possible
    sezon_num = get_key("Introdu numarul sezonului (optional, lasa gol pt. auto-detect)")
    if not sezon_num:
        sezon_num = "auto" # A special value to indicate auto-detection

    url_param = "{0}|{1}|{2}".format(playlist_id, serial_name, sezon_num)
    import_playlist(url_param)


def _import_videos_from_playlist(playlist_id, serial_name, sezon_num_default, pDialog=None, full_scan=False):
    clean_data, existing_video_ids = _read_saved_videos()
    saved_lookup = OrderedDict(( (item['serial'], str(item['sezon']), str(item['episod'])), item) for item in clean_data)

    all_videos = []
    page = 1
    has_more = True
    stop_fetching = False
    while has_more and not stop_fetching:
        if pDialog and pDialog.iscanceled(): return None
        
        api_url = "{0}/playlist/{1}/videos?fields=id,title&sort=recent&limit=100&page={2}".format(urlMain, playlist_id, page)
        try:
            content = getUrl2(api_url)
            data = json.loads(content)
        except Exception as e:
            xbmc.log("Failed to fetch playlist page {0}: {1}".format(playlist_id, e), xbmc.LOGERROR)
            return {'new': 0, 'updated': 0, 'ignored': 0, 'error': 'Could not fetch playlist.'}

        if not data.get('list'):
            break

        page_videos = data['list']
        if not full_scan: # Only apply early-exit if not a full scan
            for video in page_videos:
                if video['id'] in existing_video_ids:
                    stop_fetching = True
                    break
        
        if stop_fetching:
            for video in page_videos:
                if video['id'] in existing_video_ids: break
                all_videos.append(video)
        else:
            all_videos.extend(page_videos)

        has_more = data.get('has_more', False)
        page += 1

    if not all_videos:
        return {'new': 0, 'updated': 0, 'ignored': 0, 'error': 'No new videos found in playlist.'}

    parsed_videos = []
    ignored_count = 0
    for video in all_videos:
        sezon, episod = _parse_season_episode(video['title'])
        
        if not sezon and sezon_num_default != "auto":
            sezon = sezon_num_default

        if sezon and episod:
            parsed_videos.append({
                "video_id": video['id'], "video_title": video['title'],
                "serial": serial_name, "sezon": sezon, "episod": episod
            })
        else:
            ignored_count += 1

    if not parsed_videos:
        return {'new': 0, 'updated': 0, 'ignored': ignored_count, 'error': 'Could not parse season/episode from any new titles.'}

    updated_count, new_count = 0, 0
    for video in parsed_videos:
        lookup_key = (video['serial'], video['sezon'], video['episod'])
        if lookup_key in saved_lookup:
            if saved_lookup[lookup_key]['video_id'] != video['video_id']:
                saved_lookup[lookup_key].update(video)
                updated_count += 1
        else:
            saved_lookup[lookup_key] = video
            new_count += 1

    final_data = list(saved_lookup.values())
    if _write_saved_videos(final_data):
        return {'new': new_count, 'updated': updated_count, 'ignored': ignored_count}
    else:
        return {'new': 0, 'updated': 0, 'ignored': 0, 'error': 'Failed to save data to file.'}


def import_playlist(params):
    playlist_id, serial_name, sezon_num_default = params.split('|')
    
    pDialog.create('Import Playlist Inteligent', 'Se preiau datele pentru {0}...'.format(serial_name))
    
    summary = _import_videos_from_playlist(playlist_id, serial_name, sezon_num_default, pDialog)
    
    pDialog.close()

    if summary:
        if summary.get('error'):
            xbmcgui.Dialog().notification('Info', summary['error'], _icon, 4000, False)
        else:
            summary_message = "Import finalizat!\nEpisoade noi: {0}\nEpisoade actualizate: {1}\nTitluri ignorate: {2}".format(
                summary['new'], summary['updated'], summary['ignored'])
            xbmcgui.Dialog().ok('Rezumat Import', summary_message)
    elif not pDialog.iscanceled():
        xbmcgui.Dialog().notification('Eroare', 'A aparut o eroare neasteptata.', _icon, 3000, False)


def _normalize_romanian(text):
    text = text.lower()
    text = text.replace('ă', 'a').replace('â', 'a')
    text = text.replace('î', 'i')
    text = text.replace('ș', 's')
    text = text.replace('ț', 't')
    return text

def _parse_season_episode(title):
    sezon, episod = None, None

    # List of regex patterns to try for season and episode
    patterns = [
        re.compile(r's(\d{1,2})e(\d{1,3})', re.IGNORECASE),
        re.compile(r'sezonul?\s*(\d{1,2})\s*episodul?\s*(\d{1,3})', re.IGNORECASE),
        re.compile(r'(\d{1,2})x(\d{1,3})', re.IGNORECASE)
    ]
    
    # Try patterns that find both season and episode
    for pattern in patterns:
        match = pattern.search(title)
        if match:
            sezon, episod = str(int(match.group(1))), str(int(match.group(2)))
            break

    # If no season/episode combo found, try to find just the episode and default to Season 1
    if not episod:
        # Allow optional punctuation and parentheses around the episode number
        episode_pattern = re.compile(r'(?:ep(?:isodul)?)\s*[\.:\-]?\s*\(?\s*(\d{1,3})\s*\)?', re.IGNORECASE)
        match = episode_pattern.search(title)
        if match:
            sezon, episod = "1", str(int(match.group(1)))

    # If an episode was found, check for parts
    if episod:
        part_pattern = re.compile(r'partea?\s*(\d{1,2})', re.IGNORECASE)
        part_match = part_pattern.search(title)
        if part_match:
            part_num = str(int(part_match.group(1)))
            episod = "{0}.{1}".format(episod, part_num)

    return (sezon, episod)

def import_user_prompt(full_scan=False):
    user_id = get_key("Introdu numele de utilizator Dailymotion")
    if not user_id: return

    serial_name = get_key("Introdu numele serialului")
    if not serial_name: return

    url_param = "{0}|{1}".format(user_id, serial_name)
    if full_scan:
        import_user_videos(url_param, full_scan=True)
    else:
        import_user_videos(url_param)

def import_user_prompt_full():
    import_user_prompt(full_scan=True)

def _is_series_match_for_title(normalized_series_name, normalized_video_title):
    """
    Checks if all words from the series name are present in the video title.
    This is more robust than a simple 'in' check.
    """
    series_words = set(normalized_series_name.split())
    # Create a searchable string from title by replacing common separators with spaces
    title_searchable = normalized_video_title.replace('-', ' ').replace('_', ' ')
    title_words = set(title_searchable.split())
    
    return series_words.issubset(title_words)

def _import_videos_for_user(user_id, serial_name, pDialog=None, full_scan=False):
    # Step 1: Confirm real user ID
    real_user_id = user_id
    try:
        api_lookup_url = "{0}/user/{1}?fields=id".format(urlMain, user_id)
        content = getUrl2(api_lookup_url)
        data = json.loads(content)
        if data.get('id'):
            real_user_id = data['id']
    except Exception:
        pass # Ignore errors, proceed with original user_id
    xbmc.log("Dailymotion: resolved user_id '{0}' -> '{1}'".format(user_id, real_user_id), xbmc.LOGDEBUG)

    # Step 2: Fetch new videos since last update
    clean_data, existing_video_ids = _read_saved_videos()
    saved_lookup = OrderedDict(( (item['serial'], str(item['sezon']), str(item['episod'])), item) for item in clean_data)
    
    all_videos = []
    page = 1
    has_more = True
    stop_fetching = False
    while has_more and not stop_fetching:
        if pDialog and pDialog.iscanceled(): return None

        api_url = "{0}/videos?owner={1}&fields=id,title&sort=recent&limit=100&page={2}".format(urlMain, real_user_id, page)
        xbmc.log("Dailymotion: fetching user videos page={0} url={1}".format(page, api_url), xbmc.LOGDEBUG)
        try:
            content = getUrl2(api_url)
            data = json.loads(content)
            if data.get('list'):
                page_videos = data['list']
                if not full_scan: # Only apply early-exit if not a full scan
                    for video in page_videos:
                        if video['id'] in existing_video_ids:
                            stop_fetching = True
                            xbmc.log("Dailymotion: early-exit triggered at page={0} existing_video_id={1}".format(page, video['id']), xbmc.LOGDEBUG)
                            break
                
                if stop_fetching:
                    for video in page_videos:
                        if video['id'] in existing_video_ids: break
                        all_videos.append(video)
                else:
                    all_videos.extend(page_videos)

                has_more = data.get('has_more', False)
                xbmc.log("Dailymotion: page={0} items={1} has_more={2} total_accum={3}".format(page, len(page_videos), has_more, len(all_videos)), xbmc.LOGDEBUG)
                page += 1
            else:
                has_more = False
        except Exception as e:
            xbmc.log("Failed to fetch user videos page for {0}: {1}".format(user_id, e), xbmc.LOGERROR)
            has_more = False

    if not all_videos:
        return {'new': 0, 'updated': 0, 'ignored': 0, 'error': 'No new videos found.'}
    xbmc.log("Dailymotion: fetched total videos={0}".format(len(all_videos)), xbmc.LOGDEBUG)

    # Step 3: Filter and parse videos
    normalized_serial = _normalize_romanian(serial_name)
    filtered_videos = [v for v in all_videos if _is_series_match_for_title(normalized_serial, _normalize_romanian(v.get('title', '')))]
    xbmc.log("Dailymotion: filtering by serial='{0}' -> matched={1} unmatched={2}".format(normalized_serial, len(filtered_videos), len(all_videos) - len(filtered_videos)), xbmc.LOGDEBUG)

    parsed_videos = []
    ignored_count = len(all_videos) - len(filtered_videos)
    for video in filtered_videos:
        sezon, episod = _parse_season_episode(video['title'])
        if sezon and episod:
            parsed_videos.append({
                "video_id": video['id'], "video_title": video['title'],
                "serial": serial_name, "sezon": sezon, "episod": episod
            })
        else:
            ignored_count += 1
            xbmc.log("Dailymotion: could not parse season/episode for title='{0}'".format(video['title']), xbmc.LOGDEBUG)

    if not parsed_videos:
        return {'new': 0, 'updated': 0, 'ignored': ignored_count, 'error': 'Could not parse season/episode from any new titles.'}
    xbmc.log("Dailymotion: parsed videos count={0}".format(len(parsed_videos)), xbmc.LOGDEBUG)

    # Step 4: Merge with existing data
    updated_count, new_count = 0, 0
    for video in parsed_videos:
        lookup_key = (video['serial'], video['sezon'], video['episod'])
        if lookup_key in saved_lookup:
            if saved_lookup[lookup_key]['video_id'] != video['video_id']:
                saved_lookup[lookup_key].update(video)
                updated_count += 1
        else:
            saved_lookup[lookup_key] = video
            new_count += 1
    xbmc.log("Dailymotion: merge results new={0} updated={1}".format(new_count, updated_count), xbmc.LOGDEBUG)

    # Step 5: Write data and return summary
    final_data = list(saved_lookup.values())
    xbmc.log("Dailymotion: writing saved_videos entries={0}".format(len(final_data)), xbmc.LOGDEBUG)
    if _write_saved_videos(final_data):
        xbmc.log("Dailymotion: write saved_videos.json successful", xbmc.LOGDEBUG)
        return {'new': new_count, 'updated': updated_count, 'ignored': ignored_count}
    else:
        xbmc.log("Dailymotion: write saved_videos.json failed", xbmc.LOGERROR)
        return {'new': 0, 'updated': 0, 'ignored': 0, 'error': 'Failed to save data to file.'}


def import_user_videos(params, full_scan=False):
    user_id, serial_name = params.split('|')
    
    dialog_title = 'Import Complet' if full_scan else 'Import Inteligent'
    pDialog.create(dialog_title, 'Se preiau datele pentru {0}...'.format(serial_name))
    
    summary = _import_videos_for_user(user_id, serial_name, pDialog, full_scan=full_scan)
    
    pDialog.close()

    if summary:
        if summary.get('error'):
            xbmcgui.Dialog().notification('Info', summary['error'], _icon, 4000, False)
        else:
            summary_message = "Import finalizat!\nEpisoade noi: {0}\nEpisoade actualizate: {1}\nTitluri ignorate: {2}".format(
                summary['new'], summary['updated'], summary['ignored'])
            xbmcgui.Dialog().ok('Rezumat Import', summary_message)
    elif not pDialog.iscanceled():
        xbmcgui.Dialog().notification('Eroare', 'A aparut o eroare neasteptata.', _icon, 3000, False)

def import_user_videos_full(params):
    import_user_videos(params, full_scan=True)

def search(url):
    search_string = get_key(translation(30002))
    xbmcplugin.endOfDirectory(pluginhandle, cacheToDisc=False)
    if search_string and len(search_string) > 2:
        url2 = url.replace("&search=", "&search={0}".format(urllib_parse.quote_plus(search_string)))
        addtoHistory({'name': search_string, 'url': urllib_parse.quote_plus(url2), 'mode': 'listVideos'})
        u = "{0}?url={1}&mode=listVideos".format(sys.argv[0], urllib_parse.quote_plus(url2))
        xbmc.executebuiltin("Container.Update({0})".format(u))
    else:
        xbmc.executebuiltin("Container.Update({0},replace)".format(sys.argv[0]))


def searchLive():
    keyboard = xbmc.Keyboard('', '{0} {1}'.format(translation(30002), translation(30003)))
    keyboard.doModal()
    if keyboard.isConfirmed() and keyboard.getText():
        searchl_string = urllib_parse.quote_plus(keyboard.getText())
        listLive("{0}/videos?fields=id,thumbnail_large_url,title,views_last_hour&live_onair=1&search={1}&limit={2}&family_filter={3}&localization={4}&page=1".format(urlMain, searchl_string, itemsPerPage, familyFilter, language))


def searchUser():
    keyboard = xbmc.Keyboard('', translation(30002) + ' ' + translation(30007))
    keyboard.doModal()
    if keyboard.isConfirmed() and keyboard.getText():
        searchl_string = urllib_parse.quote_plus(keyboard.getText())
        listUsers("{0}/users?fields=username,avatar_large_url,videos_total,views_total&search={1}&limit={2}&family_filter={3}&localization={4}&page=1".format(urlMain, searchl_string, itemsPerPage, familyFilter, language))


def addtoHistory(item):
    if xbmcvfs.exists(HistoryFile):
        with open(HistoryFile, 'r') as fh:
            content = fh.read()
        if content.find(item["url"]) == -1:  # use url to verify
            with open(HistoryFile, 'a') as fh:
                fh.write(json.dumps(item) + "\n")
    else:
        with open(HistoryFile, 'a') as fh:
            fh.write(json.dumps(item) + "\n")


def History():
    if xbmcvfs.exists(HistoryFile):
        with open(HistoryFile, 'r') as fh:
            content = fh.readlines()
            if len(content) > 0:
                content = [json.loads(x) for x in content]
                reversed_content = content[::-1]  # reverse order
                addHistoryDir(reversed_content)
                addDir("[COLOR red]{0}[/COLOR]".format(translation(30116)), "", "delHistory", "{0}search.png".format(_ipath))
                xbmcplugin.endOfDirectory(pluginhandle, cacheToDisc=False)
                xbmcplugin.setContent(pluginhandle, "addons")
                if force_mode:
                    xbmc.executebuiltin('Container.SetViewMode({0})'.format(menu_mode))


def delHistory():
    if xbmcgui.Dialog().yesno("Dailymotion", "Clear all search terms?"):
        with open(HistoryFile, 'w') as fh:
            fh.write("")


def addHistoryDir(listofdicts):
    listoflists = []

    for item in listofdicts:
        liz = make_listitem(name=item["name"], labels={"genre": "History"})
        liz.setArt({"thumb": "{0}search.png".format(_ipath),
                    "icon": "{0}search.png".format(_ipath)})
        url = "{0}?url={1}&mode={2}".format(sys.argv[0], item["url"], item["mode"])
        listoflists.append((url, liz, True))

    ok = xbmcplugin.addDirectoryItems(pluginhandle, listoflists, len(listoflists))
    return ok


params = parameters_string_to_dict(sys.argv[2])
mode = urllib_parse.unquote_plus(params.get('mode', ''))
url = urllib_parse.unquote_plus(params.get('url', ''))
name = urllib_parse.unquote_plus(params.get('name', ''))
query = urllib_parse.unquote_plus(params.get('query', ''))

if mode == 'listVideos':
    listVideos(url)
elif mode == 'listLive':
    listLive(url)
elif mode == 'listUsers':
    listUsers(url)
elif mode == 'listChannels':
    listChannels()
elif mode == 'favourites':
    favourites(url)
elif mode == 'addFav':
    addFav()
elif mode == 'personalMain':
    personalMain()
elif mode == 'favouriteUsers':
    favouriteUsers()
elif mode == 'listUserPlaylists':
    listUserPlaylists(url)
elif mode == 'showPlaylist':
    showPlaylist(url)
elif mode == 'sortVideos1':
    sortVideos1(url)
elif mode == 'sortVideos2':
    sortVideos2(url)
elif mode == 'sortUsers1':
    sortUsers1()
elif mode == 'sortUsers2':
    sortUsers2(url)
elif mode == 'playVideo':
    playVideo(url)
elif mode == 'playLiveVideo':
    playVideo(url, live=True)
elif mode == 'playArte':
    playArte(url)
elif mode == "queueVideo":
    queueVideo(url, name)
elif mode == "downloadVideo":
    downloadVideo(name, url)
elif mode == 'search':
    search(url)
elif mode == 'livesearch':
    searchLive()
elif mode == 'usersearch':
    searchUser()
elif mode == 'History':
    History()
elif mode == 'delHistory':
    delHistory()
elif mode == 'save_video_data':
    save_video_data(name, url)
elif mode == 'tmdb_play':
    tmdb_play(query)
elif mode == 'tmdb_search':
    tmdb_search(query)
elif mode == 'seriale_menu':
    seriale_menu(url)
elif mode == 'search_episode':
    search_episode(url)
elif mode == 'list_saved_seasons':
    list_saved_seasons(url)
elif mode == 'list_saved_episodes':
    list_saved_episodes(url)
elif mode == 'import_playlist_prompt':
    import_playlist_prompt()
elif mode == 'import_playlist':
    import_playlist(url)
elif mode == 'import_user_prompt':
    import_user_prompt()
elif mode == 'import_user_prompt_full':
    import_user_prompt_full()
elif mode == 'import_user_videos':
    import_user_videos(url)
elif mode == 'import_user_videos_full':
    import_user_videos(url, full_scan=True)
elif mode == 'auto_update_from_users_file':
    auto_update_from_users_file()
elif mode == 'auto_update_from_users_file_full':
    auto_update_from_users_file_full()
elif mode == 'scan_user_for_all_series':
    scan_user_for_all_series()
elif mode == 'scan_user_for_all_series_full':
    scan_user_for_all_series_full()
else:
    index()
# --- Overrides: improved matching and parsing ---
_STOPWORDS = set(['de', 'si', 'in', 'la', 'cu', 'pe', 'un', 'o', 'din', 'al', 'ale', 'ul'])

def _normalize_romanian(text):
    """
    Robust normalization for Romanian strings used in matching.
    Lowercase, strip diacritics, replace separators, collapse spaces.
    """
    try:
        if not isinstance(text, str):
            text = str(text)
    except Exception:
        return ""
    import unicodedata
    text = unicodedata.normalize('NFKD', text)
    text = ''.join(ch for ch in text if not unicodedata.combining(ch))
    text = text.lower()
    mapping = {'ă': 'a', 'â': 'a', 'î': 'i', 'ș': 's', 'ş': 's', 'ț': 't', 'ţ': 't'}
    text = ''.join(mapping.get(ch, ch) for ch in text)
    for sep in ['-', '_', '.', ',', ':', ';', '|', '/', '\\']:
        text = text.replace(sep, ' ')
    text = ' '.join(text.split())
    return text

def _is_series_match_for_title(normalized_series_name, normalized_video_title):
    """
    Match if a majority of significant words from series name appear in title.
    Ignores stopwords to reduce false negatives like "State de Romania".
    """
    series_words = [w for w in normalized_series_name.split() if w not in _STOPWORDS and len(w) > 1]
    if not series_words:
        return False
    title_words = set(normalized_video_title.split())
    matches = sum(1 for w in series_words if w in title_words)
    needed = 1 if len(series_words) == 1 else max(2, int(round(0.6 * len(series_words))))
    return matches >= needed

def _parse_season_episode(title):
    """
    More flexible parser for season/episode from common Romanian and SxxExx formats.
    Supports variants: "Sezon 1 Episod 2", "S 1 E 2", "1x02", "Ep 2 Sezon 1", "Ep. 12".
    """
    sezon, episod = None, None

    patterns = [
        re.compile(r"\b[Ss]\s*(\d{1,2})\s*[Ee]\s*(\d{1,3})\b"),
        re.compile(r"sez(?:on(?:ul)?)?\s*(\d{1,2})\s*(?:ep(?:isod(?:ul)?)?)\s*(\d{1,3})", re.IGNORECASE),
        re.compile(r"(\d{1,2})\s*x\s*(\d{1,3})", re.IGNORECASE),
        re.compile(r"(?:ep(?:isod(?:ul)?)?)\s*(\d{1,3}).*?sez(?:on(?:ul)?)?\s*(\d{1,2})", re.IGNORECASE)
    ]
    for pattern in patterns:
        m = pattern.search(title)
        if m:
            if pattern.pattern.startswith('(?:ep'):
                episod_val, sezon_val = m.group(1), m.group(2)
            else:
                sezon_val, episod_val = m.group(1), m.group(2)
            try:
                sezon, episod = str(int(sezon_val)), str(int(episod_val))
            except Exception:
                pass
            break

    if not episod:
        for ep_pat in [
            re.compile(r"(?:ep(?:isod(?:ul)?)?)\s*[\.:\-]?\s*\(?\s*(\d{1,3})\s*\)?", re.IGNORECASE),
            re.compile(r"\b[Ee]\s*\(?\s*(\d{1,3})\s*\)?\b")
        ]:
            m = ep_pat.search(title)
            if m:
                try:
                    sezon, episod = "1", str(int(m.group(1)))
                except Exception:
                    pass
                if episod:
                    break

    if episod:
        part_match = re.compile(r"partea?\s*(\d{1,2})", re.IGNORECASE).search(title)
        if part_match:
            try:
                episod = "{0}.{1}".format(episod, str(int(part_match.group(1))))
            except Exception:
                pass

    return (sezon, episod)
