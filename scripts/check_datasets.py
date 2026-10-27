import csv
from pathlib import Path
from collections import Counter
root = Path(__file__).resolve().parent.parent / "data" / "raw"
def load(n):
    with (root/n).open(newline="",encoding="utf-8-sig") as f:
        return list(csv.DictReader(f))
names=["crop_master.csv","crop_suitability.csv","soil_nutrient_thresholds.csv",
"crop_nutrient_requirements.csv","organic_fertilizers.csv",
"chemical_fertilizers.csv","crop_ml_training.csv"]
data={n:load(n) for n in names}
assert len(data[names[0]])==10
assert len(data[names[1]])==38
assert all(len(data[n])>0 for n in names)
assert all(not any("irrigat" in k.lower() for k in data[n][0]) for n in names)
master={r["crop_id"] for r in data[names[0]]}
rules={(r["crop_id"],r["soil_type"],r["season"]):r for r in data[names[1]]}
assert len(rules)==38
training=data[names[-1]]
assert len({r["sample_id"] for r in training})==len(training)
assert len({tuple(r[k] for k in ("N","P","K","pH","air_temperature","air_humidity","soil_type","season","crop_id")) for r in training})==len(training)
for r in training:
    assert r["crop_id"] in master
    rule=rules[(r["crop_id"],r["soil_type"],r["season"])]
    ok=(float(rule["ph_min"])<=float(r["pH"])<=float(rule["ph_max"]) and
        float(rule["air_temp_min"])<=float(r["air_temperature"])<=float(rule["air_temp_max"]))
    if rule["air_humidity_min"] and rule["air_humidity_max"]:
        ok=ok and float(rule["air_humidity_min"])<=float(r["air_humidity"])<=float(rule["air_humidity_max"])
    assert int(r["suitability_label"])==int(ok)
print("PASS: seven files; no irrigation; unique samples; all synthetic labels match provided suitability table.")
print("Records:",{n:len(v) for n,v in data.items()})
print("ML class counts:",dict(Counter(r["suitability_label"] for r in training)))
