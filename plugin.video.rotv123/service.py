import sys
import os
import time
import socket
import xbmc
import xbmcgui
import xbmcvfs
import xbmcaddon
import socketserver
import urllib.request
import urllib.parse
import urllib.error
from http.server import BaseHTTPRequestHandler

# Setari Avansate
DEFAULT_PORT = 12345
MAX_RETRIES = 3
CHUNK_SIZE = 64 * 1024  # 64KB Buffer pentru eficienta CPU
TIMEOUT = 10

# Adaugam calea catre librarii
ADDON = xbmcaddon.Addon()
ADDON_DIR = xbmcvfs.translatePath(ADDON.getAddonInfo('path'))
sys.path.append(os.path.join(ADDON_DIR, 'resources', 'lib'))

import scraper

class AdvancedProxyHandler(BaseHTTPRequestHandler):
    protocol_version = 'HTTP/1.1' # Folosim HTTP 1.1 pentru Keep-Alive potential

    def log_message(self, format, *args):
        # Dezactivam log-urile standard de consola pentru viteza, logam doar erori critice in Kodi
        pass

    def do_HEAD(self):
        self.send_response(200)
        if '.ts' in self.path:
            self.send_header('Content-type', 'video/mp2t')
        else:
            self.send_header('Content-type', 'application/vnd.apple.mpegurl')
        self.send_header('Connection', 'close')
        self.end_headers()

    def do_GET(self):
        try:
            parsed_path = urllib.parse.urlparse(self.path)
            path = parsed_path.path
            query = dict(urllib.parse.parse_qsl(parsed_path.query))
            
            if path == '/play':
                self.handle_play_request(query)
            elif path == '/segment':
                self.handle_segment_request(query)
            else:
                self.send_error(404, "Invalid path")
        except Exception as e:
            xbmc.log(f"Rotv123 Proxy CRITICAL: {str(e)}", xbmc.LOGERROR)
            self.send_error(500)

    def resolve_redirects(self, url, headers):
        # Urmareste redirect-urile cu retry
        for attempt in range(MAX_RETRIES):
            try:
                req = urllib.request.Request(url, method='HEAD')
                for k, v in headers.items():
                    req.add_header(k, v)
                response = urllib.request.urlopen(req, timeout=5)
                return response.geturl()
            except Exception:
                time.sleep(0.5)
        return url

    def get_content_type(self, url, headers):
        try:
            req = urllib.request.Request(url, method='HEAD')
            for k, v in headers.items():
                req.add_header(k, v)
            response = urllib.request.urlopen(req, timeout=5)
            return response.headers.get('Content-Type', '').lower()
        except:
            return ''

    def handle_play_request(self, query):
        target_page_url = query.get('url')
        stream_label = query.get('label')
        
        if not target_page_url:
            self.send_error(400, "Missing url")
            return

        initial_stream_url, headers = scraper.get_stream_url(target_page_url, preferred_label_raw=stream_label)
        
        if not initial_stream_url:
            self.send_error(404, "Stream not found")
            return

        final_url = self.resolve_redirects(initial_stream_url, headers)
        xbmc.log(f"Rotv123 Proxy: Playing {target_page_url} -> {final_url}", xbmc.LOGINFO)

        # Determina tipul continutului
        ctype = self.get_content_type(final_url, headers)
        if '.m3u8' in final_url or 'mpegurl' in ctype:
            self.download_and_rewrite_m3u8(final_url, headers)
        else:
            # Redirect pentru MP4
            self.send_response(302)
            self.send_header('Location', final_url)
            self.end_headers()

    def handle_segment_request(self, query):
        target_url = query.get('url')
        if not target_url: return self.send_error(400)
        
        headers = {
            'User-Agent': scraper.USER_AGENT,
            'Referer': scraper.BASE_URL + '/',
            'Origin': scraper.BASE_URL
        }

        # Verifica daca e playlist (pentru HLS adaptiv)
        is_playlist = False
        if '.m3u8' in target_url:
            is_playlist = True
        
        # Logica de Retry
        response = None
        for attempt in range(MAX_RETRIES):
            try:
                req = urllib.request.Request(target_url)
                for k, v in headers.items(): req.add_header(k, v)
                response = urllib.request.urlopen(req, timeout=TIMEOUT)
                break # Success
            except Exception as e:
                if attempt == MAX_RETRIES - 1:
                    xbmc.log(f"Rotv123 Proxy: Failed to fetch {target_url} after retries. Error: {e}", xbmc.LOGERROR)
                    self.send_error(502, "Upstream Error")
                    return
                time.sleep(0.2)

        # Procesare raspuns
        try:
            ctype = response.headers.get('Content-Type', '').lower()
            if is_playlist or 'mpegurl' in ctype:
                content = response.read().decode('utf-8', errors='ignore')
                self.rewrite_m3u8_content(target_url, content)
            else:
                self.send_response(200)
                self.send_header('Content-Type', ctype)
                self.end_headers()
                # Streaming eficient
                while True:
                    chunk = response.read(CHUNK_SIZE)
                    if not chunk: break
                    self.wfile.write(chunk)
        except Exception as e:
            # Clientul s-a deconectat probabil
            pass

    def download_and_rewrite_m3u8(self, url, headers):
        try:
            req = urllib.request.Request(url)
            for k, v in headers.items(): req.add_header(k, v)
            response = urllib.request.urlopen(req, timeout=TIMEOUT)
            content = response.read().decode('utf-8', errors='ignore')
            self.rewrite_m3u8_content(url, content)
        except Exception as e:
            self.send_error(500, str(e))

    def rewrite_m3u8_content(self, original_url, content):
        base_url = original_url.rsplit('/', 1)[0] + '/'
        port = self.server.server_address[1] # Portul curent al serverului
        
        new_lines = []
        for line in content.splitlines():
            line = line.strip()
            if not line or line.startswith('#'):
                new_lines.append(line)
                continue
            
            # Calculam URL absolut
            if not line.startswith('http'):
                abs_url = urllib.parse.urljoin(base_url, line)
            else:
                abs_url = line
                
            # Rescriem prin proxy
            new_url = f"http://127.0.0.1:{port}/segment?url={urllib.parse.quote(abs_url)}"
            new_lines.append(new_url)
            
        self.send_response(200)
        self.send_header('Content-Type', 'application/vnd.apple.mpegurl')
        self.send_header('Connection', 'close') # Important pentru performanta
        self.end_headers()
        self.wfile.write('\n'.join(new_lines).encode('utf-8'))

