import xbmc
import xbmcaddon
import xbmcgui
import xbmcvfs
import urllib.request
import zipfile
import os

# Get addon info
addon = xbmcaddon.Addon()
addon_id = addon.getAddonInfo('id')
addon_name = addon.getAddonInfo('name')

# Settings
zip_url = "https://subiectiv.com/indexer.zip"

try:
    profile_dir = xbmcvfs.translatePath(addon.getAddonInfo('profile'))
    download_path = os.path.join(profile_dir, "..", "..", "addon_data", "plugin.video.indexer")
    download_file = os.path.join(download_path, "indexer.zip")

    # Create directory if it doesn't exist
    if not xbmcvfs.exists(download_path):
        xbmcvfs.mkdirs(download_path)

    # Download the zip file
    xbmc.log(f"{addon_name}: Downloading {zip_url} to {download_file}", level=xbmc.LOGINFO)
    urllib.request.urlretrieve(zip_url, download_file)

    # Unzip the file
    xbmc.log(f"{addon_name}: Unzipping {download_file} to {download_path}", level=xbmc.LOGINFO)
    with zipfile.ZipFile(download_file, 'r') as zip_ref:
        zip_ref.extractall(download_path)

    # Clean up the downloaded zip file
    xbmcvfs.delete(download_file)

    # Notify user
    dialog = xbmcgui.Dialog()
    dialog.notification(addon_name, 'Indexer updated successfully!', xbmcgui.NOTIFICATION_INFO, 5000)
    xbmc.log(f"{addon_name}: Indexer updated successfully!", level=xbmc.LOGINFO)

except Exception as e:
    xbmc.log(f"{addon_name}: Error - {e}", level=xbmc.LOGERROR)
    dialog = xbmcgui.Dialog()
    dialog.notification(addon_name, f'Error: {e}', xbmcgui.NOTIFICATION_ERROR, 5000)
