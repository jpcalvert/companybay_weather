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
        "&hourly=apparent_temperature,precipitation_probability,precipitation"
        f"&timezone={TZ_NAME}"
        "&temperature_unit=celsius"
    )
    with urllib.request.urlopen(url, timeout=15) as r:
        return json.loads(r.read().decode("utf-8"))

def fmt_hour_label(h: int) -> str:
    if h == 0:
        return "12am"
    if h < 12:
        return f"{h}am"
    if h == 12:
        return "12pm"
    return f"{h-12}pm"

def fmt_mm(mm: float) -> str:
    # 0.0 -> 0, 0.7 -> 0.7, 2.0 -> 2
    return f"{mm:.1f}".rstrip("0").rstrip(".")

def fmt_rain_segment(prob: float | None, mm: float | None) -> str:
    """
    Include all suggestions:
    - Show rain segment only if prob > 0
    - If mm <= 0, show only '| Y%'
    - If mm > 0, show '| Y% Zmm'
    """
    if prob is None or prob <= 0:
        return ""
    mm_val = 0.0 if mm is None else float(mm)
    if mm_val <= 0:
        return f" | {prob:.0f}%"
    return f" | {prob:.0f}% {fmt_mm(mm_val)}mm"

def build_line(data: dict) -> str:
    tz = ZoneInfo(TZ_NAME)
    now_local = datetime.now(tz)
    today = now_local.date()

    hourly = data.get("hourly", {}) or {}
    times = hourly.get("time", []) or []
    feels = hourly.get("apparent_temperature", []) or []
    pop = hourly.get("precipitation_probability", []) or []
    precip = hourly.get("precipitation", []) or []

    idx_by_time = {t: i for i, t in enumerate(times)}

    def get(arr, i):
        return arr[i] if i is not None and 0 <= i < len(arr) else None

    # NOW = current hour slot
    now_hour = now_local.replace(minute=0, second=0, microsecond=0)
    now_key = now_hour.strftime("%Y-%m-%dT%H:00")
    now_i = idx_by_time.get(now_key)
    now_x = get(feels, now_i)

    # Window = today 08:00..19:00 (inclusive)
    window_indices = []
    for h in range(8, 20):  # 8..19
        dt = datetime.combine(today, datetime.min.time(), tzinfo=tz).replace(hour=h)
        key = dt.strftime("%Y-%m-%dT%H:00")
        i = idx_by_time.get(key)
        if i is not None:
            window_indices.append(i)

    # Aggregate stats
    window_feels = [get(feels, i) for i in window_indices]
    window_feels = [v for v in window_feels if v is not None]

    window_pop = [get(pop, i) for i in window_indices]
    window_pop = [v for v in window_pop if v is not None]

    window_precip = [get(precip, i) for i in window_indices]
    window_precip = [v for v in window_precip if v is not None]

    # Defaults if data missing
    y = min(window_feels) if window_feels else None
    z = max(window_feels) if window_feels else None
    a = max(window_pop) if window_pop else 0
    b = max(window_precip) if window_precip else 0

    # Format (keep it clean)
    now_str = f"{now_x:.0f}" if now_x is not None else "—"
    minmax_str = f"{y:.0f} - {z:.0f}" if (y is not None and z is not None) else "— - —"

    # mm formatting: 0.0 -> 0, 0.7 -> 0.7, 2.0 -> 2
    b_str = f"{float(b):.1f}".rstrip("0").rstrip(".") if b is not None else "0"

    return f"Now: {now_str} °C ||| Min/Max: {minmax_str} °C ||| Rain: {a:.0f} % ({b_str} mm)"

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