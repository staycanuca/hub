# -*- coding: utf-8 -*-
import sys, re, requests, xbmcaddon, xbmcgui, xbmc, json, os
from resources.lib import utils
from urllib.parse import quote

try: 
    from infotagger.listitem import ListItemInfoTag
    tagger = True
except: tagger = False

tokencache = os.path.join(utils.cachepath, "token.json")
addon = xbmcaddon.Addon()

def resolve_link(link):
    if addon.getSetting("streammode") == "1":
        _headers={"user-agent": "MediaHubMX/2", "accept": "application/json", "content-type": "application/json; charset=utf-8", "content-length": "115", "accept-encoding": "gzip", "mediahubmx-signature":utils.getAuthSignature()}
        _data={"language":"de","region":"AT","url":link,"clientVersion":"3.0.2"}
        url = "https://vavoo.to/mediahubmx-resolve.json"
        return requests.post(url, json=_data, headers=_headers).json()[0]["url"], None
    else: return "%s.ts?n=1&b=5&vavoo_auth=%s" % (link.replace("vavoo-iptv", "live2")[0:-12], utils.gettsSignature()), "User-Agent=VAVOO/2.6"

# --- Revised filterout function ---
_FILTER_REPLACEMENTS_PRE = [
    ("EINS", "1"), ("ZWEI", "2"), ("DREI", "3"), ("SIEBEN", "7"),
    ("TNT", "WARNER"), ("III", "3"), ("II", "2"), ("BR TV", "BR"),
    ("ʜᴅ", "HD")
]

