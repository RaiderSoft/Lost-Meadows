#!/usr/bin/env python3
"""
Calculate advanced terrain features for meadow detection

Adds 11 new features:
1. Aspect (slope direction)
2-3. Curvature (profile and plan)
4. Elevation (absolute)
5-7. TPI (Topographic Position Index) at 3 scales
8. TRI (Terrain Ruggedness Index)
9-11. Multi-scale std dev (elevation 3x3, 9x9; slope 9x9)
"""

import rasterio
import numpy as np
from scipy.ndimage import generic_filter, uniform_filter, distance_transform_edt
import sys
from pathlib import Path


def calculate_aspect(dem):
    """Calculate aspect (slope direction) in degrees"""
    dy, dx = np.gradient(dem, 10)  # 10m pixel size
    aspect = np.degrees(np.arctan2(-dx, dy))
    aspect = (aspect + 360) % 360  # 0-360 degrees
    return aspect.astype(np.float32)


def calculate_curvature(dem, pixel_size=10):
    """Calculate profile and plan curvature"""
    # Calculate gradients
    zy, zx = np.gradient(dem, pixel_size)

    # Second derivatives
    zxy, zxx = np.gradient(zx, pixel_size)
    zyy, _ = np.gradient(zy, pixel_size)

    # Profile curvature (curvature in direction of slope)
    profile_curv = -((zxx * zy**2 + zyy * zx**2 - 2 * zxy * zx * zy) /
                     (zx**2 + zy**2 + 1e-10)**1.5)

    # Plan curvature (curvature perpendicular to slope)
    plan_curv = -((zxx * zx**2 + zyy * zy**2 + 2 * zxy * zx * zy) /
                  (zx**2 + zy**2 + 1e-10)**1.5)

    return profile_curv.astype(np.float32), plan_curv.astype(np.float32)


def calculate_tpi(elevation, window_size=3):
    """Calculate Topographic Position Index

    TPI = focal elevation - mean elevation in window
    Positive = ridges, Negative = valleys
    """
    # Handle NaN values using nanmean
    def nanmean_filter(values):
        return np.nanmean(values)

    # Mean elevation in window (ignoring NaN)
    mean_elev = generic_filter(elevation, nanmean_filter, size=window_size, mode='reflect')

    # TPI = elevation - mean elevation
    tpi = elevation - mean_elev

    return tpi.astype(np.float32)


