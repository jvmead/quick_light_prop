"""
Geometry Comparison - Compare gap vs no-gap configurations with FIXED physics.

This answers the DESIGN QUESTION: Does the LAr gap affect performance?

Uses FIXED physics (full realistic model) and compares:
1. With LAr gap (1mm spacing between LC and WLS)
2. Without LAr gap (LC directly adjacent to WLS)
"""

import numpy as np
import matplotlib.pyplot as plt
from pathlib import Path
import sys
from typing import List, Tuple
import pandas as pd

sys.path.insert(0, str(Path(__file__).parent.parent))

from photon_tracer import Cuboid, PhotonSimulation
from photon_tracer.simulation import SimulationConfig

plt.ioff()


def create_geometry_with_gap() -> Tuple[List[Cuboid], np.ndarray, np.ndarray]:
    """Create detector geometry WITH LAr gap."""

    width = 0.5
    height = 0.5
    lc_x = 1e-2
    lar_gap_x = 1e-3  # 1mm gap
    wls_x = 3e-6
    dm_x = 112e-6
    bulk_x = 0.5

    x_pos = 0.0

    # LC
    lc_min = np.array([x_pos, 0, 0])
    lc_max = np.array([x_pos + lc_x, height, width])
    x_pos += lc_x

    # LAr Gap
    gap_min = np.array([x_pos, 0, 0])
    gap_max = np.array([x_pos + lar_gap_x, height, width])
    x_pos += lar_gap_x

    # WLS
    wls_min = np.array([x_pos, 0, 0])
    wls_max = np.array([x_pos + wls_x, height, width])
    x_pos += wls_x

    # DM
    dm_min = np.array([x_pos, 0, 0])
    dm_max = np.array([x_pos + dm_x, height, width])
    x_pos += dm_x

    # Bulk
    bulk_min = np.array([x_pos, 0, 0])
    bulk_max = np.array([x_pos + bulk_x, height, width])

    # Source at FAR END of bulk
    source_position = np.array([bulk_max[0], height/2, width/2])

    # Sensors on LC face
    n_sipms = 6
    sensor_positions = np.array([
        [lc_x/2, (1 + 2*i)/(2*n_sipms) * height, 0.0]
        for i in range(n_sipms)
    ])

    # Material properties (FIXED: realistic physics)
    mu_a_lc = {128.0: 0.0, 420.0: 20.0, 490.0: 0.2}
    mu_a_tpb = {128.0: 5e5, 420.0: 10.0, 490.0: 1.0}
    dm_reflectance = {128.0: 0.2, 420.0: 0.95, 490.0: 0.10}

    # Create volumes
    lc = Cuboid(
        lc_min, lc_max,
        refractive_index={128: 1.65, 420: 1.60, 490: 1.58},
        name="lc",
        wls=True,
        mu_a=mu_a_lc,
        quantum_yield=0.95,
        emission_peak_nm=490.0,
        emission_sigma_nm=20.0,
    )

    gap = Cuboid(
        gap_min, gap_max,
        refractive_index={128: 1.6, 420: 1.23, 490: 1.22},
        name="lar_gap",
        wls=False,
    )

    wls = Cuboid(
        wls_min, wls_max,
        refractive_index={128: 1.70, 420: 1.62, 490: 1.60},
        name="wls",
        wls=True,
        mu_a=mu_a_tpb,
        quantum_yield=0.9,
        emission_peak_nm=420.0,
        emission_sigma_nm=15.0,
    )

    dm = Cuboid(
        dm_min, dm_max,
        refractive_index={128: 1.5, 420: 1.65, 490: 1.9},
        name="dm",
        wls=False,
        is_dichroic=True,
        reflectance=dm_reflectance,
    )

    bulk = Cuboid(
        bulk_min, bulk_max,
        refractive_index={128: 1.6, 420: 1.23, 490: 1.22},
        name="bulk",
        wls=False,
    )

    volumes = [lc, gap, wls, dm, bulk]

    return volumes, source_position, sensor_positions


