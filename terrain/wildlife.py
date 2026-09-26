"""Deterministic streamed population for the finished arctic assets.

Animals and scenery are placed in world coordinates, then owned by one terrain chunk,
so streaming never duplicates actors at chunk boundaries. Asset hierarchies are imported once
as hidden source objects and copied with their rig/actions into the owning chunk.
"""
import hashlib
import math
import os
import random

import numpy as np

from .config import CHUNK_SIZE, MILE, SEED

_ASSETS = {
    "penguin": "Penguin_Animated.glb",
    "fox": "ArcticFox_Animated.glb",
    "fish": "Fish Animated.glb",
    "orca": "Orca_Animated.glb",
    "bear": "Polar Bear Animated.glb",
    "cabin": "Scenery/Winter Cabin.glb",
    "village": "Scenery/Snowy Village.glb",
}


def _seed(*parts):
    value = ":".join(map(str, (SEED,) + parts)).encode()
    return random.Random(int.from_bytes(hashlib.blake2b(value, digest_size=8).digest(), "little"))


def _sample(a, x, y, ctx):
    n = ctx.res
    u = np.clip((x-ctx.origin[0])/ctx.size*(n-1), 0, n-1.000001)
    v = np.clip((y-ctx.origin[1])/ctx.size*(n-1), 0, n-1.000001)
    i, j = int(u), int(v)
    fx, fy = u-i, v-j
    return float((1-fy)*((1-fx)*a[j,i]+fx*a[j,i+1]) + fy*((1-fx)*a[j+1,i]+fx*a[j+1,i+1]))


def _inside(x, y, ctx, margin=0.0):
    return (ctx.origin[0]+margin <= x < ctx.origin[0]+ctx.size-margin and
            ctx.origin[1]+margin <= y < ctx.origin[1]+ctx.size-margin)


def _sources(name):
    """Load one source hierarchy and cache it outside streamed chunk ownership."""
    import bpy
    # Reuse saved sources after reopening, and never keep invalid RNA references
    # across a scene reset or load.
    col = bpy.data.collections.get("_WildlifeSource_"+name)
    if col and col.objects:
        imported = list(col.objects)
        return imported, [o for o in imported if o.parent not in imported]
    path = os.path.normpath(os.path.join(os.path.dirname(os.path.dirname(__file__)), _ASSETS[name]))
    if not os.path.isfile(path):
        return []
    before = set(bpy.data.objects)
    bpy.ops.import_scene.gltf(filepath=path)
    imported = list(set(bpy.data.objects)-before)
    # glTF's generated bone display shapes are editor helpers, not wildlife meshes.
    shapes = {bone.custom_shape for ob in imported if ob.type == 'ARMATURE'
              for bone in ob.pose.bones if bone.custom_shape is not None}
    imported = [ob for ob in imported if ob not in shapes]
    for shape in shapes:
        shape.hide_render = True
        shape.hide_set(True)
    if not imported:
        return []
    col = bpy.data.collections.get("_WildlifeSource_"+name) or bpy.data.collections.new("_WildlifeSource_"+name)
    if col.name not in bpy.context.scene.collection.children:
        bpy.context.scene.collection.children.link(col)
    imported_set = set(imported)
    for ob in imported:
        for user_col in list(ob.users_collection):
            user_col.objects.unlink(ob)
        col.objects.link(ob)
        ob.hide_render = True
        ob.hide_set(True)
    roots = [o for o in imported if o.parent not in imported_set]
    return imported, roots


def _ambient_animation(ob, name):
    """Select a species-appropriate looping clip instead of the last imported action."""
    preferred = {"penguin":"Penguin_Idle", "fox":"ArcticFox_Idle",
                 "fish":"SwimCalm", "orca":"Orca_Swim", "bear":"Walk"}
    ad = ob.animation_data
    if not ad or name not in preferred:
        return
    tracks = list(ad.nla_tracks)
    chosen = next((t for t in tracks if t.name == preferred[name]), None)
    if chosen is None:
        return
    ad.action = None
    for track in tracks:
        track.mute = track != chosen
    for strip in chosen.strips:
        strip.repeat = 10000.0
        strip.blend_type = 'REPLACE'


