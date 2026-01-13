"""
Debug a single photon to see exactly what happens.
"""

import numpy as np
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from photon_tracer import Cuboid
from photon_tracer.optics import random_isotropic_direction

# Geometry
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

# Create simple volumes (no materials for now)
lc = Cuboid(lc_min, lc_max, refractive_index=1.65, name="lc", wls=False)
wls = Cuboid(wls_min, wls_max, refractive_index=1.70, name="wls", wls=False)
dm = Cuboid(dm_min, dm_max, refractive_index=1.5, name="dm", wls=False)
bulk = Cuboid(bulk_min, bulk_max, refractive_index=1.6, name="bulk", wls=False)

volumes = [lc, wls, dm, bulk]

print("Volume boundaries:")
for v in volumes:
    print(f"  {v.name}: x ∈ [{v.min_vertex[0]:.8f}, {v.max_vertex[0]:.8f}]")
print()

# Check source location
print(f"Source at: ({source_position[0]:.8f}, {source_position[1]:.3f}, {source_position[2]:.3f})")
for idx, v in enumerate(volumes):
    if v.contains(source_position):
        print(f"  → Source is in '{v.name}'")
        break
else:
    print(f"  → Source is OUTSIDE all volumes!")
print()

# Test a photon going toward detector (negative x)
test_direction = np.array([-1.0, 0.0, 0.0])  # Straight toward detector
test_position = source_position.copy()

print("Tracing photon with direction=(-1, 0, 0):")
print(f"  Start: x={test_position[0]:.8f}")

# Find first intersection
for v in volumes:
    t = v.intersect_distance(test_position, test_direction)
    if np.isfinite(t) and t > 0:
        intersection = test_position + test_direction * t
        print(f"  Intersects {v.name} at t={t:.8f}, x={intersection[0]:.8f}")
print()

# Manually trace through volumes
current_pos = test_position.copy()
current_dir = test_direction.copy()
current_vol = bulk

for step in range(10):  # Max 10 steps
    print(f"Step {step}: in '{current_vol.name}' at x={current_pos[0]:.8f}")

    # Find boundary distance
    t_bound = current_vol.intersect_distance(current_pos, current_dir)
    if not np.isfinite(t_bound):
        print(f"  → No intersection! Lost.")
        break

    # Move to boundary
    current_pos = current_pos + current_dir * t_bound
    print(f"  → Hit boundary at x={current_pos[0]:.8f}, t={t_bound:.8f}")

    # Find next volume
    eps = 1e-9
    test_point = current_pos + current_dir * eps

    next_vol = None
    for v in volumes:
        if v.contains(test_point):
            next_vol = v
            break

    if next_vol is None:
        print(f"  → Next point {test_point} is OUTSIDE all volumes! Lost.")
        break

    print(f"  → Next volume: '{next_vol.name}'")

    # Simple transition (no refraction for this test)
    current_vol = next_vol
    current_pos = test_point

    print()
