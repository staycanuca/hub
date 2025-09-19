import sys
import os
from urllib.parse import urljoin
import xbmcaddon
import xbmcplugin
import xbmcgui
import xbmcvfs


base_url = 'https://daddylivestream.com'
base_url2 = 'https://dlhd.dad'
user_agent = 'Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Mobile Safari/537.36'
headers = {
    "User-Agent": user_agent,
    "Referer": f'{base_url}/',
    "Origin": f'{base_url}/'
}

try:
    handle = int(sys.argv[1])
except IndexError:
    handle = 0
addon = xbmcaddon.Addon()
profile_path = xbmcvfs.translatePath(addon.getAddonInfo('profile'))
addon_name = addon.getAddonInfo('name')
addon_icon = addon.getAddonInfo('icon')
addon_fanart = addon.getAddonInfo('fanart')
get_setting = addon.getSetting
get_setting_bool = addon.getSettingBool
end_directory = xbmcplugin.endOfDirectory

schedule_url = urljoin(base_url, '/schedule/schedule-generated.php')
channels_url = f'{base_url}/24-7-channels.php'
schedule_path = os.path.join(profile_path, 'schedule.json')
cat_schedule_path = os.path.join(profile_path, 'cat_schedule.json')
set_content = xbmcplugin.setContent
set_category = xbmcplugin.setPluginCategory
set_resolved_url = xbmcplugin.setResolvedUrl
list_item = xbmcgui.ListItem
system_exit = sys.exit
