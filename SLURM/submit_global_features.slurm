#!/bin/bash
# =============================================================================
# Lost Meadows — Global Model Feature Preparation (Array Job)
#
# Generates features_stacked.tif + training_data_real.csv for all 119
# watersheds across 8 nodes. Run this before submit_global_model.slurm.
#
# Usage (from repo root):
#   sbatch SLURM/submit_global_features.slurm
#
# Or chain with global model job automatically:
#   JOB=$(sbatch --parsable SLURM/submit_global_features.slurm)
#   sbatch --dependency=afterok:$JOB SLURM/submit_global_model.slurm
# =============================================================================

#SBATCH --job-name=global_features
#SBATCH --array=0-7%25
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=64
#SBATCH --mem=200G
#SBATCH --time=02:00:00
#SBATCH --partition=normal
#SBATCH --output=SLURM/logs/%A_%a_features.out
#SBATCH --error=SLURM/logs/%A_%a_features.err

WATERSHEDS_PER_NODE=16
CORES_PER_WATERSHED=4
CONDA_ENV=meadow
REPO_ROOT=$SLURM_SUBMIT_DIR
TIF_DIR="${REPO_ROOT}/GEE/TIF_Input"

source /home/lm1/miniconda3/etc/profile.d/conda.sh
conda activate "${CONDA_ENV}"
export LD_PRELOAD=$CONDA_PREFIX/lib/libstdc++.so.6
set -a && source "${REPO_ROOT}/.env" && set +a

mapfile -t ALL_TIFS < <(ls "${TIF_DIR}"/*.tif 2>/dev/null | grep -v '_fixed\.tif' | sort)
TOTAL=${#ALL_TIFS[@]}

if [ "$TOTAL" -eq 0 ]; then
    echo "ERROR: No .tif files found in ${TIF_DIR}"
    exit 1
fi

echo "Node task ${SLURM_ARRAY_TASK_ID} — ${TOTAL} total watersheds"

START=$(( SLURM_ARRAY_TASK_ID * WATERSHEDS_PER_NODE ))
PIDS=()

for i in $(seq 0 $(( WATERSHEDS_PER_NODE - 1 ))); do
    IDX=$(( START + i ))
    if [ "$IDX" -ge "$TOTAL" ]; then
        break
    fi
    TIF="${ALL_TIFS[$IDX]}"
    TIF_STEM=$(basename "${TIF}" .tif)
    FEATURES_TIF="${REPO_ROOT}/GEE/TIF_Output/${TIF_STEM}/features_stacked.tif"

    if [ -f "$FEATURES_TIF" ]; then
        echo "  Skipping (already done): ${TIF_STEM}"
        continue
    fi

    echo "  Starting: ${TIF_STEM}"
    python "${REPO_ROOT}/run_pipeline.py" "$TIF" --cores "${CORES_PER_WATERSHED}" --prepare-only &
    PIDS+=($!)
done

FAILED=0
for PID in "${PIDS[@]}"; do
    wait "$PID" || FAILED=$(( FAILED + 1 ))
done

if [ "$FAILED" -gt 0 ]; then
    echo "ERROR: ${FAILED} watershed(s) failed on task ${SLURM_ARRAY_TASK_ID}"
    exit 1
fi

echo "Task ${SLURM_ARRAY_TASK_ID} complete."
