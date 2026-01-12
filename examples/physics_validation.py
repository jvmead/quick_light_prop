"""
Physics validation and assumption testing.

This script runs controlled comparisons to validate physics models
and demonstrate the impact of key assumptions/approximations.
"""

import numpy as np
import matplotlib.pyplot as plt
from pathlib import Path
import sys
from typing import Dict, List, Tuple
import pandas as pd

sys.path.insert(0, str(Path(__file__).parent.parent))

from photon_tracer import Cuboid, PhotonSimulation
from photon_tracer.simulation import SimulationConfig
from photon_tracer.analysis import compute_geometric_efficiency

plt.ioff()  # Non-interactive mode


def create_base_geometry(
    include_gap: bool = True,
    dichroic_enabled: bool = True,
    dichroic_reflectance: Dict[float, float] = None,
    wls_enabled: bool = True,
    lc_qy: float = 0.95,
    wls_qy: float = 0.9,
    n_dispersion: bool = True,
) -> Tuple[List[Cuboid], np.ndarray, np.ndarray]:
    """
    Create detector geometry with configurable physics.

    Parameters
    ----------
    include_gap : bool
        Include LAr gap between LC and WLS
    dichroic_enabled : bool
        Enable wavelength-dependent dichroic reflectance
    dichroic_reflectance : dict
        Custom reflectance curve for DM
    wls_enabled : bool
        Enable wavelength shifting in WLS and LC
    lc_qy : float
        Light collection quantum yield
    wls_qy : float
        WLS (TPB) quantum yield
    n_dispersion : bool
        Use wavelength-dependent refractive indices

    Returns
    -------
    volumes, source_position, sensor_positions
    """
    width = 0.5
    height = 0.5
    lc_x = 1e-2
    lar_gap_x = 1e-3 if include_gap else 0.0
    wls_x = 3e-6
    dm_x = 112e-6
    bulk_x = 0.5

    # Build geometry
    x_pos = 0.0
    lc_min = np.array([x_pos, 0, 0])
    lc_max = np.array([x_pos + lc_x, height, width])
    x_pos += lc_x

    if include_gap:
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
    bulk_max = np.array([bulk_x, height, width])

    source_position = np.array([bulk_max[0], height/2, width/2])
    n_sipms = 6
    sensor_positions = np.array([
        [lc_x/2, (1 + 2*i)/(2*n_sipms) * height, 0.0]
        for i in range(n_sipms)
    ])

    # Material properties
    if n_dispersion:
        n_lc = {128: 1.65, 420: 1.60, 490: 1.58}
        n_gap = {128: 1.6, 420: 1.23, 490: 1.22}
        n_wls = {128: 1.70, 420: 1.62, 490: 1.60}
        n_dm = {128: 1.5, 420: 1.65, 490: 1.9}
        n_bulk = {128: 1.6, 420: 1.23, 490: 1.22}
    else:
        # Use average values (no dispersion)
        n_lc = 1.61
        n_gap = 1.34
        n_wls = 1.64
        n_dm = 1.68
        n_bulk = 1.34

    mu_a_lc = {128.0: 0.0, 420.0: 20.0, 490.0: 0.2} if wls_enabled else 0.0
    mu_a_tpb = {128.0: 5e5, 420.0: 10.0, 490.0: 1.0} if wls_enabled else 0.0

    if dichroic_reflectance is None:
        dm_reflectance = {128.0: 0.2, 420.0: 0.95, 490.0: 0.10}
    else:
        dm_reflectance = dichroic_reflectance

    # Create volumes
    lc = Cuboid(
        lc_min, lc_max,
        refractive_index=n_lc,
        name="lc",
        wls=wls_enabled,
        mu_a=mu_a_lc,
        quantum_yield=lc_qy,
        emission_peak_nm=490.0,
        emission_sigma_nm=20.0,
    )

    volumes = [lc]

    if include_gap:
        lar_gap = Cuboid(
            gap_min, gap_max,
            refractive_index=n_gap,
            name="lar_gap",
            wls=False,
        )
        volumes.append(lar_gap)

    wls = Cuboid(
        wls_min, wls_max,
        refractive_index=n_wls,
        name="wls",
        wls=wls_enabled,
        mu_a=mu_a_tpb,
        quantum_yield=wls_qy,
        emission_peak_nm=420.0,
        emission_sigma_nm=15.0,
    )
    volumes.append(wls)

    dm = Cuboid(
        dm_min, dm_max,
        refractive_index=n_dm,
        name="dm",
        wls=False,
        is_dichroic=dichroic_enabled,
        reflectance=dm_reflectance,
    )
    volumes.append(dm)

    bulk = Cuboid(
        bulk_min, bulk_max,
        refractive_index=n_bulk,
        name="bulk",
        wls=False,
    )
    volumes.append(bulk)

    return volumes, source_position, sensor_positions


