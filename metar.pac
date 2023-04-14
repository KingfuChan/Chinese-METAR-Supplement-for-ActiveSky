function FindProxyForURL(url, host) {
	if (dnsDomainIs(host, "metar.vatsim.net")) {
		return "PROXY 127.0.0.1:8080";
	}
}