def _instance(name, x, y, z, yaw, ctx, scale=1.0, props=None):
    import bpy
    source = _sources(name)
    if not source:
        return None
    originals, source_roots = source
    anchor = bpy.data.objects.new(f"Wildlife_{name}_{ctx.cx}_{ctx.cy}_{len(ctx.extra.get('wildlife', []))}", None)
    ctx.collection.objects.link(anchor)
    anchor.location = (x-ctx.origin[0], y-ctx.origin[1], z)
    anchor.rotation_euler[2] = yaw
    # These two imports carry centimetre transforms; use their evaluated dimensions.
    scale = {"cabin":12.0, "bear":18.0}.get(name, scale)
    anchor.scale = (scale, scale, scale)
    anchor.parent = ctx.root
    anchor["asset_type"] = name
    if props:
        for k, v in props.items():
            anchor[k] = v
    copies = {}
    for src in originals:
        ob = src.copy()
        ob.name = f"{src.name}_{ctx.cx}_{ctx.cy}_{len(ctx.extra.get('wildlife', []))}"
        ob.hide_render = False
        ctx.collection.objects.link(ob)
        ob.hide_set(False)
        _ambient_animation(ob, name)
        copies[src] = ob
    for src, ob in copies.items():
        ob.parent = copies.get(src.parent, anchor)
        for mod in ob.modifiers:
            if getattr(mod, "object", None) in copies:
                mod.object = copies[mod.object]
        for con in ob.constraints:
            if getattr(con, "target", None) in copies:
                con.target = copies[con.target]
    ctx.extra.setdefault("wildlife", []).append(anchor)
    return anchor


def _penguins(ctx):
    # Only visible colonies publish sites, after their terrain and slope checks.
    # Consume their exact coordinates instead of duplicating the colony's seed.
    for gx, gy, x, y in ctx.extra.get("penguin_nesting_sites", ()):
        r = _seed("penguin-flock", gx, gy)
        for _ in range(r.randint(6, 12)):
            a, d = r.random()*math.tau, math.sqrt(r.random())*(0.82*MILE)
            px, py = x+math.cos(a)*d, y+math.sin(a)*d
            yaw = r.random()*math.tau
            if (not _inside(px, py, ctx, 4.0) or
                    _sample(ctx.land, px, py, ctx) < .72 or
                    _sample(ctx.H, px, py, ctx) < 1.0):
                continue
            _instance("penguin", px, py, _sample(ctx.H, px, py, ctx)+.05,
                      yaw, ctx, scale=3.0, props={"colony_x":x,"colony_y":y})


def _foxes(ctx):
    # Only actual den meshes publish accepted sites. Do not infer neighboring
    # dens from a placement hash or clamp their terrain samples to this chunk.
    for dcx, dcy, local_x, local_y in ctx.extra.get("arctic_fox_den_sites", ()):
        den_x, den_y = ctx.origin[0]+local_x, ctx.origin[1]+local_y
        r = _seed("fox-range", dcx, dcy)
        for _ in range(r.randint(1, 3)):
            # Most sightings stay within roughly three miles; the Gaussian has
            # a soft tail rather than a hard three-mile confinement radius.
            d = abs(r.gauss(0, 1.5*MILE))
            a = r.random()*math.tau
            px, py = den_x+math.cos(a)*d, den_y+math.sin(a)*d
            yaw = r.random()*math.tau
            if not _inside(px, py, ctx, 20) or _sample(ctx.land,px,py,ctx)<.65:
                continue
            _instance("fox",px,py,_sample(ctx.H,px,py,ctx)+.05,yaw,ctx,
                      props={"den_x":den_x,"den_y":den_y,"estimated_range_m":d})

def _water_samples(ctx):
    # Hashed candidates in the chunk; sea level geometry is supplied by ocean.chunk_objects.
    if float(np.min(ctx.H)) >= 0:
        return []
    out=[]
    for iy in range(8):
        for ix in range(8):
            r=_seed("marine",ctx.cx,ctx.cy,ix,iy)
            x=ctx.origin[0]+(ix+.15+.70*r.random())*ctx.size/8
            y=ctx.origin[1]+(iy+.15+.70*r.random())*ctx.size/8
            if _sample(ctx.H,x,y,ctx)<-20:
                out.append((x,y,r))
    return out


