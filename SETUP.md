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

## Step 2: Create Conda Environment

Create the environment with all required Python dependencies:

```bash
# Create environment from environment.yml
conda env create -f environment.yml

# Activate the environment
conda activate meadow
```

**What this installs:**
- Python 3.10
- GDAL, Rasterio, GeoPandas (geospatial tools)
- NumPy, SciPy, Pandas (scientific computing)
- Scikit-learn (machine learning)
- MPI4Py (parallel processing)

---

## Step 3: Install TauDEM

TauDEM is required for hydrological analysis.

**Option 1: Install via Conda (Recommended - Easiest)**

```bash
# Activate your environment
conda activate meadow

# Install TauDEM from conda-forge
conda install -c conda-forge taudem

# Verify installation
mpiexec -n 1 pitremove
```

**Option 2: Build from Source (If conda install fails)**

```bash
# Install build dependencies
sudo apt update
sudo apt install -y cmake g++ mpich libgdal-dev gdal-bin git

# Clone TauDEM repository
cd ~
git clone https://github.com/dtarb/TauDEM.git
cd TauDEM

# Build TauDEM
mkdir build
cd build
cmake ..
make -j$(nproc)  # Use all CPU cores for faster build

# Install system-wide
sudo make install

# Return to home directory
cd ~
```

**Verify TauDEM Installation:**

```bash
# Should show TauDEM version info
mpiexec -n 1 pitremove
```

If you see "PitRemove version 5.x.x", TauDEM is installed correctly!

**Note:** If using Option 2, building takes 5-10 minutes on most systems.

---

## Step 4: Get Wetland Geodatabase Files

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
conda activate meadow

# Test imports
python -c "
import rasterio
import geopandas
import sklearn
import numpy
import scipy
print('All Python packages installed successfully!')
"

# Test TauDEM
mpiexec -n 1 pitremove -h > /dev/null 2>&1 && echo "TauDEM installed successfully!"

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
conda activate meadow

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
│   └── Advanced/
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
    ├── train_random_forest.py
    └── predict_meadows.py
```

---

## Troubleshooting

### Issue: "conda: command not found"
- Install Miniconda following Step 0
- Restart your terminal after installation
- Make sure you ran `source ~/.bashrc` after installation

### Issue: "TauDEM not found"
- Make sure MPI is installed: `mpiexec --version`
- Reinstall TauDEM: `sudo apt install -y taudem`

### Issue: "GDAL ERROR: ..."
- Ensure GDAL is installed: `gdalinfo --version`
- Recreate conda environment: `conda env remove -n meadow && conda env create -f environment.yml`

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

# 2. Create environment (once)
conda env create -f environment.yml

# 3. Activate environment (every session)
conda activate meadow

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
