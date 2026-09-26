"""Minecraft-style chunk streaming for the polar world.

ChunkManager keeps exactly (2*VIEW_RADIUS+1)^2 chunks loaded around a target object
("Player" empty, else the scene camera):

* Chunk (cx, cy) = root EMPTY "Chunk_{cx}_{cy}" in collection "TerrainChunks"; children are the
  terrain mesh "Terrain_{cx}_{cy}" plus whatever each feature module's chunk_objects(ctx) returns.
* LOD by Chebyshev ring (config.LOD_RES); ring change -> rebuild. Cracks between LODs are
  hidden by vertical skirts hanging from the chunk perimeter.
* Seams: vertices are sampled at X = (cx + i/(res-1)) * CHUNK_SIZE, which is bit-identical on
  both sides of a shared edge (and at coincident vertices of different LODs). Normals and
  surface masks are computed on a grid padded by one sample, so they are seam-free too.
* Floating origin: scene["terrain_offset"] = WORLD_OFFSET (x, y) in metres. Blender location =
  world - offset. When the target gets > REBASE_DIST from the Blender origin the offset is
  shifted to the target's chunk centre and the target, chunk roots, free cameras (and the
  target's location keyframes) are moved. Player["world_x"/"world_y"] always holds true metres.
* Hysteresis: the centre chunk only changes once the target is HYSTERESIS metres inside a
  neighbouring chunk.
* Budget: update(budget=N) performs at most N builds (nearest first). load_all_now() drains.

Live use: register() installs @persistent depsgraph_update_post / frame_change_post /
load_post handlers and a 0.25 s timer.
"""
import math
import time
import traceback

import bpy
import numpy as np
from bpy.app.handlers import persistent

from . import config as C
from . import world
from . import materials

COLLECTION = "TerrainChunks"
PLAYER = "Player"
OFFSET_PROP = "terrain_offset"
HYSTERESIS = 0.08 * C.CHUNK_SIZE        # ~2 km past a border before the grid re-centres
REBASE_DIST = 1.0 * C.CHUNK_SIZE        # re-base once > 1 chunk from the Blender origin
DEFAULT_BUDGET = 2                      # max chunk builds per update
TIME_BUDGET = 0.12                      # s; stop early (after >=1 build) to keep the UI live
TIMER_INTERVAL = 0.25
EYE_HEIGHT = 1.7

VERBOSE = True


def log(*a):
    if VERBOSE:
        print("[streaming]", *a)


# ============================================================================ sampling
def lod_res(lod):
    return C.LOD_RES[min(lod, max(C.LOD_RES))]


def sample_chunk(cx, cy, lod):
    """Like world.sample_chunk but (a) bit-exact seams, (b) 1-sample padding so gradients
    (normals, slope masks) are seam-free. Returns (ctx, masks, normals)."""
    res = lod_res(lod)
    step = C.CHUNK_SIZE / (res - 1)
    i = np.arange(-1, res + 1, dtype=np.float64)
    t = i / (res - 1)                                   # exact k/(res-1) fractions
    xs = (cx + t) * C.CHUNK_SIZE
    ys = (cy + t) * C.CHUNK_SIZE
    Xe, Ye = np.meshgrid(xs, ys)
    He, Le = world.height(Xe, Ye, return_land=True)
    masks_e = world.surface(Xe, Ye, He, Le, step)
    # normals by central difference on the padded grid (identical formula on both sides)
    dzdx = (He[1:-1, 2:] - He[1:-1, :-2]) / (xs[2:] - xs[:-2])[None, :]
    dzdy = (He[2:, 1:-1] - He[:-2, 1:-1]) / (ys[2:] - ys[:-2])[:, None]
    nrm = np.stack([-dzdx, -dzdy, np.ones_like(dzdx)], axis=-1)
    nrm /= np.linalg.norm(nrm, axis=-1, keepdims=True)
    s = (slice(1, -1), slice(1, -1))
    masks = {k: (np.asarray(v)[s] if np.ndim(v) == 2 and np.shape(v) == He.shape else v)
             for k, v in masks_e.items()}
    ctx = world.ChunkContext(cx, cy, lod, res, (cx * C.CHUNK_SIZE, cy * C.CHUNK_SIZE),
                             C.CHUNK_SIZE, Xe[s], Ye[s], He[s], Le[s])
    ctx.extra['masks'] = masks
    ctx.extra['spacing'] = step
    return ctx, masks, nrm


