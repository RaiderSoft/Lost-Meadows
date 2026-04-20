#!/usr/bin/env python3
"""
Lost Meadows Pipeline Test
==========================
Runs the complete pipeline on synthetic 30x30 pixel data to verify that
all dependencies, imports, and code paths are working correctly.

Completes in under 30 seconds instead of 2-4 hours.

REQUIREMENTS:
  - Must be run inside the meadow conda environment:
        conda activate meadow
  - Must be run from the repository root directory:
        python Tests/TestPipeline/run_test.py

Input files:
  - No real input files are required. All test data is generated synthetically.
  - If soil TIFs exist in GEE/TIF_Input/Soil/ they will be used as-is.
    If they do not exist, small synthetic stand-ins are created for this run only.

Output files (all deleted automatically after the test):
  - GEE/TIF_Output/test_watershed/   — temporary working directory for all
                                        feature rasters, stacked output, and
                                        training CSV created during the test

What this tests:
  - All Python packages are importable (rasterio, numpy, xgboost, etc.)
  - TauDEM is installed and on PATH
  - Soil TIF files are in the correct location
  - Every feature engineering script executes without errors
  - Feature stacking runs and produces a 23-band raster
  - XGBoost model training and prediction complete successfully

What this does NOT test:
  - TauDEM processing (synthetic TauDEM outputs are generated directly
    to skip the ~45 minute hydrological analysis step)
  - Wetland geodatabases (a synthetic training CSV is used instead of
    reading from the 2.4 GB .gdb files)
  - DagsHub/MLflow remote tracking (skipped if DAGSHUB_USER_TOKEN is not set)
"""

import sys
import os
import subprocess
import shutil
import time
from pathlib import Path

# ---------------------------------------------------------------------------
# Locate repo root (this script lives at Tests/TestPipeline/run_test.py)
# ---------------------------------------------------------------------------
REPO_ROOT = Path(__file__).resolve().parents[2]

TEST_WATERSHED = "test_watershed"
OUTPUT_DIR = REPO_ROOT / "GEE" / "TIF_Output" / TEST_WATERSHED
SOIL_DIR = REPO_ROOT / "GEE" / "TIF_Input" / "Soil"

# Soil file names the pipeline expects (POLARIS 30m, stored in Soil/)
SOIL_FILES = {
    "polaris_clay_pct_0_5cm.tif":               (5.0, 60.0),
    "polaris_organic_matter_0_5cm.tif":         (-2.0, 2.0),
    "polaris_saturated_water_content_0_5cm.tif":(0.3, 0.8),
}

FEATURE_NAMES = [
    "slope", "elev_5x5_rel", "elev_5x5_std_dev", "slope_5x5_std_dev",
    "twi_10m", "twi_100m", "dd_s", "dd_h", "dd_v",
    "aspect", "curvature_profile", "curvature_plan", "elevation",
    "tpi_3x3", "tpi_11x11", "tpi_21x21", "tri",
    "elev_std_3x3", "elev_std_9x9", "slope_std_9x9",
    # Soil features (3) — POLARIS 30m
    "soil_clay_pct", "soil_organic_matter", "soil_saturated_water_content",
]

# Tracks soil TIFs we created so we can clean them up
_temp_soil_files = []

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

PASS  = "\033[92m PASS\033[0m"
FAIL  = "\033[91m FAIL\033[0m"
SKIP  = "\033[93m SKIP\033[0m"
INFO  = "\033[94m INFO\033[0m"

results = []


def record(label, status, note=""):
    results.append((label, status, note))
    symbol = {"PASS": PASS, "FAIL": FAIL, "SKIP": SKIP}.get(status, INFO)
    suffix = f"  — {note}" if note else ""
    print(f"  [{symbol}] {label}{suffix}")


def run_step(label, cmd, cwd, env=None, timeout=120):
    """Run a subprocess step and record pass/fail."""
    merged_env = {**os.environ, **(env or {})}
    try:
        result = subprocess.run(
            cmd, shell=True, cwd=str(cwd),
            capture_output=True, text=True, env=merged_env,
            timeout=timeout
        )
    except subprocess.TimeoutExpired:
        record(label, "FAIL", f"timed out after {timeout}s — check network/DagsHub connection")
        return False
    if result.returncode == 0:
        record(label, "PASS")
        return True
    else:
        # Show last few lines of stderr to help diagnose
        stderr_tail = "\n".join(result.stderr.strip().splitlines()[-5:])
        record(label, "FAIL", f"\n      {stderr_tail}")
        return False


