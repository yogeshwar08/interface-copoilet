from app.tools.weather import weather_tool


def main():

    print("=" * 60)
    print("WEATHER TOOL SECURITY TEST")
    print("=" * 60)

    # ========================================================
    # INVALID LATITUDE
    # ========================================================

    try:

        weather_tool.run(
            latitude=200,
            longitude=77.2,
        )

        raise AssertionError(
            "Invalid latitude was accepted!"
        )

    except ValueError as exc:

        print("\nInvalid latitude:")
        print("BLOCKED")
        print(f"Reason: {exc}")

    # ========================================================
    # INVALID LONGITUDE
    # ========================================================

    try:

        weather_tool.run(
            latitude=28.6,
            longitude=300,
        )

        raise AssertionError(
            "Invalid longitude was accepted!"
        )

    except ValueError as exc:

        print("\nInvalid longitude:")
        print("BLOCKED")
        print(f"Reason: {exc}")

    # ========================================================
    # VALID COORDINATES
    # ========================================================

    result = weather_tool.run(
        latitude=28.6139,
        longitude=77.2090,
    )

    assert result["tool"] == "weather"

    print("\nValid coordinates:")
    print("ALLOWED")

    print("\n" + "=" * 60)
    print("WEATHER SECURITY TEST PASSED")
    print("=" * 60)


if __name__ == "__main__":
    main()