
from pathlib import Path

import pandas as pd
import streamlit as st

from src.auth import (
    register_farmer,
    login_farmer,
    validate_password,
)
from src.database import initialize_database
from src.history import (
    save_recommendation,
    save_fertilizer_plan,
    get_farmer_history,
    get_recommendation_details,
)
from src.crop_recommendation import recommend_crops
from src.nutrient_analysis import categorize_crop
from src.fertilizer_optimizer import optimize_chemical_fertilizers
from src.input_validation import validate_request


# ============================================
# 1. CONFIGURATION
# ============================================

st.set_page_config(
    page_title="Tumakuru Smart Agriculture",
    page_icon="🌱",
    layout="wide",
)

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data" / "raw"

initialize_database()


@st.cache_data
def load_data():
    return (
        pd.read_csv(DATA_DIR / "crop_master.csv"),
        pd.read_csv(DATA_DIR / "organic_fertilizers.csv"),
        pd.read_csv(DATA_DIR / "chemical_fertilizers.csv"),
    )


try:
    crop_master, organic, chemical = load_data()

except (OSError, ValueError) as error:
    st.error(f"Dataset loading failed: {error}")
    st.stop()


crop_names = dict(
    zip(
        crop_master["crop_id"].astype(str),
        crop_master["crop_name"].astype(str),
    )
)

per_plant_crops = {"C01", "C02", "C05"}

soil_types = [
    "Red loamy soils",
    "Red sandy loam soils",
    "Sandy clay loam soils",
    "Loamy soils",
    "Sandy soils",
]

seasons = [
    "Summer",
    "Monsoon",
    "Post-monsoon",
    "Winter",
]


# ============================================
# 2. SESSION STATE
# ============================================

if "logged_in_farmer" not in st.session_state:
    st.session_state.logged_in_farmer = None

if "last_request" not in st.session_state:
    st.session_state.last_request = None

if "current_recommendation_id" not in st.session_state:
    st.session_state.current_recommendation_id = None

if "current_crop_results" not in st.session_state:
    st.session_state.current_crop_results = []


def clear_recommendation_state():
    st.session_state.last_request = None
    st.session_state.current_recommendation_id = None
    st.session_state.current_crop_results = []

    for key in list(st.session_state.keys()):
        if (
            key.startswith("chem_")
            or key.startswith("plants_")
        ):
            del st.session_state[key]


def logout_farmer():
    clear_recommendation_state()
    st.session_state.logged_in_farmer = None


# ============================================
# 3. ACCOUNT ALREADY EXISTS POPUP
# ============================================

@st.dialog("Account Already Exists")
def account_exists_popup():
    st.warning(
        "This username is already registered. "
        "Please log in or choose another username."
    )

    if st.button("OK", key="account_exists_ok"):
        st.rerun()


# ============================================
# 4. FARMER LOGIN AND REGISTRATION
# ============================================

if st.session_state.logged_in_farmer is None:

    st.title("🌱 Tumakuru Smart Agriculture")
    st.subheader("Farmer Account")

    login_tab, signup_tab = st.tabs([
        "Login",
        "Create Account",
    ])

    # ----------------------------------------
    # LOGIN
    # ----------------------------------------

    with login_tab:

        st.markdown("### Farmer Login")

        with st.form("login_form"):

            login_username = st.text_input(
                "Username",
                key="login_username",
            )

            login_password = st.text_input(
                "Password",
                type="password",
                key="login_password",
            )

            login_submit = st.form_submit_button(
                "Login",
                type="primary",
            )

        if login_submit:

            if not login_username.strip() or not login_password:
                st.error(
                    "Please enter your username and password."
                )

            else:
                farmer = login_farmer(
                    login_username,
                    login_password,
                )

                if farmer is None:
                    st.error(
                        "Invalid username or password."
                    )

                else:
                    clear_recommendation_state()
                    st.session_state.logged_in_farmer = farmer
                    st.rerun()

    # ----------------------------------------
    # SIGN UP
    # ----------------------------------------

    with signup_tab:

        st.markdown("### Create Farmer Account")

        st.info(
            "Password requirements:\n"
            "- Minimum 8 characters\n"
            "- At least one uppercase letter\n"
            "- At least one lowercase letter\n"
            "- At least one number\n"
            "- At least one special character\n"
            "- No spaces\n"
            "- Must not contain your username"
        )

        with st.form("signup_form"):

            signup_username = st.text_input(
                "Choose Username",
                key="signup_username",
            )

            signup_password = st.text_input(
                "Choose Password",
                type="password",
                key="signup_password",
            )

            confirm_password = st.text_input(
                "Confirm Password",
                type="password",
                key="confirm_password",
            )

            signup_submit = st.form_submit_button(
                "Create Account",
                type="primary",
            )

        if signup_submit:

            if not signup_username.strip():
                st.error("Please enter a username.")

            elif signup_password != confirm_password:
                st.error("Passwords do not match.")

            else:
                valid, message = validate_password(
                    signup_username,
                    signup_password,
                )

                if not valid:
                    st.error(message)

                else:
                    success, message = register_farmer(
                        signup_username,
                        signup_password,
                    )

                    if success:
                        st.success(
                            "Account created successfully! "
                            "Please open the Login tab."
                        )

                    elif message == (
                        "This username is already registered."
                    ):
                        account_exists_popup()

                    else:
                        st.error(message)

    st.stop()


