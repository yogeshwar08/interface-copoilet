import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.tools.weather import weather_tool


def main():

    print("=" * 60)
    print("WEATHER TOOL TEST")
    print("=" * 60)

    # Delhi coordinates
    latitude = 28.6139
    longitude = 77.2090

    result = weather_tool.run(
        latitude=latitude,
        longitude=longitude,
    )

    print("\nTool:")
    print(result["tool"])

    print("\nCoordinates:")
    print(
        result["latitude"],
        result["longitude"],
    )

    print("\nTime:")
    print(result["time"])

    print("\nTemperature:")
    print(
        f"{result['temperature_c']} °C"
    )

    print("\nFeels Like:")
    print(
        f"{result['apparent_temperature_c']} °C"
    )

    print("\nHumidity:")
    print(
        f"{result['relative_humidity_percent']}%"
    )

    print("\nWind:")
    print(
        f"{result['wind_speed_kmh']} km/h"
    )

    print("\nPrecipitation:")
    print(
        f"{result['precipitation_mm']} mm"
    )

    print("\nWeather Code:")
    print(
        result["weather_code"]
    )

    print("\nTimezone:")
    print(
        result["timezone"]
    )

    print("\n" + "=" * 60)
    print("WEATHER TOOL TEST PASSED")
    print("=" * 60)


if __name__ == "__main__":
    main()