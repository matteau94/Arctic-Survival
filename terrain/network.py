"""Shared drainage network: where valleys (and the frozen rivers in them) run.

Channels are the zero-contours of domain-warped low-frequency noise. Distance to the nearest
channel is estimated as |n| / |grad n| (first-order signed-distance), which is exact enough for
carving at these scales and is a pure per-point function -> chunk-independent.

Two tiers:
  major: big glacial trunk valleys, spacing ~40-80 km, meander on ~20 km scale.
  minor: tributary valleys, spacing ~8-15 km.
valleys.py carves around these; rivers.py places ice ribbons on the major (and some minor)
centre-lines; mountains.py can use them to keep ridges between channels.
"""
import numpy as np
from . import noise as N
from .config import SEED

MAJOR_FREQ = 1.0 / 60000.0
MINOR_FREQ = 1.0 / 12000.0


def _channel_distance(X, Y, seed, freq, warp_amt):
    wx, wy = N.warp(X, Y, seed + 3, freq * 0.6, warp_amt, octaves=2)
    n, gx, gy = N.perlin(wx, wy, seed, freq, with_grad=True)
    # chain-rule ignored for warp (warp is low-frequency, error is small and smooth)
    g = np.sqrt(gx * gx + gy * gy) + 1e-12
    return np.abs(n) / g, n


def major_distance(X, Y):
    """Metres to the nearest major valley centre-line, and the raw signed noise."""
    return _channel_distance(X, Y, SEED + 500, MAJOR_FREQ, 18000.0)


def minor_distance(X, Y):
    """Metres to the nearest minor (tributary) valley centre-line."""
    return _channel_distance(X, Y, SEED + 700, MINOR_FREQ, 4000.0)
