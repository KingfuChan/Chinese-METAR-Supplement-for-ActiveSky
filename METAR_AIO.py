import json
import multiprocessing
import re
import socketserver
import time
import urllib.request
import winreg
from http.server import BaseHTTPRequestHandler
import random

PORT = 18080
INTERVAL = 15*60  # seconds

PAC_CONTENT = """function FindProxyForURL(url, host) {if (dnsDomainIs(host, "metar.vatsim.net")) {return "PROXY 127.0.0.1:__PORT__";}}"""


class MyHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        content = b""
        if self.path == "/metar.pac":
            content = PAC_CONTENT.replace("__PORT__", str(PORT)).encode()
            print("PAC requested")
        elif matches := re.search(r"metar\.php\?id=((ZB|ZG|ZJ|ZS|ZY|ZP|ZU|ZW|ZL|ZH)[A-Z]{2})",
                                  self.path, re.IGNORECASE | re.DOTALL):
            id = matches.group(1)
            config = json.load(open("config.json", 'r'))
            try:
                if id in config['RECORD'].keys() and \
                    id not in config['CONCERNED'] and \
                        time.time()-config['RECORD'][id]['TIME'] < INTERVAL:
                    metar = config['RECORD'][id]['METAR']
                    content = metar.encode()
                    print(f">>>METAR for {id} acquired (old): {metar}")
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
                    json.dump(config, open("config.json", 'w'),
                              ensure_ascii=False, indent=2)
                    content = metar.encode()
                    print(f">>>METAR for {id} acquired (new): {metar}")
            except Exception as e:
                print(e)

        self.send_response(200)
        self.send_header('Content-type', 'text/plain')
        self.end_headers()
        self.wfile.write(content)

    def log_message(self, format, *args):
        return


def set_proxy_pac(pac_url):
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


def job_server(port):
    global PORT
    PORT = port
    print(f"Listening on port {PORT}. Press Ctrl-C to stop.")
    httpd = socketserver.TCPServer(("0.0.0.0", PORT), MyHandler)
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        httpd.server_close()


def job_winreg(port):
    global PORT
    PORT = port
    time.sleep(5)
    set_proxy_pac(f"http://127.0.0.1:{PORT}/metar.pac")
    print("PAC set")


if __name__ == '__main__':
    with open("config.json", 'a+') as f:
        f.seek(0)
        content = f.read()
        if len(content):
            config = json.loads(content)
        else:
            config = {'CONCERNED': [], 'RECORD': {}}
        config['CONCERNED'] = input(
            "Concerned airports (seperated by space)>").split()
        content = json.dumps(config, ensure_ascii=False, indent=2)
        f.seek(0)
        f.truncate()
        f.write(content)

    port = random.randint(10001, 65535)
    p1 = multiprocessing.Process(target=job_winreg, args=(port,))
    p2 = multiprocessing.Process(target=job_server, args=(port,))
    p1.start()
    p2.start()
    try:
        p1.join()
        p2.join()
    except KeyboardInterrupt:
        p1.terminate()
        p2.terminate()
    finally:
        set_proxy_pac("")
        print("PAC unset")
    input("Press Enter to exit...")
