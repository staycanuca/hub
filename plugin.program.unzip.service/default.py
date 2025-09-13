# Dummy default.py for plugin.program.unzip.service
import xbmcaddon

addon = xbmcaddon.Addon()
addon_id = addon.getAddonInfo('id')
addon_name = addon.getAddonInfo('name')

print(f"[{addon_name}] - Started")