# ---------------------------------------------------------------------------
# Synthetic raster generation
# ---------------------------------------------------------------------------

def _make_profile(width=30, height=30):
    """Return a rasterio profile for a small test raster in EPSG:32610."""
    from rasterio.transform import from_origin
    from rasterio.crs import CRS
    transform = from_origin(west=500000, north=4650300, xsize=10, ysize=10)
    return {
        "driver": "GTiff",
        "dtype": "float32",
        "width": width,
        "height": height,
        "count": 1,
        "crs": CRS.from_epsg(32610),
        "transform": transform,
        "nodata": -9999.0,
    }


def write_tif(path, data, profile=None):
    """Write a 2-D numpy array to a single-band GeoTIFF."""
    import rasterio
    import numpy as np
    p = profile or _make_profile()
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with rasterio.open(path, "w", **p) as dst:
        dst.write(data.astype(np.float32), 1)


def make_synthetic_taudem_outputs():
    """
    Generate the files that TauDEM would normally produce.
    This lets the pipeline test run in seconds instead of ~45 minutes.
    """
    import numpy as np

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    profile = _make_profile()
    rng = np.random.default_rng(42)

    def rand(low, high):
        return rng.uniform(low, high, (30, 30)).astype(np.float32)

    # Filled DEM — realistic elevation gradient so terrain calculations
    # produce meaningful (non-degenerate) feature values
    x = np.linspace(0, 1, 30)
    y = np.linspace(0, 1, 30)
    xx, yy = np.meshgrid(x, y)
    elevation = (1200 + 300 * xx + 200 * yy + 20 * rng.standard_normal((30, 30))).astype(np.float32)
    write_tif(OUTPUT_DIR / f"{TEST_WATERSHED}_filled.tif", elevation, profile)

    # D-infinity slope (in degrees, as expected by calculate_twi scripts)
    write_tif(OUTPUT_DIR / f"{TEST_WATERSHED}_slp.tif", rand(0.5, 30.0), profile)

    # Specific catchment area
    write_tif(OUTPUT_DIR / f"{TEST_WATERSHED}_sca.tif", rand(5.0, 800.0), profile)

    # D-infinity flow direction angle
    write_tif(OUTPUT_DIR / f"{TEST_WATERSHED}_ang.tif", rand(0.0, 6.28), profile)

    # Stream distances
    write_tif(OUTPUT_DIR / "dd_s.tif", rand(0.0, 250.0), profile)
    write_tif(OUTPUT_DIR / "dd_h.tif", rand(0.0, 250.0), profile)
    write_tif(OUTPUT_DIR / "dd_v.tif", rand(0.0, 40.0),  profile)


def make_synthetic_soil_tifs():
    """
    Create small synthetic soil TIFs in GEE/TIF_Input/Soil/ if the real
    files are not already present. These are marked for cleanup after the test.
    """
    import numpy as np
    from rasterio.transform import from_origin
    from rasterio.crs import CRS

    # Soil TIFs are at 30m resolution, covering the watershed area with margin
    soil_profile = {
        "driver": "GTiff",
        "dtype": "float32",
        "width": 20,
        "height": 20,
        "count": 1,
        "crs": CRS.from_epsg(32610),
        "transform": from_origin(west=499800, north=4650500, xsize=30, ysize=30),
        "nodata": -9999.0,
    }

    rng = np.random.default_rng(99)
    for filename, (lo, hi) in SOIL_FILES.items():
        dest = SOIL_DIR / filename
        if dest.exists():
            continue  # Real file present — don't overwrite it
        data = rng.uniform(lo, hi, (20, 20)).astype(np.float32)
        write_tif(dest, data, soil_profile)
        _temp_soil_files.append(dest)