_FILTER_CONDITIONAL_RULES = [
    (["ALLGAU"], "ALLGAU TV"), (["1", "2", "3"], "1-2-3 TV"),
    (["HR", "FERNSEHEN"], "HR"), (["EURONEWS"], "EURONEWS"),
    (["NICK", "TOONS"], "NICKTOONS"), (["NICK", "J"], "NICK JUNIOR"),
    (["NICKEL"], "NICKELODEON"), (["ORF", "SPORT"], "ORF SPORT"),
    (["ORF", "3"], "ORF 3"), (["ORF", "2"], "ORF 2"),
    (["ORF", "1"], "ORF 1"), (["ORF", "I"], "ORF 1"),
    (["BLACK", "AXN"], "AXN BLACK"), (["WHITE", "AXN"], "AXN WHITE"),
    (["AXN"], "AXN WHITE", ["BLACK"]), # AXN White, es sei denn AXN Black passt spezifischer
    (["SONY"], "AXN BLACK"), (["ANIX"], "ANIXE"),
    (["HEIMA"], "HEIMATKANAL"), (["SIXX"], "SIXX"), (["SWR"], "SWR"),
    (["ALPHA", "ARD"], "ARD-ALPHA"), (["ERST", "DAS"], "ARD"),
    (["ARTE"], "ARTE"), (["MTV"], "MTV"), (["PHOENIX"], "PHOENIX"),
    (["KIKA"], "KIKA"), (["CENTRAL"], "COMEDY CENTRAL"), (["VIVA"], "COMEDY CENTRAL"),
    (["BR", "FERNSEHEN"], "BR"), (["DMAX"], "DMAX"),
    (["DISNEY", "CHANNEL"], "DISNEY CHANNEL"), (["DISNEY", "J"], "DISNEY JUNIOR"),
    (["MDR", "TH"], "MDR THUERINGEN"), (["MDR", "ANHALT"], "MDR SACHSEN ANHALT"),
    (["MDR", "SACHSEN"], "MDR SACHSEN"), (["MDR"], "MDR"),
    (["NDR"], "NDR"), (["RBB"], "RBB"), (["JUKEBOX"], "JUKEBOX"),
    (["SERVUS"], "SERVUS TV"), (["NITRO"], "RTL NITRO"),
    (["RTL", "CRI"], "RTL CRIME"), (["RTL", "SUPER"], "SUPER RTL"),
    (["RTL", "UP"], "RTL UP"), (["RTL", "PLUS"], "RTL UP"),
    (["RTL", "PASSION"], "RTL PASSION"), (["RTL", "LIVING"], "RTL LIVING"),
    (["RTL", "2"], "RTL 2"), (["RTL", "SPORT"], None), 
    (["UNIVERSAL"], "UNIVERSAL TV"), (["WDR"], "WDR"),
    (["ZDF", "INFO"], "ZDF INFO"), (["ZDF", "NEO"], "ZDF NEO"), (["ZDF"], "ZDF"),
    (["ANIMAL", "PLANET"], "ANIMAL PLANET"), (["PLANET"], "PLANET"),
    (["SYFY"], "SYFY"), (["SILVER"], "SILVERLINE"),
    (["E!"], "E! ENTERTAINMENT"), (["ENTERTAINMENT"], "E! ENTERTAINMENT", ["E!"]),
    (["STREET"], "13TH STREET"), (["FOXI"], "FIX & FOXI"),
    (["TELE", "5"], "TELE 5"),
    (["KABE", "CLA"], "KABEL 1 CLASSICS"), (["KABE", "DO"], "KABEL 1 DOKU"),
    (["KABE"], "KABEL 1"),
    (["PRO", "FUN"], "PRO 7 FUN"), (["PRO", "MAXX"], "PRO 7 MAXX"), (["PRO"], "PRO 7"),
    (["ZEE"], "ZEE ONE"), (["DELUX"], "DELUXE MUSIC"), (["DISCO"], "DISCOVERY"),
    (["TLC"], "TLC"), (["N-TV"], "NTV"), (["NTV"], "NTV"),
    (["TAGESSCHAU"], "TAGESSCHAU 24"),
    (["CURIOSITY", "CHANNEL"], "CURIOSITY CHANNEL"), (["CURIOSITY"], "CURIOSITY CHANNEL"),
    (["EUROSPORT", "1"], "EUROSPORT 1"), (["EUROSPORT", "2"], "EUROSPORT 2"),
    (["SPIEGEL", "GESCHICHTE"], "SPIEGEL GESCHICHTE"),
    (["SPIEGEL"], "CURIOSITY CHANNEL", ["GESCHICHTE"]), 
    (["HISTORY"], "HISTORY"), (["VISION"], "MOTORVISION"),
    (["INVESTIGATION"], "CRIME + INVESTIGATION"), (["A&"], "CRIME + INVESTIGATION"),
    (["AUTO"], "AUTO MOTOR SPORT"),
    (["KINO", "WELT"], "KINOWELT"), (["WUNDER", "WELT"], "WELT DER WUNDER"), (["WELT"], "WELT"),
    (["NAT", "GEO", "WILD"], "NAT GEO WILD"), (["NAT", "GEO"], "NATIONAL GEOGRAPHIC"),
    (["3", "SAT"], "3 SAT"), (["ROMANCE"], "ROMANCE TV"),
    (["ATV", "2"], "ATV 2"), (["ATV"], "ATV"),
    (["WARNER", "SER"], "WARNER TV SERIE"), (["WARNER", "FILM"], "WARNER TV FILM"),
    (["WARNER", "COMEDY"], "WARNER TV COMEDY"), (["WARNER"], None), 
    (["VOX", "+"], "VOX UP"), (["VOX", "UP"], "VOX UP"), (["VOX"], "VOX"),
    (["SAT", "1", "GOLD"], "SAT 1 GOLD"), (["SAT", "1", "EMOT"], "SAT 1 EMOTIONS"),
    (["SAT", "1"], "SAT 1"),
    # SKY (komplex, Reihenfolge und Exklusivität wichtig)
    (["SKY", "NATURE"], "SKY NATURE", ["BUNDES", "SPORT", "SELECT", "BOX"]),
    (["SKY", "REPLAY"], "SKY REPLAY", ["BUNDES", "SPORT", "SELECT", "BOX"]),
    (["SKY", "ATLANTIC"], "SKY ATLANTIC", ["BUNDES", "SPORT", "SELECT", "BOX"]),
    (["SKY", "DO"], "SKY DOCUMENTARIES", ["BUNDES", "SPORT", "SELECT", "BOX", "COMEDY"]),
    (["SKY", "ACTION"], "SKY CINEMA ACTION", ["BUNDES", "SPORT", "SELECT", "BOX"]),
    (["SKY", "COMEDY"], "SKY COMEDY", ["BUNDES", "SPORT", "SELECT", "BOX", "WARNER"]), 
    (["SKY", "FAMI"], "SKY CINEMA FAMILY", ["BUNDES", "SPORT", "SELECT", "BOX"]),
    (["SKY", "KRIM"], "SKY KRIMI", ["BUNDES", "SPORT", "SELECT", "BOX"]),
    (["SKY", "CRI"], "SKY CRIME", ["BUNDES", "SPORT", "SELECT", "BOX", "RTL"]), 
    (["SKY", "CLASS"], "SKY CINEMA CLASSICS", ["BUNDES", "SPORT", "SELECT", "BOX"]),
    (["SKY", "NOSTALGIE"], "SKY CINEMA CLASSICS", ["BUNDES", "SPORT", "SELECT", "BOX"]),
    (["SKY", "HIGHLIGHT"], "SKY CINEMA HIGHLIGHTS", ["BUNDES", "SPORT", "SELECT", "BOX"]),
    (["SKY", "CASE"], "SKY SHOWCASE", ["BUNDES", "SPORT", "SELECT", "BOX"]),
    (["SKY", "PREMIE", "24"], "SKY CINEMA PREMIEREN +24", ["BUNDES", "SPORT", "SELECT", "BOX"]),
    (["SKY", "PREMIE"], "SKY CINEMA PREMIEREN", ["BUNDES", "SPORT", "SELECT", "BOX"]),
    (["SKY", "ONE"], "SKY ONE", ["BUNDES", "SPORT", "SELECT", "BOX", "CINEMA", "ZEE"]),
    (["SKY", "1"], "SKY ONE", ["BUNDES", "SPORT", "SELECT", "BOX", "CINEMA", "SAT"]),
    (["PULS", "24"], "PULS 24"), (["DO", "24"], "N24 DOKU"), (["PULS"], "PULS 4"),
    (["FOX"], "SKY REPLAY", ["FOXI"])
]