# ============================================
# 5. LOGGED-IN FARMER
# ============================================

farmer = st.session_state.logged_in_farmer
farmer_id = farmer["farmer_id"]

st.sidebar.success(
    f"Logged in as: {farmer['username']}"
)

if st.sidebar.button("Logout"):
    logout_farmer()
    st.rerun()


page = st.sidebar.radio(
    "Navigation",
    [
        "Get Recommendations",
        "My History",
    ],
)


# ============================================
# 6. ORGANIC FERTILIZER ALTERNATIVES
# ============================================

def get_organic_alternatives(deficient):

    rows = []

    nutrient_columns = [
        ("N", "n_percent"),
        ("P", "p_percent"),
        ("K", "k_percent"),
    ]

    for _, item in organic.iterrows():

        nutrients = []

        for symbol, column in nutrient_columns:

            value = pd.to_numeric(
                item.get(column, 0),
                errors="coerce",
            )

            if (
                symbol in deficient
                and pd.notna(value)
                and value > 0
            ):
                nutrients.append(symbol)

        if nutrients:
            rows.append({
                "Organic Fertilizer": str(
                    item["fertilizer_name"]
                ),
                "Relevant Nutrients": ", ".join(nutrients),
            })

    return rows


# ============================================
# 7. BUILD CROP RESULT
# ============================================

def build_crop_result(crop_id, request, category):

    _, analysis = categorize_crop(
        crop_id,
        request["n"],
        request["p"],
        request["k"],
    )

    clean_analysis = []

    for item in analysis:
        clean_analysis.append({
            "nutrient": str(item["nutrient"]),
            "status": str(item["status"]),
        })

    deficient = [
        item["nutrient"]
        for item in clean_analysis
        if item["status"] == "Below reference range"
    ]

    organic_options = get_organic_alternatives(
        deficient
    )

    return {
        "crop_id": crop_id,
        "category": category,
        "nutrient_analysis": clean_analysis,
        "deficient_nutrients": deficient,
        "organic_alternatives": organic_options,
    }


# ============================================
# 8. GENERATE RECOMMENDATIONS
# ============================================

def generate_results(request):

    results_to_save = []

    if request["workflow"] == "Crop Already Planted":

        crop_id = request["crop"]

        results_to_save.append(
            build_crop_result(
                crop_id,
                request,
                "Already Planted",
            )
        )

        return results_to_save

    suitability = recommend_crops(
        request["soil"],
        request["season"],
        request["ph"],
        request["temp"],
        request["humidity"],
    )

    suitable = suitability.loc[
        suitability["status"] == "Suitable"
    ]

    for crop_id in suitable["crop_id"].astype(str):

        category, _ = categorize_crop(
            crop_id,
            request["n"],
            request["p"],
            request["k"],
        )

        if category not in [
            "Suitable without major nutrient supplementation",
            "Suitable with nutrient supplementation",
        ]:
            continue

        results_to_save.append(
            build_crop_result(
                crop_id,
                request,
                category,
            )
        )

    return results_to_save


# ============================================
# 9. DISPLAY NUTRIENT AND FERTILIZER RESULTS
# ============================================

