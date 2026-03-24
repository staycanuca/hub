# -*- coding: utf-8 -*-
#-------------------------------------------------------------------------------
# HubStream by Caperucitaferoz based on previous work by:
# - Enen92 (https://github.com/enen92)
# - Joian (https://github.com/jonian)
#
# Thanks to those who have collaborated in any way, especially to:
# - @Canna_76
# - @AceStreamMOD (https://t.me/AceStreamMOD)
# - @luisma66 (tester raspberry)
#
# This file is part of HubStream for Kodi
#
# HubStream for Kodi is free software: you can redistribute and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
#-------------------------------------------------------------------------------

from lib.utils import *
import base64
import gzip
import json

from acestream.engine import Engine
from acestream.stream import Stream

error_flag = False

# OSD and MyPlayer classes are removed as they are part of the old, direct playback method.
# The new implementation uses setResolvedUrl for better integration with Kodi.

def get_historial():
    historial = list()
    settings_path= os.path.join(data_path, "historial.json")
    if os.path.isfile(settings_path):
        try:
            historial = load_json_file(settings_path)
        except Exception:
            logger("Error load_file", "error")

    return historial


def add_historial(contenido):
    historial = get_historial()
    settings_path = os.path.join(data_path, "historial.json")

    trobat = False
    for i in historial:
        if i['infohash'] == contenido['infohash']:
            trobat = True
            break

    if not trobat:
        historial.insert(0, contenido)
        dump_json_file(historial[:10], settings_path)


def clear_cache():
    aux = False
    home = '.'
    try:
        acestream_cachefolder = get_setting("acestream_cachefolder", None)
        if not acestream_cachefolder:
            if system_platform == "windows":
                home = os.getenv("SystemDrive") + r'\\'
                acestream_cachefolder = os.path.join(os.getenv("SystemDrive"), '_acestream_cache_')
            elif system_platform == "linux":
                home = os.getenv("HOME")
                acestream_cachefolder = os.path.join(os.getenv("HOME"), '.ACEStream', 'cache', '.acestream_cache')
            else:
                home = "/storage/emulated/0/"
                acestream_cachefolder = '/storage/emulated/0/org.acestream.engine/.ACEStream/.acestream_cache'

        acestream_cachefolder = acestream_cachefolder if os.path.isdir(acestream_cachefolder) else None

        if not acestream_cachefolder:
            for root, dirnames, filenames in os.walk(home):
                if root.endswith(os.path.join('.ACEStream','cache')):
                    aux = root
                if re.search(r'.acestream_cache.?', root):
                    acestream_cachefolder = root
                    break

        if not acestream_cachefolder and aux:
            acestream_cachefolder = aux

        if acestream_cachefolder:
            set_setting("acestream_cachefolder", acestream_cachefolder)
            dirnames, filenames = xbmcvfs.listdir(acestream_cachefolder)
            for f in filenames:
                xbmcvfs.delete(os.path.join(acestream_cachefolder, f))
            logger("clear_cache")
        else:
            logger("clear_cache: cache not found", "error")

    except:
        logger("error clear_cache", "error")


def read_torrent(torrent,headers=None):
    import bencodepy
    import hashlib

    infohash = None

    try:
        if torrent.lower().startswith('http'):
            from six.moves import urllib_request

            if not headers:
                headers = dict()
            elif not isinstance(headers,dict):
                headers = eval(headers)

            if not 'User-Agent' in headers:
                headers['User-Agent'] = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:86.0) Gecko/20100101 Firefox/86.0'

            req = urllib_request.Request(torrent, headers=headers)
            torrent_file = urllib_request.urlopen(req).read()

        elif os.path.isfile(torrent):
            torrent_file = open(torrent, "rb").read()

        metainfo = bencodepy.decode(torrent_file)

        if not six.PY3:
            infohash = hashlib.sha1(bencodepy.encode(metainfo['info'])).hexdigest()
        else:
            infohash = hashlib.sha1(bencodepy.encode(metainfo[b'info'])).hexdigest()
        logger(infohash)

    except Exception as e:
        logger(e, 'error')

    return infohash

