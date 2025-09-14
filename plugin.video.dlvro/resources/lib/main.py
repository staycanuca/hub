import json
from urllib.parse import unquote_plus
import routing
from . import ddlv_provider
from . import kodi_utils
from . import playback

plugin = routing.Plugin()

@plugin.route("/")
def root() -> None:
    """
    Ruta rădăcină a addon-ului. Afișează meniul principal.
    """
    # Adăugăm manual intrarea pentru Sport TV Romania
    romania_sports_item = {
        'type': 'dir',
        'title': 'Sport Tv Romania',
        'link': '/romania_sports' # Link către noua noastră rută
    }
    
    # Obține lista de categorii/evenimente de la provider
    initial_data = ddlv_provider.get_main_list()
    
    # Parsează și procesează item-urile pentru afișare
    jen_list = ddlv_provider.parse_main_list(initial_data)
    
    # Combinăm lista de la provider cu cea manuală, pentru a o pune la sfârșit
    full_list = jen_list + [romania_sports_item]
    
    # Adaugă metadate și pregătește item-urile pentru Kodi
    processed_list = [kodi_utils.prepare_list_item(item) for item in full_list]
    
    # Afișează lista în interfața Kodi
    kodi_utils.display_list(processed_list)


@plugin.route("/romania_sports")
def show_romania_sports() -> None:
    """
    Afișează o listă filtrată cu evenimente de pe canale românești.
    """
    # Obține lista filtrată de la provider
    jen_list = ddlv_provider.get_romanian_sports_events()
    
    if jen_list:
        # Procesează fiecare item
        processed_list = [kodi_utils.prepare_list_item(item) for item in jen_list]
        # Afișează lista
        kodi_utils.display_list(processed_list)
    else:
        # Afișează o listă goală dacă nu s-au găsit evenimente
        kodi_utils.display_list([])


@plugin.route("/list/<path:url>")
def get_list(url: str) -> None:
    """
    Afișează o listă de evenimente sau canale, în funcție de URL.
    """
    # Obține datele specifice (canale, evenimente, etc.)
    response_text = ddlv_provider.get_specific_list(url)
    
    if response_text:
        # Parsează lista
        jen_list = ddlv_provider.parse_specific_list(url, response_text)
        
        # Procesează fiecare item
        processed_list = [kodi_utils.prepare_list_item(item) for item in jen_list]
        
        # Afișează lista
        kodi_utils.display_list(processed_list)
    else:
        kodi_utils.display_list([])


@plugin.route("/play/<path:video_data>")
def play_video(video_data: str):
    """
    Redă videoclipul selectat.
    """
    item = json.loads(unquote_plus(video_data))
    if item:
        playback.play_video(item)


def main():
    """
    Funcția principală care pornește plugin-ul.
    """
    plugin.run()