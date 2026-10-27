
from pathlib import Path
import math

import numpy as np
import pandas as pd
from scipy.optimize import lsq_linear


BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data" / "raw"

chemical = pd.read_csv(
    DATA_DIR / "chemical_fertilizers.csv"
)

requirements = pd.read_csv(
    DATA_DIR / "crop_nutrient_requirements.csv"
)

NUTRIENTS = ["N", "P", "K"]

CHEMICAL_COLUMNS = {
    "N": "n_percent",
    "P": "p2o5_percent",
    "K": "k2o_percent",
}

NUTRIENT_LABELS = {
    "N": "N",
    "P": "P2O5",
    "K": "K2O",
}

SUPPORTED_UNITS = {
    "kg/ha",
    "g/palm/year",
    "g/plant/cycle",
}


# ============================================
# 1. VALIDATION HELPERS
# ============================================

def valid_number(value, minimum=None, maximum=None):
    if isinstance(value, (bool, np.bool_)):
        return False

    try:
        number = float(value)
    except (TypeError, ValueError, OverflowError):
        return False

    if not math.isfinite(number):
        return False

    if minimum is not None and number < minimum:
        return False

    if maximum is not None and number > maximum:
        return False

    return True


def validate_area(land_area_ha):
    if not valid_number(land_area_ha, minimum=0.0001):
        raise ValueError(
            "Land area must be a positive finite "
            "number in hectares."
        )


def validate_plant_count(plant_count):
    if (
        not valid_number(plant_count, minimum=1)
        or not float(plant_count).is_integer()
    ):
        raise ValueError(
            "Plant count must be a positive integer."
        )


# ============================================
# 2. CALCULATE PROVISIONAL TARGETS
# ============================================

def calculate_targets(
    crop_id,
    land_area_ha,
    plant_count=None,
):
    """
    Calculate provisional nutrient reference targets.

    N is expressed as kg N.
    P is expressed as kg P2O5.
    K is expressed as kg K2O.

    These are not soil-test-adjusted fertilizer doses.
    """

    validate_area(land_area_ha)

    crop_rows = requirements[
        requirements["crop_id"].astype(str) == str(crop_id)
    ]

    if crop_rows.empty:
        raise ValueError(
            f"No nutrient requirements found for crop {crop_id}."
        )

    if (
        crop_rows["nutrient"].isna().any()
        or crop_rows["nutrient"].duplicated().any()
        or set(crop_rows["nutrient"]) != set(NUTRIENTS)
        or len(crop_rows) != 3
    ):
        raise ValueError(
            "Crop must have exactly one valid requirement "
            "record for each of N, P and K."
        )

    targets = {}

    for _, row in crop_rows.iterrows():

        nutrient = row["nutrient"]

        rate = row["recommended_quantity"]

        unit = str(
            row["quantity_unit"]
        ).strip().lower()

        if not valid_number(rate, minimum=0):
            raise ValueError(
                f"Invalid {nutrient} requirement for {crop_id}."
            )

        rate = float(rate)

        if unit not in SUPPORTED_UNITS:
            raise ValueError(
                f"Unsupported requirement unit: {unit}"
            )

        if unit == "kg/ha":

            target = rate * float(land_area_ha)

        else:

            validate_plant_count(plant_count)

            target = (
                rate * float(plant_count) / 1000.0
            )

        if not math.isfinite(target):
            raise ValueError(
                "Calculated nutrient target is not finite."
            )

        targets[nutrient] = target

    return targets


# ============================================
# 3. VALIDATE SELECTED FERTILIZERS
# ============================================

def get_selected_fertilizers(selected_fertilizers):

    if not isinstance(
        selected_fertilizers,
        (list, tuple),
    ):
        raise ValueError(
            "Selected fertilizers must be a list."
        )

    if not selected_fertilizers:
        raise ValueError(
            "Select at least one fertilizer."
        )

    if (
        any(
            not isinstance(name, str) or not name.strip()
            for name in selected_fertilizers
        )
        or len(selected_fertilizers)
        != len(set(selected_fertilizers))
    ):
        raise ValueError(
            "Invalid or duplicate fertilizer selection."
        )

    selected = chemical[
        chemical["fertilizer_name"].isin(
            selected_fertilizers
        )
    ].copy()

    if (
        len(selected) != len(selected_fertilizers)
        or selected["fertilizer_name"].duplicated().any()
    ):
        raise ValueError(
            "Unknown or duplicate fertilizer records."
        )

    # Preserve the order chosen by the farmer.
    selected = (
        selected
        .set_index("fertilizer_name")
        .loc[selected_fertilizers]
        .reset_index()
    )

    for _, row in selected.iterrows():

        percentages = []

        for nutrient in NUTRIENTS:

            column = CHEMICAL_COLUMNS[nutrient]
            value = row[column]

            if not valid_number(
                value,
                minimum=0,
                maximum=100,
            ):
                raise ValueError(
                    "Invalid nutrient percentage for "
                    f"{row['fertilizer_name']}."
                )

            percentages.append(float(value))

        if all(value == 0 for value in percentages):
            raise ValueError(
                f"{row['fertilizer_name']} has no "
                "usable nutrient content."
            )

    return selected


# ============================================
# 4. OPTIMIZE CHEMICAL FERTILIZERS
# ============================================