def resolve_stream(id=None, url=None, infohash=None):
    global error_flag
    error_flag = False
    engine = None
    stream = None
    acestream_executable = None
    cmd_stop_acestream = None

    if infohash:
        url = id = None
    elif url:
        infohash = id = None
    else:
        regex = re.compile(r'[0-9a-f]{40}\Z',re.I)
        if not id or not regex.match(id):
            xbmcgui.Dialog().ok(HEADING, translate(30015))
            return None

    if id and system_platform == 'android' and get_setting("reproductor_externo"):
        AndroidActivity = 'StartAndroidActivity("","org.acestream.action.start_content","","acestream:?content_id=%s")' % id
        logger("Abriendo " + AndroidActivity)
        xbmc.executebuiltin(AndroidActivity)
        return None

    if not server.available:
        if system_platform == "windows":
            acestream_executable = os.path.join(get_setting("install_acestream"), 'ace_engine.exe')
        elif system_platform == "linux":
            if arquitectura == 'x86':
                if root:
                    acestream_executable = os.path.join(get_setting("install_acestream"), 'acestream_chroot.start')
                    cmd_stop_acestream = ["pkill", "acestream"]
                else:
                    if os.path.exists('/snap/acestreamplayer'):
                        acestream_executable = 'snap run acestreamplayer.engine'
                        cmd_stop_acestream = ["pkill", "acestream"]
                    else:
                        xbmcgui.Dialog().ok(HEADING,translate(30027))
                        return None
            elif arquitectura == 'arm' and not root:
                try:
                    data = ''
                    with open("/etc/os-release") as f:
                        data = six.ensure_str(f.read())
                    if re.search('osmc|openelec|raspios|raspbian', data, re.I):
                        acestream_executable = 'sudo ' + os.path.join(get_setting("install_acestream"), 'acestream.start')
                        cmd_stop_acestream = ['sudo', os.path.join(get_setting("install_acestream"), 'acestream.stop')]
                except: pass
            else:
                acestream_executable = os.path.join(get_setting("install_acestream"), 'acestream.start')
                cmd_stop_acestream = [os.path.join(get_setting("install_acestream"), 'acestream.stop')]
        elif system_platform == 'android':
            if xbmcgui.Dialog().yesno(HEADING, translate(30041)):
                try:
                    xbmc.executebuiltin('StartAndroidActivity("org.acestream.engine")')
                except:
                    xbmcgui.Dialog().ok(HEADING, translate(30016))
                    return None
            else:
                return None

        logger("acestream_executable= %s" % acestream_executable)
        if cmd_stop_acestream:
            set_setting("cmd_stop_acestream", cmd_stop_acestream)
        if acestream_executable and not server.available:
            engine = Engine(acestream_executable)
        elif not acestream_executable and system_platform != 'android':
            logger("plataforma desconocida: %s" % system_platform)
            if not xbmcgui.Dialog().yesno(HEADING, translate(30016), nolabel=translate(30017), yeslabel=translate(30018)):
                return None

    try:
        d = xbmcgui.DialogProgress()
        d.create(HEADING, translate(30033))
        timedown = time.time() + get_setting("time_limit")

        if not acestream_executable or system_platform == 'android':
            while not d.iscanceled() and not server.available and time.time() < timedown and error_flag == False:
                seg = int(timedown - time.time())
                progreso = int((seg * 100) / get_setting("time_limit"))
                line1 = translate(30033)
                line2 = translate(30006) % seg
                try:
                    d.update(progreso, line1, line2)
                except:
                    d.update(progreso, '\n'.join([line1, line2]))
                time.sleep(1)
            if not server.available:
                d.close()
                notification_error(translate(30019))
                raise Exception("accion cancelada o timeout")
        elif engine and not server.available:
            engine.connect(['error','error::subprocess'], notification_error)
            engine.start()
            while not d.iscanceled() and (not engine.running or not server.available) and time.time() < timedown and error_flag == False:
                seg = int(timedown - time.time())
                progreso = int((seg * 100) / get_setting("time_limit"))
                line1 = translate(30033)
                line2 = translate(30006) % seg
                try:
                    d.update(progreso, line1, line2)
                except:
                    d.update(progreso, '\n'.join([line1, line2]))
                time.sleep(1)
            if d.iscanceled() or time.time() >= timedown or error_flag == True:
                if engine.running:
                    engine.stop()
                d.close()
                if time.time() >= timedown:
                    notification_error(translate(30019))
                raise Exception("accion cancelada o timeout")

        hls = False
        if id:
            stream = Stream(server, id=id)
        elif url:
            hls = True
            stream = Stream(server, url=url)
        else:
            hls = True
            stream = Stream(server, infohash=infohash)

        stream.connect('error', notification_error)
        stream.connect(['started','stopped'], notification_info)
        stream.start(hls=hls)

        timedown = time.time() + get_setting("time_limit")
        while not d.iscanceled() and time.time() < timedown and (not stream.status or stream.status != 'dl') and error_flag == False:
            if stream.status != 'prebuf':
                seg = int(timedown - time.time())
                progreso = int((seg * 100) / get_setting("time_limit"))
            else:
                progreso = stream.stats.progress
                timedown = time.time() + 100
            if not stream.status:
                line1 = translate(30034)
            elif stream.status == 'prebuf':
                line1 = translate(30008) %(progreso) + '%'
            elif stream.status == 'dl':
                line1 = translate(30007)
            else:
                line1 = stream.status
            line2 = translate(30010) % stream.stats.speed_down
            line3 = translate(30012) % stream.stats.peers
            try:
                d.update(progreso, line1, line2, line3)
            except:
                d.update(progreso, '\n'.join([line1, line2, line3]))
            time.sleep(0.25)

        d.close()
        if d.iscanceled() or time.time() >= timedown or error_flag == True:
            if stream:
                stream.stop()
            raise Exception("accion cancelada o timeout")
        
        return stream

    except Exception as e:
        logger(e, 'error')
        if 'stream' in locals() and stream:
            stream.stop()
        return None

