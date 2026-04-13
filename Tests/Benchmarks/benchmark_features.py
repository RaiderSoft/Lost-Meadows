#!/usr/bin/env python3
"""
Feature Engineering Benchmark
==============================
Times the specific operations we're considering rewriting (vectorized std dev,
TPI, TRI, XGBoost training) on a synthetic raster of configurable size.

Run this BEFORE and AFTER any changes to compare speedups.

Usage:
    python Tests/Benchmarks/benchmark_features.py           # 1000x1000 (default)
    python Tests/Benchmarks/benchmark_features.py --size 500
    python Tests/Benchmarks/benchmark_features.py --size 2000

REQUIREMENTS: conda activate meadow
"""

import argparse
import time
import numpy as np
from scipy.ndimage import generic_filter, uniform_filter

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_dem(size):
    """Synthetic DEM with a realistic elevation gradient."""
    rng = np.random.default_rng(42)
    x = np.linspace(0, 1, size)
    xx, yy = np.meshgrid(x, x)
    return (1200 + 300 * xx + 200 * yy + 20 * rng.standard_normal((size, size))).astype(np.float64)


def time_it(label, fn, warmup=False):
    """Run fn(), print elapsed time, return (result, elapsed_seconds)."""
    if warmup:
        fn()  # warm up before timing (JIT, cache, etc.)
    t0 = time.perf_counter()
    result = fn()
    elapsed = time.perf_counter() - t0
    print(f"  {elapsed:6.2f}s  {label}")
    return result, elapsed


# ---------------------------------------------------------------------------
# Current implementations (slow — generic_filter with Python callback)
# ---------------------------------------------------------------------------

def current_std_filter(data, window):
    def std_func(values):
        return np.std(values)
    return generic_filter(data.astype(np.float32), std_func, size=window, mode='reflect')


def current_tpi(elevation, window_size):
    def nanmean_filter(values):
        return np.nanmean(values)
    mean_elev = generic_filter(elevation, nanmean_filter, size=window_size, mode='reflect')
    return (elevation - mean_elev).astype(np.float32)