def run_comparison(
    config_name: str,
    volumes: List[Cuboid],
    source_position: np.ndarray,
    sensor_positions: np.ndarray,
    n_photons: int = 2000,
    max_thrown: int = 20000,
) -> pd.DataFrame:
    """Run simulation and return results."""
    print(f"  Running: {config_name}...")

    config = SimulationConfig(
        num_photons=n_photons,
        max_thrown=max_thrown,
        max_steps=5000,
        max_workers=8,
        initial_wavelength_nm=128.0,
        rng_seed=42,  # Same seed for fair comparison
    )

    sim = PhotonSimulation(
        volumes=volumes,
        source_position=source_position,
        sensor_positions=sensor_positions,
        sensor_radius=0.01,
        config=config,
    )

    df = sim.run(verbose=False)

    # Add configuration identifier
    df['config'] = config_name

    n_arrived = (df['event_type'] == 'arrived').sum()
    print(f"    → {n_arrived} arrived / {len(df)} thrown")

    return df


def main():
    """Run physics validation comparisons."""
    print("="*70)
    print("Physics Validation & Assumption Testing")
    print("="*70)

    results = {}

    # =========================================================================
    # 1. Gap Comparison (Primary Design Question)
    # =========================================================================
    print("\n1. Gap Configuration Comparison")
    print("-" * 70)

    volumes_gap, src, sens = create_base_geometry(include_gap=True)
    df_gap = run_comparison("With Gap", volumes_gap, src, sens)
    results['with_gap'] = df_gap

    volumes_nogap, src, sens = create_base_geometry(include_gap=False)
    df_nogap = run_comparison("No Gap", volumes_nogap, src, sens)
    results['no_gap'] = df_nogap

    # =========================================================================
    # 2. Dichroic Mirror Assumptions
    # =========================================================================
    print("\n2. Dichroic Mirror Behavior")
    print("-" * 70)

    # Baseline (with dichroic)
    volumes_dm, src, sens = create_base_geometry(dichroic_enabled=True)
    df_dm_on = run_comparison("Dichroic ON", volumes_dm, src, sens)
    results['dichroic_on'] = df_dm_on

    # No dichroic (transparent mirror)
    volumes_dm_off, src, sens = create_base_geometry(
        dichroic_enabled=False
    )
    df_dm_off = run_comparison("Dichroic OFF", volumes_dm_off, src, sens)
    results['dichroic_off'] = df_dm_off

    # Perfect reflector at all wavelengths
    volumes_perfect, src, sens = create_base_geometry(
        dichroic_reflectance={128.0: 0.95, 420.0: 0.95, 490.0: 0.95}
    )
    df_perfect = run_comparison("Perfect Mirror", volumes_perfect, src, sens)
    results['perfect_mirror'] = df_perfect

    # =========================================================================
    # 3. Wavelength Shifting Impact
    # =========================================================================
    print("\n3. Wavelength Shifting")
    print("-" * 70)

    # With WLS (baseline)
    volumes_wls_on, src, sens = create_base_geometry(wls_enabled=True)
    df_wls_on = run_comparison("WLS Enabled", volumes_wls_on, src, sens)
    results['wls_on'] = df_wls_on

    # No WLS (transparent materials)
    volumes_wls_off, src, sens = create_base_geometry(wls_enabled=False)
    df_wls_off = run_comparison("WLS Disabled", volumes_wls_off, src, sens)
    results['wls_off'] = df_wls_off

    # =========================================================================
    # 4. Quantum Yield Sensitivity
    # =========================================================================
    print("\n4. Quantum Yield Sensitivity")
    print("-" * 70)

    # Perfect QY (no non-radiative losses)
    volumes_qy_perfect, src, sens = create_base_geometry(lc_qy=1.0, wls_qy=1.0)
    df_qy_perfect = run_comparison("Perfect QY (1.0)", volumes_qy_perfect, src, sens)
    results['qy_perfect'] = df_qy_perfect

    # Realistic QY (baseline already done above as with_gap)
    # df_qy_realistic = df_gap  # 0.95 and 0.9

    # Poor QY
    volumes_qy_poor, src, sens = create_base_geometry(lc_qy=0.7, wls_qy=0.7)
    df_qy_poor = run_comparison("Poor QY (0.7)", volumes_qy_poor, src, sens)
    results['qy_poor'] = df_qy_poor

    # =========================================================================
    # 5. Refractive Index Dispersion
    # =========================================================================
    print("\n5. Refractive Index Dispersion")
    print("-" * 70)

    # With dispersion (baseline)
    volumes_disp_on, src, sens = create_base_geometry(n_dispersion=True)
    df_disp_on = run_comparison("Dispersion ON", volumes_disp_on, src, sens)
    results['dispersion_on'] = df_disp_on

    # No dispersion (constant n)
    volumes_disp_off, src, sens = create_base_geometry(n_dispersion=False)
    df_disp_off = run_comparison("Dispersion OFF", volumes_disp_off, src, sens)
    results['dispersion_off'] = df_disp_off

    # =========================================================================
    # Generate Comparison Plots
    # =========================================================================
    print("\n" + "="*70)
    print("Generating Comparison Plots")
    print("="*70)

    # 1. Gap Comparison
    plot_gap_comparison(results)

    # 2. Physics Assumptions Summary
    plot_assumptions_summary(results)

    # 3. Efficiency vs Parameters
    plot_efficiency_comparison(results)

    # 4. Path Length Comparisons
    plot_path_length_comparison(results)

    print("\n✅ All validation plots generated in docs/validation/")


