#!/usr/bin/env python3
import json
import urllib.request
from datetime import datetime, timezone, timedelta
from zoneinfo import ZoneInfo

# Company Bay, Dunedin (decimal degrees)
LAT = -45.858
LON = 170.601
TZ_NAME = "Pacific/Auckland"

OUT_FILE = "dunedin.rss"


def fetch_open_meteo():
    # Hourly gives us: feels-like (apparent), rain probability, and precip (mm)
    url = (
        "https://api.open-meteo.com/v1/forecast"
        f"?latitude={LAT}&longitude={LON}"
        "&hourly=apparent_temperature,precipitation_probability,precipitation"
        f"&timezone={TZ_NAME}"
        "&temperature_unit=celsius"
    )
    with urllib.request.urlopen(url, timeout=15) as r:
        return json.loads(r.read().decode("utf-8"))


def iso_hour_key(dt: datetime) -> str:
    return dt.strftime("%Y-%m-%dT%H:00")


def fmt_mm(mm: float) -> str:
    # 0.0 -> 0, 0.7 -> 0.7, 2.0 -> 2
    return f"{mm:.1f}".rstrip("0").rstrip(".")


def build_line(data: dict) -> str:
    # Compute local "now" from Open-Meteo's utc offset (avoids ZoneInfo/tzdata issues)
    offset_seconds = int(data.get("utc_offset_seconds", 0))
    now_local = (datetime.now(timezone.utc) + timedelta(seconds=offset_seconds)).replace(tzinfo=None)

    hourly = data.get("hourly", {}) or {}
    times = hourly.get("time", []) or []
    feels = hourly.get("apparent_temperature", []) or []
    pop = hourly.get("precipitation_probability", []) or []
    precip = hourly.get("precipitation", []) or []

    idx_by_time = {t: i for i, t in enumerate(times)}

    def get(arr, i):
        return arr[i] if i is not None and 0 <= i < len(arr) else None

    def iso_hour_key(dt: datetime) -> str:
        return dt.strftime("%Y-%m-%dT%H:00")

    def fmt_mm(mm: float) -> str:
        return f"{mm:.1f}".rstrip("0").rstrip(".")

    # Current hour slot (local)
    now_hour = now_local.replace(minute=0, second=0, microsecond=0)
    now_i = idx_by_time.get(iso_hour_key(now_hour))
    now_x = get(feels, now_i)
    now_str = f"{now_x:.0f}" if now_x is not None else "—"

    hour = now_local.hour

    # Day vs night based on local hour
    is_day = (hour >= 7) and (hour < 19)
    icon = "☀️" if is_day else "🌙"
    boundary_label = "7pm" if is_day else "7am"

    # Remaining window start/end (local)
    start = now_hour
    if is_day:
        end = now_local.replace(hour=19, minute=0, second=0, microsecond=0)
    else:
        if hour >= 19:
            end = (now_local + timedelta(days=1)).replace(hour=7, minute=0, second=0, microsecond=0)
        else:
            end = now_local.replace(hour=7, minute=0, second=0, microsecond=0)

    # Collect hourly indices from start..end inclusive
    window_indices = []
    dt = start
    while dt <= end:
        i = idx_by_time.get(iso_hour_key(dt))
        if i is not None:
            window_indices.append(i)
        dt += timedelta(hours=1)

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

    return f"{icon} Now: {now_str} °C ||| Now to {boundary_label}: {minmax_str} °C (min/max) | 🌧️ {a:.0f} % ({b_str} mm)"


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