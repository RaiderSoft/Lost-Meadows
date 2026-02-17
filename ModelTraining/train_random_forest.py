#!/usr/bin/env python3
"""
Train Random Forest model for meadow detection
Uses real wetland labels from CSV if available, otherwise falls back to synthetic labels
"""

import rasterio
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report, confusion_matrix, roc_auc_score
import joblib
import sys
from pathlib import Path

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
            # Original 9 features
            'slope', 'elev_5x5_rel', 'elev_5x5_std_dev', 'slope_5x5_std_dev',
            'twi_10m', 'twi_100m', 'dd_s', 'dd_h', 'dd_v',
            # Advanced features (11)
            'aspect', 'curvature_profile', 'curvature_plan', 'elevation',
            'tpi_3x3', 'tpi_11x11', 'tpi_21x21', 'tri',
            'elev_std_3x3', 'elev_std_9x9', 'slope_std_9x9',
            # Climate features (2)
            'precip_annual', 'precip_spring'
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

def train_model(features, labels, watershed_name):
    """Train Random Forest classifier"""

    print(f"\n{'='*60}")
    print(f"Training Random Forest Model - {watershed_name}")
    print(f"{'='*60}\n")
    
    # Split into train/test (75/25 split per paper)
    X_train, X_test, y_train, y_test = train_test_split(
        features, labels, test_size=0.25, random_state=42, stratify=labels
    )
    
    print(f"Training set: {X_train.shape[0]:,} samples")
    print(f"Testing set: {X_test.shape[0]:,} samples")
    
    # Train Random Forest (parameters from paper, adapted for 20 features)
    print("\nTraining Random Forest...")
    print("  - n_estimators: 300")
    print("  - max_features: 'sqrt' (~4.5 for 20 features)")
    print("  - random_state: 42")

    rf = RandomForestClassifier(
        n_estimators=300,
        max_features='sqrt',  # sqrt(20) ≈ 4.5
        random_state=42,
        n_jobs=-1,
        verbose=1
    )
    
    rf.fit(X_train, y_train)
    
    print("\n✓ Model training complete!")
    
    # Evaluate on test set
    print(f"\n{'='*60}")
    print("Model Evaluation")
    print(f"{'='*60}\n")
    
    y_pred = rf.predict(X_test)
    y_pred_proba = rf.predict_proba(X_test)[:, 1]
    
    # Metrics
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
    
    feature_names = [
        # Original 9 features
        "slope", "elev_5x5_rel", "elev_5x5_std_dev", "slope_5x5_std_dev",
        "twi_10m", "twi_100m", "dd_s", "dd_h", "dd_v",
        # Advanced features (11)
        "aspect", "curvature_profile", "curvature_plan", "elevation",
        "tpi_3x3", "tpi_11x11", "tpi_21x21", "tri",
        "elev_std_3x3", "elev_std_9x9", "slope_std_9x9",
        # Climate features (2)
        "precip_annual", "precip_spring"
    ]
    
    importances = rf.feature_importances_
    indices = np.argsort(importances)[::-1]
    
    for i, idx in enumerate(indices, 1):
        print(f"{i}. {feature_names[idx]:20s} {importances[idx]:.4f}")
    
    # Save model
    repo_root = get_repo_root()
    output_dir = repo_root / "GEE" / "TIF_Output" / watershed_name
    model_path = output_dir / "random_forest_model.pkl"

    print(f"\nSaving model to: {model_path}")
    joblib.dump(rf, model_path)

    print("\n✓ Model saved successfully!")

    return rf

def main(watershed_name):
    """Main training pipeline"""

    # Load training data (real or synthetic)
    features, labels = load_training_data(watershed_name)

    # Train model
    model = train_model(features, labels, watershed_name)

    print(f"\n{'='*60}")
    print("Training Complete!")
    print(f"{'='*60}")
    print("\nNext step: Use the model to predict wetland probabilities")
    print(f"  python predict_meadows.py {watershed_name}")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python train_random_forest.py <watershed_name>")
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
        watershed_name = sys.argv[1]

    main(watershed_name)