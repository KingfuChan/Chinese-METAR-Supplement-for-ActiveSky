import http.server
import re
import signal
import socketserver
import sys
import time
import urllib.request

PORT_PROXY = 8080
PORT_SERVER = 8079
INTERVAL = 15*60  # seconds
CONCERNED = []
RECORD = {}


class MyHandler(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        content = b""
        if self.path == "/metar.pac":
            content = open("metar.pac"
                           ).read().replace("127.0.0.1:8080",
                                            f"127.0.0.1:{PORT_PROXY}").encode()
        elif self.path.startswith('/metar.php') and 'id=' in self.path:
            id = self.path[-4:]
            if id[0:2] in ["ZB", "ZG", "ZJ", "ZS", "ZY", "ZP", "ZU", "ZW", "ZL", "ZH"]:
                # Make a GET request to a URL
                try:
                    if id in RECORD.keys() and id not in CONCERNED and time.time()-RECORD[id]['TIME'] < INTERVAL:
                        metar = RECORD[id]['METAR']
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
                        RECORD[id] = {
                            'METAR': metar,
                            'TIME': time.time()
                        }
                        content = metar.encode()
                        print("新请求", metar)
                except Exception as e:
                    print(e)

        self.send_response(200)
        self.send_header('Content-type', 'text/plain')
        self.end_headers()
        self.wfile.write(content)


def signal_handler(sig, frame):
    global httpd
    print('关闭服务器...')
    httpd.server_close()
    sys.exit(0)


def main(concerned):
    global CONCERNED
    if len(concerned):
        CONCERNED = concerned
    else:
        CONCERNED = input("请输入特别关注机场，以空格分隔>").split()
    global httpd
    signal.signal(signal.SIGINT, signal_handler)
    print("工作端口", PORT_SERVER)
    httpd = socketserver.TCPServer(("0.0.0.0", PORT_SERVER), MyHandler)
    httpd.serve_forever()


if __name__ == "__main__":
    main([])
