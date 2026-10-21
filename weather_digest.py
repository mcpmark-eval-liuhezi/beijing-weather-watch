#!/usr/bin/env python3
"""
weather_digest.py — Beijing Weather Watch weekly ops digest generator.

Builds the weekly markdown digest for the Beijing field-engineering team from
the weather snapshot collected on the morning of 2026-10-22 (Asia/Shanghai).

Data provenance (collected 2026-10-22 ~06:16 Beijing local time):
  * Current conditions, government alert check, and same-day-last-year
    history: WeatherAPI (Beijing, 39.9289 N / 116.3883 E), retrieved via the
    weather-data tool suite.
  * 7-day daily forecast series: Open-Meteo for the same coordinates, fetched
    programmatically at collection time, because the WeatherAPI forecast
    response is truncated by the tool output limit before the day 2-7 daily
    summaries are returned. WeatherAPI's day-1 figures (max 15.9 C, rain
    chance 3%) were used only as a cross-check of the series start.

Every figure printed in the digest is computed by this script from the
snapshot below at run time — nothing is hand-typed into the output.
"""

from datetime import date

# ---------------------------------------------------------------------------
# 1. COLLECTED SNAPSHOT
# ---------------------------------------------------------------------------

SNAPSHOT = {
    # Beijing local date at collection time (Asia/Shanghai). The year-over-year
    # reference date is derived from THIS value, not from the machine clock.
    "local_date": "2026-10-22",
    "local_time_collected": "2026-10-22 06:16",
    "timezone": "Asia/Shanghai",

    "current": {
        "last_updated": "2026-10-22 06:00",
        "temp_c": 8.9,
        "feelslike_c": 8.1,
        "condition": "Smoky haze",
        "humidity_pct": 36,
        "wind_kph": 6.5,
        "wind_dir": "NE",
        "pressure_mb": 1026,
        "precip_mm": 0.0,
        "vis_km": 6.2,
    },

    # Exactly what the government alert check returned for Beijing: an
    # empty list ("alerts": {"alert": []}).
    "alerts": [],

    # 7-day daily forecast series (Open-Meteo, Asia/Shanghai timezone).
    "forecast_days": [
        {"date": "2026-10-22", "tmax_c": 15.3, "tmin_c": 4.4, "rain_chance_pct": 0,  "precip_mm": 0.0},
        {"date": "2026-10-23", "tmax_c": 16.0, "tmin_c": 6.0, "rain_chance_pct": 2,  "precip_mm": 0.0},
        {"date": "2026-10-24", "tmax_c": 17.9, "tmin_c": 8.1, "rain_chance_pct": 4,  "precip_mm": 0.0},
        {"date": "2026-10-25", "tmax_c": 13.7, "tmin_c": 10.8, "rain_chance_pct": 62, "precip_mm": 3.5},
        {"date": "2026-10-26", "tmax_c": 18.3, "tmin_c": 10.2, "rain_chance_pct": 31, "precip_mm": 0.0},
        {"date": "2026-10-27", "tmax_c": 12.9, "tmin_c": 5.3, "rain_chance_pct": 0,  "precip_mm": 0.0},
        {"date": "2026-10-28", "tmax_c": 12.7, "tmin_c": 2.1, "rain_chance_pct": 0,  "precip_mm": 0.0},
    ],

    # Same calendar day, one year ago (WeatherAPI history for Beijing).
    "history_last_year": {
        "date": "2025-10-22",
        "tmax_c": 13.5,
        "tmin_c": 6.8,
        "tavg_c": 10.3,
        "precip_mm": 0.0,
        "condition": "Cloudy",
        "avghumidity_pct": 33,
        "maxwind_kph": 6.5,
    },
}

RAIN_CHANCE_THRESHOLD = 50  # percent

# ---------------------------------------------------------------------------
# 2. STATISTICS
# ---------------------------------------------------------------------------
def compute_statistics(snapshot):
    """Compute the weekly digest statistics from the collected snapshot."""
    forecast_days = snapshot["forecast_days"]

    # Mean of the daily maximum temperatures across the 7-day forecast.
    tmax_values = [day["tmax_c"] for day in forecast_days]
    mean_tmax = sum(tmax_values) / len(tmax_values)

    # Hottest forecast day (with its date).
    hottest_day = max(forecast_days, key=lambda day: day["tmax_c"])

    # How many forecast days have a rain chance of 50% or more.
    rainy_days = [day for day in forecast_days
                  if day["rain_chance_pct"] >= RAIN_CHANCE_THRESHOLD]

    # Alert status line: count of active alerts, or "no active alerts".
    alerts = snapshot["alerts"]
    if len(alerts) == 0:
        alert_line = "Alert status: no active alerts."
    else:
        alert_line = "Alert status: {} active alert{}.".format(
            len(alerts), "s" if len(alerts) != 1 else "")

    # Year-over-year: same-day-last-year temperature vs. the current one.
    cur = snapshot["current"]["temp_c"]
    last_year_avg = snapshot["history_last_year"]["tavg_c"]
    delta = cur - last_year_avg
    if delta > 0:
        comparison = "warmer than"
    elif delta < 0:
        comparison = "cooler than"
    else:
        comparison = "the same as"
    yoy_line = ("Year over year: Beijing is currently {cur:.1f}°C, which is "
                "{abs_delta:.1f}°C {word} the {ly:.1f}°C recorded on {date} "
                "(same calendar day, one year ago).".format(
                    cur=cur, abs_delta=abs(delta), word=comparison,
                    ly=last_year_avg, date=snapshot["history_last_year"]["date"]))

    return {
        "mean_tmax_c": mean_tmax,
        "hottest_date": hottest_day["date"],
        "hottest_tmax_c": hottest_day["tmax_c"],
        "rainy_day_count": len(rainy_days),
        "rainy_day_dates": [day["date"] for day in rainy_days],
        "alert_line": alert_line,
        "alert_count": len(alerts),
        "yoy_line": yoy_line,
        "yoy_current_c": cur,
        "yoy_last_year_c": last_year_avg,
        "yoy_delta_c": delta,
    }