def show_fertilizer_results(
    crop_result,
    request,
    recommendation_id,
):

    crop_id = crop_result["crop_id"]
    deficient = crop_result["deficient_nutrients"]
    analysis = crop_result["nutrient_analysis"]

    status_map = {
        item["nutrient"]: item["status"]
        for item in analysis
    }

    # ----------------------------------------
    # NUTRIENT ANALYSIS
    # ----------------------------------------

    st.markdown("#### Soil Nutrient Analysis")

    nutrient_rows = []

    for symbol in ["N", "P", "K"]:
        nutrient_rows.append({
            "Nutrient": symbol,
            "Measured (mg/kg)": request[symbol.lower()],
            "Status": status_map.get(symbol, "Unknown"),
        })

    st.dataframe(
        pd.DataFrame(nutrient_rows),
        hide_index=True,
        use_container_width=True,
    )

    if not deficient:
        st.success(
            "No nutrients were flagged below "
            "the provisional reference range."
        )
        return

    st.warning(
        "Nutrients requiring supplementation: "
        + ", ".join(deficient)
    )

    # ----------------------------------------
    # ORGANIC FERTILIZERS
    # ----------------------------------------

    st.markdown(
        "#### 🌿 Organic Fertilizer Alternatives"
    )

    organic_options = crop_result["organic_alternatives"]

    if organic_options:
        st.dataframe(
            pd.DataFrame(organic_options),
            hide_index=True,
            use_container_width=True,
        )

    else:
        st.info(
            "No matching organic fertilizers found."
        )

    st.caption(
        "Organic fertilizer quantities are not "
        "included in this version."
    )

    # ----------------------------------------
    # QUANTITY BASIS
    # ----------------------------------------

    if crop_id in per_plant_crops:

        if request["workflow"] == "Crop Already Planted":
            plant_count = request["plants"]

        else:
            plant_count = st.number_input(
                "Number of Plants / Palms",
                min_value=1,
                value=100,
                step=1,
                key=f"plants_{crop_id}",
            )

        st.caption(
            f"Calculation basis: {plant_count} plants/palms"
        )

    else:
        plant_count = None

        st.caption(
            f"Calculation basis: {request['area']} hectares"
        )

    # ----------------------------------------
    # CHEMICAL FERTILIZER SELECTION
    # ----------------------------------------

    st.markdown(
        "#### 🧪 Chemical Fertilizer Selection"
    )

    nutrient_columns = [
        "n_percent",
        "p2o5_percent",
        "k2o_percent",
    ]

    available = chemical.loc[
        (
            chemical[nutrient_columns].fillna(0) > 0
        ).any(axis=1),
        "fertilizer_name",
    ].dropna().astype(str).drop_duplicates().tolist()

    selected = st.multiselect(
        "Choose Chemical Fertilizers",
        available,
        key=f"chem_{crop_id}",
    )

    if not selected:
        st.info(
            "Select fertilizers to calculate "
            "a combined chemical plan."
        )
        return

    # ----------------------------------------
    # CALCULATE CHEMICAL PLAN
    # ----------------------------------------

    try:
        plan, balance = optimize_chemical_fertilizers(
            crop_id=crop_id,
            selected_fertilizers=selected,
            deficient_nutrients=deficient,
            land_area_ha=request["area"],
            plant_count=plant_count,
            tolerance_percent=10,
        )

    except (ValueError, KeyError, TypeError) as error:
        st.error(
            f"Fertilizer calculation failed: {error}"
        )
        return

    st.markdown(
        "##### Combined Chemical Fertilizer Plan"
    )

    plan_display = plan.loc[
        plan["Quantity (kg)"] > 0
    ].copy()

    if plan_display.empty:
        st.warning(
            "No positive fertilizer quantities calculated."
        )
        return

    st.dataframe(
        plan_display,
        hide_index=True,
        use_container_width=True,
    )

    st.markdown("##### Nutrient Balance")

    st.dataframe(
        balance,
        hide_index=True,
        use_container_width=True,
    )

    if (
        not balance.empty
        and balance["Within tolerance"].fillna(False).all()
    ):
        st.success(
            "Combination matches provisional nutrient "
            "targets within software tolerance."
        )

    else:
        st.warning(
            "Combination does not adequately match "
            "the provisional nutrient targets."
        )

    st.caption(
        "Quantities are illustrative nutrient-equivalent "
        "calculations using provisional full-crop targets, "
        "not validated soil-deficiency correction doses."
    )

    # ----------------------------------------
    # SAVE FERTILIZER PLAN
    # ----------------------------------------

    if st.button(
        "💾 Save Fertilizer Plan",
        key=f"save_plan_{crop_id}",
        type="primary",
    ):

        try:
            save_fertilizer_plan(
                farmer_id=farmer_id,
                recommendation_id=recommendation_id,
                crop_id=crop_id,
                plan=plan_display,
                balance=balance,
            )

            st.success(
                "Fertilizer plan saved to your history!"
            )

        except (ValueError, KeyError, TypeError) as error:
            st.error(
                f"Could not save fertilizer plan: {error}"
            )


