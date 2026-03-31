# Lost Meadows Detection — Setup Guide

Complete installation and data setup guide for the Lost Meadows detection pipeline on Linux/Ubuntu or WSL2.

---

## Prerequisites

- **Operating System**: Linux (Ubuntu 20.04+) or WSL2 (Windows Subsystem for Linux)
- **Conda/Miniconda**: Required for environment management
- **Git**: For cloning the repository
- **Disk Space**: ~15 GB (dependencies + data + per-watershed outputs)

---

## Step 0: Install Miniconda (If Not Already Installed)

```bash
# Download installer
wget https://repo.anaconda.com/miniconda/Miniconda3-latest-Linux-x86_64.sh

# Run installer
bash Miniconda3-latest-Linux-x86_64.sh

# Follow the prompts — accept license, confirm install location,
# and type "yes" when asked to initialize conda

# Reload shell
source ~/.bashrc

# Verify
conda --version
```

---

## Step 1: Clone the Repository

```bash
git clone https://github.com/RaiderSoft/Lost-Meadows.git
cd Lost-Meadows
```

---

## Step 2: Create the Conda Environment

The repository includes `environment.yml` which specifies every dependency including TauDEM, all Python packages, mlflow, and dagshub. This is the recommended way to set up the environment:

```bash
conda env create -f environment.yml
conda activate meadow
```

**Verify TauDEM is working:**

```bash
pitremove
```

You should see TauDEM output. If it says "command not found", make sure you are in the `meadow` environment.

<details>
<summary>Manual install (if environment.yml fails)</summary>

```bash
conda install -c conda-forge mamba -y

conda create -n meadow -c conda-forge taudem python=3.11 -y
conda activate meadow

mamba install -c conda-forge rasterio numpy scipy pandas scikit-learn geopandas xgboost -y
pip install mlflow dagshub
```

</details>

---

## Step 3: Download Required Data Files

All data is provided as GitHub Releases at:
**https://github.com/RaiderSoft/Lost-Meadows/releases**

There are three releases to download. Follow the instructions for each below.

---

### Release 1: TIFInputFiles (Soil Data)

This release contains the three soil TIF files required by the pipeline.

1. Download the **TIFInputFiles** release asset.
2. Extract the files into `GEE/TIF_Input/Soil/`:

```
GEE/TIF_Input/Soil/
├── depth_to_restrictive_layer.tif
├── hydraulic_connectivity.tif
└── organic_matter_pct.tif
```

These files are already in `.gitignore` — they will not be committed.

---

### Release 2: WetlandGeodatabases (Training Labels)

This release contains the Oregon and California wetland geodatabases used to generate training labels. Each is a zipped `.gdb` folder.

1. Download both zip files from the **WetlandGeodatabases** release.
2. Unzip each one — you will get a folder ending in `.gdb`.
3. Place both unzipped folders inside the `Wetlands/` directory:

```
Wetlands/
├── prepare_training_data.py
├── OR_geodatabase_wetlands.gdb/
└── CA_geodatabase_wetlands.gdb/
```

These folders are already in `.gitignore` (~2.4 GB total) — they will not be committed.

---

### Release 3: GEEInputFiles (Watershed DEMs)

This release contains all 122 watershed DEM rasters exported from Google Earth Engine, split across two zip files due to file size.

1. Download both zip files from the **GEEInputFiles** release.
2. Unzip both archives.
3. Find the specific watershed `.tif` file you want to process.
4. Place that file into `GEE/TIF_Input/`:

```
GEE/TIF_Input/
├── Hunter_Creek_1710031205.tif      ← example watershed
├── Bear_Creek_1710030801.tif        ← another watershed
└── Soil/
    ├── depth_to_restrictive_layer.tif
    ├── hydraulic_connectivity.tif
    └── organic_matter_pct.tif
```

You only need to place the watersheds you intend to process — you do not need all 122 at once. All `.tif` files in `GEE/TIF_Input/` are already in `.gitignore`.

---

## Step 4: Configure DagsHub Experiment Tracking

MLflow experiment data is stored remotely on DagsHub. The shared config lives in `ModelTraining/mlflow_config.py` and is used automatically by both training scripts.

