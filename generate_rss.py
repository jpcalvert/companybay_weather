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


from datetime import timedelta

def iso_hour_key(dt) -> str:
    return dt.strftime("%Y-%m-%dT%H:00")

def fmt_mm(mm: float) -> str:
    return f"{mm:.1f}".rstrip("0").rstrip(".")


def build_line(data: dict) -> str:
    tz = ZoneInfo(TZ_NAME)
    now_local = datetime.now(tz)

    hourly = data.get("hourly", {}) or {}
    times = hourly.get("time", []) or []
    feels = hourly.get("apparent_temperature", []) or []
    pop = hourly.get("precipitation_probability", []) or []
    precip = hourly.get("precipitation", []) or []

    idx_by_time = {t: i for i, t in enumerate(times)}

    def get(arr, i):
        return arr[i] if i is not None and 0 <= i < len(arr) else None

    # NOW (current hour slot)
    now_hour = now_local.replace(minute=0, second=0, microsecond=0)
    now_i = idx_by_time.get(iso_hour_key(now_hour))
    now_x = get(feels, now_i)

    now_str = f"{now_x:.0f}" if now_x is not None else "—"

    # Decide window: DAY 07:00–19:00, NIGHT 19:00–07:00 (crosses midnight)
    hour = now_local.hour

    is_day = (hour >= 7) and (hour < 19)
    icon = "☀️" if is_day else "🌙"

    if is_day:
        start = now_local.replace(hour=7, minute=0, second=0, microsecond=0)
        end = now_local.replace(hour=19, minute=0, second=0, microsecond=0)
    else:
        if hour >= 19:
            # night starts today 19:00, ends tomorrow 07:00
            start = now_local.replace(hour=19, minute=0, second=0, microsecond=0)
            end = (start + timedelta(days=1)).replace(hour=7)
        else:
            # after midnight before 07:00: night started yesterday 19:00, ends today 07:00
            end = now_local.replace(hour=7, minute=0, second=0, microsecond=0)
            start = (end - timedelta(days=1)).replace(hour=19)

    # Collect hourly indices in [start, end] (inclusive start, inclusive end hour)
    window_indices = []
    dt = start
    while dt <= end:
        i = idx_by_time.get(iso_hour_key(dt))
        if i is not None:
            window_indices.append(i)
        dt += timedelta(hours=1)

    # Aggregate
    window_feels = [get(feels, i) for i in window_indices]
    window_feels = [v for v in window_feels if v is not None]

    window_pop = [get(pop, i) for i in window_indices]
    window_pop = [v for v in window_pop if v is not None]

    window_precip = [get(precip, i) for i in window_indices]
    window_precip = [v for v in window_precip if v is not None]

    y = min(window_feels) if window_feels else None
    z = max(window_feels) if window_feels else None

    a = max(window_pop) if window_pop else 0
    b = max(window_precip) if window_precip else 0

    minmax_str = f"{y:.0f} - {z:.0f}" if (y is not None and z is not None) else "— - —"
    b_str = fmt_mm(float(b)) if b is not None else "0"

    return f"{icon} Now (new): {now_str} °C (min/max: {minmax_str} °C) ||| Rain: {a:.0f} % ({b_str} mm)"

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