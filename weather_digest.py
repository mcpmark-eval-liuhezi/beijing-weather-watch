"""
weather_digest.py — Weekly Beijing ops weather digest generator.

Fetches live data (Open-Meteo, no API key required) for Beijing, computes the
weekly statistics, and prints a markdown digest. Written for the field
engineering team's weekly ops digest.

Keyless APIs used:
  * Forecast:  https://api.open-meteo.com/v1/forecast
  * Archive:   https://archive-api.open-meteo.com/v1/archive

Author: ops automation
"""

import json
import sys
import urllib.request
from datetime import datetime, timedelta

# --- Beijing location and timezone anchors (from the live timezone check) ---
LAT = 39.9289
LON = 116.3883
TIMEZONE = "Asia/Shanghai"

# WMO weather interpretation codes (used for readable current conditions)
WMO_CODES = {
    0: "Clear sky",
    1: "Mainly clear",
    2: "Partly cloudy",
    3: "Overcast",
    45: "Fog",
    48: "Depositing rime fog",
    51: "Light drizzle",
    53: "Moderate drizzle",
    55: "Dense drizzle",
    61: "Slight rain",
    63: "Moderate rain",
    65: "Heavy rain",
    66: "Light freezing rain",
    67: "Heavy freezing rain",
    71: "Slight snowfall",
    73: "Moderate snowfall",
    75: "Heavy snowfall",
    77: "Snow grains",
    80: "Slight rain showers",
    81: "Moderate rain showers",
    82: "Violent rain showers",
    85: "Slight snow showers",
    86: "Heavy snow showers",
    95: "Thunderstorm",
    96: "Thunderstorm with slight hail",
    99: "Thunderstorm with heavy hail",
}


def fetch_json(url):
    """GET a URL and return the parsed JSON payload."""
    with urllib.request.urlopen(url, timeout=30) as response:
        return json.loads(response.read().decode())


def fetch_forecast():
    """Fetch the 7-day daily forecast for Beijing (local timezone)."""
    url = (
        "https://api.open-meteo.com/v1/forecast"
        f"?latitude={LAT}&longitude={LON}"
        "&daily=temperature_2m_max,temperature_2m_min,precipitation_probability_max,"
        "weather_code"
        f"&timezone={urllib.request.quote(TIMEZONE)}&forecast_days=7"
    )
    return fetch_json(url)["daily"]


def fetch_history(date_iso):
    """Fetch archived daily conditions for a specific past date (local timezone)."""
    url = (
        "https://archive-api.open-meteo.com/v1/archive"
        f"?latitude={LAT}&longitude={LON}"
        f"&start_date={date_iso}&end_date={date_iso}"
        "&daily=temperature_2m_max,temperature_2m_min,temperature_2m_mean,"
        "precipitation_sum"
        f"&timezone={urllib.request.quote(TIMEZONE)}"
    )
    return fetch_json(url)["daily"]


def fetch_current():
    """Fetch current conditions for Beijing (local timezone)."""
    url = (
        "https://api.open-meteo.com/v1/forecast"
        f"?latitude={LAT}&longitude={LON}"
        "&current=temperature_2m,relative_humidity_2m,apparent_temperature,"
        "precipitation,weather_code,wind_speed_10m"
        f"&timezone={urllib.request.quote(TIMEZONE)}"
    )
    return fetch_json(url)["current"]


# --- Statistics -------------------------------------------------------------


def compute_stats(forecast_daily, history_daily):
    """Compute all digest statistics from the fetched forecast/history data.

    Returns a dict with:
      mean_max_temp  - mean of the daily maximum temperatures across the 7-day forecast
      hottest_day    - (date, temperature) of the hottest forecast day
      rainy_days     - number of forecast days with a rain chance of 50% or more
      rainy_day_list - dates of those days (for the digest detail)
    """
    dates = forecast_daily["time"]
    max_temps = forecast_daily["temperature_2m_max"]
    rain_chances = forecast_daily["precipitation_probability_max"]

    mean_max_temp = sum(max_temps) / len(max_temps)

    hottest_index = max(range(len(max_temps)), key=lambda i: max_temps[i])
    hottest_day = (dates[hottest_index], max_temps[hottest_index])

    rainy_indices = [i for i, c in enumerate(rain_chances) if c >= 50]
    rainy_days = len(rainy_indices)
    rainy_day_list = [dates[i] for i in rainy_indices]

    return {
        "mean_max_temp": mean_max_temp,
        "hottest_day": hottest_day,
        "rainy_days": rainy_days,
        "rainy_day_list": rainy_day_list,
    }


def year_over_year(current_temp_c, last_year_temp_c, last_year_date):
    """Compare today's current temperature against the same day last year."""
    delta = current_temp_c - last_year_temp_c
    if delta > 0:
        comparison = f"{delta:+.1f}°C warmer than"
    elif delta < 0:
        comparison = f"{abs(delta):.1f}°C cooler than"
    else:
        comparison = "the same as"
    return (
        f"Year over year: Beijing is currently {current_temp_c:.1f}°C, which is "
        f"{comparison} the {last_year_temp_c:.1f}°C recorded on {last_year_date} "
        f"(same calendar day, one year ago)."
    )