# ============================================
# 10. GET RECOMMENDATIONS PAGE
# ============================================

if page == "Get Recommendations":

    st.title("🌱 Tumakuru Smart Agriculture")

    st.subheader(
        "Crop and Fertilizer Recommendation System"
    )

    st.caption(
        "Phase 2: Manual measurements. "
        "Phase 3: On-demand ESP32 sensor measurements."
    )

    st.warning(
        "Academic prototype. Agricultural thresholds "
        "and fertilizer targets are provisional."
    )

    st.sidebar.header("Farmer Inputs")

    workflow = st.sidebar.radio(
        "Farming Situation",
        [
            "Crop Not Planted",
            "Crop Already Planted",
        ],
    )

    soil_type = None
    season = None
    selected_crop = None
    plant_count = None

    # ----------------------------------------
    # WORKFLOW-SPECIFIC INPUTS
    # ----------------------------------------

    if workflow == "Crop Not Planted":

        soil_type = st.sidebar.selectbox(
            "Soil Type",
            soil_types,
        )

        season = st.sidebar.selectbox(
            "Season",
            seasons,
        )

    else:

        selected_crop = st.sidebar.selectbox(
            "Select Planted Crop",
            list(crop_names),
            format_func=lambda crop_id: crop_names[crop_id],
        )

    land_area = st.sidebar.number_input(
        "Land Area (hectares)",
        min_value=0.01,
        value=1.0,
        step=0.1,
    )

    if (
        workflow == "Crop Already Planted"
        and selected_crop in per_plant_crops
    ):

        plant_count = st.sidebar.number_input(
            "Number of Plants / Palms",
            min_value=1,
            value=100,
            step=1,
        )

    # ----------------------------------------
    # SOIL MEASUREMENTS
    # ----------------------------------------

    st.sidebar.subheader("Soil Measurements")

    n = st.sidebar.number_input(
        "Nitrogen (mg/kg)",
        min_value=0.0,
        value=90.0,
    )

    p = st.sidebar.number_input(
        "Phosphorus (mg/kg)",
        min_value=0.0,
        value=7.0,
    )

    k = st.sidebar.number_input(
        "Potassium (mg/kg)",
        min_value=0.0,
        value=80.0,
    )

    ph = st.sidebar.number_input(
        "Soil pH",
        min_value=0.0,
        max_value=14.0,
        value=6.5,
        step=0.1,
    )

    # ----------------------------------------
    # AIR MEASUREMENTS
    # ----------------------------------------

    st.sidebar.subheader("Air Measurements")

    temp = st.sidebar.number_input(
        "Air Temperature (°C)",
        min_value=-10.0,
        max_value=60.0,
        value=28.0,
    )

    humidity = st.sidebar.number_input(
        "Air Relative Humidity (%)",
        min_value=0.0,
        max_value=100.0,
        value=75.0,
    )

    # ----------------------------------------
    # GENERATE AND SAVE RECOMMENDATIONS
    # ----------------------------------------

    if st.sidebar.button(
        "Get Recommendations",
        type="primary",
    ):

        request = {
            "workflow": workflow,
            "crop": selected_crop,
            "soil": soil_type,
            "season": season,
            "area": float(land_area),
            "plants": plant_count,
            "n": float(n),
            "p": float(p),
            "k": float(k),
            "ph": float(ph),
            "temp": float(temp),
            "humidity": float(humidity),
            "measurement_source": "manual",
        }

        # STEP 10.6: VALIDATE BEFORE GENERATING OR SAVING

        errors, warnings = validate_request(
            request,
            valid_crop_ids=set(crop_names.keys()),
        )

        if errors:

            for error in errors:
                st.error(error)

            st.warning(
                "Recommendation was not generated or saved. "
                "Correct the invalid inputs and try again."
            )

        else:

            for warning in warnings:
                st.warning(warning)

            try:
                crop_results = generate_results(request)

                # Save only after successful generation
                recommendation_id = save_recommendation(
                    farmer_id=farmer_id,
                    request=request,
                    crop_results=crop_results,
                )

                clear_recommendation_state()

                st.session_state.last_request = request
                st.session_state.current_crop_results = (
                    crop_results
                )
                st.session_state.current_recommendation_id = (
                    recommendation_id
                )

                st.success(
                    "Recommendation generated and "
                    "saved to your history!"
                )

            except Exception as error:
                st.error(
                    "Recommendation could not be completed: "
                    f"{error}"
                )

    # ----------------------------------------
    # DISPLAY CURRENT RESULTS
    # ----------------------------------------

    request = st.session_state.last_request

    recommendation_id = st.session_state[
        "current_recommendation_id"
    ]

    crop_results = st.session_state[
        "current_crop_results"
    ]

    if request is None:

        st.info(
            "Enter measurements in the sidebar "
            "and click Get Recommendations."
        )

    elif request["workflow"] != workflow:

        st.info(
            "Click Get Recommendations for the "
            "currently selected farming situation."
        )

    elif request["workflow"] == "Crop Already Planted":

        crop_id = request["crop"]

        st.header(
            "Crop Already Planted: "
            + crop_names.get(crop_id, crop_id)
        )

        st.write(
            f"Land area: {request['area']} hectares"
        )

        if crop_results:
            show_fertilizer_results(
                crop_results[0],
                request,
                recommendation_id,
            )

    else:

        st.header("Crop Not Planted: Results")

        category1 = [
            result
            for result in crop_results
            if result["category"] == (
                "Suitable without major nutrient supplementation"
            )
        ]

        category2 = [
            result
            for result in crop_results
            if result["category"] == (
                "Suitable with nutrient supplementation"
            )
        ]

        col1, col2 = st.columns(2)

        col1.metric(
            "Without Major Supplementation",
            len(category1),
        )

        col2.metric(
            "With Supplementation",
            len(category2),
        )

        st.subheader(
            "Category 1: Suitable Without "
            "Major Nutrient Supplementation"
        )

        if category1:

            st.dataframe(
                pd.DataFrame({
                    "Crop": [
                        crop_names.get(
                            item["crop_id"],
                            item["crop_id"],
                        )
                        for item in category1
                    ]
                }),
                hide_index=True,
                use_container_width=True,
            )

        else:
            st.info("No crops in Category 1.")

        st.subheader(
            "Category 2: Suitable With "
            "Nutrient Supplementation"
        )

        if not category2:
            st.info("No crops in Category 2.")

        for item in category2:

            crop_id = item["crop_id"]

            with st.expander(
                f"🌾 {crop_names.get(crop_id, crop_id)}"
            ):

                show_fertilizer_results(
                    item,
                    request,
                    recommendation_id,
                )

        st.caption(
            "Crops with insufficient suitability or nutrient "
            "information are not included in these categories."
        )