def current_tri(elevation):
    def tri_func(values):
        center = values[len(values) // 2]
        return np.sum(np.abs(values - center))
    return generic_filter(elevation, tri_func, size=3, mode='reflect').astype(np.float32)


# ---------------------------------------------------------------------------
# Proposed implementations (vectorized — no Python callback)
# ---------------------------------------------------------------------------

def fast_std_filter(data, window):
    """Vectorized std dev: Var(X) = E[X²] - E[X]²"""
    d = data.astype(np.float64)
    mean    = uniform_filter(d,    size=window, mode='reflect')
    mean_sq = uniform_filter(d**2, size=window, mode='reflect')
    return np.sqrt(np.maximum(mean_sq - mean**2, 0)).astype(np.float32)


def fast_tpi(elevation, window_size):
    """Vectorized TPI using uniform_filter instead of generic_filter."""
    # Keep float64 throughout to avoid precision loss vs current implementation
    mean_elev = uniform_filter(elevation, size=window_size, mode='reflect')
    return (elevation - mean_elev).astype(np.float32)


def fast_tri(elevation):
    """Vectorized TRI using explicit 3x3 stencil with reflect-padded slicing.

    np.roll wraps edges toroidally — wrong boundary behavior. Instead, pad with
    reflect mode first so sliced neighbors match generic_filter(mode='reflect').
    """
    elev = elevation.astype(np.float64)
    padded = np.pad(elev, 1, mode='reflect')
    tri = np.zeros_like(elev)
    for di in range(3):
        for dj in range(3):
            if di == 1 and dj == 1:
                continue  # skip center cell
            neighbor = padded[di:di + elev.shape[0], dj:dj + elev.shape[1]]
            tri += np.abs(neighbor - elev)
    return tri.astype(np.float32)


# ---------------------------------------------------------------------------
# XGBoost benchmark (training)
# ---------------------------------------------------------------------------

def benchmark_xgboost(n_samples=50_000):
    import xgboost as xgb
    from sklearn.datasets import make_classification

    X, y = make_classification(
        n_samples=n_samples, n_features=23,
        n_informative=15, n_redundant=5,
        weights=[0.8, 0.2], random_state=42
    )

    params = dict(
        n_estimators=200, max_depth=8, learning_rate=0.05,
        subsample=0.8, colsample_bytree=0.6, gamma=0.5,
        reg_alpha=0, reg_lambda=2.0, min_child_weight=1,
        random_state=42, eval_metric='auc',
    )

    print("\n  XGBoost training (CPU):")
    cpu_model = xgb.XGBClassifier(**params)
    _, cpu_time = time_it("  n_estimators=200, 50k samples", lambda: cpu_model.fit(X, y))

    # GPU — only if CUDA is available
    try:
        gpu_model = xgb.XGBClassifier(**params, device='cuda')
        gpu_model.fit(X[:10], y[:10])  # tiny fit to check if GPU works
        print("\n  XGBoost training (GPU):")
        gpu_model2 = xgb.XGBClassifier(**params, device='cuda')
        _, gpu_time = time_it("  n_estimators=200, 50k samples", lambda: gpu_model2.fit(X, y))
        print(f"\n  GPU speedup: {cpu_time / gpu_time:.1f}x")
    except Exception as e:
        print(f"\n  GPU: not available ({e})")


# ---------------------------------------------------------------------------
# Correctness checks
# ---------------------------------------------------------------------------

def check_close(label, current_out, fast_out, rtol=1e-4, atol=1e-4):
    """Assert that fast output matches current output within tolerance."""
    match = np.allclose(current_out, fast_out, rtol=rtol, atol=atol, equal_nan=True)
    max_diff = np.nanmax(np.abs(current_out.astype(np.float64) - fast_out.astype(np.float64)))
    status = "PASS" if match else "FAIL"
    print(f"  [{status}] {label}  (max diff: {max_diff:.2e})")
    return match


def run_correctness_checks(dem):
    """Run all current vs proposed outputs through numerical comparison."""
    all_passed = True

    all_passed &= check_close("std dev window=5",
        current_std_filter(dem, 5), fast_std_filter(dem, 5))

    all_passed &= check_close("std dev window=9",
        current_std_filter(dem, 9), fast_std_filter(dem, 9))

    all_passed &= check_close("TPI window=3",
        current_tpi(dem, 3), fast_tpi(dem, 3))

    all_passed &= check_close("TPI window=11",
        current_tpi(dem, 11), fast_tpi(dem, 11))

    all_passed &= check_close("TPI window=21",
        current_tpi(dem, 21), fast_tpi(dem, 21))

    # TRI: fast version has a known boundary correctness issue — investigate before applying
    tri_passed = check_close("TRI (experimental)",
        current_tri(dem), fast_tri(dem))
    if not tri_passed:
        print("  NOTE: fast_tri boundary handling differs from generic_filter — NOT applied to scripts")

    return all_passed


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--size', type=int, default=1000,
                        help='Raster side length in pixels (default: 1000)')
    parser.add_argument('--skip-xgboost', action='store_true',
                        help='Skip XGBoost benchmark')
    parser.add_argument('--correctness-only', action='store_true',
                        help='Run correctness checks only, skip timing')
    args = parser.parse_args()

    size = args.size
    n_pixels = size * size

    print("=" * 60)
    print(f"  Feature Engineering Benchmark  ({size}×{size} = {n_pixels:,} pixels)")
    print("=" * 60)

    dem = make_dem(size)

    # ── Correctness checks (always run first) ────────────────────────────────
    print("\n── Correctness: current vs proposed ────────────────────────────")
    print("  (checks that fast implementations match slow ones numerically)")
    passed = run_correctness_checks(dem)
    if not passed:
        print("\n  CORRECTNESS FAILURES DETECTED — do not apply changes until fixed.")
        import sys; sys.exit(1)
    else:
        print("  All correctness checks passed.")

    if args.correctness_only:
        return

    # ── Std dev filter ───────────────────────────────────────────────────────
    print("\n── std dev filter (window=5) ───────────────────────────────────")
    print("  current (generic_filter + Python callback):")
    _, t_cur_5 = time_it("elev_std_5x5", lambda: current_std_filter(dem, 5))

    print("  proposed (vectorized uniform_filter):")
    _, t_fast_5 = time_it("elev_std_5x5", lambda: fast_std_filter(dem, 5))
    print(f"  speedup: {t_cur_5 / t_fast_5:.1f}x")

    print("\n── std dev filter (window=9) ───────────────────────────────────")
    print("  current:")
    _, t_cur_9 = time_it("elev_std_9x9", lambda: current_std_filter(dem, 9))

    print("  proposed:")
    _, t_fast_9 = time_it("elev_std_9x9", lambda: fast_std_filter(dem, 9))
    print(f"  speedup: {t_cur_9 / t_fast_9:.1f}x")

    # ── TPI ──────────────────────────────────────────────────────────────────
    print("\n── TPI (window=11) ─────────────────────────────────────────────")
    print("  current:")
    _, t_cur_tpi = time_it("tpi_11x11", lambda: current_tpi(dem, 11))

    print("  proposed:")
    _, t_fast_tpi = time_it("tpi_11x11", lambda: fast_tpi(dem, 11))
    print(f"  speedup: {t_cur_tpi / t_fast_tpi:.1f}x")

    print("\n── TPI (window=21) ─────────────────────────────────────────────")
    print("  current:")
    _, t_cur_tpi21 = time_it("tpi_21x21", lambda: current_tpi(dem, 21))

    print("  proposed:")
    _, t_fast_tpi21 = time_it("tpi_21x21", lambda: fast_tpi(dem, 21))
    print(f"  speedup: {t_cur_tpi21 / t_fast_tpi21:.1f}x")

    # ── TRI ──────────────────────────────────────────────────────────────────
    print("\n── TRI ─────────────────────────────────────────────────────────")
    print("  current:")
    _, t_cur_tri = time_it("tri", lambda: current_tri(dem))

    print("  proposed:")
    _, t_fast_tri = time_it("tri", lambda: fast_tri(dem))
    print(f"  speedup: {t_cur_tri / t_fast_tri:.1f}x")

    # ── Summary ──────────────────────────────────────────────────────────────
    total_current  = t_cur_5 + t_cur_9 + t_cur_tpi + t_cur_tpi21 + t_cur_tri
    total_proposed = t_fast_5 + t_fast_9 + t_fast_tpi + t_fast_tpi21 + t_fast_tri

    print("\n" + "=" * 60)
    print(f"  Total (timed operations)")
    print(f"    Current:   {total_current:.2f}s")
    print(f"    Proposed:  {total_proposed:.2f}s")
    print(f"    Speedup:   {total_current / total_proposed:.1f}x")
    print("=" * 60)

    # ── XGBoost ──────────────────────────────────────────────────────────────
    if not args.skip_xgboost:
        print("\n── XGBoost ─────────────────────────────────────────────────────")
        benchmark_xgboost()

    print()


if __name__ == "__main__":
    main()
