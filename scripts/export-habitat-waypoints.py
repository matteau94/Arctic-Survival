"""Run in background Blender against the saved world, without saving it.

blender --background --factory-startup --disable-autoexec Terrain_World.blend \
    --python-exit-code 1 --python scripts/export-habitat-waypoints.py

Optional arguments after --: --output PATH. This exports JSON only.
"""
import argparse
from collections import Counter
from pathlib import Path
import runpy
import sys

import bpy


def main():
    root = Path(__file__).resolve().parents[1]
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=root / 'viewer/data/waypoints.json')
    args = parser.parse_args(sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else [])
    if not bpy.data.filepath:
        raise RuntimeError('Load the saved Terrain_World.blend before running this script.')
    if args.output.suffix.lower() != '.json':
        raise ValueError('Waypoint output must be a .json file.')
    helper = runpy.run_path(str(root / 'viewer/habitat-waypoints.py'))
    payload = helper['export_waypoints'](bpy.context.scene, args.output)
    counts = Counter(item['type'] for item in payload['waypoints'])
    print('HABITAT_WAYPOINTS', dict(counts), 'source:', bpy.data.filepath,
          'output:', args.output, 'bytes:', args.output.stat().st_size)


if __name__ == '__main__':
    main()