class ThreadedHTTPServer(socketserver.ThreadingMixIn, socketserver.TCPServer):
    allow_reuse_address = True
    daemon_threads = True

def get_free_port():
    # Incearca portul default, apoi un port random
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.bind(('127.0.0.1', DEFAULT_PORT))
        s.close()
        return DEFAULT_PORT
    except OSError:
        # Portul 12345 e ocupat, cere unul random sistemului
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.bind(('127.0.0.1', 0))
        port = s.getsockname()[1]
        s.close()
        return port

def start_server():
    port = get_free_port()
    
    # SALVAM PORTUL IN MEMORIA KODI
    # Astfel default.py stie mereu unde ruleaza serverul, chiar daca portul se schimba
    window = xbmcgui.Window(10000) # WindowID 10000 este "Home", mereu disponibil
    window.setProperty('rotv123.proxy_port', str(port))
    
    try:
        server = ThreadedHTTPServer(('127.0.0.1', port), AdvancedProxyHandler)
        xbmc.log(f"Rotv123 Proxy: Started efficiently on port {port}", xbmc.LOGINFO)
        server.serve_forever()
    except Exception as e:
        xbmc.log(f"Rotv123 Proxy: Failed to start - {str(e)}", xbmc.LOGERROR)

if __name__ == '__main__':
    start_server()
