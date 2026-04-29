#!/usr/bin/env python3
"""
Randomized hyperparameter search for XGBoost meadow detection model

This script is called automatically by run_pipeline.py before training to find
the best hyperparameters for each individual watershed. Results are saved to
best_params.json in the watershed output directory, which train_xgboost.py
reads automatically.

Can also be run standalone:
    python xgboost_gridsearch.py <watershed_name>
"""

import json
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
    'aspect', 'curvature_profile', 'curvature_plan',
    'tpi_3x3', 'tpi_11x11', 'tpi_21x21', 'tri',
    'elev_std_3x3', 'elev_std_9x9', 'slope_std_9x9',
    # Soil features (9) — POLARIS 30m, 3 depths
    'soil_clay_pct_0_5cm', 'soil_clay_pct_5_15cm', 'soil_clay_pct_15_30cm',
    'soil_ksat_0_5cm', 'soil_ksat_5_15cm', 'soil_ksat_15_30cm',
    'soil_organic_matter_0_5cm', 'soil_organic_matter_5_15cm', 'soil_organic_matter_15_30cm',
]

def main(watershed_name, ncores=1):

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
        n_jobs=1,
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
    print("  - This may take ~1 minute...\n")

    search = RandomizedSearchCV(
        estimator=base_model,
        param_distributions=param_dist,
        n_iter=100,
        scoring='roc_auc',
        cv=cv,
        random_state=42,
        n_jobs=ncores,
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

    # Save best params to JSON for train_xgboost.py to pick up automatically
    output_dir = get_repo_root() / "GEE" / "TIF_Output" / watershed_name
    params_path = output_dir / "best_params.json"
    # Don't save scale_pos_weight — train_xgboost.py computes it dynamically
    params_to_save = {k: v for k, v in search.best_params_.items() if k != "scale_pos_weight"}
    params_to_save["best_cv_auc"] = round(float(search.best_score_), 4)
    with open(params_path, "w") as f:
        json.dump(params_to_save, f, indent=2)
    print(f"\n{'='*60}")
    print(f"Best parameters saved to: {params_path}")
    print("train_xgboost.py will use these automatically.")
    print(f"{'='*60}")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python xgboost_gridsearch.py <watershed_name> [ncores]")
        print("\nExample:")
        print("  python xgboost_gridsearch.py Bear_Creek_1710030801 4")
        base_dir = get_repo_root() / "GEE" / "TIF_Output"
        watersheds = [d.name for d in base_dir.iterdir() if d.is_dir() and not d.name.startswith('.')]
        if len(watersheds) == 1:
            print(f"\nAuto-detected: {watersheds[0]}")
            main(watersheds[0])
        else:
            print(f"\nAvailable watersheds: {', '.join(watersheds)}")
            sys.exit(1)
    else:
        ncores = int(sys.argv[2]) if len(sys.argv) > 2 else 1
        main(sys.argv[1], ncores)