def plot_gap_comparison(results: Dict[str, pd.DataFrame]):
    """Compare with-gap vs no-gap configurations."""
    print("  1/4 Gap configuration comparison...")

    fig, axes = plt.subplots(2, 2, figsize=(14, 10))

    df_gap = results['with_gap']
    df_nogap = results['no_gap']

    # Detection efficiency
    ax = axes[0, 0]
    configs = ['With Gap', 'No Gap']
    efficiencies = [
        100 * (df_gap['arrived'].sum() / len(df_gap)),
        100 * (df_nogap['arrived'].sum() / len(df_nogap))
    ]
    bars = ax.bar(configs, efficiencies, color=['cyan', 'blue'], alpha=0.7, edgecolor='black')
    ax.set_ylabel('Detection Efficiency (%)', fontsize=11)
    ax.set_title('A) Detection Efficiency', fontweight='bold')
    ax.grid(axis='y', alpha=0.3)
    for bar, eff in zip(bars, efficiencies):
        ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.001,
                f'{eff:.3f}%', ha='center', va='bottom', fontsize=10)

    # Reflections
    ax = axes[0, 1]
    data_refl = [df_gap['n_reflections'], df_nogap['n_reflections']]
    bp = ax.boxplot(data_refl, labels=configs, patch_artist=True)
    for patch, color in zip(bp['boxes'], ['cyan', 'blue']):
        patch.set_facecolor(color)
        patch.set_alpha(0.6)
    ax.set_ylabel('Number of Reflections', fontsize=11)
    ax.set_title('B) Reflection Statistics', fontweight='bold')
    ax.grid(axis='y', alpha=0.3)

    # Path lengths (arrived only)
    ax = axes[1, 0]
    gap_arrived = df_gap[df_gap['arrived']]
    nogap_arrived = df_nogap[df_nogap['arrived']]

    if len(gap_arrived) > 0 and len(nogap_arrived) > 0:
        ax.hist([gap_arrived['path_length'], nogap_arrived['path_length']],
                bins=20, label=configs, color=['cyan', 'blue'],
                alpha=0.6, edgecolor='black')
        ax.set_xlabel('Path Length (m)', fontsize=11)
        ax.set_ylabel('Count (Arrived Only)', fontsize=11)
        ax.set_title('C) Path Length Distribution', fontweight='bold')
        ax.legend()
        ax.grid(axis='y', alpha=0.3)
    else:
        ax.text(0.5, 0.5, 'Insufficient arrived photons', ha='center', va='center',
                transform=ax.transAxes)
        ax.set_title('C) Path Length Distribution', fontweight='bold')

    # Event type breakdown
    ax = axes[1, 1]
    gap_events = df_gap['event_type'].value_counts()
    nogap_events = df_nogap['event_type'].value_counts()

    # Get common event types
    all_events = set(gap_events.index) | set(nogap_events.index)
    event_labels = sorted(all_events)
    gap_counts = [gap_events.get(e, 0) for e in event_labels]
    nogap_counts = [nogap_events.get(e, 0) for e in event_labels]

    x = np.arange(len(event_labels))
    width = 0.35
    ax.bar(x - width/2, gap_counts, width, label='With Gap', color='cyan', alpha=0.7)
    ax.bar(x + width/2, nogap_counts, width, label='No Gap', color='blue', alpha=0.7)
    ax.set_xlabel('Event Type', fontsize=11)
    ax.set_ylabel('Count', fontsize=11)
    ax.set_title('D) Event Type Distribution', fontweight='bold')
    ax.set_xticks(x)
    ax.set_xticklabels([e.replace('_', '\n') for e in event_labels],
                       rotation=45, ha='right', fontsize=8)
    ax.legend()
    ax.set_yscale('log')
    ax.grid(axis='y', alpha=0.3)

    plt.suptitle('Gap Configuration Comparison: Impact on Detection Performance',
                 fontsize=14, fontweight='bold', y=0.995)
    plt.tight_layout()
    Path('docs/validation').mkdir(exist_ok=True, parents=True)
    plt.savefig('docs/validation/gap_comparison.png', dpi=150, bbox_inches='tight')
    plt.close()


