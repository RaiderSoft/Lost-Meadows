# Lost Meadows Detection - Setup Guide

Complete installation guide for setting up the Lost Meadows detection pipeline on Linux/Ubuntu systems.

## Prerequisites

- **Operating System**: Linux (Ubuntu 20.04+) or WSL2 (Windows Subsystem for Linux)
- **Conda/Miniconda**: Required for Python environment management
- **Git**: For cloning the repository
- **Disk Space**: ~10 GB for dependencies and data

---

## Step 0: Install Miniconda (If Not Already Installed)

Miniconda is a minimal installer for conda. If you don't have conda installed:

```bash
# Download Miniconda installer
wget https://repo.anaconda.com/miniconda/Miniconda3-latest-Linux-x86_64.sh

# Run the installer
bash Miniconda3-latest-Linux-x86_64.sh

# Follow the prompts:
# - Press Enter to review license
# - Type "yes" to accept
# - Press Enter to confirm installation location
# - Type "yes" when asked to initialize conda

# Reload your shell configuration
source ~/.bashrc

# Verify installation
conda --version
```

If conda is installed, you should see output like: `conda 24.1.2`

---

## Step 1: Clone Repository

```bash
git clone https://github.com/your-username/Lost-Meadows.git
cd Lost-Meadows
```

---

## Step 2: Create Conda Environment with TauDEM

The entire pipeline runs from a single conda environment with Python 3.11 and TauDEM.

First, install mamba for faster dependency solving:

```bash
conda install -c conda-forge mamba -y
```

Then create the environment with TauDEM included:

```bash
conda create -n meadow -c conda-forge taudem python=3.11 -y
conda activate meadow
```

Then install the remaining Python packages:

```bash
mamba install -c conda-forge rasterio numpy scipy pandas scikit-learn geopandas xgboost mlflow -y
pip install dagshub
```

**Verify TauDEM installation:**

```bash
pitremove
```

If you see TauDEM output, the installation is working correctly.

---

## Step 4: Configure DagsHub Experiment Tracking

MLflow run data is stored remotely on DagsHub. The shared config lives in
`ModelTraining/mlflow_config.py` — both `train_random_forest.py` and
`train_xgboost.py` pull from it automatically.

