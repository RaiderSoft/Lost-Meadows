#!/usr/bin/env python3
"""
Automated TauDEM workflow for meadow detection
Usage: python run_taudem_workflow.py <input_dem.tif>

Examples:
  python run_taudem_workflow.py ../GEE/TIF_Input/Bear_Creek_Watershed_10m.tif
  python run_taudem_workflow.py ../GEE/TIF_Input/East_Fork_Illinois_River_10m.tif

Output directory will be automatically created as: TIF_Output/<watershed_name>/
"""

import subprocess
import sys
import os
import numpy as np
import rasterio
from scipy.ndimage import distance_transform_edt
from pathlib import Path

def run_cmd(cmd, description):
    """Run a shell command and print status"""
    print(f"\n{'='*60}")
    print(f"RUNNING: {description}")
    print(f"{'='*60}")
    print(f"Command: {cmd}\n")

    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)

    if result.returncode != 0:
        print(f"ERROR: {description} failed!")
        print(f"stderr: {result.stderr}")
        sys.exit(1)
    else:
        print(f"SUCCESS: {description} completed!")

    return result

def extract_watershed_name(input_dem):
    """
    Extract watershed name from input DEM filename
    Examples:
      Bear_Creek_Watershed_10m.tif -> Bear_Creek_Watershed_10m
      East_Fork_Illinois_River_10m.tif -> East_Fork_Illinois_River_10m
    """
    return Path(input_dem).stem

def fix_distance_rasters(output_dir):
    """
    TauDEM's dinfdistdown leaves invalid values (nodata sentinel ~-3.4e38 and
    Inf) in the distance rasters for pixels where it cannot determine a valid
    downslope flow path — typically at watershed boundary edges and flow
    divides. These invalid pixels are dropped by predict_meadows.py, creating
    gaps in the final output.

    This function fills those invalid pixels using nearest-neighbor
    interpolation from surrounding valid pixels, recovering ~1.4M pixels
    that would otherwise be missing from the prediction.
    """
    distance_files = ["dd_s.tif", "dd_h.tif", "dd_v.tif"]

    print(f"\n{'='*60}")
    print("Fixing invalid pixels in stream distance rasters")
    print(f"{'='*60}")

    for fname in distance_files:
        fpath = os.path.join(output_dir, fname)
        with rasterio.open(fpath) as src:
            profile = src.profile.copy()
            data = src.read(1).astype(np.float32)

        invalid = np.isnan(data) | np.isinf(data) | (data < -1e10)
        n_invalid = int(invalid.sum())

        if n_invalid > 0:
            # distance_transform_edt returns the indices of the nearest valid
            # pixel for every invalid pixel — fill from those neighbours
            _, nearest = distance_transform_edt(
                invalid, return_distances=True, return_indices=True
            )
            data[invalid] = data[nearest[0][invalid], nearest[1][invalid]]

        with rasterio.open(fpath, "w", **profile) as dst:
            dst.write(data, 1)

        print(f"  ✓ {fname}: filled {n_invalid:,} invalid pixels via nearest-neighbour")