def notification_info(*args,**kwargs):
    transmitter = kwargs['class_name']
    msg = kwargs['event_name']

    logger("%s: %s" %(transmitter, msg))

def notification_error(*args,**kwargs):
    global error_flag
    transmitter = kwargs.get('class_name', ADDON_NAME)
    event = kwargs.get('event_name','')
    msg = args[0]
    error_flag = True

    logger("Error in %s: %s" % (transmitter, msg))

    if event != 'error::subprocess':
        xbmcgui.Dialog().notification('Error Acestream %s' % transmitter, msg,
                                      os.path.join(runtime_path, 'resources', 'media', 'error.png'))


def mainmenu():
    itemlist = list()

    if get_favorites():
        itemlist.append(Item(
            label="Favorites",
            action='list_favorites'
        ))

    itemlist.append(Item(
        label="Sport Agenda",
        action='list_sport_submenu'
    ))

    itemlist.append(Item(
        label="Ace Channels",
        action='list_ace_channels'
    ))

    itemlist.append(Item(
        label="User Lists",
        action='user_lists_menu'
    ))

    itemlist.append(Item(
        label="Search",
        action='search_submenu'
    ))

    itemlist.append(Item(
        label=translate(30020),
        action='play'
    ))

    if get_historial():
        itemlist.append(Item(
            label = translate(30037),
            action = 'historial'
        ))

    if server.available and system_platform != 'android':
        itemlist.append(Item(
            label= translate(30036),
            action='kill'
        ))

    itemlist.append(Item(
        label= translate(30021),
        action='open_settings'
    ))

    return itemlist


def ass_decoder(ass_id_or_json):
    from six.moves import urllib_request

    itemlist = list()
    is_json = 1
    try:
        json_data = json.loads(ass_id_or_json)
    except:
        is_json = 0
    if not is_json:
    #input is  ASS ID and not json
        req = urllib_request.Request("https://dns.google/resolve?name={}.elcano.top&type=TXT".format(ass_id_or_json.replace("ass://","")), data=None, headers={'Accept': 'application/json'})
        response = json.loads(six.ensure_str(urllib_request.urlopen(req).read()))
        if "Answer" in response.keys():
            for i in range(len(response["Answer"])):
                if "H4sIAAAAAAAA" in response["Answer"][i]["data"]:
                #gz data
                    json_data = gzip.decompress(base64.b64decode(response["Answer"][i]["data"])).decode("utf-8")
                else:
                #base64
                    json_data = base64.b64decode(response["Answer"][i]["data"]).decode("utf-8")
                itemlist = itemlist + ass_decoder(json_data)
    else:
        for i in range(len(json_data)):
            jsitem = json_data[i]
            if "subLinks" in jsitem.keys():
                itemlist = itemlist + ass_decoder(json.dumps(jsitem["subLinks"]))
            elif "ref" in jsitem.keys():
                itemlist = itemlist + ass_decoder(jsitem["ref"])
            elif "url" in jsitem.keys() and len(jsitem["url"]) >= 40:
                itemlist.append(Item(label=jsitem["name"] ,action='play',id=jsitem["url"].replace("acestream://",""), isPlayable=True))
            else:
                xbmc.log("HUBSTREAM - ASS decoder ignored item: " + str(jsitem))
    return itemlist


