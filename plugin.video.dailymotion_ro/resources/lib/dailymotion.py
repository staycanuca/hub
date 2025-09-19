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
    if enablePlaylistImport:
        addDir("[COLOR yellow]Importa Playlist in JSON[/COLOR]", "", 'import_playlist_prompt', "{0}playlists.png".format(_ipath))
    if enableUserImport:
        addDir("[COLOR yellow]Importa Videoclipuri de la Utilizator[/COLOR]", "", 'import_user_prompt', "{0}users.png".format(_ipath))

    # Hardcoded shows
    hardcoded_shows = {
        "Las Fierbinti": "las_fierbinti",
        "Vlad": "vlad",
        "Iubire cu parfum de lavanda": "iubire_cu_parfum_de_lavanda",
        "Clanul": "clanul",
        "Tatutu": "tatutu",
        "Baieti de oras": "baieti_de_oras",
        "Adela": "adela",
        "Lia - Sotia sotului meu": "lia_sotia_sotului_meu"
    }

    for show_name, show_id in hardcoded_shows.items():
        addDir(show_name, show_id, 'list_seasons', "{0}channels.png".format(_ipath))

    # Dynamically added shows from JSON
    save_file = translate_path('{0}/resources/files/saved_videos.json'.format(_path))
    if xbmcvfs.exists(save_file):
        try:
            with xbmcvfs.File(save_file, 'r') as f:
                content = f.read()
                if content:
                    saved_data = json.loads(content)
                    # Get unique serial names from json
                    json_shows = sorted(list(set([item['serial'] for item in saved_data if 'serial' in item])))
                    
                    for show_name in json_shows:
                        # Add show if not in hardcoded list
                        if show_name not in hardcoded_shows:
                            # The URL passed will be the show name itself, to be handled by a new function
                            addDir("[COLOR yellow]{0}[/COLOR]".format(show_name), show_name, 'list_saved_seasons', "{0}channels.png".format(_ipath))

        except Exception as e:
            xbmc.log("Error processing saved_videos.json for dynamic menu: {0}".format(e), xbmc.LOGERROR)

    xbmcplugin.endOfDirectory(pluginhandle)


def list_saved_seasons(show_name):
    save_file = translate_path('{0}/resources/files/saved_videos.json'.format(_path))
    seasons = set()
    if xbmcvfs.exists(save_file):
        try:
            with xbmcvfs.File(save_file, 'r') as f:
                content = f.read()
                if content:
                    saved_data = json.loads(content)
                    for item in saved_data:
                        if item.get('serial') == show_name and item.get('sezon'):
                            seasons.add(int(item['sezon']))
        except Exception as e:
            xbmc.log("Error reading seasons from saved_videos.json: {0}".format(e), xbmc.LOGERROR)

    if seasons:
        for season_num in sorted(list(seasons), reverse=True):
            url_param = "{0}|{1}".format(show_name, season_num)
            addDir("Sezonul {0}".format(season_num), url_param, 'list_saved_episodes', "{0}channels.png".format(_ipath))

    xbmcplugin.endOfDirectory(pluginhandle)


def list_saved_episodes(url):
    show_name, season_num = url.split('|')
    season_num = int(season_num)
    
    save_file = translate_path('{0}/resources/files/saved_videos.json'.format(_path))
    episodes = []
    if xbmcvfs.exists(save_file):
        try:
            with xbmcvfs.File(save_file, 'r') as f:
                content = f.read()
                if content:
                    saved_data = json.loads(content)
                    for item in saved_data:
                        if item.get('serial') == show_name and item.get('sezon') and int(item.get('sezon')) == season_num:
                            episodes.append(item)
        except Exception as e:
            xbmc.log("Error reading episodes from saved_videos.json: {0}".format(e), xbmc.LOGERROR)

    if episodes:
        # Sort episodes by episode number
        sorted_episodes = sorted(episodes, key=lambda x: int(x.get('episod', 0)))
        for episode_data in sorted_episodes:
            vid_id = episode_data.get('video_id')
            ep_num = int(episode_data.get('episod', 0))
            # Use video_title from json if available, otherwise construct a default one
            title = episode_data.get('video_title', "{0} - episodul {1}".format(show_name, ep_num))
            
            u = "{0}?url={1}&mode=playVideo".format(sys.argv[0], urllib_parse.quote_plus(vid_id))
            liz = make_listitem(name=title)
            liz.setArt({'thumb': "{0}videos.png".format(_ipath)})
            liz.setProperty('IsPlayable', 'true')
            xbmcplugin.addDirectoryItem(handle=int(sys.argv[1]), url=u, listitem=liz, isFolder=False)

    xbmcplugin.endOfDirectory(pluginhandle)