# ============================================
# 11. MY RECOMMENDATION HISTORY
# ============================================

elif page == "My History":

    st.title("📜 My Recommendation History")

    st.write(
        f"Farmer: **{farmer['username']}**"
    )

    history = get_farmer_history(
        farmer_id=farmer_id,
        limit=100,
    )

    if not history:

        st.info(
            "No recommendations saved yet. "
            "Generate a recommendation first."
        )

    else:

        history_filter = st.selectbox(
            "Filter by Farming Situation",
            [
                "All",
                "Crop Not Planted",
                "Crop Already Planted",
            ],
        )

        if history_filter != "All":

            history = [
                item
                for item in history
                if item["farming_situation"] == history_filter
            ]

        st.write(
            f"Showing {len(history)} recommendation(s)"
        )

        for entry in history:

            recommendation_id = entry[
                "recommendation_id"
            ]

            label = (
                f"#{recommendation_id} | "
                f"{entry['farming_situation']} | "
                f"{entry['created_at']}"
            )

            with st.expander(label):

                details = get_recommendation_details(
                    farmer_id,
                    recommendation_id,
                )

                if details is None:
                    st.error(
                        "This recommendation is unavailable."
                    )
                    continue

                saved = details["recommendation"]

                st.markdown("#### Farmer Inputs")

                input_rows = [
                    (
                        "Farming Situation",
                        saved["farming_situation"],
                    ),
                    (
                        "Land Area (ha)",
                        saved["land_area_ha"],
                    ),
                    (
                        "Nitrogen (mg/kg)",
                        saved["nitrogen"],
                    ),
                    (
                        "Phosphorus (mg/kg)",
                        saved["phosphorus"],
                    ),
                    (
                        "Potassium (mg/kg)",
                        saved["potassium"],
                    ),
                    (
                        "Soil pH",
                        saved["soil_ph"],
                    ),
                    (
                        "Air Temperature (°C)",
                        saved["air_temperature"],
                    ),
                    (
                        "Air Humidity (%)",
                        saved["air_humidity"],
                    ),
                    (
                        "Measurement Source",
                        saved["measurement_source"],
                    ),
                ]

                if saved["farming_situation"] == "Crop Not Planted":

                    input_rows.insert(
                        1,
                        ("Soil Type", saved["soil_type"]),
                    )

                    input_rows.insert(
                        2,
                        ("Season", saved["season"]),
                    )

                else:

                    input_rows.insert(
                        1,
                        (
                            "Planted Crop",
                            crop_names.get(
                                saved["crop_id"],
                                saved["crop_id"],
                            ),
                        ),
                    )

                if saved["plant_count"] is not None:

                    input_rows.append(
                        ("Plant Count", saved["plant_count"])
                    )

                st.dataframe(
                    pd.DataFrame(
                        input_rows,
                        columns=[
                            "Input",
                            "Saved Value",
                        ],
                    ),
                    hide_index=True,
                    use_container_width=True,
                )

                st.markdown("#### Saved Recommendations")

                saved_crops = details["crop_results"]

                if not saved_crops:
                    st.info(
                        "No crops were assigned to a "
                        "recommendation category."
                    )

                for crop in saved_crops:

                    crop_name = crop_names.get(
                        crop["crop_id"],
                        crop["crop_id"],
                    )

                    st.markdown(
                        f"##### 🌾 {crop_name}"
                    )

                    st.write(
                        f"**Category:** {crop['category']}"
                    )

                    if crop["category"] == (
                        "Suitable without major nutrient supplementation"
                    ):
                        continue

                    # --------------------------------
                    # SAVED NUTRIENT ANALYSIS
                    # --------------------------------

                    if crop["nutrient_analysis"]:

                        st.markdown(
                            "**Nutrient Analysis**"
                        )

                        st.dataframe(
                            pd.DataFrame(
                                crop["nutrient_analysis"]
                            ),
                            hide_index=True,
                            use_container_width=True,
                        )

                    deficient = crop[
                        "deficient_nutrients"
                    ]

                    st.write(
                        "**Deficient Nutrients:** "
                        + (
                            ", ".join(deficient)
                            if deficient
                            else "None flagged"
                        )
                    )

                    # --------------------------------
                    # SAVED ORGANIC ALTERNATIVES
                    # --------------------------------

                    organic_saved = crop[
                        "organic_alternatives"
                    ]

                    st.markdown(
                        "**Organic Fertilizer Alternatives**"
                    )

                    if organic_saved:

                        st.dataframe(
                            pd.DataFrame(organic_saved),
                            hide_index=True,
                            use_container_width=True,
                        )

                    else:
                        st.write(
                            "No organic alternatives saved."
                        )

                    # --------------------------------
                    # SAVED CHEMICAL FERTILIZERS
                    # --------------------------------

                    chemical_saved = crop[
                        "chemical_fertilizers"
                    ]

                    st.markdown(
                        "**Saved Chemical Fertilizer Plan**"
                    )

                    if chemical_saved:

                        st.dataframe(
                            pd.DataFrame(chemical_saved),
                            hide_index=True,
                            use_container_width=True,
                        )

                        if crop["nutrient_balance"]:

                            st.markdown(
                                "**Saved Nutrient Balance**"
                            )

                            st.dataframe(
                                pd.DataFrame(
                                    crop["nutrient_balance"]
                                ),
                                hide_index=True,
                                use_container_width=True,
                            )

                    else:
                        st.info(
                            "No chemical fertilizer plan "
                            "was saved for this crop."
                        )
