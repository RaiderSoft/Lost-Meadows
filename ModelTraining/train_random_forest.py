#!/usr/bin/env python3
"""
Train Random Forest model for meadow detection
Uses real wetland labels from CSV if available, otherwise falls back to synthetic labels
"""

import rasterio
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split, GridSearchCV
from sklearn.metrics import classification_report, confusion_matrix, roc_auc_score
import joblib
import sys
from pathlib import Path
import mlflow
import mlflow.sklearn
from mlflow_config import init_mlflow

MLFLOW_EXPERIMENT = "random-forest-meadow"


def get_repo_root():
    # ModelTraining/train_random_forest.py
    return Path(__file__).resolve().parents[1]

def load_training_data(watershed_name):
    """
    Load training data from CSV (real wetland labels)
    Falls back to synthetic labels if CSV doesn't exist
    """
    repo_root = get_repo_root()
    base_dir = repo_root / "GEE" / "TIF_Output" / watershed_name
    training_csv = base_dir / "training_data_real.csv"
    
    if training_csv.exists():
        print(f"Loading real training data from: {training_csv}")
        df = pd.read_csv(training_csv)
        
        feature_names = [
            'slope', 'elev_5x5_rel', 'elev_5x5_std_dev', 'slope_5x5_std_dev',
            'twi_10m', 'twi_100m', 'dd_s', 'dd_h', 'dd_v',
            # Advanced features (11)
            'aspect', 'curvature_profile', 'curvature_plan', 'elevation',
            'tpi_3x3', 'tpi_11x11', 'tpi_21x21', 'tri',
            'elev_std_3x3', 'elev_std_9x9', 'slope_std_9x9'
        ]
        
        features = df[feature_names].values
        labels = df['label'].values
        
        print(f"\nReal wetland training data:")
        print(f"  Total samples: {len(df):,}")
        print(f"  Wetland samples (1): {np.sum(labels == 1):,}")
        print(f"  Non-wetland samples (0): {np.sum(labels == 0):,}")
        print(f"  Ratio: 1:{np.sum(labels == 0) / np.sum(labels == 1):.1f}")
        
        print(f"\nFeature value ranges:")
        for i, name in enumerate(feature_names):
            print(f"  {name:20s} [{features[:, i].min():.2f}, {features[:, i].max():.2f}]")
        
        return features, labels
    
    else:
        print(f"WARNING: Real training CSV not found at {training_csv}")
        print("Falling back to synthetic labels (TWI-based)")
        return extract_samples_from_raster_synthetic(base_dir / "features_stacked.tif")

def extract_samples_from_raster_synthetic(raster_path, n_samples=10000):
    """
    Extract random samples with synthetic labels (fallback method)
    """
    print(f"\nReading features from: {raster_path}")
    
    with rasterio.open(raster_path) as src:
        data = src.read()
        n_bands, height, width = data.shape
        
        print(f"Raster shape: {n_bands} bands, {height}x{width} pixels")
        
        data_flat = data.reshape(n_bands, -1).T
        
        valid_mask = np.ones(data_flat.shape[0], dtype=bool)
        valid_mask &= ~np.any(np.isnan(data_flat), axis=1)
        valid_mask &= ~np.any(np.isinf(data_flat), axis=1)
        valid_mask &= ~np.any(data_flat < -1e30, axis=1)
        
        data_clean = data_flat[valid_mask]
        
        print(f"Valid pixels: {data_clean.shape[0]:,} ({100*data_clean.shape[0]/data_flat.shape[0]:.1f}%)")
        
        if data_clean.shape[0] == 0:
            print("\nERROR: No valid pixels found!")
            sys.exit(1)
        
        if data_clean.shape[0] > n_samples:
            indices = np.random.choice(data_clean.shape[0], n_samples, replace=False)
            sampled_data = data_clean[indices]
        else:
            sampled_data = data_clean
            print(f"Note: Using all {data_clean.shape[0]} valid pixels")
        
        print(f"\nSample data shape: {sampled_data.shape}")
        
        twi_values = sampled_data[:, 4]  # twi_10m
        twi_threshold = np.percentile(twi_values, 90)
        labels = (twi_values > twi_threshold).astype(int)
        
        print(f"\nSynthetic labels (TWI threshold = {twi_threshold:.2f}):")
        print(f"  Meadow samples (1): {np.sum(labels == 1)}")
        print(f"  Non-meadow samples (0): {np.sum(labels == 0)}")
        
        return sampled_data, labels