def calculate_tri(elevation):
    """Calculate Terrain Ruggedness Index

    TRI = sum of absolute differences from center cell
    """
    def tri_func(values):
        # Sum of absolute differences from center
        center = values[len(values)//2]
        return np.sum(np.abs(values - center))

    tri = generic_filter(elevation, tri_func, size=3, mode='reflect')
    return tri.astype(np.float32)


def fill_boundary_nans(data, watershed_mask):
    """
    Fill NaN pixels that are inside the watershed but got NaN'd due to edge
    effects in gradient or windowed filter operations. Uses nearest-neighbor
    interpolation from surrounding valid pixels.

    watershed_mask: boolean array, True where DEM is valid (inside watershed)
    """
    invalid = np.isnan(data) & watershed_mask
    n_invalid = int(invalid.sum())
    if n_invalid > 0:
        _, nearest = distance_transform_edt(
            np.isnan(data), return_distances=True, return_indices=True
        )
        data[invalid] = data[nearest[0][invalid], nearest[1][invalid]]
    return data, n_invalid


def calculate_std_dev_multiwindow(data, window_sizes=[3, 5, 9]):
    """Calculate standard deviation at multiple window sizes"""
    results = {}

    for window in window_sizes:
        def std_func(values):
            return np.std(values)

        std_dev = generic_filter(data, std_func, size=window, mode='reflect')
        results[f'window_{window}'] = std_dev.astype(np.float32)

    return results


def main(watershed_name):
    """Calculate all advanced features"""

    base_output_dir = Path(__file__).resolve().parent.parent.parent / "GEE" / "TIF_Output"
    output_dir = base_output_dir / watershed_name

    print(f"\n{'='*60}")
    print(f"Calculating Advanced Features - {watershed_name}")
    print(f"{'='*60}\n")

    # Load DEM
    dem_files = list(output_dir.glob("*_filled.tif"))
    if not dem_files:
        print("ERROR: No filled DEM found. Run TauDEM first!")
        sys.exit(1)

    dem_file = dem_files[0]
    print(f"Loading DEM: {dem_file.name}")

    with rasterio.open(dem_file) as src:
        dem = src.read(1).astype(np.float64)
        profile = src.profile

    # Mask of pixels inside the watershed (used for boundary NaN filling)
    # Outside-watershed pixels are stored as NaN in the GEE-exported DEM
    watershed_mask = ~np.isnan(dem)

    # 1. Aspect
    print("Calculating aspect...")
    aspect = calculate_aspect(dem)
    aspect, n = fill_boundary_nans(aspect, watershed_mask)
    if n: print(f"  (filled {n:,} boundary NaN pixels)")
    with rasterio.open(output_dir / "aspect.tif", 'w', **profile) as dst:
        dst.write(aspect, 1)
    print("✓ aspect.tif")

    # 2. Curvature
    print("Calculating curvature...")
    curv_prof, curv_plan = calculate_curvature(dem)
    curv_prof, n = fill_boundary_nans(curv_prof, watershed_mask)
    if n: print(f"  (filled {n:,} boundary NaN pixels in profile curvature)")
    curv_plan, n = fill_boundary_nans(curv_plan, watershed_mask)
    if n: print(f"  (filled {n:,} boundary NaN pixels in plan curvature)")
    with rasterio.open(output_dir / "curvature_profile.tif", 'w', **profile) as dst:
        dst.write(curv_prof, 1)
    with rasterio.open(output_dir / "curvature_plan.tif", 'w', **profile) as dst:
        dst.write(curv_plan, 1)
    print("✓ curvature_profile.tif, curvature_plan.tif")

    # 3. Elevation (copy DEM as feature)
    print("Saving elevation as feature...")
    with rasterio.open(output_dir / "elevation.tif", 'w', **profile) as dst:
        dst.write(dem.astype(np.float32), 1)
    print("✓ elevation.tif")

    # 4. TPI at multiple scales
    print("Calculating TPI at multiple scales...")
    for window in [3, 11, 21]:
        tpi = calculate_tpi(dem, window)
        with rasterio.open(output_dir / f"tpi_{window}x{window}.tif", 'w', **profile) as dst:
            dst.write(tpi, 1)
        print(f"✓ tpi_{window}x{window}.tif")

    # 5. TRI
    print("Calculating TRI...")
    tri = calculate_tri(dem)
    tri, n = fill_boundary_nans(tri, watershed_mask)
    if n: print(f"  (filled {n:,} boundary NaN pixels)")
    with rasterio.open(output_dir / "tri.tif", 'w', **profile) as dst:
        dst.write(tri, 1)
    print("✓ tri.tif")

    # 6. Multi-scale std dev for elevation
    print("Calculating multi-scale elevation std dev...")
    elev_std = calculate_std_dev_multiwindow(dem, [3, 9])
    for window, data in elev_std.items():
        size = window.split('_')[1]
        data, n = fill_boundary_nans(data, watershed_mask)
        if n: print(f"  (filled {n:,} boundary NaN pixels in elev_std_{size}x{size})")
        with rasterio.open(output_dir / f"elev_std_{size}x{size}.tif", 'w', **profile) as dst:
            dst.write(data, 1)
        print(f"✓ elev_std_{size}x{size}.tif")

    # 7. Load slope and calculate multi-scale slope std dev
    slope_file = output_dir / "slope.tif"
    if slope_file.exists():
        print("Calculating multi-scale slope std dev...")
        with rasterio.open(slope_file) as src:
            slope = src.read(1).astype(np.float64)

        slope_std = calculate_std_dev_multiwindow(slope, [3, 9])
        for window, data in slope_std.items():
            size = window.split('_')[1]
            data, n = fill_boundary_nans(data, watershed_mask)
            if n: print(f"  (filled {n:,} boundary NaN pixels in slope_std_{size}x{size})")
            with rasterio.open(output_dir / f"slope_std_{size}x{size}.tif", 'w', **profile) as dst:
                dst.write(data, 1)
            print(f"✓ slope_std_{size}x{size}.tif")

    print(f"\n{'='*60}")
    print("Advanced features complete!")
    print(f"Added 11 new features → Total: 20 features")
    print(f"{'='*60}")

    # Clean up TauDEM intermediate files (now that ALL features are done)
    print(f"\n{'='*60}")
    print("Cleaning up TauDEM intermediate files...")
    print(f"{'='*60}")

    # Find all files matching TauDEM patterns (except dd_s, dd_h, dd_v which are features)
    taudem_patterns = ['*_filled.tif', '*_p.tif', '*_ad8.tif', '*_src.tif',
                       '*_ang.tif', '*_sd8.tif', '*_sca.tif', '*_slp.tif']

    deleted_count = 0
    for pattern in taudem_patterns:
        for file in output_dir.glob(pattern):
            try:
                file.unlink()
                print(f"  ✓ Deleted {file.name}")
                deleted_count += 1
            except Exception as e:
                print(f"  ⚠ Could not delete {file.name}: {e}")

    if deleted_count > 0:
        print(f"\n✓ Cleaned up {deleted_count} TauDEM intermediate files")
    else:
        print(f"\n✓ No TauDEM intermediate files to clean up")

    print(f"\nOnly feature files (20 total) remain in output directory")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python calculate_advanced_features.py <watershed_name>")
        sys.exit(1)

    watershed_name = sys.argv[1]
    main(watershed_name)
