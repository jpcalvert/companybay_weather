#!/usr/bin/env python3
import json
import urllib.request
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

LAT = -45.858
LON = 170.601
TZ_NAME = "Pacific/Auckland"

OUT_FILE = "dunedin.rss"

def fetch_open_meteo():
    url = (
        "https://api.open-meteo.com/v1/forecast"
        f"?latitude={LAT}&longitude={LON}"
        # current "feels like"
        "&current=apparent_temperature"
        # hourly feels-like + rain probability + precip (mm)
        "&hourly=apparent_temperature,precipitation_probability,precipitation"
        f"&timezone={TZ_NAME}"
        "&temperature_unit=celsius"
        "&wind_speed_unit=kmh"
    )
    with urllib.request.urlopen(url, timeout=15) as r:
        return json.loads(r.read().decode("utf-8"))

def fmt_hour_label(h: int) -> str:
    # 8 -> 8am, 12 -> 12pm, 13 -> 1pm, 19 -> 7pm
    if h == 0:
        return "12am"
    if h < 12:
        return f"{h}am"
    if h == 12:
        return "12pm"
    return f"{h-12}pm"

def fmt_precip(prob: float | None, mm: float | None) -> str:
    # Only include if probability is non-zero
    if prob is None or prob <= 0:
        return ""
    mm = 0.0 if mm is None else mm
    # keep mm tidy: 0.0/0.2/1.5/12
    mm_str = f"{mm:.1f}".rstrip("0").rstrip(".")
    return f" | {prob:.0f}% ({mm_str})"

def build_line(data: dict) -> str:
    tz = ZoneInfo(TZ_NAME)
    now_local = datetime.now(tz)

    # "Now" feels-like
    cur = data.get("current", {}) or {}
    now_feels = cur.get("apparent_temperature", None)
    now_part = "Now: —"
    if now_feels is not None:
        now_part = f"Now: {now_feels:.0f}°"

    # Hourly arrays
    hourly = data.get("hourly", {}) or {}
    times = hourly.get("time", []) or []
    feels = hourly.get("apparent_temperature", []) or []
    pop = hourly.get("precipitation_probability", []) or []
    precip = hourly.get("precipitation", []) or []

    # Map timestamps -> index
    idx_by_time = {t: i for i, t in enumerate(times)}

    # Only show upcoming hours between 8am and 7pm local, for *today*
    start_hour = 8
    end_hour = 19

    parts = [now_part]

    for h in range(start_hour, end_hour + 1):
        # build a datetime for today at hour h (local)
        target = now_local.replace(hour=h, minute=0, second=0, microsecond=0)

        # remove times that are current or already past
        if target <= now_local:
            continue

        key = target.strftime("%Y-%m-%dT%H:00")
        i = idx_by_time.get(key)
        if i is None:
            continue

        x = feels[i] if i < len(feels) else None
        if x is None:
            continue

        y = pop[i] if i < len(pop) else None
        z = precip[i] if i < len(precip) else None

        label = fmt_hour_label(h)
        seg = f"{label}: {x:.0f}°{fmt_precip(y, z)}"
        parts.append(seg)

    return "  ".join(parts)

def write_rss(line: str):
    now = datetime.now(timezone.utc).strftime("%a, %d %b %Y %H:%M:%S %z")
    rss = f"""<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0">
  <channel>
    <title>Company Bay Practical Weather</title>
    <link>https://open-meteo.com/</link>
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
    line = build_line(data)
    write_rss(line)
    print("Wrote", OUT_FILE, "->", line)

if __name__ == "__main__":
    main()
