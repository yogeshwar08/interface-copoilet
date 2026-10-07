import httpx


OPEN_METEO_URL = "https://api.open-meteo.com/v1/forecast"


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
            raise ValueError(
                "Latitude must be between -90 and 90."
            )

        if not -180 <= longitude <= 180:
            raise ValueError(
                "Longitude must be between -180 and 180."
            )

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
        # API REQUEST
        # ====================================================

        try:

            response = httpx.get(
                OPEN_METEO_URL,
                params=params,
                timeout=10.0,
            )

            response.raise_for_status()

            data = response.json()

        except httpx.HTTPError as exc:

            raise RuntimeError(
                f"Weather API request failed: {exc}"
            ) from exc

        # ====================================================
        # RESPONSE VALIDATION
        # ====================================================

        if "current" not in data:

            raise RuntimeError(
                "Weather API returned an unexpected response."
            )

        current = data["current"]

        # ====================================================
        # NORMALIZED TOOL RESPONSE
        # ====================================================

        return {
            "tool": self.name,
            "latitude": latitude,
            "longitude": longitude,
            "time": current.get("time"),
            "temperature_c": current.get(
                "temperature_2m"
            ),
            "apparent_temperature_c": current.get(
                "apparent_temperature"
            ),
            "relative_humidity_percent": current.get(
                "relative_humidity_2m"
            ),
            "precipitation_mm": current.get(
                "precipitation"
            ),
            "wind_speed_kmh": current.get(
                "wind_speed_10m"
            ),
            "weather_code": current.get(
                "weather_code"
            ),
            "timezone": data.get("timezone"),
        }


weather_tool = WeatherTool()