# -*- coding: utf-8 -*-
import xbmcgui, xbmcaddon, sys, xbmc, os, time, json, xbmcplugin, requests
PY2 = sys.version_info[0] == 2
if PY2:
	from urlparse import urlparse, parse_qsl, urlsplit
	from urllib import urlencode, quote_plus, quote
else:
	from urllib.parse import urlencode, urlparse, parse_qsl, quote_plus, urlsplit, quote
	import xbmcvfs

def translatePath(*args):
	if PY2: return xbmc.translatePath(*args).decode("utf-8")
	else: return xbmcvfs.translatePath(*args)

def exists(*args):
	return os.path.exists(translatePath(*args))

addon = xbmcaddon.Addon()
addonInfo = addon.getAddonInfo
addonID = addonInfo('id')
addonprofile = translatePath(addonInfo('profile'))
addonpath = translatePath(addonInfo('path'))
cachepath = os.path.join(addonprofile, "cache")
if not exists(cachepath): os.makedirs(cachepath)
	
home = xbmcgui.Window(10000)

def clear(auto=False):
	for a in os.listdir(cachepath):
		file = os.path.join(cachepath, a)
		if os.path.isfile(file):
			key = a.replace(".json", "")
			if auto:
				with open(file) as k: r = json.load(k)
				sigValidUntil = r.get('sigValidUntil', 0)
				if sigValidUntil != False and sigValidUntil < int(time.time()):
					os.remove(file)
					home.clearProperty(key)
			else: 
				os.remove(file)
				home.clearProperty(key)
		
clear(auto=True)

def getAuthSignature():
	_headers={"user-agent": "okhttp/4.11.0", "accept": "application/json", "content-type": "application/json; charset=utf-8", "content-length": "1106", "accept-encoding": "gzip"}
	_data = {"token":"tosFwQCJMS8qrW_AjLoHPQ41646J5dRNha6ZWHnijoYQQQoADQoXYSo7ki7O5-CsgN4CH0uRk6EEoJ0728ar9scCRQW3ZkbfrPfeCXW2VgopSW2FWDqPOoVYIuVPAOnXCZ5g","reason":"app-blur","locale":"de","theme":"dark","metadata":{"device":{"type":"Handset","brand":"google","model":"Nexus","name":"21081111RG","uniqueId":"d10e5d99ab665233"},"os":{"name":"android","version":"7.1.2","abis":["arm64-v8a","armeabi-v7a","armeabi"],"host":"android"},"app":{"platform":"android","version":"3.1.20","buildId":"289515000","engine":"hbc85","signatures":["6e8a975e3cbf07d5de823a760d4c2547f86c1403105020adee5de67ac510999e"],"installer":"app.revanced.manager.flutter"},"version":{"package":"tv.vavoo.app","binary":"3.1.20","js":"3.1.20"}},"appFocusTime":0,"playerActive":False,"playDuration":0,"devMode":False,"hasAddon":True,"castConnected":False,"package":"tv.vavoo.app","version":"3.1.20","process":"app","firstAppStart":1743962904623,"lastAppStart":1743962904623,"ipLocation":"","adblockEnabled":True,"proxy":{"supported":["ss","openvpn"],"engine":"ss","ssVersion":1,"enabled":True,"autoServer":True,"id":"pl-waw"},"iap":{"supported":False}}
	req = requests.post('https://www.vavoo.tv/api/app/ping', json=_data, headers=_headers).json()
	return req.get("addonSig")

