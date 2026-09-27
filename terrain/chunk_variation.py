"""Deterministic, world-coordinate rolling foothills and regional relief.

Registration point: add ``chunk_variation.height_delta(X, Y, land)`` to ``h`` in
``terrain.world.height`` before valley, river, and coast carving.
"""
import numpy as np

from .config import CONTINENT_RADIUS, WORLD_RADIUS
from .config import SEED
from .mountains import _fbm, _sstep

# Incommensurate directions and metre-scale spatial frequencies avoid a short
# repeating chunk template. Components span regional undulation to local ridges.
_COMPONENTS = (
    (1 / 151_000.0, 0.37, 2.2),
    (1 / 93_000.0, 1.91, 3.5),
    (1 / 57_000.0, 2.73, 4.0),
    (1 / 34_000.0, 0.84, 4.5),
    (1 / 19_000.0, 2.21, 5.0),
    (1 / 10_000.0, 1.36, 4.0),
    (1 / 5_400.0, 0.11, 3.0),
)


def _field(X, Y):
    result = np.zeros(np.broadcast_shapes(np.shape(X), np.shape(Y)), dtype=np.float64)
    for freq, angle, amplitude in _COMPONENTS:
        phase = np.remainder(
            freq * (np.cos(angle) * X + np.sin(angle) * Y), 2.0 * np.pi
        )
        result += amplitude * np.sin(phase)
    # Noise uses an arithmetic hash, so this layer has no 256-cell permutation
    # repeat. Wavelengths are resolvable by the near 100 m terrain mesh.
    regional = _fbm(X, Y, SEED + 1900, 1 / 42000.0, 3)
    wx = X + 1600.0 * _fbm(X, Y, SEED + 1901, 1 / 14000.0, 2)
    wy = Y + 1600.0 * _fbm(X, Y, SEED + 1902, 1 / 14000.0, 2)
    hills = _fbm(wx, wy, SEED + 1903, 1 / 3800.0, 3)
    strength = 0.35 + 0.65 * _sstep(-0.25, 0.35, regional)
    return result + 210.0 * regional + 260.0 * strength * hills


def height_delta(X, Y, land):
    """Return seamless deterministic relief in metres for broadcastable world arrays.

    Regional swells and kilometre-scale foothills add tens to hundreds of metres
    of relief before the downstream valley and frozen-river carving. It fades
    offshore toward the playable world's outer edge. Identical world coordinates
    always produce identical values, independent of chunk or evaluation order.
    """
    X, Y, land = np.broadcast_arrays(
        np.asarray(X, dtype=np.float64),
        np.asarray(Y, dtype=np.float64),
        np.clip(np.asarray(land, dtype=np.float64), 0.0, 1.0),
    )
    radius = np.hypot(X, Y)
    t = np.clip(
        (WORLD_RADIUS - radius) / max(WORLD_RADIUS - 0.78 * CONTINENT_RADIUS, 1.0),
        0.0, 1.0,
    )
    offshore_fade = t * t * (3.0 - 2.0 * t)
    # Fractional land masks soften the coastal transition; full land retains relief.
    return _field(X, Y) * _sstep(0.25, 1.0, land) * offshore_fade


def diagnose_chunk_matrix(cx0=-2, cy0=-2, width=5, chunk_size=None):
    """Return relief values and summary statistics sampled at chunk centers."""
    if width < 1:
        raise ValueError("width must be positive")
    if chunk_size is None:
        from .config import CHUNK_SIZE
        chunk_size = CHUNK_SIZE
    cx, cy = np.meshgrid(
        np.arange(cx0, cx0 + width, dtype=np.float64),
        np.arange(cy0, cy0 + width, dtype=np.float64),
    )
    values = height_delta((cx + 0.5) * chunk_size, (cy + 0.5) * chunk_size,
                          np.ones_like(cx))
    return {
        "values_m": values,
        "mean_m": float(values.mean()),
        "std_m": float(values.std()),
        "min_m": float(values.min()),
        "max_m": float(values.max()),
        "distinct_centers": int(np.unique(np.round(values, 3)).size),
    }
