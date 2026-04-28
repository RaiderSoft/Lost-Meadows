#!/usr/bin/env python3
"""
Calculate Topographic Wetness Index (TWI) from TauDEM outputs
TWI = ln(sca / tan(slope))
"""

import rasterio
import numpy as np
import sys
import os

def calculate_twi(sca_file, slope_file, output_file):
    """Calculate TWI from specific catchment area and slope"""
    
    print(f"Reading {sca_file}...")
    with rasterio.open(sca_file) as src:
        sca = src.read(1).astype(np.float64)
        profile = src.profile
        sca_nodata = src.nodata

    print(f"Reading {slope_file}...")
    with rasterio.open(slope_file) as src:
        slope = src.read(1).astype(np.float64)
        slope_nodata = src.nodata

    # Mask nodata pixels so they don't corrupt edge calculations
    nodata_mask = np.isnan(sca) | np.isnan(slope) | (sca > 1e10) | (slope > 1e10) | (sca < -1e10) | (slope < -1e10)
    if sca_nodata is not None:
        nodata_mask |= (sca == sca_nodata)
    if slope_nodata is not None:
        nodata_mask |= (slope == slope_nodata)
    sca[nodata_mask] = np.nan
    slope[nodata_mask] = np.nan

    print("Calculating TWI...")

    # Convert slope from degrees to radians
    slope_rad = np.radians(slope)
    
    # Calculate tan(slope), avoid division by zero
    tan_slope = np.tan(slope_rad)
    tan_slope[tan_slope <= 0] = 0.001  # Minimum threshold
    
    # Calculate TWI = ln(sca / tan(slope))
    twi = np.log(sca / tan_slope)
    
    # Handle invalid values — set nodata pixels to -9999
    twi[nodata_mask | ~np.isfinite(twi)] = -9999
    profile.update(nodata=-9999)

    print(f"Writing {output_file}...")
    with rasterio.open(output_file, 'w', **profile) as dst:
        dst.write(twi.astype(np.float32), 1)
    
    print(f"✓ TWI saved to {output_file}")
    
    # Print statistics
    print(f"\nTWI Statistics:")
    print(f"  Min: {np.min(twi[np.isfinite(twi)]):.2f}")
    print(f"  Max: {np.max(twi[np.isfinite(twi)]):.2f}")
    print(f"  Mean: {np.mean(twi[np.isfinite(twi)]):.2f}")
    print(f"  Median: {np.median(twi[np.isfinite(twi)]):.2f}")

if __name__ == "__main__":
    import sys
    import glob
    from pathlib import Path

    if len(sys.argv) < 2:
        print("Usage: python calculate_twi_10m.py <watershed_name>")
        print("\nExample:")
        print("  python calculate_twi_10m.py Bear_Creek_Watershed_10m")
        print("\nOr auto-detect from TIF_Output (if only one watershed):")
        # Auto-detect if only one watershed directory exists
        base_dir = Path(__file__).resolve().parents[2] / "GEE" / "TIF_Output"
        watersheds = [d.name for d in base_dir.iterdir() if d.is_dir() and not d.name.startswith('.')]
        if len(watersheds) == 1:
            watershed_name = watersheds[0]
            print(f"  Auto-detected: {watershed_name}")
        else:
            print(f"  Available watersheds: {', '.join(watersheds)}")
            sys.exit(1)
    else:
        watershed_name = sys.argv[1]

    output_dir = f"../../GEE/TIF_Output/{watershed_name}"

    if not Path(output_dir).exists():
        print(f"ERROR: Output directory not found: {output_dir}")
        print("Make sure you've run the TauDEM workflow first!")
        sys.exit(1)

    # Auto-detect SCA and slope files
    sca_files = glob.glob(f"{output_dir}/*_sca.tif")
    slope_files = glob.glob(f"{output_dir}/*_slp.tif")
    
    if not sca_files:
        print(f"ERROR: No SCA file (*_sca.tif) found in {output_dir}")
        sys.exit(1)
    
    if not slope_files:
        print(f"ERROR: No slope file (*_slp.tif) found in {output_dir}")
        sys.exit(1)
    
    sca_file = sca_files[0]
    slope_file = slope_files[0]
    output_file = f"{output_dir}/twi_10m.tif"
    
    print(f"Input SCA: {sca_file}")
    print(f"Input slope: {slope_file}")
    print(f"Output: {output_file}\n")
    
    calculate_twi(sca_file, slope_file, output_file)