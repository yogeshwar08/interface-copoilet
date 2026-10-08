import time
import httpx

# ============================================================
# Weather Tool — Dual-backend implementation
# ============================================================
# PRIMARY:  OpenWeatherMap "Current Weather Data" API
#           - Requires OPENWEATHERMAP_API_KEY env var
#           - Free tier: 60 calls/min, 1 M calls/month — no IP rate-limiting
#           - Sign up: https://openweathermap.org/api
#
# FALLBACK: Open-Meteo (keyless, completely free)
#           - May be temporarily rate-limited (429) on shared server IPs
#           - Used automatically when OPENWEATHERMAP_API_KEY is not set
# ============================================================

OWM_URL = "https://api.openweathermap.org/data/2.5/weather"
OPEN_METEO_URL = "https://api.open-meteo.com/v1/forecast"

_MAX_RETRIES = 3
_BASE_BACKOFF_S = 1.5


def _get_owm_key() -> str | None:
    """Lazy-load the OWM API key from app settings to avoid circular imports."""
    try:
        from app.config import settings
        return settings.openweathermap_api_key or None
    except Exception:
        return None


class WeatherTool:

    name = "weather"

    description = (
        "Get current weather information for a geographic "
        "location using latitude and longitude."
    )

    def run(
        self,
        latitude: float,
        longitude: float,
    ) -> dict:

        # ====================================================
        # INPUT VALIDATION
        # ====================================================

        if not -90 <= latitude <= 90:
            raise ValueError("Latitude must be between -90 and 90.")

        if not -180 <= longitude <= 180:
            raise ValueError("Longitude must be between -180 and 180.")

        owm_key = _get_owm_key()
        if owm_key:
            return self._run_openweathermap(latitude, longitude, owm_key)
        else:
            return self._run_open_meteo(latitude, longitude)

    # ----------------------------------------------------------
    # Backend 1: OpenWeatherMap (key-based, preferred on Render)
    # ----------------------------------------------------------

    def _run_openweathermap(self, latitude: float, longitude: float, api_key: str) -> dict:
        params = {
            "lat": latitude,
            "lon": longitude,
            "appid": api_key,
            "units": "metric",   # °C, km/h
        }

        last_exc = None
        for attempt in range(1, _MAX_RETRIES + 1):
            try:
                response = httpx.get(OWM_URL, params=params, timeout=10.0)

                if response.status_code == 401:
                    raise RuntimeError(
                        "OpenWeatherMap API key is invalid or not yet activated. "
                        "Keys can take up to 2 hours to activate after sign-up."
                    )

                if response.status_code == 429:
                    retry_after = float(response.headers.get("Retry-After", _BASE_BACKOFF_S * attempt))
                    if attempt < _MAX_RETRIES:
                        time.sleep(min(retry_after, 5.0))
                        continue
                    raise RuntimeError(
                        "OpenWeatherMap rate limit reached. Please try again shortly."
                    )

                response.raise_for_status()
                data = response.json()
                break

            except httpx.HTTPStatusError as exc:
                last_exc = exc
                if attempt < _MAX_RETRIES and exc.response.status_code >= 500:
                    time.sleep(_BASE_BACKOFF_S * attempt)
                    continue
                raise RuntimeError(f"OpenWeatherMap request failed: {exc}") from exc

            except httpx.HTTPError as exc:
                last_exc = exc
                if attempt < _MAX_RETRIES:
                    time.sleep(_BASE_BACKOFF_S * attempt)
                    continue
                raise RuntimeError(f"OpenWeatherMap request failed: {exc}") from exc
        else:
            raise RuntimeError(
                f"OpenWeatherMap unavailable after {_MAX_RETRIES} attempts. "
                f"Last error: {last_exc}"
            )

        # Normalise OWM response → standard dict
        main = data.get("main", {})
        wind = data.get("wind", {})
        rain = data.get("rain", {})
        snow = data.get("snow", {})
        weather_arr = data.get("weather", [{}])

        return {
            "tool": self.name,
            "backend": "openweathermap",
            "latitude": latitude,
            "longitude": longitude,
            "time": None,                             # OWM doesn't return ISO time directly
            "temperature_c": main.get("temp"),
            "apparent_temperature_c": main.get("feels_like"),
            "relative_humidity_percent": main.get("humidity"),
            "precipitation_mm": rain.get("1h", snow.get("1h", 0.0)),
            "wind_speed_kmh": round((wind.get("speed", 0)) * 3.6, 1),  # m/s → km/h
            "weather_code": weather_arr[0].get("id"),
            "weather_description": weather_arr[0].get("description", "").title(),
            "timezone": data.get("timezone"),
            "city": data.get("name", ""),
        }

    # ----------------------------------------------------------
    # Backend 2: Open-Meteo (keyless fallback)
    # ----------------------------------------------------------

    def _run_open_meteo(self, latitude: float, longitude: float) -> dict:
        params = {
            "latitude": latitude,
            "longitude": longitude,
            "current": (
                "temperature_2m,"
                "relative_humidity_2m,"
                "apparent_temperature,"
                "precipitation,"
                "weather_code,"
                "wind_speed_10m"
            ),
            "timezone": "auto",
        }

        last_exc = None
        for attempt in range(1, _MAX_RETRIES + 1):
            try:
                response = httpx.get(OPEN_METEO_URL, params=params, timeout=10.0)

                if response.status_code == 429:
                    retry_after = float(response.headers.get("Retry-After", _BASE_BACKOFF_S * attempt))
                    if attempt < _MAX_RETRIES:
                        time.sleep(min(retry_after, 5.0))
                        continue
                    raise RuntimeError(
                        "Weather service is temporarily rate-limited on this server. "
                        "Set OPENWEATHERMAP_API_KEY in Render environment variables to use "
                        "the key-based weather backend which is not rate-limited."
                    )

                response.raise_for_status()
                data = response.json()
                break

            except httpx.HTTPStatusError as exc:
                last_exc = exc
                if attempt < _MAX_RETRIES and exc.response.status_code >= 500:
                    time.sleep(_BASE_BACKOFF_S * attempt)
                    continue
                raise RuntimeError(f"Weather API request failed: {exc}") from exc

            except httpx.HTTPError as exc:
                last_exc = exc
                if attempt < _MAX_RETRIES:
                    time.sleep(_BASE_BACKOFF_S * attempt)
                    continue
                raise RuntimeError(f"Weather API request failed: {exc}") from exc
        else:
            raise RuntimeError(
                f"Weather API unavailable after {_MAX_RETRIES} attempts. "
                f"Last error: {last_exc}"
            )

        if "current" not in data:
            raise RuntimeError("Weather API returned an unexpected response.")

        current = data["current"]

        return {
            "tool": self.name,
            "backend": "open-meteo",
            "latitude": latitude,
            "longitude": longitude,
            "time": current.get("time"),
            "temperature_c": current.get("temperature_2m"),
            "apparent_temperature_c": current.get("apparent_temperature"),
            "relative_humidity_percent": current.get("relative_humidity_2m"),
            "precipitation_mm": current.get("precipitation"),
            "wind_speed_kmh": current.get("wind_speed_10m"),
            "weather_code": current.get("weather_code"),
            "weather_description": None,
            "timezone": data.get("timezone"),
            "city": "",
        }


weather_tool = WeatherTool()