def make_synthetic_training_csv():
    """
    Write a synthetic training_data_real.csv to the watershed output dir.
    This bypasses the geodatabase step (which requires the 2.4 GB .gdb files).
    200 samples: 50 wetland (1) and 150 non-wetland (0).
    """
    import numpy as np
    import pandas as pd

    rng = np.random.default_rng(7)
    n = 200
    data = {name: rng.uniform(0, 1, n) for name in FEATURE_NAMES}
    labels = np.zeros(n, dtype=int)
    labels[:50] = 1
    rng.shuffle(labels)
    data["label"] = labels

    df = pd.DataFrame(data)
    csv_path = OUTPUT_DIR / "training_data_real.csv"
    df.to_csv(csv_path, index=False)


# ---------------------------------------------------------------------------
# Prerequisite checks
# ---------------------------------------------------------------------------

def check_prerequisites():
    print("\n── Prerequisite checks ─────────────────────────────────────────")

    # Python packages
    packages = [
        ("rasterio",    "import rasterio"),
        ("numpy",       "import numpy"),
        ("scipy",       "import scipy"),
        ("pandas",      "import pandas"),
        ("geopandas",   "import geopandas"),
        ("sklearn",     "import sklearn"),
        ("xgboost",     "import xgboost"),
        ("mlflow",      "import mlflow"),
        ("dagshub",     "import dagshub"),
        ("joblib",      "import joblib"),
    ]
    for name, stmt in packages:
        try:
            exec(stmt)
            record(f"import {name}", "PASS")
        except ImportError as e:
            record(f"import {name}", "FAIL", str(e))

    # TauDEM binary
    result = subprocess.run("pitremove", shell=True, capture_output=True, text=True)
    if result.returncode == 0 or "Usage" in result.stdout + result.stderr:
        record("TauDEM (pitremove)", "PASS")
    else:
        record("TauDEM (pitremove)", "FAIL",
               "run: conda activate meadow — then re-run this test")

    # Soil files
    for fname in SOIL_FILES:
        path = SOIL_DIR / fname
        if path.exists():
            record(f"Soil: {fname}", "PASS")
        else:
            record(f"Soil: {fname}", "SKIP",
                   "not found — synthetic file will be used for this test run")

    # Wetland geodatabases (optional but noted)
    for gdb in ["OR_geodatabase_wetlands.gdb", "CA_geodatabase_wetlands.gdb"]:
        path = REPO_ROOT / "Wetlands" / gdb
        if path.exists():
            record(f"Wetlands: {gdb}", "PASS")
        else:
            record(f"Wetlands: {gdb}", "SKIP",
                   "not found — geodatabase step skipped in this test")


# ---------------------------------------------------------------------------
# Pipeline steps
# ---------------------------------------------------------------------------

def run_pipeline_steps():
    print("\n── Pipeline steps ──────────────────────────────────────────────")
    fe = REPO_ROOT / "FeatureEngineering"

    # TWI
    run_step("2a. TWI 10m",
             f"python calculate_twi_10m.py {TEST_WATERSHED}",
             fe / "TWI")

    run_step("2b. TWI 100m",
             f"python calculate_twi_100m.py {TEST_WATERSHED}",
             fe / "TWI")

    # Terrain
    run_step("3. Terrain features",
             f"python calculate_terrain_features.py {TEST_WATERSHED}",
             fe / "Terrain")

    # Advanced
    run_step("4. Advanced features",
             f"python calculate_advanced_features.py {TEST_WATERSHED}",
             fe / "Advanced")

    # Soil
    run_step("4b. Soil features",
             f"python calculate_soil_features.py {TEST_WATERSHED}",
             fe / "Soil")

    # Stacking
    run_step("5. Feature stacking (23 bands)",
             f"python stack_features.py {TEST_WATERSHED}",
             REPO_ROOT / "FeatureStacking")

    # Training data — always use synthetic CSV (skip geodatabases)
    # Check geodatabases are present even though we skip reading them here
    or_gdb = REPO_ROOT / "Wetlands" / "OR_geodatabase_wetlands.gdb"
    ca_gdb = REPO_ROOT / "Wetlands" / "CA_geodatabase_wetlands.gdb"
    if or_gdb.exists() and ca_gdb.exists():
        record("6. Prepare training data",  "SKIP",
               "geodatabase step always skipped in test (uses synthetic CSV) — "
               "both .gdb folders confirmed present in Wetlands/")
    else:
        missing = []
        if not or_gdb.exists():
            missing.append("OR_geodatabase_wetlands.gdb")
        if not ca_gdb.exists():
            missing.append("CA_geodatabase_wetlands.gdb")
        record("6. Prepare training data", "FAIL",
               f"missing from Wetlands/: {', '.join(missing)} — "
               "download from WetlandGeodatabases release (see SETUP.md Step 3)")

    # Hyperparameter tuning
    run_step("7. Hyperparameter tuning",
             f"python xgboost_gridsearch.py {TEST_WATERSHED}",
             REPO_ROOT / "ModelTraining",
             timeout=300)

    # Training — uses test_train.py to avoid DagsHub network calls
    run_step("8. Train XGBoost",
             f"python Tests/TestPipeline/test_train.py {TEST_WATERSHED}",
             REPO_ROOT)

    # Prediction (only if model file was produced)
    model_file = OUTPUT_DIR / "xgboost_model.pkl"
    if model_file.exists():
        run_step("9. Predict meadow probabilities",
                 f"python predict_meadows.py {TEST_WATERSHED}",
                 REPO_ROOT / "ModelTraining")
    else:
        record("9. Predict meadow probabilities", "SKIP",
               "model not produced — training step was skipped or failed")


