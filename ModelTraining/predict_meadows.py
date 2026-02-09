#!/usr/bin/env python3
"""
Apply trained Random Forest model to predict meadow probabilities
across the entire watershed
"""

import rasterio
import numpy as np
import joblib
import sys
from pathlib import Path

def predict_probabilities(features_path, model_path, output_path, chunk_size=1000):
    """
    Apply model to entire raster in chunks to avoid memory issues
    """
    print(f"\n{'='*60}")
    print("Predicting Meadow Probabilities")
    print(f"{'='*60}\n")
    
    # Load model
    print(f"Loading model from: {model_path}")
    model = joblib.load(model_path)
    print(f"✓ Model loaded (n_estimators={model.n_estimators})")
    
    # Open features raster
    print(f"\nReading features from: {features_path}")
    with rasterio.open(features_path) as src:
        profile = src.profile.copy()
        n_bands, height, width = src.count, src.height, src.width
        
        print(f"Raster dimensions: {n_bands} bands, {height}x{width} pixels")
        print(f"Total pixels: {height * width:,}")
        
        # Create output array
        probabilities = np.full((height, width), -9999.0, dtype='float32')
        
        print("\nProcessing in chunks...")
        n_chunks = (height + chunk_size - 1) // chunk_size
        
        for chunk_idx in range(n_chunks):
            start_row = chunk_idx * chunk_size
            end_row = min(start_row + chunk_size, height)
            
            # Read chunk
            window = ((start_row, end_row), (0, width))
            data_chunk = src.read(window=window)  # Shape: (bands, rows, cols)
            
            # Reshape to (pixels, bands)
            chunk_height = end_row - start_row
            data_flat = data_chunk.reshape(n_bands, -1).T
            
            # Find valid pixels (no NaN, no extreme values)
            valid_mask = ~np.any(np.isnan(data_flat), axis=1)
            valid_mask &= ~np.any(np.isinf(data_flat), axis=1)
            valid_mask &= ~np.any(data_flat < -1e30, axis=1)
            
            # Predict for valid pixels
            if np.sum(valid_mask) > 0:
                predictions = model.predict_proba(data_flat[valid_mask])[:, 1]
                
                # Place predictions back into chunk
                prob_chunk = np.full(data_flat.shape[0], -9999.0)
                prob_chunk[valid_mask] = predictions
                
                # Reshape back to 2D
                prob_chunk_2d = prob_chunk.reshape(chunk_height, width)
                probabilities[start_row:end_row, :] = prob_chunk_2d
            
            # Progress
            if (chunk_idx + 1) % 10 == 0 or (chunk_idx + 1) == n_chunks:
                pct = 100 * (chunk_idx + 1) / n_chunks
                print(f"  Chunk {chunk_idx + 1}/{n_chunks} ({pct:.1f}%)")
        
        print("\n✓ Prediction complete!")
        
        # Calculate statistics
        valid_probs = probabilities[probabilities > -9999]
        print(f"\nPrediction Statistics:")
        print(f"  Valid pixels: {len(valid_probs):,}")
        print(f"  Min probability: {valid_probs.min():.4f}")
        print(f"  Max probability: {valid_probs.max():.4f}")
        print(f"  Mean probability: {valid_probs.mean():.4f}")
        print(f"  Median probability: {np.median(valid_probs):.4f}")
        
        # High-confidence meadow pixels (>0.5 threshold from paper)
        high_conf = np.sum(valid_probs > 0.5)
        high_conf_pct = 100 * high_conf / len(valid_probs)
        print(f"\nHigh-confidence meadow pixels (>0.5): {high_conf:,} ({high_conf_pct:.2f}%)")
        
        # Area calculation (10m pixels = 100 m²)
        pixel_area_m2 = 100
        meadow_area_ha = (high_conf * pixel_area_m2) / 10000
        print(f"Predicted meadow area: {meadow_area_ha:.2f} hectares")
        
        # Write output
        print(f"\nWriting probability raster to: {output_path}")
        profile.update({
            'count': 1,
            'dtype': 'float32',
            'nodata': -9999
        })
        
        with rasterio.open(output_path, 'w', **profile) as dst:
            dst.write(probabilities, 1)
        
        print("✓ Probability raster saved!")
        
        return probabilities

def main(run_num):
    """Main prediction pipeline"""
    
    base_dir = Path.home() / "Capstone" / "Lost-Meadows" / "GEE" / "TIF_Output" / str(run_num)
    
    features_path = base_dir / "features_stacked.tif"
    model_path = base_dir / "random_forest_model.pkl"
    output_path = base_dir / "meadow_probability.tif"
    
    # Check inputs exist
    if not features_path.exists():
        print(f"ERROR: {features_path} not found!")
        sys.exit(1)
    
    if not model_path.exists():
        print(f"ERROR: {model_path} not found!")
        print("Run train_random_forest.py first!")
        sys.exit(1)
    
    # Run prediction
    probabilities = predict_probabilities(
        str(features_path),
        str(model_path),
        str(output_path),
        chunk_size=500
    )
    
    print(f"\n{'='*60}")
    print("Prediction Complete!")
    print(f"{'='*60}")
    print(f"\nOutput: {output_path}")
    print("\nNext steps:")
    print("  1. Upload meadow_probability.tif to Google Earth Engine")
    print("  2. Create GEE app to visualize results")

if __name__ == "__main__":
    run_num = sys.argv[1] if len(sys.argv) > 1 else "1"
    main(run_num)