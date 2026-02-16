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
        sca = src.read(1)
        profile = src.profile
    
    print(f"Reading {slope_file}...")
    with rasterio.open(slope_file) as src:
        slope = src.read(1)
    
    print("Calculating TWI...")
    
    # Convert slope from degrees to radians
    slope_rad = np.radians(slope)
    
    # Calculate tan(slope), avoid division by zero
    tan_slope = np.tan(slope_rad)
    tan_slope[tan_slope <= 0] = 0.001  # Minimum threshold
    
    # Calculate TWI = ln(sca / tan(slope))
    twi = np.log(sca / tan_slope)
    
    # Handle invalid values
    twi[~np.isfinite(twi)] = 0
    
    print(f"Writing {output_file}...")
    with rasterio.open(output_file, 'w', **profile) as dst:
        dst.write(twi, 1)
    
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
    
    run_num = sys.argv[1] if len(sys.argv) > 1 else "1"
    output_dir = f"../../GEE/TIF_Output/{run_num}"
    
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