import random
import re
import json
import time
import datetime
import multiprocessing
import socketserver
import urllib.request
import winreg
from http.server import BaseHTTPRequestHandler

PORT_METAR = 18080
PORT_PAC = 18081
INTERVAL = 15*60  # seconds

PAC_CONTENT = """function FindProxyForURL(url, host) {if (dnsDomainIs(host, "metar.vatsim.net")) {return "PROXY 127.0.0.1:__PORT__";}}"""
CONFIG_FILE = "METAR.json"


def format_time(time: float) -> str:
    return datetime.datetime.fromtimestamp(time).strftime(r"%H:%M:%S")


class METARHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        content = b""
        pattern_url = r"metar\.php\?id=((ZB|ZG|ZJ|ZS|ZY|ZP|ZU|ZW|ZL|ZH)[A-Z]{2})"
        if matches := re.search(pattern_url, self.path, re.IGNORECASE | re.DOTALL):
            id = matches.group(1)
            config = json.load(open(CONFIG_FILE, 'r'))
            try:
                if id in config['RECORD'].keys() and \
                    id not in config['CONCERNED'] and \
                        time.time()-config['RECORD'][id]['TIME'] < INTERVAL:
                    metar = config['RECORD'][id]['METAR']
                    content = metar.encode()
                    print(f"[{format_time(time.time())}-METAR] (OLD)\n\t{metar}")
                else:
                    url = f"http://xmairavt7.xiamenair.com/WarningPage/AirportInfo?arp4code={id}"
                    response = urllib.request.urlopen(url, timeout=5)
                    data = response.read().decode("utf-8")
                    metar = re.search(
                        r"<p>(METAR|SPECI) (.*)</p>", data).group(2)
                    metar = id + ' ' + \
                        re.search(f"{id} (.*)", metar).group(1)
                    config['RECORD'][id] = {
                        'METAR': metar,
                        'TIME': time.time()
                    }
                    json.dump(config, open(CONFIG_FILE, 'w'),
                              ensure_ascii=False, indent=2)
                    content = metar.encode()
                    print(f"[{format_time(time.time())}-METAR] (NEW)\n\t{metar}")
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
            content = PAC_CONTENT.replace("__PORT__", str(PORT_METAR)).encode()
            print(f"[{format_time(time.time())}-PAC] (GET)")
        self.send_response(200)
        self.send_header('Content-type', 'text/plain')
        self.end_headers()
        self.wfile.write(content)

    def log_message(self, format, *args):
        return


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


def job_METAR(port):
    global PORT_METAR
    PORT_METAR = port
    print(f"[INFO] METAR server is listening on port {PORT_METAR}")
    httpd = socketserver.TCPServer(("0.0.0.0", PORT_METAR), METARHandler)
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        httpd.server_close()


def job_PAC(port_pac, port_metar):
    global PORT_PAC, PORT_METAR
    PORT_PAC, PORT_METAR = port_pac, port_metar
    print(f"[INFO] PAC server is listening on port {PORT_PAC}")
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
    print("[INFO] PAC ON")


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
        config['CONCERNED'] = input(
            "Airports to concern (seperated by space)>").upper().split()
        content = json.dumps(config, ensure_ascii=False, indent=2)
        f.seek(0)
        f.truncate()
        f.write(content)

    pm = random.randint(10001, 65535)
    pp = random.randint(10001, 65535)
    p1 = multiprocessing.Process(target=job_winreg, args=(pp,))
    p2 = multiprocessing.Process(target=job_METAR, args=(pm,))
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
        print("[INFO] Servers are shutdown")
    finally:
        set_proxy_pac()
        print("[INFO] PAC OFF")
    input("Press Enter to exit...")