def create_geometry_no_gap() -> Tuple[List[Cuboid], np.ndarray, np.ndarray]:
    """Create detector geometry WITHOUT LAr gap."""

    width = 0.5
    height = 0.5
    lc_x = 1e-2
    # NO GAP
    wls_x = 3e-6
    dm_x = 112e-6
    bulk_x = 0.5

    x_pos = 0.0

    # LC
    lc_min = np.array([x_pos, 0, 0])
    lc_max = np.array([x_pos + lc_x, height, width])
    x_pos += lc_x

    # NO GAP - WLS directly adjacent to LC

    # WLS
    wls_min = np.array([x_pos, 0, 0])
    wls_max = np.array([x_pos + wls_x, height, width])
    x_pos += wls_x

    # DM
    dm_min = np.array([x_pos, 0, 0])
    dm_max = np.array([x_pos + dm_x, height, width])
    x_pos += dm_x

    # Bulk
    bulk_min = np.array([x_pos, 0, 0])
    bulk_max = np.array([x_pos + bulk_x, height, width])

    # Source at FAR END of bulk
    source_position = np.array([bulk_max[0], height/2, width/2])

    # Sensors on LC face
    n_sipms = 6
    sensor_positions = np.array([
        [lc_x/2, (1 + 2*i)/(2*n_sipms) * height, 0.0]
        for i in range(n_sipms)
    ])

    # Material properties (FIXED: same as with-gap case)
    mu_a_lc = {128.0: 0.0, 420.0: 20.0, 490.0: 0.2}
    mu_a_tpb = {128.0: 5e5, 420.0: 10.0, 490.0: 1.0}
    dm_reflectance = {128.0: 0.2, 420.0: 0.95, 490.0: 0.10}

    # Create volumes (SAME physics as with-gap)
    lc = Cuboid(
        lc_min, lc_max,
        refractive_index={128: 1.65, 420: 1.60, 490: 1.58},
        name="lc",
        wls=True,
        mu_a=mu_a_lc,
        quantum_yield=0.95,
        emission_peak_nm=490.0,
        emission_sigma_nm=20.0,
    )

    wls = Cuboid(
        wls_min, wls_max,
        refractive_index={128: 1.70, 420: 1.62, 490: 1.60},
        name="wls",
        wls=True,
        mu_a=mu_a_tpb,
        quantum_yield=0.9,
        emission_peak_nm=420.0,
        emission_sigma_nm=15.0,
    )

    dm = Cuboid(
        dm_min, dm_max,
        refractive_index={128: 1.5, 420: 1.65, 490: 1.9},
        name="dm",
        wls=False,
        is_dichroic=True,
        reflectance=dm_reflectance,
    )

    bulk = Cuboid(
        bulk_min, bulk_max,
        refractive_index={128: 1.6, 420: 1.23, 490: 1.22},
        name="bulk",
        wls=False,
    )

    volumes = [lc, wls, dm, bulk]  # NO gap volume

    return volumes, source_position, sensor_positions


def run_simulation(name: str, volumes, src, sens, n_photons=50000, max_thrown=500000):
    """Run simulation and return results."""
    print(f"  Running: {name}...")

    config = SimulationConfig(
        num_photons=n_photons,
        max_thrown=max_thrown,
        max_steps=5000,
        max_workers=8,
        initial_wavelength_nm=128.0,
        rng_seed=42,  # SAME seed for fair comparison
    )

    sim = PhotonSimulation(
        volumes=volumes,
        source_position=src,
        sensor_positions=sens,
        sensor_radius=0.01,
        config=config,
    )

    df = sim.run(verbose=True)
    df['geometry'] = name

    return df