def search(url):
    from six.moves import urllib_request

    itemlist = list()
    ids = list()

    # Ejemplos de urls validas: 
    # 

    try:
        if "://" not in url:
            req = urllib_request.Request("https://acestreamsearch.net/en/?q={}".format(url), data=None, headers={'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_9_3) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/35.0.1916.47 Safari/537.36'})
            data = six.ensure_str(urllib_request.urlopen(req).read())
            data=data.split('list-group">')[1].split("</ul>")[0]
            data = re.sub(r"\\n|\\r|\\t|\\s{2}|&nbsp;", "", data)
            patron = '<a href="(.*?)">(\\w*.*?)<'
            for channel in re.findall(patron, data, re.I):
                itemlist.append(Item(label=channel[1]+ " (acestreamsearch.net)",
                            action='play',
                            id=channel[0].replace("acestream://",""),
                            isPlayable=True))
            req = urllib_request.Request("https://search-ace.stream/search?query={}".format(url), data=None, headers={'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_9_3) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/35.0.1916.47 Safari/537.36'})
            data = json.loads(six.ensure_str(urllib_request.urlopen(req).read()))
            for i in range(len(data)):
                itemlist.append(Item(label=data[i]["name"]+ " (search-ace.stream)",
                            action='play',
                            id=data[i]["content_id"],
                            isPlayable=True))
            req = urllib_request.Request("https://search.acestream.net/search?query={}".format(url), data=None, headers={'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_9_3) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/35.0.1916.47 Safari/537.36'})
            data = json.loads(six.ensure_str(urllib_request.urlopen(req).read()))
            for i in data['results']:
                itemlist.append(Item(label=i["name"]+ " (search.acestream.net)",
                            action='play',
                            id=i["infohash"],
                            isPlayable=True))
        elif url.startswith("ass://"):
            itemlist = ass_decoder(url)
        else:
            req = urllib_request.Request(url, data=None, headers={'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_9_3) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/35.0.1916.47 Safari/537.36'})
            data = six.ensure_str(urllib_request.urlopen(req).read())

            if data:
                if url.startswith('https://ipfs.io/'):
                    data = re.sub(r"\\n|\\r|\\t|\\s{2}|&nbsp;", "", data)
                    patron = '<a href="(/ipfs/[^\"]+acelive)">(\d*)'
                    for ace,n in re.findall(patron, data, re.I):
                        itemlist.append(Item(label="Arenavisión Canal " + n,
                                             action='play',
                                             url="https://ipfs.io" + ace,
                                             isPlayable=True))
                elif url.startswith('https://pastebin') or "192.168." in url:
                    counter = 0
                    for it in data.split('\n'):
                        if len(it) > 1:
                            if (counter % 2) == 0:
                                name = it
                            else:
                                id = re.findall('([0-9a-f]{40})', it, re.I)[0]
                                itemlist.append(Item(label=name ,action='play',id=id, isPlayable=True))
                            counter = counter + 1
                elif "elcano" in url:
                    data = json.loads(data.split("linksData = ")[1].split(";")[0])
                    for link in data["links"]:
                        if len(link["url"]) >= 40:
                            itemlist.append(Item(label=link["name"] ,action='play',id=link["url"].replace("acestream://",""), isPlayable=True))
                elif "shickat" in url:
                    data = data.split('id="canal-list">')[1].split("</section>")[0]
                    for line in data.split("\n"):
                        if "canal-nombre" in line:
                            name = line.split(">")[1].split("<")[0]
                        elif "acestream-link" in line:
                            id = line.split('href="')[1].split('"')[0].replace("acestream://","")
                            itemlist.append(Item(label=name ,action='play',id=id, isPlayable=True))
                elif "vercel.app" in url:
                    data = re.sub(r"\\n|\\r|\\t|\\s{2}|&nbsp;", "", data)
                    patron = '<a href=["\\](.*?)["\\](?: target="_blank"|)>(\\w*.*?)</a>'
                    for channel in re.findall(patron, data, re.I):
                        itemlist.append(Item(label=channel[1],
                                action='play',
                                id=channel[0].replace("acestream://",""),
                                isPlayable=True))
                else:
                    data = re.sub(r"\\n|\\r|\\t|\\s{2}|&nbsp;", "", data)
                    try:
                        for n, it in enumerate(eval(re.findall('(\[.*?])', data)[0])):
                            label = it.get("name", it.get("title", it.get("label")))
                            id = it.get("id", it.get("url"))
                            id = re.findall('([0-9a-f]{40})', id, re.I)[0]
                            icon = it.get("icon", it.get("image", it.get("thumb")))

                            new_item = Item(label= label if label else translate(30030) % (n,id), action='play', id=id, isPlayable=True)

                            if icon:
                                new_item.icon = icon

                            itemlist.append(new_item)
                    except:
                        for patron in [r'#EXTINF:-1.*?id="([^"]+)".*?([0-9a-f]{40})', r'#EXTINF:-1.*?,(.*?)http.*?([0-9a-f]{40})']:
                            for label, id in re.findall(patron, data):
                                itemlist.append(Item(label=label, action='play', id=id, isPlayable=True))
                            if itemlist: break

                        if not itemlist:
                            itemlist = []
                            for patron in [r'acestream://([0-9a-f]{40})', r'(?:">)([0-9a-f]{40})(?:")<']:
                                n = 1
                                for id in re.findall(patron, data, re.I):
                                    if id not in ids:
                                        ids.append(id)
                                        itemlist.append(Item(label= translate(30030) % (n,id),
                                                             action='play',
                                                             id= id,
                                                             isPlayable=True))
                                        n += 1
                                if itemlist: break
    except: pass

    return itemlist


