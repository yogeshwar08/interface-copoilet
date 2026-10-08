import time
import httpx


OPEN_METEO_URL = "https://api.open-meteo.com/v1/forecast"

# Open-Meteo free tier: max 10,000 req/day, bursts rate-limited with 429.
# Use a simple retry with exponential backoff.
_MAX_RETRIES = 3
_BASE_BACKOFF_S = 1.5


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

        # ====================================================
        # API PARAMETERS
        # ====================================================

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

        # ====================================================
        # API REQUEST — with retry on 429 rate-limit
        # ====================================================

        last_exc = None
        for attempt in range(1, _MAX_RETRIES + 1):
            try:
                response = httpx.get(
                    OPEN_METEO_URL,
                    params=params,
                    timeout=10.0,
                )

                # Explicit 429 handling — back off and retry
                if response.status_code == 429:
                    retry_after = float(response.headers.get("Retry-After", _BASE_BACKOFF_S * attempt))
                    if attempt < _MAX_RETRIES:
                        time.sleep(min(retry_after, 5.0))
                        continue
                    raise RuntimeError(
                        "Weather service is temporarily rate-limited. "
                        "Please try again in a few seconds."
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

        # ====================================================
        # RESPONSE VALIDATION
        # ====================================================

        if "current" not in data:
            raise RuntimeError("Weather API returned an unexpected response.")

        current = data["current"]

        # ====================================================
        # NORMALIZED TOOL RESPONSE
        # ====================================================

        return {
            "tool": self.name,
            "latitude": latitude,
            "longitude": longitude,
            "time": current.get("time"),
            "temperature_c": current.get("temperature_2m"),
            "apparent_temperature_c": current.get("apparent_temperature"),
            "relative_humidity_percent": current.get("relative_humidity_2m"),
            "precipitation_mm": current.get("precipitation"),
            "wind_speed_kmh": current.get("wind_speed_10m"),
            "weather_code": current.get("weather_code"),
            "timezone": data.get("timezone"),
        }


weather_tool = WeatherTool()