def optimize_chemical_fertilizers(
    crop_id,
    selected_fertilizers,
    deficient_nutrients,
    land_area_ha,
    plant_count=None,
    tolerance_percent=10,
):
    """
    Calculate illustrative chemical fertilizer quantities.

    Only nutrients flagged below the provisional reference
    range receive nonzero targets.

    The optimizer minimizes weighted nutrient differences.
    It does not guarantee that all targets can be met.

    All contributions from each selected fertilizer
    are included in the nutrient balance.
    """

    if not valid_number(
        tolerance_percent,
        minimum=0,
        maximum=100,
    ):
        raise ValueError(
            "Tolerance percentage must be between 0 and 100."
        )

    if not isinstance(
        deficient_nutrients,
        (list, tuple, set),
    ):
        raise ValueError(
            "Deficient nutrients must be a collection."
        )

    deficient = set(deficient_nutrients)

    if not deficient.issubset(set(NUTRIENTS)):
        raise ValueError(
            "Deficient nutrients must contain only N, P or K."
        )

    if not deficient:
        raise ValueError(
            "No nutrients were flagged below "
            "the provisional reference range."
        )

    targets = calculate_targets(
        crop_id,
        land_area_ha,
        plant_count,
    )

    selected = get_selected_fertilizers(
        selected_fertilizers
    )

    # N / P2O5 / K2O target vector.
    target_vector = np.array(
        [
            targets[nutrient]
            if nutrient in deficient
            else 0.0
            for nutrient in NUTRIENTS
        ],
        dtype=float,
    )

    if not np.isfinite(target_vector).all():
        raise ValueError(
            "Invalid nutrient target values."
        )

    if not np.any(target_vector > 0):
        raise ValueError(
            "All selected nutrient targets are zero."
        )

    # Rows: N, P2O5, K2O.
    # Columns: selected fertilizers.
    matrix = np.array(
        [
            [
                float(
                    row[CHEMICAL_COLUMNS[nutrient]]
                ) / 100.0
                for row in selected.to_dict("records")
            ]
            for nutrient in NUTRIENTS
        ],
        dtype=float,
    )

    # Do not attempt a plan if no selected fertilizer
    # can supply any of the requested nutrients.
    required_indices = [
        index
        for index, nutrient in enumerate(NUTRIENTS)
        if nutrient in deficient
        and target_vector[index] > 0
    ]

    if not any(
        np.any(matrix[index, :] > 0)
        for index in required_indices
    ):
        raise ValueError(
            "Selected fertilizers cannot supply "
            "the nutrients requiring supplementation."
        )

    # A higher weight discourages supplying nutrients
    # that were not flagged below the reference range.
    # This is a penalty, not a strict upper bound.
    weights = np.array(
        [
            1.0 if nutrient in deficient else 3.0
            for nutrient in NUTRIENTS
        ],
        dtype=float,
    )

    weighted_matrix = (
        matrix * weights[:, None]
    )

    weighted_target = (
        target_vector * weights
    )

    solution = lsq_linear(
        weighted_matrix,
        weighted_target,
        bounds=(0, np.inf),
    )

    if not solution.success:
        raise ValueError(
            "Fertilizer optimization did not converge."
        )

    quantities = np.asarray(
        solution.x,
        dtype=float,
    )

    if (
        not np.isfinite(quantities).all()
        or np.any(quantities < -1e-8)
    ):
        raise ValueError(
            "Optimizer returned invalid quantities."
        )

    quantities = np.maximum(
        quantities,
        0.0,
    )

    # Round the actual displayed fertilizer amounts first,
    # then recalculate the balance from those same amounts.
    displayed_quantities = np.round(
        quantities,
        2,
    )

    supplied = (
        matrix @ displayed_quantities
    )

    # ----------------------------------------
    # FERTILIZER PLAN
    # ----------------------------------------

    plan_rows = []

    for index, (_, fertilizer) in enumerate(
        selected.iterrows()
    ):

        plan_rows.append({
            "Fertilizer": str(
                fertilizer["fertilizer_name"]
            ),
            "Quantity (kg)": float(
                displayed_quantities[index]
            ),
        })

    plan_df = pd.DataFrame(
        plan_rows,
        columns=[
            "Fertilizer",
            "Quantity (kg)",
        ],
    )

    # ----------------------------------------
    # NUTRIENT BALANCE
    # ----------------------------------------

    balance_rows = []

    for index, nutrient in enumerate(NUTRIENTS):

        target = float(
            target_vector[index]
        )

        actual = float(
            supplied[index]
        )

        difference = actual - target

        if target > 0:

            deviation_percent = (
                abs(difference) / target * 100.0
            )

            within_tolerance = (
                deviation_percent <= tolerance_percent
            )

        else:

            # Zero-target nutrients should receive no
            # meaningful unintended nutrient supply.
            within_tolerance = (
                abs(actual) < 0.01
            )

        balance_rows.append({
            "Nutrient": NUTRIENT_LABELS[nutrient],
            "Target (kg)": round(target, 2),
            "Supplied (kg)": round(actual, 2),
            "Difference (kg)": round(difference, 2),
            "Within tolerance": bool(
                within_tolerance
            ),
        })

    balance_df = pd.DataFrame(
        balance_rows,
        columns=[
            "Nutrient",
            "Target (kg)",
            "Supplied (kg)",
            "Difference (kg)",
            "Within tolerance",
        ],
    )

    return plan_df, balance_df