def height_at(x, y):
    return float(world.height(np.array([[x]], np.float64), np.array([[y]], np.float64))[0, 0])


# ============================================================================ mesh build
_TOPO_CACHE = {}


def _topology(res):
    """Loop vertex indices for grid quads + skirt quads, and the perimeter index loop."""
    tp = _TOPO_CACHE.get(res)
    if tp is not None:
        return tp
    n = res
    r, c = np.meshgrid(np.arange(n - 1), np.arange(n - 1), indexing='ij')
    i0 = (r * n + c).ravel()
    grid = np.stack([i0, i0 + 1, i0 + n + 1, i0 + n], axis=1)
    # perimeter, CCW seen from above: S (c++), E (r++), N (c--), W (r--)
    S = [0 * n + k for k in range(n - 1)]
    E = [k * n + (n - 1) for k in range(n - 1)]
    N = [(n - 1) * n + (n - 1 - k) for k in range(n - 1)]
    W = [(n - 1 - k) * n for k in range(n - 1)]
    per = np.array(S + E + N + W, dtype=np.int64)
    P = len(per)
    bot = n * n + np.arange(P)
    nxt = np.roll(np.arange(P), -1)
    skirt = np.stack([per, bot, bot[nxt], per[nxt]], axis=1)   # outward-facing
    loops = np.concatenate([grid, skirt]).astype(np.int32).ravel()
    tp = (loops, per, (n - 1) ** 2 + P)
    _TOPO_CACHE[res] = tp
    return tp


def build_terrain_mesh(name, ctx, masks, nrm):
    res = ctx.res
    loops, per, nfaces = _topology(res)
    step = C.CHUNK_SIZE / (res - 1)
    t = np.arange(res, dtype=np.float64) / (res - 1) * C.CHUNK_SIZE
    lx, ly = np.meshgrid(t, t)
    H = ctx.H
    # skirt depth: covers any LOD crack along this edge (bounded by local edge relief)
    eh = H.ravel()[per]
    dh = np.abs(np.diff(np.append(eh, eh[0])))
    depth = 20.0 + 0.25 * step + 2.0 * float(dh.max())
    ctx.extra['skirt_depth'] = depth

    nv = res * res + len(per)
    co = np.empty((nv, 3), np.float64)
    co[:res * res, 0] = lx.ravel(); co[:res * res, 1] = ly.ravel(); co[:res * res, 2] = H.ravel()
    co[res * res:] = co[per]
    co[res * res:, 2] -= depth

    me = bpy.data.meshes.new(name)
    me.vertices.add(nv)
    try:                                    # attribute path is ~50x faster than 'co'
        me.attributes['position'].data.foreach_set('vector', co.astype(np.float32).ravel())
    except Exception:
        me.vertices.foreach_set('co', co.astype(np.float32).ravel())
    me.loops.add(len(loops))
    try:
        me.attributes['.corner_vert'].data.foreach_set('value', loops)
    except Exception:
        me.loops.foreach_set('vertex_index', loops)
    me.polygons.add(nfaces)
    me.polygons.foreach_set('loop_start', np.arange(0, 4 * nfaces, 4, dtype=np.int32))
    me.update(calc_edges=True)

    # packed surface masks: R snow, G rock, B ice, A water
    rgba = np.empty((res * res, 4), np.float32)
    for k, key in enumerate(('snow', 'rock', 'ice', 'water')):
        v = masks.get(key)
        rgba[:, k] = 0.0 if v is None else np.clip(np.asarray(v, np.float64).ravel(), 0, 1)
    rgba = np.concatenate([rgba, rgba[per]])
    ca = me.color_attributes.new(materials.SURF_ATTR, 'FLOAT_COLOR', 'POINT')
    ca.data.foreach_set('color', rgba.ravel())
    me.color_attributes.active_color = ca
    me.color_attributes.render_color_index = me.color_attributes.find(materials.SURF_ATTR)

    # smooth + seam-exact custom normals (skirt verts inherit the edge normal)
    n3 = nrm.reshape(-1, 3)
    n3 = np.concatenate([n3, n3[per]]).astype(np.float32)
    me.shade_smooth()
    try:
        a = me.attributes.new('custom_normal', 'FLOAT_VECTOR', 'POINT')
        a.data.foreach_set('vector', n3.ravel())
    except Exception:
        me.normals_split_custom_set_from_vertices(n3.tolist())
    me.materials.append(materials.terrain_material())
    return me


