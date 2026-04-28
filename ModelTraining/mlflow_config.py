#!/usr/bin/env python3
"""
Shared MLflow / DagsHub configuration for all training scripts.

Authentication
--------------
Set DAGSHUB_USER_TOKEN in your environment before running any training script:

    export DAGSHUB_USER_TOKEN=your_token_here

Or add it to a .env file at the repo root (never commit .env):

    echo "DAGSHUB_USER_TOKEN=your_token_here" > .env
    source .env          # bash/zsh
    # or: set -a && source .env && set +a

If the variable is not set, dagshub falls back to interactive browser login.
"""

import os
import mlflow
import dagshub

DAGSHUB_REPO_OWNER = "Laurlov413"
DAGSHUB_REPO_NAME  = "Lost-Meadows"


def init_mlflow(experiment_name: str) -> None:
    """Initialise MLflow tracking.

    Uses local tracking when running inside a SLURM job to avoid rate-limiting
    DagsHub with hundreds of concurrent API calls. Uses DagsHub remote tracking
    for local/interactive runs.
    """
    if os.environ.get("SLURM_JOB_ID"):
        print("SLURM environment detected — using local MLflow tracking.")
        mlflow.set_tracking_uri("mlruns")
        mlflow.set_experiment(experiment_name)
        return

    token = os.environ.get("DAGSHUB_USER_TOKEN")
    if token:
        os.environ["MLFLOW_TRACKING_USERNAME"] = DAGSHUB_REPO_OWNER
        os.environ["MLFLOW_TRACKING_PASSWORD"] = token

    try:
        dagshub.init(
            repo_owner=DAGSHUB_REPO_OWNER,
            repo_name=DAGSHUB_REPO_NAME,
            mlflow=True,
        )
        mlflow.set_experiment(experiment_name)
    except Exception as e:
        print(f"WARNING: DagsHub unavailable ({e}), falling back to local MLflow tracking.")
        mlflow.set_tracking_uri("mlruns")
        mlflow.set_experiment(experiment_name)