def plot_assumptions_summary(results: Dict[str, pd.DataFrame]):
    """Summary of key physics assumptions."""
    print("  2/4 Physics assumptions summary...")

    fig, axes = plt.subplots(2, 3, figsize=(16, 10))

    # Extract efficiencies for each comparison
    comparisons = [
        ('Dichroic ON', 'Dichroic OFF', 'Dichroic\nBehavior'),
        ('WLS Enabled', 'WLS Disabled', 'Wavelength\nShifting'),
        ('Perfect QY (1.0)', 'Poor QY (0.7)', 'Quantum\nYield'),
        ('Dispersion ON', 'Dispersion OFF', 'Refractive\nDispersion'),
        ('Perfect Mirror', 'Dichroic ON', 'Mirror\nQuality'),
        ('With Gap', 'No Gap', 'Gap\nPresence'),
    ]

    for idx, (config1, config2, label) in enumerate(comparisons):
        ax = axes[idx // 3, idx % 3]

        if config1 in results and config2 in results:
            df1 = results[config1]
            df2 = results[config2]

            eff1 = 100 * (df1['arrived'].sum() / len(df1))
            eff2 = 100 * (df2['arrived'].sum() / len(df2))

            configs = [config1.split()[0], config2.split()[0]]
            effs = [eff1, eff2]

            bars = ax.bar(configs, effs, color=['green', 'orange'], alpha=0.7,
                         edgecolor='black', linewidth=1.5)
            ax.set_ylabel('Efficiency (%)', fontsize=10)
            ax.set_title(label, fontweight='bold', fontsize=11)
            ax.grid(axis='y', alpha=0.3)

            # Add values on bars
            for bar, eff in zip(bars, effs):
                height = bar.get_height()
                ax.text(bar.get_x() + bar.get_width()/2, height,
                       f'{eff:.3f}%', ha='center', va='bottom', fontsize=9)

            # Add percentage change
            pct_change = ((eff1 - eff2) / eff2 * 100) if eff2 > 0 else 0
            ax.text(0.5, 0.95, f'Δ = {pct_change:+.1f}%',
                   transform=ax.transAxes, ha='center', va='top',
                   bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.5),
                   fontsize=9)

    plt.suptitle('Impact of Physics Assumptions on Detection Efficiency',
                 fontsize=14, fontweight='bold')
    plt.tight_layout()
    plt.savefig('docs/validation/assumptions_summary.png', dpi=150, bbox_inches='tight')
    plt.close()


