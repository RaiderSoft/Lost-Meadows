#!/usr/bin/env python3
"""
Calculate terrain features using 5x5 moving windows
- Relative elevation (mean of 5x5 window minus focal pixel)
- Elevation std dev in 5x5 window
- Slope at focal pixel
- Slope std dev in 5x5 window
"""

import rasterio
import numpy as np
from scipy.ndimage import uniform_filter, generic_filter
import sys
import os
import glob

def calculate_relative_elevation(elevation, window_size=5):
    """Calculate relative elevation: mean of window minus focal pixel"""
    print("Calculating relative elevation...")
    
    # Handle NaN values by temporarily replacing with median (more robust than mean)
    mask = np.isnan(elevation)
    valid_values = elevation[~mask]
    
    if len(valid_values) == 0:
        print("ERROR: No valid elevation values!")
        return elevation
    
    fill_value = np.median(valid_values)
    elevation_filled = elevation.copy()
    elevation_filled[mask] = fill_value
    
    # Calculate mean in window using float64 to avoid overflow
    elevation_float = elevation_filled.astype(np.float64)
    mean_elev = uniform_filter(elevation_float, size=window_size, mode='reflect')
    
    # Relative elevation = mean - focal pixel
    rel_elev = mean_elev - elevation_float
    
    # Restore NaN where original was NaN
    rel_elev[mask] = np.nan
    
    return rel_elev.astype(np.float32)

def calculate_std_dev(data, window_size=5):
    """Calculate standard deviation in moving window"""
    print(f"Calculating std dev (window size {window_size})...")
    
    # Handle NaN values
    mask = np.isnan(data)
    data_filled = data.copy()
    data_filled[mask] = np.nanmedian(data)
    
    def std_func(values):
        return np.std(values)
    
    std_dev = generic_filter(data_filled, std_func, size=window_size, mode='reflect')
    
    # Restore NaN where original was NaN
    std_dev[mask] = np.nan
    
    return std_dev

def calculate_slope(dem, profile):
    """Calculate slope in degrees"""
    print("Calculating slope...")
    
    # Get pixel size from transform
    transform = profile['transform']
    pixel_size = transform[0]  # Should be 10m
    
    # Create a version without NaN for gradient calculation
    mask = np.isnan(dem)
    dem_filled = dem.copy()
    dem_filled[mask] = np.nanmedian(dem)
    
    # Calculate gradients
    dy, dx = np.gradient(dem_filled, pixel_size)
    
    # Calculate slope
    slope_rad = np.arctan(np.sqrt(dx**2 + dy**2))
    slope_deg = np.degrees(slope_rad)
    
    # Restore NaN where original DEM was NaN
    slope_deg[mask] = np.nan
    
    return slope_deg

def main(watershed_name):
    """Calculate all terrain features"""

    output_dir = f"../../GEE/TIF_Output/{watershed_name}"

    if not os.path.exists(output_dir):
        print(f"ERROR: Output directory not found: {output_dir}")
        print("Make sure you've run the TauDEM workflow first!")
        sys.exit(1)

    # Auto-detect the filled DEM in the output directory
    dem_files = glob.glob(f"{output_dir}/*_filled.tif")

    if not dem_files:
        print(f"ERROR: No filled DEM (*_filled.tif) found in {output_dir}")
        print("Run TauDEM workflow first!")
        sys.exit(1)

    dem_file = dem_files[0]

    print(f"\n{'='*60}")
    print(f"Calculating Terrain Features - {watershed_name}")
    print(f"{'='*60}\n")
    print(f"Using DEM: {dem_file}\n")
    
    # Read elevation data
    with rasterio.open(dem_file) as src:
        elevation = src.read(1)
        profile = src.profile
    
    # CRITICAL: Replace TauDEM NoData values with NaN
    print("Cleaning TauDEM NoData values...")
    nodata_mask = elevation > 1e10  # Any huge value is NoData
    print(f"  Found {np.sum(nodata_mask):,} NoData pixels")
    elevation[nodata_mask] = np.nan
    
    print(f"DEM shape: {elevation.shape}")
    print(f"Valid pixels: {np.sum(~np.isnan(elevation)):,}")
    print(f"Elevation range: {np.nanmin(elevation):.2f} to {np.nanmax(elevation):.2f}\n")
    
    # 1. Relative elevation (5x5 window)
    rel_elev = calculate_relative_elevation(elevation, window_size=5)
    output_file = f"{output_dir}/elev_5x5_rel.tif"
    print(f"Writing {output_file}...")
    with rasterio.open(output_file, 'w', **profile) as dst:
        dst.write(rel_elev, 1)
    print(f"✓ Relative elevation saved (valid pixels: {np.sum(~np.isnan(rel_elev)):,})")
    
    # 2. Elevation std dev (5x5 window)
    elev_std = calculate_std_dev(elevation, window_size=5)
    output_file = f"{output_dir}/elev_5x5_std_dev.tif"
    print(f"Writing {output_file}...")
    with rasterio.open(output_file, 'w', **profile) as dst:
        dst.write(elev_std, 1)
    print(f"✓ Elevation std dev saved (valid pixels: {np.sum(~np.isnan(elev_std)):,})")
    
    # 3. Slope
    slope = calculate_slope(elevation, profile)
    output_file = f"{output_dir}/slope.tif"
    print(f"Writing {output_file}...")
    with rasterio.open(output_file, 'w', **profile) as dst:
        dst.write(slope, 1)
    print(f"✓ Slope saved (valid pixels: {np.sum(~np.isnan(slope)):,})")
    
    # 4. Slope std dev (5x5 window)
    slope_std = calculate_std_dev(slope, window_size=5)
    output_file = f"{output_dir}/slope_5x5_std_dev.tif"
    print(f"Writing {output_file}...")
    with rasterio.open(output_file, 'w', **profile) as dst:
        dst.write(slope_std, 1)
    print(f"✓ Slope std dev saved (valid pixels: {np.sum(~np.isnan(slope_std)):,})")
    
    print(f"\n{'='*60}")
    print("Terrain features calculation complete!")
    print(f"{'='*60}")
    print("\nGenerated files:")
    print("  - elev_5x5_rel.tif")
    print("  - elev_5x5_std_dev.tif")
    print("  - slope.tif")
    print("  - slope_5x5_std_dev.tif")

    print(f"\nNote: TauDEM intermediate files (*_filled, *_sca, *_slp, etc.) are kept")
    print("      for advanced features calculation. They'll be cleaned up after that.")

if __name__ == "__main__":
    from pathlib import Path

    if len(sys.argv) < 2:
        print("Usage: python calculate_terrain_features.py <watershed_name>")
        print("\nExample:")
        print("  python calculate_terrain_features.py Bear_Creek_Watershed_10m")
        # Auto-detect if only one watershed directory exists
        base_dir = Path(__file__).resolve().parents[2] / "GEE" / "TIF_Output"
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