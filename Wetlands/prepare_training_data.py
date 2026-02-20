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
from shapely.geometry import box

def load_wetlands(study_bounds):
    """
    Load wetlands from Oregon and/or California based on study area location
    Automatically detects which dataset(s) to use
    """
    
    min_lon, min_lat = study_bounds[0], study_bounds[1]
    max_lon, max_lat = study_bounds[2], study_bounds[3]
    
    print(f"Study area bounds:")
    print(f"  Longitude: {min_lon:.2f} to {max_lon:.2f}")
    print(f"  Latitude: {min_lat:.2f} to {max_lat:.2f}")
    
    # Determine which state(s) to load based on latitude
    # Oregon/CA border is at 42°N
    use_oregon = max_lat >= 42.0
    use_california = min_lat < 42.5  # Small overlap for border watersheds

    print(f"\nDatasets to load:")
    print(f"  Oregon: {'Yes' if use_oregon else 'No'}")
    print(f"  California: {'Yes' if use_california else 'No'}")

    wetlands_list = []

    # Use ACTUAL study bounds with small buffer (0.1 degree = ~10km)
    # This prevents loading hundreds of thousands of unnecessary polygons
    buffer = 0.1
    filter_bounds_tight = box(
        min_lon - buffer,
        min_lat - buffer,
        max_lon + buffer,
        max_lat + buffer
    )

    print(f"\nFilter area (study bounds + 0.1° buffer):")
    print(f"  Longitude: {min_lon - buffer:.2f} to {max_lon + buffer:.2f}")
    print(f"  Latitude: {min_lat - buffer:.2f} to {max_lat + buffer:.2f}")

    # Load Oregon if needed (with tight spatial filter)
    if use_oregon:
        print("\nLoading Oregon wetlands...")
        try:
            or_gdb = 'OR_geodatabase_wetlands.gdb'

            or_filter_gdf = gpd.GeoDataFrame([1], geometry=[filter_bounds_tight], crs='EPSG:4326')

            # Get CRS and reproject filter
            or_crs = gpd.read_file(or_gdb, rows=1).crs
            print(f"  Oregon CRS: {or_crs}")
            or_filter = or_filter_gdf.to_crs(or_crs).geometry.iloc[0]

            or_wetlands = gpd.read_file(or_gdb, layer='OR_Wetlands', mask=or_filter)
            print(f"  ✓ Loaded {len(or_wetlands):,} Oregon wetland polygons")
            wetlands_list.append(or_wetlands)
        except Exception as e:
            print(f"  ⚠ Warning: Could not load Oregon wetlands: {e}")

    # Load California if needed (with tight spatial filter)
    if use_california:
        print("\nLoading California wetlands...")
        try:
            ca_gdb = 'CA_geodatabase_wetlands.gdb'

            ca_filter_gdf = gpd.GeoDataFrame([1], geometry=[filter_bounds_tight], crs='EPSG:4326')

            # Get CRS and reproject filter
            ca_crs = gpd.read_file(ca_gdb, layer='CA_Wetlands', rows=1).crs
            print(f"  California CRS: {ca_crs}")
            ca_filter = ca_filter_gdf.to_crs(ca_crs).geometry.iloc[0]

            ca_wetlands = gpd.read_file(
                ca_gdb,
                layer='CA_Wetlands',
                mask=ca_filter
            )
            print(f"  ✓ Loaded {len(ca_wetlands):,} California wetland polygons")
            wetlands_list.append(ca_wetlands)
        except Exception as e:
            print(f"  ⚠ Warning: Could not load California wetlands: {e}")
    
    # Combine datasets
    if len(wetlands_list) == 0:
        print("\nERROR: No wetlands loaded!")
        return None
    elif len(wetlands_list) == 1:
        gdf = wetlands_list[0]
    else:
        print("\nMerging Oregon and California wetlands...")
        gdf = gpd.pd.concat(wetlands_list, ignore_index=True)

    print(f"\nTotal wetland polygons before filter: {len(gdf):,}")

    # Filter to meadow and degraded meadow wetland types:
    # PEM = Palustrine Emergent (active wet meadows)
    # PSS = Palustrine Scrub-Shrub (meadows degraded by shrub/willow encroachment)
    # PFO = Palustrine Forested (meadows degraded by conifer encroachment)
    meadow_mask = gdf['ATTRIBUTE'].str.startswith(('PEM', 'PSS', 'PFO'))
    gdf = gdf[meadow_mask].copy()

    pem_count = gdf['ATTRIBUTE'].str.startswith('PEM').sum()
    pss_count = gdf['ATTRIBUTE'].str.startswith('PSS').sum()
    pfo_count = gdf['ATTRIBUTE'].str.startswith('PFO').sum()
    print(f"  PEM (active wet meadow):          {pem_count:,}")
    print(f"  PSS (shrub-encroached meadow):    {pss_count:,}")
    print(f"  PFO (conifer-encroached meadow):  {pfo_count:,}")
    print(f"  Total lost meadow polygons:       {len(gdf):,}")

    if len(gdf) == 0:
        print("ERROR: No meadow wetlands (PEM/PSS/PFO) found in study area!")
        return None

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

