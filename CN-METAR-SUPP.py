import datetime
import json
import multiprocessing
import random
import re
import socketserver
import sys
import time
import urllib.request
import winreg
from http.server import BaseHTTPRequestHandler

PORT_METAR = None  # change to None to randomize
PORT_PAC = None  # change to None to randomize
INTERVAL = 9*60  # seconds
REPLACE_CAVOK_NSC = True

METAR_URL = sys.argv[1] if len(sys.argv) > 1\
    else "http://xmairavt7.xiamenair.com/WarningPage/AirportInfo?arp4code=__ICAO__"
PAC_CONTENT = """function FindProxyForURL(url, host) {if (dnsDomainIs(host, "metar.vatsim.net")) {return "PROXY 127.0.0.1:__PORT__";} return "__FALLBACK__";}"""
CONFIG_FILE = "METAR.json"
INVALID = []


def format_time(time: float) -> str:
    return datetime.datetime.fromtimestamp(time).strftime(r"%H:%M:%S")


class METARHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        content = b""
        pattern_url = r"metar\.php\?id=(Z[A-Z]{3})"
        if matches := re.search(pattern_url, self.path, re.IGNORECASE | re.DOTALL):
            id = matches.group(1)
            config = json.load(open(CONFIG_FILE, 'r'))

            try:
                if id in config['RECORD'].keys() and \
                    id not in config['CONCERNED'] and \
                        time.time()-config['RECORD'][id]['TIME'] < INTERVAL:
                    metar = config['RECORD'][id]['METAR']
                    mtime = config['RECORD'][id]['TIME']
                    mtype = "OLD"
                    content = metar.encode()
                elif id not in INVALID:
                    response = urllib.request.urlopen(
                        METAR_URL.replace("__ICAO__", id), timeout=5)
                    data = response.read().decode("utf-8")
                    metar = re.search(
                        r"<([a-zA-Z0-9]+)>(METAR|SPECI) (.+?)</\1>", data).group(3)
                    metar = metar.replace('=', '')  # deal with trailing '='
                    mtime = time.time()
                    mtype = "NEW"

                # METAR post-process
                config['RECORD'][id] = {
                    'METAR': metar,
                    'TIME': mtime
                }
                json.dump(config, open(CONFIG_FILE, 'w'),
                          ensure_ascii=False, indent=2)
                msg = f"\t{metar}"
                if REPLACE_CAVOK_NSC:
                    metar = metar.replace("CAVOK", "9999 ////")
                    metar = metar.replace("NSC", "////")
                    msg += f"\n\t{metar}"
                content = metar.encode()
                print(f"[{format_time(time.time())}-METAR] ({mtype})\n{msg}")

            except AttributeError as e:
                INVALID.append(id)
                print(
                    f"[{format_time(time.time())}-METAR] (ERR-REMOVED)\n\t{id}:", e)

            except Exception as e:
                print(f"[{format_time(time.time())}-METAR] (ERR)\n\t{id}:", e)

        self.send_response(200)
        self.send_header('Content-type', 'text/plain')
        self.end_headers()
        self.wfile.write(content)

    def log_message(self, format, *args):
        return


class PACHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        content = b""
        if self.path.endswith("pac"):
            content = PAC_CONTENT.encode()
            print(f"[{format_time(time.time())}-PAC] (GET)")
        self.send_response(200)
        self.send_header('Content-type', 'text/plain')
        self.end_headers()
        self.wfile.write(content)

    def log_message(self, format, *args):
        return


def get_http_proxy():
    registry_path = r'Software\Microsoft\Windows\CurrentVersion\Internet Settings'
    key = winreg.OpenKey(winreg.HKEY_CURRENT_USER,
                         registry_path, 0, winreg.KEY_ALL_ACCESS)
    registry_key = 'ProxyEnable'
    value, _regtype = winreg.QueryValueEx(key, registry_key)
    if not value:
        winreg.CloseKey(key)
        return ''
    registry_key = 'ProxyServer'
    value, _regtype = winreg.QueryValueEx(key, registry_key)
    winreg.CloseKey(key)
    return value


