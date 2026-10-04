"""Synthetic Open-Meteo responses, so threshold cases don't depend on today's real weather."""
from datetime import datetime, timedelta

CALM = {"temperature_2m": 26, "apparent_temperature": 27, "relative_humidity_2m": 55, "precipitation": 0.0,
        "precipitation_probability": 10, "weather_code": 1, "wind_speed_10m": 10, "wind_gusts_10m": 18, "uv_index": 5}


def fake_forecast(now="2026-09-03T10:30", **overrides):
    """Same shape as /v1/forecast with past_days=3, forecast_days=3; every hour gets the same values."""
    values = {**CALM, **overrides}
    t0 = datetime.fromisoformat(now).replace(hour=0, minute=0) - timedelta(days=3)
    times = [t0 + timedelta(hours=i) for i in range(24 * 7)]
    hourly = {"time": [t.strftime("%Y-%m-%dT%H:%M") for t in times]}
    hourly |= {k: [v] * len(times) for k, v in values.items()}
    return {"current": {"time": now}, "hourly": hourly}
