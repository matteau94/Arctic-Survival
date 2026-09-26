"""Check saved population hierarchies and habitat metadata in Blender."""
import collections
import math
import bpy

actors = [o for o in bpy.data.objects if o.get('asset_type')]
counts = collections.Counter(o['asset_type'] for o in actors)
assert 'human' not in counts
for actor in actors:
    assert actor.parent and actor.parent.name.startswith('Chunk_')
    assert not any(o.name.startswith('Icosphere') for o in actor.children_recursive)
    if actor['asset_type'] == 'penguin':
        wx = actor.parent['cx'] * 25749.504 + actor.location.x
        wy = actor.parent['cy'] * 25749.504 + actor.location.y
        assert math.hypot(wx-actor['colony_x'], wy-actor['colony_y']) <= 1609.344
    for rig in actor.children_recursive:
        if rig.type == 'ARMATURE':
            assert rig.animation_data and any(not t.mute for t in rig.animation_data.nla_tracks)
            for ob in actor.children_recursive:
                for modifier in ob.modifiers:
                    if modifier.type == 'ARMATURE':
                        assert modifier.object in actor.children_recursive
print('POPULATION_CHECK_OK', dict(counts))