def list_seasons(url):
    show_id = url
    if show_id == "las_fierbinti":
        show_name = "Las Fierbinti"
        seasons_url = "https://www.tvmaze.com/shows/4071/las-fierbinti/seasons"
    elif show_id == "vlad":
        show_name = "Vlad"
        seasons_url = "https://www.tvmaze.com/shows/38309/vlad/seasons"
    elif show_id == "iubire_cu_parfum_de_lavanda":
        show_name = "Iubire cu parfum de lavanda"
        seasons_url = "https://www.tvmaze.com/shows/80908/iubire-cu-parfum-de-lavanda/seasons"
    elif show_id == "clanul":
        show_name = "Clanul"
        seasons_url = "https://www.tvmaze.com/shows/68023/clanul/seasons"
    elif show_id == "tatutu":
        show_name = "Tatutu"
        seasons_url = "https://www.tvmaze.com/shows/79887/tatutu/seasons"
    elif show_id == "baieti_de_oras":
        show_name = "Baieti de oras"
        seasons_url = "https://www.tvmaze.com/shows/55185/baieti-de-oras/seasons"
    elif show_id == "adela":
        show_name = "Adela"
        seasons_url = "https://www.tvmaze.com/shows/53958/adela/seasons"
    elif show_id == "lia_sotia_sotului_meu":
        show_name = "Lia - Sotia sotului meu"
        seasons_url = "https://www.tvmaze.com/shows/66548/lia-sotia-sotului-meu/seasons"
    else:
        xbmcplugin.endOfDirectory(pluginhandle)
        return

    headers = {'User-Agent': _UA}
    html_content = requests.get(seasons_url, headers=headers).text
    seasons_data = re.findall(r'<a href="(/seasons/(\d+)/[^"]+)">Season (\d+)</a>', html_content, re.IGNORECASE)
    seasons = sorted([(int(num), sid, url) for url, sid, num in seasons_data], reverse=True)
    for season_number, season_id, season_url in seasons:
        full_season_url = "https://www.tvmaze.com" + season_url + "/episodes"
        url_param = "{0}|{1}".format(show_name, full_season_url)
        addDir("Sezonul {0}".format(season_number), url_param, 'list_episodes', "{0}channels.png".format(_ipath))
    xbmcplugin.endOfDirectory(pluginhandle)

