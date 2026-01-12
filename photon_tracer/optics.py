"""
Optical physics functions for photon propagation.

This module provides core optical physics operations including:
- Reflection (specular)
- Refraction (Snell's law)
- Random direction generation (isotropic)
"""

import numpy as np
from typing import Optional

# Speed of light in vacuum (m/s)
C0 = 299_792_458.0


def random_isotropic_direction(rng: np.random.Generator) -> np.ndarray:
    """
    Generate a random isotropic direction vector (unit vector).

    Uses the method of sampling uniformly on a unit sphere.

    Parameters
    ----------
    rng : np.random.Generator
        NumPy random number generator

    Returns
    -------
    np.ndarray
        Unit direction vector [x, y, z]
    """
    u = rng.uniform(-1.0, 1.0)
    phi = rng.uniform(0.0, 2.0 * np.pi)
    s = np.sqrt(max(0.0, 1.0 - u * u))
    return np.array([s * np.cos(phi), s * np.sin(phi), u], dtype=float)


def reflect(direction: np.ndarray, normal: np.ndarray) -> np.ndarray:
    """
    Compute specular reflection direction.

    Uses the formula: r = d - 2(d·n)n
    where d is the incident direction and n is the surface normal.

    Parameters
    ----------
    direction : np.ndarray
        Incident direction vector
    normal : np.ndarray
        Surface normal vector (should point away from surface)

    Returns
    -------
    np.ndarray
        Reflected direction (unit vector)
    """
    d = direction / np.linalg.norm(direction)
    n = normal / np.linalg.norm(normal)
    r = d - 2.0 * np.dot(d, n) * n
    return r / np.linalg.norm(r)


def refract(
    direction: np.ndarray,
    normal: np.ndarray,
    n1: float,
    n2: float
) -> Optional[np.ndarray]:
    """
    Compute refraction direction using Snell's law.

    The normal vector should point from medium 1 (with index n1) into
    medium 2 (with index n2). If total internal reflection occurs,
    returns None.

    Parameters
    ----------
    direction : np.ndarray
        Incident direction vector
    normal : np.ndarray
        Surface normal pointing from n1 into n2
    n1 : float
        Refractive index of incident medium
    n2 : float
        Refractive index of transmitted medium

    Returns
    -------
    Optional[np.ndarray]
        Refracted direction (unit vector) or None if TIR occurs

    Notes
    -----
    Uses Snell's law: n1*sin(θ1) = n2*sin(θ2)

    Total internal reflection occurs when n1 > n2 and
    sin(θ2) = (n1/n2)*sin(θ1) > 1
    """
    d = direction / np.linalg.norm(direction)
    n = normal / np.linalg.norm(normal)

    # Compute cos(θ_incident) using dot product
    # Convention: normal points into medium 2, so cos_i should be negative
    # for a ray traveling toward the interface
    cos_i = -np.dot(n, d)
    sin2_i = max(0.0, 1.0 - cos_i * cos_i)

    # Snell's law: n1*sin(θ1) = n2*sin(θ2)
    eta = n1 / n2
    sin2_t = eta * eta * sin2_i

    # Check for total internal reflection
    if sin2_t >= 1.0:
        return None

    cos_t = np.sqrt(max(0.0, 1.0 - sin2_t))

    # Refracted direction using vector form of Snell's law
    t = eta * d + (eta * cos_i - cos_t) * n

    return t / np.linalg.norm(t)


def fresnel_reflectance(
    cos_i: float,
    n1: float,
    n2: float
) -> float:
    """
    Compute Fresnel reflectance for unpolarized light.

    Parameters
    ----------
    cos_i : float
        Cosine of incident angle
    n1 : float
        Refractive index of incident medium
    n2 : float
        Refractive index of transmitted medium

    Returns
    -------
    float
        Fresnel reflectance coefficient (0 to 1)

    Notes
    -----
    This function computes the average of s and p polarization
    reflectances for unpolarized light.
    """
    cos_i = abs(cos_i)

    # Compute transmitted angle
    sin2_i = 1.0 - cos_i * cos_i
    sin2_t = (n1 / n2) ** 2 * sin2_i

    # Total internal reflection
    if sin2_t >= 1.0:
        return 1.0

    cos_t = np.sqrt(1.0 - sin2_t)

    # Fresnel equations
    rs = ((n1 * cos_i - n2 * cos_t) / (n1 * cos_i + n2 * cos_t)) ** 2
    rp = ((n1 * cos_t - n2 * cos_i) / (n1 * cos_t + n2 * cos_i)) ** 2

    # Average for unpolarized light
    return 0.5 * (rs + rp)