def gettsSignature():
	vec = {"vec": "9frjpxPjxSNilxJPCJ0XGYs6scej3dW/h/VWlnKUiLSG8IP7mfyDU7NirOlld+VtCKGj03XjetfliDMhIev7wcARo+YTU8KPFuVQP9E2DVXzY2BFo1NhE6qEmPfNDnm74eyl/7iFJ0EETm6XbYyz8IKBkAqPN/Spp3PZ2ulKg3QBSDxcVN4R5zRn7OsgLJ2CNTuWkd/h451lDCp+TtTuvnAEhcQckdsydFhTZCK5IiWrrTIC/d4qDXEd+GtOP4hPdoIuCaNzYfX3lLCwFENC6RZoTBYLrcKVVgbqyQZ7DnLqfLqvf3z0FVUWx9H21liGFpByzdnoxyFkue3NzrFtkRL37xkx9ITucepSYKzUVEfyBh+/3mtzKY26VIRkJFkpf8KVcCRNrTRQn47Wuq4gC7sSwT7eHCAydKSACcUMMdpPSvbvfOmIqeBNA83osX8FPFYUMZsjvYNEE3arbFiGsQlggBKgg1V3oN+5ni3Vjc5InHg/xv476LHDFnNdAJx448ph3DoAiJjr2g4ZTNynfSxdzA68qSuJY8UjyzgDjG0RIMv2h7DlQNjkAXv4k1BrPpfOiOqH67yIarNmkPIwrIV+W9TTV/yRyE1LEgOr4DK8uW2AUtHOPA2gn6P5sgFyi68w55MZBPepddfYTQ+E1N6R/hWnMYPt/i0xSUeMPekX47iucfpFBEv9Uh9zdGiEB+0P3LVMP+q+pbBU4o1NkKyY1V8wH1Wilr0a+q87kEnQ1LWYMMBhaP9yFseGSbYwdeLsX9uR1uPaN+u4woO2g8sw9Y5ze5XMgOVpFCZaut02I5k0U4WPyN5adQjG8sAzxsI3KsV04DEVymj224iqg2Lzz53Xz9yEy+7/85ILQpJ6llCyqpHLFyHq/kJxYPhDUF755WaHJEaFRPxUqbparNX+mCE9Xzy7Q/KTgAPiRS41FHXXv+7XSPp4cy9jli0BVnYf13Xsp28OGs/D8Nl3NgEn3/eUcMN80JRdsOrV62fnBVMBNf36+LbISdvsFAFr0xyuPGmlIETcFyxJkrGZnhHAxwzsvZ+Uwf8lffBfZFPRrNv+tgeeLpatVcHLHZGeTgWWml6tIHwWUqv2TVJeMkAEL5PPS4Gtbscau5HM+FEjtGS+KClfX1CNKvgYJl7mLDEf5ZYQv5kHaoQ6RcPaR6vUNn02zpq5/X3EPIgUKF0r/0ctmoT84B2J1BKfCbctdFY9br7JSJ6DvUxyde68jB+Il6qNcQwTFj4cNErk4x719Y42NoAnnQYC2/qfL/gAhJl8TKMvBt3Bno+va8ve8E0z8yEuMLUqe8OXLce6nCa+L5LYK1aBdb60BYbMeWk1qmG6Nk9OnYLhzDyrd9iHDd7X95OM6X5wiMVZRn5ebw4askTTc50xmrg4eic2U1w1JpSEjdH/u/hXrWKSMWAxaj34uQnMuWxPZEXoVxzGyuUbroXRfkhzpqmqqqOcypjsWPdq5BOUGL/Riwjm6yMI0x9kbO8+VoQ6RYfjAbxNriZ1cQ+AW1fqEgnRWXmjt4Z1M0ygUBi8w71bDML1YG6UHeC2cJ2CCCxSrfycKQhpSdI1QIuwd2eyIpd4LgwrMiY3xNWreAF+qobNxvE7ypKTISNrz0iYIhU0aKNlcGwYd0FXIRfKVBzSBe4MRK2pGLDNO6ytoHxvJweZ8h1XG8RWc4aB5gTnB7Tjiqym4b64lRdj1DPHJnzD4aqRixpXhzYzWVDN2kONCR5i2quYbnVFN4sSfLiKeOwKX4JdmzpYixNZXjLkG14seS6KR0Wl8Itp5IMIWFpnNokjRH76RYRZAcx0jP0V5/GfNNTi5QsEU98en0SiXHQGXnROiHpRUDXTl8FmJORjwXc0AjrEMuQ2FDJDmAIlKUSLhjbIiKw3iaqp5TVyXuz0ZMYBhnqhcwqULqtFSuIKpaW8FgF8QJfP2frADf4kKZG1bQ99MrRrb2A="}
	url = 'https://www.vavoo.tv/api/box/ping2'
	req = requests.post(url, data=vec).json()
	return req['response'].get('signed')

