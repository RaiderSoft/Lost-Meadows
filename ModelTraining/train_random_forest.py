#!/usr/bin/env python3
"""
Train Random Forest model for meadow detection
For testing: uses random sampling without real meadow polygons
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

def extract_samples_from_raster(raster_path, n_samples=10000):
    """
    Extract random samples from stacked feature raster
    For testing purposes - creates synthetic labels based on TWI
    """
    print(f"Reading features from: {raster_path}")
    
    with rasterio.open(raster_path) as src:
        # Read all bands
        data = src.read()  # Shape: (bands, height, width)
        n_bands, height, width = data.shape
        
        print(f"Raster shape: {n_bands} bands, {height}x{width} pixels")
        
        # Flatten spatial dimensions
        data_flat = data.reshape(n_bands, -1).T  # Shape: (pixels, bands)
        
        # TauDEM uses -3.4028235e+38 as NoData
        taudem_nodata = -3.4028235e+38
        
        # Create mask for valid pixels
        valid_mask = np.ones(data_flat.shape[0], dtype=bool)
        
        # Remove NaN values
        valid_mask &= ~np.any(np.isnan(data_flat), axis=1)
        
        # Remove infinite values
        valid_mask &= ~np.any(np.isinf(data_flat), axis=1)
        
        # Remove TauDEM NoData values (check if close to NoData value)
        valid_mask &= ~np.any(data_flat < -1e30, axis=1)
        
        data_clean = data_flat[valid_mask]
        
        print(f"Valid pixels: {data_clean.shape[0]:,} ({100*data_clean.shape[0]/data_flat.shape[0]:.1f}%)")
        
        if data_clean.shape[0] == 0:
            print("\nERROR: No valid pixels found!")
            sys.exit(1)
        
        # Sample random pixels
        if data_clean.shape[0] > n_samples:
            indices = np.random.choice(data_clean.shape[0], n_samples, replace=False)
            sampled_data = data_clean[indices]
        else:
            sampled_data = data_clean
            print(f"Note: Using all {data_clean.shape[0]} valid pixels")
        
        print(f"\nSample data shape: {sampled_data.shape}")
        print(f"Feature value ranges:")
        feature_names = [
            "slope", "elev_5x5_rel", "elev_5x5_std_dev", "slope_5x5_std_dev",
            "twi_10m", "twi_100m", "dd_s", "dd_h", "dd_v"
        ]
        for i, name in enumerate(feature_names):
            print(f"  {name:20s} [{sampled_data[:, i].min():.2f}, {sampled_data[:, i].max():.2f}]")
        
        # Create synthetic labels based on TWI (band 4: twi_10m)
        # High TWI values are more likely to be meadows
        twi_values = sampled_data[:, 4]  # twi_10m is band 5 (index 4)
        
        # Simple threshold: top 10% of TWI values = meadow
        twi_threshold = np.percentile(twi_values, 90)
        labels = (twi_values > twi_threshold).astype(int)
        
        print(f"\nSynthetic labels created (TWI threshold = {twi_threshold:.2f}):")
        print(f"  Meadow samples (1): {np.sum(labels == 1)}")
        print(f"  Non-meadow samples (0): {np.sum(labels == 0)}")
        
        return sampled_data, labels

def train_model(features, labels, run_num):
    """Train Random Forest classifier"""
    
    print(f"\n{'='*60}")
    print("Training Random Forest Model")
    print(f"{'='*60}\n")
    
    # Split into train/test (75/25 split per paper)
    X_train, X_test, y_train, y_test = train_test_split(
        features, labels, test_size=0.25, random_state=42, stratify=labels
    )
    
    print(f"Training set: {X_train.shape[0]:,} samples")
    print(f"Testing set: {X_test.shape[0]:,} samples")
    
    # Train Random Forest (parameters from paper)
    print("\nTraining Random Forest...")
    print("  - n_estimators: 300")
    print("  - max_features: 4 (mtry)")
    print("  - random_state: 42")
    
    rf = RandomForestClassifier(
        n_estimators=300,
        max_features=4,
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
    print(classification_report(y_test, y_pred, target_names=['Non-Meadow', 'Meadow']))
    
    print("\nConfusion Matrix:")
    cm = confusion_matrix(y_test, y_pred)
    print(f"                 Predicted")
    print(f"               Non-M  Meadow")
    print(f"Actual Non-M   {cm[0,0]:5d}  {cm[0,1]:5d}")
    print(f"       Meadow  {cm[1,0]:5d}  {cm[1,1]:5d}")
    
    auc = roc_auc_score(y_test, y_pred_proba)
    print(f"\nAUC Score: {auc:.3f}")
    print(f"(Paper reports AUC > 0.89 for local models)")
    
    # Feature importance
    print(f"\n{'='*60}")
    print("Feature Importance")
    print(f"{'='*60}\n")
    
    feature_names = [
        "slope", "elev_5x5_rel", "elev_5x5_std_dev", "slope_5x5_std_dev",
        "twi_10m", "twi_100m", "dd_s", "dd_h", "dd_v"
    ]
    
    importances = rf.feature_importances_
    indices = np.argsort(importances)[::-1]
    
    for i, idx in enumerate(indices, 1):
        print(f"{i}. {feature_names[idx]:20s} {importances[idx]:.4f}")
    
    # Save model
    output_dir = Path.home() / "Capstone" / "Lost-Meadows" / "GEE" / "TIF_Output" / str(run_num)
    model_path = output_dir / "random_forest_model.pkl"
    
    print(f"\nSaving model to: {model_path}")
    joblib.dump(rf, model_path)
    
    print("\n✓ Model saved successfully!")
    
    return rf

def main(run_num):
    """Main training pipeline"""
    
    # Input files
    base_dir = Path.home() / "Capstone" / "Lost-Meadows" / "GEE" / "TIF_Output" / str(run_num)
    raster_path = base_dir / "features_stacked.tif"
    
    if not raster_path.exists():
        print(f"ERROR: {raster_path} not found!")
        print("Run stack_features.py first!")
        sys.exit(1)
    
    # Extract samples
    features, labels = extract_samples_from_raster(str(raster_path), n_samples=10000)
    
    # Train model
    model = train_model(features, labels, run_num)
    
    print(f"\n{'='*60}")
    print("Training Complete!")
    print(f"{'='*60}")
    print("\nNext step: Use the model to predict meadow probabilities across the entire raster")

if __name__ == "__main__":
    run_num = sys.argv[1] if len(sys.argv) > 1 else "1"
    main(run_num)