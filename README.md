# Lost Meadows Detection Using Machine Learning

Replication of "Resetting the baseline: using machine learning to find lost meadows" (Cummings et al., 2023) for detecting potential historical meadow locations using Random Forest classification on hydrogeomorphic features.

---

## Table of Contents

1. [Project Overview](#project-overview)
2. [Project Structure](#project-structure)
3. [Requirements](#requirements)
4. [Workflow Overview](#workflow-overview)
5. [Detailed Step-by-Step Instructions](#detailed-step-by-step-instructions)
6. [Expected Outputs](#expected-outputs)
7. [Current Status](#current-status)
8. [Known Issues](#known-issues)
9. [References](#references)

---

## Project Overview

### What This Project Does

This project uses machine learning (Random Forest) to predict where meadows likely existed historically but may no longer be mapped. It analyzes terrain and hydrological features derived from elevation data to identify locations with meadow-like characteristics.

### Why It Matters

- Meadows provide critical ecosystem services (water storage, biodiversity, carbon sequestration)
- Many meadows have been lost or degraded but remain unmapped
- Machine learning can identify "lost" meadows at scale for restoration prioritization

### The Approach

1. **Extract hydrogeomorphic features** from elevation data (slope, wetness, distance to streams, etc.)
2. **Train a Random Forest model** on known meadow locations
3. **Predict meadow probability** across entire watersheds
4. **Identify high-confidence potential meadows** for ground-truthing and restoration

---

## Project Structure
```
Lost-Meadows/
├── README.md                          # This file
├── docs/                              # Project website (GitHub Pages)
│   ├── index.html                     # Main landing page
│   ├── client.html                    # Client page
│   ├── team.html                      # Team page
│   ├── tools.html                     # Tools page
│   ├── video.html                     # Video page
│   ├── styles.css                     # Stylesheet
│   ├── favicon.svg                    # Site icon
│   ├── leaves.js                      # Falling leaves animation
│   ├── logo-animate.js                # Logo animation
│   ├── nav.js                         # Navigation scripts
│   ├── scroll-animate.js              # Scroll animations
│   ├── images/                        # Image assets
│   ├── WEBSITE.md                     # Website documentation
│   └── _config.yml                    # Jekyll configuration
├── GEE/                               # Google Earth Engine scripts and data
│   ├── TIF_Export.js                  # GEE script for elevation export (runs in GEE)
│   ├── MeadowVisualization.js         # GEE script for visualization (runs in GEE)
│   ├── TIF_Input/                     # Original elevation data from GEE
│   │   └── 3DEP_10m_TEST_watershed.tif
│   └── TIF_Output/                    # Processed features and results
│       └── 1/                         # Run #1 outputs
│           ├── [TauDEM outputs]       # Flow direction, accumulation, etc.
│           ├── twi_10m.tif            # Topographic Wetness Index 10m
│           ├── twi_100m.tif           # Topographic Wetness Index 100m
│           ├── dd_s.tif               # Surface distance to stream
│           ├── dd_h.tif               # Horizontal distance to stream
│           ├── dd_v.tif               # Vertical distance to stream
│           ├── slope.tif              # Slope
│           ├── elev_5x5_rel.tif       # Relative elevation (5x5 window)
│           ├── elev_5x5_std_dev.tif   # Elevation std dev (5x5 window)
│           ├── slope_5x5_std_dev.tif  # Slope std dev (5x5 window)
│           ├── features_stacked.tif   # All 9 features in one multi-band raster
│           ├── random_forest_model.pkl # Trained model
│           └── meadow_probability.tif  # Predicted meadow probabilities (0-1)
├── TauDEM/                            # TauDEM workflow scripts (runs in WSL)
│   └── run_taudem_workflow.py         # Automated TauDEM processing
├── FeatureEngineering/                # Feature generation scripts (runs in WSL)
│   ├── TWI/
│   │   ├── calculate_twi_10m.py       # Calculate TWI at 10m resolution
│   │   └── calculate_twi_100m.py      # Calculate TWI at 100m, resample to 10m
│   └── Terrain/
│       └── calculate_terrain_features.py  # Slope, relative elevation, std devs
├── FeatureStacking/                   # Feature stacking scripts (runs in WSL)
│   └── stack_features.py              # Combine all features into multi-band raster
└── ModelTraining/                     # Machine learning scripts (runs in WSL)
    ├── train_random_forest.py         # Train Random Forest classifier
    └── predict_meadows.py             # Apply model to generate probability map
```

**Notes:**
- `TIF_Export.js` and `MeadowVisualization.js` are Google Earth Engine scripts that run in the GEE Code Editor (https://code.earthengine.google.com), NOT in VSCode or WSL. All Python scripts run in WSL with the conda environment.
- Large data files (`.tif`, `.pkl`, installers) are excluded from git via `.gitignore` - you'll need to generate these locally by following the workflow steps.

---

## Requirements

### Software

- **Google Earth Engine** account (https://earthengine.google.com)
- **WSL (Windows Subsystem for Linux)** with Ubuntu 24
- **Miniconda** or Anaconda
- **TauDEM** (Terrain Analysis Using Digital Elevation Models)
- **Python 3.10+** with packages:
  - rasterio
  - numpy
  - scipy
  - pandas
  - scikit-learn
  - joblib
  - GDAL

### Installation
```bash
# Install Miniconda (if not already installed)
wget https://repo.anaconda.com/miniconda/Miniconda3-latest-Linux-x86_64.sh
bash Miniconda3-latest-Linux-x86_64.sh
# Close and reopen terminal

# Create environment with all dependencies
conda create -n meadow python=3.10
conda activate meadow
conda install -c conda-forge taudem rasterio numpy scipy pandas scikit-learn joblib gdal
```

---

## Workflow Overview

### High-Level Process (5 Main Steps)

1. **Acquire elevation data** from Google Earth Engine
2. **Generate hydrological features** using TauDEM (flow, wetness, distance to streams)
3. **Generate terrain features** using Python (slope, relative elevation, variability)
4. **Train Random Forest model** on known meadow locations vs non-meadow locations
5. **Predict and visualize** meadow probabilities across the landscape

### Features Used (9 total)

From the paper (Cummings et al., 2023):

| Feature | Description | Tool |
|---------|-------------|------|
| slope | Topographic slope (degrees) | Python |
| elev_5×5_rel | Relative elevation (mean - focal) in 5×5 window | Python |
| elev_5×5_std_dev | Elevation standard deviation in 5×5 window | Python |
| slope_5×5_std_dev | Slope standard deviation in 5×5 window | Python |
| twi_10m | Topographic Wetness Index at 10m resolution | TauDEM + Python |
| twi_100m | Topographic Wetness Index at 100m resolution | TauDEM + Python |
| dd_s | Surface distance to nearest stream | TauDEM |
| dd_h | Horizontal distance to nearest stream | TauDEM |
| dd_v | Vertical distance to nearest stream | TauDEM |

*Note: Paper uses 11 features including snowpack; this implementation uses 9 (snowpack excluded for initial testing)*

---

## Detailed Step-by-Step Instructions

### Step 1: Export Elevation Data from Google Earth Engine

**Where:** Google Earth Engine Code Editor (https://code.earthengine.google.com)

**Script:** `GEE/TIF_Export.js` ⚠️ **Runs in Google Earth Engine Code Editor, NOT VSCode**

**What it does:** Downloads 10m resolution USGS 3DEP elevation data for your study area

**Instructions:**

1. Open GEE Code Editor in your web browser (https://code.earthengine.google.com)
2. Copy and paste the code from `GEE/TIF_Export.js`, or use this example:
3. Adjust the study area coordinates as needed:
```javascript
// Load USGS HUC10 watershed boundaries
var studyArea = ee.Geometry.Rectangle([-120.5, 37.0, -119.0, 38.5]); // Adjust coordinates

var watersheds = ee.FeatureCollection('USGS/WBD/2017/HUC10');
var studyWatersheds = watersheds.filterBounds(studyArea);
var studyAreaRefined = studyWatersheds.union().geometry();

// Load 3DEP elevation data
var dem3DEP = ee.ImageCollection('USGS/3DEP/10m_collection')
  .filterBounds(studyAreaRefined)
  .mosaic()
  .clip(studyAreaRefined);

var elevation = dem3DEP.select('elevation');

// Export
Export.image.toDrive({
  image: elevation,
  description: '3DEP_10m_TEST_watershed',
  folder: 'GEE_Exports_BS',
  fileNamePrefix: '3DEP_10m_TEST_watershed',
  region: studyAreaRefined,
  scale: 10,
  maxPixels: 1e13,
  fileFormat: 'GeoTIFF',
  formatOptions: {cloudOptimized: true}
});
```

4. Click **Run** in the GEE Code Editor
5. Go to **Tasks** tab (upper right) → Click **Run** on the export task
6. Download the file from your Google Drive once the task completes
7. Move the downloaded `.tif` file to the `GEE/TIF_Input/` directory in WSL:
```bash
# From Windows, copy to WSL
cp /mnt/c/Users/YourUsername/Downloads/3DEP_10m_elevation_only.tif ~/Capstone/Lost-Meadows/GEE/TIF_Input/
```

**Output:** `3DEP_10m_TEST_watershed.tif`

---

### Step 2: Generate Hydrological Features with TauDEM

**Where:** WSL terminal, `TauDEM/` directory

**Script:** `run_taudem_workflow.py`

**What it does:** Processes elevation data to calculate flow direction, accumulation, stream networks, and distances to streams

**Instructions:**
```bash
cd ~/Capstone/Lost-Meadows/TauDEM
conda activate meadow
python run_taudem_workflow.py ../GEE/TIF_Input/3DEP_10m_TEST_watershed.tif
```

**Time:** 30-90 minutes depending on watershed size and CPU

**Outputs (in `GEE/TIF_Output/1/`):**
- `3DEP_10m_TEST_watershed_filled.tif` - Pit-filled DEM
- `3DEP_10m_TEST_watershed_p.tif` - D8 flow direction
- `3DEP_10m_TEST_watershed_ad8.tif` - D8 flow accumulation
- `3DEP_10m_TEST_watershed_src.tif` - Stream network
- `3DEP_10m_TEST_watershed_ang.tif` - D-infinity flow angles
- `3DEP_10m_TEST_watershed_sca.tif` - Specific catchment area
- `3DEP_10m_TEST_watershed_slp.tif` - Slope (from TauDEM)
- `dd_s.tif` - Surface distance to stream ✓
- `dd_h.tif` - Horizontal distance to stream ✓
- `dd_v.tif` - Vertical distance to stream ✓

---

### Step 3a: Calculate TWI (Topographic Wetness Index)

**Where:** WSL terminal, `FeatureEngineering/TWI/` directory

**Scripts:** 
- `calculate_twi_10m.py` - TWI at 10m resolution
- `calculate_twi_100m.py` - TWI at 100m resolution (then resampled to 10m)

**What it does:** Calculates wetness index (ln(catchment area / tan(slope))) at two scales

**Instructions:**
```bash
cd ~/Capstone/Lost-Meadows/FeatureEngineering/TWI

# Calculate TWI at 10m
python calculate_twi_10m.py 1

# Calculate TWI at 100m (then resample to 10m)
python calculate_twi_100m.py 1
```

**Time:** 5-10 minutes

**Outputs (in `GEE/TIF_Output/1/`):**
- `twi_10m.tif` ✓
- `twi_100m.tif` ✓

---

### Step 3b: Calculate Terrain Features

**Where:** WSL terminal, `FeatureEngineering/Terrain/` directory

**Script:** `calculate_terrain_features.py`

**What it does:** Calculates slope and moving-window statistics (relative elevation, standard deviations)

**Instructions:**
```bash
cd ~/Capstone/Lost-Meadows/FeatureEngineering/Terrain
python calculate_terrain_features.py 1
```

**Time:** 10-20 minutes (moving windows are computationally intensive)

**Outputs (in `GEE/TIF_Output/1/`):**
- `slope.tif` ✓
- `elev_5x5_rel.tif` ✓
- `elev_5x5_std_dev.tif` ✓
- `slope_5x5_std_dev.tif` ✓

---

### Step 4: Stack All Features into Multi-Band Raster

**Where:** WSL terminal, `FeatureEngineering/FeatureStacking/` directory

**Script:** `stack_features.py`

**What it does:** Combines all 9 feature rasters into a single multi-band GeoTIFF for efficient model training

**Instructions:**
```bash
cd ~/Capstone/Lost-Meadows/FeatureEngineering/FeatureStacking
python stack_features.py 1
```

**Time:** 1-2 minutes

**Output (in `GEE/TIF_Output/1/`):**
- `features_stacked.tif` - 9-band raster with all features

---

### Step 5: Train Random Forest Model

**Where:** WSL terminal, `ModelTraining/` directory

**Script:** `train_random_forest.py`

**What it does:** Trains a Random Forest classifier on meadow vs non-meadow samples

**Instructions:**
```bash
cd ~/Capstone/Lost-Meadows/ModelTraining
python train_random_forest.py 1
```

**Model Parameters (from paper):**
- Number of trees: 300
- mtry (variables per split): 4
- Class imbalance: 1:9 (meadow:non-meadow)

**Time:** 1-2 minutes

**Outputs (in `GEE/TIF_Output/1/`):**
- `random_forest_model.pkl` - Trained model
- Console output showing:
  - Feature importance rankings
  - Accuracy metrics (AUC, precision, recall)
  - Confusion matrix

**Note:** Currently uses synthetic training data (high TWI = meadow). For real results, replace with actual meadow polygon data.

---

### Step 6: Predict Meadow Probabilities

**Where:** WSL terminal, `ModelTraining/` directory

**Script:** `predict_meadows.py`

**What it does:** Applies trained model to entire watershed, generating probability map (0-1 for each pixel)

**Instructions:**
```bash
cd ~/Capstone/Lost-Meadows/ModelTraining
python predict_meadows.py 1
```

**Time:** 5-10 minutes

**Output (in `GEE/TIF_Output/1/`):**
- `meadow_probability.tif` - Probability values (0.0 to 1.0)
  - 0.0 = definitely not a meadow
  - 0.5+ = high confidence meadow (paper's threshold)
  - 1.0 = definitely a meadow

---

### Step 7: Visualize Results in Google Earth Engine

**Where:** Google Earth Engine Code Editor (https://code.earthengine.google.com)

**Script:** `GEE/MeadowVisualization.js` ⚠️ **Runs in Google Earth Engine Code Editor, NOT VSCode**

**What it does:** Creates interactive map showing meadow probabilities

**Instructions:**

1. **Upload probability raster to GEE:**
   - Copy file from WSL to Windows:
```bash
cp /home/lm1/Capstone/Lost-Meadows/GEE/TIF_Output/1/meadow_probability.tif /mnt/c/Users/YourUsername/Downloads/
```
   - In GEE Code Editor → **Assets** tab → **NEW** → **Image Upload**
   - Upload `meadow_probability.tif`
   - Wait for ingestion to complete (check **Tasks** tab)

2. **Create visualization script in GEE Code Editor:**
   - Copy and paste code from `GEE/MeadowVisualization.js`, or use this example:
```javascript
// Load probability raster
var meadowProb = ee.Image('projects/your-project/assets/meadow_probability');

// Visualize probability gradient
var probVis = {
  min: 0,
  max: 1,
  palette: ['white', 'yellow', 'orange', 'red', 'darkred']
};

Map.addLayer(meadowProb, probVis, 'Meadow Probability');

// Visualize high-confidence meadows (>0.5)
var highConfidence = meadowProb.gt(0.5);
Map.addLayer(highConfidence.selfMask(), {palette: ['green']}, 'High Confidence Meadows');

// Center map
Map.centerObject(meadowProb, 10);
```

3. **Update the asset path** in the script to match your GEE project:
   - Replace `'projects/lost-meadows/assets/meadow_probability'` with your actual project path
   - Find your project name in GEE Code Editor under the Assets tab

4. **Run** the script in GEE Code Editor and explore the interactive map!

---

## Expected Outputs

### Intermediate Files

- 20+ TIF files (various resolutions, intermediate products)
- File sizes: 50-500 MB per feature raster
- Total storage: ~2-5 GB per watershed

### Final Deliverables

1. **Feature Stack** (`features_stacked.tif`) - 9-band multi-layer raster
2. **Trained Model** (`random_forest_model.pkl`) - Reusable for other watersheds
3. **Probability Map** (`meadow_probability.tif`) - Main result showing meadow likelihood
4. **GEE Visualization** - Interactive web map

### Validation Metrics

From training (synthetic data example):
- **AUC:** 1.000 (perfect on synthetic data)
- **Precision:** 1.00
- **Recall:** 1.00
- **Feature Importance:** TWI 10m (87%), TWI 100m (6%), distances (6%), terrain (1%)

*Note: Paper reports AUC > 0.89 for real meadow training data*

---

## Current Status

### ✅ Completed

1. Elevation data acquisition from GEE
2. TauDEM hydrological feature generation
3. Python terrain feature generation
4. TWI calculation at both scales
5. Feature stacking
6. Model training framework
7. Prediction pipeline
8. GEE visualization

### ⚠️ Using Synthetic Data

Currently the model is trained on **synthetic labels** (high TWI = meadow) rather than real meadow polygons. This validates the workflow but doesn't produce scientifically meaningful results.

### 🔄 Next Steps

1. **Acquire real meadow training data:**
   - Download National Wetlands Inventory (NWI) data for Oregon
   - Or switch to California Sierra Nevada with actual meadow polygons
   - Filter to "emergent wetlands" (meadow-like habitats)

2. **Retrain model with real data:**
   - Sample inside meadow polygons (positive class)
   - Sample outside meadows (negative class)
   - Maintain 1:9 ratio per paper

3. **Validate on holdout data:**
   - 75% training / 25% testing split
   - Calculate AUC, precision, recall
   - Compare with paper's reported metrics

4. **Scale to full study area:**
   - Process multiple watersheds
   - Compare local vs regional models
   - Identify restoration priorities

---

## Known Issues

### Data Quality Issues

1. **NoData values:** TauDEM uses -3.4028235e+38 as NoData (not recognized by rasterio)
   - **Solution:** Filter values < -1e30 during processing

2. **NaN values:** Some edge pixels have NaN in terrain features
   - **Solution:** Valid mask filters ~40-45% of watershed pixels

3. **Infinity values:** Distance-to-stream can have inf values for pixels far from streams
   - **Solution:** Filter infinite values before model training

### Performance Notes

- **Memory usage:** ~8-16 GB RAM for typical watershed
- **Processing time:** ~2-4 hours total for one watershed
- **Chunk processing:** Prediction uses chunks to avoid memory overflow

### Platform-Specific

- **Windows/WSL file paths:** Use `/mnt/c/` to access Windows drives
- **GEE asset paths:** Cloud assets use `projects/PROJECT/assets/` format
- **Conda environment:** Always activate `meadow` environment before running scripts

---

## References

### Primary Paper

Cummings, A. K., Pope, K. L., & Mak, G. (2023). Resetting the baseline: using machine learning to find lost meadows. *Landscape Ecology*, 38, 2639-2653.  
https://doi.org/10.1007/s10980-023-01726-7

### Data Sources

- **USGS 3DEP:** 10m elevation data
  - https://www.usgs.gov/3d-elevation-program
- **USGS HUC Watersheds:** Watershed boundaries
  - https://www.usgs.gov/national-hydrography/watershed-boundary-dataset
- **National Wetlands Inventory:** Wetland polygons
  - https://www.fws.gov/program/national-wetlands-inventory

### Tools & Methods

- **TauDEM:** Terrain Analysis Using Digital Elevation Models
  - https://hydrology.usu.edu/taudem/
- **Random Forest:** Breiman, L. (2001). Machine Learning, 45(1), 5-32.
- **Google Earth Engine:** Gorelick et al. (2017). Remote Sensing of Environment.

---

## Attribution

**Original Paper Authors:** Cummings, A. K., Pope, K. L., & Mak, G.

---

## License

This project replicates methods from published research. Please cite the original paper when using this workflow.
```
Cummings, A. K., Pope, K. L., & Mak, G. (2023). 
Resetting the baseline: using machine learning to find lost meadows. 
Landscape Ecology, 38, 2639-2653.
```
