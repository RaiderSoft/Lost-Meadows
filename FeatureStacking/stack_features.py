#!/usr/bin/env python3
"""
Stack all feature rasters into a single multi-band GeoTIFF
"""

import rasterio
import numpy as np
import os
import sys
from pathlib import Path

def stack_features(run_num):
    """Stack all 10 features into one multi-band raster"""
    
    # Use absolute path from home directory
    base_dir = Path.home() / "Capstone" / "Lost-Meadows" / "GEE" / "TIF_Output" / str(run_num)
    output_dir = str(base_dir)
    
    # Define all feature files in the order they should be stacked
    feature_files = [
        f"{output_dir}/slope.tif",                          # 1. Slope
        f"{output_dir}/elev_5x5_rel.tif",                   # 2. Relative elevation
        f"{output_dir}/elev_5x5_std_dev.tif",               # 3. Elevation std dev
        f"{output_dir}/slope_5x5_std_dev.tif",              # 4. Slope std dev
        f"{output_dir}/twi_10m.tif",                        # 5. TWI 10m
        f"{output_dir}/twi_100m.tif",                       # 6. TWI 100m
        f"{output_dir}/dd_s.tif",                           # 7. Surface distance to stream
        f"{output_dir}/dd_h.tif",                           # 8. Horizontal distance to stream
        f"{output_dir}/dd_v.tif",                           # 9. Vertical distance to stream
    ]
    
    feature_names = [
        "slope",
        "elev_5x5_rel",
        "elev_5x5_std_dev",
        "slope_5x5_std_dev",
        "twi_10m",
        "twi_100m",
        "dd_s",
        "dd_h",
        "dd_v"
    ]
    
    print(f"\n{'='*60}")
    print(f"Stacking Features - Run #{run_num}")
    print(f"{'='*60}\n")
    
    # Check all files exist
    print("Checking feature files...")
    missing = []
    for i, file in enumerate(feature_files):
        if os.path.exists(file):
            print(f"  ✓ {feature_names[i]}")
        else:
            print(f"  ✗ {feature_names[i]} - NOT FOUND")
            missing.append(feature_names[i])
    
    if missing:
        print(f"\nERROR: Missing features: {', '.join(missing)}")
        sys.exit(1)
    
    print(f"\nStacking {len(feature_files)} features...")
    
    # Read first raster to get profile
    with rasterio.open(feature_files[0]) as src:
        profile = src.profile.copy()
        height = src.height
        width = src.width
    
    # Update profile for multi-band output
    profile.update({
        'count': len(feature_files),
        'dtype': 'float32'
    })
    
    # Create output file
    output_file = f"{output_dir}/features_stacked.tif"
    
    print(f"Writing stacked raster to: {output_file}")
    
    with rasterio.open(output_file, 'w', **profile) as dst:
        for i, (file, name) in enumerate(zip(feature_files, feature_names), 1):
            print(f"  Band {i}: {name}")
            with rasterio.open(file) as src:
                data = src.read(1)
                dst.write(data.astype('float32'), i)
                dst.set_band_description(i, name)
    
    print(f"\n{'='*60}")
    print("Feature stacking complete!")
    print(f"{'='*60}")
    print(f"\nOutput: {output_file}")
    print(f"Bands: {len(feature_files)}")
    print(f"Size: {width} x {height} pixels")
    print(f"\nBand descriptions:")
    for i, name in enumerate(feature_names, 1):
        print(f"  Band {i}: {name}")
    
    # Calculate file size
    file_size_mb = os.path.getsize(output_file) / (1024 * 1024)
    print(f"\nFile size: {file_size_mb:.2f} MB")
    
    print("\nNext step: Convert to CSV or train model directly from raster")

if __name__ == "__main__":
    run_num = sys.argv[1] if len(sys.argv) > 1 else "1"
    stack_features(run_num)