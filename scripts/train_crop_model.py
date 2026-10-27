"""Optional Phase 2 ML baseline: synthetic labels only, NOT field accuracy."""
from pathlib import Path
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import classification_report
from sklearn.model_selection import GroupShuffleSplit
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder
import joblib

root = Path(__file__).resolve().parent.parent / "data" / "raw"
df=pd.read_csv(root/"crop_ml_training.csv")
categorical=["crop_id","soil_type","season"]
numeric=["pH","air_temperature","air_humidity"]
features=categorical+numeric
X=df[features]
y=df["suitability_label"].astype(int)
groups=df["scenario_id"]
split=GroupShuffleSplit(n_splits=1,test_size=0.2,random_state=42)
tr,te=next(split.split(X,y,groups))
pipeline=Pipeline([
 ("preprocess",ColumnTransformer([
   ("categorical",OneHotEncoder(handle_unknown="ignore"),categorical),
   ("numeric","passthrough",numeric)
 ])),
 ("classifier",RandomForestClassifier(n_estimators=250,random_state=42,
                                      class_weight="balanced"))
])
pipeline.fit(X.iloc[tr],y.iloc[tr])
pred=pipeline.predict(X.iloc[te])
print("SYNTHETIC RULE-LABEL EVALUATION ONLY — NOT AGRONOMIC ACCURACY")
print(classification_report(y.iloc[te],pred,zero_division=0))
model_path = Path(__file__).resolve().parent.parent / "models" / "crop_suitability_demo_model.joblib"
joblib.dump(pipeline, model_path)
print("Saved crop_suitability_demo_model.joblib")
print("IMPORTANT: For a new crop/soil/season not in crop_suitability.csv,")
print("return 'insufficient data' instead of trusting an extrapolated ML label.")
