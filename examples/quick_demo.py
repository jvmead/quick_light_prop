"""
Quick demo for generating README plots (reduced photon count for speed).
"""

import numpy as np
import matplotlib.pyplot as plt
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))

from photon_tracer import Cuboid, PhotonSimulation
from photon_tracer.simulation import SimulationConfig
from photon_tracer.analysis import (
    plot_geometry_3d,
    plot_trajectories,
    plot_event_statistics,
    plot_path_length_distribution,
)

# Suppress matplotlib display (save only)
plt.ioff()

def main():
    print("Generating example plots for README...")

    # Simplified geometry
    width = 0.5
    height = 0.5
    lc_x = 1e-2
    lar_gap_x = 1e-3
    wls_x = 3e-6
    dm_x = 112e-6
    bulk_x = 0.5

    x_pos = 0.0
    lc_min = np.array([x_pos, 0, 0])
    lc_max = np.array([x_pos + lc_x, height, width])
    x_pos += lc_x

    gap_min = np.array([x_pos, 0, 0])
    gap_max = np.array([x_pos + lar_gap_x, height, width])
    x_pos += lar_gap_x

    wls_min = np.array([x_pos, 0, 0])
    wls_max = np.array([x_pos + wls_x, height, width])
    x_pos += wls_x

    dm_min = np.array([x_pos, 0, 0])
    dm_max = np.array([x_pos + dm_x, height, width])
    x_pos += dm_x

    bulk_min = np.array([x_pos, 0, 0])
    bulk_max = np.array([x_pos + bulk_x, height, width])

    source_position = np.array([bulk_max[0], height/2, width/2])

    n_sipms = 6
    sensor_positions = np.array([
        [lc_x/2, (1 + 2*i)/(2*n_sipms) * height, 0.0]
        for i in range(n_sipms)
    ])

    # Material properties
    mu_a_lc = {128.0: 0.0, 420.0: 20.0, 490.0: 0.2}
    mu_a_tpb = {128.0: 5e5, 420.0: 10.0, 490.0: 1.0}
    dm_reflectance = {128.0: 0.2, 420.0: 0.95, 490.0: 0.10}

    # Create volumes
    lc = Cuboid(lc_min, lc_max, refractive_index={128: 1.65, 420: 1.60, 490: 1.58},
                name="lc", wls=True, mu_a=mu_a_lc, quantum_yield=0.95,
                emission_peak_nm=490.0, emission_sigma_nm=20.0)

    lar_gap = Cuboid(gap_min, gap_max, refractive_index={128: 1.6, 420: 1.23, 490: 1.22},
                     name="lar_gap", wls=False)

    wls = Cuboid(wls_min, wls_max, refractive_index={128: 1.70, 420: 1.62, 490: 1.60},
                 name="wls", wls=True, mu_a=mu_a_tpb, quantum_yield=0.9,
                 emission_peak_nm=420.0, emission_sigma_nm=15.0)

    dm = Cuboid(dm_min, dm_max, refractive_index={128: 1.5, 420: 1.65, 490: 1.9},
                name="dm", wls=False, is_dichroic=True, reflectance=dm_reflectance)

    bulk = Cuboid(bulk_min, bulk_max, refractive_index={128: 1.6, 420: 1.23, 490: 1.22},
                  name="bulk", wls=False)

    volumes = [lc, lar_gap, wls, dm, bulk]

    # 1. Geometry plot
    print("  1/5 Plotting geometry...")
    fig = plt.figure(figsize=(10, 8))
    ax = fig.add_subplot(111, projection='3d')
    plot_geometry_3d(volumes, source_position, sensor_positions, ax=ax,
                     colors=['blue', 'cyan', 'red', 'orange', 'green'])
    ax.set_title("Multi-Layer Optical Detector Geometry", fontsize=14, fontweight='bold')
    ax.view_init(elev=20, azim=45)
    plt.tight_layout()
    plt.savefig("docs/geometry.png", dpi=150, bbox_inches='tight')
    plt.close()

    # Run quick simulation (fewer photons for speed)
    print("  2/5 Running simulation (10000 photons)...")
    config = SimulationConfig(
        num_photons=10000,
        max_thrown=100000,
        max_steps=5000,
        max_workers=8,
        initial_wavelength_nm=128.0,
        rng_seed=42,
    )

    sim = PhotonSimulation(
        volumes=volumes,
        source_position=source_position,
        sensor_positions=sensor_positions,
        sensor_radius=0.01,
        config=config,
    )

    df = sim.run(verbose=False)

    print(f"     Results: {(df['event_type']=='arrived').sum()} arrived / {len(df)} thrown")

    # 3. Event statistics
    print("  3/5 Plotting statistics...")
    fig = plot_event_statistics(df, figsize=(15, 5))
    plt.savefig("docs/statistics.png", dpi=150, bbox_inches='tight')
    plt.close()

    # 4. Path lengths
    print("  4/5 Plotting path lengths...")
    fig = plot_path_length_distribution(df, figsize=(10, 6))
    plt.savefig("docs/path_lengths.png", dpi=150, bbox_inches='tight')
    plt.close()

    # 5. Trajectories
    print("  5/5 Plotting trajectories...")
    arrived_df = df[df['event_type'] == 'arrived']
    if len(arrived_df) > 0:
        fig = plot_trajectories(
            arrived_df,
            volumes,
            event_types=['arrived'],
            max_per_type=200,
            alpha=0.5,
            figsize=(12, 10)
        )
        ax = fig.gca()
        ax.set_title("Successful Photon Trajectories (Arrived at Sensors)",
                     fontsize=14, fontweight='bold')
        ax.view_init(elev=20, azim=45)
        plt.savefig("docs/trajectories.png", dpi=150, bbox_inches='tight')
        plt.close()

    print("\n✅ All plots generated in docs/ directory!")

if __name__ == "__main__":
    main()