def kill_process():
    cmd_stop_acestream = get_setting("cmd_stop_acestream")

    if system_platform == 'windows':
        os.system('taskkill /f /im ace_engine.exe')

    elif cmd_stop_acestream:
        logger("cmd_stop_acestream= %s" % cmd_stop_acestream)
        subprocess.call(cmd_stop_acestream)


    time.sleep(0.75)

    if not server.available:
        logger("Motor Acestream cerrado")
        xbmcgui.Dialog().notification(HEADING, translate(30035),
                                      os.path.join(runtime_path, 'resources', 'media', 'icon.png'))
        return True
    else:
        logger("Motor Acestream NO cerrado")
        xbmcgui.Dialog().notification(HEADING, translate(30040),
                                      os.path.join(runtime_path, 'resources', 'media', 'error.png'))
        return False


def parse_sport_groups(groups):
    itemlist = list()
    for group in groups:
        if isinstance(group, dict):
            name = group.get('name', '').strip()
            # Allow names with '>' but not standalone '>' or containing newlines
            if not name or '\n' in name or name == '>':
                continue

            if group.get('stations'):
                # Check for acestream links before creating the folder
                acestream_stations = [s for s in group['stations'] if isinstance(s, dict) and s.get('url', '').startswith('acestream://')]
                if acestream_stations:
                    item = Item(label=name, action='list_stations', stations=acestream_stations, icon=group.get('image', ''))
                    itemlist.append(item)
            elif group.get('groups'):
                sub_items = parse_sport_groups(group['groups'])
                if sub_items:
                    item = Item(label=name, action='list_sub_groups', subgroups=[sub_item.__dict__ for sub_item in sub_items], icon=group.get('image', ''))
                    itemlist.append(item)
    return itemlist

def list_sport_events():
    from six.moves import urllib_request
    itemlist = list()
    try:
        req = urllib_request.Request("http://elizabethharmon.zapto.org/elsup/wiseManager.php", data=None, headers={'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_9_3) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/35.0.1916.47 Safari/537.36'})
        response = urllib_request.urlopen(req)
        data = six.ensure_str(response.read())
        
        # Handle potential BOM and decode properly
        if data.startswith('\ufeff'):
            data = data[1:]
            
        data = json.loads(data)
        itemlist = parse_sport_groups(data.get('groups', []))
    except Exception as e:
        logger("Error fetching sport events: %s" % str(e), 'error')
        import traceback
        logger("Traceback: %s" % traceback.format_exc(), 'error')
    return itemlist

def list_stations(stations_data):
    itemlist = list()
    for station in stations_data:
        if isinstance(station, dict) and station.get('url', '').startswith('acestream://') and station.get('name'):
            url = station['url']
            item = Item(label=station['name'], action='play', id=url.replace("acestream://", "").strip(), icon=station.get('image', ''), isPlayable=True)
            itemlist.append(item)
    return itemlist

def list_sport_submenu():
    itemlist = list()
    itemlist.append(Item(label="Sport Events", action='list_sport_events'))
    itemlist.append(Item(label="Sport Channels", action='list_sport_channels'))
    return itemlist

