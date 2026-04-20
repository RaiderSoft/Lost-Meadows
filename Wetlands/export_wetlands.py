#!/usr/bin/env python3
"""
One-time export: filter OR + CA wetland .gdb files to PEM/PSS types,
clip to the Cascade-Siskiyou bioregion, and save as GeoJSON for
upload to GEE as a Table asset.

Usage:
  cd Lost-Meadows
  python Wetlands/export_wetlands_for_gee.py
"""

import geopandas as gpd
import pandas as pd
from pathlib import Path
from shapely.geometry import box

# Cascade-Siskiyou bioregion bounding box (degrees)
# Adjust if you have a tighter polygon — this is a safe outer envelope
BIOREGION_BOUNDS = (-124.6, 41.0, -120.5, 44.5)  # (min_lon, min_lat, max_lon, max_lat)

WETLANDS_DIR = Path(__file__).resolve().parent
OUTPUT_PATH  = WETLANDS_DIR / 'wetlands_PEM_PSS_bioregion.geojson'

def load_and_filter(gdb_path, layer_name, clip_geom, label):
    print(f'\nLoading {label}...')
    gdf = gpd.read_file(gdb_path, layer=layer_name, mask=clip_geom)
    print(f'  Raw polygons in bounding box: {len(gdf):,}')

    # Filter to meadow-relevant Cowardin types
    mask = gdf['ATTRIBUTE'].str.startswith(('PEM', 'PSS'), na=False)
    gdf  = gdf[mask].copy()
    print(f'  PEM/PSS polygons: {len(gdf):,}')

    # Keep only columns needed for the overlay
    keep = ['ATTRIBUTE', 'WETLAND_TYPE', 'ACRES', 'geometry']
    keep = [c for c in keep if c in gdf.columns]
    return gdf[keep]

def main():
    clip_geom = gpd.GeoDataFrame(
        [1], geometry=[box(*BIOREGION_BOUNDS)], crs='EPSG:4326'
    ).geometry.iloc[0]

    or_gdb = WETLANDS_DIR / 'OR_geodatabase_wetlands.gdb'
    ca_gdb = WETLANDS_DIR / 'CA_geodatabase_wetlands.gdb'

    parts = []

    if or_gdb.exists():
        # Detect CRS, reproject clip geometry, then load
        or_crs  = gpd.read_file(or_gdb, rows=1).crs
        or_clip = gpd.GeoDataFrame([1], geometry=[clip_geom], crs='EPSG:4326').to_crs(or_crs).geometry.iloc[0]
        parts.append(load_and_filter(or_gdb, 'OR_Wetlands', or_clip, 'Oregon'))
    else:
        print('WARNING: OR_geodatabase_wetlands.gdb not found — skipping')

    if ca_gdb.exists():
        ca_crs  = gpd.read_file(ca_gdb, layer='CA_Wetlands', rows=1).crs
        ca_clip = gpd.GeoDataFrame([1], geometry=[clip_geom], crs='EPSG:4326').to_crs(ca_crs).geometry.iloc[0]
        parts.append(load_and_filter(ca_gdb, 'CA_Wetlands', ca_clip, 'California'))
    else:
        print('WARNING: CA_geodatabase_wetlands.gdb not found — skipping')

    if not parts:
        print('ERROR: No wetland data found.')
        return

    merged = gpd.GeoDataFrame(
        pd.concat(parts, ignore_index=True),
        crs=parts[0].crs
    ).to_crs('EPSG:4326')

    print(f'\nTotal PEM/PSS polygons for export: {len(merged):,}')
    merged.to_file(OUTPUT_PATH, driver='GeoJSON')
    print(f'Saved: {OUTPUT_PATH}')
    print('\nNext: upload to GEE')
    print('  earthengine upload table \\')
    print('    --asset_id projects/lost-meadows/assets/wetlands_PEM_PSS \\')
    print(f'   {OUTPUT_PATH}')

if __name__ == '__main__':
    main()