#!/usr/bin/env python3
"""
Process soil features for meadow detection.

Crops and resamples soil TIF files to match individual watershed
resolution (10m) and extent.

Expected input files in GEE/TIF_Input/Soil/ (POLARIS 30m, 3 depth bands each):
  - polaris_clay_pct_0_30cm.tif      (bands: 0-5cm, 5-15cm, 15-30cm)
  - polaris_ksat_0_30cm.tif          (bands: 0-5cm, 5-15cm, 15-30cm)
  - polaris_organic_matter_0_30cm.tif (bands: 0-5cm, 5-15cm, 15-30cm)

Output files written to GEE/TIF_Output/<watershed_name>/:
  - soil_clay_pct_0_5cm.tif / soil_clay_pct_5_15cm.tif / soil_clay_pct_15_30cm.tif
  - soil_ksat_0_5cm.tif / soil_ksat_5_15cm.tif / soil_ksat_15_30cm.tif
  - soil_organic_matter_0_5cm.tif / soil_organic_matter_5_15cm.tif / soil_organic_matter_15_30cm.tif

Usage:
    python calculate_soil_features.py <watershed_name>
    python calculate_soil_features.py  # auto-detects if only one watershed
"""

import rasterio
from rasterio.warp import reproject, Resampling
import numpy as np
import sys
from pathlib import Path


