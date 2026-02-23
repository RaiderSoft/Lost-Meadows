#!/usr/bin/env python3
"""
Master Pipeline Script for Lost Meadows Detection
Runs the complete workflow from DEM to meadow probability map

Usage:
  python run_pipeline.py <input_dem.tif>

Example:
  python run_pipeline.py GEE/TIF_Input/Bear_Creek_Watershed_10m.tif

Steps executed:
  1. TauDEM hydrological processing
  2. TWI calculation (10m and 100m scales)
  3. Terrain features calculation
  4. Advanced features calculation (aspect, curvature, TPI, etc.)
  5. Feature stacking (20 features)
  6. Training data preparation
  7. Model training
  8. Meadow probability prediction
"""

import subprocess
import sys
import os
from pathlib import Path
import time

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

def get_repo_root():
    return Path(__file__).resolve().parents[1]

def main(input_dem):
    """Run the complete pipeline"""

    # Check if input DEM exists
    if not os.path.exists(input_dem):
        print(f"ERROR: Input DEM not found: {input_dem}")
        sys.exit(1)

    # Extract watershed name from filename
    watershed_name = Path(input_dem).stem

    # Get absolute paths
    repo_root = get_repo_root()
    base_dir = repo_root / "Lost-Meadows"
    input_dem_abs = Path(input_dem).absolute()

    print(f"\n{'='*70}")
    print(f"LOST MEADOWS DETECTION PIPELINE")
    print(f"{'='*70}")
    print(f"Input DEM: {input_dem}")
    print(f"Watershed: {watershed_name}")
    print(f"Output directory: {base_dir}/GEE/TIF_Output/{watershed_name}")
    print(f"\nThis will execute 8 major steps and may take 2-4 hours.")
    print(f"{'='*70}")

    input(f"\nPress Enter to start the pipeline...")

    pipeline_start = time.time()

    # Step 1: TauDEM workflow
    run_step(
        "1. TauDEM Hydrological Processing",
        f"python run_taudem_workflow.py {input_dem_abs}",
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

    # Step 5: Stack features
    run_step(
        "5. Stack all 20 features into multi-band raster",
        f"python stack_features.py {watershed_name}",
        cwd=base_dir / "FeatureStacking"
    )

    # Step 6: Prepare training data
    run_step(
        "6. Prepare Training Data from Wetlands (OR/CA geodatabases)",
        f"python prepare_training_data.py {watershed_name}",
        cwd=base_dir / "Wetlands"
    )

    # Step 7: Train model
    run_step(
        "7. Train XGBoost Model (300 trees, 75/25 split)",
        f"python train_xgboost.py {watershed_name}",
        cwd=base_dir / "ModelTraining"
    )

    # Step 8: Predict meadow probabilities
    run_step(
        "8. Generate Meadow Probability Map",
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
    print(f"  ✓ 20 feature rasters (terrain)")
    print(f"     - dd_h, dd_s, dd_v, slope, TWI, aspect, curvature, TPI, TRI, etc.")
    print(f"  ✓ features_stacked.tif (20-band multi-band raster)")
    print(f"  ✓ training_data_real.csv")
    print(f"  ✓ random_forest_model.pkl (trained model)")
    print(f"  ✓ {watershed_name}_meadow_probability.tif (FINAL OUTPUT)")
    print(f"\nNext steps:")
    print(f"  1. Upload {watershed_name}_meadow_probability.tif to Google Earth Engine")
    print(f"  2. Run GEE/MeadowVisualization.js for interactive map")
    print(f"{'='*70}\n")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python run_pipeline.py <input_dem.tif>")
        print("\nExample:")
        print("  python run_pipeline.py GEE/TIF_Input/Bear_Creek_Watershed_10m.tif")
        print("\nAvailable DEMs in TIF_Input:")
        
        # Adjustment for file pathing
        repo_root = get_repo_root()

        tif_input = repo_root / "GEE" / "TIF_Input"
        if tif_input.exists():
            tif_files = sorted(tif_input.glob("*.tif"))
            if tif_files:
                for tif in tif_files:
                    print(f"  - {tif.name}")
            else:
                print("  (No TIF files found)")

        sys.exit(1)

    input_dem = sys.argv[1]
    main(input_dem)
