import json
import requests
import hashlib
import time
import os
import sys
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

TIMEOUT = 15

SERVERS_URL = os.environ.get(
    "SERVERS_URL",
    "https://raw.githubusercontent.com/staycanuca/hub/refs/heads/main/_tools/servers.json",
)
OUTPUT_FILE = os.environ.get("OUTPUT_FILE", "servers.json")
GITHUB_OUTPUT = os.environ.get("GITHUB_OUTPUT")


def detect_portal_type(base_url):
    headers = {
        "User-Agent": "Mozilla/5.0 (QtEmbedded; U; Linux; C) AppleWebKit/533.3 (KHTML, like Gecko) MAG200 stbapp ver: 2 rev: 250 Safari/533.3",
        "Accept-Encoding": "identity",
        "Accept": "*/*",
        "Connection": "keep-alive",
    }

    version_urls = [
        f"{base_url}/c/version.js",
        f"{base_url}/stalker_portal/c/version.js",
    ]

    for version_url in version_urls:
        try:
            response = requests.get(
                version_url, headers=headers, timeout=TIMEOUT, verify=False
            )
            if response.status_code == 200:
                if "stalker_portal" in version_url:
                    return "stalker_portal/server/load.php"
                else:
                    return "portal.php"
        except:
            continue

    return "portal.php"


def check_portal(url):
    try:
        full_url = url.rstrip("/") + "/c/"
        response = requests.get(
            full_url, timeout=TIMEOUT, verify=False, allow_redirects=True
        )
        if response.status_code == 200:
            return True
        if response.status_code in [301, 302, 303, 307, 308]:
            return True
        return False
    except Exception:
        return False


def check_mac(portal_url, mac):
    try:
        portal_url = portal_url.rstrip("/")

        portal_type = detect_portal_type(portal_url)

        serialnumber = hashlib.md5(mac.encode()).hexdigest().upper()
        sn = serialnumber[0:13]
        device_id = hashlib.sha256(sn.encode()).hexdigest().upper()
        device_id2 = hashlib.sha256(mac.encode()).hexdigest().upper()
        hw_version_2 = hashlib.sha1(mac.encode()).hexdigest()

        cookies = {
            "adid": hw_version_2,
            "debug": "1",
            "device_id2": device_id2,
            "device_id": device_id,
            "hw_version": "1.7-BD-00",
            "mac": mac,
            "sn": sn,
            "stb_lang": "en",
            "timezone": "America/Los_Angeles",
        }

        headers = {
            "User-Agent": "Mozilla/5.0 (QtEmbedded; U; Linux; C) AppleWebKit/533.3 (KHTML, like Gecko) MAG200 stbapp ver: 2 rev: 250 Safari/533.3",
            "Accept-Encoding": "identity",
            "Accept": "*/*",
            "Connection": "keep-alive",
        }

        handshake_url = f"{portal_url}/{portal_type}?action=handshake&type=stb&token=&JsHttpRequest=1-xml"

        response = requests.get(
            handshake_url,
            cookies=cookies,
            headers=headers,
            timeout=TIMEOUT,
            verify=False,
        )

        if response.status_code != 200 or len(response.text) == 0:
            return False

        try:
            data = response.json()
            token = data.get("js", {}).get("token")
            token_random = data.get("js", {}).get("random")
        except:
            return False

        if not token:
            return False

        if token_random:
            sig = hashlib.sha256(token_random.encode()).hexdigest().upper()
            headers["Authorization"] = f"Bearer {token}"
            headers["X-Random"] = f"{token_random}"
        else:
            token_random = "0"
            sig = hashlib.sha256(token_random.encode()).hexdigest().upper()

        profile_url = (
            f"{portal_url}/{portal_type}?"
            f"type=stb&action=get_profile&hd=1&ver=ImageDescription: 0.2.18-r23-250; "
            f"ImageDate: Wed Aug 29 10:49:53 EEST 2018; PORTAL version: 5.3.1; "
            f"API Version: JS API version: 343; STB API version: 146; "
            f"Player Engine version: 0x58c&num_banks=2&sn={sn}&stb_type=MAG250&client_type=STB&"
            f"image_version=218&video_out=hdmi&device_id={device_id2}&device_id2={device_id2}&"
            f"sig={sig}&auth_second_step=1&hw_version=1.7-BD-00&not_valid_token=0&"
            f"timestamp={round(time.time())}&api_sig=262&prehash=0"
        )

        profile_response = requests.get(
            profile_url, cookies=cookies, headers=headers, timeout=TIMEOUT, verify=False
        )

        if profile_response.status_code == 200 and len(profile_response.text) > 0:
            try:
                profile_data = profile_response.json()
                if profile_data.get("js"):
                    return True
            except:
                pass

        return False

    except Exception:
        return False


def verify_server(server):
    portal_url = server.get("portal_url", "")
    if not portal_url:
        return None

    portal_works = check_portal(portal_url)

    valid_macs = []
    macs = server.get("macs", [])

    for mac in macs:
        if check_mac(portal_url, mac):
            valid_macs.append(mac)

    if portal_works and not valid_macs:
        return None

    if not portal_works and not valid_macs:
        return None

    return valid_macs


def main():
    print(f"Fetching servers from: {SERVERS_URL}")

    response = requests.get(SERVERS_URL, timeout=30)
    response.raise_for_status()
    data = response.json()

    servers = data.get("servers", [])
    valid_servers = []

    print(f"Verificare {len(servers)} servere...")

    for server in servers:
        print(f"Verificare server: {server.get('name')} - {server.get('portal_url')}")

        portal_works = check_portal(server.get("portal_url", ""))
        print(f"  Portal: {'OK' if portal_works else 'FAIL'}")

        result = verify_server(server)

        if result is None:
            print(f"  -> Server invalid sau toate MAC-urile nefunctionale - STERS")
            continue

        server["macs"] = result
        valid_servers.append(server)
        print(f"  -> Server OK, {len(result)} MAC-uri valide")

    data["servers"] = valid_servers

    with open(OUTPUT_FILE, "w") as f:
        json.dump(data, f, indent=4)

    print(f"\nTerminat: {len(valid_servers)}/{len(servers)} servere ramase")

    if GITHUB_OUTPUT:
        with open(GITHUB_OUTPUT, "a") as f:
            f.write(f"valid_servers={len(valid_servers)}\n")
            f.write(f"total_servers={len(servers)}\n")
            f.write(f"valid_macs={sum(len(s['macs']) for s in valid_servers)}\n")

    return len(valid_servers) > 0


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
