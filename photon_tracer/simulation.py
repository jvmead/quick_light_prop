"""
Monte Carlo photon propagation simulation.

This module implements a multi-threaded ray tracer for photon transport
through complex optical systems with wavelength shifting and dichroic optics.
"""

import numpy as np
import pandas as pd
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from tqdm import tqdm
from typing import List, Optional, Tuple, Dict
from dataclasses import dataclass, field

from .geometry import Cuboid
from .optics import random_isotropic_direction, reflect, refract


@dataclass
class SimulationConfig:
    """
    Configuration for photon simulation.

    Attributes
    ----------
    num_photons : int
        Target number of successfully detected photons
    max_thrown : int
        Maximum total photons to throw
    max_steps : int
        Maximum propagation steps per photon
    max_workers : int
        Number of parallel worker threads
    initial_wavelength_nm : float
        Initial photon wavelength [nm]
    rng_seed : int, optional
        Random seed for reproducibility
    """
    num_photons: int = 1000
    max_thrown: int = 10000
    max_steps: int = 5000
    max_workers: int = 8
    initial_wavelength_nm: float = 128.0
    rng_seed: Optional[int] = None


@dataclass
class PhotonEvent:
    """
    Record of a single photon's propagation.

    Attributes
    ----------
    trajectory : List[np.ndarray]
        List of position vectors along path
    event_type : str
        Final fate of photon (arrived, lost_*, absorbed_*)
    n_reflections : int
        Total number of reflections
    n_tir : int
        Number of total internal reflections
    n_refractions : int
        Number of successful refractions
    path_length : float
        Total geometric path length [m]
    wavelength_history : List[float]
        Wavelengths at each shift point [nm]
    """
    trajectory: List[np.ndarray] = field(default_factory=list)
    event_type: str = "unknown"
    n_reflections: int = 0
    n_tir: int = 0
    n_refractions: int = 0
    path_length: float = 0.0
    wavelength_history: List[float] = field(default_factory=list)

    def to_dict(self) -> Dict:
        """Convert to dictionary for DataFrame."""
        return {
            "trajectory": ";".join([",".join(map(str, p)) for p in self.trajectory]),
            "event_type": self.event_type,
            "arrived": self.event_type == "arrived",
            "lost": self.event_type != "arrived",
            "n_reflections": self.n_reflections,
            "n_tir": self.n_tir,
            "n_refractions": self.n_refractions,
            "path_length": self.path_length,
            "wavelength_history": ";".join(f"{w:.6g}" for w in self.wavelength_history),
        }