_FILTER_SUFFIXES_TO_REMOVE = [
    " RAW", " HEVC", " HD+", " FHD", " UHD", " QHD", " 4K", " 2K",
    " 1080P", " 1080", " 720P", " 720",
    " AUSTRIA", " GERMANY", " DEUTSCHLAND", " DE"
]
_FILTER_ENDSWITH_TO_REMOVE = [" HEVC", " RAW", " HD+", " FHD", " UHD", " QHD", " HD"]

def filterout(name: str) -> str:
    if not name: return ""
    original_name_for_reference = name # Für Debugging oder sehr komplexe Regeln
    name = name.upper().strip()
    name = name.replace("  ", " ")

    for find, replace in _FILTER_REPLACEMENTS_PRE:
        name = name.replace(find, replace).strip()
    name = name.replace("  ", " ")

    if addon.getSetting("filter") == "true":
        for keywords, new_name_candidate, *avoid_keywords_tuple in _FILTER_CONDITIONAL_RULES:
            avoid_keywords = avoid_keywords_tuple[0] if avoid_keywords_tuple else []
            if all(kw in name for kw in keywords):
                if not any(avoid_kw in name for avoid_kw in avoid_keywords):
                    if new_name_candidate is None: 
                        break 
                    name = new_name_candidate
                    break 
    
    name = re.sub(r" \.[A-Z]$", "", name)
    name = re.sub(r"\(.*\)", "", name)
    name = re.sub(r"\[.*\]", "", name).strip()

    for suffix in _FILTER_SUFFIXES_TO_REMOVE: 
        name = name.replace(suffix, "")
    for suffix in _FILTER_ENDSWITH_TO_REMOVE: 
        if name.endswith(suffix):
            name = name[:-len(suffix)]
    name = name.strip()
    name = re.sub(r"^[A-Z]{1,3}\s?[:|]\s+", "", name) 
    return name.strip()

def vavoo_groups():
    groups=[]
    for c in requests.get("https://www2.vavoo.to/live2/index?output=json").json():
        if c["group"] not in groups: groups.append(c["group"])
    return sorted(groups)
    
def choose():
    groups = vavoo_groups()
    oldgroups = utils.get_cache("groups")
    preselect = []
    if oldgroups:
        for oldgroup in oldgroups:
            preselect.append(groups.index(oldgroup))
    indicies = utils.selectDialog(groups, "Choose VAVOO Groups", True, preselect)
    group = []
    if indicies:
        for i in indicies: group.append(groups[i])
        addon.setSetting("groups", json.dumps(group))
        return group

def get_cache_or_setting(setting):
    a = utils.get_cache(setting)
    if not a : a = addon.getSetting(setting)
    utils.set_cache(setting, a)
    return a

def getchannels():
    return get_vav_channels()

def vav_channels():
    chans = utils.get_cache("vav_channels")
    if chans: return chans
    _headers={"user-agent": "okhttp/4.11.0", "accept": "application/json", "content-type": "application/json; charset=utf-8", "content-length": "1106", "accept-encoding": "gzip", "mediahubmx-signature": utils.getAuthSignature()}
    items = []
    for group in vavoo_groups():
        cursor = 0
        while True:
            _data={"language":"de","region":"AT","catalogId":"iptv","id":"iptv","adult":False,"search":"","sort":"name","filter":{"group":group},"cursor":cursor,"clientVersion":"3.0.2"}
            r = requests.post("https://vavoo.to/mediahubmx-catalog.json", json=_data, headers=_headers).json()
            cursor = r.get("nextCursor")
            items += r.get("items")
            if not cursor: break
    utils.set_cache("vav_channels", items, timeout = 60 * int(addon.getSetting("vav_cache")))
    return items

