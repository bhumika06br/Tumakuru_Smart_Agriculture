
import math
from numbers import Real


PER_PLANT_CROPS = {"C01", "C02", "C05"}

VALID_WORKFLOWS = {
    "Crop Not Planted",
    "Crop Already Planted",
}

VALID_SOIL_TYPES = {
    "Red loamy soils",
    "Red sandy loam soils",
    "Sandy clay loam soils",
    "Loamy soils",
    "Sandy soils",
}

VALID_SEASONS = {
    "Summer",
    "Monsoon",
    "Post-monsoon",
    "Winter",
}


def is_valid_number(value):
    """Accept finite numeric values, excluding booleans."""
    return (
        isinstance(value, Real)
        and not isinstance(value, bool)
        and math.isfinite(float(value))
    )


def validate_number(name, value, minimum, maximum):
    """Return an error message if a numeric value is invalid."""

    if not is_valid_number(value):
        return f"{name} must be a valid number."

    if value < minimum or value > maximum:
        return (
            f"{name} must be between "
            f"{minimum} and {maximum}."
        )

    return None


def validate_request(request, valid_crop_ids=None):
    """
    Validate farmer inputs before generating or saving
    recommendations.

    Returns:
        errors: list of blocking error messages
        warnings: list of non-blocking warnings
    """

    errors = []
    warnings = []

    if not isinstance(request, dict):
        return ["Invalid recommendation request."], []

    workflow = request.get("workflow")

    if workflow not in VALID_WORKFLOWS:
        errors.append("Please select a valid farming situation.")

    # ----------------------------------------
    # LAND AREA
    # ----------------------------------------

    area = request.get("area")

    error = validate_number(
        "Land area (hectares)",
        area,
        0.0001,
        100000,
    )

    if error:
        errors.append(error)

    # ----------------------------------------
    # NPK MEASUREMENTS
    # ----------------------------------------

    nutrients = [
        ("Nitrogen", "n"),
        ("Phosphorus", "p"),
        ("Potassium", "k"),
    ]

    for nutrient_name, key in nutrients:

        value = request.get(key)

        error = validate_number(
            f"{nutrient_name} (mg/kg)",
            value,
            0,
            1000000,
        )

        if error:
            errors.append(error)

        elif value > 10000:
            warnings.append(
                f"{nutrient_name} is unusually high. "
                "Verify the measurement and units."
            )

    # ----------------------------------------
    # SOIL pH
    # ----------------------------------------

    ph = request.get("ph")

    error = validate_number(
        "Soil pH",
        ph,
        0,
        14,
    )

    if error:
        errors.append(error)

    elif ph < 3 or ph > 10:
        warnings.append(
            "Soil pH is outside the usual agricultural "
            "range. Verify the measurement."
        )

    # ----------------------------------------
    # AIR TEMPERATURE
    # ----------------------------------------

    temperature = request.get("temp")

    error = validate_number(
        "Air temperature (°C)",
        temperature,
        -40,
        80,
    )

    if error:
        errors.append(error)

    elif temperature < 5 or temperature > 45:
        warnings.append(
            "Air temperature is unusual for many "
            "crop-growing conditions. Verify the reading."
        )

    # ----------------------------------------
    # AIR HUMIDITY
    # ----------------------------------------

    humidity = request.get("humidity")

    error = validate_number(
        "Air relative humidity (%)",
        humidity,
        0,
        100,
    )

    if error:
        errors.append(error)

    # ----------------------------------------
    # CROP NOT PLANTED
    # ----------------------------------------

    if workflow == "Crop Not Planted":

        soil_type = request.get("soil")
        season = request.get("season")

        if soil_type not in VALID_SOIL_TYPES:
            errors.append("Please select a valid soil type.")

        if season not in VALID_SEASONS:
            errors.append("Please select a valid season.")

    # ----------------------------------------
    # CROP ALREADY PLANTED
    # ----------------------------------------

    elif workflow == "Crop Already Planted":

        crop_id = request.get("crop")

        if not isinstance(crop_id, str) or not crop_id:
            errors.append("Please select a planted crop.")

        elif (
            valid_crop_ids is not None
            and crop_id not in valid_crop_ids
        ):
            errors.append(
                "The selected crop is not supported."
            )

        if crop_id in PER_PLANT_CROPS:

            plants = request.get("plants")

            if (
                not is_valid_number(plants)
                or not float(plants).is_integer()
                or plants < 1
            ):
                errors.append(
                    "Plant count must be a positive integer."
                )

    # ----------------------------------------
    # MEASUREMENT SOURCE
    # ----------------------------------------

    source = request.get(
        "measurement_source",
        "manual",
    )

    if source not in {"manual", "ESP32"}:
        errors.append("Invalid measurement source.")

    return errors, warnings
