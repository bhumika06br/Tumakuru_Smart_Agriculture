
from pathlib import Path
import pandas as pd

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data" / "raw"

organic = pd.read_csv(DATA_DIR / "organic_fertilizers.csv")
chemical = pd.read_csv(DATA_DIR / "chemical_fertilizers.csv")
requirements = pd.read_csv(DATA_DIR / "crop_nutrient_requirements.csv")

ORGANIC_COLUMNS = {
    "N": "n_percent",
    "P": "p_percent",
    "K": "k_percent"
}

CHEMICAL_COLUMNS = {
    "N": "n_percent",
    "P": "p2o5_percent",
    "K": "k2o_percent"
}


def get_nutrient_target(crop_id, nutrient, land_area_ha, plant_count=None):
    rows = requirements[
        (requirements["crop_id"] == crop_id)
        & (requirements["nutrient"] == nutrient)
    ]

    if rows.empty:
        return None

    row = rows.iloc[0]
    rate = float(row["recommended_quantity"])
    unit = str(row["quantity_unit"]).strip().lower()

    if unit == "kg/ha":
        return rate * land_area_ha

    if unit in ("g/palm/year", "g/plant/cycle"):
        if plant_count is None:
            return None
        return rate * plant_count / 1000

    return None


def get_fertilizer_recommendations(
    crop_id, deficient_nutrients, land_area_ha, plant_count=None
):
    results = []

    for nutrient in deficient_nutrients:

        target_kg = get_nutrient_target(
            crop_id, nutrient, land_area_ha, plant_count
        )

        if target_kg is None:
            continue

        for _, fert in organic.iterrows():
            percent = float(fert[ORGANIC_COLUMNS[nutrient]])

            if percent <= 0:
                continue

            quantity = target_kg / (percent / 100)

            results.append({
                "crop_id": crop_id,
                "nutrient": nutrient,
                "fertilizer_type": "Organic",
                "fertilizer_name": fert["fertilizer_name"],
                "quantity_kg": round(quantity, 2),
                "calculation": "Nutrient-equivalent demonstration"
            })

        for _, fert in chemical.iterrows():
            percent = float(fert[CHEMICAL_COLUMNS[nutrient]])

            if percent <= 0:
                continue

            quantity = target_kg / (percent / 100)

            results.append({
                "crop_id": crop_id,
                "nutrient": nutrient,
                "fertilizer_type": "Chemical",
                "fertilizer_name": fert["fertilizer_name"],
                "quantity_kg": round(quantity, 2),
                "calculation": "Nutrient-equivalent demonstration"
            })

    return pd.DataFrame(results)
