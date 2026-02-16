#!/usr/bin/env python3
"""
Automated TauDEM workflow for meadow detection
Usage: python run_taudem_workflow.py input_dem.tif [run_number]

# Future runs will auto-create folders 2, 3, 4, etc.
python run_taudem_workflow.py ../GEE/TIF_Input/3DEP_10m_TEST_watershed.tif

# Or specify a run number manually
python run_taudem_workflow.py ../GEE/TIF_Input/some_other.tif 5

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

def get_next_run_number(base_output_dir):
    """Find the next available run number"""
    if not os.path.exists(base_output_dir):
        return 1
    
    existing = [d for d in os.listdir(base_output_dir) if d.isdigit()]
    if not existing:
        return 1
    
    return max(int(d) for d in existing) + 1

def main(input_dem, run_number=None):
    """Run full TauDEM workflow"""
    
    # Check if file exists
    if not os.path.exists(input_dem):
        print(f"ERROR: Input file {input_dem} not found!")
        sys.exit(1)
    
    # Setup output directory
    base_output_dir = "../GEE/TIF_Output"
    
    if run_number is None:
        run_number = get_next_run_number(base_output_dir)
    
    output_dir = os.path.join(base_output_dir, str(run_number))
    os.makedirs(output_dir, exist_ok=True)
    
    # Get base name without extension
    base = Path(input_dem).stem
    
    # Number of cores (adjust based on your CPU)
    ncores = 4
    
    print(f"\n{'='*60}")
    print(f"TauDEM Workflow - Run #{run_number}")
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
    
    # NEW: Clean up intermediate files
    print("\nCleaning up intermediate files...")
    
    # Get the base name from the input DEM
    base_name = Path(input_dem).stem
    
    intermediates = [
        output_dir / f"{base_name}_filled.tif",
        output_dir / f"{base_name}_p.tif",
        output_dir / f"{base_name}_ad8.tif",
        output_dir / f"{base_name}_src.tif",
        output_dir / f"{base_name}_ang.tif",
        output_dir / f"{base_name}_sd8.tif",
    ]
    
    for file in intermediates:
        if file.exists():
            file.unlink()
            print(f"  ✓ Deleted {file.name}")
    
    print(f"\nKept essential files:")
    print(f"  - {base_name}_sca.tif (for TWI)")
    print(f"  - {base_name}_slp.tif (slope)")
    print(f"  - dd_s.tif, dd_h.tif, dd_v.tif (features)")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python run_taudem_workflow.py input_dem.tif [run_number]")
        sys.exit(1)
    
    input_dem = sys.argv[1]
    run_number = int(sys.argv[2]) if len(sys.argv) > 2 else None
    
    main(input_dem, run_number)