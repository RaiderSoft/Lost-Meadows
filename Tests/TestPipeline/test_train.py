#!/usr/bin/env python3
"""
Minimal XGBoost training script for pipeline testing.
Trains on the synthetic CSV produced by run_test.py and saves the model
to the same location that predict_meadows.py expects.

Does NOT connect to DagsHub/MLflow — this is intentional. The test only
needs to verify that XGBoost can train and the model file can be produced.
Real experiment tracking happens when you run train_xgboost.py directly.

Usage (called automatically by run_test.py):
    python Tests/TestPipeline/test_train.py <watershed_name>
"""

import json
import sys
import numpy as np
import pandas as pd
import joblib
from xgboost import XGBClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import roc_auc_score
from pathlib import Path

FEATURE_NAMES = [
    "slope", "elev_5x5_rel", "elev_5x5_std_dev", "slope_5x5_std_dev",
    "twi_10m", "twi_100m", "dd_s", "dd_h", "dd_v",
    "aspect", "curvature_profile", "curvature_plan", "elevation",
    "tpi_3x3", "tpi_11x11", "tpi_21x21", "tri",
    "elev_std_3x3", "elev_std_9x9", "slope_std_9x9",
    "soil_depth_restrictive", "soil_hydraulic_connectivity", "soil_organic_matter",
]

def main(watershed_name):
    repo_root = Path(__file__).resolve().parents[2]
    output_dir = repo_root / "GEE" / "TIF_Output" / watershed_name
    csv_path = output_dir / "training_data_real.csv"
    model_path = output_dir / "xgboost_model.pkl"

    df = pd.read_csv(csv_path)
    X = df[FEATURE_NAMES].values
    y = df["label"].values

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.25, random_state=42, stratify=y
    )

    pos = np.sum(y_train == 1)
    neg = np.sum(y_train == 0)
    scale_pos_weight = neg / pos if pos > 0 else 1.0

    # Load tuned params from grid search if available
    params_path = output_dir / "best_params.json"
    if params_path.exists():
        with open(params_path) as f:
            tuned = json.load(f)
        tuned.pop("scale_pos_weight", None)
        tuned["n_estimators"] = 10  # Keep fast for test regardless of tuned value
    else:
        tuned = {"max_depth": 4, "learning_rate": 0.1}

    model = XGBClassifier(
        n_estimators=10,          # Reduced from tuned value — speed only, not accuracy
        **{k: v for k, v in tuned.items() if k != "n_estimators"},
        scale_pos_weight=scale_pos_weight,
        random_state=42,
        eval_metric="logloss",
        verbosity=0,
    )
    model.fit(X_train, y_train)

    y_prob = model.predict_proba(X_test)[:, 1]
    auc = roc_auc_score(y_test, y_prob)
    print(f"Test AUC: {auc:.3f}")

    joblib.dump(model, model_path)
    print(f"Model saved to {model_path}")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python test_train.py <watershed_name>")
        sys.exit(1)
    main(sys.argv[1])
