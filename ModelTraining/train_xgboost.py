#!/usr/bin/env python3
"""
Train XGBoost model for meadow detection
Mirrors train_random_forest.py for direct comparison
"""

import numpy as np
import pandas as pd
from xgboost import XGBClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report, confusion_matrix, roc_auc_score
import joblib
import sys
from pathlib import Path

FEATURE_NAMES = [
    # Original 9 features
    'slope', 'elev_5x5_rel', 'elev_5x5_std_dev', 'slope_5x5_std_dev',
    'twi_10m', 'twi_100m', 'dd_s', 'dd_h', 'dd_v',
    # Advanced features (11)
    'aspect', 'curvature_profile', 'curvature_plan', 'elevation',
    'tpi_3x3', 'tpi_11x11', 'tpi_21x21', 'tri',
    'elev_std_3x3', 'elev_std_9x9', 'slope_std_9x9'
]

def load_training_data(watershed_name):
    base_dir = Path.home() / "Capstone" / "Lost-Meadows" / "GEE" / "TIF_Output" / watershed_name
    training_csv = base_dir / "training_data_real.csv"

    if not training_csv.exists():
        print(f"ERROR: Training CSV not found at {training_csv}")
        print("Run prepare_training_data.py first.")
        sys.exit(1)

    print(f"Loading training data from: {training_csv}")
    df = pd.read_csv(training_csv)

    features = df[FEATURE_NAMES].values
    labels = df['label'].values

    print(f"\nTraining data:")
    print(f"  Total samples:          {len(df):,}")
    print(f"  Wetland samples (1):    {np.sum(labels == 1):,}")
    print(f"  Non-wetland samples (0):{np.sum(labels == 0):,}")
    print(f"  Ratio:                  1:{np.sum(labels == 0) / np.sum(labels == 1):.1f}")

    return features, labels


def train_model(features, labels, watershed_name):
    """Train XGBoost classifier"""

    print(f"\n{'='*60}")
    print(f"Training XGBoost Model - {watershed_name}")
    print(f"{'='*60}\n")

    X_train, X_test, y_train, y_test = train_test_split(
        features, labels, test_size=0.25, random_state=42, stratify=labels
    )

    print(f"Training set: {X_train.shape[0]:,} samples")
    print(f"Testing set:  {X_test.shape[0]:,} samples")

    print(f"\nTraining XGBoost...")
    print(f"  - n_estimators:     200")
    print(f"  - max_depth:        8")
    print(f"  - learning_rate:    0.05")
    print(f"  - subsample:        0.8")
    print(f"  - colsample_bytree: 0.6")
    print(f"  - scale_pos_weight: 3")
    print(f"  - gamma:            0.5")
    print(f"  - reg_alpha:        0")
    print(f"  - reg_lambda:       2.0")
    print(f"  - min_child_weight: 1")
    print(f"  - random_state:     42")
    print(f"  (Parameters from RandomizedSearchCV, best CV AUC=0.9326)")

    xgb = XGBClassifier(
        n_estimators=200,
        max_depth=8,
        learning_rate=0.05,
        subsample=0.8,
        colsample_bytree=0.6,
        scale_pos_weight=3,
        gamma=0.5,
        reg_alpha=0,
        reg_lambda=2.0,
        min_child_weight=1,
        random_state=42,
        n_jobs=-1,
        eval_metric='logloss',
        verbosity=0
    )

    xgb.fit(X_train, y_train)

    print("\nModel training complete!")

    # Evaluate
    print(f"\n{'='*60}")
    print("Model Evaluation")
    print(f"{'='*60}\n")

    y_pred = xgb.predict(X_test)
    y_pred_proba = xgb.predict_proba(X_test)[:, 1]

    print("Classification Report:")
    print(classification_report(y_test, y_pred, target_names=['Non-Wetland', 'Wetland']))

    print("\nConfusion Matrix:")
    cm = confusion_matrix(y_test, y_pred)
    print(f"                 Predicted")
    print(f"               Non-W  Wetland")
    print(f"Actual Non-W   {cm[0,0]:5d}  {cm[0,1]:5d}")
    print(f"       Wetland {cm[1,0]:5d}  {cm[1,1]:5d}")

    auc = roc_auc_score(y_test, y_pred_proba)
    print(f"\nAUC Score: {auc:.3f}")
    print(f"(Paper reports AUC > 0.89 for local models)")

    # Feature importance
    print(f"\n{'='*60}")
    print("Feature Importance")
    print(f"{'='*60}\n")

    importances = xgb.feature_importances_
    indices = np.argsort(importances)[::-1]

    for i, idx in enumerate(indices, 1):
        print(f"{i:2d}. {FEATURE_NAMES[idx]:20s} {importances[idx]:.4f}")

    # Save model
    output_dir = Path.home() / "Capstone" / "Lost-Meadows" / "GEE" / "TIF_Output" / watershed_name
    model_path = output_dir / "xgboost_model.pkl"

    print(f"\nSaving model to: {model_path}")
    joblib.dump(xgb, model_path)
    print("Model saved successfully!")

    return xgb


def main(watershed_name):
    features, labels = load_training_data(watershed_name)
    train_model(features, labels, watershed_name)

    print(f"\n{'='*60}")
    print("Training Complete!")
    print(f"{'='*60}")
    print("\nTo predict with XGBoost:")
    print(f"  python predict_meadows.py {watershed_name} --model xgboost_model.pkl")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python train_xgboost.py <watershed_name>")
        print("\nExample:")
        print("  python train_xgboost.py Hunter_Creek_1710031205")
        base_dir = Path.home() / "Capstone" / "Lost-Meadows" / "GEE" / "TIF_Output"
        watersheds = [d.name for d in base_dir.iterdir() if d.is_dir() and not d.name.startswith('.')]
        if len(watersheds) == 1:
            watershed_name = watersheds[0]
            print(f"\nAuto-detected: {watershed_name}")
        else:
            print(f"\nAvailable watersheds: {', '.join(watersheds)}")
            sys.exit(1)
    else:
        watershed_name = sys.argv[1]

    main(watershed_name)
