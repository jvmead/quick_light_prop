"""
Analysis and visualization utilities for simulation results.

This module provides functions for analyzing photon simulation data,
computing detection efficiencies, solid angles, and creating plots.
"""

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from typing import List, Tuple, Optional
from mpl_toolkits.mplot3d import Axes3D

from .geometry import Cuboid


def solid_angle_triangle(
    observer: np.ndarray,
    v1: np.ndarray,
    v2: np.ndarray,
    v3: np.ndarray
) -> float:
    """
    Compute solid angle subtended by a triangle.

    Uses the Oosterom & Strackee formula for numerical stability.

    Parameters
    ----------
    observer : np.ndarray
        Observer position [x, y, z]
    v1, v2, v3 : np.ndarray
        Triangle vertices [x, y, z]

    Returns
    -------
    float
        Solid angle in steradians

    References
    ----------
    Van Oosterom, A. and Strackee, J., 1983. The solid angle of a plane
    triangle. IEEE transactions on Biomedical Engineering, (2), pp.125-126.
    """
    # Position vectors relative to observer
    r1 = v1 - observer
    r2 = v2 - observer
    r3 = v3 - observer

    # Lengths
    l1 = np.linalg.norm(r1)
    l2 = np.linalg.norm(r2)
    l3 = np.linalg.norm(r3)

    # Handle degenerate cases
    eps = 1e-15
    if l1 < eps or l2 < eps or l3 < eps:
        return 0.0

    # Triple scalar product
    numerator = np.dot(r1, np.cross(r2, r3))

    # Oosterom & Strackee denominator
    denominator = (
        l1 * l2 * l3 +
        np.dot(r1, r2) * l3 +
        np.dot(r2, r3) * l1 +
        np.dot(r3, r1) * l2
    )

    return 2.0 * np.arctan2(numerator, denominator)


def solid_angle_rectangle(
    observer: np.ndarray,
    v1: np.ndarray,
    v2: np.ndarray,
    v3: np.ndarray,
    v4: np.ndarray
) -> float:
    """
    Compute solid angle subtended by a rectangle.

    Divides rectangle into two triangles (v1-v2-v3 and v1-v3-v4).

    Parameters
    ----------
    observer : np.ndarray
        Observer position
    v1, v2, v3, v4 : np.ndarray
        Rectangle vertices in order

    Returns
    -------
    float
        Solid angle in steradians
    """
    omega1 = solid_angle_triangle(observer, v1, v2, v3)
    omega2 = solid_angle_triangle(observer, v1, v3, v4)
    return abs(omega1 + omega2)


def compute_geometric_efficiency(
    source_position: np.ndarray,
    target_cuboid: Cuboid,
    target_face: str = "xmin"
) -> Tuple[float, float]:
    """
    Compute geometric acceptance (solid angle / 4π) for a cuboid face.

    Parameters
    ----------
    source_position : np.ndarray
        Isotropic source location [x, y, z]
    target_cuboid : Cuboid
        Target volume
    target_face : str
        Which face to use: 'xmin', 'xmax', 'ymin', 'ymax', 'zmin', 'zmax'

    Returns
    -------
    Tuple[float, float]
        (solid_angle [sr], geometric_fraction [dimensionless])

    Notes
    -----
    geometric_fraction = solid_angle / (4π) gives the fraction of
    isotropically emitted photons that hit the face.
    """
    min_v = target_cuboid.min_vertex
    max_v = target_cuboid.max_vertex

    # Define rectangle vertices for each face
    face_vertices = {
        "xmin": [  # -x face
            np.array([min_v[0], min_v[1], min_v[2]]),
            np.array([min_v[0], max_v[1], min_v[2]]),
            np.array([min_v[0], max_v[1], max_v[2]]),
            np.array([min_v[0], min_v[1], max_v[2]]),
        ],
        "xmax": [  # +x face
            np.array([max_v[0], min_v[1], min_v[2]]),
            np.array([max_v[0], max_v[1], min_v[2]]),
            np.array([max_v[0], max_v[1], max_v[2]]),
            np.array([max_v[0], min_v[1], max_v[2]]),
        ],
        "ymin": [  # -y face
            np.array([min_v[0], min_v[1], min_v[2]]),
            np.array([max_v[0], min_v[1], min_v[2]]),
            np.array([max_v[0], min_v[1], max_v[2]]),
            np.array([min_v[0], min_v[1], max_v[2]]),
        ],
        "ymax": [  # +y face
            np.array([min_v[0], max_v[1], min_v[2]]),
            np.array([max_v[0], max_v[1], min_v[2]]),
            np.array([max_v[0], max_v[1], max_v[2]]),
            np.array([min_v[0], max_v[1], max_v[2]]),
        ],
        "zmin": [  # -z face
            np.array([min_v[0], min_v[1], min_v[2]]),
            np.array([max_v[0], min_v[1], min_v[2]]),
            np.array([max_v[0], max_v[1], min_v[2]]),
            np.array([min_v[0], max_v[1], min_v[2]]),
        ],
        "zmax": [  # +z face
            np.array([min_v[0], min_v[1], max_v[2]]),
            np.array([max_v[0], min_v[1], max_v[2]]),
            np.array([max_v[0], max_v[1], max_v[2]]),
            np.array([min_v[0], max_v[1], max_v[2]]),
        ],
    }

    if target_face not in face_vertices:
        raise ValueError(f"Invalid face: {target_face}")

    v1, v2, v3, v4 = face_vertices[target_face]
    solid_angle = solid_angle_rectangle(source_position, v1, v2, v3, v4)
    geometric_fraction = solid_angle / (4.0 * np.pi)

    return solid_angle, geometric_fraction


