import os
import requests
import logging

try:
    from livekit.agents import function_tool
except ImportError:
    def function_tool(func): 
        return func

logger = logging.getLogger(__name__)

def fetch_weather_wttr(city: str = "") -> str:
    url = f"https://wttr.in/{city}?format=j1" if city else "https://wttr.in/?format=j1"
    resp = requests.get(url, timeout=6)
    if resp.status_code == 200:
        data = resp.json()
        area = data.get("nearest_area", [{}])[0]
        detected_city = area.get("areaName", [{}])[0].get("value", city or "Current Location")
        country = area.get("country", [{}])[0].get("value", "")
        curr = data.get("current_condition", [{}])[0]
        condition = curr.get("weatherDesc", [{}])[0].get("value", "Clear").strip()
        temp = curr.get("temp_C", "N/A")
        humidity = curr.get("humidity", "N/A")
        wind = curr.get("windspeedKmph", "N/A")
        loc_str = f"{detected_city}, {country}" if country else detected_city
        return (
            f"Weather in {loc_str}:\n"
            f"- Condition: {condition}\n"
            f"- Temperature: {temp}\u00b0C\n"
            f"- Humidity: {humidity}%\n"
            f"- Wind Speed: {wind} km/h"
        )
    raise RuntimeError(f"wttr.in status {resp.status_code}")

def fetch_weather_openmeteo(city: str = "") -> str:
    target_city = city or "Dhaka"
    geo_url = f"https://geocoding-api.open-meteo.com/v1/search?name={target_city}&count=1"
    geo_res = requests.get(geo_url, timeout=5).json()
    if geo_res.get("results"):
        r0 = geo_res["results"][0]
        lat, lon = r0["latitude"], r0["longitude"]
        name = r0["name"]
        country = r0.get("country", "")
        w_url = f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&current_weather=true"
        w_res = requests.get(w_url, timeout=5).json()
        curr = w_res.get("current_weather", {})
        temp = curr.get("temperature", "N/A")
        wind = curr.get("windspeed", "N/A")
        loc_str = f"{name}, {country}" if country else name
        return f"Weather in {loc_str}: Temperature is {temp}\u00b0C with wind speed {wind} km/h."
    raise RuntimeError("Open-Meteo geocoding failed")

@function_tool()
async def get_weather(city: str = "") -> str:
    """
    Gives current live weather information for a given city or the user's current location.
    Use this tool whenever the user asks about weather, temperature, rain, or climate.
    If no city is mentioned, leave city empty to auto-detect current location.
    """
    import asyncio
    def _get():
        # 1. Try wttr.in (instant, free, worldwide)
        try:
            return fetch_weather_wttr(city.strip())
        except Exception as e:
            logger.warning(f"wttr.in failed: {e}")

        # 2. Try Open-Meteo (instant, free)
        try:
            return fetch_weather_openmeteo(city.strip())
        except Exception as e:
            logger.warning(f"Open-Meteo failed: {e}")

        # 3. Fallback OpenWeatherMap if key is set
        api_key = os.getenv("OPENWEATHER_API_KEY")
        if api_key:
            try:
                c = city or "Ishwardi"
                url = "https://api.openweathermap.org/data/2.5/weather"
                params = {"q": c, "appid": api_key, "units": "metric"}
                res = requests.get(url, params=params, timeout=5).json()
                cond = res["weather"][0]["description"].title()
                temp = res["main"]["temp"]
                return f"Weather in {c}: {cond}, {temp}\u00b0C."
            except Exception:
                pass

        return f"Could not fetch weather right now for {city or 'your location'}. Please try again shortly."

    return await asyncio.to_thread(_get)