def plot_efficiency_comparison(results: Dict[str, pd.DataFrame]):
    """Bar chart of all configuration efficiencies."""
    print("  3/4 Efficiency comparison across all configs...")

    fig, ax = plt.subplots(figsize=(14, 6))

    configs = []
    effs = []
    colors = []

    config_color_map = {
        'with_gap': 'cyan',
        'no_gap': 'blue',
        'dichroic_on': 'green',
        'dichroic_off': 'lightgreen',
        'perfect_mirror': 'darkgreen',
        'wls_on': 'red',
        'wls_off': 'pink',
        'qy_perfect': 'purple',
        'qy_poor': 'lavender',
        'dispersion_on': 'orange',
        'dispersion_off': 'yellow',
    }

    for key, df in results.items():
        config_name = df['config'].iloc[0]
        eff = 100 * (df['arrived'].sum() / len(df))
        configs.append(config_name)
        effs.append(eff)
        colors.append(config_color_map.get(key, 'gray'))

    # Sort by efficiency
    sorted_indices = np.argsort(effs)[::-1]
    configs = [configs[i] for i in sorted_indices]
    effs = [effs[i] for i in sorted_indices]
    colors = [colors[i] for i in sorted_indices]

    bars = ax.barh(configs, effs, color=colors, alpha=0.7, edgecolor='black')
    ax.set_xlabel('Detection Efficiency (%)', fontsize=12, fontweight='bold')
    ax.set_title('Efficiency Ranking Across All Configurations',
                 fontsize=14, fontweight='bold')
    ax.grid(axis='x', alpha=0.3)

    # Add values
    for bar, eff in zip(bars, effs):
        width = bar.get_width()
        ax.text(width + 0.001, bar.get_y() + bar.get_height()/2,
               f'{eff:.3f}%', ha='left', va='center', fontsize=9)

    plt.tight_layout()
    plt.savefig('docs/validation/efficiency_ranking.png', dpi=150, bbox_inches='tight')
    plt.close()


def plot_path_length_comparison(results: Dict[str, pd.DataFrame]):
    """Compare path length distributions for key configs."""
    print("  4/4 Path length comparison...")

    fig, axes = plt.subplots(2, 2, figsize=(14, 10))

    comparisons = [
        (['with_gap', 'no_gap'], 'Gap Configuration', axes[0, 0]),
        (['dichroic_on', 'dichroic_off'], 'Dichroic Mirror', axes[0, 1]),
        (['wls_on', 'wls_off'], 'Wavelength Shifting', axes[1, 0]),
        (['qy_perfect', 'qy_poor'], 'Quantum Yield', axes[1, 1]),
    ]

    for keys, title, ax in comparisons:
        data = []
        labels = []
        colors_list = ['green', 'orange']

        for i, key in enumerate(keys):
            if key in results:
                df = results[key]
                # Use only arrived photons for fair comparison
                arrived = df[df['arrived']]
                if len(arrived) > 0:
                    data.append(arrived['path_length'])
                    labels.append(df['config'].iloc[0])
                else:
                    # Use all photons if no arrivals
                    data.append(df['path_length'])
                    labels.append(df['config'].iloc[0] + '*')

        if data:
            ax.hist(data, bins=30, label=labels, alpha=0.6,
                   color=colors_list[:len(data)], edgecolor='black')
            ax.set_xlabel('Path Length (m)', fontsize=11)
            ax.set_ylabel('Count', fontsize=11)
            ax.set_title(title, fontweight='bold')
            ax.legend()
            ax.grid(axis='y', alpha=0.3)
            ax.set_yscale('log')

    plt.suptitle('Path Length Distributions: Impact of Physics Assumptions',
                 fontsize=14, fontweight='bold')
    plt.tight_layout()
    plt.savefig('docs/validation/path_length_comparison.png', dpi=150, bbox_inches='tight')
    plt.close()


if __name__ == "__main__":
    main()
