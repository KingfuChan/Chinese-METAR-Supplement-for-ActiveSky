import multiprocessing
import re
import json
import time
import socketserver
from http.server import BaseHTTPRequestHandler
import urllib.request

import mitmproxy.http
from mitmproxy.tools.main import mitmdump

PORT_PROXY = 8080
PORT_SERVER = 8079
INTERVAL = 15*60  # seconds


class MyHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        content = b""
        if self.path == "/metar.pac":
            content = open("metar.pac"
                           ).read().replace("127.0.0.1:8080",
                                            f"127.0.0.1:{PORT_PROXY}").encode()
        elif self.path.startswith('/metar.php') and 'id=' in self.path:
            id = self.path[-4:]
            if id[0:2] in ["ZB", "ZG", "ZJ", "ZS", "ZY", "ZP", "ZU", "ZW", "ZL", "ZH"]:
                config = json.load(open("config.json", 'r'))
                try:
                    if id in config['RECORD'].keys() and id not in config['CONCERNED'] and time.time()-config['RECORD'][id]['TIME'] < INTERVAL:
                        metar = config['RECORD'][id]['METAR']
                        content = metar.encode()
                        print("既有数据", metar)
                    else:
                        url = f"http://xmairavt7.xiamenair.com/WarningPage/AirportInfo?arp4code={id}"
                        response = urllib.request.urlopen(url)
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
                        print("新请求", metar)
                except Exception as e:
                    print(e)

        self.send_response(200)
        self.send_header('Content-type', 'text/plain')
        self.end_headers()
        self.wfile.write(content)


def request(flow: mitmproxy.http.HTTPFlow):
    if flow.request.pretty_url.startswith("http://metar.vatsim.net/"):
        flow.request.host = "localhost"
        flow.request.port = PORT_SERVER


def job_proxy():
    # Start mitmproxy in a separate thread
    mitmdump(["--set", f"listen_port={PORT_PROXY}", "-s", __file__])


def job_server():
    print("工作端口", PORT_SERVER)
    httpd = socketserver.TCPServer(("0.0.0.0", PORT_SERVER), MyHandler)
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        httpd.server_close()


if __name__ == '__main__':
    with open("config.json", 'a+') as f:
        content = f.read()
        if len(content):
            config = json.loads(content)
        else:
            config = {'CONCERNED': [], 'RECORD': {}}
    config['CONCERNED'] = input("请输入特别关注机场，以空格分隔>").split()
    json.dump(config, open("config.json", 'w'),
              ensure_ascii=False, indent=2)

    # Create two processes for each job
    p1 = multiprocessing.Process(target=job_proxy)
    p2 = multiprocessing.Process(target=job_server)
    # Start both processes
    p1.start()
    p2.start()
    # Wait for both processes to finish
    try:
        p1.join()
        p2.join()
    except KeyboardInterrupt:
        p1.terminate()
        p2.terminate()
