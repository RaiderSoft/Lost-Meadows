#!/usr/bin/env python3
"""
Train a single global XGBoost model on combined data from all 119 watersheds.

Outputs:
  - global_xgboost_model.pkl       : trained model (use with predict_meadows.py)
  - global_best_params.json        : best hyperparameters from gridsearch
  - global_model_log.txt           : global + per-watershed performance summary

Usage (from repo root):
  python GlobalModel/train_global_model.py [ncores]

Run on ORCA via:
  sbatch SLURM/submit_global_model.slurm
"""

import datetime
import json
import sys
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.metrics import classification_report, confusion_matrix, roc_auc_score
from sklearn.model_selection import (
    RandomizedSearchCV,
    StratifiedKFold,
    train_test_split,
)
from xgboost import XGBClassifier
import mlflow
import mlflow.xgboost

def get_repo_root():
    return Path(__file__).resolve().parents[1]

FEATURE_NAMES = [
    'slope', 'elev_5x5_rel', 'elev_5x5_std_dev', 'slope_5x5_std_dev',
    'twi_10m', 'twi_100m', 'dd_s', 'dd_h', 'dd_v',
    'aspect', 'curvature_profile', 'curvature_plan',
    'tpi_3x3', 'tpi_11x11', 'tpi_21x21', 'tri',
    'elev_std_3x3', 'elev_std_9x9', 'slope_std_9x9',
    'soil_clay_pct_0_5cm', 'soil_clay_pct_5_15cm', 'soil_clay_pct_15_30cm',
    'soil_ksat_0_5cm', 'soil_ksat_5_15cm', 'soil_ksat_15_30cm',
    'soil_organic_matter_0_5cm', 'soil_organic_matter_5_15cm', 'soil_organic_matter_15_30cm',
]

OUTPUT_DIR = get_repo_root() / "GlobalModel"
TRAINING_DIR = get_repo_root() / "GEE" / "TIF_Output" / "TrainingData"


def load_all_watersheds():
    """Load and combine all watershed CSVs, tracking watershed name per row."""
    csv_files = sorted(TRAINING_DIR.glob("*_training_data.csv"))
    if not csv_files:
        print(f"ERROR: No training CSVs found in {TRAINING_DIR}")
        sys.exit(1)

    print(f"Loading {len(csv_files)} watershed CSVs...")
    dfs = []
    for csv in csv_files:
        watershed = csv.name.replace("_training_data.csv", "")
        df = pd.read_csv(csv)
        df["watershed"] = watershed
        dfs.append(df)

    combined = pd.concat(dfs, ignore_index=True)
    print(f"Combined dataset: {len(combined):,} rows from {len(csv_files)} watersheds")
    print(f"  Wetland:     {combined['label'].sum():,} ({100*combined['label'].mean():.1f}%)")
    print(f"  Non-wetland: {(combined['label']==0).sum():,}")
    return combined


def run_gridsearch(X, y, watersheds, ncores=1):
    """Run randomized hyperparameter search on a watershed-stratified 50k subsample.

    Samples ~420 rows per watershed so every watershed is represented rather
    than risking the subsample being dominated by large watersheds.
    """
    print(f"\n{'='*60}")
    print("Hyperparameter Search (watershed-stratified 50k subsample, 5-fold CV)")
    print(f"{'='*60}")

    rng = np.random.RandomState(42)
    unique_ws = np.unique(watersheds)
    rows_per_ws = max(1, 50000 // len(unique_ws))
    idx_list = []
    for ws in unique_ws:
        ws_idx = np.where(watersheds == ws)[0]
        chosen = rng.choice(ws_idx, min(rows_per_ws, len(ws_idx)), replace=False)
        idx_list.append(chosen)
    idx = np.concatenate(idx_list)
    X_sub, y_sub = X[idx], y[idx]
    print(f"Subsampled to {len(idx):,} rows (~{rows_per_ws} per watershed, all {len(unique_ws)} watersheds represented)")

    param_dist = {
        'n_estimators':     [100, 200, 300],
        'max_depth':        [3, 4, 6, 8],
        'learning_rate':    [0.01, 0.05, 0.1, 0.2],
        'subsample':        [0.6, 0.8, 1.0],
        'colsample_bytree': [0.6, 0.8, 1.0],
        'gamma':            [0, 0.1, 0.5, 1.0],
        'reg_alpha':        [0, 0.1, 0.5],
        'reg_lambda':       [1, 1.5, 2.0],
        'min_child_weight': [1, 3, 5],
    }

    base = XGBClassifier(random_state=42, n_jobs=1, eval_metric='logloss', verbosity=0)
    cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)
    search = RandomizedSearchCV(
        base, param_dist, n_iter=100, scoring='roc_auc',
        cv=cv, random_state=42, n_jobs=ncores, verbose=1
    )
    search.fit(X_sub, y_sub)

    print(f"\nBest CV AUC: {search.best_score_:.4f}")
    print("Best params:")
    for k, v in sorted(search.best_params_.items()):
        print(f"  {k}: {v}")

    params = {k: v for k, v in search.best_params_.items()}
    params["best_cv_auc"] = round(float(search.best_score_), 4)
    params_path = OUTPUT_DIR / "global_best_params.json"
    with open(params_path, "w") as f:
        json.dump(params, f, indent=2)
    print(f"\nSaved: {params_path}")
    return params


