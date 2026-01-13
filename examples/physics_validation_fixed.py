"""
Physics validation: Test impact of model assumptions.

This tests the physics MODEL, not design choices.
Design choices (gap vs no-gap) should be in the main example scripts.

Tests:
1. Baseline (full physics)
2. No WLS absorption (transparent materials)
3. No dichroic (transparent mirror)
4. Perfect quantum yields (QY=1.0)
5. Poor quantum yields (QY=0.5)
6. No refractive index dispersion (constant n)
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


def create_geometry(
    wls_absorption: bool = True,
    dichroic_enabled: bool = True,
    lc_qy: float = 0.95,
    wls_qy: float = 0.9,
    dispersion: bool = True,
) -> Tuple[List[Cuboid], np.ndarray, np.ndarray]:
    """Create detector geometry with configurable physics."""

    width = 0.5
    height = 0.5
    lc_x = 1e-2
    wls_x = 3e-6
    dm_x = 112e-6
    bulk_x = 0.5  # THICKNESS of bulk

    # Build geometry step by step
    x_pos = 0.0

    # LC
    lc_min = np.array([x_pos, 0, 0])
    lc_max = np.array([x_pos + lc_x, height, width])
    x_pos += lc_x

    # WLS
    wls_min = np.array([x_pos, 0, 0])
    wls_max = np.array([x_pos + wls_x, height, width])
    x_pos += wls_x

    # DM
    dm_min = np.array([x_pos, 0, 0])
    dm_max = np.array([x_pos + dm_x, height, width])
    x_pos += dm_x

    # Bulk (FIXED: use x_pos + bulk_x, not just bulk_x!)
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

    # Material properties
    if dispersion:
        n_lc = {128: 1.65, 420: 1.60, 490: 1.58}
        n_wls_mat = {128: 1.70, 420: 1.62, 490: 1.60}
        n_dm = {128: 1.5, 420: 1.65, 490: 1.9}
        n_bulk = {128: 1.6, 420: 1.23, 490: 1.22}
    else:
        # Constant n (average values)
        n_lc = 1.61
        n_wls_mat = 1.64
        n_dm = 1.68
        n_bulk = 1.34

    # Absorption coefficients
    if wls_absorption:
        mu_a_lc = {128.0: 0.0, 420.0: 20.0, 490.0: 0.2}
        mu_a_tpb = {128.0: 5e5, 420.0: 10.0, 490.0: 1.0}
    else:
        mu_a_lc = 0.0
        mu_a_tpb = 0.0

    # Dichroic reflectance
    if dichroic_enabled:
        dm_reflectance = {128.0: 0.2, 420.0: 0.95, 490.0: 0.10}
    else:
        dm_reflectance = 0.0

    # Create volumes
    lc = Cuboid(
        lc_min, lc_max,
        refractive_index=n_lc,
        name="lc",
        wls=wls_absorption,
        mu_a=mu_a_lc,
        quantum_yield=lc_qy,
        emission_peak_nm=490.0,
        emission_sigma_nm=20.0,
    )

    wls = Cuboid(
        wls_min, wls_max,
        refractive_index=n_wls_mat,
        name="wls",
        wls=wls_absorption,
        mu_a=mu_a_tpb,
        quantum_yield=wls_qy,
        emission_peak_nm=420.0,
        emission_sigma_nm=15.0,
    )

    dm = Cuboid(
        dm_min, dm_max,
        refractive_index=n_dm,
        name="dm",
        wls=False,
        is_dichroic=dichroic_enabled,
        reflectance=dm_reflectance,
    )

    bulk = Cuboid(
        bulk_min, bulk_max,
        refractive_index=n_bulk,
        name="bulk",
        wls=False,
    )

    volumes = [lc, wls, dm, bulk]

    return volumes, source_position, sensor_positions


def run_test(name: str, volumes, src, sens, n_photons=1000, max_thrown=20000):
    """Run simulation and return results."""
    print(f"  Running: {name}...")

    config = SimulationConfig(
        num_photons=n_photons,
        max_thrown=max_thrown,
        max_steps=5000,
        max_workers=8,
        initial_wavelength_nm=128.0,
        rng_seed=42,
    )

    sim = PhotonSimulation(
        volumes=volumes,
        source_position=src,
        sensor_positions=sens,
        sensor_radius=0.01,
        config=config,
    )

    df = sim.run(verbose=False)
    df['config'] = name

    n_arrived = (df['event_type'] == 'arrived').sum()
    efficiency = 100.0 * n_arrived / len(df)

    print(f"    → Efficiency: {efficiency:.3f}% ({n_arrived} / {len(df)})")

    return df


def main():
    print("="*70)
    print("Physics Model Validation")
    print("="*70)
    print("\nTesting impact of physics approximations on detector performance")

    results = {}

    # 1. Baseline (full physics)
    print("\n1. Baseline Configuration")
    print("-" * 70)
    volumes, src, sens = create_geometry(
        wls_absorption=True,
        dichroic_enabled=True,
        lc_qy=0.95,
        wls_qy=0.9,
        dispersion=True,
    )
    results['baseline'] = run_test("Baseline (Full Physics)", volumes, src, sens)

    # 2. No WLS absorption
    print("\n2. No WLS Absorption (Transparent Materials)")
    print("-" * 70)
    volumes, src, sens = create_geometry(
        wls_absorption=False,
        dichroic_enabled=True,
        lc_qy=0.95,
        wls_qy=0.9,
        dispersion=True,
    )
    results['no_wls'] = run_test("No WLS Absorption", volumes, src, sens)

    # 3. No dichroic
    print("\n3. No Dichroic Reflectance (Transparent Mirror)")
    print("-" * 70)
    volumes, src, sens = create_geometry(
        wls_absorption=True,
        dichroic_enabled=False,
        lc_qy=0.95,
        wls_qy=0.9,
        dispersion=True,
    )
    results['no_dichroic'] = run_test("No Dichroic", volumes, src, sens)

    # 4. Perfect QY
    print("\n4. Perfect Quantum Yields (QY = 1.0)")
    print("-" * 70)
    volumes, src, sens = create_geometry(
        wls_absorption=True,
        dichroic_enabled=True,
        lc_qy=1.0,
        wls_qy=1.0,
        dispersion=True,
    )
    results['perfect_qy'] = run_test("Perfect QY", volumes, src, sens)

    # 5. Poor QY
    print("\n5. Poor Quantum Yields (QY = 0.5)")
    print("-" * 70)
    volumes, src, sens = create_geometry(
        wls_absorption=True,
        dichroic_enabled=True,
        lc_qy=0.5,
        wls_qy=0.5,
        dispersion=True,
    )
    results['poor_qy'] = run_test("Poor QY", volumes, src, sens)

    # 6. No dispersion
    print("\n6. No Refractive Index Dispersion (Constant n)")
    print("-" * 70)
    volumes, src, sens = create_geometry(
        wls_absorption=True,
        dichroic_enabled=True,
        lc_qy=0.95,
        wls_qy=0.9,
        dispersion=False,
    )
    results['no_dispersion'] = run_test("No Dispersion", volumes, src, sens)

    # Generate comparison plots
    print("\n" + "="*70)
    print("Generating Comparison Plots")
    print("="*70)

    plot_comparison(results)

    print("\n✅ Physics validation complete!")
    print("Results saved to docs/validation/")


def plot_comparison(results):
    """Generate comparison plots."""

    # Create output directory
    Path('docs/validation').mkdir(exist_ok=True, parents=True)

    # 1. Efficiency comparison
    print("  1/2 Efficiency comparison...")
    fig, ax = plt.subplots(figsize=(12, 6))

    configs = []
    effs = []
    colors_list = []

    color_map = {
        'baseline': 'green',
        'no_wls': 'red',
        'no_dichroic': 'orange',
        'perfect_qy': 'blue',
        'poor_qy': 'purple',
        'no_dispersion': 'brown',
    }

    for key, df in results.items():
        config_name = df['config'].iloc[0]
        eff = 100 * ((df['event_type'] == 'arrived').sum() / len(df))
        configs.append(config_name)
        effs.append(eff)
        colors_list.append(color_map.get(key, 'gray'))

    # Sort by efficiency
    sorted_indices = np.argsort(effs)[::-1]
    configs = [configs[i] for i in sorted_indices]
    effs = [effs[i] for i in sorted_indices]
    colors_list = [colors_list[i] for i in sorted_indices]

    bars = ax.barh(configs, effs, color=colors_list, alpha=0.7, edgecolor='black', linewidth=1.5)
    ax.set_xlabel('Detection Efficiency (%)', fontsize=12, fontweight='bold')
    ax.set_title('Physics Model Comparison: Impact on Efficiency', fontsize=14, fontweight='bold')
    ax.grid(axis='x', alpha=0.3)

    # Add values
    for bar, eff in zip(bars, effs):
        width = bar.get_width()
        ax.text(width + 0.01, bar.get_y() + bar.get_height()/2,
                f'{eff:.3f}%', ha='left', va='center', fontsize=10, fontweight='bold')

    plt.tight_layout()
    plt.savefig('docs/validation/physics_model_comparison.png', dpi=150, bbox_inches='tight')
    plt.close()

    # 2. Event type breakdown
    print("  2/2 Event type breakdown...")
    fig, axes = plt.subplots(2, 3, figsize=(16, 10))
    axes = axes.flatten()

    for idx, (key, df) in enumerate(results.items()):
        ax = axes[idx]
        config_name = df['config'].iloc[0]

        # Count events
        event_counts = df['event_type'].value_counts()

        # Plot
        ax.bar(range(len(event_counts)), event_counts.values,
               color=color_map.get(key, 'gray'), alpha=0.7, edgecolor='black')
        ax.set_xticks(range(len(event_counts)))
        ax.set_xticklabels([e.replace('_', '\n') for e in event_counts.index],
                          rotation=45, ha='right', fontsize=8)
        ax.set_ylabel('Count', fontsize=10)
        ax.set_title(config_name, fontweight='bold', fontsize=11)
        ax.set_yscale('log')
        ax.grid(axis='y', alpha=0.3)

    plt.suptitle('Event Type Distribution by Physics Model', fontsize=14, fontweight='bold')
    plt.tight_layout()
    plt.savefig('docs/validation/event_types_comparison.png', dpi=150, bbox_inches='tight')
    plt.close()


if __name__ == "__main__":
    main()
