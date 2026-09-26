"""Small deterministic, world-coordinate terrain relief layer.

Registration point: add ``chunk_variation.height_delta(X, Y, land)`` to ``h`` in
``terrain.world.height`` after the existing feature pipeline. This file is standalone.
"""
import numpy as np

from .config import CONTINENT_RADIUS, WORLD_RADIUS

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
    return result


def height_delta(X, Y, land):
    """Return seamless deterministic relief in metres for broadcastable world arrays.

    Relief peaks around 25 m before land weighting, adding gentle roll to the ice
    sheet and moderate texture across mountain/valley terrain. It smoothly fades
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
    return _field(X, Y) * (0.25 + 0.75 * land) * offshore_fade


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