# ============================================================================ scene helpers
def get_collection(scene=None):
    scene = scene or bpy.context.scene
    col = bpy.data.collections.get(COLLECTION)
    if col is None:
        col = bpy.data.collections.new(COLLECTION)
    if col.name not in scene.collection.children:
        scene.collection.children.link(col)
    return col


def get_offset(scene):
    v = scene.get(OFFSET_PROP)
    return (float(v[0]), float(v[1])) if v is not None else (0.0, 0.0)


def set_offset(scene, ox, oy):
    scene[OFFSET_PROP] = (float(ox), float(oy))
    materials.set_offset(ox, oy)


def find_target(scene):
    p = bpy.data.objects.get(PLAYER)
    if p is not None and p.name in scene.objects:
        return p
    return scene.camera


def _collect_tree(obj, out):
    out.append(obj)
    for ch in obj.children:
        _collect_tree(ch, out)


def remove_objects(objs):
    """Delete objects + their now-unused data and non-shared materials."""
    datas, mats = [], []
    for o in objs:
        if o.data is not None:
            datas.append(o.data)
            mats += [m for m in getattr(o.data, 'materials', []) if m is not None]
        mats += [s.material for s in o.material_slots if s.material is not None]
    bpy.data.batch_remove(list({o.as_pointer(): o for o in objs}.values()))
    dead = []
    for d in {d.as_pointer(): d for d in datas}.values():
        try:
            if d.users == 0:
                dead.append(d)
        except ReferenceError:
            pass
    if dead:
        bpy.data.batch_remove(dead)
    dead = []
    for m in {m.as_pointer(): m for m in mats}.values():
        try:
            if m.users == 0 and not m.use_fake_user:
                dead.append(m)
        except ReferenceError:
            pass
    if dead:
        bpy.data.batch_remove(dead)


