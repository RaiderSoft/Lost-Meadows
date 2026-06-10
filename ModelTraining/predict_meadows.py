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
from scipy.ndimage import label, distance_transform_edt

def get_repo_root():
    # ModelTraining/predict_meadows.py
    return Path(__file__).resolve().parents[1]

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
    print(f"✓ Model loaded ({type(model).__name__}, n_estimators={model.n_estimators})")
    
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

        # Fill internal NoData holes with nearest-neighbor prediction.
        # "Internal" = nodata regions fully surrounded by valid predictions (not touching the raster edge).
        nodata_mask = probabilities == -9999.0
        labeled, _ = label(nodata_mask)
        exterior_labels = set()
        for edge in (labeled[0, :], labeled[-1, :], labeled[:, 0], labeled[:, -1]):
            exterior_labels.update(edge.tolist())
        exterior_labels.discard(0)
        interior_holes = nodata_mask.copy()
        for lbl in exterior_labels:
            interior_holes[labeled == lbl] = False
        n_filled = int(interior_holes.sum())
        if n_filled > 0:
            indices = distance_transform_edt(nodata_mask, return_distances=False, return_indices=True)
            probabilities[interior_holes] = probabilities[indices[0][interior_holes], indices[1][interior_holes]]
            print(f"  Filled {n_filled:,} internal NoData pixels with nearest-neighbor prediction")

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

def main(watershed_name, model_file="xgboost_model.pkl"):
    """Main prediction pipeline"""
    repo_root = get_repo_root()
    base_dir = repo_root / "GEE" / "TIF_Output" / watershed_name

    if not base_dir.exists():
        print(f"ERROR: Output directory not found: {base_dir}")
        print("Make sure you've run the full pipeline first!")
        sys.exit(1)

    features_path = base_dir / "features_stacked.tif"
    model_path = base_dir / model_file

    # Name output file after the model used
    model_stem = Path(model_file).stem
    output_path = base_dir / f"{watershed_name}_{model_stem}_probability.tif"

    # Check inputs exist
    if not features_path.exists():
        print(f"ERROR: {features_path} not found!")
        print("Run feature stacking first!")
        sys.exit(1)

    if not model_path.exists():
        print(f"ERROR: {model_path} not found!")
        print("Run train_xgboost.py first!")
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
    print(f"\nFinal output file: {output_path.name}")
    print("\nNext steps:")
    print(f"  1. Upload {output_path.name} to Google Earth Engine")
    print("  2. Create GEE app to visualize results")

if __name__ == "__main__":
    import sys
    from pathlib import Path

    if len(sys.argv) < 2:
        print("Usage: python predict_meadows.py <watershed_name>")
        print("\nExample:")
        print("  python predict_meadows.py Bear_Creek_Watershed_10m")
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

    model_file = sys.argv[2] if len(sys.argv) > 2 else "xgboost_model.pkl"
    main(watershed_name, model_file)