def train_and_evaluate(combined_df, params, ncores=1):
    """Train global model and evaluate globally + per watershed."""
    X = combined_df[FEATURE_NAMES].values
    y = combined_df["label"].values
    watersheds = combined_df["watershed"].values

    X_train, X_test, y_train, y_test, ws_train, ws_test = train_test_split(
        X, y, watersheds, test_size=0.25, random_state=42, stratify=y
    )

    print(f"\n{'='*60}")
    print("Training Global XGBoost Model")
    print(f"{'='*60}")
    print(f"Train: {len(X_train):,}  |  Test: {len(X_test):,}")

    neg = int(np.sum(y_train == 0))
    pos = int(np.sum(y_train == 1))
    scale_pos_weight = round(neg / pos, 4)

    best_cv_auc = params.pop("best_cv_auc", None)
    xgb_params = {**params, "scale_pos_weight": scale_pos_weight, "random_state": 42}

    xgb = XGBClassifier(**xgb_params, n_jobs=ncores, eval_metric='logloss', verbosity=0)
    xgb.fit(X_train, y_train)
    print("Training complete!")

    # Global evaluation
    y_pred = xgb.predict(X_test)
    y_proba = xgb.predict_proba(X_test)[:, 1]
    auc = roc_auc_score(y_test, y_proba)
    cm = confusion_matrix(y_test, y_pred)
    report = classification_report(
        y_test, y_pred,
        target_names=["non_wetland", "wetland"],
        output_dict=True
    )

    print(f"\n{'='*60}")
    print("Global Performance")
    print(f"{'='*60}")
    print(classification_report(y_test, y_pred, target_names=["Non-Wetland", "Wetland"]))
    print(f"AUC: {auc:.4f}")

    # Per-watershed evaluation
    print(f"\n{'='*60}")
    print("Per-Watershed Breakdown")
    print(f"{'='*60}")
    print(f"{'Watershed':<50} {'AUC':>6} {'Recall':>7} {'Precision':>10} {'F1':>6} {'N':>7}")
    print("-" * 90)

    ws_results = []
    for ws in sorted(np.unique(ws_test)):
        mask = ws_test == ws
        if mask.sum() < 10:
            continue
        ws_auc = roc_auc_score(y_test[mask], y_proba[mask])
        ws_rep = classification_report(
            y_test[mask], y_pred[mask],
            target_names=["non_wetland", "wetland"],
            output_dict=True, zero_division=0
        )
        ws_results.append({
            "watershed": ws,
            "auc": ws_auc,
            "recall": ws_rep["wetland"]["recall"],
            "precision": ws_rep["wetland"]["precision"],
            "f1": ws_rep["wetland"]["f1-score"],
            "n": int(mask.sum()),
        })
        print(f"{ws:<50} {ws_auc:>6.4f} {ws_rep['wetland']['recall']:>7.4f} "
              f"{ws_rep['wetland']['precision']:>10.4f} {ws_rep['wetland']['f1-score']:>6.4f} {int(mask.sum()):>7,}")

    return xgb, auc, cm, report, ws_results, xgb_params, best_cv_auc, (X_train, X_test, y_train, y_test)