def main(input_dem):
    """Run full TauDEM workflow"""

    # Check if file exists
    if not os.path.exists(input_dem):
        print(f"ERROR: Input file {input_dem} not found!")
        sys.exit(1)

    # Extract watershed name from filename
    watershed_name = extract_watershed_name(input_dem)

    # Setup output directory using watershed name
    base_output_dir = "../GEE/TIF_Output"
    output_dir = os.path.join(base_output_dir, watershed_name)
    os.makedirs(output_dir, exist_ok=True)

    # Get base name without extension (for TauDEM internal files)
    base = Path(input_dem).stem

    # Ask user how many cores to use for MPI parallelism
    available_cores = os.cpu_count() or 4
    print(f"\nYour machine has {available_cores} CPU cores available.")
    print("More cores = faster TauDEM processing.")
    print("Recommended: leave at least 2 cores free for the OS.")
    while True:
        try:
            ncores = int(input(f"How many cores should TauDEM use? [1-{available_cores}]: "))
            if 1 <= ncores <= available_cores:
                break
            print(f"  Please enter a number between 1 and {available_cores}.")
        except ValueError:
            print("  Please enter a valid number.")

    print(f"\n{'='*60}")
    print(f"TauDEM Workflow - {watershed_name}")
    print(f"{'='*60}")
    print(f"Input: {input_dem}")
    print(f"Output: {output_dir}")
    print(f"Cores: {ncores}\n")
    
    # Helper to create output path
    def out(filename):
        return os.path.join(output_dir, filename)
    
    # Step 1: Fill pits
    run_cmd(
        f"mpiexec -n {ncores} pitremove -z {input_dem} -fel {out(base + '_filled.tif')}",
        "Step 1: Fill pits"
    )
    
    # Step 2: D8 flow direction
    run_cmd(
        f"mpiexec -n {ncores} d8flowdir -fel {out(base + '_filled.tif')} -p {out(base + '_p.tif')} -sd8 {out(base + '_sd8.tif')}",
        "Step 2: D8 flow direction"
    )
    
    # Step 3: D8 flow accumulation
    run_cmd(
        f"mpiexec -n {ncores} aread8 -p {out(base + '_p.tif')} -ad8 {out(base + '_ad8.tif')}",
        "Step 3: D8 flow accumulation"
    )
    
    # Step 4: Stream network (threshold = 350 per paper)
    run_cmd(
        f"mpiexec -n {ncores} threshold -ssa {out(base + '_ad8.tif')} -src {out(base + '_src.tif')} -thresh 350",
        "Step 4: Stream network definition"
    )
    
    # Step 5: D-infinity flow direction
    run_cmd(
        f"mpiexec -n {ncores} dinfflowdir -fel {out(base + '_filled.tif')} -ang {out(base + '_ang.tif')} -slp {out(base + '_slp.tif')}",
        "Step 5: D-infinity flow direction"
    )
    
    # Step 6: D-infinity contributing area
    run_cmd(
        f"mpiexec -n {ncores} areadinf -ang {out(base + '_ang.tif')} -sca {out(base + '_sca.tif')}",
        "Step 6: D-infinity contributing area"
    )
    
    # Step 7a: Distance to stream - surface
    run_cmd(
        f"mpiexec -n {ncores} dinfdistdown -ang {out(base + '_ang.tif')} -fel {out(base + '_filled.tif')} -src {out(base + '_src.tif')} -dd {out('dd_s.tif')} -m ave s",
        "Step 7a: Distance to stream (surface)"
    )
    
    # Step 7b: Distance to stream - horizontal
    run_cmd(
        f"mpiexec -n {ncores} dinfdistdown -ang {out(base + '_ang.tif')} -fel {out(base + '_filled.tif')} -src {out(base + '_src.tif')} -dd {out('dd_h.tif')} -m ave h",
        "Step 7b: Distance to stream (horizontal)"
    )
    
    # Step 7c: Distance to stream - vertical
    run_cmd(
        f"mpiexec -n {ncores} dinfdistdown -ang {out(base + '_ang.tif')} -fel {out(base + '_filled.tif')} -src {out(base + '_src.tif')} -dd {out('dd_v.tif')} -m ave v",
        "Step 7c: Distance to stream (vertical)"
    )

    # Step 8: Fix invalid pixels in stream distance rasters
    # dinfdistdown leaves nodata sentinels (~-3.4e38) and Inf values for pixels
    # where it cannot compute a valid downslope path (boundary edges, flow divides).
    # These are filled via nearest-neighbor interpolation so no pixels are dropped.
    fix_distance_rasters(output_dir)

    print(f"\n{'='*60}")
    print(f"TauDEM workflow completed successfully!")
    print(f"{'='*60}")
    print(f"\nAll outputs saved to: {output_dir}")
    print("\nKey output files:")
    print("  - dd_s.tif (surface distance to stream)")
    print("  - dd_h.tif (horizontal distance to stream)")
    print("  - dd_v.tif (vertical distance to stream)")
    print(f"  - {base}_sca.tif (specific catchment area)")
    print(f"  - {base}_slp.tif (slope)")
    print("\nNext: Run calculate_twi.py to generate TWI layers")

    print(f"\n{'='*60}")
    print("TauDEM Processing Complete!")
    print(f"{'='*60}")

    print("\nNOTE: TauDEM intermediate files (_sca, _slp, _filled) are kept")
    print("      temporarily - they're needed for TWI and terrain calculations.")
    print("      They will be cleaned up after terrain features are done.")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python run_taudem_workflow.py <input_dem.tif>")
        print("\nExample:")
        print("  python run_taudem_workflow.py ../GEE/TIF_Input/Bear_Creek_Watershed_10m.tif")
        sys.exit(1)

    input_dem = sys.argv[1]

    main(input_dem)