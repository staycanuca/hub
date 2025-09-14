# used accross all addon
import xbmc
import xbmcgui
import xbmcaddon

ownAddon = xbmcaddon.Addon()
addon_id = ownAddon.getAddonInfo('id')
debugMode = ownAddon.getSetting('debug') or 'false' 
PATH = xbmcaddon.Addon().getAddonInfo("path")
text_view = xbmcgui.Dialog().textviewer

def get_setting(setting_id: str) -> str:
    """
    Obține valoarea unei setări din settings.xml.
    """
    return ownAddon.getSetting(setting_id)
 
def do_log(info):
    if debugMode. lower() == 'true' :
        xbmc.log(f' > MicroJen Log > \n {info}', xbmc.LOGINFO)