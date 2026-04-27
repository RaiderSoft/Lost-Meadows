#!/usr/bin/env python3
"""
Master Pipeline Script for Lost Meadows Detection
Runs the complete workflow from DEM to meadow probability map

Usage:
  python run_pipeline.py <input_dem.tif>

Example:
  python run_pipeline.py GEE/TIF_Input/Bear_Creek_Watershed_10m.tif

Steps executed:
  0. Preprocess raster to add value to nodata
  1. TauDEM hydrological processing
  2. TWI calculation (10m and 100m scales)
  3. Terrain features calculation
  4. Advanced features calculation (aspect, curvature, TPI, etc.)
  4b. Soil features processing
  5. Feature stacking (23 features)
  6. Training data preparation
  7. Per-watershed hyperparameter tuning (100 combinations, 5-fold CV)
  8. Model training (uses tuned hyperparameters)
  9. Meadow probability prediction
"""

import subprocess
import sys
import os
from pathlib import Path
import time
import numpy as np
import rasterio

def run_step(description, command, cwd=None):
    """Run a pipeline step and handle errors"""
    print(f"\n{'='*70}")
    print(f"STEP: {description}")
    print(f"{'='*70}")
    print(f"Command: {command}")
    print(f"Working directory: {cwd or 'current'}\n")

    start_time = time.time()

    result = subprocess.run(
        command,
        shell=True,
        cwd=cwd,
        capture_output=False,  # Show output in real-time
        text=True
    )

    elapsed = time.time() - start_time
    minutes = int(elapsed // 60)
    seconds = int(elapsed % 60)

    if result.returncode != 0:
        print(f"\n ERROR: {description} failed!")
        print(f"Exit code: {result.returncode}")
        sys.exit(1)
    else:
        print(f"\n✓ {description} completed in {minutes}m {seconds}s")

    return result

def fix_nodata(input_path: str, nodata_value: float = -9999.0) -> str:
    """
    Re-write a raster with an explicit NoData value before TauDEM processing.

    Without a defined NoData value, TauDEM treats the empty border region as
    real elevation data (~3e34), causing water to flow uphill out of the raster
    and producing stripe artifacts in all downstream outputs.

    Writes a new file at <stem>_fixed.tif and returns its path.
    The original file is not modified.
    """
    input_path = str(input_path)
    p = Path(input_path)
    output_path = str(p.parent / (p.stem + "_fixed.tif"))

    print(f"  Fixing NoData: {p.name} → {Path(output_path).name}")

    with rasterio.open(input_path) as src:
        profile = src.profile.copy()
        data = src.read(1).astype(np.float32)
        existing_nodata = src.nodata

    # Mask: old NoData sentinel, NaN, Inf, and extreme border values (~3e34)
    mask = np.zeros(data.shape, dtype=bool)
    if existing_nodata is not None:
        mask |= (data == existing_nodata)
    mask |= np.isnan(data) | np.isinf(data) | (data > 1e10) | (data < -1e10)

    n_masked = int(mask.sum())
    print(f"  {n_masked:,} border/sentinel pixels masked as NoData ({nodata_value})")

    data[mask] = nodata_value
    profile.update(dtype=rasterio.float32, nodata=nodata_value)

    with rasterio.open(output_path, "w", **profile) as dst:
        dst.write(data, 1)

    print(f"  ✓ Fixed raster written: {output_path}")
    return output_path


def get_repo_root():
    # run_pipeline.py is at the repo root
    return Path(__file__).resolve().parent

def main(input_dem, ncores):
    """Run the complete pipeline"""

    # Check if input DEM exists
    if not os.path.exists(input_dem):
        print(f"ERROR: Input DEM not found: {input_dem}")
        sys.exit(1)

    # Get absolute paths
    base_dir = get_repo_root()
    input_dem_abs = Path(input_dem).absolute()

    print(f"\n{'='*70}")
    print(f"LOST MEADOWS DETECTION PIPELINE")
    print(f"{'='*70}")
    print(f"Input DEM: {input_dem}")
    print(f"\nThis will execute 10 major steps and may take 2-4 hours.")
    print(f"  (Includes NoData fix, per-watershed hyperparameter tuning — adds ~1 minute)")
    print(f"{'='*70}")

    pipeline_start = time.time()

    # Step 0: Fix NoData — must run before TauDEM
    # Without an explicit NoData value, TauDEM treats the raster border as real
    # elevation data, causing stripe artifacts throughout all downstream outputs.
    print(f"\n{'='*70}")
    print(f"STEP: 0. Fix NoData Value in Input DEM")
    print(f"{'='*70}")
    fixed_dem = fix_nodata(input_dem_abs)
    fixed_dem_abs = Path(fixed_dem).absolute()

    # Watershed name is derived from the FIXED DEM stem so all downstream steps
    # look in the same output folder that TauDEM writes to.
    watershed_name = fixed_dem_abs.stem
    print(f"Watershed: {watershed_name}")
    print(f"Output directory: {base_dir}/GEE/TIF_Output/{watershed_name}")

    # Step 1: TauDEM workflow
    run_step(
        "1. TauDEM Hydrological Processing",
        f"python run_taudem_workflow.py {fixed_dem_abs} {ncores}",
        cwd=base_dir / "TauDEM"
    )

    # Step 2a: TWI 10m
    run_step(
        "2a. Calculate TWI at 10m resolution",
        f"python calculate_twi_10m.py {watershed_name}",
        cwd=base_dir / "FeatureEngineering" / "TWI"
    )

    # Step 2b: TWI 100m
    run_step(
        "2b. Calculate TWI at 100m resolution (resampled to 10m)",
        f"python calculate_twi_100m.py {watershed_name}",
        cwd=base_dir / "FeatureEngineering" / "TWI"
    )

    # Step 3: Terrain features
    run_step(
        "3. Calculate Terrain Features (slope, relative elevation, variability)",
        f"python calculate_terrain_features.py {watershed_name}",
        cwd=base_dir / "FeatureEngineering" / "Terrain"
    )

    # Step 4: Advanced features
    run_step(
        "4. Calculate Advanced Features (aspect, curvature, TPI, TRI, multi-scale)",
        f"python calculate_advanced_features.py {watershed_name}",
        cwd=base_dir / "FeatureEngineering" / "Advanced"
    )

    # Step 4b: Soil features
    run_step(
        "4b. Process Soil Features (depth to restrictive layer, hydraulic connectivity, organic matter)",
        f"python calculate_soil_features.py {watershed_name}",
        cwd=base_dir / "FeatureEngineering" / "Soil"
    )

    # Step 5: Stack features
    run_step(
        "5. Stack all 23 features into multi-band raster",
        f"python stack_features.py {watershed_name}",
        cwd=base_dir / "FeatureStacking"
    )

    # Step 6: Prepare training data
    run_step(
        "6. Prepare Training Data from Wetlands (OR/CA geodatabases)",
        f"python prepare_training_data.py {watershed_name}",
        cwd=base_dir / "Wetlands"
    )

    # Step 7: Hyperparameter tuning
    run_step(
        "7. Tune XGBoost Hyperparameters (100 combinations, 5-fold CV)",
        f"python xgboost_gridsearch.py {watershed_name}",
        cwd=base_dir / "ModelTraining"
    )

    # Step 8: Train model
    run_step(
        "8. Train XGBoost Model (tuned hyperparameters, 75/25 split)",
        f"python train_xgboost.py {watershed_name}",
        cwd=base_dir / "ModelTraining"
    )

    # Step 9: Predict meadow probabilities
    run_step(
        "9. Generate Meadow Probability Map",
        f"python predict_meadows.py {watershed_name}",
        cwd=base_dir / "ModelTraining"
    )

    # Pipeline complete!
    pipeline_elapsed = time.time() - pipeline_start
    total_minutes = int(pipeline_elapsed // 60)
    total_seconds = int(pipeline_elapsed % 60)

    output_dir = base_dir / "GEE" / "TIF_Output" / watershed_name

    print(f"\n{'='*70}")
    print(f"PIPELINE COMPLETE!")
    print(f"{'='*70}")
    print(f"Total time: {total_minutes}m {total_seconds}s")
    print(f"\nOutputs in: {output_dir}")
    print(f"\nKey files generated:")
    print(f"  ✓ 23 feature rasters (terrain + soil)")
    print(f"     - dd_h, dd_s, dd_v, slope, TWI, aspect, curvature, TPI, TRI, etc.")
    print(f"     - soil_depth_restrictive, soil_hydraulic_connectivity, soil_organic_matter")
    print(f"  ✓ features_stacked.tif (23-band multi-band raster)")
    print(f"  ✓ training_data_real.csv")
    print(f"  ✓ xgboost_model.pkl (trained model)")
    print(f"  ✓ {watershed_name}_xgboost_model_probability.tif (FINAL OUTPUT)")
    print(f"\nNext steps:")
    print(f"  1. Upload {watershed_name}_xgboost_model_probability.tif to Google Earth Engine")
    print(f"  2. Run GEE/MeadowVisualization.js for interactive map")
    print(f"{'='*70}\n")

if __name__ == "__main__":
    args = sys.argv[1:]
    base_dir = Path(__file__).resolve().parent
    keep_going = "--keep-going" in args
    use_all = "--all" in args

    # Parse --cores
    if "--cores" in args:
        idx = args.index("--cores")
        try:
            ncores = int(args[idx + 1])
        except (IndexError, ValueError):
            print("ERROR: --cores requires a number (e.g. --cores 8)")
            sys.exit(1)
    else:
        ncores = (os.cpu_count() or 4) - 2

    # Parse DEM paths (strip flags and flag values)
    skip_next = False
    paths = []
    for a in args:
        if skip_next:
            skip_next = False
            continue
        if a == "--cores":
            skip_next = True
        elif not a.startswith("--"):
            paths.append(a)

    tif_input = base_dir / "GEE" / "TIF_Input"

    if use_all:
        dems = sorted(tif_input.glob("*.tif"))
    elif paths:
        dems = [Path(p) for p in paths]
    else:
        print("Usage:")
        print("  python run_pipeline.py GEE/TIF_Input/Bear_Creek_Watershed_10m.tif [--cores N]")
        print("  python run_pipeline.py --all [--keep-going] [--cores N]")
        sys.exit(1)

    if len(dems) == 1:
        main(dems[0], ncores)
    else:
        results = []
        batch_start = time.time()

        for dem in dems:
            print(f"\n{'#'*70}")
            print(f"# Starting: {dem.name}")
            print(f"{'#'*70}")
            start = time.time()

            result = subprocess.run(
                [sys.executable, __file__, str(dem), "--cores", str(ncores)],
                cwd=base_dir
            )

            elapsed = int(time.time() - start)
            success = result.returncode == 0
            status = "✓ SUCCESS" if success else "✗ FAILED"
            results.append((dem.name, status, elapsed))
            print(f"\n{status}: {dem.name} ({elapsed // 60}m {elapsed % 60}s)")

            if not success and not keep_going:
                print("\nStopping batch. Use --keep-going to continue past failures.")
                break

        total_elapsed = int(time.time() - batch_start)
        n_success = sum(1 for _, s, _ in results if "SUCCESS" in s)
        n_failed = len(results) - n_success
        n_skipped = len(dems) - len(results)

        print(f"\n{'='*70}")
        print(f"BATCH COMPLETE — {n_success} succeeded, {n_failed} failed, {n_skipped} skipped")
        print(f"Total time: {total_elapsed // 60}m {total_elapsed % 60}s")
        print(f"{'='*70}")
        for name, status, elapsed in results:
            print(f"  {status}  {name}  ({elapsed // 60}m {elapsed % 60}s)")
        if n_skipped:
            for d in dems[len(results):]:
                print(f"  - SKIPPED  {d.name}")
        print()

        sys.exit(0 if n_failed == 0 else 1)