def write_log(auc, cm, report, ws_results, xgb_params, best_cv_auc, combined_df, split_sizes):
    X_train, X_test, y_train, y_test = split_sizes
    n_wetland = int(combined_df['label'].sum())
    n_non_wetland = int((combined_df['label'] == 0).sum())
    importances = None  # written separately below

    lines = [
        "=" * 80,
        "GLOBAL XGBOOST MODEL",
        f"Date/Time: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        f"Watersheds: 119",
        "=" * 80,
        "",
        "DATA SUMMARY",
        f"  Total samples:           {len(combined_df):,}",
        f"  Wetland (1):             {n_wetland:,}  ({100*n_wetland/len(combined_df):.1f}%)",
        f"  Non-wetland (0):         {n_non_wetland:,}  ({100*n_non_wetland/len(combined_df):.1f}%)",
        f"  Training set:            {len(X_train):,}",
        f"  Test set:                {len(X_test):,}",
        "",
        "HYPERPARAMETERS (tuned on 50k subsample)",
    ]
    if best_cv_auc:
        lines.append(f"  {'best_cv_auc':<25s} {best_cv_auc:.4f}")
    for k, v in sorted(xgb_params.items()):
        lines.append(f"  {k:<25s} {v}")
    lines += [
        "",
        "GLOBAL TEST SET PERFORMANCE",
        f"  AUC:                     {auc:.4f}",
        f"  Accuracy:                {report['accuracy']:.4f}",
        "",
        "  Wetland:",
        f"    Precision:             {report['wetland']['precision']:.4f}",
        f"    Recall:                {report['wetland']['recall']:.4f}",
        f"    F1-score:              {report['wetland']['f1-score']:.4f}",
        f"    Support:               {int(report['wetland']['support']):,}",
        "",
        "  Non-Wetland:",
        f"    Precision:             {report['non_wetland']['precision']:.4f}",
        f"    Recall:                {report['non_wetland']['recall']:.4f}",
        f"    F1-score:              {report['non_wetland']['f1-score']:.4f}",
        f"    Support:               {int(report['non_wetland']['support']):,}",
        "",
        "CONFUSION MATRIX",
        f"                       Predicted Non-W  Predicted Wetland",
        f"  Actual Non-W              {cm[0,0]:8,}          {cm[0,1]:8,}",
        f"  Actual Wetland            {cm[1,0]:8,}          {cm[1,1]:8,}",
        "",
        "PER-WATERSHED BREAKDOWN",
        f"  {'Watershed':<50} {'AUC':>6} {'Recall':>7} {'Precision':>10} {'F1':>6} {'N':>7}",
        "  " + "-" * 88,
    ]
    for r in ws_results:
        lines.append(
            f"  {r['watershed']:<50} {r['auc']:>6.4f} {r['recall']:>7.4f} "
            f"{r['precision']:>10.4f} {r['f1']:>6.4f} {r['n']:>7,}"
        )
    lines.append("")

    log_path = OUTPUT_DIR / "global_model_log.txt"
    with open(log_path, "w") as f:
        f.write("\n".join(lines))
    print(f"\n  ✓ Log written: {log_path}")


def main(ncores=1):
    combined_df = load_all_watersheds()

    X = combined_df[FEATURE_NAMES].values
    y = combined_df["label"].values

    params = run_gridsearch(X, y, combined_df["watershed"].values, ncores)

    xgb, auc, cm, report, ws_results, xgb_params, best_cv_auc, split_sizes = \
        train_and_evaluate(combined_df, params, ncores)

    # Save model
    model_path = OUTPUT_DIR / "global_xgboost_model.pkl"
    joblib.dump(xgb, model_path)
    print(f"\n  ✓ Model saved: {model_path}")

    # Feature importances
    importances = xgb.feature_importances_
    indices = np.argsort(importances)[::-1]
    print(f"\n{'='*60}")
    print("Feature Importances")
    print(f"{'='*60}")
    for i, idx in enumerate(indices, 1):
        print(f"  {i:2d}. {FEATURE_NAMES[idx]:<35s} {importances[idx]:.4f}")

    write_log(auc, cm, report, ws_results, xgb_params, best_cv_auc, combined_df, split_sizes)

    print(f"\n{'='*60}")
    print("Global model training complete!")
    print(f"{'='*60}")
    print(f"\nTo predict with the global model on a watershed:")
    print(f"  python ModelTraining/predict_meadows.py <watershed_name> global_xgboost_model.pkl")
    print(f"\nOr predict all watersheds at once:")
    print(f"  python GlobalModel/predict_all_watersheds.py")


if __name__ == "__main__":
    ncores = int(sys.argv[1]) if len(sys.argv) > 1 else 1
    main(ncores)
