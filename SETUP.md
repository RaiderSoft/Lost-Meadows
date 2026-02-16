# Lost Meadows Detection - Setup Guide

Complete installation guide for setting up the Lost Meadows detection pipeline.

## 🎯 Prerequisites

- **Operating System**:
  - ✅ Linux (Ubuntu 20.04+)
  - ✅ macOS (10.15+)
  - ✅ **Windows 10/11** (via WSL2 - **Recommended**)
  - ⚠️ Windows (native PowerShell - **Advanced**, see notes below)
- **Conda/Miniconda**: [Install here](https://docs.conda.io/en/latest/miniconda.html)
- **Git**: For cloning the repository
- **Disk Space**: ~10 GB for dependencies and data

### 🪟 Windows Users - Important!

**We STRONGLY recommend using WSL2 (Windows Subsystem for Linux)** instead of native Windows:

**Why WSL2?**
- ✅ TauDEM works out-of-the-box (harder on Windows)
- ✅ GDAL/geospatial tools install easily
- ✅ Faster processing
- ✅ Better compatibility

**Native Windows PowerShell:**
- ⚠️ TauDEM is difficult to install (needs manual build)
- ⚠️ Path issues (backslashes vs forward slashes)
- ⚠️ Some scripts may need modification
- Only use if you're experienced with Windows development

**➡️ See [Windows Setup Options](#windows-setup-options) below for details**

---

## 📦 Step 1: Clone Repository

### Linux / macOS / WSL2
```bash
git clone https://github.com/your-username/Lost-Meadows.git
cd Lost-Meadows
```

### Windows PowerShell (Native)
```powershell
git clone https://github.com/your-username/Lost-Meadows.git
cd Lost-Meadows
```

---

## 🐍 Step 2: Create Conda Environment

The easiest way to set up all Python dependencies:

### Linux / macOS / WSL2
```bash
# Create environment from environment.yml
conda env create -f environment.yml

# Activate the environment
conda activate meadow
```

### Windows PowerShell (Native)
```powershell
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

**Note**: On Windows, conda may have issues with some packages. If so, see [Windows Troubleshooting](#windows-troubleshooting)

---

## ⚡ Step 3: Install TauDEM

TauDEM is required for hydrological analysis. Installation varies by OS:

### **Ubuntu/WSL2** (Recommended for Windows users)

```bash
# Update package list
sudo apt update

# Install dependencies
sudo apt install -y mpich libgdal-dev gdal-bin

# Install TauDEM
sudo apt install -y taudem
```

### **macOS** (Using Homebrew)

```bash
# Install GDAL and MPI
brew install gdal open-mpi

# Clone and build TauDEM
git clone https://github.com/dtarb/TauDEM.git
cd TauDEM
mkdir build
cd build
cmake ..
make
sudo make install
```

### **Windows (Native PowerShell)** ⚠️ Advanced

**Option 1: Use WSL2 instead (STRONGLY RECOMMENDED)**
- Follow WSL2 instructions above
- Much easier!

**Option 2: Build from source (Advanced)**

1. **Install Microsoft MPI**:
   - Download MS-MPI from [Microsoft](https://learn.microsoft.com/en-us/message-passing-interface/microsoft-mpi)
   - Install both `msmpisetup.exe` and `msmpisdk.msi`

2. **Install OSGeo4W** (for GDAL):
   ```powershell
   # Download from https://trac.osgeo.org/osgeo4w/
   # Run installer and select GDAL
   ```

3. **Install CMake**:
   ```powershell
   # Download from https://cmake.org/download/
   # Add to PATH during installation
   ```

4. **Build TauDEM** (requires Visual Studio):
   ```powershell
   git clone https://github.com/dtarb/TauDEM.git
   cd TauDEM
   mkdir build
   cd build
   cmake .. -G "Visual Studio 17 2022"
   cmake --build . --config Release
   ```

5. **Add to PATH**:
   ```powershell
   # Add TauDEM\build\Release to System PATH
   ```

**This is complex!** Consider using WSL2 instead for a much smoother experience.

### **Verify TauDEM Installation**

#### Linux / macOS / WSL2
```bash
# Should show TauDEM help
mpiexec -n 1 pitremove -h
```

#### Windows PowerShell
```powershell
# Should show TauDEM help
mpiexec -n 1 pitremove.exe -h
```

If successful, you should see TauDEM's help message!

---

## 🗺️ Step 4: Get Wetland Geodatabase Files

**Required for training data:**

1. **Oregon Wetlands**: Download from [Oregon Geospatial Data Clearinghouse](https://spatialdata.oregonexplorer.info/)
2. **California Wetlands**: Download from [CA Open Data Portal](https://data.ca.gov/)

Place the `.gdb` folders in the `Wetlands/` directory:
```
Lost-Meadows/
  └── Wetlands/
      ├── OR_geodatabase_wetlands.gdb/
      └── CA_geodatabase_wetlands.gdb/
```

**File sizes**: ~2.4 GB total (already in .gitignore)

---

## 🌍 Step 5: Set Up Google Earth Engine (Optional)

Only needed if you want to export DEM data yourself:

### All Platforms
```bash
# Install Earth Engine API
pip install earthengine-api

# Authenticate (opens browser)
earthengine authenticate

# Initialize
python -c "import ee; ee.Initialize()"
```

**Note**: Pre-processed DEMs are included, so this is optional!

---

## ✅ Step 6: Verify Installation

Run this test script to verify everything is set up correctly:

### Linux / macOS / WSL2
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
print('✅ All Python packages installed successfully!')
"

# Test TauDEM
mpiexec -n 1 pitremove -h > /dev/null 2>&1 && echo "✅ TauDEM installed successfully!"

# Check for wetland data
if [ -d "Wetlands/OR_geodatabase_wetlands.gdb" ]; then
    echo "✅ Oregon wetland data found!"
else
    echo "⚠️  Oregon wetland data missing - download required"
fi

if [ -d "Wetlands/CA_geodatabase_wetlands.gdb" ]; then
    echo "✅ California wetland data found!"
else
    echo "⚠️  California wetland data missing - download required"
fi
```

### Windows PowerShell
```powershell
cd ~\Capstone\Lost-Meadows

# Activate environment
conda activate meadow

# Test imports
python -c "import rasterio; import geopandas; import sklearn; import numpy; import scipy; print('✅ All Python packages installed successfully!')"

# Test TauDEM (if installed)
mpiexec -n 1 pitremove.exe -h 2>$null
if ($?) { Write-Host "✅ TauDEM installed successfully!" }

# Check for wetland data
if (Test-Path "Wetlands\OR_geodatabase_wetlands.gdb") {
    Write-Host "✅ Oregon wetland data found!"
} else {
    Write-Host "⚠️  Oregon wetland data missing - download required"
}

if (Test-Path "Wetlands\CA_geodatabase_wetlands.gdb") {
    Write-Host "✅ California wetland data found!"
} else {
    Write-Host "⚠️  California wetland data missing - download required"
}
```

---

## 🚀 Step 7: Run Your First Pipeline

### Linux / macOS / WSL2
```bash
# Make sure you're in the correct directory
cd ~/Capstone/Lost-Meadows

# Activate environment
conda activate meadow

# Run the full pipeline on a test watershed
python run_pipeline.py GEE/TIF_Input/Hunter_Creek_1710031205.tif
```

### Windows PowerShell (if using native Windows)
```powershell
# Make sure you're in the correct directory
cd ~\Capstone\Lost-Meadows

# Activate environment
conda activate meadow

# Run the full pipeline on a test watershed
python run_pipeline.py GEE\TIF_Input\Hunter_Creek_1710031205.tif
```

This will take ~2-4 hours and generate meadow probability maps!

---

## 📁 Directory Structure After Setup

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
│   └── Terrain/
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

## 🐛 Troubleshooting

### **Issue: "conda: command not found"**
- Install Miniconda: https://docs.conda.io/en/latest/miniconda.html
- Restart your terminal

### **Issue: "TauDEM not found"**
- Make sure MPI is installed: `mpiexec --version`
- Reinstall TauDEM following Step 3

### **Issue: "GDAL ERROR: ..."**
- Ensure GDAL is installed: `gdalinfo --version`
- Recreate conda environment: `conda env remove -n meadow && conda env create -f environment.yml`

### **Issue: "No wetland data found"**
- Download the geodatabase files (Step 4)
- Place them in `Wetlands/` directory
- Verify with: `ls -la Wetlands/*.gdb`

### **Issue: Pipeline runs but no output**
- Check disk space: `df -h` (Linux/macOS) or `Get-PSDrive` (PowerShell)
- Verify input DEM exists: `ls -lh GEE/TIF_Input/` (Linux/macOS) or `dir GEE\TIF_Input\` (PowerShell)
- Check logs for errors

---

## 🪟 Windows Setup Options

### Option 1: WSL2 (Recommended) ⭐

**Advantages:**
- ✅ Easy TauDEM installation
- ✅ All Linux instructions work perfectly
- ✅ Better performance
- ✅ No path issues

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

4. **Install Miniconda in WSL**:
   ```bash
   wget https://repo.anaconda.com/miniconda/Miniconda3-latest-Linux-x86_64.sh
   bash Miniconda3-latest-Linux-x86_64.sh
   source ~/.bashrc
   ```

5. **Follow Linux instructions** from Step 1!

**Accessing Windows files from WSL:**
```bash
# Windows C: drive is at /mnt/c/
cd /mnt/c/Users/YourName/Documents
```

**Accessing WSL files from Windows:**
- In File Explorer: `\\wsl$\Ubuntu-22.04\home\username\`

### Option 2: Native Windows PowerShell (Advanced) ⚠️

**Only if you really can't use WSL2!**

**Known Issues:**
- TauDEM requires manual compilation (complex)
- GDAL/Rasterio can be finicky
- Path separators (\ vs /) may cause issues
- Some MPI operations slower

**Workarounds:**
1. Use pre-built TauDEM Windows binaries (if available)
2. Or skip TauDEM and use pre-computed features
3. Modify scripts to handle Windows paths:
   ```python
   from pathlib import Path
   # Use Path objects for cross-platform compatibility
   ```

---

## 🐛 Windows-Specific Troubleshooting

### **Issue: "conda activate meadow" doesn't work**
```powershell
# Initialize conda for PowerShell
conda init powershell
# Close and reopen PowerShell
```

### **Issue: "GDAL not found" on Windows**
```powershell
# Try installing from conda-forge specifically
conda install -c conda-forge gdal rasterio
```

### **Issue: "Import Error: DLL load failed"**
- GDAL/Rasterio DLL issues on Windows
- Solution: Use WSL2 instead (seriously!)
- Or: Install OSGeo4W and set environment variables

### **Issue: Path errors (backslashes)**
- Python scripts use forward slashes `/`
- Windows uses backslashes `\`
- Solution: Use `pathlib.Path` or WSL2

### **Issue: "Permission denied" when installing**
```powershell
# Run PowerShell as Administrator
# Right-click PowerShell → "Run as Administrator"
```

### **Issue: TauDEM build fails on Windows**
- This is complex! Requires Visual Studio, CMake, MS-MPI SDK
- **Solution**: Use WSL2 instead (much easier)

---

## 💡 Quick Start Cheat Sheet

### Linux / macOS / WSL2
```bash
# 1. Create environment (once)
conda env create -f environment.yml

# 2. Activate environment (every session)
conda activate meadow

# 3. Run pipeline
python run_pipeline.py GEE/TIF_Input/your_watershed.tif

# 4. Deactivate when done
conda deactivate
```

### Windows PowerShell
```powershell
# 1. Create environment (once)
conda env create -f environment.yml

# 2. Activate environment (every session)
conda activate meadow

# 3. Run pipeline (note backslashes)
python run_pipeline.py GEE\TIF_Input\your_watershed.tif

# 4. Deactivate when done
conda deactivate
```

---

## 📚 Additional Resources

- **Paper**: "Resetting the baseline: using machine learning to find lost meadows" (Cummings et al., 2023)
- **TauDEM Documentation**: https://hydrology.usu.edu/taudem/taudem5/
- **Rasterio Docs**: https://rasterio.readthedocs.io/
- **Scikit-learn Docs**: https://scikit-learn.org/

---

## 🆘 Getting Help

If you encounter issues:

1. Check this SETUP.md file first
2. Search existing GitHub issues
3. Create a new issue with:
   - Your OS and version
   - Full error message
   - Steps to reproduce

---

## ✅ You're Ready!

Once all checks pass, you're ready to detect lost meadows! 🌿

Next: See `README.md` for usage instructions and examples.