def train_model(features, labels, watershed_name, use_grid_search=False):
    """Train Random Forest classifier and log everything to MLflow / DagsHub."""

    print(f"\n{'='*60}")
    print(f"Training Random Forest Model - {watershed_name}")
    print(f"{'='*60}\n")

    # Split into train/test (75/25 split per paper)
    X_train, X_test, y_train, y_test = train_test_split(
        features, labels, test_size=0.25, random_state=42, stratify=labels
    )

    print(f"Training set: {X_train.shape[0]:,} samples")
    print(f"Testing set: {X_test.shape[0]:,} samples")

    with mlflow.start_run(run_name=watershed_name):

        # ---- tags -------------------------------------------------------
        mlflow.set_tags({
            "watershed": watershed_name,
            "model_type": "RandomForest",
            "label_source": "real" if "training_data_real.csv" in str(
                get_repo_root() / "GEE" / "TIF_Output" / watershed_name / "training_data_real.csv"
            ) and (get_repo_root() / "GEE" / "TIF_Output" / watershed_name / "training_data_real.csv").exists()
            else "synthetic",
        })

        # ---- data params ------------------------------------------------
        n_wetland = int(np.sum(labels == 1))
        n_non_wetland = int(np.sum(labels == 0))
        mlflow.log_params({
            "test_size": 0.25,
            "random_state": 42,
            "n_features": features.shape[1],
            "n_samples_total": len(labels),
            "n_samples_train": X_train.shape[0],
            "n_samples_test": X_test.shape[0],
            "n_wetland": n_wetland,
            "n_non_wetland": n_non_wetland,
            "class_ratio_neg_pos": round(n_non_wetland / max(n_wetland, 1), 2),
            "use_grid_search": use_grid_search,
        })

        # ---- model training ---------------------------------------------
        if use_grid_search:
            print("\nRunning GridSearchCV for Random Forest...")

            param_grid = {
                "n_estimators": list(range(50, 301, 50)),
                "max_depth": [None, 10, 20],
                "min_samples_split": [2, 5],
                "min_samples_leaf": [1, 2],
                "bootstrap": [True, False],
                "class_weight": [None, "balanced", "balanced_subsample", {0: 1, 1: 3}, {0: 1, 1: 5}],
            }

            base_rf = RandomForestClassifier(random_state=42, n_jobs=-1)

            grid_search = GridSearchCV(
                estimator=base_rf,
                param_grid=param_grid,
                cv=5,
                scoring="roc_auc",
                n_jobs=-1,
                verbose=2,
            )
            grid_search.fit(X_train, y_train)

            print("\nBest Parameters:")
            print(grid_search.best_params_)
            print("\nBest Estimator:")
            print(grid_search.best_estimator_)

            rf = grid_search.best_estimator_
            mlflow.log_params(grid_search.best_params_)
            mlflow.log_metric("cv_best_roc_auc", grid_search.best_score_)
        else:
            print("\nTraining Random Forest...")
            print("  - n_estimators: 300")
            print("  - max_features: 'sqrt' (~4.5 for 20 features)")
            print("  - random_state: 42")

            rf = RandomForestClassifier(
                n_estimators=300,
                max_features="sqrt",
                random_state=42,
                n_jobs=-1,
                verbose=1,
            )
            mlflow.log_params({
                "n_estimators": 300,
                "max_features": "sqrt",
                "max_depth": "None",
                "min_samples_split": 2,
                "min_samples_leaf": 1,
                "bootstrap": True,
                "class_weight": "None",
            })

        rf.fit(X_train, y_train)
        print("\n Model training complete!")

        # ---- evaluation -------------------------------------------------
        print(f"\n{'='*60}")
        print("Model Evaluation")
        print(f"{'='*60}\n")

        y_pred = rf.predict(X_test)
        y_pred_proba = rf.predict_proba(X_test)[:, 1]

        print("Classification Report:")
        print(classification_report(y_test, y_pred, target_names=["Non-Wetland", "Wetland"]))

        print("\nConfusion Matrix:")
        cm = confusion_matrix(y_test, y_pred)
        print(f"                 Predicted")
        print(f"               Non-W  Wetland")
        print(f"Actual Non-W   {cm[0,0]:5d}  {cm[0,1]:5d}")
        print(f"       Wetland {cm[1,0]:5d}  {cm[1,1]:5d}")

        auc = roc_auc_score(y_test, y_pred_proba)
        print(f"\nAUC Score: {auc:.3f}")
        print(f"(Paper reports AUC > 0.89 for local models)")

        # Per-class report dict for easy metric extraction
        report = classification_report(
            y_test, y_pred,
            target_names=["non_wetland", "wetland"],
            output_dict=True,
        )

        mlflow.log_metrics({
            "roc_auc": round(auc, 4),
            "accuracy": round(report["accuracy"], 4),
            # wetland class
            "wetland_precision": round(report["wetland"]["precision"], 4),
            "wetland_recall":    round(report["wetland"]["recall"], 4),
            "wetland_f1":        round(report["wetland"]["f1-score"], 4),
            # non-wetland class
            "non_wetland_precision": round(report["non_wetland"]["precision"], 4),
            "non_wetland_recall":    round(report["non_wetland"]["recall"], 4),
            "non_wetland_f1":        round(report["non_wetland"]["f1-score"], 4),
            # confusion matrix cells
            "cm_tn": int(cm[0, 0]),
            "cm_fp": int(cm[0, 1]),
            "cm_fn": int(cm[1, 0]),
            "cm_tp": int(cm[1, 1]),
        })

        # ---- feature importance -----------------------------------------
        print(f"\n{'='*60}")
        print("Feature Importance")
        print(f"{'='*60}\n")

        feature_names = [
            "slope", "elev_5x5_rel", "elev_5x5_std_dev", "slope_5x5_std_dev",
            "twi_10m", "twi_100m", "dd_s", "dd_h", "dd_v",
            "aspect", "curvature_profile", "curvature_plan", "elevation",
            "tpi_3x3", "tpi_11x11", "tpi_21x21", "tri",
            "elev_std_3x3", "elev_std_9x9", "slope_std_9x9",
        ]

        importances = rf.feature_importances_
        indices = np.argsort(importances)[::-1]

        for i, idx in enumerate(indices, 1):
            print(f"{i}. {feature_names[idx]:20s} {importances[idx]:.4f}")

        # Log individual feature importances as metrics
        for name, imp in zip(feature_names, importances):
            mlflow.log_metric(f"importance_{name}", round(float(imp), 6))

        # ---- save & log model artifact ----------------------------------
        repo_root = get_repo_root()
        output_dir = repo_root / "GEE" / "TIF_Output" / watershed_name
        model_path = output_dir / "random_forest_model.pkl"

        print(f"\nSaving model to: {model_path}")
        joblib.dump(rf, model_path)
        mlflow.sklearn.log_model(rf, name="random_forest_model")

        print(" Model saved and logged to MLflow!")
        print(f" Run URL: {mlflow.get_tracking_uri()}")

    return rf