def plot_geometry_3d(
    volumes: List[Cuboid],
    source_position: Optional[np.ndarray] = None,
    sensor_positions: Optional[np.ndarray] = None,
    ax: Optional[plt.Axes] = None,
    colors: Optional[List[str]] = None
) -> plt.Axes:
    """
    Plot 3D visualization of geometry setup.

    Parameters
    ----------
    volumes : List[Cuboid]
        Volumes to visualize
    source_position : np.ndarray, optional
        Source location to mark
    sensor_positions : np.ndarray, optional
        Sensor locations to mark
    ax : plt.Axes, optional
        Existing 3D axes (creates new if None)
    colors : List[str], optional
        Colors for each volume

    Returns
    -------
    plt.Axes
        3D axes with geometry plotted
    """
    if ax is None:
        fig = plt.figure(figsize=(10, 8))
        ax = fig.add_subplot(111, projection='3d')

    if colors is None:
        colors = ['blue', 'red', 'orange', 'green', 'cyan', 'magenta', 'yellow']

    # Draw each volume as wireframe box
    for i, vol in enumerate(volumes):
        color = colors[i % len(colors)]
        _draw_cuboid_wireframe(ax, vol.min_vertex, vol.max_vertex, color, vol.name)

    # Mark source
    if source_position is not None:
        ax.scatter(*source_position, c='black', marker='*', s=200, label='Source')

    # Mark sensors
    if sensor_positions is not None:
        sensors = np.asarray(sensor_positions)
        if sensors.ndim == 1:
            sensors = sensors.reshape(1, -1)
        ax.scatter(sensors[:, 0], sensors[:, 1], sensors[:, 2],
                   c='red', marker='o', s=100, label='Sensors')

    ax.set_xlabel('X [m]')
    ax.set_ylabel('Y [m]')
    ax.set_zlabel('Z [m]')
    ax.legend()

    return ax


def _draw_cuboid_wireframe(
    ax: plt.Axes,
    min_v: np.ndarray,
    max_v: np.ndarray,
    color: str,
    label: Optional[str] = None
):
    """Draw wireframe box for a cuboid."""
    # Define 12 edges of box
    edges = [
        # Bottom face
        ([min_v[0], max_v[0]], [min_v[1], min_v[1]], [min_v[2], min_v[2]]),
        ([min_v[0], min_v[0]], [min_v[1], max_v[1]], [min_v[2], min_v[2]]),
        ([max_v[0], max_v[0]], [min_v[1], max_v[1]], [min_v[2], min_v[2]]),
        ([min_v[0], max_v[0]], [max_v[1], max_v[1]], [min_v[2], min_v[2]]),
        # Top face
        ([min_v[0], max_v[0]], [min_v[1], min_v[1]], [max_v[2], max_v[2]]),
        ([min_v[0], min_v[0]], [min_v[1], max_v[1]], [max_v[2], max_v[2]]),
        ([max_v[0], max_v[0]], [min_v[1], max_v[1]], [max_v[2], max_v[2]]),
        ([min_v[0], max_v[0]], [max_v[1], max_v[1]], [max_v[2], max_v[2]]),
        # Vertical edges
        ([min_v[0], min_v[0]], [min_v[1], min_v[1]], [min_v[2], max_v[2]]),
        ([max_v[0], max_v[0]], [min_v[1], min_v[1]], [min_v[2], max_v[2]]),
        ([min_v[0], min_v[0]], [max_v[1], max_v[1]], [min_v[2], max_v[2]]),
        ([max_v[0], max_v[0]], [max_v[1], max_v[1]], [min_v[2], max_v[2]]),
    ]

    for i, (x, y, z) in enumerate(edges):
        ax.plot(x, y, z, c=color, linewidth=1.5, label=label if i == 0 else None)