def _animate_orca_hunt(anchor, x, y, target_x, target_y, target_z, ctx):
    """Animate a scripted approach along open water toward one fish.

    This is a one-shot authored approach, not a live predator AI simulation.
    """
    points = [(x, y)]
    dx, dy = target_x-x, target_y-y
    distance = math.hypot(dx, dy)
    if distance < 1.0:
        return
    # Sample intermediate positions so a long approach never cuts across land.
    spacing = ctx.size/(ctx.res-1)
    segments = max(1, math.ceil(distance/min(25.0,spacing/2)))
    for i in range(segments+1):
        t = i/segments
        px, py = x+dx*t, y+dy*t
        pz = -12.0+(target_z+12.0)*t
        # Bound all vertices of every cell touched by this leg and a 5 m body
        # corridor. This bounds the rendered triangles as well as interpolation.
        nt = min(1.0,(i+1)/segments)
        nx, ny = x+dx*nt,y+dy*nt
        lx,hx,ly,hy = min(px,nx)-5,max(px,nx)+5,min(py,ny)-5,max(py,ny)+5
        if not (_inside(lx,ly,ctx) and _inside(hx,hy,ctx)):
            return False
        ix0,ix1 = math.floor((lx-ctx.origin[0])/spacing),math.ceil((hx-ctx.origin[0])/spacing)
        iy0,iy1 = math.floor((ly-ctx.origin[1])/spacing),math.ceil((hy-ctx.origin[1])/spacing)
        seabed = float(np.max(ctx.H[iy0:iy1+1,ix0:ix1+1]))
        nz = -12.0+(target_z+12.0)*nt
        if seabed+4 >= min(pz,nz) or max(pz,nz)+4 >= 0:
            return False
        if 0 < i < segments:
            points.append((px, py))
    points.append((target_x, target_y))

    import bpy
    scene = bpy.context.scene
    fps = float(scene.render.fps) / max(float(scene.render.fps_base), 1e-6)
    speed_mps = 7.0
    start_frame = float(scene.frame_start)
    frame = start_frame
    start_z = -12.0
    start_loc = (x-ctx.origin[0], y-ctx.origin[1], start_z)
    anchor.rotation_euler[2] = math.atan2(dy,dx)+math.pi/2
    start_rot = anchor.rotation_euler.copy()
    anchor.location = start_loc
    anchor.keyframe_insert(data_path="location", frame=frame)
    for leg_i, ((ax, ay), (bx, by)) in enumerate(zip(points, points[1:])):
        leg = math.sqrt((bx-ax)**2+(by-ay)**2+((target_z-start_z)/(len(points)-1))**2)
        if leg < 1e-4:
            continue
        # Authored snout faces local -Y.
        anchor.rotation_euler[2] = math.atan2(by-ay, bx-ax)+math.pi/2
        anchor.keyframe_insert(data_path="rotation_euler", frame=frame)
        frame += max(1.0, leg/speed_mps*fps)
        t = (leg_i+1)/(len(points)-1)
        z = start_z+(target_z-start_z)*t
        anchor.location = (bx-ctx.origin[0], by-ctx.origin[1], z)
        anchor.keyframe_insert(data_path="location", frame=frame)
        anchor.keyframe_insert(data_path="rotation_euler", frame=frame)
    # Keep newly spawned actors at their starting pose while retaining the keyed path.
    anchor.location = start_loc
    anchor.rotation_euler = start_rot
    if anchor.animation_data and anchor.animation_data.action:
        from .streaming import _location_fcurves
        for curve in _location_fcurves(anchor.animation_data):
            for key in curve.keyframe_points:
                key.interpolation = 'LINEAR'
    scene.frame_end = max(scene.frame_end,math.ceil(frame))
    return True


def _marine(ctx):
    candidates=_water_samples(ctx)
    if not candidates:
        return
    # Fish schools: several fish per school, swimming below the open-water surface.
    schools=[]
    for x,y,r in candidates:
        if r.random()>.055:
            continue
        school=[]
        for k in range(r.randint(4,8)):
            a=r.random()*math.tau; d=r.uniform(8,55)
            fx,fy=x+math.cos(a)*d,y+math.sin(a)*d
            seabed = _sample(ctx.H,fx,fy,ctx) if _inside(fx,fy,ctx,60) else 0.0
            if seabed < -20:
                # Fish stay within 60 m of the surface and above the seabed.
                fish_z = min(-8.0, max(seabed+8.0, -60.0))
                ob=_instance("fish",fx,fy,fish_z,r.random()*math.tau,ctx,
                             scale=12.0,props={"school_id":f"{ctx.cx}:{ctx.cy}:{len(schools)}"})
                if ob: school.append((fx,fy,fish_z,ob))
        if school: schools.append((x,y,school))
    # A portion of fish schools attract a nearby orca. Derive the hunter from the
    # school key so each school gets a stable, deliberate prey relationship.
    for school_i,(sx,sy,fish) in enumerate(schools):
        hunter_rng=_seed("orca-school",ctx.cx,ctx.cy,school_i)
        if hunter_rng.random()>.30:
            continue
        nearby=[(x,y) for x,y,_ in candidates
                if 250.0 < math.hypot(sx-x,sy-y) <= 2.5*MILE
                and _sample(ctx.H,x,y,ctx)<-20]
        if not nearby:
            continue
        x,y=nearby[hunter_rng.randrange(len(nearby))]
        prey_x,prey_y,prey_z,_prey=fish[hunter_rng.randrange(len(fish))]
        hunter=_instance("orca",x,y,-12,math.atan2(prey_y-y,prey_x-x)+math.pi/2,ctx,scale=1.0,
                         props={"prey_x":prey_x,"prey_y":prey_y,"prey_z":prey_z,
                                "prey_count":len(fish),"behavior":"scripted_hunt_approach"})
        if hunter:
            if not _animate_orca_hunt(hunter,x,y,prey_x,prey_y,prey_z,ctx):
                hunter["behavior"] = "idle_open_water"


