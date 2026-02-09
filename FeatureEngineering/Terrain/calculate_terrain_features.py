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

def calculate_relative_elevation(elevation, window_size=5):
    """Calculate relative elevation: mean of window minus focal pixel"""
    print("Calculating relative elevation...")
    
    # Handle NaN values by temporarily replacing with a fill value
    mask = np.isnan(elevation)
    elevation_filled = elevation.copy()
    elevation_filled[mask] = np.nanmean(elevation)
    
    # Calculate mean in window
    mean_elev = uniform_filter(elevation_filled, size=window_size, mode='reflect')
    
    # Relative elevation = mean - focal pixel
    rel_elev = mean_elev - elevation_filled
    
    # Restore NaN where original was NaN
    rel_elev[mask] = np.nan
    
    return rel_elev

def calculate_std_dev(data, window_size=5):
    """Calculate standard deviation in moving window"""
    print(f"Calculating std dev (window size {window_size})...")
    
    # Handle NaN values
    mask = np.isnan(data)
    data_filled = data.copy()
    data_filled[mask] = np.nanmean(data)
    
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
    dem_filled[mask] = np.nanmean(dem)
    
    # Calculate gradients
    dy, dx = np.gradient(dem_filled, pixel_size)
    
    # Calculate slope
    slope_rad = np.arctan(np.sqrt(dx**2 + dy**2))
    slope_deg = np.degrees(slope_rad)
    
    # Restore NaN where original DEM was NaN
    slope_deg[mask] = np.nan
    
    return slope_deg

def main(run_num):
    """Calculate all terrain features"""
    
    input_dir = f"../../GEE/TIF_Input"
    output_dir = f"../../GEE/TIF_Output/{run_num}"
    
    # Input elevation file (original DEM)
    dem_file = f"{input_dir}/3DEP_10m_TEST_watershed.tif"
    
    if not os.path.exists(dem_file):
        print(f"ERROR: {dem_file} not found!")
        sys.exit(1)
    
    print(f"\n{'='*60}")
    print(f"Calculating Terrain Features - Run #{run_num}")
    print(f"{'='*60}\n")
    
    # Read elevation data
    print(f"Reading {dem_file}...")
    with rasterio.open(dem_file) as src:
        elevation = src.read(1)
        profile = src.profile
    
    print(f"DEM shape: {elevation.shape}")
    print(f"Valid pixels: {np.sum(~np.isnan(elevation)):,}")
    
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

if __name__ == "__main__":
    run_num = sys.argv[1] if len(sys.argv) > 1 else "1"
    main(run_num)