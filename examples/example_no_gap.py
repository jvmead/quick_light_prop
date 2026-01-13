"""
Example simulation without LAr gap (LC directly adjacent to WLS).

This script replicates the photon_sim_analytic_no_gap_new notebook
with a clean, modular implementation.
"""

import numpy as np
import matplotlib.pyplot as plt
from pathlib import Path
import sys

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from photon_tracer import Cuboid, PhotonSimulation
from photon_tracer.simulation import SimulationConfig
from photon_tracer.analysis import (
    plot_geometry_3d,
    plot_trajectories,
    plot_event_statistics,
    plot_path_length_distribution,
    compute_geometric_efficiency,
)


def main():
    """Run photon simulation without LAr gap configuration."""

    print("="*60)
    print("Photon Tracing Simulation - No LAr Gap")
    print("="*60)

    # =============================
    # Geometry Configuration
    # =============================
    width = 0.5   # meters
    height = 0.5  # meters

    # Layer thicknesses (no gap)
    lc_x = 1e-2       # Light collection region
    wls_x = 3e-6      # Wavelength shifter (TPB)
    dm_x = 112e-6     # Dichroic mirror
    bulk_x = 0.5      # Bulk LAr

    # Build geometry layer by layer along x-axis
    x_pos = 0.0

    # Light Collection region (EJ280)
    lc_min = np.array([x_pos, 0, 0])
    lc_max = np.array([x_pos + lc_x, height, width])
    x_pos += lc_x

    # WLS (TPB) - directly adjacent to LC
    wls_min = np.array([x_pos, 0, 0])
    wls_max = np.array([x_pos + wls_x, height, width])
    x_pos += wls_x

    # Dichroic Mirror
    dm_min = np.array([x_pos, 0, 0])
    dm_max = np.array([x_pos + dm_x, height, width])
    x_pos += dm_x

    # Bulk LAr
    bulk_min = np.array([x_pos, 0, 0])
    bulk_max = np.array([x_pos + bulk_x, height, width])

    # Source at far end of bulk
    source_position = np.array([bulk_max[0], height/2, width/2])

    # Sensors on LC face
    n_sipms = 6
    sensor_positions = np.array([
        [lc_x/2, (1 + 2*i)/(2*n_sipms) * height, 0.0]
        for i in range(n_sipms)
    ])

    # =============================
    # Material Properties
    # =============================

    # EJ280 (LC) properties
    mu_a_lc = {
        128.0: 0.0,    # No VUV absorption
        420.0: 20.0,   # ~5 cm absorption length
        490.0: 0.2,    # Transparent at emission
    }

    # TPB (WLS) properties
    mu_a_tpb = {
        128.0: 5e5,    # Strong VUV absorption
        420.0: 10.0,   # Transparent to blue
        490.0: 1.0,    # Transparent to green
    }

    # Dichroic mirror reflectance
    dm_reflectance = {
        128.0: 0.2,    # Low VUV reflectance
        420.0: 0.95,   # High blue reflectance
        490.0: 0.10,   # Low green reflectance (transmit)
    }

    # =============================
    # Create Volumes
    # =============================

    lc = Cuboid(
        min_point=lc_min,
        max_point=lc_max,
        refractive_index={128: 1.65, 420: 1.60, 490: 1.58},
        name="lc",
        wls=True,
        mu_a=mu_a_lc,
        quantum_yield=0.95,
        emission_peak_nm=490.0,
        emission_sigma_nm=20.0,
    )

    wls = Cuboid(
        min_point=wls_min,
        max_point=wls_max,
        refractive_index={128: 1.70, 420: 1.62, 490: 1.60},
        name="wls",
        wls=True,
        mu_a=mu_a_tpb,
        quantum_yield=0.9,
        emission_peak_nm=420.0,
        emission_sigma_nm=15.0,
    )

    dm = Cuboid(
        min_point=dm_min,
        max_point=dm_max,
        refractive_index={128: 1.5, 420: 1.65, 490: 1.9},
        name="dm",
        wls=False,
        is_dichroic=True,
        reflectance=dm_reflectance,
    )

    bulk = Cuboid(
        min_point=bulk_min,
        max_point=bulk_max,
        refractive_index={128: 1.6, 420: 1.23, 490: 1.22},
        name="bulk",
        wls=False,
    )

    volumes = [lc, wls, dm, bulk]

    # =============================
    # Visualize Geometry
    # =============================
    print("\n1. Visualizing geometry...")
    fig = plt.figure(figsize=(10, 8))
    ax = fig.add_subplot(111, projection='3d')
    plot_geometry_3d(volumes, source_position, sensor_positions, ax=ax)
    ax.set_title("Detector Geometry - No LAr Gap")
    plt.tight_layout()
    plt.savefig("geometry_no_gap.png", dpi=150)
    print("   Saved: geometry_no_gap.png")

    # =============================
    # Run Simulation
    # =============================
    print("\n2. Running photon simulation...")

    config = SimulationConfig(
        num_photons=50000,
        max_thrown=500000,
        max_steps=5000,
        max_workers=8,
        initial_wavelength_nm=128.0,  # LAr scintillation
        rng_seed=12345,
    )

    sim = PhotonSimulation(
        volumes=volumes,
        source_position=source_position,
        sensor_positions=sensor_positions,
        sensor_radius=0.01,  # 1 cm sensor radius
        config=config,
    )

    df = sim.run(verbose=True)

    # Save results
    df.to_csv("results_no_gap.csv", index=False)
    print("   Saved: results_no_gap.csv")

    # =============================
    # Compute Efficiency
    # =============================
    print("\n3. Computing detection efficiency...")

    n_arrived = (df['event_type'] == 'arrived').sum()
    raw_efficiency = 100.0 * n_arrived / len(df)

    # Compute solid angle correction
    solid_angle, geom_frac = compute_geometric_efficiency(
        source_position=source_position,
        target_cuboid=dm,
        target_face="xmax"  # DM face closest to source
    )

    corrected_efficiency = raw_efficiency / geom_frac if geom_frac > 0 else 0

    print(f"\n   Raw efficiency: {raw_efficiency:.3f}%")
    print(f"   Solid angle: {solid_angle:.6f} sr")
    print(f"   Geometric fraction: {geom_frac:.6e}")
    print(f"   Corrected efficiency: {corrected_efficiency:.2f}%")

    # =============================
    # Generate Plots
    # =============================
    print("\n4. Generating analysis plots...")

    # Event statistics
    fig = plot_event_statistics(df, figsize=(15, 5))
    plt.savefig("statistics_no_gap.png", dpi=150)
    print("   Saved: statistics_no_gap.png")
    plt.close()

    # Path length distribution
    fig = plot_path_length_distribution(df, figsize=(10, 6))
    plt.savefig("path_lengths_no_gap.png", dpi=150)
    print("   Saved: path_lengths_no_gap.png")
    plt.close()

    # Trajectories (arrived photons)
    fig = plot_trajectories(
        df[df['event_type'] == 'arrived'],
        volumes,
        event_types=['arrived'],
        max_per_type=100,
        alpha=0.6,
        figsize=(12, 10)
    )
    plt.savefig("trajectories_arrived_no_gap.png", dpi=150)
    print("   Saved: trajectories_arrived_no_gap.png")
    plt.close()

    # Trajectories (lost photons - sample)
    lost_types = [et for et in df['event_type'].unique() if 'lost' in et]
    if lost_types:
        fig = plot_trajectories(
            df,
            volumes,
            event_types=lost_types[:3],  # Show first 3 loss types
            max_per_type=50,
            alpha=0.4,
            figsize=(12, 10)
        )
        plt.savefig("trajectories_lost_no_gap.png", dpi=150)
        print("   Saved: trajectories_lost_no_gap.png")
        plt.close()

    print("\n" + "="*60)
    print("Simulation complete!")
    print("="*60)

    # =============================
    # Comparison Note
    # =============================
    print("\nNote: This configuration has no LAr gap between LC and WLS.")
    print("Compare with example_with_gap.py to see the effect of the gap.")


if __name__ == "__main__":
    main()
