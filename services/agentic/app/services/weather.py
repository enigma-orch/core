from __future__ import annotations

import logging
import time
from dataclasses import dataclass

import httpx

logger = logging.getLogger(__name__)

# Open-Meteo — free, no API key needed
FORECAST_URL = "https://api.open-meteo.com/v1/forecast"

# Open-Meteo updates hourly; 15 minutes per location is plenty and
# keeps the scraper from re-geocoding every cycle.
_CACHE_TTL_SECONDS = 15 * 60
_cache: dict[str, tuple[float, "Weather"]] = {}


@dataclass
class Weather:
    condition: str
    temperature_c: float
    is_rainy: bool
    is_cold: bool
    is_hot: bool
    tags: list[str]


_WEATHER_CODES: dict[int, str] = {
    0: "clear", 1: "clear", 2: "cloudy", 3: "cloudy",
    45: "foggy", 48: "foggy",
    51: "drizzle", 53: "drizzle", 55: "drizzle",
    61: "rainy", 63: "rainy", 65: "rainy",
    71: "snowy", 73: "snowy", 75: "snowy",
    80: "rainy", 81: "rainy", 82: "rainy",
    95: "stormy", 96: "stormy", 99: "stormy",
}


async def get_weather(location: str | None = None) -> Weather:
    if not location:
        return Weather(condition="unknown", temperature_c=20.0, is_rainy=False, is_cold=False, is_hot=False, tags=["mild"])

    cache_key = location.strip().lower()
    cached = _cache.get(cache_key)
    if cached and (time.monotonic() - cached[0]) < _CACHE_TTL_SECONDS:
        return cached[1]

    try:
        coords = await _geocode(location)
        if not coords:
            return _default_weather()

        async with httpx.AsyncClient(timeout=8) as client:
            resp = await client.get(FORECAST_URL, params={
                "latitude": coords[0],
                "longitude": coords[1],
                "current_weather": True,
            })
            resp.raise_for_status()
            data = resp.json()
            current = data.get("current_weather", {})
            temp = current.get("temperature", 20.0)
            code = current.get("weathercode", 0)

        condition = _WEATHER_CODES.get(code, "unknown")
        is_rainy = code in (51, 53, 55, 61, 63, 65, 80, 81, 82, 95, 96, 99)
        is_cold = temp < 10
        is_hot = temp > 30

        tags = [condition]
        if is_cold:
            tags.append("cold")
        elif is_hot:
            tags.append("hot")
        else:
            tags.append("mild")
        if is_rainy:
            tags.append("rainy")

        result = Weather(
            condition=condition,
            temperature_c=temp,
            is_rainy=is_rainy,
            is_cold=is_cold,
            is_hot=is_hot,
            tags=tags,
        )
        _cache[cache_key] = (time.monotonic(), result)
        return result
    except Exception as exc:
        logger.warning("Weather fetch failed for %s: %s", location, exc)
        return _default_weather()


def _default_weather() -> Weather:
    return Weather(condition="unknown", temperature_c=20.0, is_rainy=False, is_cold=False, is_hot=False, tags=["mild"])


async def _geocode(location: str) -> tuple[float, float] | None:
    try:
        async with httpx.AsyncClient(timeout=5) as client:
            resp = await client.get(
                "https://geocoding-api.open-meteo.com/v1/search",
                params={"name": location, "count": 1},
            )
            resp.raise_for_status()
            data = resp.json()
            results = data.get("results")
            if results:
                return results[0]["latitude"], results[0]["longitude"]
    except Exception as exc:
        logger.warning("Geocoding failed for %s: %s", location, exc)
    return None
