# Chinese-METAR-Supplement-for-ActiveSky

**Methodology:** Use a PAC proxy to intercept requests to metar.vatsim.net and return a value from <http://xmairavt7.xiamenair.com/WarningPage/AirportInfo?arp4code=ZXXX>.

As you may be aware that this API is no longer publicly available, the script allows you to enter your own URL for this service, as long as the response contains a METAR.

**Usage:**

1. Modify the global parameters inside the script as desired.
2. Run the python script. The script accepts an URL as command line parameter to replace the default. E.g. `python CN-METAR-SUPP.py http://127.0.0.1:9999/METAR.php?ICAO=__ICAO__`.
3. Start up ActiveSky and check "VATSIM online weather" in Settings -> General.
4. Load a flight plan into ActiveSky.

**Note:**

+ This script will automatically setup Windows proxy via PAC and will conflict with other programs using PAC. When normal HTTP proxy is set via other program, this script will read it from WinREG and use the address as fallback in PAC.
