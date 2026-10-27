
from pathlib import Path

import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import (
    accuracy_score,
    classification_report,
    confusion_matrix,
    precision_score,
    recall_score,
    f1_score,
)
from sklearn.model_selection import GroupShuffleSplit
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder


BASE_DIR = Path(__file__).resolve().parent.parent
DATA_PATH = BASE_DIR / "data" / "raw" / "crop_ml_training.csv"

df = pd.read_csv(DATA_PATH)

categorical = ["crop_id", "soil_type", "season"]
numeric = ["pH", "air_temperature", "air_humidity"]
features = categorical + numeric

required_columns = features + [
    "suitability_label",
    "scenario_id",
]

missing = set(required_columns) - set(df.columns)

if missing:
    raise ValueError(f"Missing columns: {sorted(missing)}")

if df[required_columns].isna().any().any():
    raise ValueError("Dataset contains missing required values.")

X = df[features]
y = df["suitability_label"].astype(int)
groups = df["scenario_id"]

if not set(y.unique()).issubset({0, 1}):
    raise ValueError("Labels must be 0 or 1.")

split = GroupShuffleSplit(
    n_splits=1,
    test_size=0.2,
    random_state=42,
)

train_idx, test_idx = next(
    split.split(X, y, groups)
)

X_train = X.iloc[train_idx]
X_test = X.iloc[test_idx]

y_train = y.iloc[train_idx]
y_test = y.iloc[test_idx]

train_groups = set(groups.iloc[train_idx])
test_groups = set(groups.iloc[test_idx])

assert train_groups.isdisjoint(test_groups), (
    "Train/test scenario leakage detected."
)

if y_train.nunique() != 2 or y_test.nunique() != 2:
    raise ValueError(
        "Both splits must contain both label classes."
    )

pipeline = Pipeline([
    (
        "preprocess",
        ColumnTransformer([
            (
                "categorical",
                OneHotEncoder(handle_unknown="ignore"),
                categorical,
            ),
            ("numeric", "passthrough", numeric),
        ]),
    ),
    (
        "classifier",
        RandomForestClassifier(
            n_estimators=250,
            random_state=42,
            class_weight="balanced",
        ),
    ),
])

pipeline.fit(X_train, y_train)

predictions = pipeline.predict(X_test)

print("\n" + "=" * 55)
print("SYNTHETIC CROP SUITABILITY MODEL EVALUATION")
print("=" * 55)

print(f"Total records: {len(df)}")
print(f"Training records: {len(X_train)}")
print(f"Testing records: {len(X_test)}")
print(f"Training scenarios: {len(train_groups)}")
print(f"Testing scenarios: {len(test_groups)}")
print("Scenario overlap: 0")

print("\nCLASS DISTRIBUTION")
print("Training:", y_train.value_counts().to_dict())
print("Testing:", y_test.value_counts().to_dict())

print("\nPERFORMANCE METRICS")
print(f"Accuracy : {accuracy_score(y_test, predictions):.4f}")
print(
    f"Precision: {precision_score(y_test, predictions, zero_division=0):.4f}"
)
print(
    f"Recall   : {recall_score(y_test, predictions, zero_division=0):.4f}"
)
print(
    f"F1-score : {f1_score(y_test, predictions, zero_division=0):.4f}"
)

print("\nCLASSIFICATION REPORT")
print(
    classification_report(
        y_test,
        predictions,
        labels=[0, 1],
        target_names=["Not suitable", "Suitable"],
        zero_division=0,
    )
)

matrix = confusion_matrix(
    y_test,
    predictions,
    labels=[0, 1],
)

tn, fp, fn, tp = matrix.ravel()

print("\nCONFUSION MATRIX")
print("                    Predicted 0    Predicted 1")
print(f"Actual 0            {tn:11d}    {fp:11d}")
print(f"Actual 1            {fn:11d}    {tp:11d}")

print("\nINTERPRETATION")
print(f"True negatives : {tn}")
print(f"False positives: {fp}")
print(f"False negatives: {fn}")
print(f"True positives : {tp}")

print("\nIMPORTANT LIMITATIONS")
print("- Labels are synthetic and rule-derived.")
print("- Metrics do not measure real-world crop success.")
print("- This script evaluates a newly fitted baseline.")
print("- The deployed .joblib model is not modified.")
print("- Final rule-gated application decisions are not")
print("  independently evaluated by these metrics.")
