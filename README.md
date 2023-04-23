# Chinese-METAR-Supplement-for-ActiveSky

Methodology: Use a PAC proxy to intercept requests to metar.vatsim.net and return a value from <http://xmairavt7.xiamenair.com/WarningPage/AirportInfo?arp4code=ZXXX>.

Usage: Check \"VATSIM online weather\" and load a flight plan.

Note: This script will automatically setup Winodos proxy via PAC and will conflict with other programs using PAC. When normal HTTP proxy is set via other program, this script will read it from WinREG and use the address as fallback in PAC, but it isn't flawless.