def list_episodes(url):
    show_name, episodes_url = url.split('|')

    # Load saved videos for priority matching
    saved_videos_lookup = {}
    save_file = translate_path('{0}/resources/files/saved_videos.json'.format(_path))
    if xbmcvfs.exists(save_file):
        try:
            with xbmcvfs.File(save_file, 'r') as f:
                content = f.read()
                if content:
                    saved_data = json.loads(content)
                    for item in saved_data:
                        try:
                            key = (item['serial'].lower().strip(), str(int(item['sezon'])), str(int(item['episod'])))
                            saved_videos_lookup[key] = item['video_id']
                        except (ValueError, KeyError):
                            continue # Skip malformed entries
        except Exception as e:
            xbmc.log("Error processing saved_videos.json: {0}".format(e), xbmc.LOGERROR)

    headers = {'User-Agent': _UA}
    html_content = requests.get(episodes_url, headers=headers).text
    episodes = re.findall(r'<a href="/episodes/\d+/[^>]*?(\d+)x(\d+)[^>]*?>([^<]+)</a>', html_content)
    for s_num, e_num, episode_title in episodes:
        saved_vid_id = None
        try:
            # Normalize numbers to ensure matching (e.g., '01' becomes '1')
            lookup_key = (show_name.lower().strip(), str(int(s_num)), str(int(e_num)))
            saved_vid_id = saved_videos_lookup.get(lookup_key)
        except ValueError:
            pass # s_num or e_num from regex is not a valid int

        if saved_vid_id:
            # Priority: Use the saved video ID
            new_title = "[COLOR green][SAVED][/COLOR] {0} - ep. {1:02d}".format(episode_title.strip(), int(e_num))
            u = "{0}?url={1}&mode=playVideo".format(sys.argv[0], urllib_parse.quote_plus(saved_vid_id))
            liz = make_listitem(name=new_title)
            liz.setArt({'thumb': "{0}videos.png".format(_ipath)})
            liz.setProperty('IsPlayable', 'true')
            
            context_items = []
            search_query_1 = "{0} S{1:02d}E{2:02d}".format(show_name, int(s_num), int(e_num))
            context_action_1 = 'Container.Update({0}?mode=search_episode&url={1})'.format(sys.argv[0], urllib_parse.quote_plus(search_query_1))
            context_items.append(('Cauta (format SXXEYY)', context_action_1))
            search_query_2 = "{0} s{1}e{2}".format(show_name.lower(), int(s_num), int(e_num))
            context_action_2 = 'Container.Update({0}?mode=search_episode&url={1})'.format(sys.argv[0], urllib_parse.quote_plus(search_query_2))
            context_items.append(('Cauta (format sXeY)', context_action_2))
            liz.addContextMenuItems(context_items)

            xbmcplugin.addDirectoryItem(handle=int(sys.argv[1]), url=u, listitem=liz, isFolder=False)
        else:
            # Fallback: Search on Dailymotion
            search_query1 = "{0} S{1:02d}E{2:02d}".format(show_name, int(s_num), int(e_num))
            search_url1 = "{0}/videos?fields=id,title&search={1}&sort=relevance&limit=10&family_filter={2}&localization={3}&page=1".format(urlMain, urllib_parse.quote_plus(search_query1), familyFilter, language)
            search_query2 = "{0} s{1}e{2}".format(show_name.lower(), int(s_num), int(e_num))
            search_url2 = "{0}/videos?fields=id,title&search={1}&sort=relevance&limit=10&family_filter={2}&localization={3}&page=1".format(urlMain, urllib_parse.quote_plus(search_query2), familyFilter, language)

            found_vid = None
            try:
                content = getUrl2(search_url1)
                data = json.loads(content)
                if data['list']:
                    for item in data['list']:
                        if "s{0:02d}e{1:02d}".format(int(s_num), int(e_num)).lower() in item['title'].lower():
                            found_vid = item['id']
                            break
                
                if not found_vid:
                    content = getUrl2(search_url2)
                    data = json.loads(content)
                    if data['list']:
                        for item in data['list']:
                            if "s{0}e{1}".format(int(s_num), int(e_num)).lower() in item['title'].lower():
                                found_vid = item['id']
                                break

                if found_vid:
                    new_title = "{0} - ep. {1:02d}".format(episode_title.strip(), int(e_num))
                    u = "{0}?url={1}&mode=playVideo".format(sys.argv[0], urllib_parse.quote_plus(found_vid))
                    liz = make_listitem(name=new_title)
                    liz.setArt({'thumb': "{0}videos.png".format(_ipath)})
                    liz.setProperty('IsPlayable', 'true')
                    
                    context_items = []
                    search_query_1 = "{0} S{1:02d}E{2:02d}".format(show_name, int(s_num), int(e_num))
                    context_action_1 = 'Container.Update({0}?mode=search_episode&url={1})'.format(sys.argv[0], urllib_parse.quote_plus(search_query_1))
                    context_items.append(('Cauta (format SXXEYY)', context_action_1))
                    search_query_2 = "{0} s{1}e{2}".format(show_name.lower(), int(s_num), int(e_num))
                    context_action_2 = 'Container.Update({0}?mode=search_episode&url={1})'.format(sys.argv[0], urllib_parse.quote_plus(search_query_2))
                    context_items.append(('Cauta (format sXeY)', context_action_2))
                    liz.addContextMenuItems(context_items)
                    xbmcplugin.addDirectoryItem(handle=int(sys.argv[1]), url=u, listitem=liz, isFolder=False)
                else:
                    new_title = "{0} - ep. {1:02d} (Not Found)".format(episode_title.strip(), int(e_num))
                    liz = make_listitem(name=new_title)
                    liz.setArt({'thumb': "{0}videos.png".format(_ipath)})
                    liz.setProperty('IsPlayable', 'false')
                    xbmcplugin.addDirectoryItem(handle=int(sys.argv[1]), url='', listitem=liz, isFolder=False)

            except Exception as e:
                xbmc.log("Error fetching episode: {0}".format(e), xbmc.LOGERROR)
                new_title = "{0} - ep. {1:02d} (Error)".format(episode_title.strip(), int(e_num))
                liz = make_listitem(name=new_title)
                liz.setArt({'thumb': "{0}videos.png".format(_ipath)})
                liz.setProperty('IsPlayable', 'false')
                xbmcplugin.addDirectoryItem(handle=int(sys.argv[1]), url='', listitem=liz, isFolder=False)

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
        "sezon": sezon_num,
        "episod": episod_num
    }

    save_dir = translate_path('{0}/resources/files/'.format(_path))
    save_file = translate_path('{0}/resources/files/saved_videos.json'.format(_path))

    if not xbmcvfs.exists(save_dir):
        xbmcvfs.mkdirs(save_dir)

    saved_data = []
    if xbmcvfs.exists(save_file):
        with xbmcvfs.File(save_file, 'r') as f:
            try:
                content = f.read()
                if content:
                    saved_data = json.loads(content)
            except Exception as e:
                xbmc.log("Error reading saved_videos.json: {0}".format(e), xbmc.LOGERROR)
    
    saved_data.append(data_to_save)

    with xbmcvfs.File(save_file, 'w') as f:
        f.write(json.dumps(saved_data, indent=4))

    xbmcgui.Dialog().notification('Succes', 'Datele video au fost salvate.', _icon, 3000, False)


