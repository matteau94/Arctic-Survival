"""Read fixed habitat locations from an already loaded Blender scene.

No scene changes, procedural regeneration, geometry export, or blend saves.
Future export integration (before any exporter mutates the scene)::

    import runpy
    helper = runpy.run_path(str(Path(__file__).with_name('habitat-waypoints.py')))
    helper['export_waypoints'](scene, Path(OUT) / 'waypoints.json')

Fox positions are the midpoint of the two inner threshold vertices documented
by terrain/arctic_fox_dens.py. Penguin centers use persisted colony_x/colony_y
metadata from terrain/wildlife.py, gated by an actual NestStones mesh; height
comes from a ray against that colony's saved terrain. Actor positions are never
used. Missing or ambiguous metadata fails explicitly rather than guessing.
"""
import json
import math
from pathlib import Path
import re

from mathutils import Vector


def _waypoint(identifier, kind, name, world):
    position = [float(world.x), float(world.z), float(-world.y)]
    if not all(math.isfinite(value) for value in position):
        raise ValueError(f'Non-finite habitat position: {identifier}')
    return dict(id=identifier, type=kind, name=name, position=position)


def extract_waypoints(scene):
    """Return {waypoints: [...]} in viewer coordinates, using saved meshes only."""
    result = []
    offset = scene.get('terrain_offset', (0.0, 0.0))
    for obj in sorted(scene.objects, key=lambda item: item.name):
        if obj.type != 'MESH':
            continue
        den = re.fullmatch(r'FoxDen_Entrance_(-?\d+)_(-?\d+)', obj.name)
        colony = re.fullmatch(r'PenguinColony_(-?\d+)_(-?\d+)_NestStones', obj.name)
        if den:
            if len(obj.data.vertices) != 10:
                raise ValueError(f'Unexpected entrance topology: {obj.name}')
            local = (obj.data.vertices[5].co + obj.data.vertices[6].co) * 0.5
            tag = '_'.join(den.groups())
            result.append(_waypoint(f'fox_den_{tag}', 'fox_den',
                                    f'Arctic fox den ({tag.replace("_", ", ")})',
                                    obj.matrix_world @ local))
        elif colony:
            if not obj.data.vertices or obj.parent is None:
                raise ValueError(f'Empty or unparented colony: {obj.name}')
            sites = {(float(actor['colony_x']), float(actor['colony_y']))
                     for actor in obj.parent.children
                     if actor.get('asset_type') == 'penguin'
                     and 'colony_x' in actor and 'colony_y' in actor}
            if len(sites) != 1:
                raise ValueError(f'Expected one persisted colony center for {obj.name}: {sites}')
            tag = '_'.join(colony.groups())
            terrain = scene.objects.get(f'Terrain_{tag}')
            if terrain is None or terrain.type != 'MESH' or terrain.parent != obj.parent:
                raise ValueError(f'Missing owning terrain for {obj.name}')
            x, y = next(iter(sites))
            # Metadata is absolute procedural XY; the saved scene uses a floating origin.
            top = max((terrain.matrix_world @ Vector(corner)).z
                      for corner in terrain.bound_box) + 1.0
            origin = Vector((x - offset[0], y - offset[1], top))
            inverse = terrain.matrix_world.inverted()
            direction = (inverse.to_3x3() @ Vector((0, 0, -1))).normalized()
            hit, point, _normal, _face = terrain.ray_cast(inverse @ origin, direction)
            if not hit:
                raise ValueError(f'Colony center misses saved terrain: {obj.name}')
            result.append(_waypoint(f'penguin_nest_{tag}', 'penguin_nest',
                                    f'Penguin nesting colony ({tag.replace("_", ", ")})',
                                    terrain.matrix_world @ point))
    return {'waypoints': sorted(result, key=lambda item: item['id'])}


def export_waypoints(scene, output_path):
    """Write only the small JSON manifest; return the extracted payload."""
    payload = extract_waypoints(scene)
    destination = Path(output_path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(json.dumps(payload, separators=(',', ':'), allow_nan=False) + '\n',
                           encoding='utf-8')
    return payload
