
import json

from src.database import (
    get_connection,
    initialize_database
)


# ============================================
# SAVE RECOMMENDATION AND CROP RESULTS
# ============================================

def save_recommendation(
    farmer_id,
    request,
    crop_results
):
    """
    Save one recommendation session and its crop results.

    request: dictionary containing farmer inputs.

    crop_results: list of dictionaries containing:
        crop_id
        category
        nutrient_analysis
        deficient_nutrients
        organic_alternatives
    """

    initialize_database()

    if not isinstance(crop_results, list):
        raise ValueError("crop_results must be a list.")

    if request["workflow"] == "Crop Already Planted":
        if not request.get("crop"):
            raise ValueError("Planted crop is required.")

    with get_connection() as connection:

        # Verify that the farmer exists.
        farmer = connection.execute(
            """
            SELECT farmer_id
            FROM farmers
            WHERE farmer_id = ?
            """,
            (farmer_id,)
        ).fetchone()

        if farmer is None:
            raise ValueError("Farmer account not found.")

        cursor = connection.execute(
            """
            INSERT INTO recommendations (
                farmer_id,
                farming_situation,
                crop_id,
                soil_type,
                season,
                land_area_ha,
                plant_count,
                nitrogen,
                phosphorus,
                potassium,
                soil_ph,
                air_temperature,
                air_humidity,
                measurement_source,
                result_status
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                farmer_id,
                request["workflow"],
                request.get("crop"),
                request.get("soil"),
                request.get("season"),
                request["area"],
                request.get("plants"),
                request["n"],
                request["p"],
                request["k"],
                request["ph"],
                request["temp"],
                request["humidity"],
                request.get("measurement_source", "manual"),
                "completed"
            )
        )

        recommendation_id = cursor.lastrowid

        for result in crop_results:

            connection.execute(
                """
                INSERT INTO crop_results (
                    recommendation_id,
                    crop_id,
                    category,
                    nutrient_analysis_json,
                    deficient_nutrients_json,
                    organic_alternatives_json
                )
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    recommendation_id,
                    result["crop_id"],
                    result["category"],
                    json.dumps(
                        result.get("nutrient_analysis", [])
                    ),
                    json.dumps(
                        result.get("deficient_nutrients", [])
                    ),
                    json.dumps(
                        result.get("organic_alternatives", [])
                    )
                )
            )

        connection.commit()

        return recommendation_id


# ============================================
# SAVE CONFIRMED CHEMICAL FERTILIZER PLAN
# ============================================

def save_fertilizer_plan(
    farmer_id,
    recommendation_id,
    crop_id,
    plan,
    balance
):
    """
    Save a confirmed chemical fertilizer plan.

    plan: pandas DataFrame with columns:
        Fertilizer
        Quantity (kg)

    balance: pandas DataFrame containing nutrient balance.
    """

    initialize_database()

    with get_connection() as connection:

        # Ownership check: the recommendation must
        # belong to the logged-in farmer.
        result = connection.execute(
            """
            SELECT cr.result_id
            FROM crop_results cr
            JOIN recommendations r
              ON r.recommendation_id = cr.recommendation_id
            WHERE r.recommendation_id = ?
              AND r.farmer_id = ?
              AND cr.crop_id = ?
            """,
            (
                recommendation_id,
                farmer_id,
                crop_id
            )
        ).fetchone()

        if result is None:
            raise ValueError(
                "Crop result not found for this farmer."
            )

        result_id = result["result_id"]

        # Replace the previous saved plan for this crop.
        connection.execute(
            """
            DELETE FROM fertilizer_results
            WHERE result_id = ?
            """,
            (result_id,)
        )

        balance_json = balance.to_json(
            orient="records"
        )

        for _, item in plan.iterrows():

            quantity = float(item["Quantity (kg)"])

            if quantity <= 0:
                continue

            connection.execute(
                """
                INSERT INTO fertilizer_results (
                    result_id,
                    fertilizer_name,
                    quantity_kg,
                    nutrient_balance_json
                )
                VALUES (?, ?, ?, ?)
                """,
                (
                    result_id,
                    str(item["Fertilizer"]),
                    quantity,
                    balance_json
                )
            )

        connection.commit()


# ============================================
# GET FARMER RECOMMENDATION HISTORY
# ============================================

def get_farmer_history(farmer_id, limit=50):

    initialize_database()

    with get_connection() as connection:

        rows = connection.execute(
            """
            SELECT *
            FROM recommendations
            WHERE farmer_id = ?
            ORDER BY recommendation_id DESC
            LIMIT ?
            """,
            (
                farmer_id,
                max(1, min(int(limit), 500))
            )
        ).fetchall()

        return [dict(row) for row in rows]


# ============================================
# GET ONE RECOMMENDATION WITH DETAILS
# ============================================

def get_recommendation_details(
    farmer_id,
    recommendation_id
):

    initialize_database()

    with get_connection() as connection:

        recommendation = connection.execute(
            """
            SELECT *
            FROM recommendations
            WHERE recommendation_id = ?
              AND farmer_id = ?
            """,
            (
                recommendation_id,
                farmer_id
            )
        ).fetchone()

        if recommendation is None:
            return None

        crop_rows = connection.execute(
            """
            SELECT *
            FROM crop_results
            WHERE recommendation_id = ?
            ORDER BY result_id
            """,
            (recommendation_id,)
        ).fetchall()

        crops = []

        for crop_row in crop_rows:

            crop = dict(crop_row)

            crop["nutrient_analysis"] = json.loads(
                crop.pop("nutrient_analysis_json") or "[]"
            )

            crop["deficient_nutrients"] = json.loads(
                crop.pop("deficient_nutrients_json") or "[]"
            )

            crop["organic_alternatives"] = json.loads(
                crop.pop("organic_alternatives_json") or "[]"
            )

            fertilizer_rows = connection.execute(
                """
                SELECT
                    fertilizer_name,
                    quantity_kg,
                    nutrient_balance_json,
                    saved_at
                FROM fertilizer_results
                WHERE result_id = ?
                ORDER BY fertilizer_result_id
                """,
                (crop["result_id"],)
            ).fetchall()

            crop["chemical_fertilizers"] = [
                {
                    "fertilizer_name": row["fertilizer_name"],
                    "quantity_kg": row["quantity_kg"],
                    "saved_at": row["saved_at"]
                }
                for row in fertilizer_rows
            ]

            if fertilizer_rows:
                crop["nutrient_balance"] = json.loads(
                    fertilizer_rows[0][
                        "nutrient_balance_json"
                    ] or "[]"
                )
            else:
                crop["nutrient_balance"] = []

            crops.append(crop)

        return {
            "recommendation": dict(recommendation),
            "crop_results": crops
        }
