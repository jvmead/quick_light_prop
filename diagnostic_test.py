"""
Diagnostic test to understand why efficiency is so low.
"""

import numpy as np
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from photon_tracer import Cuboid, PhotonSimulation
from photon_tracer.simulation import SimulationConfig

# Geometry from physics_validation_fixed.py
width = 0.5
height = 0.5
lc_x = 1e-2
wls_x = 3e-6
dm_x = 112e-6
bulk_x = 0.5

x_pos = 0.0
lc_min = np.array([x_pos, 0, 0])
lc_max = np.array([x_pos + lc_x, height, width])
x_pos += lc_x

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

# Material properties (full physics)
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

volumes = [lc, wls, dm, bulk]

print("Geometry Summary:")
print(f"  LC:   x ∈ [{lc_min[0]:.6f}, {lc_max[0]:.6f}]")
print(f"  WLS:  x ∈ [{wls_min[0]:.6f}, {wls_max[0]:.6f}]")
print(f"  DM:   x ∈ [{dm_min[0]:.6f}, {dm_max[0]:.6f}]")
print(f"  Bulk: x ∈ [{bulk_min[0]:.6f}, {bulk_max[0]:.6f}]")
print(f"  Source: ({source_position[0]:.6f}, {source_position[1]:.3f}, {source_position[2]:.3f})")
print(f"  Sensors: x={sensor_positions[0][0]:.6f}, z=0.0")
print()

# Run small simulation
config = SimulationConfig(
    num_photons=1000,
    max_thrown=10000,
    max_steps=5000,
    max_workers=4,
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

df = sim.run(verbose=True)

# Analyze results
print("\nEvent Type Distribution:")
for event_type in df['event_type'].value_counts().head(10).items():
    print(f"  {event_type[0]}: {event_type[1]}")

print("\nReflection Statistics (arrived photons):")
arrived = df[df['event_type'] == 'arrived']
if len(arrived) > 0:
    print(f"  Mean reflections: {arrived['n_reflections'].mean():.2f}")
    print(f"  Mean TIR: {arrived['n_tir'].mean():.2f}")
    print(f"  Mean refractions: {arrived['n_refractions'].mean():.2f}")
    print(f"  Mean path length: {arrived['path_length'].mean():.4f} m")
else:
    print("  No photons arrived!")

print("\nWavelength shifts:")
for wl_hist in df['wavelength_history'].head(10):
    print(f"  {wl_hist}")
