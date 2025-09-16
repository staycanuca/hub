import requests
import hashlib
import time
from collections import OrderedDict
from urllib.parse import quote, urlencode
import json
import logging

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

import re

class StalkerPortal:
    def __init__(self, portal_url, mac):
        self.portal_url = portal_url.rstrip("/")
        self.mac = mac.strip()
        self.session = requests.Session()
        self.token = None
        self.bearer_token = None
        self.stream_base_url = portal_url.rstrip('/')
        self.last_handshake = 0
        self.token_expiry = 3600  # 1 hour default

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.session.close()

    def ensure_valid_token(self):
        """Asigură că token-ul este valid, reface handshake-ul dacă e necesar"""
        current_time = time.time()
        
        if not self.token or (current_time - self.last_handshake) > (self.token_expiry - 300):
            logger.debug("Token expirat sau lipsește, refac handshake-ul")
            self.handshake()
            return
        
        # Testează token-ul curent cu o cerere simplă
        try:
            test_url = f"{self.portal_url}/portal.php?type=stb&action=get_profile&JsHttpRequest=1-xml"
            response = self.session.get(test_url, 
                                      headers=self.get_headers(), 
                                      cookies=self.get_cookies(), 
                                      timeout=5)
            if response.status_code != 200:
                logger.debug("Token invalid, refac handshake-ul")
                self.handshake()
        except:
            logger.debug("Eroare la testarea token-ului, refac handshake-ul")
            self.handshake()

    def get_headers(self):
        """Returnează header-urile standard"""
        headers = {
            'User-Agent': 'Mozilla/5.0 (QtEmbedded; U; Linux; C) AppleWebKit/533.3 (KHTML, like Gecko) MAG200 stbapp ver: 2 rev: 250 Safari/533.3'
        }
        if self.bearer_token:
            headers['Authorization'] = f'Bearer {self.bearer_token}'
        return headers

    def get_cookies(self):
        """Returnează cookie-urile standard"""
        cookies = {'mac': self.mac, 'stb_lang': 'en', 'timezone': 'Europe/Paris'}
        if self.token:
            cookies['token'] = self.token
        return cookies

    def handshake(self):
        url = f"{self.portal_url}/portal.php?type=stb&action=handshake&token=&JsHttpRequest=1-xml"
        headers = self.get_headers()
        cookies = {'mac': self.mac}

        try:
            response = self.session.get(url, headers=headers, cookies=cookies, timeout=10)
            response.raise_for_status()
            data = response.json()
            self.token = data.get('js', {}).get('token')
            self.bearer_token = self.token
            self.last_handshake = time.time()
            logger.debug(f"Handshake successful, token: {self.token}")
        except requests.exceptions.HTTPError as e:
            logger.error(f"Handshake failed with HTTPError: {e}")
            logger.error(f"Response body: {e.response.text}")
            raise ConnectionError("Failed to perform handshake. Check server response.")
        except requests.exceptions.RequestException as e:
            logger.error(f"Handshake failed: {e}")
            raise ConnectionError("Failed to perform handshake")

    def validate_stream_url(self, url):
        """Verifică dacă URL-ul stream este valid"""
        try:
            response = self.session.head(url, timeout=5)
            return response.status_code == 200
        except:
            return False

    def detect_portal_structure(self):
        """Detectează structura URL-urilor pentru acest portal"""
        test_patterns = [
            "/stalker_portal/c/",
            "/ch/",
            "/live/",
            "/stream/",
            "/tv/"
        ]
        
        for pattern in test_patterns:
            test_url = f"{self.portal_url}{pattern}test"
            try:
                response = self.session.head(test_url, timeout=3)
                if response.status_code != 404:
                    logger.debug(f"Detected portal structure: {pattern}")
                    return pattern
            except:
                continue
        
        return "/ch/"  # default

    def get_itv_categories(self):
        self.ensure_valid_token()
        
        url = f"{self.portal_url}/portal.php?type=itv&action=get_genres&JsHttpRequest=1-xml"
        headers = self.get_headers()
        cookies = self.get_cookies()

        try:
            response = self.session.get(url, headers=headers, cookies=cookies, timeout=10)
            response.raise_for_status()
            data = response.json()
            return data.get('js', [])
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to get ITV categories: {e}")
            return []

    def get_channels_in_category(self, category_id):
        self.ensure_valid_token()
        
        url = f"{self.portal_url}/portal.php?type=itv&action=get_ordered_list&genre={category_id}&JsHttpRequest=1-xml"
        headers = self.get_headers()
        cookies = self.get_cookies()

        try:
            response = self.session.get(url, headers=headers, cookies=cookies, timeout=10)
            response.raise_for_status()
            data = response.json()
            return data.get('js', {}).get('data', [])
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to get channels in category {category_id}: {e}")
            return []

    def get_vod_categories(self):
        self.ensure_valid_token()
        
        url = f"{self.portal_url}/portal.php?type=vod&action=get_categories&JsHttpRequest=1-xml"
        headers = self.get_headers()
        cookies = self.get_cookies()

        try:
            response = self.session.get(url, headers=headers, cookies=cookies, timeout=10)
            response.raise_for_status()
            data = response.json()
            return data.get('js', [])
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to get VOD categories: {e}")
            return []

    def get_vod_in_category(self, category_id):
        self.ensure_valid_token()
        
        url = f"{self.portal_url}/portal.php?type=vod&action=get_ordered_list&category={category_id}&JsHttpRequest=1-xml"
        headers = self.get_headers()
        cookies = self.get_cookies()

        try:
            response = self.session.get(url, headers=headers, cookies=cookies, timeout=10)
            response.raise_for_status()
            data = response.json()
            return data.get('js', {}).get('data', [])
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to get VOD in category {category_id}: {e}")
            return []

    def get_series_categories(self):
        self.ensure_valid_token()
        
        url = f"{self.portal_url}/portal.php?type=series&action=get_categories&JsHttpRequest=1-xml"
        headers = self.get_headers()
        cookies = self.get_cookies()

        try:
            response = self.session.get(url, headers=headers, cookies=cookies, timeout=10)
            response.raise_for_status()
            data = response.json()
            return data.get('js', [])
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to get Series categories: {e}")
            return []

    def get_series_in_category(self, category_id):
        self.ensure_valid_token()
        
        url = f"{self.portal_url}/portal.php?type=series&action=get_ordered_list&category={category_id}&JsHttpRequest=1-xml"
        headers = self.get_headers()
        cookies = self.get_cookies()

        try:
            response = self.session.get(url, headers=headers, cookies=cookies, timeout=10)
            response.raise_for_status()
            data = response.json()
            return data.get('js', {}).get('data', [])
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to get Series in category {category_id}: {e}")
            return []

    def get_seasons(self, movie_id):
        self.ensure_valid_token()
        
        url = f"{self.portal_url}/portal.php?type=series&action=get_ordered_list&movie_id={movie_id}&JsHttpRequest=1-xml"
        headers = self.get_headers()
        cookies = self.get_cookies()

        try:
            response = self.session.get(url, headers=headers, cookies=cookies, timeout=10)
            response.raise_for_status()
            data = response.json()
            return data.get('js', {}).get('data', [])
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to get seasons for movie {movie_id}: {e}")
            return []

    def get_episodes(self, movie_id, season_id):
        self.ensure_valid_token()
        
        url = f"{self.portal_url}/portal.php?type=series&action=get_ordered_list&movie_id={movie_id}&season_id={season_id}&JsHttpRequest=1-xml"
        headers = self.get_headers()
        cookies = self.get_cookies()

        try:
            response = self.session.get(url, headers=headers, cookies=cookies, timeout=10)
            response.raise_for_status()
            data = response.json()
            return data.get('js', {}).get('data', [])
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to get episodes for movie {movie_id} and season {season_id}: {e}")
            return []

    def search_itv(self, query):
        self.ensure_valid_token()
        url = f"{self.portal_url}/portal.php?type=itv&action=search&q={quote(query)}&JsHttpRequest=1-xml"
        headers = self.get_headers()
        cookies = self.get_cookies()
        try:
            response = self.session.get(url, headers=headers, cookies=cookies, timeout=15)
            response.raise_for_status()
            data = response.json()
            return data.get('js', {}).get('data', [])
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to search ITV for '{query}': {e}")
            return []

    def search_vod(self, query):
        self.ensure_valid_token()
        url = f"{self.portal_url}/portal.php?type=vod&action=search&q={quote(query)}&JsHttpRequest=1-xml"
        headers = self.get_headers()
        cookies = self.get_cookies()
        try:
            response = self.session.get(url, headers=headers, cookies=cookies, timeout=15)
            response.raise_for_status()
            data = response.json()
            return data.get('js', {}).get('data', [])
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to search VOD for '{query}': {e}")
            return []

    def search_series(self, query):
        self.ensure_valid_token()
        url = f"{self.portal_url}/portal.php?type=series&action=search&q={quote(query)}&JsHttpRequest=1-xml"
        headers = self.get_headers()
        cookies = self.get_cookies()
        try:
            response = self.session.get(url, headers=headers, cookies=cookies, timeout=15)
            response.raise_for_status()
            data = response.json()
            return data.get('js', {}).get('data', [])
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to search Series for '{query}': {e}")
            return []

    def get_stream_link(self, cmd, stream_id):
        logger.debug(f"[STREAM] Comandă originală: {cmd}, ID Stream: {stream_id}")

        stream_cmd = cmd.strip()

        if re.match(r'(?i)^ffmpeg\s*(.*)', stream_cmd):
            logger.debug(f"[STREAM] Înlătur prefixul 'ffmpeg': {stream_cmd}")
            stream_cmd = re.sub(r'(?i)^ffmpeg\s*', '', stream_cmd).strip()

        create_link_url = f"{self.portal_url}/portal.php?type=itv&action=create_link&cmd={quote(stream_cmd)}&JsHttpRequest=1-xml"
        headers = self.get_headers()
        cookies = self.get_cookies()

        try:
            logger.debug(f"[STREAM] Efectuez cerere create_link: {create_link_url}")
            response = self.session.get(create_link_url, headers=headers, cookies=cookies, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            returned_cmd = data.get('js', {}).get('cmd')

            if returned_cmd:
                logger.debug(f"[STREAM] Comandă returnată de la create_link: {returned_cmd}")
                try:
                    play_token = returned_cmd.split('play_token=')[1].split('&')[0]
                    # Construiește URL-ul final folosind stream_id și play_token
                    final_stream_url = f"{self.portal_url}/play/live.php?mac={self.mac}&stream={stream_id}&extension=ts&play_token={play_token}"
                    logger.debug(f"[STREAM] URL stream final generat: {final_stream_url}")
                    return final_stream_url
                except IndexError:
                    logger.error(f"[STREAM] Nu am putut extrage play_token din: {returned_cmd}")
                    # Fallback la comportamentul vechi dacă extragerea token-ului eșuează
                    return returned_cmd
            else:
                logger.warning(f"[STREAM] Portalul nu a returnat o comandă validă în răspunsul create_link: {data}")
                return None

        except requests.exceptions.RequestException as e:
            logger.error(f"[STREAM] Eroare la cererea create_link: {e}")
            return None

    def get_vod_stream_url(self, movie_id):
        self.ensure_valid_token()
        
        cmd = f"movie {movie_id}"
        url = f"{self.portal_url}/portal.php?type=vod&action=create_link&cmd={quote(cmd)}&JsHttpRequest=1-xml"
        headers = self.get_headers()
        cookies = self.get_cookies()

        try:
            response = self.session.get(url, headers=headers, cookies=cookies, timeout=10)
            response.raise_for_status()
            data = response.json()
            returned_url = data.get('js', {}).get('cmd')
            
            if returned_url:
                try:
                    play_token = returned_url.split('play_token=')[1].split('&')[0]
                    stream_url = f"{self.portal_url}/play/movie.php?mac={self.mac}&stream={movie_id}.mkv&play_token={play_token}&type=movie"
                    logger.debug(f"[VOD] URL stream generat: {stream_url}")
                    return stream_url
                except IndexError:
                    # Dacă nu găsește play_token, încearcă să proceseze URL-ul direct
                    logger.debug(f"[VOD] Nu găsesc play_token, procesez URL direct: {returned_url}")
                    return self.get_stream_link(returned_url)
            
            return None
        except (requests.exceptions.RequestException, IndexError) as e:
            logger.error(f"Failed to get VOD stream link for movie {movie_id}: {e}")
            return None

    def get_series_stream_url(self, cmd, episode_num):
        self.ensure_valid_token()
        
        url = f"{self.portal_url}/portal.php?type=vod&action=create_link&cmd={quote(cmd)}&series={episode_num}&JsHttpRequest=1-xml"
        headers = self.get_headers()
        cookies = self.get_cookies()

        try:
            response = self.session.get(url, headers=headers, cookies=cookies, timeout=10)
            response.raise_for_status()
            data = response.json()
            stream_url = data.get('js', {}).get('cmd')
            
            if stream_url:
                if stream_url.startswith('ffmpeg '):
                    processed_url = stream_url.split(' ', 1)[1]
                    logger.debug(f"[SERIES] URL procesat după îndepărtarea ffmpeg: {processed_url}")
                    return processed_url
                else:
                    logger.debug(f"[SERIES] URL procesat direct: {stream_url}")
                    return stream_url
                    
            return None
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to get series stream link for cmd {cmd}, episode {episode_num}: {e}")
            return None