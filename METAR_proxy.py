from mitmproxy import http
from mitmproxy.tools.main import mitmdump

PORT_SERVER = 8079
PORT_PROXY = 8080


def request(flow: http.HTTPFlow) -> None:
    if flow.request.pretty_url.startswith("http://metar.vatsim.net/"):
        flow.request.host = "localhost"
        flow.request.port = PORT_SERVER


def main():
    # Start mitmproxy in a separate thread
    mitmdump(["--set", f"listen_port={PORT_PROXY}", "-s", __file__])


if __name__ == "__main__":
    main()