def get_key(heading):
    keyboard = xbmc.Keyboard('', heading)
    keyboard.doModal()
    if keyboard.isConfirmed():
        return keyboard.getText()


def import_playlist_prompt():
    playlist_id = get_key("Introdu ID-ul playlist-ului Dailymotion")
    if not playlist_id: return

    serial_name = get_key("Introdu numele serialului")
    if not serial_name: return
    
    sezon_num = get_key("Introdu numarul sezonului")
    if not sezon_num: return

    start_episod_str = get_key("Introdu numarul episodului de start (default: 1)")
    if not start_episod_str or not start_episod_str.isdigit():
        start_episod = 1
    else:
        start_episod = int(start_episod_str)

    url_param = "{0}|{1}|{2}|{3}".format(playlist_id, serial_name, sezon_num, start_episod)
    import_playlist(url_param)


def import_playlist(params):
    playlist_id, serial_name, sezon_num, start_episod = params.split('|')
    start_episod = int(start_episod)
    
    pDialog.create('Import Playlist', 'Se preiau datele playlist-ului...')
    
    save_dir = translate_path('{0}/resources/files/'.format(_path))
    save_file = translate_path('{0}/resources/files/saved_videos.json'.format(_path))

    if not xbmcvfs.exists(save_dir):
        xbmcvfs.mkdirs(save_dir)

    saved_data = []
    if xbmcvfs.exists(save_file):
        with xbmcvfs.File(save_file, 'r') as f:
            try:
                content = f.read()
                if content:
                    saved_data = json.loads(content)
            except Exception as e:
                xbmc.log("Error reading saved_videos.json for import: {0}".format(e), xbmc.LOGERROR)

    # Create a lookup for faster duplicate checking
    # Key: (serial_name, sezon_num, episod_num)
    saved_lookup = {(item['serial'], str(item['sezon']), str(item['episod'])): item for item in saved_data}
    
    new_videos = []
    page = 1
    has_more = True
    imported_count = 0
    
    while has_more:
        if pDialog.iscanceled():
            break
        
        pDialog.update(int(page * 10), 'Se preia pagina {0}...'.format(page))
        
        api_url = "{0}/playlist/{1}/videos?fields=id,title&limit=100&page={2}".format(urlMain, playlist_id, page)
        try:
            content = getUrl2(api_url)
            data = json.loads(content)
        except Exception as e:
            xbmc.log("Failed to fetch playlist page: {0}".format(e), xbmc.LOGERROR)
            xbmcgui.Dialog().notification('Eroare', 'Nu s-a putut prelua playlist-ul.', _icon, 3000, False)
            pDialog.close()
            return

        if not data.get('list'):
            break # No more videos

        new_videos.extend(data['list'])
        has_more = data.get('has_more', False)
        page += 1

    if not new_videos:
        xbmcgui.Dialog().notification('Info', 'Playlist-ul este gol sau nu a fost gasit.', _icon, 3000, False)
        pDialog.close()
        return

    pDialog.update(90, 'Se proceseaza videoclipurile...')
    
    current_episode_num = start_episod
    for video_item in new_videos:
        lookup_key = (serial_name, sezon_num, str(current_episode_num))
        
        new_entry = {
            "video_id": video_item['id'],
            "video_title": video_item['title'],
            "serial": serial_name,
            "sezon": sezon_num,
            "episod": str(current_episode_num)
        }

        if lookup_key in saved_lookup:
            # Update existing entry
            saved_lookup[lookup_key].update(new_entry)
        else:
            # Add as a new entry to be appended later
            saved_lookup[lookup_key] = new_entry
        
        imported_count += 1
        current_episode_num += 1

    # Convert the lookup back to a list
    final_data = list(saved_lookup.values())

    try:
        with xbmcvfs.File(save_file, 'w') as f:
            f.write(json.dumps(final_data, indent=4))
        pDialog.close()
        xbmcgui.Dialog().notification('Succes', '{0} episoade importate/actualizate.'.format(imported_count), _icon, 4000, False)
    except Exception as e:
        pDialog.close()
        xbmc.log("Error writing saved_videos.json: {0}".format(e), xbmc.LOGERROR)
        xbmcgui.Dialog().notification('Eroare', 'Salvarea datelor a esuat.', _icon, 3000, False)