def main(watershed_name):
    """Main pipeline for preparing training data"""

    print(f"\n{'='*60}")
    print(f"Preparing Real Training Data - {watershed_name}")
    print(f"{'='*60}\n")

    # Paths
    base_dir = Path.home() / "Capstone" / "Lost-Meadows"
    output_dir = base_dir / "GEE" / "TIF_Output" / watershed_name

    if not output_dir.exists():
        print(f"ERROR: Output directory not found: {output_dir}")
        print("Make sure you've run the feature stacking step first!")
        sys.exit(1)
    
    reference_raster = output_dir / "features_stacked.tif"
    wetland_raster_path = output_dir / "wetland_mask.tif"
    training_csv = output_dir / "training_data_real.csv"
    
    # Check inputs
    if not reference_raster.exists():
        print(f"ERROR: {reference_raster} not found!")
        print("Run feature stacking first!")
        sys.exit(1)
    
    # Get study area bounds from reference raster
    with rasterio.open(reference_raster) as src:
        bounds = src.bounds
        study_bounds = [bounds.left, bounds.bottom, bounds.right, bounds.top]
    
    # Step 1: Load wetlands (auto-detects OR/CA)
    wetlands = load_wetlands(study_bounds)
    
    if wetlands is None:
        sys.exit(1)
    
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
        # Original 9 features
        'slope', 'elev_5x5_rel', 'elev_5x5_std_dev', 'slope_5x5_std_dev',
        'twi_10m', 'twi_100m', 'dd_s', 'dd_h', 'dd_v',
        # Advanced features (11)
        'aspect', 'curvature_profile', 'curvature_plan', 'elevation',
        'tpi_3x3', 'tpi_11x11', 'tpi_21x21', 'tri',
        'elev_std_3x3', 'elev_std_9x9', 'slope_std_9x9'
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
    print(f"  python train_random_forest.py {watershed_name}")

    # Clean up wetland mask
    print("\nCleaning up intermediate files...")
    if wetland_raster_path.exists():
        wetland_raster_path.unlink()
        print(f"  ✓ Deleted wetland_mask.tif (data now in CSV)")
    
    print(f"\nOutputs:")
    print(f"  - Training CSV: {training_csv}")

if __name__ == "__main__":
    # Check for geopandas
    try:
        import geopandas
    except ImportError:
        print("ERROR: geopandas not installed!")
        print("Install with: conda install -c conda-forge geopandas")
        sys.exit(1)

    if len(sys.argv) < 2:
        print("Usage: python prepare_training_data.py <watershed_name>")
        print("\nExample:")
        print("  python prepare_training_data.py Bear_Creek_Watershed_10m")
        # Auto-detect if only one watershed directory exists
        base_dir = Path.home() / "Capstone" / "Lost-Meadows" / "GEE" / "TIF_Output"
        watersheds = [d.name for d in base_dir.iterdir() if d.is_dir() and not d.name.startswith('.')]
        if len(watersheds) == 1:
            watershed_name = watersheds[0]
            print(f"\nAuto-detected: {watershed_name}")
        else:
            print(f"\nAvailable watersheds: {', '.join(watersheds)}")
            sys.exit(1)
    else:
        watershed_name = sys.argv[1]

    main(watershed_name)