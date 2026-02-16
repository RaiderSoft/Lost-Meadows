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

    # Number of cores (adjust based on your CPU)
    # Using 4 out of 8 available cores - good balance of speed and system responsiveness
    ncores = 4

    print(f"\n{'='*60}")
    print(f"TauDEM Workflow - {watershed_name}")
    print(f"{'='*60}")
    print(f"Input: {input_dem}")
    print(f"Output: {output_dir}")
    print(f"Cores: {ncores} (out of 16 available)\n")
    
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