def _scenery(ctx):
    # Sparse human-scale shelters on broad, gently rising ground. A few cabins can
    # share a chunk, while each village asset is itself a small grouped settlement.
    r=_seed("scenery",ctx.cx,ctx.cy)
    if float(np.max(ctx.land))>.8:
        cabins=[]
        if r.random()<.40:
            for _ in range(20):
                x=ctx.origin[0]+r.uniform(.12,.88)*ctx.size
                y=ctx.origin[1]+r.uniform(.12,.88)*ctx.size
                if (_sample(ctx.land,x,y,ctx)>.78 and 5<_sample(ctx.H,x,y,ctx)<3000
                        and _slope_at(x,y,ctx)<.35):
                    cabins.append((x,y))
                    if len(cabins)>=r.randint(2,4):
                        break
        for x,y in cabins:
            _instance("cabin",x,y,_sample(ctx.H,x,y,ctx),r.random()*math.tau,ctx,scale=.12,
                      props={"settlement":"cabin_cluster"})

        if r.random()<.35:
            for _ in range(16):
                x=ctx.origin[0]+r.uniform(.2,.8)*ctx.size
                y=ctx.origin[1]+r.uniform(.2,.8)*ctx.size
                if (_sample(ctx.land,x,y,ctx)>.82 and 10<_sample(ctx.H,x,y,ctx)<3000
                        and _slope_at(x,y,ctx)<.28):
                    _instance("village",x,y,_sample(ctx.H,x,y,ctx),r.random()*math.tau,
                              ctx,scale=.12,props={"settlement":"snowy_village"})
                    break


def _slope_at(x,y,ctx):
    """Estimate local grade from adjacent terrain samples, in rise/run units."""
    spacing=ctx.size/(ctx.res-1)
    i=max(0,min(ctx.res-2,int((x-ctx.origin[0])/spacing)))
    j=max(0,min(ctx.res-2,int((y-ctx.origin[1])/spacing)))
    return max(abs(float(ctx.H[j,i+1]-ctx.H[j,i])),
               abs(float(ctx.H[j+1,i]-ctx.H[j,i]))) / max(spacing,1.0)


def _bears(ctx):
    """Place sparse polar bears on low coastal land within foraging distance of sea."""
    r=_seed("polar-bears",ctx.cx,ctx.cy)
    if r.random()>.70 or float(np.min(ctx.H))>=0:
        return
    sites=[]
    # Candidates stay away from chunk edges so each bear and its territory belong
    # to exactly one streamed chunk. Prefer low, level terrain near open water.
    for _ in range(120):
        x=ctx.origin[0]+r.uniform(.08,.92)*ctx.size
        y=ctx.origin[1]+r.uniform(.08,.92)*ctx.size
        h=_sample(ctx.H,x,y,ctx)
        land=_sample(ctx.land,x,y,ctx)
        if land<.35 or not 0<h<2600 or _slope_at(x,y,ctx)>.85:
            continue
        # A 5 km terrain-grid scan rewards shoreline and near-shore hunting grounds.
        i=max(0,min(ctx.res-1,int((x-ctx.origin[0])/ctx.size*(ctx.res-1))))
        j=max(0,min(ctx.res-1,int((y-ctx.origin[1])/ctx.size*(ctx.res-1))))
        radius=max(1,int(5000/ctx.size*(ctx.res-1)))
        y0,y1=max(0,j-radius),min(ctx.res,j+radius+1)
        x0,x1=max(0,i-radius),min(ctx.res,i+radius+1)
        if not np.any(ctx.H[y0:y1,x0:x1]<-5):
            continue
        if all(math.hypot(x-sx,y-sy)>6500 for sx,sy in sites):
            sites.append((x,y))
            if len(sites)>=r.randint(1,2):
                break
    for x,y in sites:
        _instance("bear",x,y,_sample(ctx.H,x,y,ctx)+.05,r.random()*math.tau,ctx,
                  scale=10.0,props={"habitat":"coastal_tundra","foraging_radius_m":3*MILE})


def chunk_objects(ctx):
    """Populate eligible chunks (full populations at near and medium LOD)."""
    if ctx.lod > 1:
        return []
    _penguins(ctx)
    _foxes(ctx)
    _marine(ctx)
    _bears(ctx)
    _scenery(ctx)
    return ctx.extra.get("wildlife", [])