1. Create a free account at [dagshub.com](https://dagshub.com) and create a repo named `Lost-Meadows`.
2. Open `ModelTraining/mlflow_config.py` and set your DagsHub username:
   ```python
   DAGSHUB_REPO_OWNER = "your-dagshub-username"
   ```
3. Generate a DagsHub access token: **Settings → Tokens** on DagsHub.
4. Copy `.env.example` to `.env` (never commit this file) and paste your token:
   ```bash
   cp .env.example .env
   # Edit .env and replace the placeholder with your actual token
   ```
5. Load the token before running any training script:
   ```bash
   set -a && source .env && set +a
   ```

After training, runs will appear under the **Experiments** tab of your DagsHub repo.

---

## Step 5: Verify Installation

Run these checks to confirm everything is set up before starting the pipeline:

```bash
cd ~/path/to/Lost-Meadows
conda activate meadow

# Test Python packages
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

# Check for wetland geodatabases
if [ -d "Wetlands/OR_geodatabase_wetlands.gdb" ]; then
    echo "Oregon wetland data found!"
else
    echo "WARNING: Oregon wetland data missing — download from WetlandGeodatabases release"
fi

if [ -d "Wetlands/CA_geodatabase_wetlands.gdb" ]; then
    echo "California wetland data found!"
else
    echo "WARNING: California wetland data missing — download from WetlandGeodatabases release"
fi

# Check for soil data
if [ -f "GEE/TIF_Input/Soil/depth_to_restrictive_layer.tif" ] && \
   [ -f "GEE/TIF_Input/Soil/hydraulic_connectivity.tif" ] && \
   [ -f "GEE/TIF_Input/Soil/organic_matter_pct.tif" ]; then
    echo "Soil TIF files found!"
else
    echo "WARNING: Soil TIF files missing — download from TIFInputFiles release"
fi

# Check for at least one watershed DEM
if ls GEE/TIF_Input/*.tif 1> /dev/null 2>&1; then
    echo "Watershed DEM(s) found:"
    ls GEE/TIF_Input/*.tif
else
    echo "WARNING: No watershed DEMs found — download from GEEInputFiles release"
fi
```

---

## Step 6: Run the Pipeline

```bash
cd ~/path/to/Lost-Meadows
conda activate meadow

# Load DagsHub token
set -a && source .env && set +a

# Run the full pipeline on a watershed (~2-4 hours)
python run_pipeline.py GEE/TIF_Input/Hunter_Creek_1710031205.tif
```

The script will prompt you to press Enter before starting. You can watch each step's progress in real time.

**Outputs** are written to `GEE/TIF_Output/<watershed_name>/`, including:
- All 23 individual feature rasters
- `features_stacked.tif` (23-band multi-band raster)
- `training_data_real.csv`
- `xgboost_model.pkl`
- `<watershed>_meadow_probability.tif` — the final output

---

## Directory Structure After Full Setup

```
Lost-Meadows/
├── run_pipeline.py
├── environment.yml
├── SETUP.md
├── .env                         # Your DagsHub token (never committed)
├── .gitignore
│
├── GEE/
│   ├── LostMeadowsApplication.js
│   ├── TIF_Export.js
│   ├── MeadowVisualization.js
│   ├── TIF_Input/               # Watershed DEMs go here
│   │   ├── Hunter_Creek_1710031205.tif
│   │   └── Soil/                # Soil TIFs go here
│   │       ├── depth_to_restrictive_layer.tif
│   │       ├── hydraulic_connectivity.tif
│   │       └── organic_matter_pct.tif
│   └── TIF_Output/              # Created automatically during pipeline run
│       └── Hunter_Creek_1710031205/
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
│   ├── OR_geodatabase_wetlands.gdb/   # From WetlandGeodatabases release
│   └── CA_geodatabase_wetlands.gdb/   # From WetlandGeodatabases release
│
└── ModelTraining/
    ├── train_xgboost.py               # Primary model (used in pipeline)
    ├── predict_meadows.py
    ├── mlflow_config.py
    ├── train_random_forest.py         # Comparison only — not in pipeline
    └── xgboost_gridsearch.py          # Tuning utility — not in pipeline
```

---

## Quick Start Cheat Sheet

```bash
# One-time setup
conda env create -f environment.yml
conda activate meadow

# Every session
conda activate meadow
set -a && source .env && set +a

# Run pipeline
python run_pipeline.py GEE/TIF_Input/your_watershed.tif

# Deactivate when done
conda deactivate
```

---

## Troubleshooting

### "conda: command not found"
- Install Miniconda following Step 0 and restart your terminal.

### "TauDEM not found" / "pitremove: command not found"
- Make sure you activated the correct environment: `conda activate meadow`
- Verify: `pitremove`

### "GDAL ERROR: ..."
- Confirm you are in the correct environment: `conda activate meadow`
- Reinstall: `mamba install -c conda-forge rasterio gdal -y`

### "No wetland data found" / geodatabase errors
- Download from the **WetlandGeodatabases** release and unzip into `Wetlands/`
- Verify: `ls -la Wetlands/*.gdb`

### "Soil input directory not found"
- Download from the **TIFInputFiles** release and place files in `GEE/TIF_Input/Soil/`

### Pipeline runs but no output
- Check disk space: `df -h`
- Verify the watershed DEM exists: `ls -lh GEE/TIF_Input/`
- Scroll up in the terminal for the failed step's error output

---

## Using WSL2 on Windows

If you are on Windows, use WSL2 (Windows Subsystem for Linux):

1. **Enable WSL2** (PowerShell as Administrator):
   ```powershell
   wsl --install
   # Restart your computer
   ```

2. **Install Ubuntu**:
   ```powershell
   wsl --install -d Ubuntu-22.04
   ```

3. **Set up Ubuntu** (opens automatically):
   ```bash
   sudo apt update && sudo apt upgrade -y
   ```

4. Follow all steps above starting from Step 0.

**Accessing Windows files from WSL:**
```bash
# Windows C: drive
cd /mnt/c/Users/YourName/Documents
```

**Accessing WSL files from Windows Explorer:**
```
\\wsl$\Ubuntu-22.04\home\username\
```

---

## Additional Resources

- **Paper**: Cummings et al. (2023), *"Resetting the baseline: using machine learning to find lost meadows"*
- **TauDEM Documentation**: https://hydrology.usu.edu/taudem/taudem5/
- **Rasterio Docs**: https://rasterio.readthedocs.io/
- **Miniconda**: https://docs.conda.io/en/latest/miniconda.html

---

## Getting Help

If you encounter issues:

1. Check the Troubleshooting section above
2. Search existing [GitHub Issues](https://github.com/RaiderSoft/Lost-Meadows/issues)
3. Open a new issue with your OS, full error message, and steps to reproduce
