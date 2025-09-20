# -*- coding: utf-8 -*-

# edit 2024-12-10 kasi

import sys, xbmc, json, requests, urllib3, resolveurl, base64
from resources.lib import utils
from xbmcgui import ListItem, Dialog

urllib3.disable_warnings()
session = requests.Session()
BASEURL = "https://vavoo.to/ccapi/"

def _index(params):
	from resources.lib.vjlive import favchannels, channels, a_z_tv, group_tv
	utils.set_content("files")
	try: lines = json.loads(utils.addon.getSetting("favs"))
	except: lines = []
	if len(lines)>0: addDir2("Live - Favorites", "DefaultAddonPVRClient", "favchannels")
	addDir2("Live - All", "DefaultAddonPVRClient", "channels")
	addDir2("Live - A to Z", "DefaultAddonPVRClient", "a_z_tv")
	addDir2("Live - Groups", "DefaultAddonPVRClient", "group_tv")
	addDir2("Live - Romania", "DefaultAddonPVRClient", "channels", type="vavoo", group="Romania")
	utils.end(cacheToDisc=False)

def addDir(name, params, iconimage="DefaultFolder.png", isFolder=True, context=[]):
	liz = ListItem(name)
	liz.setArt({"icon":iconimage, "thumb":iconimage})
	plot = " "
	if not context: context.append(("Settings", "RunPlugin(%s?action=settings)" % sys.argv[0]))
	if name == "TV Favorites (Live)":
		plot = "[COLOR gold]List of own live favorites[/COLOR]"
		context.append(("Remove all favorites", "RunPlugin(%s?action=delallTvFavorit)" % sys.argv[0]))
	liz.addContextMenuItems(context)
	infoLabels={"title": name, "plot": plot}
	liz.setInfo("Video", infoLabels)
	utils.add(params, liz, isFolder)

def addDir2(name_, icon_, action, context = [], isFolder=True, **params):
	params["action"] = action
	iconimage = utils.getIcon(icon_) if utils.getIcon(icon_) else icon_
	addDir(name_, params, iconimage, isFolder, context)
