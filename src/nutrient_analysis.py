
from pathlib import Path
import math

import pandas as pd

BASE_DIR = Path(__file__).resolve().parent.parent

THRESHOLD_FILE = (
    BASE_DIR
    / "data"
    / "raw"
    / "soil_nutrient_thresholds.csv"
)

thresholds = pd.read_csv(THRESHOLD_FILE)


def analyze_nutrients(crop_id, n, p, k):
    """
    Demonstration-only nutrient screening.

    Thresholds are provisional laboratory-method
    reference values, not crop-specific or validated
    NPK sensor thresholds.
    """

    readings = {
        "N": n,
        "P": p,
        "K": k,
    }

    results = []

    for nutrient, value in readings.items():

        if (
            isinstance(value, bool)
            or not isinstance(value, (int, float))
            or not math.isfinite(value)
            or value < 0
        ):
            results.append({
                "nutrient": nutrient,
                "reading": value,
                "status": "Unknown",
            })
            continue

        matched = thresholds[
            (thresholds["crop_id"] == crop_id)
            & (thresholds["nutrient"] == nutrient)
        ]

        if len(matched) != 1:
            results.append({
                "nutrient": nutrient,
                "reading": value,
                "status": "Unknown",
            })
            continue

        row = matched.iloc[0]

        if (
            row["unit"] != "mg/kg"
            or pd.isna(row["low_threshold"])
            or pd.isna(row["high_threshold"])
        ):
            results.append({
                "nutrient": nutrient,
                "reading": value,
                "status": "Unknown",
            })
            continue

        low = float(row["low_threshold"])
        high = float(row["high_threshold"])

        if (
            not math.isfinite(low)
            or not math.isfinite(high)
            or low < 0
            or high < low
        ):
            results.append({
                "nutrient": nutrient,
                "reading": value,
                "status": "Unknown",
            })
            continue

        if value < low:
            status = "Below reference range"

        elif value <= high:
            status = "Within reference range"

        else:
            status = "Above reference range"

        results.append({
            "nutrient": nutrient,
            "reading": value,
            "status": status,
        })

    return results


def categorize_crop(crop_id, n, p, k):

    analysis = analyze_nutrients(crop_id, n, p, k)

    if any(
        item["status"] == "Unknown"
        for item in analysis
    ):
        return "Insufficient nutrient data", analysis

    if any(
        item["status"] == "Below reference range"
        for item in analysis
    ):
        return (
            "Suitable with nutrient supplementation",
            analysis,
        )

    return (
        "Suitable without major nutrient supplementation",
        analysis,
    )