def set_proxy_pac(pac_url=str()):
    registry_path = r'Software\Microsoft\Windows\CurrentVersion\Internet Settings'
    registry_key = 'AutoConfigURL'
    key = winreg.OpenKey(winreg.HKEY_CURRENT_USER,
                         registry_path, 0, winreg.KEY_WRITE)
    if len(pac_url):
        winreg.SetValueEx(key, registry_key, 0, winreg.REG_SZ, pac_url)
    else:
        winreg.DeleteValue(key, registry_key)
    winreg.CloseKey(key)

    registry_path = r'Software\Microsoft\Windows\CurrentVersion\Internet Settings\Connections'
    registry_key = 'DefaultConnectionSettings'
    key = winreg.OpenKey(winreg.HKEY_CURRENT_USER,
                         registry_path, 0, winreg.KEY_ALL_ACCESS)
    value, regtype = winreg.QueryValueEx(key, registry_key)
    value = list(value)
    value[8] = 9 if len(pac_url) else 5
    value = bytes(value)
    winreg.SetValueEx(key, registry_key, 0, regtype, value)
    winreg.CloseKey(key)

    import ctypes
    internet_option_refresh = 37
    internet_option_settings_changed = 39
    internet_set_option = ctypes.windll.Wininet.InternetSetOptionW
    internet_set_option(0, internet_option_refresh, 0, 0)
    internet_set_option(0, internet_option_settings_changed, 0, 0)


def job_METAR(port, url):
    global PORT_METAR, METAR_URL
    PORT_METAR = port
    METAR_URL = url if len(url) else METAR_URL
    print(f"[INFO] Using {METAR_URL} as METAR source.")
    print(f"[INFO] METAR server is listening on port {PORT_METAR}.")
    httpd = socketserver.TCPServer(("0.0.0.0", PORT_METAR), METARHandler)
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        httpd.server_close()


def job_PAC(port_pac, port_metar):
    global PORT_PAC, PAC_CONTENT
    PORT_PAC = port_pac
    http_proxy = get_http_proxy()
    if len(http_proxy):
        print(f"[INFO] PAC fallback on {http_proxy}.")
        PAC_CONTENT = PAC_CONTENT.replace(
            "__FALLBACK__", f"PROXY {http_proxy}")
    else:
        PAC_CONTENT = PAC_CONTENT.replace("__FALLBACK__", "DIRECT")
    PAC_CONTENT = PAC_CONTENT.replace("__PORT__", str(port_metar))
    print(f"[INFO] PAC server is listening on port {PORT_PAC}.")
    httpd = socketserver.TCPServer(("0.0.0.0", PORT_PAC), PACHandler)
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        httpd.server_close()


def job_winreg(port):
    global PORT_PAC
    PORT_PAC = port
    time.sleep(5)
    set_proxy_pac(f"http://127.0.0.1:{PORT_PAC}/metar.pac")
    print("[INFO] PAC ON.")


if __name__ == '__main__':
    print("Chinese-METAR-Supplement-for-ActiveSky")
    print("Check \"VATSIM online weather\" and load a flight plan.")
    print("Use Ctrl-C to close this program.")

    with open(CONFIG_FILE, 'a+') as f:
        f.seek(0)
        content = f.read()
        if len(content):
            config = json.loads(content)
        else:
            config = {'CONCERNED': [], 'RECORD': {}}
        concerned = input(
            "Airports to concern (seperated by space, starting with + for additons)>").upper()
        if len(concerned) and concerned[0] == '+':
            config['CONCERNED'].extend(concerned[1:].split())
        else:
            config['CONCERNED'] = concerned.split()
            config['RECORD'] = {}
        content = json.dumps(config, ensure_ascii=False, indent=2)
        f.seek(0)
        f.truncate()
        f.write(content)

    pm = random.randint(10001, 65535) if PORT_METAR is None else PORT_METAR
    pp = random.randint(10001, 65535) if PORT_PAC is None else PORT_PAC
    p1 = multiprocessing.Process(target=job_winreg, args=(pp,))
    p2 = multiprocessing.Process(target=job_METAR, args=(pm, METAR_URL))
    p3 = multiprocessing.Process(target=job_PAC, args=(pp, pm))
    p1.start()
    p2.start()
    p3.start()
    try:
        p1.join()
        p2.join()
        p3.join()
    except KeyboardInterrupt:
        p1.terminate()
        p2.terminate()
        p3.terminate()
        print("[INFO] Servers are shutdown.")
    finally:
        set_proxy_pac()
        print("[INFO] PAC OFF.")
    input("Press Enter to exit...")
