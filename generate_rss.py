#!/usr/bin/env python3
import json
import urllib.request
from datetime import datetime, timezone

LAT = -45.8788
LON = 170.5028
TZ  = "Pacific/Auckland"

OUT_FILE = "dunedin.rss"

def fetch_open_meteo():
    url = (
        "https://api.open-meteo.com/v1/forecast"
        f"?latitude={LAT}&longitude={LON}"
        "&current=temperature_2m,apparent_temperature,relative_humidity_2m,wind_speed_10m,wind_gusts_10m"
        f"&timezone={TZ}"
        "&temperature_unit=celsius"
        "&wind_speed_unit=kmh"
    )
    with urllib.request.urlopen(url, timeout=15) as r:
        return json.loads(r.read().decode("utf-8"))

def make_rss_line(cur: dict) -> str:
    t = cur.get("temperature_2m")
    feels = cur.get("apparent_temperature")
    rh = cur.get("relative_humidity_2m")
    wind = cur.get("wind_speed_10m")
    gust = cur.get("wind_gusts_10m")

    parts = []
    if t is not None and feels is not None:
        parts.append(f"Dunedin now: {t:.0f}°C (feels {feels:.0f}°C)")
    elif t is not None:
        parts.append(f"Dunedin now: {t:.0f}°C")

    if wind is not None:
        if gust is not None:
            parts.append(f"Wind {wind:.0f} km/h (gust {gust:.0f})")
        else:
            parts.append(f"Wind {wind:.0f} km/h")

    if rh is not None:
        parts.append(f"RH {rh:.0f}%")

    return " • ".join(parts)

def write_rss(line: str):
    # basic RSS 2.0; keep it simple
    now = datetime.now(timezone.utc).strftime("%a, %d %b %Y %H:%M:%S %z")
    rss = f"""<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0">
  <channel>
    <title>Dunedin Practical Weather</title>
    <link>https://example.invalid/</link>
    <description>Auto-generated for DAKboard</description>
    <lastBuildDate>{now}</lastBuildDate>
    <item>
      <title>{line}</title>
      <link>https://open-meteo.com/</link>
      <description>{line}</description>
      <pubDate>{now}</pubDate>
    </item>
  </channel>
</rss>
"""
    with open(OUT_FILE, "w", encoding="utf-8") as f:
        f.write(rss)

def main():
    data = fetch_open_meteo()
    cur = data.get("current", {})
    line = make_rss_line(cur)
    write_rss(line)
    print("Wrote", OUT_FILE, "->", line)

if __name__ == "__main__":
    main()