1. Create a free account at [dagshub.com](https://dagshub.com) and create a repo named `Lost-Meadows`.
2. Open `ModelTraining/mlflow_config.py` and set your username:
   ```python
   DAGSHUB_REPO_OWNER = "your-dagshub-username"
   ```
3. Generate a DagsHub access token: **Settings → Tokens** on DagsHub.
4. Copy `.env.example` to `.env` (never commit this file) and paste your token:
   ```bash
   cp .env.example .env
   # Edit .env and replace the placeholder with your real token
   ```
5. Load the token into your shell before running any training script:
   ```bash
   source .env
   ```
   Or export it directly for a single session:
   ```bash
   export DAGSHUB_USER_TOKEN=your_token_here
   ```

After training, runs will appear under the **Experiments** tab of your DagsHub repo.

---

## Step 5: Get Wetland Geodatabase Files

**Required for training data:**

1. **Oregon Wetlands**: Download from [FWS](https://www.fws.gov/program/national-wetlands-inventory/download-state-wetlands-data)
2. **California Wetlands**: Download from [FWS](https://www.fws.gov/program/national-wetlands-inventory/download-state-wetlands-data)

Place the `.gdb` folders in the `Wetlands/` directory:
```
Lost-Meadows/
  └── Wetlands/
      ├── OR_geodatabase_wetlands.gdb/
      └── CA_geodatabase_wetlands.gdb/
```

**File sizes**: ~2.4 GB total (already in .gitignore)

---

## Step 6: Verify Installation

Run this test script to verify everything is set up correctly:

```bash
cd ~/Capstone/Lost-Meadows

# Activate environment
conda activate taudem_env

# Test imports
python -c "
import rasterio
import geopandas
import sklearn
import numpy
import scipy
import mlflow
import dagshub
print('All Python packages installed successfully!')
"

# Test TauDEM
pitremove && echo "TauDEM installed successfully!"

# Check for wetland data
if [ -d "Wetlands/OR_geodatabase_wetlands.gdb" ]; then
    echo "Oregon wetland data found!"
else
    echo "WARNING: Oregon wetland data missing - download required"
fi

if [ -d "Wetlands/CA_geodatabase_wetlands.gdb" ]; then
    echo "California wetland data found!"
else
    echo "WARNING: California wetland data missing - download required"
fi
```

---

## Step 7: Run Your First Pipeline

```bash
# Make sure you're in the correct directory
cd ~/Capstone/Lost-Meadows

# Activate environment
conda activate taudem_env

# Load DagsHub token
set -a && source .env && set +a

# Run the full pipeline on a test watershed
python run_pipeline.py GEE/TIF_Input/Hunter_Creek_1710031205.tif
```

This will take ~1-2 hours and generate meadow probability maps!

---

## Directory Structure After Setup

```
Lost-Meadows/
├── environment.yml              # Conda environment file
├── SETUP.md                     # This file
├── run_pipeline.py              # Master pipeline script
├── .gitignore                   # Excludes large files
│
├── GEE/
│   ├── TIF_Input/              # Put your DEM files here
│   │   ├── Precip/             # Regional precipitation TIF files
│   │   └── Soil/               # Soil TIF files (depth, hydraulic, organic matter)
│   ├── TIF_Output/             # Output folders created here
│   ├── TIF_Export.js           # GEE script for DEM export
│   └── MeadowVisualization.js  # GEE visualization
│
├── TauDEM/
│   └── run_taudem_workflow.py
│
├── FeatureEngineering/
│   ├── TWI/
│   ├── Terrain/
│   ├── Advanced/
│   └── Soil/
│
├── FeatureStacking/
│   └── stack_features.py
│
├── Wetlands/
│   ├── prepare_training_data.py
│   ├── OR_geodatabase_wetlands.gdb/  # Download these!
│   └── CA_geodatabase_wetlands.gdb/  # Download these!
│
└── ModelTraining/
    ├── train_xgboost.py
    └── predict_meadows.py
```

---

## Troubleshooting

### Issue: "conda: command not found"
- Install Miniconda following Step 0
- Restart your terminal after installation
- Make sure you ran `source ~/.bashrc` after installation

### Issue: "TauDEM not found"
- Make sure you are in the `taudem_env` environment: `conda activate taudem_env`
- Verify with: `pitremove`

### Issue: "GDAL ERROR: ..."
- Ensure you are in the correct environment: `conda activate taudem_env`
- Reinstall: `mamba install -c conda-forge rasterio gdal -y`

### Issue: "No wetland data found"
- Download the geodatabase files (Step 4)
- Place them in `Wetlands/` directory
- Verify with: `ls -la Wetlands/*.gdb`

### Issue: Pipeline runs but no output
- Check disk space: `df -h`
- Verify input DEM exists: `ls -lh GEE/TIF_Input/`
- Check logs for errors

---

## Using WSL2 on Windows

If you're on Windows, we recommend using WSL2 (Windows Subsystem for Linux):

**Setup WSL2:**

1. **Enable WSL2** (PowerShell as Administrator):
   ```powershell
   wsl --install
   # Restart computer
   ```

2. **Install Ubuntu**:
   ```powershell
   wsl --install -d Ubuntu-22.04
   ```

3. **Set up Ubuntu** (opens automatically):
   ```bash
   # Create username and password
   # Update packages
   sudo apt update && sudo apt upgrade -y
   ```

4. **Follow all setup steps above** starting from Step 0!

**Accessing Windows files from WSL:**
```bash
# Windows C: drive is at /mnt/c/
cd /mnt/c/Users/YourName/Documents
```

**Accessing WSL files from Windows:**
- In File Explorer: `\\wsl$\Ubuntu-22.04\home\username\`

---

## Quick Start Cheat Sheet

```bash
# 1. Install Miniconda (if needed - once only)
wget https://repo.anaconda.com/miniconda/Miniconda3-latest-Linux-x86_64.sh
bash Miniconda3-latest-Linux-x86_64.sh
source ~/.bashrc

# 2. Install mamba and create environment (once)
conda install -c conda-forge mamba -y
conda create -n taudem_env -c conda-forge taudem python=3.11 -y
conda activate taudem_env
mamba install -c conda-forge rasterio numpy scipy pandas scikit-learn geopandas xgboost mlflow -y
pip install dagshub

# 3. Activate environment (every session)
conda activate taudem_env
set -a && source .env && set +a

# 4. Run pipeline
python run_pipeline.py GEE/TIF_Input/your_watershed.tif

# 5. Deactivate when done
conda deactivate
```

---

## Additional Resources

- **Paper**: "Resetting the baseline: using machine learning to find lost meadows" (Cummings et al., 2023)
- **TauDEM Documentation**: https://hydrology.usu.edu/taudem/taudem5/
- **Rasterio Docs**: https://rasterio.readthedocs.io/
- **Scikit-learn Docs**: https://scikit-learn.org/
- **Miniconda Installation**: https://docs.conda.io/en/latest/miniconda.html

---

## Getting Help

If you encounter issues:

1. Check this SETUP.md file first
2. Search existing GitHub issues
3. Create a new issue with:
   - Your OS and version
   - Full error message
   - Steps to reproduce

---

## You're Ready!

Once all checks pass, you're ready to detect lost meadows!

Next: See `README.md` for usage instructions and examples.
