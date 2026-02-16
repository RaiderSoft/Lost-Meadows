#!/usr/bin/env python3
"""
Calculate TWI at 100m resolution then resample back to 10m
"""

import rasterio
from rasterio.enums import Resampling
import numpy as np
import sys
import os

def resample_to_100m(input_file, output_file):
    """Resample raster to 100m resolution"""
    print(f"Resampling {input_file} to 100m...")
    
    with rasterio.open(input_file) as src:
        scale_factor = 10
        new_width = int(src.width / scale_factor)
        new_height = int(src.height / scale_factor)
        
        transform = src.transform * src.transform.scale(
            (src.width / new_width),
            (src.height / new_height)
        )
        
        data = src.read(
            out_shape=(src.count, new_height, new_width),
            resampling=Resampling.bilinear
        )
        
        profile = src.profile.copy()
        profile.update({
            'width': new_width,
            'height': new_height,
            'transform': transform
        })
        
        with rasterio.open(output_file, 'w', **profile) as dst:
            dst.write(data)
    
    print(f"✓ Resampled to {output_file}")
    return output_file

def calculate_slope_100m(dem_file, output_file):
    """Calculate slope from 100m DEM"""
    print(f"Calculating slope from {dem_file}...")
    
    with rasterio.open(dem_file) as src:
        dem = src.read(1)
        profile = src.profile
        transform = src.transform
        
        pixel_size = transform[0]
        
        dy, dx = np.gradient(dem, pixel_size)
        slope_rad = np.arctan(np.sqrt(dx**2 + dy**2))
        slope_deg = np.degrees(slope_rad)
        
        with rasterio.open(output_file, 'w', **profile) as dst:
            dst.write(slope_deg, 1)
    
    print(f"✓ Slope saved to {output_file}")
    return output_file

def calculate_twi(sca_file, slope_file, output_file):
    """Calculate TWI = ln(sca / tan(slope))"""
    print(f"Calculating TWI at 100m...")
    
    with rasterio.open(sca_file) as src:
        sca = src.read(1)
        profile = src.profile
    
    with rasterio.open(slope_file) as src:
        slope = src.read(1)
    
    slope_rad = np.radians(slope)
    tan_slope = np.tan(slope_rad)
    tan_slope[tan_slope <= 0] = 0.001
    
    twi = np.log(sca / tan_slope)
    twi[~np.isfinite(twi)] = 0
    
    with rasterio.open(output_file, 'w', **profile) as dst:
        dst.write(twi, 1)
    
    print(f"✓ TWI 100m saved to {output_file}")
    
    print(f"\nTWI 100m Statistics:")
    print(f"  Min: {np.min(twi[np.isfinite(twi)]):.2f}")
    print(f"  Max: {np.max(twi[np.isfinite(twi)]):.2f}")
    print(f"  Mean: {np.mean(twi[np.isfinite(twi)]):.2f}")
    print(f"  Median: {np.median(twi[np.isfinite(twi)]):.2f}")

def resample_back_to_10m(input_100m, reference_10m, output_file):
    """Resample 100m TWI back to 10m to match other features"""
    print(f"\nResampling TWI back to 10m resolution...")
    
    with rasterio.open(reference_10m) as ref:
        ref_profile = ref.profile.copy()
        ref_height = ref.height
        ref_width = ref.width
    
    with rasterio.open(input_100m) as src:
        data_resampled = src.read(
            out_shape=(1, ref_height, ref_width),
            resampling=Resampling.bilinear
        )[0]
        
        with rasterio.open(output_file, 'w', **ref_profile) as dst:
            dst.write(data_resampled, 1)
    
    print(f"✓ TWI 100m resampled to {ref_width}x{ref_height} (10m resolution)")

if __name__ == "__main__":
    import sys
    import glob
    
    run_num = sys.argv[1] if len(sys.argv) > 1 else "1"
    output_dir = f"../../GEE/TIF_Output/{run_num}"
    
    # Auto-detect filled DEM and SCA files
    dem_files = glob.glob(f"{output_dir}/*_filled.tif")
    sca_files = glob.glob(f"{output_dir}/*_sca.tif")
    
    if not dem_files:
        print(f"ERROR: No filled DEM (*_filled.tif) found in {output_dir}")
        sys.exit(1)
    
    if not sca_files:
        print(f"ERROR: No SCA file (*_sca.tif) found in {output_dir}")
        sys.exit(1)
    
    dem_filled = dem_files[0]
    sca_10m = sca_files[0]
    twi_10m = f"{output_dir}/twi_10m.tif"
    
    dem_100m = f"{output_dir}/dem_100m_temp.tif"
    sca_100m = f"{output_dir}/sca_100m_temp.tif"
    slope_100m = f"{output_dir}/slope_100m_temp.tif"
    twi_100m_temp = f"{output_dir}/twi_100m_temp.tif"
    twi_100m_final = f"{output_dir}/twi_100m.tif"
    
    print(f"Input DEM: {dem_filled}")
    print(f"Input SCA: {sca_10m}\n")
    
    # Process at 100m
    resample_to_100m(dem_filled, dem_100m)
    resample_to_100m(sca_10m, sca_100m)
    calculate_slope_100m(dem_100m, slope_100m)
    calculate_twi(sca_100m, slope_100m, twi_100m_temp)
    
    # Resample back to 10m
    resample_back_to_10m(twi_100m_temp, twi_10m, twi_100m_final)
    
    print("\n✓ TWI 100m calculation complete and resampled to 10m!")
    
    # Clean up temp files
    print("\nCleaning up temporary files...")
    import os
    temp_files = [dem_100m, sca_100m, slope_100m, twi_100m_temp]
    for temp_file in temp_files:
        if os.path.exists(temp_file):
            os.remove(temp_file)
            print(f"  ✓ Deleted {os.path.basename(temp_file)}")