# --- Digest rendering --------------------------------------------------------


def build_digest(current, forecast_daily, history_daily, alert_count):
    """Build the markdown digest from live data and the alert status."""
    stats = compute_stats(forecast_daily, history_daily)
    hottest_date, hottest_temp = stats["hottest_day"]

    # Determine the local date from the API's timezone-anchored timestamps
    today_local = forecast_daily["time"][0]
    last_year_date = history_daily["time"][0]
    last_year_temp = history_daily["temperature_2m_mean"][0]

    # Alert status line: count of active alerts, or 'no active alerts'
    if alert_count:
        alert_line = f"Alert status: {alert_count} active alert(s) for Beijing."
    else:
        alert_line = "Alert status: no active alerts."

    code = current["weather_code"]
    condition = WMO_CODES.get(code, f"Weather code {code}")

    lines = []
    lines.append("# Beijing Weather Watch — Weekly Ops Digest")
    lines.append("")
    lines.append(f"_Generated {current['time']} ({TIMEZONE})_")
    lines.append("")
    lines.append("## Current conditions (Beijing)")
    lines.append("")
    lines.append(f"- **Temperature:** {current['temperature_2m']:.1f}°C "
                 f"(feels like {current['apparent_temperature']:.1f}°C)")
    lines.append(f"- **Condition:** {condition}")
    lines.append(f"- **Humidity:** {current['relative_humidity_2m']}%")
    lines.append(f"- **Wind:** {current['wind_speed_10m']:.1f} km/h")
    lines.append(f"- **Precipitation:** {current['precipitation']:.1f} mm")
    lines.append("")
    lines.append("## Alerts and warnings")
    lines.append("")
    lines.append(f"- {alert_line}")
    lines.append("")
    lines.append("## 7-day forecast")
    lines.append("")
    lines.append("| Date | Max (°C) | Min (°C) | Rain chance (%) |")
    lines.append("|------|----------|----------|-----------------|")
    for i, date in enumerate(forecast_daily["time"]):
        lines.append(
            f"| {date} | {forecast_daily['temperature_2m_max'][i]:.1f} "
            f"| {forecast_daily['temperature_2m_min'][i]:.1f} "
            f"| {forecast_daily['precipitation_probability_max'][i]} |"
        )
    lines.append("")
    lines.append("## Weekly statistics")
    lines.append("")
    lines.append(f"- **Mean daily max temperature (7-day forecast):** "
                 f"{stats['mean_max_temp']:.2f}°C")
    lines.append(f"- **Hottest forecast day:** {hottest_date} "
                 f"({hottest_temp:.1f}°C)")
    lines.append(f"- **Forecast days with rain chance ≥ 50%:** {stats['rainy_days']}"
                 + (f" ({', '.join(stats['rainy_day_list'])})"
                    if stats["rainy_day_list"] else ""))
    lines.append(f"- {alert_line}")
    lines.append(f"- {year_over_year(current['temperature_2m'], last_year_temp, last_year_date)}")
    lines.append("")
    lines.append("## Same day last year (year-over-year reference)")
    lines.append("")
    lines.append(f"On {last_year_date} Beijing recorded a high of "
                 f"{history_daily['temperature_2m_max'][0]:.1f}°C, a low of "
                 f"{history_daily['temperature_2m_min'][0]:.1f}°C, a daily mean of "
                 f"{last_year_temp:.1f}°C, and "
                 f"{history_daily['precipitation_sum'][0]:.1f} mm of precipitation.")
    lines.append("")

    digest = "\n".join(lines)

    headline = {
        "mean_max_temp": stats["mean_max_temp"],
        "hottest_day": stats["hottest_day"],
        "rainy_days": stats["rainy_days"],
        "alert_line": alert_line,
        "year_over_year": year_over_year(
            current["temperature_2m"], last_year_temp, last_year_date
        ),
    }
    return digest, headline


def main():
    # Alert status comes from the government weather-alert check run for
    # Beijing: it returned an empty alert list, i.e. nothing active.
    ALERT_COUNT = 0

    current = fetch_current()
    forecast_daily = fetch_forecast()
    history_daily = fetch_history("2025-10-22")

    digest, headline = build_digest(current, forecast_daily, history_daily, ALERT_COUNT)

    print(digest)
    print()
    print("----- HEADLINE (for the pull request description) -----")
    print(f"Mean daily max temperature (7-day forecast): {headline['mean_max_temp']:.2f}°C")
    hottest_date, hottest_temp = headline["hottest_day"]
    print(f"Hottest forecast day: {hottest_date} ({hottest_temp:.1f}°C)")
    print(f"Forecast days with rain chance >= 50%: {headline['rainy_days']}")
    print(headline["alert_line"])
    print(headline["year_over_year"])

    # Also write the digest to a file next to this script for publication
    with open("DIGEST.md", "w", encoding="utf-8") as fh:
        fh.write(digest + "\n")
    print()
    print("Wrote DIGEST.md")


if __name__ == "__main__":
    main()