def _normalize_romanian(text):
    text = text.lower()
    text = text.replace('ă', 'a').replace('â', 'a')
    text = text.replace('î', 'i')
    text = text.replace('ș', 's')
    text = text.replace('ț', 't')
    return text

def _parse_season_episode(title):
    # Try SxxExx format, case-insensitive
    match = re.search(r's(\d{1,2})e(\d{1,3})', title, re.IGNORECASE)
    if match:
        return (str(int(match.group(1))), str(int(match.group(2))))

    # Try Sezonul X Episodul Y format, case-insensitive
    match = re.search(r'sezonul?\s*(\d{1,2})\s*episodul?\s*(\d{1,3})', title, re.IGNORECASE)
    if match:
        return (str(int(match.group(1))), str(int(match.group(2))))

    # Try 1x01 format
    match = re.search(r'(\d{1,2})x(\d{1,3})', title, re.IGNORECASE)
    if match:
        return (str(int(match.group(1))), str(int(match.group(2))))

    return (None, None)

def import_user_prompt():
    user_id = get_key("Introdu numele de utilizator Dailymotion")
    if not user_id: return

    serial_name = get_key("Introdu numele serialului")
    if not serial_name: return

    url_param = "{0}|{1}".format(user_id, serial_name)
    import_user_videos(url_param)

