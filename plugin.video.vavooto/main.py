# -*- coding: utf-8 -*-

# edit 2024-12-05 kasi

if __name__ == "__main__":
	import sys, xbmc, json
	from resources.lib import utils, vjackson, vjlive

	
	if not xbmc.getCondVisibility("System.HasAddon(inputstream.ffmpegdirect)"):
		xbmc.executebuiltin('InstallAddon(inputstream.ffmpegdirect)')
		xbmc.executebuiltin('SendClick(11)')
	params = dict(utils.parse_qsl(sys.argv[2][1:]))

	tv = params.get("name")
	action = params.pop("action", None)

	if tv:
		if action == "addTvFavorit": vjlive.change_favorit(tv)
		elif action == "delTvFavorit": vjlive.change_favorit(tv, True)
		else: vjlive.livePlay(tv, params.get('type'), params.get('group'))
	elif action == None: vjackson._index(params)
	elif action == "clear": utils.clear()
	elif action == "delallTvFavorit":
		utils.addon.setSetting("favs", "[]")
		xbmc.executebuiltin('Container.Refresh')
	elif action == 'a_z_tv': vjlive.a_z_tv()
	elif action == "group_tv": vjlive.group_tv(params.get('type'))
	elif action == "channels": vjlive.channels(params.get('items'), params.get('type'), params.get('group'))
	elif action == "settings": utils.addon.openSettings(sys.argv[1])
	elif action == "favchannels": vjlive.favchannels()
	elif action == "makem3u": vjlive.makem3u()
	elif action == "choose": vjlive.choose()
