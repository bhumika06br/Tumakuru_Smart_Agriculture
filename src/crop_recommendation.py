
from pathlib import Path

import joblib
import pandas as pd

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data" / "raw"
MODEL_PATH = BASE_DIR / "models" / "crop_suitability_demo_model.joblib"

model = joblib.load(MODEL_PATH)

crops = pd.read_csv(DATA_DIR / "crop_master.csv")
rules = pd.read_csv(DATA_DIR / "crop_suitability.csv")


def recommend_crops(soil_type, season, ph, air_temp, air_humidity):
    results = []

    for _, crop in crops.iterrows():
        crop_id = str(crop["crop_id"])

        matching_rules = rules[
            (rules["crop_id"] == crop_id)
            & (rules["soil_type"] == soil_type)
            & (rules["season"] == season)
        ]

        if matching_rules.empty:
            results.append({
                "crop_id": crop_id,
                "status": "Insufficient data",
                "suitability_probability": None,
            })
            continue

        features = pd.DataFrame([{
            "crop_id": crop_id,
            "soil_type": soil_type,
            "season": season,
            "pH": ph,
            "air_temperature": air_temp,
            "air_humidity": air_humidity,
        }])

        probability = float(
            model.predict_proba(features)[0][1]
        )

        suitable = False
        incomplete_rule_found = False

        for _, rule in matching_rules.iterrows():

            required_columns = [
                "ph_min",
                "ph_max",
                "air_temp_min",
                "air_temp_max",
            ]

            if rule[required_columns].isna().any():
                incomplete_rule_found = True
                continue

            ph_valid = (
                rule["ph_min"] <= ph <= rule["ph_max"]
            )

            temp_valid = (
                rule["air_temp_min"]
                <= air_temp
                <= rule["air_temp_max"]
            )

            if not (ph_valid and temp_valid):
                continue

            humidity_min = rule["air_humidity_min"]
            humidity_max = rule["air_humidity_max"]

            if pd.isna(humidity_min) or pd.isna(humidity_max):
                incomplete_rule_found = True
                continue

            humidity_valid = (
                humidity_min
                <= air_humidity
                <= humidity_max
            )

            if humidity_valid:
                suitable = True
                break

        if suitable:
            status = "Suitable"
        elif incomplete_rule_found:
            status = "Insufficient data"
        else:
            status = "Not suitable"

        results.append({
            "crop_id": crop_id,
            "status": status,
            "suitability_probability": round(probability, 3),
        })

    return pd.DataFrame(results)