# ============================================================================ manager
class ChunkManager:
    def __init__(self, scene=None, radius=C.VIEW_RADIUS, budget=DEFAULT_BUDGET):
        self.scene = scene or bpy.context.scene
        self.radius = radius
        self.budget = budget
        self.center = None                 # (cx, cy) the grid is built around
        self.chunks = {}                   # (cx, cy) -> {'root': obj, 'lod': int}
        self.queue = []
        self.stats = []                    # (cx, cy, lod, seconds)
        self._busy = False
        self._last_xy = None
        self.adopt_existing()

    # ------------------------------------------------------------------ state
    def adopt_existing(self):
        """Re-attach to chunks already in the file (after load)."""
        col = bpy.data.collections.get(COLLECTION)
        if col is None:
            return
        for o in list(col.objects):
            if o.parent is None and o.name.startswith("Chunk_") and "cx" in o:
                key = (int(o["cx"]), int(o["cy"]))
                if key in self.chunks:          # duplicate (shouldn't happen) -> drop
                    t = []; _collect_tree(o, t); remove_objects(t)
                    continue
                self.chunks[key] = {'root': o, 'lod': int(o.get("lod", 0))}
        if self.chunks:
            c = self.scene.get("terrain_center")
            if c is not None:
                self.center = (int(c[0]), int(c[1]))

    def target_world_xy(self, target):
        ox, oy = get_offset(self.scene)
        loc = _loc(target)
        return loc.x + ox, loc.y + oy

    def ring(self, key):
        return max(abs(key[0] - self.center[0]), abs(key[1] - self.center[1]))

    def desired(self):
        cx, cy = self.center
        r = self.radius
        return {(cx + i, cy + j): max(abs(i), abs(j))
                for i in range(-r, r + 1) for j in range(-r, r + 1)}

    # ------------------------------------------------------------------ centre / hysteresis
    def _update_center(self, wx, wy):
        pc = world.chunk_of(wx, wy)
        if self.center is None:
            self.center = pc
        elif pc != self.center:
            cx, cy = self.center
            x0, y0 = cx * C.CHUNK_SIZE - HYSTERESIS, cy * C.CHUNK_SIZE - HYSTERESIS
            x1, y1 = (cx + 1) * C.CHUNK_SIZE + HYSTERESIS, (cy + 1) * C.CHUNK_SIZE + HYSTERESIS
            if not (x0 <= wx <= x1 and y0 <= wy <= y1):
                self.center = pc
        cur = self.scene.get("terrain_center")
        if cur is None or tuple(cur) != tuple(self.center):
            self.scene["terrain_center"] = self.center

    # ------------------------------------------------------------------ floating origin
    def maybe_rebase(self, target, force=False):
        loc = _loc(target)
        if not force and max(abs(loc.x), abs(loc.y)) <= REBASE_DIST:
            return False
        ox, oy = get_offset(self.scene)
        wx, wy = loc.x + ox, loc.y + oy
        cx, cy = world.chunk_of(wx, wy)
        nox, noy = (cx + 0.5) * C.CHUNK_SIZE, (cy + 0.5) * C.CHUNK_SIZE
        dx, dy = nox - ox, noy - oy
        if dx == 0 and dy == 0:
            return False
        self.shift_scene(dx, dy, target)
        set_offset(self.scene, nox, noy)
        log(f"re-based: offset ({ox:.0f},{oy:.0f}) -> ({nox:.0f},{noy:.0f})")
        return True

    def shift_scene(self, dx, dy, target):
        """Move everything that lives in Blender space by (-dx, -dy)."""
        movers = set()
        for info in self.chunks.values():
            movers.add(info['root'])
        movers.add(target)
        for o in self.scene.objects:
            if o.type == 'CAMERA' and o.parent is None:
                movers.add(o)
        for o in movers:
            if o.parent is not None and o.parent in movers:
                continue
            if o.parent is None:
                o.location.x -= dx; o.location.y -= dy
            ad = o.animation_data
            if ad and ad.action:
                for fc in _location_fcurves(ad):
                    d = dx if fc.array_index == 0 else dy
                    for kp in fc.keyframe_points:
                        kp.co.y -= d; kp.handle_left.y -= d; kp.handle_right.y -= d
                    fc.update()
        # 3D viewports follow the player
        try:
            for scr in bpy.data.screens:
                for area in scr.areas:
                    if area.type == 'VIEW_3D':
                        for sp in area.spaces:
                            if sp.type == 'VIEW_3D' and sp.region_3d:
                                sp.region_3d.view_location.x -= dx
                                sp.region_3d.view_location.y -= dy
        except Exception:
            pass

    # ------------------------------------------------------------------ build / unload
    def _root_location(self, cx, cy):
        ox, oy = get_offset(self.scene)
        return (cx * C.CHUNK_SIZE - ox, cy * C.CHUNK_SIZE - oy, 0.0)

    def unload(self, key):
        info = self.chunks.pop(key, None)
        if info is None:
            return
        objs = []
        try:
            _collect_tree(info['root'], objs)
        except ReferenceError:
            return
        remove_objects(objs)

    def build(self, key, lod, place=True, features=True):
        t0 = time.perf_counter()
        cx, cy = key
        if key in self.chunks:
            self.unload(key)
        col = get_collection(self.scene)
        ctx, masks, nrm = sample_chunk(cx, cy, lod)
        root = bpy.data.objects.new(f"Chunk_{cx}_{cy}", None)
        root.empty_display_type = 'PLAIN_AXES'
        root.empty_display_size = 200.0
        root["cx"], root["cy"], root["lod"] = cx, cy, lod
        root.location = self._root_location(cx, cy) if place else (0.0, 0.0, 0.0)
        col.objects.link(root)
        me = build_terrain_mesh(f"Terrain_{cx}_{cy}", ctx, masks, nrm)
        root["skirt_depth"] = float(ctx.extra.get("skirt_depth", 0.0))
        tob = bpy.data.objects.new(f"Terrain_{cx}_{cy}", me)
        col.objects.link(tob)
        tob.parent = root
        ctx.root, ctx.collection = root, col
        ctx.extra['terrain_object'] = tob
        t_mesh = time.perf_counter() - t0
        if features:
            for mod in world.FEATURES:
                fn = getattr(mod, 'chunk_objects', None)
                if fn is None:
                    continue
                try:
                    objs = fn(ctx) or []
                except Exception:
                    log(f"chunk_objects failed in {mod.__name__} for {key}:\n{traceback.format_exc()}")
                    continue
                for o in objs:
                    try:
                        if not o.users_collection:
                            col.objects.link(o)
                        if o.parent is None:
                            o.parent = root
                    except Exception:
                        log(f"bad object from {mod.__name__}: {o!r}")
        self.chunks[key] = {'root': root, 'lod': lod}
        dt = time.perf_counter() - t0
        self.stats.append((cx, cy, lod, dt, t_mesh))
        return root

    # ------------------------------------------------------------------ main update
    def update(self, budget=-1, target=None, allow_rebase=True):
        """budget: max builds this call (-1 = self.budget, None = unlimited)."""
        if self._busy:
            return 0
        self._busy = True
        try:
            return self._update(self.budget if budget == -1 else budget, target, allow_rebase)
        finally:
            self._busy = False

    def _update(self, budget, target, allow_rebase=True):
        target = target or find_target(self.scene)
        if target is None:
            return 0
        if allow_rebase:
            self.maybe_rebase(target)
        wx, wy = self.target_world_xy(target)
        if target.name == PLAYER:
            if target.get("world_x") != wx or target.get("world_y") != wy:
                target["world_x"], target["world_y"] = wx, wy
        self._update_center(wx, wy)
        want = self.desired()
        for key in [k for k in self.chunks if k not in want]:
            self.unload(key)
        todo = [(ring, (k[0] - self.center[0]) ** 2 + (k[1] - self.center[1]) ** 2, k)
                for k, ring in want.items()
                if k not in self.chunks or self.chunks[k]['lod'] != ring]
        todo.sort()
        self.queue = [k for _, _, k in todo]
        n = 0
        t0 = time.perf_counter()
        while self.queue and (budget is None or n < budget):
            if budget is not None and n and time.perf_counter() - t0 > TIME_BUDGET:
                break
            k = self.queue.pop(0)
            self.build(k, want[k])
            n += 1
        return n

    def load_all_now(self, target=None):
        n = self.update(budget=None, target=target)
        return n

    def pending(self):
        return len(self.queue)

    def snap_to_ground(self, target):
        """Keep the Player standing on the terrain (Player['snap_to_ground'] toggles)."""
        if target is None or target.name != PLAYER or not target.get("snap_to_ground", True):
            return
        if target.animation_data and target.animation_data.action:
            for fc in _location_fcurves(target.animation_data):
                if fc.array_index == 2:
                    return                         # z is animated -> leave it alone
        wx, wy = self.target_world_xy(target)
        if self._last_xy == (round(wx, 2), round(wy, 2)):
            return
        self._last_xy = (round(wx, 2), round(wy, 2))
        if target.parent is None:
            z = max(height_at(wx, wy), C.SEA_LEVEL)
            if abs(target.location.z - z) > 0.01:
                target.location.z = z