def list_sport_channels():
    from six.moves import urllib_request
    import json
    itemlist = list()
    try:
        req = urllib_request.Request("https://raw.githubusercontent.com/Osfesi/mis-canales-app/50f98c2134c5971d4534d05c4dcd579c181f04b1/Canales_acestream.txt")
        data = six.ensure_str(urllib_request.urlopen(req).read()).strip()
        
        decoder = json.JSONDecoder()
        channels = []
        pos = 0
        while pos < len(data):
            # Skip whitespace and commas
            while pos < len(data) and (data[pos].isspace() or data[pos] == ','):
                pos += 1
            if pos == len(data):
                break
            
            # Find the start of the next object
            if data[pos] == '{':
                try:
                    obj, pos = decoder.raw_decode(data, pos)
                    channels.append(obj)
                except json.JSONDecodeError:
                    # Malformed object, find next potential start
                    pos = data.find('{', pos + 1)
                    if pos == -1:
                        break # No more objects
            else:
                # Should not happen in this file, but as a safeguard
                pos += 1

        for channel in channels:
            name = channel.get('name', '')
            if '-->' in name:
                name = name.split('-->')[0]
            if len(name) > 30:
                name = name[:30]
            name = name.strip()
            url = channel.get('url', '')
            if name and url.startswith('acestream://'):
                item = Item(label=name, action='play', id=url.replace('acestream://', ''), isPlayable=True)
                itemlist.append(item)
    except Exception as e:
        logger(e, 'error')
    return itemlist

