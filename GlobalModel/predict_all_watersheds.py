#!/usr/bin/env python3
"""
Run the global XGBoost model on all 119 watersheds and save probability TIFs.

Outputs go to GEE/TIF_Output/FinalOutputGlobal/ (separate from local model outputs).

Usage (from repo root):
  python GlobalModel/predict_all_watersheds.py
"""

import sys
from pathlib import Path

# Allow importing from ModelTraining/
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "ModelTraining"))
from predict_meadows import predict_probabilities


def get_repo_root():
    return Path(__file__).resolve().parents[1]


def main():
    repo_root = get_repo_root()
    tif_input_dir = repo_root / "GEE" / "TIF_Input"
    tif_output_dir = repo_root / "GEE" / "TIF_Output"
    output_dir = tif_output_dir / "FinalOutputGlobal"
    model_path = repo_root / "GlobalModel" / "global_xgboost_model.pkl"

    if not model_path.exists():
        print(f"ERROR: Global model not found at {model_path}")
        print("Run GlobalModel/train_global_model.py first.")
        sys.exit(1)

    output_dir.mkdir(exist_ok=True)

    tif_files = sorted(tif_input_dir.glob("*.tif"))
    tif_files = [t for t in tif_files if not t.name.endswith("_fixed.tif")]
    print(f"Found {len(tif_files)} watersheds to predict")

    failed = []
    for i, tif in enumerate(tif_files, 1):
        watershed = tif.stem
        features_path = tif_output_dir / watershed / "features_stacked.tif"
        prob_tif = output_dir / f"{watershed}_Probability.tif"

        if prob_tif.exists():
            print(f"[{i}/{len(tif_files)}] Skipping (already done): {watershed}")
            continue

        if not features_path.exists():
            print(f"[{i}/{len(tif_files)}] Skipping (no features_stacked.tif): {watershed}")
            failed.append(watershed)
            continue

        print(f"\n[{i}/{len(tif_files)}] Predicting: {watershed}")
        try:
            predict_probabilities(
                str(features_path),
                str(model_path),
                str(prob_tif),
                chunk_size=500
            )
        except Exception as e:
            print(f"  ERROR: {watershed} failed — {e}")
            failed.append(watershed)

    print(f"\n{'='*60}")
    print(f"Done! {len(tif_files) - len(failed)}/{len(tif_files)} succeeded")
    if failed:
        print(f"Failed: {', '.join(failed)}")
    print(f"Outputs in: {output_dir}")


if __name__ == "__main__":
    main()
