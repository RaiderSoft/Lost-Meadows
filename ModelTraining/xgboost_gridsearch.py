#!/usr/bin/env python3
"""
Randomized hyperparameter search for XGBoost meadow detection model
Uses 10k samples for speed, then reports best parameters to use in train_xgboost.py

NOTE FOR NEW USERS:
This script is NOT part of the main production pipeline (run_pipeline.py).
It is a standalone tuning utility used to find the best hyperparameters for XGBoost.

How to use it:
    1. Run this script on a watershed to search across many parameter combinations:
           python xgboost_gridsearch.py <watershed_name>
    2. It will print the best parameters found.
    3. Copy those parameters manually into train_xgboost.py to use them in production.

This search runs on a 10k sample subset for speed. Once good parameters are found
they should be locked into train_xgboost.py — do not run this script on every
pipeline run, only when you want to re-tune the model.
"""

import numpy as np
import pandas as pd
from xgboost import XGBClassifier
from sklearn.model_selection import RandomizedSearchCV, StratifiedKFold, train_test_split
from sklearn.metrics import classification_report, roc_auc_score, f1_score
import sys
from pathlib import Path

def get_repo_root():
    # ModelTraining/xgboost_gridsearch.py
    return Path(__file__).resolve().parents[1]

FEATURE_NAMES = [
    # Terrain features (9)
    'slope', 'elev_5x5_rel', 'elev_5x5_std_dev', 'slope_5x5_std_dev',
    'twi_10m', 'twi_100m', 'dd_s', 'dd_h', 'dd_v',
    # Advanced terrain features (11)
    'aspect', 'curvature_profile', 'curvature_plan', 'elevation',
    'tpi_3x3', 'tpi_11x11', 'tpi_21x21', 'tri',
    'elev_std_3x3', 'elev_std_9x9', 'slope_std_9x9',
    # Soil features (3)
    'soil_depth_restrictive', 'soil_hydraulic_connectivity', 'soil_organic_matter',
]

def main(watershed_name):

    # Load training data
    csv = get_repo_root() / "GEE" / "TIF_Output" / watershed_name / "training_data_real.csv"
    if not csv.exists():
        print(f"ERROR: {csv} not found. Run prepare_training_data.py first.")
        sys.exit(1)

    print(f"Loading training data from: {csv}")
    df = pd.read_csv(csv)

    # Subsample to 10k for speed
    n_samples = min(10000, len(df))
    if len(df) > n_samples:
        df = df.sample(n=n_samples, random_state=42)
        print(f"Subsampled to {n_samples:,} rows for speed")

    X = df[FEATURE_NAMES].values
    y = df['label'].values

    print(f"Samples: {len(X):,}  |  Wetland: {y.sum():,}  |  Non-wetland: {(y==0).sum():,}")

    # Parameter grid
    param_dist = {
        'n_estimators':      [100, 200, 300],
        'max_depth':         [3, 4, 6, 8],
        'learning_rate':     [0.01, 0.05, 0.1, 0.2],
        'subsample':         [0.6, 0.8, 1.0],
        'colsample_bytree':  [0.6, 0.8, 1.0],
        'scale_pos_weight':  [1, 3, 5, 9],
        'gamma':             [0, 0.1, 0.5, 1.0],
        'reg_alpha':         [0, 0.1, 0.5],
        'reg_lambda':        [1, 1.5, 2.0],
        'min_child_weight':  [1, 3, 5],
    }

    base_model = XGBClassifier(
        random_state=42,
        n_jobs=-1,
        eval_metric='logloss',
        verbosity=0
    )

    cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)

    print(f"\n{'='*60}")
    print("Running RandomizedSearchCV")
    print(f"{'='*60}")
    print("  - 100 random combinations")
    print("  - 5-fold cross-validation")
    print("  - Scoring: AUC")
    print("  - This may take a few minutes...\n")

    search = RandomizedSearchCV(
        estimator=base_model,
        param_distributions=param_dist,
        n_iter=100,
        scoring='roc_auc',
        cv=cv,
        random_state=42,
        n_jobs=-1,
        verbose=1
    )

    search.fit(X, y)

    print(f"\n{'='*60}")
    print("Search Complete - Results")
    print(f"{'='*60}")
    print(f"\nBest CV AUC: {search.best_score_:.4f}")
    print(f"\nBest Parameters:")
    for k, v in sorted(search.best_params_.items()):
        print(f"  {k:25s}: {v}")

    # Evaluate best model on a held-out test set
    print(f"\n{'='*60}")
    print("Evaluating Best Model on Hold-out Test Set")
    print(f"{'='*60}")

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.25, random_state=42, stratify=y
    )

    best = search.best_estimator_
    best.fit(X_train, y_train)
    y_pred = best.predict(X_test)
    y_proba = best.predict_proba(X_test)[:, 1]

    print("\nClassification Report:")
    print(classification_report(y_test, y_pred, target_names=['Non-Wetland', 'Wetland']))
    print(f"AUC: {roc_auc_score(y_test, y_proba):.4f}")

    # Show top 10 combinations by AUC
    print(f"\n{'='*60}")
    print("Top 10 Parameter Combinations by AUC")
    print(f"{'='*60}")
    results = pd.DataFrame(search.cv_results_)
    top10 = results.sort_values('mean_test_score', ascending=False).head(10)
    for i, (_, row) in enumerate(top10.iterrows(), 1):
        print(f"\n{i}. AUC={row['mean_test_score']:.4f} (±{row['std_test_score']:.4f})")
        params = row['params']
        for k, v in sorted(params.items()):
            print(f"   {k:25s}: {v}")

    print(f"\n{'='*60}")
    print("Copy these best parameters into train_xgboost.py:")
    print(f"{'='*60}")
    for k, v in sorted(search.best_params_.items()):
        val = f"'{v}'" if isinstance(v, str) else v
        print(f"  {k}={val},")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python xgboost_gridsearch.py <watershed_name>")
        print("\nExample:")
        print("  python xgboost_gridsearch.py Bear_Creek_1710030801")
        base_dir = get_repo_root() / "GEE" / "TIF_Output"
        watersheds = [d.name for d in base_dir.iterdir() if d.is_dir() and not d.name.startswith('.')]
        if len(watersheds) == 1:
            print(f"\nAuto-detected: {watersheds[0]}")
            main(watersheds[0])
        else:
            print(f"\nAvailable watersheds: {', '.join(watersheds)}")
            sys.exit(1)
    else:
        main(sys.argv[1])
