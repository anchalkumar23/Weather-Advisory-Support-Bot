"""Open-Meteo access and window facts. Every number the bot may report comes out of compute_facts()."""
import os
from datetime import datetime, timedelta

import httpx

GEOCODE_URL = os.getenv("GEOCODE_URL", "https://geocoding-api.open-meteo.com/v1/search")
FORECAST_URL = os.getenv("FORECAST_URL", "https://api.open-meteo.com/v1/forecast")
HOURLY = ("temperature_2m,apparent_temperature,relative_humidity_2m,precipitation,"
          "precipitation_probability,weather_code,wind_speed_10m,wind_gusts_10m,uv_index")

# The vocabulary SOP conditions can reference. Adding a metric here is the one policy change that needs code.
METRICS = {
    "temp_max_c": "highest air temperature in the window (°C)",
    "temp_min_c": "lowest air temperature in the window (°C)",
    "feels_like_max_c": "highest feels-like temperature in the window (°C)",
    "feels_like_min_c": "lowest feels-like temperature in the window (°C)",
    "rain_prob_max_pct": "highest hourly chance of rain in the window (%)",
    "rain_window_mm": "total rain expected in the window (mm)",
    "rain_past24h_mm": "rain over the last 24 hours (mm)",
    "rain_next24h_mm": "rain expected over the next 24 hours (mm)",
    "rain_72h_mm": "rain over the last 48h plus next 24h (mm)",
    "wind_max_kmh": "highest sustained wind in the window (km/h)",
    "gust_max_kmh": "highest wind gust in the window (km/h)",
    "uv_max": "highest UV index in the window",
    "humidity_max_pct": "highest relative humidity in the window (%)",
    "thunder_in_window": "thunderstorm forecast in the window (true/false)",
}

# Hour ranges (inclusive) for each part of the day.
PARTS = {"morning": (6, 11), "afternoon": (12, 16), "evening": (17, 20), "night": (21, 23), "all_day": (6, 21)}


class WeatherError(Exception):
    """Location can't be resolved or the weather service failed. Always routed to the honest fallback."""


def _get(url, params):
    try:
        r = httpx.get(url, params=params, timeout=10)
        r.raise_for_status()
        data = r.json()
    except httpx.HTTPStatusError as e:
        raise WeatherError("the weather service returned an error") from e
    except (httpx.HTTPError, ValueError) as e:
        raise WeatherError("the weather service is not responding") from e
    if isinstance(data, dict) and data.get("error"):
        raise WeatherError(f"the weather service reported a problem: {data.get('reason', 'unknown')}")
    return data


def geocode(name):
    results = _get(GEOCODE_URL, {"name": name, "count": 1, "language": "en", "format": "json"}).get("results")
    if not results:
        raise WeatherError(f"couldn't find a place called '{name}'")
    top = results[0]
    label = ", ".join(x for x in (top["name"], top.get("admin1"), top.get("country")) if x)
    return {"name": label, "lat": top["latitude"], "lon": top["longitude"]}


def fetch_forecast(lat, lon):
    return _get(FORECAST_URL, {
        "latitude": lat, "longitude": lon, "timezone": "auto", "past_days": 3, "forecast_days": 3,
        "current": "temperature_2m,precipitation,wind_speed_10m", "hourly": HOURLY,
    })


def window_range(now, day, part):
    """Return (start, end, label). A 'today' part that is already over rolls to tomorrow, and the label says so."""
    if part == "now":
        return now, now + timedelta(hours=2), f"now ({now:%H:00}–{now + timedelta(hours=2):%H:00})"
    lo, hi = PARTS[part]
    date = now.date() + timedelta(days=1 if day == "tomorrow" else 0)
    start, end = datetime(date.year, date.month, date.day, lo), datetime(date.year, date.month, date.day, hi)
    if day == "today" and end < now:
        start, end, day = start + timedelta(days=1), end + timedelta(days=1), "tomorrow"
    name = "rest of the day" if part == "all_day" and start < now else part.replace("_", " ")
    start = max(start, now)
    return start, end, f"{day} {name} ({start:%H:00}–{end:%H:00})"


def compute_facts(raw, day="today", part="now"):
    h = raw["hourly"]
    times = [datetime.fromisoformat(t) for t in h["time"]]
    now = datetime.fromisoformat(raw["current"]["time"]).replace(minute=0)
    start, end, label = window_range(now, day, part)

    def pick(key, lo, hi):
        return [v for t, v in zip(times, h[key]) if lo <= t <= hi and v is not None]

    def total(lo, hi):  # hourly precipitation is the sum over the preceding hour
        return round(sum(pick("precipitation", lo, hi)), 1)

    win = {k: pick(k, start, end) for k in h if k != "time"}
    if not win["temperature_2m"]:
        raise WeatherError("no forecast data for the requested time window")
    hour = timedelta(hours=1)
    facts = {
        "temp_max_c": max(win["temperature_2m"]),
        "temp_min_c": min(win["temperature_2m"]),
        "feels_like_max_c": max(win["apparent_temperature"]),
        "feels_like_min_c": min(win["apparent_temperature"]),
        "rain_prob_max_pct": max(win["precipitation_probability"], default=0),
        "rain_window_mm": total(start, end),
        "rain_past24h_mm": total(now - 23 * hour, now),
        "rain_next24h_mm": total(now + hour, now + 24 * hour),
        "rain_72h_mm": total(now - 47 * hour, now + 24 * hour),
        "wind_max_kmh": max(win["wind_speed_10m"]),
        "gust_max_kmh": max(win["wind_gusts_10m"]),
        "uv_max": max(win["uv_index"], default=0),
        "humidity_max_pct": max(win["relative_humidity_2m"]),
        "thunder_in_window": any(c >= 95 for c in win["weather_code"]),
    }
    return {k: round(v, 1) if isinstance(v, float) else v for k, v in facts.items()}, label


def get_weather(location, day, part):
    place = geocode(location)
    facts, label = compute_facts(fetch_forecast(place["lat"], place["lon"]), day, part)
    return place, facts, label
