
import sqlite3
from pathlib import Path


# ============================================
# DATABASE LOCATION
# ============================================

BASE_DIR = Path(__file__).resolve().parent.parent

DATABASE_DIR = BASE_DIR / "database"
DATABASE_DIR.mkdir(parents=True, exist_ok=True)

DATABASE_PATH = DATABASE_DIR / "agriculture.db"


# ============================================
# DATABASE CONNECTION
# ============================================

def get_connection():

    connection = sqlite3.connect(
        DATABASE_PATH,
        timeout=10
    )

    connection.row_factory = sqlite3.Row

    # Enforce foreign key relationships.
    connection.execute("PRAGMA foreign_keys = ON")

    # Improve concurrent reading and writing.
    connection.execute("PRAGMA journal_mode = WAL")

    return connection


# ============================================
# INITIALIZE DATABASE
# ============================================

def initialize_database():

    with get_connection() as connection:

        # ------------------------------------
        # TABLE 1: FARMERS
        # ------------------------------------

        connection.execute("""
            CREATE TABLE IF NOT EXISTS farmers (

                farmer_id INTEGER PRIMARY KEY AUTOINCREMENT,

                username TEXT NOT NULL UNIQUE,

                password_hash TEXT NOT NULL,

                created_at TEXT NOT NULL
                    DEFAULT CURRENT_TIMESTAMP

            )
        """)

        # ------------------------------------
        # TABLE 2: RECOMMENDATIONS
        # ------------------------------------

        connection.execute("""
            CREATE TABLE IF NOT EXISTS recommendations (

                recommendation_id INTEGER
                    PRIMARY KEY AUTOINCREMENT,

                farmer_id INTEGER NOT NULL,

                farming_situation TEXT NOT NULL
                    CHECK (
                        farming_situation IN (
                            'Crop Not Planted',
                            'Crop Already Planted'
                        )
                    ),

                crop_id TEXT,

                soil_type TEXT,

                season TEXT,

                land_area_ha REAL NOT NULL,

                plant_count INTEGER,

                nitrogen REAL NOT NULL,

                phosphorus REAL NOT NULL,

                potassium REAL NOT NULL,

                soil_ph REAL NOT NULL,

                air_temperature REAL NOT NULL,

                air_humidity REAL NOT NULL,

                measurement_source TEXT NOT NULL
                    DEFAULT 'manual'
                    CHECK (
                        measurement_source IN (
                            'manual',
                            'ESP32'
                        )
                    ),

                result_status TEXT NOT NULL
                    DEFAULT 'completed',

                created_at TEXT NOT NULL
                    DEFAULT CURRENT_TIMESTAMP,

                FOREIGN KEY (farmer_id)
                    REFERENCES farmers(farmer_id)
                    ON DELETE CASCADE

            )
        """)

        # ------------------------------------
        # TABLE 3: CROP RESULTS
        # ------------------------------------

        connection.execute("""
            CREATE TABLE IF NOT EXISTS crop_results (

                result_id INTEGER
                    PRIMARY KEY AUTOINCREMENT,

                recommendation_id INTEGER NOT NULL,

                crop_id TEXT NOT NULL,

                category TEXT NOT NULL,

                nutrient_analysis_json TEXT,

                deficient_nutrients_json TEXT,

                organic_alternatives_json TEXT,

                FOREIGN KEY (recommendation_id)
                    REFERENCES recommendations(
                        recommendation_id
                    )
                    ON DELETE CASCADE

            )
        """)

        # ------------------------------------
        # TABLE 4: FERTILIZER RESULTS
        # ------------------------------------

        connection.execute("""
            CREATE TABLE IF NOT EXISTS fertilizer_results (

                fertilizer_result_id INTEGER
                    PRIMARY KEY AUTOINCREMENT,

                result_id INTEGER NOT NULL,

                fertilizer_name TEXT NOT NULL,

                quantity_kg REAL NOT NULL,

                nutrient_balance_json TEXT,

                saved_at TEXT NOT NULL
                    DEFAULT CURRENT_TIMESTAMP,

                FOREIGN KEY (result_id)
                    REFERENCES crop_results(result_id)
                    ON DELETE CASCADE

            )
        """)

        # ------------------------------------
        # INDEXES FOR FAST HISTORY RETRIEVAL
        # ------------------------------------

        connection.execute("""
            CREATE INDEX IF NOT EXISTS
                idx_recommendations_farmer_date
            ON recommendations (
                farmer_id,
                created_at DESC
            )
        """)

        connection.execute("""
            CREATE INDEX IF NOT EXISTS
                idx_crop_results_recommendation
            ON crop_results (
                recommendation_id
            )
        """)

        connection.execute("""
            CREATE INDEX IF NOT EXISTS
                idx_fertilizer_results_crop
            ON fertilizer_results (
                result_id
            )
        """)

        connection.commit()


# ============================================
# DISPLAY DATABASE TABLES
# ============================================

def get_table_names():

    with get_connection() as connection:

        rows = connection.execute("""
            SELECT name
            FROM sqlite_master
            WHERE type = 'table'
              AND name NOT LIKE 'sqlite_%'
            ORDER BY name
        """).fetchall()

        return [row["name"] for row in rows]


# ============================================
# RUN DIRECTLY FOR INITIAL TEST
# ============================================

if __name__ == "__main__":

    initialize_database()

    print("Database initialized successfully!")

    print(f"Database location: {DATABASE_PATH}")

    print("\nCreated tables:")

    for table_name in get_table_names():
        print("-", table_name)
