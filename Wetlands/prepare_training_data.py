#!/usr/bin/env python3
"""
Prepare training data from NWI wetlands for Random Forest model
Uses ALL wetlands as positive training examples
"""

import geopandas as gpd
import rasterio
from rasterio.features import rasterize
import numpy as np
import pandas as pd
from pathlib import Path
import sys

def load_wetlands(nwi_geojson):
    """
    Load only northern California wetlands using spatial filter
    """
    print(f"Loading wetlands data from: {nwi_geojson}")
    
    # Define bounding box in lat/lon for northern CA
    min_lon, min_lat = -124.5, 41.0
    max_lon, max_lat = -121.0, 43.0
    
    print(f"Filtering to northern CA only:")
    print(f"  Longitude: {min_lon} to {max_lon}")
    print(f"  Latitude: {min_lat} to {max_lat}")
    
    from shapely.geometry import box
    import geopandas as gpd
    
    # Create filter box in lat/lon
    filter_box = box(min_lon, min_lat, max_lon, max_lat)
    filter_gdf = gpd.GeoDataFrame([1], geometry=[filter_box], crs='EPSG:4326')
    
    # Reproject filter to match geodatabase CRS (NAD_1983_Albers)
    gdb_crs = gpd.read_file(nwi_geojson, layer='CA_Wetlands', rows=1).crs
    filter_gdf = filter_gdf.to_crs(gdb_crs)
    
    print(f"Filter box reprojected to: {gdb_crs}")
    
    # Read with mask in correct projection
    gdf = gpd.read_file(
        nwi_geojson, 
        layer='CA_Wetlands',
        mask=filter_gdf.geometry.iloc[0]
    )
    
    print(f"Wetland polygons in northern CA: {len(gdf):,}")
    
    return gdf

def rasterize_wetlands(wetlands_gdf, reference_raster, output_path):
    """
    Convert wetland polygons to raster matching reference raster
    """
    print(f"\nRasterizing wetland polygons...")
    
    with rasterio.open(reference_raster) as ref:
        profile = ref.profile.copy()
        transform = ref.transform
        shape = (ref.height, ref.width)
        bounds = ref.bounds
        crs = ref.crs
    
    print(f"Reference raster:")
    print(f"  CRS: {crs}")
    print(f"  Dimensions: {shape[1]} x {shape[0]} pixels")
    print(f"  Bounds: {bounds}")
    
    print(f"\nWetland polygons CRS: {wetlands_gdf.crs}")
    
    # Reproject if needed
    if wetlands_gdf.crs != crs:
        print(f"Reprojecting wetlands from {wetlands_gdf.crs} to {crs}")
        wetlands_gdf = wetlands_gdf.to_crs(crs)
    
    # Check if any polygons intersect the study area
    from shapely.geometry import box
    study_box = box(bounds.left, bounds.bottom, bounds.right, bounds.top)
    wetlands_in_area = wetlands_gdf[wetlands_gdf.intersects(study_box)]
    
    print(f"\nWetlands intersecting study area: {len(wetlands_in_area):,}")
    
    if len(wetlands_in_area) == 0:
        print("WARNING: No wetlands found in study area!")
        print("Study area may not overlap with wetland data")
        return None
    
    # Rasterize
    shapes = [(geom, 1) for geom in wetlands_in_area.geometry]
    
    wetland_raster = rasterize(
        shapes,
        out_shape=shape,
        transform=transform,
        fill=0,
        dtype='uint8'
    )
    
    n_wetland_pixels = np.sum(wetland_raster == 1)
    print(f"Rasterized {n_wetland_pixels:,} wetland pixels")
    print(f"Wetland coverage: {100 * n_wetland_pixels / (shape[0] * shape[1]):.2f}%")
    
    # Save
    profile.update({'dtype': 'uint8', 'count': 1, 'nodata': 255})
    with rasterio.open(output_path, 'w', **profile) as dst:
        dst.write(wetland_raster, 1)
    
    print(f"✓ Saved wetland raster to: {output_path}")
    
    return wetland_raster