def process_soil_features(watershed_name):
    """
    Load soil TIF files, split bands by depth, crop to watershed bounds, and resample to 10m.
    """

    base_dir = Path(__file__).resolve().parent.parent.parent
    soil_dir = base_dir / "GEE" / "TIF_Input" / "Soil"
    output_dir = base_dir / "GEE" / "TIF_Output" / watershed_name

    print(f"\n{'='*60}")
    print(f"Processing Soil Features - {watershed_name}")
    print(f"{'='*60}\n")

    # Validate soil input directory
    if not soil_dir.exists():
        print(f"ERROR: Soil input directory not found: {soil_dir}")
        print("Create GEE/TIF_Input/Soil/ and place your soil TIF files there.")
        sys.exit(1)

    # Validate output directory
    if not output_dir.exists():
        print(f"ERROR: Output directory not found: {output_dir}")
        print("Make sure you've run the TauDEM and terrain feature steps first!")
        sys.exit(1)

    # Get reference raster for bounds, CRS, and resolution
    reference_files = list(output_dir.glob("slope.tif"))
    if not reference_files:
        reference_files = list(output_dir.glob("*_filled.tif"))

    if not reference_files:
        print("ERROR: No reference raster found in output directory.")
        print("Run TauDEM and terrain features first (slope.tif must exist).")
        sys.exit(1)

    reference_file = reference_files[0]
    print(f"Using reference raster: {reference_file.name}")

    # Load reference raster metadata
    with rasterio.open(reference_file) as ref:
        ref_crs = ref.crs
        ref_transform = ref.transform
        ref_width = ref.width
        ref_height = ref.height
        ref_profile = ref.profile

        print(f"Reference:")
        print(f"  Bounds: {ref.bounds}")
        print(f"  CRS:    {ref_crs}")
        print(f"  Shape:  {ref_width} x {ref_height} pixels")
        print(f"  Resolution: {ref_transform.a:.1f}m")

    # Define soil layers to process
    # Format: (input_filename, [(output_name, description), ...], resampling_method)
    # Each input file has 3 bands: band 1 = 0-5cm, band 2 = 5-15cm, band 3 = 15-30cm
    soil_layers = [
        (
            "polaris_clay_pct_0_30cm.tif",
            [
                ("soil_clay_pct_0_5cm",   "Clay % 0-5cm"),
                ("soil_clay_pct_5_15cm",  "Clay % 5-15cm"),
                ("soil_clay_pct_15_30cm", "Clay % 15-30cm"),
            ],
            Resampling.bilinear,
        ),
        (
            "polaris_ksat_0_30cm.tif",
            [
                ("soil_ksat_0_5cm",   "Sat. hydraulic conductivity 0-5cm"),
                ("soil_ksat_5_15cm",  "Sat. hydraulic conductivity 5-15cm"),
                ("soil_ksat_15_30cm", "Sat. hydraulic conductivity 15-30cm"),
            ],
            Resampling.bilinear,
        ),
        (
            "polaris_organic_matter_0_30cm.tif",
            [
                ("soil_organic_matter_0_5cm",   "Organic matter 0-5cm"),
                ("soil_organic_matter_5_15cm",  "Organic matter 5-15cm"),
                ("soil_organic_matter_15_30cm", "Organic matter 15-30cm"),
            ],
            Resampling.bilinear,
        ),
    ]

    processed = []
    skipped = []

    for soil_file, band_outputs, resampling in soil_layers:
        soil_path = soil_dir / soil_file

        if not soil_path.exists():
            print(f"\nWARNING: {soil_file} not found in {soil_dir}, skipping...")
            for output_name, _ in band_outputs:
                skipped.append(output_name)
            continue

        print(f"\nProcessing {soil_file}...")

        with rasterio.open(soil_path) as src:
            print(f"  Source resolution: {src.res[0]:.1f}m")
            print(f"  Source CRS: {src.crs}")
            print(f"  Bands: {src.count}")
            src_nodata = src.nodata

            for band_idx, (output_name, description) in enumerate(band_outputs, start=1):
                print(f"\n  Band {band_idx} — {description}")

                output_data = np.zeros((ref_height, ref_width), dtype=np.float32)

                reproject(
                    source=rasterio.band(src, band_idx),
                    destination=output_data,
                    src_transform=src.transform,
                    src_crs=src.crs,
                    dst_transform=ref_transform,
                    dst_crs=ref_crs,
                    resampling=resampling,
                )

                # Mask out nodata values that may bleed in from bilinear interpolation
                if src_nodata is not None:
                    output_data[output_data <= src_nodata * 0.9] = np.nan

                # Write output
                output_file = output_dir / f"{output_name}.tif"
                out_profile = ref_profile.copy()
                out_profile.update({"dtype": "float32", "count": 1})

                with rasterio.open(output_file, "w", **out_profile) as dst:
                    dst.write(output_data, 1)

                valid = output_data[~np.isnan(output_data) & (output_data != 0)]
                if len(valid) > 0:
                    print(f"  ✓ {output_name}.tif saved")
                    print(f"    Range: {valid.min():.3f} to {valid.max():.3f}")
                    print(f"    Mean:  {valid.mean():.3f}")
                else:
                    print(f"  ⚠ {output_name}.tif saved (all zero/NaN — check input extent)")

                processed.append(output_name)

    # Summary
    print(f"\n{'='*60}")
    print("Soil features complete!")
    print(f"{'='*60}")

    if processed:
        print("\nGenerated files:")
        for name in processed:
            print(f"  - {name}.tif")

    if skipped:
        print("\nSkipped (input not found):")
        for name in skipped:
            print(f"  - {name}.tif")
        print(f"\n  Place missing TIF files in: {soil_dir}")

    if not processed:
        print("\nNo soil features were processed. Check that input files exist.")
        sys.exit(1)

    print("\nNext step: Run stack_features.py to combine all 29 features")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python calculate_soil_features.py <watershed_name>")
        print("\nExample:")
        print("  python calculate_soil_features.py Bear_Creek_Watershed_10m")

        # Auto-detect if only one watershed directory exists
        base_dir = Path(__file__).resolve().parent.parent.parent
        output_base = base_dir / "GEE" / "TIF_Output"
        watersheds = [
            d.name
            for d in output_base.iterdir()
            if d.is_dir() and not d.name.startswith(".")
        ]

        if len(watersheds) == 1:
            watershed_name = watersheds[0]
            print(f"\nAuto-detected: {watershed_name}")
        else:
            print(f"\nAvailable watersheds: {', '.join(watersheds)}")
            sys.exit(1)
    else:
        watershed_name = sys.argv[1]

    process_soil_features(watershed_name)