def selectDialog(list, heading=None, multiselect = False, preselect=[]):
	if heading == 'default' or heading is None: heading = addonInfo('name')
	if multiselect: return xbmcgui.Dialog().multiselect(str(heading), list, preselect=preselect)
	return xbmcgui.Dialog().select(str(heading), list)

def set_cache(key, value, timeout=False):
	path = convertPluginParams(key)
	data={"sigValidUntil": False if timeout == False else int(time.time()) +timeout,"value": value}
	home.setProperty(path, json.dumps(data))
	file = os.path.join(cachepath, f"{path}.json")
	k = open(file, "w") if PY2 else xbmcvfs.File(file, "w")
	json.dump(data, k, indent=4)
	k.close()
	
def get_cache(key):
	path = convertPluginParams(key)
	keyfile = home.getProperty(path)
	if keyfile:
		r = json.loads(keyfile)
		sigValidUntil = r.get('sigValidUntil', 0)
		if sigValidUntil == False or sigValidUntil > int(time.time()):
			log(f"{key} from cache")
			try: ret =  json.loads(r.get('value'))
			except: ret = r.get('value')
			return ret
		home.clearProperty(path)
	try:
		file = os.path.join(cachepath, f"{path}.json" )
		with open(file) as k: r = json.load(k)
		sigValidUntil = r.get('sigValidUntil', 0) 
		if sigValidUntil == False or sigValidUntil > int(time.time()):
			value = r.get('value')
			data={"sigValidUntil": sigValidUntil,"value": value}
			home.setProperty(path, json.dumps(data))
			log(f"{key} from cache")
			try: ret =  json.loads(value)
			except: ret = value
			return ret
		os.remove(file)
	except: return

def log(msg, header=""):
	try: msg = json.dumps(msg, indent=4)
	except: pass
	#msg += " ".join(repr(args))
	if header: header+="\n"
	out = "\n####VAVOOTO####\n%s%s\n########" % (header, msg)
	mode = xbmc.LOGDEBUG
	if addon.getSetting("debug") == "true":
		mode = xbmc.LOGNOTICE if PY2 else xbmc.LOGINFO
	xbmc.log(out, mode)

def ok(heading, line1, line2='', line3=''):
	if PY2: return xbmcgui.Dialog().ok(heading, line1,line2,line3)
	else: return xbmcgui.Dialog().ok(heading, line1+"\n"+line2+"\n"+line3)

def getIcon(name):
	if exists("%s/resources/art/%s.png" % (addonpath ,name)):return "%s/resources/art/%s.png" % (addonpath ,name)
	elif exists("special://skin/extras/videogenre/%s.png" % name): return translatePath("special://skin/extras/videogenre/%s.png" % name)
	else: return  "%s.png" % name

def end(succeeded=True, cacheToDisc=True):
	return xbmcplugin.endOfDirectory(int(sys.argv[1]), succeeded=succeeded, cacheToDisc=cacheToDisc)
	
def add(params, o, isFolder=False):
	return xbmcplugin.addDirectoryItem(int(sys.argv[1]), url_for(params), o, isFolder)

def set_content(cont):
	xbmcplugin.setContent(int(sys.argv[1]), cont)
	
def set_resolved(item):
	xbmcplugin.setResolvedUrl(int(sys.argv[1]), True, item)

def sort_method():
	xbmcplugin.addSortMethod(int(sys.argv[1]), xbmcplugin.SORT_METHOD_VIDEO_TITLE)

def convertPluginParams(params):
	if isinstance(params, dict):
		p = []
		for key, value in list(params.items()):
			if isinstance(value, int):
				value = str(value)
			if PY2 and isinstance(value, unicode):
				value = value.encode("utf-8")
			p.append(urlencode({key: value}))
		params = '&'.join(p)
	return params

def url_for(params):
	return "%s?%s" % (sys.argv[0], convertPluginParams(params))