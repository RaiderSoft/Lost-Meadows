#!/usr/bin/env python3
"""
Process precipitation features for meadow detection

Crops and resamples large regional precipitation rasters to match
individual watershed resolution (10m) and extent.
"""

import rasterio
from rasterio.warp import reproject, Resampling
import numpy as np
import sys
from pathlib import Path


def process_precipitation(watershed_name):
    """
    Load regional precipitation data, crop to watershed, and resample to 10m
    """

    # Paths
    base_dir = Path(__file__).resolve().parent.parent.parent
    precip_dir = base_dir / "GEE" / "TIF_Input" / "Precip"
    output_dir = base_dir / "GEE" / "TIF_Output" / watershed_name

    print(f"\n{'='*60}")
    print(f"Processing Precipitation Features - {watershed_name}")
    print(f"{'='*60}\n")

    # Get reference raster (DEM or any existing feature) for bounds and resolution
    reference_files = list(output_dir.glob("slope.tif"))
    if not reference_files:
        reference_files = list(output_dir.glob("*_filled.tif"))

    if not reference_files:
        print("ERROR: No reference raster found. Run TauDEM and terrain features first!")
        sys.exit(1)

    reference_file = reference_files[0]
    print(f"Using reference raster: {reference_file.name}")

    # Load reference raster metadata
    with rasterio.open(reference_file) as ref:
        ref_bounds = ref.bounds
        ref_crs = ref.crs
        ref_transform = ref.transform
        ref_width = ref.width
        ref_height = ref.height
        ref_profile = ref.profile

        print(f"Reference:")
        print(f"  Bounds: {ref_bounds}")
        print(f"  CRS: {ref_crs}")
        print(f"  Shape: {ref_width} x {ref_height} pixels")
        print(f"  Resolution: {ref_transform.a:.1f}m")

    # Process each precipitation layer
    precip_layers = [
        ('SouthernOregon_precip_annual.tif', 'precip_annual'),
        ('SouthernOregon_precip_spring.tif', 'precip_spring')
    ]

    for precip_file, output_name in precip_layers:
        precip_path = precip_dir / precip_file

        if not precip_path.exists():
            print(f"WARNING: {precip_file} not found, skipping...")
            continue

        print(f"\nProcessing {precip_file}...")

        # Read source precipitation data
        with rasterio.open(precip_path) as src:
            print(f"  Source resolution: {src.res[0]:.1f}m")
            print(f"  Source CRS: {src.crs}")

            # Create output array matching reference
            output_data = np.zeros((ref_height, ref_width), dtype=np.float32)

            # Reproject to match reference raster
            reproject(
                source=rasterio.band(src, 1),
                destination=output_data,
                src_transform=src.transform,
                src_crs=src.crs,
                dst_transform=ref_transform,
                dst_crs=ref_crs,
                resampling=Resampling.bilinear  # Smooth interpolation for climate data
            )

        # Save output
        output_file = output_dir / f"{output_name}.tif"

        # Update profile for output
        out_profile = ref_profile.copy()
        out_profile.update({
            'dtype': 'float32',
            'count': 1
        })

        with rasterio.open(output_file, 'w', **out_profile) as dst:
            dst.write(output_data, 1)

        # Print statistics
        valid_data = output_data[~np.isnan(output_data)]
        if len(valid_data) > 0:
            print(f"  ✓ {output_name}.tif saved")
            print(f"    Range: {valid_data.min():.1f} to {valid_data.max():.1f} mm")
            print(f"    Mean: {valid_data.mean():.1f} mm")
        else:
            print(f"  ⚠ {output_name}.tif saved (all NaN)")

    print(f"\n{'='*60}")
    print("Precipitation features complete!")
    print(f"{'='*60}")
    print("\nGenerated files:")
    print("  - precip_annual.tif (annual precipitation in mm)")
    print("  - precip_spring.tif (spring precipitation in mm)")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python calculate_precipitation_features.py <watershed_name>")
        print("\nExample:")
        print("  python calculate_precipitation_features.py Hunter_Creek_1710031205")

        # Auto-detect if only one watershed directory exists
        base_dir = Path(__file__).resolve().parent.parent.parent
        output_base = base_dir / "GEE" / "TIF_Output"
        watersheds = [d.name for d in output_base.iterdir() if d.is_dir() and not d.name.startswith('.')]

        if len(watersheds) == 1:
            watershed_name = watersheds[0]
            print(f"\nAuto-detected: {watershed_name}")
        else:
            print(f"\nAvailable watersheds: {', '.join(watersheds)}")
            sys.exit(1)
    else:
        watershed_name = sys.argv[1]

    process_precipitation(watershed_name)
