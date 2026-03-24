import urllib.request
import urllib.parse
import re

BASE_URL = 'https://rotv123.com'
USER_AGENT = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/115.0'

def get_data(url):
    if not url.startswith('http'):
        url = urllib.parse.urljoin(BASE_URL + '/', url)
    
    req = urllib.request.Request(url)
    req.add_header('User-Agent', USER_AGENT)
    req.add_header('Referer', BASE_URL + '/')
    
    try:
        response = urllib.request.urlopen(req, timeout=20)
        return response.read().decode('utf-8', errors='ignore')
    except Exception as e:
        # Poti adauga logging aici daca transmiti un logger
        return None

def get_all_streams(page_url):
    """
    Returneaza o lista de tupluri (label, stream_url, raw_label) gasite in pagina.
    Ex: [('Fhd', 'http...', 'fhd'), ('Hd', 'http...', 'hd')]
    """
    html = get_data(page_url)
    if not html:
        return []
        
    streams_match = re.search(r'const streams\s*=\s*\{([^}]+)\}', html, re.DOTALL)
    if streams_match:
        # Regex: (\w+)\s*:\s*[\'"]\s*([^'"\s,]+)
        # Group 1: Label (ex: fhd, hd), Group 2: URL
        url_matches = re.findall(r"(\w+)\s*:\s*[\'\"]\s*([^\'\"\s,]+)", streams_match.group(1))
        
        results = []
        for lbl, u in url_matches:
            clean_lbl = lbl.replace('_', ' ').capitalize()
            results.append((clean_lbl, u, lbl)) # pastram si label-ul original (raw) pentru matching
        return results
            
    return []

def get_stream_url(page_url, preferred_label_raw=None):
    """
    Extrage URL-ul de stream.
    Daca preferred_label_raw este specificat (ex: 'fhd'), incearca sa gaseasca acel stream specific.
    Altfel returneaza primul gasit.
    """
    streams = get_all_streams(page_url)
    if not streams:
        return None, None
        
    selected_url = ""
    
    if preferred_label_raw:
        # Cautam stream-ul care are label-ul raw identic
        for _, url, raw_lbl in streams:
            if raw_lbl == preferred_label_raw:
                selected_url = url
                break
    
    # Daca nu am gasit specific sau nu s-a cerut, luam primul
    if not selected_url and streams:
        selected_url = streams[0][1]

    if selected_url:
        headers = {
            'User-Agent': USER_AGENT,
            'Referer': BASE_URL + '/',
            'Origin': BASE_URL
        }
        return selected_url, headers
            
    return None, None