# ---------------------------------------------------------------------------
# 3. DIGEST RENDERING
# ---------------------------------------------------------------------------
def render_digest(snapshot, stats):
    """Render the collected data and computed statistics as markdown."""
    cur = snapshot["current"]
    hist = snapshot["history_last_year"]
    rainy_list = ", ".join(stats["rainy_day_dates"]) if stats["rainy_day_dates"] else "none"

    lines = []
    lines.append("# Beijing Weather Watch — Weekly Ops Digest")
    lines.append("")
    lines.append("_Generated {} (Asia/Shanghai), week of {}_".format(
        snapshot["local_time_collected"], snapshot["local_date"]))
    lines.append("")
    lines.append("## Current conditions (Beijing)")
    lines.append("")
    lines.append("- **Temperature:** {:.1f}°C (feels like {:.1f}°C)".format(
        cur["temp_c"], cur["feelslike_c"]))
    lines.append("- **Condition:** {}".format(cur["condition"]))
    lines.append("- **Humidity:** {}%".format(cur["humidity_pct"]))
    lines.append("- **Wind:** {} km/h {}".format(cur["wind_kph"], cur["wind_dir"]))
    lines.append("- **Pressure:** {} mb".format(cur["pressure_mb"]))
    lines.append("- **Visibility:** {} km".format(cur["vis_km"]))
    lines.append("- **Precipitation:** {:.1f} mm".format(cur["precip_mm"]))
    lines.append("")
    lines.append("## Alerts and warnings")
    lines.append("")
    lines.append("- " + stats["alert_line"])
    lines.append("  - The government alert check for Beijing returned an empty "
                 "alert list — explicitly, **nothing is active**.")
    lines.append("")
    lines.append("## 7-day forecast")
    lines.append("")
    lines.append("| Date | Max (°C) | Min (°C) | Rain chance (%) |")
    lines.append("|------|----------|----------|-----------------|")
    for day in snapshot["forecast_days"]:
        lines.append("| {} | {:.1f} | {:.1f} | {} |".format(
            day["date"], day["tmax_c"], day["tmin_c"], day["rain_chance_pct"]))
    lines.append("")
    lines.append("## Weekly statistics")
    lines.append("")
    lines.append("- **Mean daily max temperature (7-day forecast):** {:.2f}°C".format(
        stats["mean_tmax_c"]))
    lines.append("- **Hottest forecast day:** {} ({:.1f}°C)".format(
        stats["hottest_date"], stats["hottest_tmax_c"]))
    lines.append("- **Forecast days with rain chance ≥ 50%:** {} ({})".format(
        stats["rainy_day_count"], rainy_list))
    lines.append("- " + stats["alert_line"])
    lines.append("- " + stats["yoy_line"])
    lines.append("")
    lines.append("## Same day last year (year-over-year reference)")
    lines.append("")
    lines.append("On {} Beijing recorded a high of {:.1f}°C, a low of {:.1f}°C, "
                 "a daily mean of {:.1f}°C, and {:.1f} mm of precipitation.".format(
                     hist["date"], hist["tmax_c"], hist["tmin_c"],
                     hist["tavg_c"], hist["precip_mm"]))
    lines.append("")
    return "\n".join(lines)


def main():
    stats = compute_statistics(SNAPSHOT)
    digest = render_digest(SNAPSHOT, stats)

    # Headline summary for the pull-request description.
    headline = "\n".join([
        "**Mean daily max temperature (7-day forecast):** {:.2f}°C".format(stats["mean_tmax_c"]),
        "**Hottest forecast day:** {} ({:.1f}°C)".format(stats["hottest_date"], stats["hottest_tmax_c"]),
        "**Forecast days with rain chance ≥ 50%:** {} ({})".format(stats["rainy_day_count"],
                                                                   ", ".join(stats["rainy_day_dates"]) or "none"),
        "**" + stats["alert_line"] + "**",
        "**" + stats["yoy_line"] + "**",
    ])

    print(digest)
    print()
    print("=" * 70)
    print("DIGEST HEADLINE (for PR description):")
    print("=" * 70)
    print(headline)

    # Write the generated markdown to DIGEST.md next to this script.
    with open("DIGEST.md", "w", encoding="utf-8") as f:
        f.write(digest + "\n")
    print()
    print("DIGEST.md written ({} bytes)".format(len(digest) + 1))


if __name__ == "__main__":
    main()
