#!/bin/bash
# =============================================================================
# Lost Meadows — Global Model Training + Prediction
#
# Trains a single XGBoost model on all 119 watershed CSVs combined,
# then predicts on all watersheds using the global model.
#
# Usage (from repo root):
#   sbatch SLURM/submit_global_model.slurm
# =============================================================================

#SBATCH --job-name=global_model
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=32
#SBATCH --mem=200G
#SBATCH --time=03:00:00
#SBATCH --partition=normal
#SBATCH --output=SLURM/logs/%j_global.out
#SBATCH --error=SLURM/logs/%j_global.err

CONDA_ENV=meadow
REPO_ROOT=$SLURM_SUBMIT_DIR
NCORES=32

source /home/lm1/miniconda3/etc/profile.d/conda.sh
conda activate "${CONDA_ENV}"
export LD_PRELOAD=$CONDA_PREFIX/lib/libstdc++.so.6
set -a && source "${REPO_ROOT}/.env" && set +a

echo "===== Global Model Training ====="
echo "REPO_ROOT: ${REPO_ROOT}"
echo "NCORES: ${NCORES}"
echo "Started: $(date)"

# Step 1: Train global model (gridsearch + training)
python "${REPO_ROOT}/GlobalModel/train_global_model.py" "${NCORES}"

if [ $? -ne 0 ]; then
    echo "ERROR: Training failed"
    exit 1
fi

echo ""
echo "===== Global Model Prediction ====="
echo "Started: $(date)"

# Step 2: Predict all watersheds with global model
python "${REPO_ROOT}/GlobalModel/predict_all_watersheds.py"

echo ""
echo "===== Complete ====="
echo "Finished: $(date)"