def get_vav_channels(groups=None):
    vavchannels = {}
    if not groups:
        try: groups = json.loads(addon.getSetting("groups"))
        except: groups = choose()
    for item in vav_channels():
        if item["group"] not in groups: continue
        name = filterout(item["name"])
        if name not in vavchannels: vavchannels[name] = []
        if item["url"] not in vavchannels[name]:
            vavchannels[name].append(item["url"])
    return vavchannels

def livePlay(name, type=None, group=None):
    if type == "vavoo": m = get_vav_channels([group])[name]
    else: m = getchannels()[name]
    i, title = 0, None
    if len(m) > 1:
        if addon.getSetting("auto") == "0":
            # Autoplay - rotieren bei la Stream Auswahl
            # ist wichtig wenn z.B. der erste gelistete Stream nicht funzt
            if addon.getSetting("idn") == name:
                i = int(addon.getSetting("num")) + 1
                if i == len(m): i = 0
            addon.setSetting("idn", name)
            addon.setSetting("num", str(i))
            title = "%s (%s/%s)" % (name, i + 1, len(m))  # wird verwendet für infoLabels
        elif addon.getSetting("auto") == "1":
            cap = []
            for i, n in enumerate(m, 1):
                cap.append("STREAM %s" %i)
            i = utils.selectDialog(cap)
            if i < 0: return
            title = "%s (%s/%s)" %(name, i+1, len(m))  # wird verwendet für infoLabels
        else:
            cap=[]
            for i, n in enumerate(m, 1): cap.append("STREAM %s" %i)
            i = utils.selectDialog(cap)
            if i < 0: return
            title = "%s (%s/%s)" % (name, i + 1, len(m))  # wird verwendet für infoLabels
    n = m[i]
    title = title if title else name
    infoLabels={"title": title, "plot": "[B]%s[/B] - Stream %s of %s" % (name, i+1, len(m))}
    o = xbmcgui.ListItem(name)
    url, headers = resolve_link(n)
    utils.log("Playing %s" % n)
    utils.log("Playing %s" % url)
    inputstream = None
    if "hls" in url or "m3u8" in url:
        #o.setMimeType("application/vnd.apple.mpegurl")
        if xbmc.getCondVisibility("System.HasAddon(inputstream.ffmpegdirect)") and addon.getSetting("hlsinputstream") == "0": inputstream = "inputstream.ffmpegdirect"
        else: inputstream = "inputstream.adaptive"
        if utils.PY2: o.setProperty("inputstreamaddon", inputstream)
        else: o.setProperty("inputstream", inputstream)
    else:
        #o.setMimeType("video/mp2t")
        if xbmc.getCondVisibility("System.HasAddon(inputstream.ffmpegdirect)"): 
            o.setProperty("inputstream", "inputstream.ffmpegdirect")
            inputstream = "inputstream.ffmpegdirect"
    if inputstream == "inputstream.ffmpegdirect":
        if addon.getSetting("openmode") != "0": o.setProperty("inputstream.ffmpegdirect.open_mode", "ffmpeg" if  addon.getSetting("openmode") == "1" else "curl")
    if headers:
        if inputstream == "inputstream.adaptive":
            o.setProperty(f'{inputstream}.common_headers', headers)
            o.setProperty(f'{inputstream}.stream_headers', headers)
        else: url+=f"|{headers}"
    o.setPath(url)
    o.setProperty("IsPlayable", "true")
    if tagger:
        info_tag = ListItemInfoTag(o, 'video')
        info_tag.set_info(infoLabels)
    else: o.setInfo("Video", infoLabels) # so kann man die Stream Auswahl auch sehen (Info)
    utils.set_resolved(o)
    utils.end()
            
def makem3u():
    m3u = ["#EXTM3U\n"]
    for name in getchannels():
        m3u.append('#EXTINF:-1 group-title="Standart",%s\nplugin://plugin.video.vavooto/?name=%s\n' % (name.strip(), name.replace("&", "%26").replace("+", "%2b").strip()))
    m3uPath = os.path.join(utils.addonprofile, "vavoo.m3u")
    with open(m3uPath ,"w") as a:
        a.writelines(m3u)
    dialog = xbmcgui.Dialog()
    ok = dialog.ok('VAVOO.TO', 'm3u created in %s' % m3uPath)
        
