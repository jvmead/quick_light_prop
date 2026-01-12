"""
Photon ray tracing simulation for optical detector systems.

This package provides tools for simulating photon propagation through
multi-layer optical systems with wavelength shifting, dichroic mirrors,
and complex geometries.
"""

from .geometry import Cuboid
from .simulation import PhotonSimulation
from .optics import reflect, refract, random_isotropic_direction

__version__ = "1.0.0"
__all__ = [
    "Cuboid",
    "PhotonSimulation",
    "reflect",
    "refract",
    "random_isotropic_direction",
]