class PhotonSimulation:
    """
    Monte Carlo photon ray tracing simulation.

    This class manages photon propagation through a multi-volume optical
    system with support for wavelength shifting, dichroic optics, and
    parallel execution.

    Parameters
    ----------
    volumes : List[Cuboid]
        List of optical volumes (order matters for overlaps)
    source_position : array-like
        Isotropic point source location [x, y, z] in meters
    sensor_positions : array-like
        Array of sensor locations [N x 3] in meters
    sensor_radius : float
        Detection radius for sensors in meters
    config : SimulationConfig, optional
        Simulation configuration parameters

    Attributes
    ----------
    data_df : pd.DataFrame
        Results dataframe after running simulation
    """

    def __init__(
        self,
        volumes: List[Cuboid],
        source_position: np.ndarray,
        sensor_positions: np.ndarray,
        sensor_radius: float,
        config: Optional[SimulationConfig] = None,
    ):
        self.volumes = list(volumes)
        self.source_position = np.asarray(source_position, dtype=float)
        self.sensor_positions = np.asarray(sensor_positions, dtype=float)
        self.sensor_radius = float(sensor_radius)

        self.config = config if config is not None else SimulationConfig()

        # Results storage
        self.data: List[PhotonEvent] = []
        self.data_df: Optional[pd.DataFrame] = None

        # Create combined bounding volume for early exit detection
        if self.volumes:
            all_mins = np.min([v.min_vertex for v in self.volumes], axis=0)
            all_maxs = np.max([v.max_vertex for v in self.volumes], axis=0)
            self.combined_bbox = Cuboid(all_mins, all_maxs, name="combined")
        else:
            self.combined_bbox = None

    def find_containing_volume(
        self,
        point: np.ndarray
    ) -> Tuple[Optional[int], Optional[Cuboid]]:
        """
        Find which volume contains a point.

        Parameters
        ----------
        point : np.ndarray
            Point coordinates [x, y, z]

        Returns
        -------
        Tuple[Optional[int], Optional[Cuboid]]
            (index, volume) or (None, None) if outside all volumes

        Notes
        -----
        Returns first volume in list that contains point.
        Volume ordering matters for overlapping regions.
        """
        for idx, volume in enumerate(self.volumes):
            if volume.contains(point):
                return idx, volume
        return None, None

    def hits_sensor(self, point: np.ndarray) -> bool:
        """
        Check if point hits any sensor.

        Parameters
        ----------
        point : np.ndarray
            Point coordinates [x, y, z]

        Returns
        -------
        bool
            True if within sensor_radius of any sensor
        """
        if len(self.sensor_positions) == 0:
            return False

        distances = np.linalg.norm(self.sensor_positions - point, axis=1)
        return bool(np.any(distances <= self.sensor_radius))

    def propagate_single_photon(self, photon_index: int = 0) -> PhotonEvent:
        """
        Trace a single photon from source to termination.

        Parameters
        ----------
        photon_index : int
            Photon identifier for seeding RNG

        Returns
        -------
        PhotonEvent
            Complete record of photon propagation

        Notes
        -----
        Termination conditions:
        - Hits sensor (arrived)
        - Exits all volumes (lost)
        - Non-radiative absorption (absorbed)
        - Exceeds max_steps (lost_maxsteps)
        """
        # Initialize RNG with unique seed per photon
        if self.config.rng_seed is not None:
            seed = self.config.rng_seed + 1_000_003 * photon_index
            rng = np.random.default_rng(seed)
        else:
            rng = np.random.default_rng()

        # Initialize photon state
        event = PhotonEvent()
        position = self.source_position.copy()
        direction = random_isotropic_direction(rng)
        wavelength = self.config.initial_wavelength_nm

        event.trajectory.append(position.copy())
        event.wavelength_history.append(wavelength)

        # Find starting volume
        vol_idx, current_vol = self.find_containing_volume(position)
        if current_vol is None:
            event.event_type = "lost_outside"
            return event

        eps = 1e-9  # Small offset for boundary transitions

        # Main propagation loop
        for step in range(self.config.max_steps):
            # Check if outside combined bounding box (early exit)
            if self.combined_bbox and not self.combined_bbox.contains(position):
                event.event_type = f"lost_{current_vol.name or vol_idx}"
                return event

            # Find distance to boundary
            t_boundary = current_vol.intersect_distance(position, direction)
            if not np.isfinite(t_boundary):
                event.event_type = f"lost_{current_vol.name or vol_idx}"
                return event

            # --- Beer-Lambert absorption in WLS volumes ---
            if current_vol.wls:
                mu_a = max(0.0, current_vol.get_mu_a(wavelength))
                if mu_a > 0.0:
                    # Sample absorption distance
                    U = max(rng.uniform(0.0, 1.0), 1e-300)
                    s_abs = -np.log(U) / mu_a

                    if s_abs < t_boundary:
                        # Absorption before boundary
                        position = position + direction * s_abs
                        event.trajectory.append(position.copy())
                        event.path_length += s_abs

                        # Check for non-radiative decay
                        if rng.uniform(0.0, 1.0) > current_vol.quantum_yield:
                            event.event_type = f"absorbed_nonrad_{current_vol.name or vol_idx}"
                            return event

                        # Re-emit with shifted wavelength
                        wavelength = current_vol.sample_emission_wavelength(rng, wavelength)
                        event.wavelength_history.append(wavelength)
                        direction = random_isotropic_direction(rng)

                        # Check sensor hit after re-emission
                        if self.hits_sensor(position):
                            event.event_type = "arrived"
                            return event

                        continue  # Stay in same volume

            # --- Propagate to boundary ---
            position = position + direction * t_boundary
            event.trajectory.append(position.copy())
            event.path_length += t_boundary

            # Check sensor hit at boundary
            if self.hits_sensor(position):
                event.event_type = "arrived"
                return event

            # --- Determine next volume ---
            test_point = position + direction * eps
            next_idx, next_vol = self.find_containing_volume(test_point)

            if next_vol is None:
                event.event_type = f"lost_{current_vol.name or vol_idx}"
                return event

            # Get surface normal (points outward from current volume)
            normal = current_vol.surface_normal_at(position)

            # --- Dichroic reflectance ---
            if current_vol.is_dichroic or next_vol.is_dichroic:
                # Use dichroic volume's reflectance curve
                dm_vol = current_vol if current_vol.is_dichroic else next_vol
                R = np.clip(dm_vol.get_reflectance(wavelength), 0.0, 1.0)

                if rng.uniform(0.0, 1.0) < R:
                    # Dichroic reflection
                    direction = reflect(direction, normal)
                    event.n_reflections += 1
                    position = position + direction * eps
                    continue
                # else: transmitted through dichroic

            # --- Handle optical interface ---
            n1 = current_vol.get_refractive_index(wavelength)
            n2 = next_vol.get_refractive_index(wavelength)

            # Check if same optical medium (no interface)
            if np.isclose(n1, n2, rtol=0, atol=1e-6):
                vol_idx, current_vol = next_idx, next_vol
                position = position + direction * eps
                continue

            # Real optical interface: try refraction
            # Normal points outward from current volume, which is correct for refract()
            refracted_dir = refract(direction, normal, n1, n2)

            if refracted_dir is None:
                # Total internal reflection
                direction = reflect(direction, normal)
                event.n_reflections += 1
                event.n_tir += 1
                position = position + direction * eps
            else:
                # Successful refraction into next volume
                direction = refracted_dir
                event.n_refractions += 1
                vol_idx, current_vol = next_idx, next_vol
                position = position + direction * eps

        # Exceeded max steps
        event.event_type = f"lost_maxsteps_{current_vol.name or vol_idx}"
        return event

    def run(self, verbose: bool = True) -> pd.DataFrame:
        """
        Run the full Monte Carlo simulation.

        Parameters
        ----------
        verbose : bool, optional
            Print progress and statistics (default: True)

        Returns
        -------
        pd.DataFrame
            Results with columns: trajectory, event_type, n_reflections,
            n_tir, n_refractions, path_length, wavelength_history, etc.
        """
        start_time = time.time()
        self.data = []

        successful = 0
        thrown = 0

        with ThreadPoolExecutor(max_workers=self.config.max_workers) as executor:
            # Submit all photons
            futures = {
                executor.submit(self.propagate_single_photon, i): i
                for i in range(self.config.max_thrown)
            }

            # Progress bar
            pbar = tqdm(
                total=self.config.max_thrown,
                desc="Photon tracing",
                disable=not verbose,
            )

            # Collect results
            for future in as_completed(futures):
                thrown += 1
                event = future.result()
                self.data.append(event)
                pbar.update(1)

                if event.event_type == "arrived":
                    successful += 1
                    if successful >= self.config.num_photons:
                        break

                if thrown >= self.config.max_thrown:
                    break

            pbar.close()

        elapsed = time.time() - start_time

        # Convert to DataFrame
        self.data_df = pd.DataFrame([event.to_dict() for event in self.data])

        # Print statistics
        if verbose:
            print(f"\nSimulation complete:")
            print(f"  Total thrown: {thrown}")
            print(f"  Arrived: {successful}")
            print(f"  Efficiency: {100.0 * successful / thrown:.3f}%")
            print(f"  Time: {elapsed:.2f} s")
            print(f"\nFates:")
            for volume in self.volumes:
                name = volume.name or f"vol_{self.volumes.index(volume)}"
                for fate_type in ["lost", "absorbed_nonrad"]:
                    key = f"{fate_type}_{name}"
                    count = (self.data_df["event_type"] == key).sum()
                    if count > 0:
                        print(f"  {key}: {count}")

        return self.data_df

    def save_results(self, filename: str):
        """Save results to CSV file."""
        if self.data_df is None:
            raise RuntimeError("No results to save. Run simulation first.")
        self.data_df.to_csv(filename, index=False)
        print(f"Results saved to {filename}")

    def load_results(self, filename: str):
        """Load results from CSV file."""
        self.data_df = pd.read_csv(filename)
        print(f"Results loaded from {filename}")