def _location_fcurves(ad):
    act = ad.action
    fcs = []
    try:
        fcs = [fc for fc in act.fcurves if fc.data_path == 'location']
    except AttributeError:
        pass
    if not fcs:
        # Blender 4.4+ layered actions
        try:
            for layer in act.layers:
                for strip in layer.strips:
                    bag = strip.channelbag(ad.action_slot)
                    if bag:
                        fcs += [fc for fc in bag.fcurves if fc.data_path == 'location']
        except Exception:
            pass
    return fcs


# ============================================================================ live hooks
_manager = None


def manager():
    global _manager
    scene = bpy.context.scene
    if _manager is None or _manager.scene != scene:
        _manager = ChunkManager(scene)
    try:
        _manager.scene.name
    except ReferenceError:
        _manager = ChunkManager(bpy.context.scene)
    return _manager


_last_tick_loc = [None]


def _safe_update(snap=False, allow_rebase=True):
    try:
        m = manager()
        tgt = find_target(m.scene)
        if snap:
            m.snap_to_ground(tgt)
        m.update(allow_rebase=allow_rebase)
    except Exception:
        log("update failed:\n" + traceback.format_exc())


@persistent
def _on_depsgraph(scene, depsgraph=None):
    # Fires during interactive G-drags: stream chunks but never move the Player (a running
    # transform modal would overwrite the shift). Re-base / ground snap happen in the timer.
    if _manager is not None and _manager._busy:
        return
    _safe_update(snap=False, allow_rebase=False)


