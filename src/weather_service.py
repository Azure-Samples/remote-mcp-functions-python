"""Weather service for fetching weather data from Open-Meteo API."""
import logging
from typing import Dict, Any, Optional, Tuple
from datetime import datetime
import urllib.request
import urllib.parse
import json


def normalize_location(location: str) -> str:
    """Normalize location input, defaulting to Seattle, WA if empty."""
    return "Seattle, WA" if not location or location.strip() == "" else location.strip()


def map_weather_code(code: int) -> str:
    """Map WMO weather code to condition string."""
    weather_codes = {
        0: "Clear sky",
        1: "Mainly clear",
        2: "Partly cloudy",
        3: "Overcast",
        45: "Fog",
        48: "Fog",
        51: "Drizzle",
        53: "Drizzle",
        55: "Drizzle",
        56: "Freezing drizzle",
        57: "Freezing drizzle",
        61: "Rain",
        63: "Rain",
        65: "Rain",
        66: "Freezing rain",
        67: "Freezing rain",
        71: "Snowfall",
        73: "Snowfall",
        75: "Snowfall",
        77: "Snow grains",
        80: "Rain showers",
        81: "Rain showers",
        82: "Rain showers",
        85: "Snow showers",
        86: "Snow showers",
        95: "Thunderstorm",
        96: "Thunderstorm with hail",
        99: "Thunderstorm with hail",
    }
    return weather_codes.get(code, "Unknown")


def deg_to_cardinal(deg: float) -> str:
    """Convert degrees to cardinal direction."""
    dirs = ["N", "NNE", "NE", "ENE", "E", "ESE", "SE", "SSE", "S", "SSW", "SW", "WSW", "W", "WNW", "NW", "NNW"]
    return dirs[round(((deg % 360) / 22.5)) % 16]


def parse_observation(props: Dict[str, Any], location: str) -> Dict[str, Any]:
    """Parse observation data to WeatherResult."""
    temp_c = props.get("temperature_2m")
    temp_f = round(temp_c * 1.8 + 32) if temp_c is not None else None
    
    weather_code = props.get("weather_code")
    condition = map_weather_code(weather_code) if isinstance(weather_code, (int, float)) else "Unknown"
    
    humidity = props.get("relative_humidity_2m")
    humidity_percent = round(humidity) if humidity is not None else None
    
    wind_speed = props.get("wind_speed_10m")
    wind_kph = round(wind_speed) if wind_speed is not None else None
    
    wind_dir_deg = props.get("wind_direction_10m")
    wind_dir = f" {deg_to_cardinal(wind_dir_deg)}" if wind_dir_deg is not None else ""
    
    reported_time = props.get("time")
    if isinstance(reported_time, str):
        try:
            dt = datetime.fromisoformat(reported_time.replace("Z", "+00:00"))
            reported_at_utc = dt.strftime("%Y-%m-%d %H:%M:%S") + "Z"
        except:
            reported_at_utc = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S") + "Z"
    else:
        reported_at_utc = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S") + "Z"
    
    return {
        "Location": location,
        "Condition": condition,
        "TemperatureC": round(temp_c) if temp_c is not None else None,
        "TemperatureF": temp_f,
        "HumidityPercent": humidity_percent,
        "WindKph": wind_kph,
        "Wind": f"{wind_kph} km/h{wind_dir}" if wind_kph is not None else "—",
        "ReportedAtUtc": reported_at_utc,
        "Source": "open-meteo"
    }


class WeatherService:
    """
    WeatherService class for fetching weather data from Open-Meteo API.
    Matches the TypeScript WeatherService implementation.
    """
    
    def get_current_weather(self, location: str) -> Dict[str, Any]:
        """
        Get current weather for a location.
        
        Args:
            location: City name, address, or zip code
            
        Returns:
            WeatherResult on success, WeatherError on failure
        """
        normalized = normalize_location(location)
        
        coords = self._geocode(normalized)
        if not coords:
            return {
                "Location": normalized,
                "Error": "Could not find this location. Try a city, address, or zip code.",
                "Source": "open-meteo"
            }
        
        lat, lon, canonical = coords
        
        observation = self._get_latest_observation(lat, lon)
        if not observation:
            return {
                "Location": canonical,
                "Error": "Could not retrieve current observations.",
                "Source": "open-meteo"
            }
        
        return parse_observation(observation, canonical)
    
    def _geocode(self, location: str) -> Optional[Tuple[float, float, str]]:
        """
        Geocode a location string to coordinates.
        
        Args:
            location: City name
            
        Returns:
            Tuple of (latitude, longitude, canonical_name) or None if not found
        """
        try:
            encoded = urllib.parse.quote(location)
            url = f"https://geocoding-api.open-meteo.com/v1/search?name={encoded}&count=1&language=en&format=json"
            
            with urllib.request.urlopen(url) as response:
                data = json.loads(response.read().decode())
                results = data.get("results", [])
                
                if not results:
                    return None
                
                match = results[0]
                lat = match["latitude"]
                lon = match["longitude"]
                name = match.get("name", location)
                admin1 = match.get("admin1")
                country = match.get("country")
                
                # Build canonical name
                canonical_parts = [name, admin1, country]
                canonical = ", ".join([s for s in canonical_parts if s and s.strip()])
                
                return (lat, lon, canonical if canonical else location)
                
        except Exception as e:
            logging.error(f"Error geocoding location {location}: {str(e)}")
            return None
    
    def _get_latest_observation(self, lat: float, lon: float) -> Optional[Dict[str, Any]]:
        """
        Get latest observation from Open-Meteo.
        
        Args:
            lat: Latitude coordinate
            lon: Longitude coordinate
            
        Returns:
            Dict with current weather data, or None if request failed
        """
        try:
            url = f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&current=temperature_2m,relative_humidity_2m,wind_speed_10m,wind_direction_10m,weather_code"
            
            with urllib.request.urlopen(url) as response:
                data = json.loads(response.read().decode())
                return data.get("current")
                
        except Exception as e:
            logging.error(f"Error fetching weather data: {str(e)}")
            return None


# Default instance for convenience
weather_service = WeatherService()

