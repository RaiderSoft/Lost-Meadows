#!/bin/bash
# =============================================================================
# Lost Meadows — Slurm Array Job
# Runs multiple watersheds in parallel across nodes.
#
# Each array task handles WATERSHEDS_PER_NODE watersheds simultaneously
# using background processes, then waits for all to finish.
#
# Usage:
#   sbatch SLURM/submit_watersheds.slurm
#
# Tune before submitting:
#   --array upper bound  : ceil(total_tifs / WATERSHEDS_PER_NODE) - 1
#   --cpus-per-task      : WATERSHEDS_PER_NODE * CORES_PER_WATERSHED
#   --partition          : your ORCA partition name
#   --time               : add buffer beyond expected ~5 min/watershed
#   CONDA_ENV            : name of your conda environment
# =============================================================================

#SBATCH --job-name=lost_meadows
#SBATCH --array=0-7%25           # 8 tasks (119 watersheds / 16 each), max 25 nodes at once
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=64       # 16 watersheds × 4 cores = all 64 cores
#SBATCH --mem=200G               # 576GB available, 200G is plenty of headroom
#SBATCH --time=00:30:00
#SBATCH --partition=normal
#SBATCH --output=SLURM/logs/%A_%a.out
#SBATCH --error=SLURM/logs/%A_%a.err

# --- Config ---
WATERSHEDS_PER_NODE=16
CORES_PER_WATERSHED=4
CONDA_ENV=meadow
REPO_ROOT=$SLURM_SUBMIT_DIR
TIF_DIR="${REPO_ROOT}/GEE/TIF_Input"

# --- Activate conda ---
source /home/lm1/miniconda3/etc/profile.d/conda.sh
conda activate "${CONDA_ENV}"
export LD_PRELOAD=$CONDA_PREFIX/lib/libstdc++.so.6
set -a && source "${REPO_ROOT}/.env" && set +a

# --- Build watershed list ---
mapfile -t ALL_TIFS < <(ls "${TIF_DIR}"/*.tif 2>/dev/null | sort)
TOTAL=${#ALL_TIFS[@]}

if [ "$TOTAL" -eq 0 ]; then
    echo "ERROR: No .tif files found in ${TIF_DIR}"
    exit 1
fi

echo "Node task ${SLURM_ARRAY_TASK_ID} — ${TOTAL} total watersheds"

# --- Launch this task's watersheds in parallel ---
START=$(( SLURM_ARRAY_TASK_ID * WATERSHEDS_PER_NODE ))
FINAL_OUTPUT_DIR="${REPO_ROOT}/GEE/TIF_Output/FinalOutput"
PIDS=()

for i in $(seq 0 $(( WATERSHEDS_PER_NODE - 1 ))); do
    IDX=$(( START + i ))
    if [ "$IDX" -ge "$TOTAL" ]; then
        break
    fi
    TIF="${ALL_TIFS[$IDX]}"
    TIF_STEM=$(basename "${TIF}" .tif)
    PROB_TIF="${FINAL_OUTPUT_DIR}/${TIF_STEM}_Probability.tif"
    if [ -f "$PROB_TIF" ]; then
        echo "  Skipping (already done): ${TIF_STEM}"
        continue
    fi
    echo "  Starting: ${TIF_STEM}"
    python "${REPO_ROOT}/run_pipeline.py" "$TIF" --cores "${CORES_PER_WATERSHED}" &
    PIDS+=($!)
done

# --- Wait for all watersheds on this node to finish ---
FAILED=0
for PID in "${PIDS[@]}"; do
    wait "$PID" || FAILED=$(( FAILED + 1 ))
done

if [ "$FAILED" -gt 0 ]; then
    echo "ERROR: ${FAILED} watershed(s) failed on task ${SLURM_ARRAY_TASK_ID}"
    exit 1
fi

echo "Task ${SLURM_ARRAY_TASK_ID} complete."