def sample_training_points(wetland_raster, features_raster, n_wetland=1000, n_non_wetland=9000):
    """
    Sample training points from wetland and non-wetland areas
    """
    print(f"\nSampling training points...")
    
    # Load features
    with rasterio.open(features_raster) as src:
        features = src.read()  # Shape: (bands, height, width)
        n_bands, height, width = features.shape
    
    print(f"Features shape: {n_bands} bands, {height}x{width} pixels")
    
    # Flatten
    features_flat = features.reshape(n_bands, -1).T  # (pixels, bands)
    wetland_flat = wetland_raster.flatten()
    
    # Create valid pixel mask (no NaN, no extreme values)
    valid_mask = np.ones(features_flat.shape[0], dtype=bool)
    valid_mask &= ~np.any(np.isnan(features_flat), axis=1)
    valid_mask &= ~np.any(np.isinf(features_flat), axis=1)
    valid_mask &= ~np.any(features_flat < -1e30, axis=1)
    
    print(f"Valid pixels: {np.sum(valid_mask):,} ({100*np.sum(valid_mask)/len(valid_mask):.1f}%)")
    
    # Separate wetland and non-wetland pixels
    wetland_pixels = np.where((wetland_flat == 1) & valid_mask)[0]
    non_wetland_pixels = np.where((wetland_flat == 0) & valid_mask)[0]
    
    print(f"Available wetland pixels: {len(wetland_pixels):,}")
    print(f"Available non-wetland pixels: {len(non_wetland_pixels):,}")
    
    if len(wetland_pixels) == 0:
        print("ERROR: No valid wetland pixels found!")
        print("Wetlands may not overlap with valid feature data")
        return None, None
    
    # Sample
    n_wetland_sample = min(n_wetland, len(wetland_pixels))
    n_non_wetland_sample = min(n_non_wetland, len(non_wetland_pixels))
    
    print(f"\nSampling {n_wetland_sample:,} wetland points...")
    meadow_sample_idx = np.random.choice(wetland_pixels, n_wetland_sample, replace=False)
    
    print(f"Sampling {n_non_wetland_sample:,} non-wetland points...")
    non_meadow_sample_idx = np.random.choice(non_wetland_pixels, n_non_wetland_sample, replace=False)
    
    # Combine
    sample_idx = np.concatenate([meadow_sample_idx, non_meadow_sample_idx])
    labels = np.concatenate([
        np.ones(n_wetland_sample),
        np.zeros(n_non_wetland_sample)
    ])
    
    sampled_features = features_flat[sample_idx]
    
    print(f"\nFinal training set:")
    print(f"  Wetland samples: {n_wetland_sample:,}")
    print(f"  Non-wetland samples: {n_non_wetland_sample:,}")
    print(f"  Ratio: 1:{n_non_wetland_sample/n_wetland_sample:.1f}")
    
    return sampled_features, labels

def main(run_num):
    """Main pipeline for preparing training data"""
    
    print(f"\n{'='*60}")
    print("Preparing Real Training Data from NWI Wetlands")
    print(f"{'='*60}\n")
    
    # Paths
    base_dir = Path.home() / "Capstone" / "Lost-Meadows"
    nwi_file = base_dir / "Wetlands" / "CA_geodatabase_wetlands" / "CA_geodatabase_wetlands.gdb"
    output_dir = base_dir / "GEE" / "TIF_Output" / str(run_num)
    
    reference_raster = output_dir / "features_stacked.tif"
    wetland_raster_path = output_dir / "wetland_mask.tif"
    training_csv = output_dir / "training_data_real.csv"
    
    # Check inputs
    if not nwi_file.exists():
        print(f"ERROR: {nwi_file} not found!")
        sys.exit(1)
    
    if not reference_raster.exists():
        print(f"ERROR: {reference_raster} not found!")
        print("Run feature stacking first!")
        sys.exit(1)
    
    # Step 1: Load wetlands
    wetlands = load_wetlands(str(nwi_file))
    
    # Step 2: Rasterize wetlands
    wetland_raster = rasterize_wetlands(wetlands, str(reference_raster), str(wetland_raster_path))
    
    if wetland_raster is None:
        print("\nERROR: Could not create wetland raster")
        sys.exit(1)
    
    # Step 3: Sample training points
    features, labels = sample_training_points(
        wetland_raster, 
        str(reference_raster),
        n_wetland=1000,
        n_non_wetland=9000
    )
    
    if features is None:
        sys.exit(1)
    
    # Step 4: Save as CSV
    print(f"\nSaving training data to: {training_csv}")
    
    feature_names = [
        'slope', 'elev_5x5_rel', 'elev_5x5_std_dev', 'slope_5x5_std_dev',
        'twi_10m', 'twi_100m', 'dd_s', 'dd_h', 'dd_v'
    ]
    
    df = pd.DataFrame(features, columns=feature_names)
    df['label'] = labels.astype(int)
    df.to_csv(training_csv, index=False)
    
    print(f"✓ Saved {len(df):,} training samples")
    
    print(f"\n{'='*60}")
    print("Training Data Preparation Complete!")
    print(f"{'='*60}")
    print(f"\nOutputs:")
    print(f"  - Wetland mask: {wetland_raster_path}")
    print(f"  - Training CSV: {training_csv}")
    print(f"\nNext: Retrain model with real wetland data")
    print(f"  cd ~/Capstone/Lost-Meadows/ModelTraining")
    print(f"  python train_random_forest.py {run_num} --real-data")

if __name__ == "__main__":
    # Check for geopandas
    try:
        import geopandas
    except ImportError:
        print("ERROR: geopandas not installed!")
        print("Install with: conda install -c conda-forge geopandas")
        sys.exit(1)
    
    run_num = sys.argv[1] if len(sys.argv) > 1 else "1"
    main(run_num)