@persistent
def _on_frame(scene, depsgraph=None):
    _safe_update(snap=True, allow_rebase=True)       # playback: keyframes are shifted too


def _on_timer():
    try:
        tgt = find_target(bpy.context.scene)
        loc = tuple(_loc(tgt))[:2] if tgt is not None else None
    except Exception:
        loc = None
    still = loc is not None and loc == _last_tick_loc[0]   # unchanged for one tick -> not dragging
    _last_tick_loc[0] = loc
    _safe_update(snap=still, allow_rebase=still)
    return TIMER_INTERVAL


@persistent
def _on_load(*_):
    global _manager
    _manager = None
    _register_timer()


def _register_timer():
    old = bpy.app.driver_namespace.get('_terrain_stream_timer')
    if old is not None and old is not _on_timer:
        try:
            if bpy.app.timers.is_registered(old):
                bpy.app.timers.unregister(old)     # stale copy from a re-imported module
        except Exception:
            pass
    if not bpy.app.timers.is_registered(_on_timer):
        bpy.app.timers.register(_on_timer, first_interval=TIMER_INTERVAL, persistent=True)
    bpy.app.driver_namespace['_terrain_stream_timer'] = _on_timer


def _strip(lst, name):
    for f in list(lst):
        if getattr(f, '__name__', '') == name and getattr(f, '__module__', '').endswith('streaming'):
            lst.remove(f)


def register():
    """Idempotent: safe to call again after re-import / file reload."""
    unregister()
    bpy.app.handlers.depsgraph_update_post.append(_on_depsgraph)
    bpy.app.handlers.frame_change_post.append(_on_frame)
    bpy.app.handlers.load_post.append(_on_load)
    _register_timer()
    log("live streaming registered")


def unregister():
    for lst, name in ((bpy.app.handlers.depsgraph_update_post, '_on_depsgraph'),
                      (bpy.app.handlers.frame_change_post, '_on_frame'),
                      (bpy.app.handlers.load_post, '_on_load')):
        _strip(lst, name)
    try:
        if bpy.app.timers.is_registered(_on_timer):
            bpy.app.timers.unregister(_on_timer)
    except Exception:
        pass


def _loc(obj):
    """Blender-space position; uses .location for unparented objects so it is current even
    before the depsgraph re-evaluates matrix_world (headless scripts)."""
    return obj.location if obj.parent is None else obj.matrix_world.translation
