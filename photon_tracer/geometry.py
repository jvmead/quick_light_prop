"""
Geometric primitives for ray tracing.

This module provides axis-aligned bounding box (AABB) geometry
with optical properties for wavelength shifting and dichroic behavior.
"""

import numpy as np
from typing import Union, Dict, Callable, Optional, List


class Cuboid:
    """
    Axis-aligned bounding box (AABB) with optical properties.

    This class represents a rectangular volume with optional physics:
    - Wavelength-dependent refractive index
    - Bulk wavelength shifting (Beer-Lambert absorption)
    - Dichroic reflectance at interfaces

    Parameters
    ----------
    min_point : array-like
        Minimum corner [x_min, y_min, z_min]
    max_point : array-like
        Maximum corner [x_max, y_max, z_max]
    refractive_index : float, dict, or callable, optional
        Refractive index as:
        - float: constant n
        - dict: {wavelength_nm: n} for lookup
        - callable: n(wavelength_nm)
    name : str, optional
        Identifier for this volume
    wls : bool, optional
        Enable wavelength shifting (default: False)
    mu_a : float, dict, or callable, optional
        Absorption coefficient [1/m] for Beer-Lambert absorption
    quantum_yield : float, optional
        Re-emission probability after absorption (default: 1.0)
    emission_peak_nm : float, optional
        Peak emission wavelength for WLS [nm]
    emission_sigma_nm : float, optional
        Gaussian width for WLS emission [nm]
    wls_transitions : dict, optional
        Discrete wavelength transitions {lambda_in: lambda_out}
    is_dichroic : bool, optional
        Enable wavelength-dependent reflectance (default: False)
    reflectance : float, dict, or callable, optional
        Reflectance R(λ) in [0, 1]

    Attributes
    ----------
    min_vertex : np.ndarray
        Minimum corner of AABB
    max_vertex : np.ndarray
        Maximum corner of AABB
    center : np.ndarray
        Center point of AABB
    """

    def __init__(
        self,
        min_point: Union[List, np.ndarray],
        max_point: Union[List, np.ndarray],
        refractive_index: Union[float, Dict[float, float], Callable] = 1.0,
        name: Optional[str] = None,
        wls: bool = False,
        mu_a: Union[float, Dict[float, float], Callable] = 0.0,
        quantum_yield: float = 1.0,
        emission_peak_nm: Optional[float] = None,
        emission_sigma_nm: Optional[float] = None,
        wls_transitions: Optional[Dict[float, float]] = None,
        is_dichroic: bool = False,
        reflectance: Union[float, Dict[float, float], Callable] = 0.0,
    ):
        self.min_vertex = np.asarray(min_point, dtype=float)
        self.max_vertex = np.asarray(max_point, dtype=float)

        # Validate geometry
        if not np.all(self.max_vertex > self.min_vertex):
            raise ValueError("max_point must be greater than min_point in all dimensions")

        self.center = 0.5 * (self.min_vertex + self.max_vertex)
        self.refractive_index = refractive_index
        self.name = name

        # Wavelength shifting properties
        self.wls = bool(wls)
        self.mu_a = mu_a
        self.quantum_yield = float(quantum_yield)
        self.wls_transitions = wls_transitions or {}
        self.emission_peak_nm = emission_peak_nm
        self.emission_sigma_nm = emission_sigma_nm

        # Dichroic properties
        self.is_dichroic = bool(is_dichroic)
        self.reflectance = reflectance

    @classmethod
    def from_vertices(cls, vertices: np.ndarray, **kwargs):
        """
        Create Cuboid from 8 corner vertices.

        Parameters
        ----------
        vertices : array-like
            8x3 array of corner vertices
        **kwargs
            Additional parameters passed to Cuboid constructor

        Returns
        -------
        Cuboid
            New cuboid instance
        """
        verts = np.asarray(vertices, dtype=float)
        min_point = np.min(verts, axis=0)
        max_point = np.max(verts, axis=0)
        return cls(min_point, max_point, **kwargs)

    def contains(self, point: np.ndarray, eps: float = 1e-12) -> bool:
        """
        Check if a point is inside the cuboid.

        Parameters
        ----------
        point : np.ndarray
            Point coordinates [x, y, z]
        eps : float, optional
            Tolerance for boundary (default: 1e-12)

        Returns
        -------
        bool
            True if point is inside (or on boundary within eps)
        """
        p = np.asarray(point, dtype=float)
        return bool(
            np.all(p >= self.min_vertex - eps) and
            np.all(p <= self.max_vertex + eps)
        )

    def intersect_distance(
        self,
        origin: np.ndarray,
        direction: np.ndarray
    ) -> float:
        """
        Compute ray-AABB intersection distance.

        Uses the slab method for efficient ray-box intersection.

        Parameters
        ----------
        origin : np.ndarray
            Ray origin [x, y, z]
        direction : np.ndarray
            Ray direction [dx, dy, dz] (need not be normalized)

        Returns
        -------
        float
            Distance to first intersection (t >= 0), or np.inf if no hit

        Notes
        -----
        Returns the parameter t such that intersection point is origin + t*direction
        """
        o = np.asarray(origin, dtype=float)
        d = np.asarray(direction, dtype=float)

        # Avoid division by zero
        inv_dir = np.where(np.abs(d) > 1e-15, 1.0 / d, np.inf)

        # Compute intersection distances for all slabs
        t0 = (self.min_vertex - o) * inv_dir
        t1 = (self.max_vertex - o) * inv_dir

        # Sort to get tmin and tmax for each slab
        tmin = np.max(np.minimum(t0, t1))
        tmax = np.min(np.maximum(t0, t1))

        # Check for valid intersection
        if tmax < 0 or tmin > tmax:
            return np.inf

        # Return nearest intersection that's in front of ray
        return float(tmin) if tmin >= 0 else float(tmax)

    def surface_normal_at(
        self,
        point: np.ndarray,
        eps: float = 1e-9
    ) -> np.ndarray:
        """
        Get outward surface normal at a point on the boundary.

        Parameters
        ----------
        point : np.ndarray
            Point on surface [x, y, z]
        eps : float, optional
            Tolerance for determining which face (default: 1e-9)

        Returns
        -------
        np.ndarray
            Outward unit normal vector

        Notes
        -----
        Returns the normal for the face closest to the point.
        Normals point outward from the volume.
        """
        p = np.asarray(point, dtype=float)

        # Compute distances to each face
        distances = np.array([
            abs(p[0] - self.min_vertex[0]),  # -x face
            abs(p[0] - self.max_vertex[0]),  # +x face
            abs(p[1] - self.min_vertex[1]),  # -y face
            abs(p[1] - self.max_vertex[1]),  # +y face
            abs(p[2] - self.min_vertex[2]),  # -z face
            abs(p[2] - self.max_vertex[2]),  # +z face
        ])

        # Find closest face
        face_index = int(np.argmin(distances))

        # Return corresponding normal (outward)
        normals = [
            np.array([-1.0, 0.0, 0.0]),  # -x face
            np.array([+1.0, 0.0, 0.0]),  # +x face
            np.array([0.0, -1.0, 0.0]),  # -y face
            np.array([0.0, +1.0, 0.0]),  # +y face
            np.array([0.0, 0.0, -1.0]),  # -z face
            np.array([0.0, 0.0, +1.0]),  # +z face
        ]

        return normals[face_index]

    def get_refractive_index(self, wavelength_nm: float) -> float:
        """
        Get refractive index at a given wavelength.

        Parameters
        ----------
        wavelength_nm : float
            Wavelength in nanometers

        Returns
        -------
        float
            Refractive index (dimensionless)
        """
        if isinstance(self.refractive_index, dict):
            # Find nearest wavelength in dictionary
            wavelengths = np.array(list(self.refractive_index.keys()), dtype=float)
            idx = int(np.abs(wavelengths - wavelength_nm).argmin())
            return float(self.refractive_index[wavelengths[idx]])
        elif callable(self.refractive_index):
            return float(self.refractive_index(wavelength_nm))
        else:
            return float(self.refractive_index)

    def get_mu_a(self, wavelength_nm: float) -> float:
        """
        Get absorption coefficient at a given wavelength.

        Parameters
        ----------
        wavelength_nm : float
            Wavelength in nanometers

        Returns
        -------
        float
            Absorption coefficient in [1/m]
        """
        if isinstance(self.mu_a, dict):
            wavelengths = np.array(list(self.mu_a.keys()), dtype=float)
            idx = int(np.abs(wavelengths - wavelength_nm).argmin())
            return float(self.mu_a[wavelengths[idx]])
        elif callable(self.mu_a):
            return float(self.mu_a(wavelength_nm))
        else:
            return float(self.mu_a)

    def get_reflectance(self, wavelength_nm: float) -> float:
        """
        Get dichroic reflectance at a given wavelength.

        Parameters
        ----------
        wavelength_nm : float
            Wavelength in nanometers

        Returns
        -------
        float
            Reflectance coefficient in [0, 1]
        """
        if isinstance(self.reflectance, dict):
            wavelengths = np.array(list(self.reflectance.keys()), dtype=float)
            idx = int(np.abs(wavelengths - wavelength_nm).argmin())
            return float(self.reflectance[wavelengths[idx]])
        elif callable(self.reflectance):
            return float(self.reflectance(wavelength_nm))
        else:
            return float(self.reflectance)

    def sample_emission_wavelength(
        self,
        rng: np.random.Generator,
        incident_wavelength_nm: float
    ) -> float:
        """
        Sample emission wavelength after absorption.

        Uses either discrete transitions or Gaussian emission spectrum.

        Parameters
        ----------
        rng : np.random.Generator
            Random number generator
        incident_wavelength_nm : float
            Incident photon wavelength [nm]

        Returns
        -------
        float
            Emitted wavelength [nm]
        """
        # Check for discrete wavelength transition
        if self.wls_transitions:
            wavelengths = np.array(list(self.wls_transitions.keys()), dtype=float)
            idx = int(np.abs(wavelengths - incident_wavelength_nm).argmin())
            return float(self.wls_transitions[wavelengths[idx]])

        # Gaussian emission spectrum
        if self.emission_peak_nm is not None:
            sigma = float(self.emission_sigma_nm) if self.emission_sigma_nm else 10.0
            emitted = rng.normal(loc=float(self.emission_peak_nm), scale=sigma)
            return float(max(1.0, emitted))  # Ensure positive wavelength

        # No wavelength shift
        return float(incident_wavelength_nm)

    def __repr__(self) -> str:
        """String representation of cuboid."""
        name_str = f"'{self.name}'" if self.name else "unnamed"
        return (
            f"Cuboid({name_str}, "
            f"min={self.min_vertex}, max={self.max_vertex}, "
            f"wls={self.wls}, dichroic={self.is_dichroic})"
        )