def import_user_videos(params):
    user_id, serial_name = params.split('|')
    
    pDialog.create('Import Inteligent', 'Se verifica ID-ul utilizatorului...')

    real_user_id = user_id # Default to original input
    try:
        api_lookup_url = "{0}/user/{1}?fields=id".format(urlMain, user_id)
        content = getUrl2(api_lookup_url)
        data = json.loads(content)
        if data.get('id'):
            real_user_id = data['id']
            xbmc.log("Dailymotion: Confirmed real user ID for '{0}' is '{1}'".format(user_id, real_user_id), xbmc.LOGDEBUG)
    except Exception as e:
        xbmc.log("Dailymotion: Exception while confirming user ID: {0}".format(e), xbmc.LOGERROR)

    pDialog.update(10, 'Se preiau datele...')
    
    # Fetch all videos from user
    all_videos = []
    page = 1
    has_more = True
    while has_more:
        if pDialog.iscanceled(): break
        pDialog.update(10 + int(page * 10), 'Se preia pagina {0}...'.format(page))
        api_url = "{0}/videos?owner={1}&fields=id,title&sort=recent&limit=100&page={2}".format(urlMain, real_user_id, page)
        try:
            content = getUrl2(api_url)
            data = json.loads(content)
            if data.get('list'):
                all_videos.extend(data['list'])
                has_more = data.get('has_more', False)
                page += 1
            else:
                has_more = False
        except Exception as e:
            xbmc.log("Failed to fetch user videos page: {0}".format(e), xbmc.LOGERROR)
            has_more = False

    if pDialog.iscanceled(): return

    if not all_videos:
        xbmcgui.Dialog().notification('Info', 'Utilizatorul nu are videoclipuri sau nu a fost gasit.', _icon, 3000, False)
        pDialog.close()
        return

    # Filter videos by serial name (diacritic-insensitive)
    pDialog.update(70, 'Se filtreaza videoclipurile pentru "{0}"...'.format(serial_name))
    normalized_serial = _normalize_romanian(serial_name)
    filtered_videos = [v for v in all_videos if normalized_serial in _normalize_romanian(v.get('title', ''))]

    if not filtered_videos:
        xbmcgui.Dialog().notification('Info', 'Nu s-au gasit videoclipuri pentru "{0}" la acest utilizator.'.format(serial_name), _icon, 4000, False)
        pDialog.close()
        return

    # Parse season and episode from titles
    pDialog.update(80, 'Se analizeaza titlurile video...')
    parsed_videos = []
    for video in filtered_videos:
        sezon, episod = _parse_season_episode(video['title'])
        if sezon and episod:
            parsed_videos.append({
                "video_id": video['id'],
                "video_title": video['title'],
                "serial": serial_name,
                "sezon": sezon,
                "episod": episod
            })

    if not parsed_videos:
        xbmcgui.Dialog().notification('Info', 'Nu s-a putut extrage sezon/episod din niciun titlu.', _icon, 4000, False)
        pDialog.close()
        return

    # Load existing data and merge
    pDialog.update(90, 'Se actualizeaza baza de date locala...')
    save_file = translate_path('{0}/resources/files/saved_videos.json'.format(_path))
    saved_data = []
    if xbmcvfs.exists(save_file):
        with xbmcvfs.File(save_file, 'r') as f:
            try:
                content = f.read()
                if content: saved_data = json.loads(content)
            except: pass

    saved_lookup = {(item['serial'], str(item['sezon']), str(item['episod'])): item for item in saved_data}
    
    updated_count = 0
    new_count = 0
    for video in parsed_videos:
        lookup_key = (video['serial'], video['sezon'], video['episod'])
        if lookup_key in saved_lookup:
            if saved_lookup[lookup_key]['video_id'] != video['video_id']:
                saved_lookup[lookup_key].update(video)
                updated_count += 1
        else:
            saved_lookup[lookup_key] = video
            new_count += 1

    # Save final data
    final_data = list(saved_lookup.values())
    try:
        with xbmcvfs.File(save_file, 'w') as f:
            f.write(json.dumps(final_data, indent=4))
        pDialog.close()
        xbmcgui.Dialog().notification('Succes', '{0} episoade noi, {1} actualizate.'.format(new_count, updated_count), _icon, 4000, False)
    except Exception as e:
        pDialog.close()
        xbmc.log("Error writing saved_videos.json: {0}".format(e), xbmc.LOGERROR)
        xbmcgui.Dialog().notification('Eroare', 'Salvarea datelor a esuat.', _icon, 3000, False)

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
elif mode == 'list_seasons':
    list_seasons(url)
elif mode == 'list_episodes':
    list_episodes(url)
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
elif mode == 'import_user_videos':
    import_user_videos(url)
else:
    index()