# edit kasi
def channels(items=None, type=None, group=None):
    try: lines = json.loads(addon.getSetting("favs"))
    except: lines=[]
    if items: results = json.loads(items)
    elif type == "vavoo": results = get_vav_channels([group])
    else: results = getchannels()
    for name in results:
        index = len(results[name])
        title = name if addon.getSetting("stream_count") == "false" or index == 1 else "%s  (%s)" % (name, index)
        o = xbmcgui.ListItem(name)
        cm = []
        if not name in lines:
            cm.append(("Add to TV Favorites", "RunPlugin(%s?action=addTvFavorit&name=%s)" % (sys.argv[0], name.replace("&", "%26").replace("+", "%2b"))))
            plot = ""
        else:
            plot = "[COLOR gold]TV Favorite[/COLOR]" #% name
            cm.append(("Remove from TV Favorites", "RunPlugin(%s?action=delTvFavorit&name=%s)" % (sys.argv[0], name.replace("&", "%26").replace("+", "%2b"))))
        cm.append(("Settings", "RunPlugin(%s?action=settings)" % sys.argv[0]))
        cm.append(("Create m3u", "RunPlugin(%s?action=makem3u)" % sys.argv[0]))
        o.addContextMenuItems(cm)
        o.setArt({'poster': 'DefaultTVShows.png', 'icon': 'DefaultTVShows.png'})
        infoLabels={"title": title, "plot": plot}
        if tagger:
            info_tag = ListItemInfoTag(o, 'video')
            info_tag.set_info(infoLabels)
        else: o.setInfo("Video", infoLabels)
        o.setProperty("IsPlayable", "true")
        param = {"name":name, "type": type, "group": group} if type else {"name":name}
        utils.add(param, o)
    utils.sort_method()
    utils.end()

def favchannels():
    try: lines = json.loads(addon.getSetting("favs"))
    except: return
    for name in getchannels():
        if not name in lines: continue
        o = xbmcgui.ListItem(name)
        cm = []
        cm.append(("Remove from TV Favorites", "RunPlugin(%s?action=delTvFavorit&name=%s)" % (sys.argv[0], name.replace("&", "%26").replace("+", "%2b"))))
        cm.append(("Settings", "RunPlugin(%s?action=settings)" % sys.argv[0]))
        o.addContextMenuItems(cm)
        infoLabels={"title": name, "plot": "[COLOR gold]List of own live favorites[/COLOR]"}
        if tagger:
            info_tag = ListItemInfoTag(o, 'video')
            info_tag.set_info(infoLabels)
        else: o.setInfo("Video", infoLabels)
        o.setProperty("IsPlayable", "true")
        utils.add({"name":name}, o)
    utils.sort_method()
    utils.end()

def change_favorit(name, delete=False):
    try: lines = json.loads(addon.getSetting("favs"))
    except: lines= []
    if delete: lines.remove(name)
    else: lines.append(name)
    addon.setSetting("favs", json.dumps(lines))
    if len(lines) == 0: xbmc.executebuiltin("Action(ParentDir)")
    else: xbmc.executebuiltin("Container.Refresh")

# edit by kasi
def live():
    from resources.lib.vjackson import addDir2
    try: lines = json.loads(addon.getSetting("favs"))
    except: lines = []
    if len(lines)>0: addDir2("Live - Favorites", "DefaultAddonPVRClient", "favchannels")
    addDir2("Live - All", "DefaultAddonPVRClient", "channels")
    addDir2("Live - A to Z", "DefaultAddonPVRClient", "a_z_tv")
    addDir2("Live - Groups", "DefaultAddonPVRClient", "group_tv")
    utils.end(cacheToDisc=False)

def group_tv(type=None):
    from resources.lib.vjackson import addDir2
    gruppen = vavoo_groups()
    for group in gruppen: 
        addDir2(group, "DefaultAddonPVRClient", "channels", type="vavoo", group=group)
    utils.end()

def a_z_tv():
    from resources.lib.vjackson import addDir2
    from collections import defaultdict
    results = getchannels()
    res = defaultdict(dict)
    for key, val in results.items():
        prefix, number = key[:1].upper() if key[:1].isalpha() else "#", key
        res[prefix][number] = val
    res = dict(sorted(res.items()))
    for key, val in res.items():
        addDir2(key, "DefaultAddonPVRClient", "channels", items=json.dumps(val))
    utils.end()