def list_ace_channels():
    from six.moves import urllib_request
    itemlist = list()
    try:
        url = "https://acestreamui.app/static/js/main.5c0cebab.js"
        req = urllib_request.Request(url, data=None, headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'})
        data = six.ensure_str(urllib_request.urlopen(req).read())
        
        patron = r'infohash:"([a-f0-9]+)",name:"(.*?)"'
        matches = re.findall(patron, data)
        
        for infohash, name in matches:
            itemlist.append(Item(label=name, action='play', infohash=infohash, isPlayable=True))

    except Exception as e:
        logger(e, 'error')
    
    return itemlist

def get_user_lists():
    user_lists = list()
    settings_path = os.path.join(data_path, "user_lists.json")
    if os.path.isfile(settings_path):
        try:
            user_lists = load_json_file(settings_path)
        except Exception:
            logger("Error load_file", "error")
    return user_lists

def user_lists_menu():
    itemlist = list()
    user_lists = get_user_lists()

    for user_list in user_lists:
        itemlist.append(Item(label=user_list['name'], action='list_user_list_items', url=user_list['url']))

    itemlist.append(Item(label="Add List", action='add_user_list'))
    itemlist.append(Item(label="Delete List", action='delete_user_list'))

    return itemlist

def add_user_list():
    user_lists = get_user_lists()
    list_name = xbmcgui.Dialog().input("List Name")
    if not list_name:
        return
    list_url = xbmcgui.Dialog().input("List URL")
    if not list_url:
        return

    user_lists.append({'name': list_name, 'url': list_url})
    settings_path = os.path.join(data_path, "user_lists.json")
    dump_json_file(user_lists, settings_path)
    xbmc.executebuiltin('Container.Refresh')

def delete_user_list():
    user_lists = get_user_lists()
    list_names = [user_list['name'] for user_list in user_lists]
    selected_index = xbmcgui.Dialog().select("Select a list to delete", list_names)

    if selected_index != -1:
        del user_lists[selected_index]
        settings_path = os.path.join(data_path, "user_lists.json")
        dump_json_file(user_lists, settings_path)
        xbmc.executebuiltin('Container.Refresh')

def list_user_list_items(url):
    from six.moves import urllib_request
    import re
    itemlist = list()
    try:
        req = urllib_request.Request(url)
        data = six.ensure_str(urllib_request.urlopen(req).read())
        if data:
            name = None
            for line in data.split('\n'):
                line = line.strip()
                if line.startswith('#EXTINF'):
                    name = line.split(',')[-1]
                elif (line.startswith('acestream://') or 'ace/getstream?id=' in line) and name:
                    if line.startswith('acestream://'):
                        id = line.replace('acestream://','').strip()
                    else:
                        id_match = re.search('id=([0-9a-fA-F]{40})', line, re.I)
                        if id_match:
                            id = id_match.group(1)
                        else:
                            continue
                    itemlist.append(Item(label=name, action='play', id=id, isPlayable=True))
                    name = None
    except Exception as e:
        logger(e, 'error')
    return itemlist

def search_acestream_main():
    from six.moves import urllib_request
    itemlist = list()
    query = xbmcgui.Dialog().input("Search query")
    if not query:
        return

    try:
        url = "https://search-ace.stream/search?query={}".format(query)
        req = urllib_request.Request(url)
        data = json.loads(six.ensure_str(urllib_request.urlopen(req).read()))
        for i in range(len(data)):
            itemlist.append(Item(label=data[i]["name"]+ " (search-ace.stream)",
                        action='play',
                        id=data[i]["content_id"],
                        isPlayable=True))
    except Exception as e:
        logger(e, 'error')

    return itemlist

def search_acestreamsearch_net():
    from six.moves import urllib_request
    itemlist = list()
    query = xbmcgui.Dialog().input("Search query")
    if not query:
        return

    try:
        req = urllib_request.Request("https://acestreamsearch.net/en/?q={}".format(query), data=None, headers={'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_9_3) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/35.0.1916.47 Safari/537.36'})
        data = six.ensure_str(urllib_request.urlopen(req).read())
        data=data.split('list-group">')[1].split("</ul>")[0]
        data = re.sub(r"\\n|\\r|\\t|\\s{2}|&nbsp;", "", data)
        patron = '<a href="(.*?)">(\\w*.*?)<'
        for channel in re.findall(patron, data, re.I):
            itemlist.append(Item(label=channel[1]+ " (acestreamsearch.net)",
                        action='play',
                        id=channel[0].replace("acestream://",""),
                        isPlayable=True))
    except Exception as e:
        logger(e, 'error')

    return itemlist

def search_submenu():
    itemlist = list()
    itemlist.append(Item(
        label="Search on search-ace.stream",
        action='search_acestream_main'
    ))

    itemlist.append(Item(
        label="Search on acestreamsearch.net",
        action='search_acestreamsearch_net'
    ))

    itemlist.append(Item(
        label="Search multiple providers",
        action='search'
    ))
    return itemlist

def get_favorites():
    favorites = list()
    settings_path = os.path.join(data_path, "favorites.json")
    if os.path.isfile(settings_path):
        try:
            favorites = load_json_file(settings_path)
        except Exception:
            logger("Error load_file", "error")
    return favorites

def add_to_favorites(item):
    favorites = get_favorites()
    favorites.append(item.__dict__)
    settings_path = os.path.join(data_path, "favorites.json")
    dump_json_file(favorites, settings_path)
    xbmcgui.Dialog().notification("Favorites", "Channel added to favorites")

def list_favorites():
    itemlist = list()
    favorites = get_favorites()
    for favorite in favorites:
        itemlist.append(Item(**favorite))
    return itemlist

def run(item):
    itemlist = list()

    if not item.action:
        logger("Item sin acción")
        return

    if item.action == "mainmenu":
        itemlist = mainmenu()

    elif item.action == "list_sport_submenu":
        itemlist = list_sport_submenu()

    elif item.action == "list_ace_channels":
        itemlist = list_ace_channels()

    elif item.action == "user_lists_menu":
        itemlist = user_lists_menu()

    elif item.action == "search_submenu":
        itemlist = search_submenu()

    elif item.action == "add_user_list":
        add_user_list()

    elif item.action == "delete_user_list":
        delete_user_list()

    elif item.action == "list_user_list_items":
        itemlist = list_user_list_items(item.url)

    elif item.action == "search_acestream_main":
        itemlist = search_acestream_main()

    elif item.action == "search_acestreamsearch_net":
        itemlist = search_acestreamsearch_net()

    elif item.action == "list_favorites":
        itemlist = list_favorites()

    elif item.action == "add_to_favorites":
        add_to_favorites(item)

    elif item.action == "list_sport_events":
        itemlist = list_sport_events()

    elif item.action == "list_sport_channels":
        itemlist = list_sport_channels()

    elif item.action == "list_stations":
        itemlist = list_stations(item.stations)

    elif item.action == "list_sub_groups":
        itemlist = [Item(**sub_item) for sub_item in item.subgroups]

    elif item.action == "kill":
        if kill_process():
            xbmc.executebuiltin('Container.Refresh')

    elif item.action == "historial":
        for it in get_historial():
            itemlist.append(Item(label= it.get('title'),
                                 action='play',
                                 infohash=it.get('infohash'),
                                 icon=it.get('icon'),
                                 plot=it.get('plot')))

    elif item.action == "search":
        url_list = xbmcgui.Dialog().input(translate(30032),get_setting("last_search", "http://acetv.org/js/data.json"))
        if url_list:
            itemlist = list()
            tmp_itemlist = list()
            ids = list()
            for url in url_list.split(";"):
                if url:
                    tmp_itemlist.append(Item(label=">>>>>>>>>> Source [{}] <<<<<<<<<<".format(url) ,action='play',id=url))
                    tmp_itemlist = tmp_itemlist + search(url)
            for item in tmp_itemlist:
                if item.id not in ids:
                    itemlist.append(item)
                    ids.append(item.id)
            if len(itemlist) > len(url_list.split(";")):
                set_setting("last_search", url_list)
            else:
                xbmcgui.Dialog().ok(HEADING,  translate(30031) % url_list)
        else:
            return

    elif item.action == 'open_settings':
            xbmcaddon.Addon().openSettings()


    elif item.action == 'play':
        id = url = infohash = None
        title = item.label or item.title
        iconimage = item.icon
        plot = item.plot

        if item.id:
            id = item.id
        elif item.url:
            url = item.url
        elif item.infohash:
            infohash = item.infohash
        else:
            last_id = get_setting("last_id", "a0270364634d9c49279ba61ae3d8467809fb7095")
            input_str = xbmcgui.Dialog().input(translate(30022), last_id if get_setting("remerber_last_id") else "")
            if not input_str:
                return
            if re.findall('^(http|magnet)', input_str, re.I):
                url = input_str
            else:
                id = input_str.replace("acestream://","")
            title = id or url

        if url and url.lower().endswith('.torrent'):
            infohash = read_torrent(url)
            url = None
        elif url and url.lower().startswith('magnet:'):
            match = re.findall('xt=urn:btih:([a-f0-9]+)', url, re.I)
            if match:
                infohash = match[0]
                url = None
        
        stream = resolve_stream(id=id, url=url, infohash=infohash)

        if stream and stream.playback_url:
            logger("Stream resolved. URL: %s" % stream.playback_url)
            listitem = xbmcgui.ListItem(path=stream.playback_url)
            listitem.setInfo('video', {'title': title, 'plot': plot})
            listitem.setArt(item.getart())
            listitem.setProperty('IsPlayable', 'true')
            
            if stream.infohash:
                 add_historial({'infohash': stream.infohash,
                               'title': title,
                               'icon': iconimage,
                               'plot': plot})
            if stream.id:
                set_setting("last_id", stream.id)

            xbmcplugin.setResolvedUrl(handle=int(sys.argv[1]), succeeded=True, listitem=listitem)
        else:
            logger("Failed to resolve stream.", "error")
            xbmcplugin.setResolvedUrl(handle=int(sys.argv[1]), succeeded=False, listitem=xbmcgui.ListItem())


    if itemlist:
        for item in itemlist:
            listitem = xbmcgui.ListItem(item.label or item.title)
            listitem.setInfo('video', {'title': item.label or item.title, 'mediatype': 'video'})
            listitem.setArt(item.getart())
            listitem.setInfo('video', {'plot': item.plot or item.id})

            if item.isPlayable:
                listitem.setProperty('IsPlayable', 'true')
                isFolder = False
                context_menu = [("Add to Favorites", 'RunPlugin(%s?%s)' % (sys.argv[0], Item(action='add_to_favorites', label=item.label, id=item.id).tourl()))]
                listitem.addContextMenuItems(context_menu)

            elif isinstance(item.isFolder, bool):
                isFolder = item.isFolder

            elif not item.action:
                isFolder = False

            else:
                isFolder = True

            xbmcplugin.addDirectoryItem(
                handle=int(sys.argv[1]),
                url='%s?%s' % (sys.argv[0], item.tourl()),
                listitem=listitem,
                isFolder= isFolder,
                totalItems=len(itemlist)
            )
        
        xbmcplugin.addSortMethod(handle=int(sys.argv[1]), sortMethod=xbmcplugin.SORT_METHOD_NONE)
        xbmcplugin.endOfDirectory(handle=int(sys.argv[1]), succeeded=True)


if __name__ == '__main__':
    if system_platform in ['linux', 'windows'] and not get_setting("install_acestream"):
        install_acestream()

    if sys.argv[2]:
        item = None
        try:
            item = Item().fromurl(sys.argv[2])
        except:
            # Fallback for external calls that are not Item objects
            argumentos = dict()
            for c in sys.argv[2][1:].split('&'):
                k, v = c.split('=')
                argumentos[k] = urllib_parse.unquote_plus(six.ensure_str(v))
            
            item = Item(**argumentos)
            logger("Llamada externa (legacy): %s" %argumentos)

        if item.action == 'play':
            run(item)
        elif item.action == 'install_acestream':
            if system_platform in ['linux', 'windows']:
                install_acestream()
        else:
            run(item)

    else:
        item = Item(action='mainmenu')
        run(item)
