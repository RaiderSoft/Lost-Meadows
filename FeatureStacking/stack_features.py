#!/usr/bin/env python3
"""
Stack all feature rasters into a single multi-band GeoTIFF
"""

import rasterio
import numpy as np
import os
import sys
from pathlib import Path

def get_repo_root():
    # ModelTraining/train_random_forest.py
    return Path(__file__).resolve().parents[1]

def stack_features(watershed_name):
    """Stack all 29 features into one multi-band raster"""

    # Use absolute path from home directory
    repo_root = get_repo_root()
    base_dir = repo_root / "GEE" / "TIF_Output" / watershed_name
    output_dir = str(base_dir)

    if not base_dir.exists():
        print(f"ERROR: Output directory not found: {output_dir}")
        print("Make sure you've run all feature engineering steps first!")
        sys.exit(1)

    # Define all feature files in the order they should be stacked
    feature_files = [
        # Original 9 features
        f"{output_dir}/slope.tif",                          # 1. Slope
        f"{output_dir}/elev_5x5_rel.tif",                   # 2. Relative elevation
        f"{output_dir}/elev_5x5_std_dev.tif",               # 3. Elevation std dev
        f"{output_dir}/slope_5x5_std_dev.tif",              # 4. Slope std dev
        f"{output_dir}/twi_10m.tif",                        # 5. TWI 10m
        f"{output_dir}/twi_100m.tif",                       # 6. TWI 100m
        f"{output_dir}/dd_s.tif",                           # 7. Surface distance to stream
        f"{output_dir}/dd_h.tif",                           # 8. Horizontal distance to stream
        f"{output_dir}/dd_v.tif",                           # 9. Vertical distance to stream

        # New 11 advanced features
        f"{output_dir}/aspect.tif",                         # 10. Aspect (slope direction)
        f"{output_dir}/curvature_profile.tif",              # 11. Profile curvature
        f"{output_dir}/curvature_plan.tif",                 # 12. Plan curvature
        f"{output_dir}/tpi_3x3.tif",                        # 13. TPI 3x3
        f"{output_dir}/tpi_11x11.tif",                      # 14. TPI 11x11
        f"{output_dir}/tpi_21x21.tif",                      # 15. TPI 21x21
        f"{output_dir}/tri.tif",                            # 16. TRI
        f"{output_dir}/elev_std_3x3.tif",                   # 17. Elevation std dev 3x3
        f"{output_dir}/elev_std_9x9.tif",                   # 18. Elevation std dev 9x9
        f"{output_dir}/slope_std_9x9.tif",                  # 19. Slope std dev 9x9

        # Soil features (9) — POLARIS 30m, 3 depths each
        f"{output_dir}/soil_clay_pct_0_5cm.tif",            # 20. Clay % 0-5cm
        f"{output_dir}/soil_clay_pct_5_15cm.tif",           # 21. Clay % 5-15cm
        f"{output_dir}/soil_clay_pct_15_30cm.tif",          # 22. Clay % 15-30cm
        f"{output_dir}/soil_ksat_0_5cm.tif",                # 23. Ksat 0-5cm
        f"{output_dir}/soil_ksat_5_15cm.tif",               # 24. Ksat 5-15cm
        f"{output_dir}/soil_ksat_15_30cm.tif",              # 25. Ksat 15-30cm
        f"{output_dir}/soil_organic_matter_0_5cm.tif",      # 26. Organic matter 0-5cm
        f"{output_dir}/soil_organic_matter_5_15cm.tif",     # 27. Organic matter 5-15cm
        f"{output_dir}/soil_organic_matter_15_30cm.tif",    # 28. Organic matter 15-30cm

    ]

    feature_names = [
        # Original 9
        "slope",
        "elev_5x5_rel",
        "elev_5x5_std_dev",
        "slope_5x5_std_dev",
        "twi_10m",
        "twi_100m",
        "dd_s",
        "dd_h",
        "dd_v",

        # New 11
        "aspect",
        "curvature_profile",
        "curvature_plan",
        "tpi_3x3",
        "tpi_11x11",
        "tpi_21x21",
        "tri",
        "elev_std_3x3",
        "elev_std_9x9",
        "slope_std_9x9",

        # Soil features (9) — POLARIS 30m, 3 depths
        "soil_clay_pct_0_5cm",
        "soil_clay_pct_5_15cm",
        "soil_clay_pct_15_30cm",
        "soil_ksat_0_5cm",
        "soil_ksat_5_15cm",
        "soil_ksat_15_30cm",
        "soil_organic_matter_0_5cm",
        "soil_organic_matter_5_15cm",
        "soil_organic_matter_15_30cm",

    ]
    
    print(f"\n{'='*60}")
    print(f"Stacking Features - {watershed_name}")
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
    if len(sys.argv) < 2:
        print("Usage: python stack_features.py <watershed_name>")
        print("\nExample:")
        print("  python stack_features.py Bear_Creek_Watershed_10m")
        # Auto-detect if only one watershed directory exists
        base_dir = get_repo_root() / "GEE" / "TIF_Output"
        watersheds = [d.name for d in base_dir.iterdir() if d.is_dir() and not d.name.startswith('.')]
        if len(watersheds) == 1:
            watershed_name = watersheds[0]
            print(f"\nAuto-detected: {watershed_name}")
        else:
            print(f"\nAvailable watersheds: {', '.join(watersheds)}")
            sys.exit(1)
    else:
        watershed_name = sys.argv[1]

    stack_features(watershed_name)

    # Optional cleanup
    print("\nIndividual feature files can now be deleted (optional).")
    print("They are all combined in features_stacked.tif")
    print("\nTo keep them for inspection: do nothing")
    print("To delete them: remove slope.tif, twi_10m.tif, etc. manually")
    print("  (Keeping for now as they're useful for debugging)")