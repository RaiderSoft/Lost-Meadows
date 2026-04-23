#!/usr/bin/env python3
"""
Batch pipeline runner — processes multiple watersheds sequentially overnight.

Usage:
  python run_batch.py GEE/TIF_Input/Bear_Creek_Watershed_10m.tif GEE/TIF_Input/Gold_Hill_10m.tif ...

Or to run all DEMs in TIF_Input:
  python run_batch.py --all

Flags:
  --all          Run all .tif files found in GEE/TIF_Input/
  --keep-going   Continue to next watershed if one fails (default: stop on failure)

================================================================================
ONE-TIME SETUP — required before using this script
================================================================================

Two small edits are needed to prevent interactive prompts from blocking the
batch run. Without them the script will hang waiting for keyboard input.

--- 1. run_pipeline.py (repo root) ---

Delete or comment out the "Press Enter" line so the pipeline starts
automatically. Find this line (around line 91) and remove it:

    input(f"\\nPress Enter to start the pipeline...")

--- 2. TauDEM/run_taudem_workflow.py ---

Replace the interactive core-count prompt with a hardcoded value.
Find this block (around line 108) and replace the entire section:

    REMOVE:
        available_cores = os.cpu_count() or 4
        print(f"\\nYour machine has {available_cores} CPU cores available.")
        print("More cores = faster TauDEM processing.")
        print("Recommended: leave at least 2 cores free for the OS.")
        while True:
            try:
                ncores = int(input(f"How many cores should TauDEM use? [1-{{available_cores}}]: "))
                if 1 <= ncores <= available_cores:
                    break
                print(f"  Please enter a number between 1 and {{available_cores}}.")
            except ValueError:
                print("  Please enter a valid number.")

    REPLACE WITH (adjust 8 to match your machine):
        ncores = min(8, os.cpu_count() or 8)

Recommended: total cores minus 2 (e.g. 10-core machine -> use 8).
================================================================================
"""

import subprocess
import sys
import time
from pathlib import Path


def main():
    repo_root = Path(__file__).resolve().parent
    tif_input = repo_root / "GEE" / "TIF_Input"

    args = sys.argv[1:]
    keep_going = "--keep-going" in args
    use_all = "--all" in args
    paths = [a for a in args if not a.startswith("--")]

    if use_all:
        dems = sorted(tif_input.glob("*.tif"))
    elif paths:
        dems = [Path(p) for p in paths]
    else:
        print("No DEMs specified. Pass paths or use --all.")
        print("\nUsage:")
        print("  python run_batch.py GEE/TIF_Input/Bear_Creek_Watershed_10m.tif [more...] [--keep-going]")
        print("  python run_batch.py --all [--keep-going]")
        sys.exit(1)

    if not dems:
        print("No .tif files found in GEE/TIF_Input/")
        sys.exit(1)

    print(f"\nBatch run: {len(dems)} watershed(s)  |  keep-going: {keep_going}")
    for d in dems:
        print(f"  - {d.name}")
    print()

    results = []
    batch_start = time.time()

    for dem in dems:
        print(f"\n{'#'*70}")
        print(f"# Starting: {dem.name}")
        print(f"{'#'*70}")
        start = time.time()

        result = subprocess.run(
            [sys.executable, "run_pipeline.py", str(dem)],
            cwd=repo_root
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
        skipped = dems[len(results):]
        for d in skipped:
            print(f"  - SKIPPED  {d.name}")
    print()

    sys.exit(0 if n_failed == 0 else 1)


if __name__ == "__main__":
    main()