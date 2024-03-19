# Chinese-METAR-Supplement-for-ActiveSky

**Methodology:** Use a PAC proxy to intercept requests to metar.vatsim.net and return a value from <http://xmairavt7.xiamenair.com/WarningPage/AirportInfo?arp4code=ZXXX>.

As you may be aware that this API is no longer publicly available, the script allows you to enter your own URL for this service, as long as the response contains a METAR.

**Usage:** Check "VATSIM online weather" in settings and load a flight plan into ActiveSky.

**Note:**

1. In order to achieve more accurate CAVOK cloud behaviour, the script replaces all `CAVOK` to `// ////`. This will cause discrepancy between real-world METAR and ActiveSky display, but it allows ActiveSky to use its original cloud coverage at the airport. Chinese METAR only contains cloud coverage below FL100 even when it's overcast at higher altitude.
2. This script will automatically setup Windows proxy via PAC and will conflict with other programs using PAC. When normal HTTP proxy is set via other program, this script will read it from WinREG and use the address as fallback in PAC.