def main():
    print("="*70)
    print("Geometry Comparison: Gap vs No-Gap")
    print("="*70)
    print("\nPhysics: FIXED (realistic model)")
    print("Testing: Impact of LAr gap on performance\n")

    results = {}

    # 1. With gap
    print("1. With LAr Gap (1mm spacing)")
    print("-" * 70)
    volumes, src, sens = create_geometry_with_gap()
    results['with_gap'] = run_simulation("With Gap", volumes, src, sens)

    # 2. Without gap
    print("\n2. Without LAr Gap (LC adjacent to WLS)")
    print("-" * 70)
    volumes, src, sens = create_geometry_no_gap()
    results['no_gap'] = run_simulation("No Gap", volumes, src, sens)

    # Save combined results
    print("\n" + "="*70)
    print("Saving Results")
    print("="*70)

    Path('results').mkdir(exist_ok=True)
    all_df = pd.concat(results.values(), ignore_index=True)
    all_df.to_csv('results/geometry_comparison.csv', index=False)
    print("  Saved: results/geometry_comparison.csv")

    # Generate comparison plots
    print("\n" + "="*70)
    print("Generating Comparison Plots")
    print("="*70)

    Path('results/plots').mkdir(exist_ok=True, parents=True)

    # 1. Efficiency comparison
    fig, ax = plt.subplots(figsize=(10, 6))

    configs = []
    effs = []

    for key, df in results.items():
        geom_name = df['geometry'].iloc[0]
        n_arrived = (df['event_type'] == 'arrived').sum()
        eff = 100 * n_arrived / len(df)
        configs.append(geom_name)
        effs.append(eff)

    bars = ax.bar(configs, effs, color=['steelblue', 'coral'], alpha=0.7, edgecolor='black', linewidth=2)
    ax.set_ylabel('Detection Efficiency (%)', fontsize=12, fontweight='bold')
    ax.set_title('Geometry Comparison: Impact of LAr Gap', fontsize=14, fontweight='bold')
    ax.grid(axis='y', alpha=0.3)

    # Add values on bars
    for bar, eff in zip(bars, effs):
        height = bar.get_height()
        ax.text(bar.get_x() + bar.get_width()/2, height + max(effs)*0.01,
                f'{eff:.3f}%', ha='center', va='bottom', fontsize=12, fontweight='bold')

    plt.tight_layout()
    plt.savefig('results/plots/geometry_comparison.png', dpi=150, bbox_inches='tight')
    plt.close()
    print("  Saved: results/plots/geometry_comparison.png")

    # 2. Event type comparison
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(16, 6))

    for ax, (key, df) in zip([ax1, ax2], results.items()):
        geom_name = df['geometry'].iloc[0]
        event_counts = df['event_type'].value_counts().head(10)

        ax.barh(range(len(event_counts)), event_counts.values, color='steelblue', alpha=0.7, edgecolor='black')
        ax.set_yticks(range(len(event_counts)))
        ax.set_yticklabels(event_counts.index, fontsize=9)
        ax.set_xlabel('Count', fontsize=11)
        ax.set_title(f'{geom_name}', fontsize=12, fontweight='bold')
        ax.set_xscale('log')
        ax.grid(axis='x', alpha=0.3)

        # Add counts as text
        for i, (event, count) in enumerate(event_counts.items()):
            ax.text(count * 1.1, i, f'{count}', va='center', fontsize=9)

    plt.suptitle('Event Type Distribution by Geometry', fontsize=14, fontweight='bold')
    plt.tight_layout()
    plt.savefig('results/plots/event_distribution_comparison.png', dpi=150, bbox_inches='tight')
    plt.close()
    print("  Saved: results/plots/event_distribution_comparison.png")

    # Print summary
    print("\n" + "="*70)
    print("Summary")
    print("="*70)
    print("\nEfficiency Comparison:")
    for (key, df), eff in zip(results.items(), effs):
        geom_name = df['geometry'].iloc[0]
        n_arrived = (df['event_type'] == 'arrived').sum()
        n_total = len(df)
        print(f"  {geom_name}: {eff:.3f}% ({n_arrived}/{n_total})")

    print("\n✅ Geometry comparison complete!")
    print("Results saved to results/")


if __name__ == "__main__":
    main()
