TUMAKURU CROP & FERTILIZER MINI-PROJECT — FINAL DEMONSTRATION DATA PACKAGE
Date: 2026-10-26

SEVEN CSV DATASETS (keep these filenames)
1 crop_master.csv — ten crop IDs and names
2 crop_suitability.csv — 38 documented crop/soil/season combinations and provisional environmental ranges
3 soil_nutrient_thresholds.csv — provisional LAB-METHOD reference values; NOT validated for the planned NPK sensor
4 crop_nutrient_requirements.csv — provisional baseline N/P2O5/K2O dose references, NOT soil-test-adjusted prescriptions
5 organic_fertilizers.csv — indicative, variable organic nutrient compositions and application rates; P/K chemical form unverified
6 chemical_fertilizers.csv — typical chemical fertilizer nutrient grades, check product label
7 crop_ml_training.csv — 934 rule-labeled SYNTHETIC candidate rows across 300 environmental scenarios

EXTRA FILE
crop_ml_unresolved.csv — 2066 crop/scenario combinations that were NOT assigned binary labels
because the crop-soil-season combination was absent from the 38-row rules table.
Do NOT automatically interpret unresolved as unsuitable.

PROJECT CONSTRAINTS
Ten crops; five soil types; four seasons; N/P/K in mg/kg, pH, AIR temperature in C,
AIR relative humidity in %RH; NO IRRIGATION inputs, rules or features.
Land area is used for scaling quantities, not ML suitability.

HOW TO USE FOR THE PHASE 2 SOFTWARE DEMO
- Use crop_suitability.csv as the rule table for multi-crop suitability.
- Train a scikit-learn binary classifier on crop_ml_training.csv with
  crop_id, soil_type, season, pH, air_temperature, air_humidity as features.
  NPK columns are retained for integration but must NOT be used to claim nutrient-based ML.
- Split training/test by scenario_id, not by individual row.
- For new cases with absent crop-soil-season rules, show 'Not evaluated / insufficient data'.
- For fertilizer UI, show crop baseline reference rates and fertilizer composition as
  *illustrative*, not sensor-derived nutrient deficits or field-ready prescriptions.
- For annual crops, convert hectares = acres * 0.40468564224 before scaling kg/ha.
- For coconut/arecanut/banana, doses are per palm/plant; AREA ALONE is insufficient.
  Require the number of palms/plants before computing totals.
- Do not calculate deficiency (kg/ha) by subtracting NPK sensor mg/kg from
  fertilizer kg/ha. Lab method, depth, bulk density, nutrient forms and calibration matter.
- Organic fertilizers are variable and not directly interchangeable with chemical fertilizers.
  Do not add organic and chemical alternatives together as though both are mandatory.

IMPORTANT LIMITATION
The data are compatible as a *software prototype* and internally checked against the
supplied rule table. The agronomic suitability bounds, threshold figures and crop
fertilizer dose numbers have not been independently established as locally authoritative.
This is NOT a validated agricultural advisory system.

Files include check_datasets.py (local consistency checks) and train_crop_model.py
(optional grouped evaluation for the synthetic classifier).