def main(watershed_name, use_grid_search=False):
    """Main training pipeline"""

    # Initialise DagsHub remote tracking
    init_mlflow(MLFLOW_EXPERIMENT)

    # Load training data (real or synthetic)
    features, labels = load_training_data(watershed_name)

    # Train model
    model = train_model(features, labels, watershed_name, use_grid_search=use_grid_search)

    print(f"\n{'='*60}")
    print("Training Complete!")
    print(f"{'='*60}")
    print("\nNext step: Use the model to predict wetland probabilities")
    print(f"  python predict_meadows.py {watershed_name}")

if __name__ == "__main__":
    args = sys.argv[1:]
    use_grid_search = False
    if "--grid-search" in args:
        use_grid_search = True
        args.remove("--grid-search")

    if len(args) < 1:
        print("Usage: python train_random_forest.py <watershed_name>")
        print("       python train_random_forest.py <watershed_name> --grid-search")
        print("\nExample:")
        print("  python train_random_forest.py Bear_Creek_Watershed_10m")
        # Auto-detect if only one watershed directory exists
        repo_root = get_repo_root()
        base_dir = repo_root / "GEE" / "TIF_Output"
        watersheds = [d.name for d in base_dir.iterdir() if d.is_dir() and not d.name.startswith('.')]
        if len(watersheds) == 1:
            watershed_name = watersheds[0]
            print(f"\nAuto-detected: {watershed_name}")
        else:
            print(f"\nAvailable watersheds: {', '.join(watersheds)}")
            sys.exit(1)
    else:
        watershed_name = args[0]

    main(watershed_name, use_grid_search=use_grid_search)