def plot_trajectories(
    df: pd.DataFrame,
    volumes: List[Cuboid],
    event_types: Optional[List[str]] = None,
    max_per_type: int = 100,
    alpha: float = 0.5,
    figsize: Tuple[int, int] = (12, 10)
) -> plt.Figure:
    """
    Plot photon trajectories colored by event type.

    Parameters
    ----------
    df : pd.DataFrame
        Results dataframe with 'trajectory' and 'event_type' columns
    volumes : List[Cuboid]
        Volumes to show as wireframes
    event_types : List[str], optional
        Which event types to plot (plots all if None)
    max_per_type : int
        Maximum trajectories to plot per event type
    alpha : float
        Transparency for trajectory lines
    figsize : Tuple[int, int]
        Figure size

    Returns
    -------
    plt.Figure
        Figure with 3D trajectory plot
    """
    fig = plt.figure(figsize=figsize)
    ax = fig.add_subplot(111, projection='3d')

    # Plot geometry
    plot_geometry_3d(volumes, ax=ax)

    # Determine event types to plot
    if event_types is None:
        event_types = df['event_type'].unique()

    # Color map for event types
    color_map = {
        'arrived': 'black',
        'lost_bulk': 'gray',
        'lost_lc': 'blue',
        'lost_wls': 'red',
        'lost_dm': 'orange',
        'lost_lar_gap': 'cyan',
    }

    for event_type in event_types:
        df_subset = df[df['event_type'] == event_type].head(max_per_type)
        color = color_map.get(event_type, 'pink')

        for i, traj_str in enumerate(df_subset['trajectory']):
            # Parse trajectory string
            points = [list(map(float, p.split(','))) for p in traj_str.split(';')]
            points = np.array(points)

            if len(points) < 2:
                continue

            ax.plot(
                points[:, 0], points[:, 1], points[:, 2],
                c=color, alpha=alpha, linewidth=0.5,
                label=event_type if i == 0 else None
            )

    ax.set_title('Photon Trajectories')
    ax.legend()

    return fig


def plot_event_statistics(
    df: pd.DataFrame,
    figsize: Tuple[int, int] = (15, 5)
) -> plt.Figure:
    """
    Plot histograms of reflection, TIR, and refraction counts.

    Parameters
    ----------
    df : pd.DataFrame
        Results dataframe
    figsize : Tuple[int, int]
        Figure size

    Returns
    -------
    plt.Figure
        Figure with statistics plots
    """
    fig, axes = plt.subplots(1, 3, figsize=figsize)

    metrics = ['n_reflections', 'n_tir', 'n_refractions']
    titles = ['Total Reflections', 'Total Internal Reflections', 'Refractions']

    event_types = df['event_type'].unique()
    colors = plt.cm.tab10(np.linspace(0, 1, len(event_types)))

    for ax, metric, title in zip(axes, metrics, titles):
        data = [df[df['event_type'] == et][metric] for et in event_types]
        ax.hist(data, bins=30, stacked=True, label=event_types,
                color=colors, alpha=0.8)
        ax.set_xlabel(metric.replace('_', ' ').title())
        ax.set_ylabel('Count')
        ax.set_title(title)
        ax.set_yscale('log')
        ax.legend(fontsize=8)
        ax.grid(alpha=0.3)

    plt.tight_layout()
    return fig


def plot_path_length_distribution(
    df: pd.DataFrame,
    figsize: Tuple[int, int] = (10, 6)
) -> plt.Figure:
    """
    Plot stacked histogram of path lengths by event type.

    Parameters
    ----------
    df : pd.DataFrame
        Results dataframe
    figsize : Tuple[int, int]
        Figure size

    Returns
    -------
    plt.Figure
        Figure with path length histogram
    """
    fig, ax = plt.subplots(figsize=figsize)

    event_types = df['event_type'].unique()
    colors = plt.cm.tab10(np.linspace(0, 1, len(event_types)))

    data = [df[df['event_type'] == et]['path_length'] for et in event_types]

    ax.hist(data, bins=50, stacked=True, label=event_types,
            color=colors, alpha=0.8)
    ax.set_xlabel('Path Length [m]')
    ax.set_ylabel('Number of Photons')
    ax.set_yscale('log')
    ax.set_title('Photon Path Lengths by Event Type')
    ax.legend()
    ax.grid(alpha=0.3)

    plt.tight_layout()
    return fig