# ---------------------------------------------------------------------------
# Cleanup
# ---------------------------------------------------------------------------

def cleanup():
    # Remove the test watershed output directory
    if OUTPUT_DIR.exists():
        shutil.rmtree(OUTPUT_DIR)

    # Remove any synthetic soil TIFs we created
    for path in _temp_soil_files:
        if path.exists():
            path.unlink()

    # Remove local MLflow test runs if created
    mlruns = REPO_ROOT / "Tests" / "TestPipeline" / "test_mlruns"
    if mlruns.exists():
        shutil.rmtree(mlruns)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    print("=" * 60)
    print("  Lost Meadows — Pipeline Test")
    print("=" * 60)

    # Confirm we're running from repo root
    if not (REPO_ROOT / "run_pipeline.py").exists():
        print("\nERROR: Could not locate run_pipeline.py.")
        print("Run this script from the repository root:")
        print("    python Tests/TestPipeline/run_test.py")
        sys.exit(1)

    start = time.time()

    # 1. Prerequisites
    check_prerequisites()

    # 2. Set up synthetic data
    print("\n── Generating synthetic test data ──────────────────────────────")
    try:
        make_synthetic_taudem_outputs()
        make_synthetic_soil_tifs()
        make_synthetic_training_csv()
        record("Synthetic data created", "PASS",
               f"30×30 pixel test watershed at {OUTPUT_DIR.name}")
    except Exception as e:
        record("Synthetic data created", "FAIL", str(e))
        print("\nCannot continue without test data. Aborting.")
        sys.exit(1)

    # 3. Run pipeline steps
    run_pipeline_steps()

    # 4. Cleanup
    cleanup()

    # 5. Summary
    elapsed = time.time() - start
    passed  = sum(1 for _, s, _ in results if s == "PASS")
    failed  = sum(1 for _, s, _ in results if s == "FAIL")
    skipped = sum(1 for _, s, _ in results if s == "SKIP")

    print("\n" + "=" * 60)
    print(f"  Results: {passed} passed, {failed} failed, {skipped} skipped")
    print(f"  Time: {elapsed:.1f}s")
    print("=" * 60)

    if failed > 0:
        print("\nSome steps failed. Check the output above for details.")
        print("Common fixes:")
        print("  - Wrong conda environment: conda activate meadow")
        print("  - Missing data files: see SETUP.md → Step 3")
        sys.exit(1)
    elif skipped > 0:
        print("\nAll checks passed. Some steps were skipped:")
        if not os.environ.get("DAGSHUB_USER_TOKEN"):
            print("  - Training/prediction: set DAGSHUB_USER_TOKEN (see SETUP.md → Step 4)")
        print("\nFor a full test, complete all data setup in SETUP.md and re-run.")
    else:
        print("\nAll checks passed. Your environment is fully configured.")


if __name__ == "__main__":
    main()
