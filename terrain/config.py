"""World constants shared by every terrain module.

Units: 1 Blender unit = 1 metre. +X east, +Y north, +Z up. The world origin is deep in the
interior of the continent (near the "pole"). Heights are metres above sea level (SEA_LEVEL = 0).
"""
MILE = 1609.344
CHUNK_MILES = 16
CHUNK_SIZE = CHUNK_MILES * MILE          # 25 749.5 m per chunk edge
VIEW_RADIUS = 2                          # chunks loaded in each direction -> 5x5 grid

SEED = 1337
SEA_LEVEL = 0.0

# Continent: roughly circular ice-covered landmass centred on the origin, coastline
# CONTINENT_RADIUS away (noisy), Southern-Ocean-style sea beyond it out to WORLD_RADIUS.
CONTINENT_RADIUS = 1400 * MILE           # ~2 250 km  (continent is ~2 800 miles across)
WORLD_RADIUS = 2500 * MILE               # playable world ends in open ocean past this
PLATEAU_HEIGHT = 2800.0                  # interior ice-sheet elevation (m)

# Mesh resolution per chunk by ring distance (Chebyshev) from the player's chunk.
# Vertices per edge; the grid spacing is CHUNK_SIZE / (n - 1).
LOD_RES = {0: 257, 1: 129, 2: 65}

# Coastal spawn near a fjord, chosen so the initial streamed window includes land, sea,
# penguin habitat and coastal wildlife rather than only the interior ice sheet.
SPAWN = (1_961_940.0, 752_276.0)
