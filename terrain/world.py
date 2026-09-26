"""Composition of the terrain. THIS FILE IS THE CONTRACT between feature modules.

Every feature module is a pure function of world coordinates (numpy float64 arrays, metres)
so chunks can be generated in any order and always match at the seams.

Height pipeline (in order):
    base, land = ocean.continent(X, Y)          # ice-sheet plateau + sea floor, land in [0,1]
    h  = base + mountains.height(X, Y, land)    # additive ranges (0 over sea)
    h  = valleys.carve(X, Y, h, land)           # U-shaped glacial valleys along network.py
    h  = rivers.carve(X, Y, h, land)            # flat frozen river beds in valley floors
    h  = ocean.coast(X, Y, h, land)             # ice cliffs, shelves, fjords, beaches

Surface masks (floats in [0,1] per vertex, written into a dict by each module's surface()):
    'snow', 'rock', 'ice' (river/lake/sea ice, blue-ish), 'water' (open sea floor/under water)
World computes a default snow/rock split from slope first, then modules override.

Extra per-chunk geometry (water plane, sea ice, icebergs, river ice ribbons, ...):
    module.chunk_objects(ctx) -> list[bpy.types.Object]
ctx is a ChunkContext (below). Objects MUST be built in chunk-local coordinates (world
minus ctx.origin) and parented to ctx.root with identity local transform; streaming.py handles
placement / floating origin. Keep object counts low (instancing / merged meshes).
"""
import numpy as np
from dataclasses import dataclass, field
from .config import CHUNK_SIZE, LOD_RES
from . import ocean, mountains, valleys, rivers

FEATURES = (ocean, mountains, valleys, rivers)


def height(X, Y, return_land=False):
    X = np.asarray(X, dtype=np.float64); Y = np.asarray(Y, dtype=np.float64)
    base, land = ocean.continent(X, Y)
    h = base + mountains.height(X, Y, land)
    h = valleys.carve(X, Y, h, land)
    h = rivers.carve(X, Y, h, land)
    h = ocean.coast(X, Y, h, land)
    return (h, land) if return_land else h


def surface(X, Y, H, land, spacing):
    """Per-vertex surface masks for a regular grid (H shape = X shape, row-major y, x).
    streaming.py passes a grid padded by one sample on every side (then crops), so module
    surface() functions must not assume the chunk resolution."""
    gy, gx = np.gradient(H, spacing)
    slope = np.sqrt(gx * gx + gy * gy)
    rock = np.clip((slope - 0.55) / 0.35, 0.0, 1.0)
    masks = {'snow': 1.0 - rock, 'rock': rock,
             'ice': np.zeros_like(H), 'water': np.zeros_like(H), 'slope': slope}
    for m in FEATURES:
        f = getattr(m, 'surface', None)
        if f is not None:
            f(X, Y, H, land, masks)
    return masks


@dataclass
class ChunkContext:
    cx: int                     # chunk index (x)
    cy: int                     # chunk index (y)
    lod: int                    # ring distance from player chunk (0, 1, 2)
    res: int                    # vertices per edge
    origin: tuple               # world metres of the chunk's SW corner (x0, y0)
    size: float                 # CHUNK_SIZE
    X: np.ndarray               # (res, res) world x of grid vertices
    Y: np.ndarray
    H: np.ndarray               # heights
    land: np.ndarray
    root: object = None         # bpy Object (empty) to parent extra geometry to
    collection: object = None   # bpy Collection to link new objects into
    extra: dict = field(default_factory=dict)


def sample_chunk(cx, cy, lod):
    res = LOD_RES[min(lod, max(LOD_RES))]
    x0, y0 = cx * CHUNK_SIZE, cy * CHUNK_SIZE
    t = np.arange(res) / (res - 1)               # exact shared edges across chunks and LODs
    X, Y = np.meshgrid((cx + t) * CHUNK_SIZE, (cy + t) * CHUNK_SIZE)   # rows = y, cols = x
    H, land = height(X, Y, return_land=True)
    return ChunkContext(cx, cy, lod, res, (x0, y0), CHUNK_SIZE, X, Y, H, land)


def chunk_of(x, y):
    return int(np.floor(x / CHUNK_SIZE)), int(np.floor(y / CHUNK_SIZE))
