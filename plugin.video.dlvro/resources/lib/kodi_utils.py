
import sys
import urllib.parse
import json
import xbmcgui
import xbmcplugin
import routing

from .modules.common import ownAddon

# --- Inițializare ---
# Folosim același obiect 'plugin' din main.py pentru a construi URL-uri corecte
# Este important ca 'main.py' să-l fi creat deja.
# O alternativă ar fi să-l pasăm ca argument, dar aceasta e mai simplă pentru structura Kodi.
try:
    from .main import plugin
except ImportError:
    # Fallback în caz că modulul e importat într-un context neașteptat
    plugin = routing.Plugin()

ADDON_ICON = ownAddon.getAddonInfo('icon')
ADDON_FANART = ownAddon.getAddonInfo('fanart')
ADDON_HANDLE = int(sys.argv[1])

# --- Funcții de Procesare Item ---

def prepare_list_item(item: dict) -> dict:
    """
    Procesează un item (dict) și adaugă informațiile necesare pentru Kodi.
    Combină logica din 'default_process_item.py' și 'get_meta.py'.
    """
    # 1. Setează URL-ul final bazat pe tipul item-ului
    item_type = item.get("type")
    link = item.get("link", "")
    is_dir = False

    if item_type == "dir":
        # Pentru directoare, link-ul este o rută internă
        final_link = link  # 'link' este deja formatat corect în provider
        is_dir = True
    elif item_type == "item":
        # Pentru item-uri redabile, creăm un URL către acțiunea 'play'
        # și serializăm toate datele item-ului în URL.
        video_data = urllib.parse.quote_plus(json.dumps(item))
        final_link = f"/play/{video_data}"
    else:
        final_link = ""

    item["final_link"] = final_link
    item["is_dir"] = is_dir

    # 2. Creează obiectul xbmcgui.ListItem
    title = item.get("title", "")
    thumbnail = item.get("thumbnail", ADDON_ICON)
    fanart = item.get("fanart", ADDON_FANART)
    summary = item.get("summary", title)

    list_item = xbmcgui.ListItem(title)
    list_item.setArt({"icon": thumbnail, "poster": thumbnail, "thumb": thumbnail, "fanart": fanart})
    list_item.setInfo("video", {"plot": summary, "plotoutline": summary, "title": title})
    
    # Pentru item-urile redabile, setăm proprietatea 'IsPlayable' la 'true'.
    # Acest lucru îi spune lui Kodi că un click direct ar trebui să inițieze redarea.
    if item_type == "item":
        list_item.setProperty('IsPlayable', 'true')

    item["list_item"] = list_item
    return item

# --- Funcții de Afișare ---

def display_list(processed_list: list):
    """
    Afișează o listă de item-uri procesate în interfața Kodi.
    """
    for item in processed_list:
        if "list_item" in item and "final_link" in item:
            xbmcplugin.addDirectoryItem(
                handle=ADDON_HANDLE,
                url=plugin.url_for_path(item["final_link"]),
                listitem=item["list_item"],
                isFolder=item["is_dir"]
            )
    
    xbmcplugin.endOfDirectory(ADDON_HANDLE)

def show_ok_dialog(message: str, title: str = "Info"):
    """Afișează un dialog 'OK' simplu."""
    xbmcgui.Dialog().ok(title, message)

def show_select_dialog(options: list, title: str = "Selectați o opțiune") -> int:
    """
    Afișează un dialog de selecție și returnează index-ul opțiunii alese.
    'options' ar trebui să fie o listă de string-uri.
    Returnează -1 dacă utilizatorul anulează.
    """
    return xbmcgui.Dialog().select(title, options)
