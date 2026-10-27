
"""
Step 10.10 - Database, Authentication and History Tests

Tests run using a temporary SQLite database.
Your production database/agriculture.db is not modified.
"""

from pathlib import Path
from contextlib import contextmanager
import shutil
import sys
import tempfile

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parent.parent
SOURCE = PROJECT_ROOT / "src"


def check(label, condition):
    if not condition:
        raise AssertionError(label)

    print(f"PASS: {label}")


def main():

    with tempfile.TemporaryDirectory(
        prefix="agriculture_db_test_"
    ) as folder:

        root = Path(folder)
        src = root / "src"
        src.mkdir()

        (src / "__init__.py").write_text("")

        # Copy modules into temporary project.
        for filename in (
            "database.py",
            "auth.py",
            "history.py",
        ):
            shutil.copy2(
                SOURCE / filename,
                src / filename,
            )

        sys.path.insert(0, str(root))

        try:
            from src.database import initialize_database
            from src.auth import (
                register_farmer,
                login_farmer,
                validate_password,
            )
            from src.history import (
                save_recommendation,
                save_fertilizer_plan,
                get_farmer_history,
                get_recommendation_details,
            )

            import src.database as db_module
            import src.auth as auth_module
            import src.history as history_module

            # Important Windows fix:
            # SQLite context managers do not close connections.
            # Wrap the copied database connection so that
            # every connection is explicitly closed.

            original_get_connection = db_module.get_connection

            @contextmanager
            def closing_connection():
                connection = original_get_connection()

                try:
                    with connection:
                        yield connection
                finally:
                    connection.close()

            db_module.get_connection = closing_connection
            auth_module.get_connection = closing_connection
            history_module.get_connection = closing_connection

            initialize_database()

            # ------------------------------------
            # TEST 1: DATABASE TABLES
            # ------------------------------------

            with closing_connection() as conn:

                tables = {
                    row["name"]
                    for row in conn.execute(
                        """
                        SELECT name
                        FROM sqlite_master
                        WHERE type = 'table'
                        """
                    )
                }

                foreign_keys = conn.execute(
                    "PRAGMA foreign_keys"
                ).fetchone()[0]

            expected_tables = {
                "farmers",
                "recommendations",
                "crop_results",
                "fertilizer_results",
            }

            check(
                "All four tables exist",
                expected_tables.issubset(tables),
            )

            check(
                "Foreign keys enabled",
                foreign_keys == 1,
            )

            # ------------------------------------
            # TEST 2: AUTHENTICATION
            # ------------------------------------

            check(
                "Weak password rejected",
                not validate_password(
                    "test_farmer",
                    "weak",
                )[0],
            )

            ok, message = register_farmer(
                "test_farmer_1",
                "Strong!Pass987",
            )

            check("Farmer 1 registration", ok)

            ok, message = register_farmer(
                "test_farmer_2",
                "Strong!Pass987",
            )

            check("Farmer 2 registration", ok)

            ok, message = register_farmer(
                "test_farmer_1",
                "Strong!Pass987",
            )

            check(
                "Duplicate username rejected",
                not ok,
            )

            farmer1 = login_farmer(
                "test_farmer_1",
                "Strong!Pass987",
            )

            farmer2 = login_farmer(
                "test_farmer_2",
                "Strong!Pass987",
            )

            check(
                "Correct password login",
                bool(farmer1 and farmer2),
            )

            check(
                "Incorrect password rejected",
                login_farmer(
                    "test_farmer_1",
                    "Wrong!Pass987",
                ) is None,
            )

            # ------------------------------------
            # TEST 3: SAVE RECOMMENDATION
            # ------------------------------------

            request = {
                "workflow": "Crop Already Planted",
                "crop": "C03",
                "soil": None,
                "season": None,
                "area": 1.0,
                "plants": None,
                "n": 70.0,
                "p": 8.0,
                "k": 90.0,
                "ph": 6.5,
                "temp": 28.0,
                "humidity": 65.0,
                "measurement_source": "manual",
            }

            results = [
                {
                    "crop_id": "C03",
                    "category": (
                        "Suitable without major "
                        "nutrient supplementation"
                    ),
                    "nutrient_analysis": [
                        {
                            "nutrient": "N",
                            "status": "Within reference range",
                        }
                    ],
                    "deficient_nutrients": [],
                    "organic_alternatives": [],
                }
            ]

            rec_id = save_recommendation(
                farmer1["farmer_id"],
                request,
                results,
            )

            check(
                "Recommendation saved",
                isinstance(rec_id, int) and rec_id > 0,
            )

            # ------------------------------------
            # TEST 4: OWNERSHIP AND HISTORY
            # ------------------------------------

            own = get_recommendation_details(
                farmer1["farmer_id"],
                rec_id,
            )

            other = get_recommendation_details(
                farmer2["farmer_id"],
                rec_id,
            )

            check(
                "Owner can read details",
                own is not None
                and len(own["crop_results"]) == 1,
            )

            check(
                "Other farmer cannot read details",
                other is None,
            )

            history1 = get_farmer_history(
                farmer1["farmer_id"]
            )

            check(
                "Owner sees history",
                any(
                    item["recommendation_id"] == rec_id
                    for item in history1
                ),
            )

            history2 = get_farmer_history(
                farmer2["farmer_id"]
            )

            check(
                "Other farmer does not see history",
                not history2,
            )

            # ------------------------------------
            # TEST 5: FERTILIZER PLAN
            # ------------------------------------

            plan = pd.DataFrame([
                {
                    "Fertilizer": "Urea",
                    "Quantity (kg)": 10.0,
                }
            ])

            balance = pd.DataFrame([
                {
                    "Nutrient": "N",
                    "Target (kg)": 4.6,
                    "Supplied (kg)": 4.6,
                    "Difference (kg)": 0.0,
                    "Within tolerance": True,
                }
            ])

            blocked = False

            try:
                save_fertilizer_plan(
                    farmer2["farmer_id"],
                    rec_id,
                    "C03",
                    plan,
                    balance,
                )

            except ValueError:
                blocked = True

            check(
                "Other farmer cannot save plan",
                blocked,
            )

            save_fertilizer_plan(
                farmer1["farmer_id"],
                rec_id,
                "C03",
                plan,
                balance,
            )

            saved = get_recommendation_details(
                farmer1["farmer_id"],
                rec_id,
            )

            check(
                "Owner fertilizer plan saved",
                len(
                    saved["crop_results"][0][
                        "chemical_fertilizers"
                    ]
                ) == 1,
            )

            # Save again: previous plan must be replaced.
            save_fertilizer_plan(
                farmer1["farmer_id"],
                rec_id,
                "C03",
                plan,
                balance,
            )

            saved = get_recommendation_details(
                farmer1["farmer_id"],
                rec_id,
            )

            check(
                "Re-saving replaces rather than duplicates plan",
                len(
                    saved["crop_results"][0][
                        "chemical_fertilizers"
                    ]
                ) == 1,
            )

            print()
            print("ALL INTEGRATION TESTS PASSED")
            print("Production database unchanged.")

        finally:
            sys.path.remove(str(root))


if __name__ == "__main__":
    main()
