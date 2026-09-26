"""Shared materials + polar sky.

* get_or_create(name, builder) -> bpy.types.Material
    Shared-material pattern for every module: returns bpy.data.materials[name] if it exists,
    else creates it, calls builder(mat) to fill the node tree, sets use_fake_user=True (so
    streaming's cleanup never deletes shared materials when their last chunk unloads).
* terrain_material()  - the ONE material used by every terrain chunk mesh. Reads the packed
    point colour attribute "surf" (R=snow, G=rock, B=ice, A=water) written by streaming.py and
    texture-space = Geometry Position + "TerrainOffset" (world offset mod OFFSET_PERIOD), so the
    procedural noise is continuous across chunks.
* add_distance_fog(mat, shader_socket) - wrap a material's final shader in world-colour
    distance haze (no volumes). Feature agents can call it on their own materials.
* setup_world(scene) - polar sky gradient world, low Sun at ~8 deg, mist settings.
"""
import math
import bpy

SURF_ATTR = "surf"
TERRAIN_MAT = "Terrain_Mat"
OFFSET_PERIOD = 8 * 25749.504      # shader offset wraps every 8 chunks (keeps float32 coords small)
HAZE_COLOR = (0.74, 0.80, 0.90)
HAZE_DIST = 60000.0                # metres for ~63% haze (x max)
HAZE_MAX = 0.7
SUN_ELEVATION_DEG = 8.0
SUN_AZIMUTH_DEG = 200.0            # degrees clockwise from +Y (north)


def get_or_create(name, builder):
    mat = bpy.data.materials.get(name)
    if mat is None:
        mat = bpy.data.materials.new(name)
        builder(mat)
        mat.use_fake_user = True
    return mat


# --------------------------------------------------------------------------- helpers
def _n(nt, typ, loc, **props):
    node = nt.nodes.new(typ)
    node.location = loc
    for k, v in props.items():
        setattr(node, k, v)
    return node


def _mix(nt, loc, data_type='RGBA', blend='MIX'):
    m = _n(nt, 'ShaderNodeMix', loc)
    m.data_type = data_type
    if data_type == 'RGBA':
        m.blend_type = blend
    return m


def _mix_io(m):
    """(factor, A, B, result) sockets for the active data type of a ShaderNodeMix."""
    t = m.data_type
    idx = {'FLOAT': 0, 'VECTOR': 1, 'RGBA': 2}[t]
    ins = [s for s in m.inputs if s.name in ('A', 'B')]
    a = [s for s in m.inputs if s.name == 'A'][idx]
    b = [s for s in m.inputs if s.name == 'B'][idx]
    out = m.outputs[idx]
    fac = m.inputs[0]
    return fac, a, b, out


def add_distance_fog(mat, shader_socket, haze_color=HAZE_COLOR, dist=HAZE_DIST, max_fog=HAZE_MAX):
    """Insert a distance-haze mix between shader_socket and the Material Output."""
    nt = mat.node_tree
    out = next(n for n in nt.nodes if n.type == 'OUTPUT_MATERIAL')
    cam = _n(nt, 'ShaderNodeCameraData', (out.location.x - 900, out.location.y - 300))
    # fog = max_fog * (1 - exp(-d / dist))
    div = _n(nt, 'ShaderNodeMath', (out.location.x - 700, out.location.y - 300), operation='DIVIDE')
    nt.links.new(cam.outputs['View Distance'], div.inputs[0]); div.inputs[1].default_value = -dist
    ex = _n(nt, 'ShaderNodeMath', (out.location.x - 550, out.location.y - 300), operation='EXPONENT')
    nt.links.new(div.outputs[0], ex.inputs[0])
    one = _n(nt, 'ShaderNodeMath', (out.location.x - 400, out.location.y - 300), operation='SUBTRACT')
    one.inputs[0].default_value = 1.0; nt.links.new(ex.outputs[0], one.inputs[1])
    mul = _n(nt, 'ShaderNodeMath', (out.location.x - 250, out.location.y - 300), operation='MULTIPLY')
    nt.links.new(one.outputs[0], mul.inputs[0]); mul.inputs[1].default_value = max_fog
    emit = _n(nt, 'ShaderNodeEmission', (out.location.x - 250, out.location.y - 450))
    emit.inputs['Color'].default_value = (*haze_color, 1.0)
    emit.inputs['Strength'].default_value = 1.0
    mix = _n(nt, 'ShaderNodeMixShader', (out.location.x - 120, out.location.y))
    nt.links.new(mul.outputs[0], mix.inputs[0])
    nt.links.new(shader_socket, mix.inputs[1])
    nt.links.new(emit.outputs[0], mix.inputs[2])
    nt.links.new(mix.outputs[0], out.inputs['Surface'])
    return mix


# --------------------------------------------------------------------------- terrain
def _build_terrain(mat):
    nt = mat.node_tree
    nt.nodes.clear()
    L = nt.links.new
    out = _n(nt, 'ShaderNodeOutputMaterial', (1600, 0))
    bsdf = _n(nt, 'ShaderNodeBsdfPrincipled', (1200, 0))

    # texture space: world position (Blender) + offset uniform (floating-origin compensation)
    geo = _n(nt, 'ShaderNodeNewGeometry', (-1600, 200))
    ox = _n(nt, 'ShaderNodeValue', (-1600, -100)); ox.name = ox.label = 'TerrainOffsetX'
    oy = _n(nt, 'ShaderNodeValue', (-1600, -200)); oy.name = oy.label = 'TerrainOffsetY'
    cxyz = _n(nt, 'ShaderNodeCombineXYZ', (-1400, -100))
    L(ox.outputs[0], cxyz.inputs[0]); L(oy.outputs[0], cxyz.inputs[1])
    pos = _n(nt, 'ShaderNodeVectorMath', (-1200, 100), operation='ADD')
    L(geo.outputs['Position'], pos.inputs[0]); L(cxyz.outputs[0], pos.inputs[1])
    P = pos.outputs[0]

    attr = _n(nt, 'ShaderNodeAttribute', (-1600, 600), attribute_name=SURF_ATTR)
    attr.attribute_type = 'GEOMETRY'
    sep = _n(nt, 'ShaderNodeSeparateColor', (-1400, 600))
    L(attr.outputs['Color'], sep.inputs[0])
    snow_rock = sep.outputs[1]            # G = rock
    ice = sep.outputs[2]                  # B = ice
    water = attr.outputs['Alpha']         # A = water

    def noise(loc, scale, detail=4.0, rough=0.55):
        t = _n(nt, 'ShaderNodeTexNoise', loc)
        t.noise_dimensions = '3D'
        t.inputs['Scale'].default_value = scale
        t.inputs['Detail'].default_value = detail
        t.inputs['Roughness'].default_value = rough
        L(P, t.inputs['Vector'])
        return t

    # --- snow: bright, slight blue variation, roughness variation, sparkle
    n_snow = noise((-900, 900), 1 / 60.0, 6)
    ramp_s = _n(nt, 'ShaderNodeValToRGB', (-650, 900))
    ramp_s.color_ramp.elements[0].color = (0.80, 0.87, 0.97, 1)
    ramp_s.color_ramp.elements[1].color = (0.96, 0.975, 1.0, 1)
    ramp_s.color_ramp.elements[0].position = 0.35; ramp_s.color_ramp.elements[1].position = 0.7
    L(n_snow.outputs['Fac'], ramp_s.inputs[0])
    sparkle = _n(nt, 'ShaderNodeTexVoronoi', (-900, 600))
    sparkle.inputs['Scale'].default_value = 6.0
    L(P, sparkle.inputs['Vector'])
    sp = _n(nt, 'ShaderNodeMapRange', (-650, 600))
    sp.inputs['From Min'].default_value = 0.0; sp.inputs['From Max'].default_value = 0.12
    sp.inputs['To Min'].default_value = 0.12; sp.inputs['To Max'].default_value = 0.0
    L(sparkle.outputs['Distance'], sp.inputs['Value'])
    n_rgh = noise((-900, 350), 1 / 25.0, 3)
    snow_rgh = _n(nt, 'ShaderNodeMapRange', (-650, 350))
    snow_rgh.inputs['To Min'].default_value = 0.42; snow_rgh.inputs['To Max'].default_value = 0.78
    L(n_rgh.outputs['Fac'], snow_rgh.inputs['Value'])
    snow_rgh2 = _n(nt, 'ShaderNodeMath', (-450, 400), operation='SUBTRACT')
    L(snow_rgh.outputs[0], snow_rgh2.inputs[0]); L(sp.outputs[0], snow_rgh2.inputs[1])

    # --- rock: sparse charcoal outcrops amid the snow
    n_rock = noise((-900, 100), 1 / 18.0, 8, 0.65)
    ramp_r = _n(nt, 'ShaderNodeValToRGB', (-650, 100))
    ramp_r.color_ramp.elements[0].color = (0.018, 0.022, 0.027, 1)
    ramp_r.color_ramp.elements[1].color = (0.105, 0.12, 0.135, 1)
    L(n_rock.outputs['Fac'], ramp_r.inputs[0])

    # Rock masks are authored by the mountain, valley and coast fields. Limit their
    # exposed area to a sparse 5–7.5% of eligible snow and break edges into outcrops.
    sepn = _n(nt, 'ShaderNodeSeparateXYZ', (-1200, -400))
    L(geo.outputs['Normal'], sepn.inputs[0])
    slope_f = _n(nt, 'ShaderNodeMapRange', (-1000, -400))
    slope_f.inputs['From Min'].default_value = 0.80; slope_f.inputs['From Max'].default_value = 0.62
    L(sepn.outputs['Z'], slope_f.inputs['Value'])
    rmax = _n(nt, 'ShaderNodeMath', (-800, -300), operation='MAXIMUM')
    L(snow_rock, rmax.inputs[0]); L(slope_f.outputs[0], rmax.inputs[1])
    n_break = noise((-1000, -650), 1 / 40.0, 4)
    brk = _n(nt, 'ShaderNodeMath', (-800, -550), operation='SUBTRACT')
    L(n_break.outputs['Fac'], brk.inputs[0]); brk.inputs[1].default_value = 0.5
    radd = _n(nt, 'ShaderNodeMath', (-600, -400), operation='ADD')
    L(rmax.outputs[0], radd.inputs[0]); L(brk.outputs[0], radd.inputs[1])
    # A deterministic 3-D noise threshold selects small clustered exposures. Feature
    # masks localize candidates to ridges, valley walls and rocky coasts; steepness alone
    # cannot expose broad plains. The high threshold keeps exposures to about 5–7.5% of
    # eligible snow (the exact fraction depends on Blender's noise distribution).
    exposure = _n(nt, 'ShaderNodeMapRange', (-420, -400))
    exposure.clamp = True
    exposure.inputs['From Min'].default_value = 0.925
    exposure.inputs['From Max'].default_value = 0.99
    exposure.inputs['To Min'].default_value = 0.0
    exposure.inputs['To Max'].default_value = 1.0
    L(n_break.outputs['Fac'], exposure.inputs['Value'])
    sparse = _n(nt, 'ShaderNodeMath', (-200, -400), operation='MULTIPLY')
    L(rmax.outputs[0], sparse.inputs[0]); L(exposure.outputs[0], sparse.inputs[1])
    rfac = _n(nt, 'ShaderNodeMapRange', (0, -400))
    rfac.clamp = True
    rfac.inputs['From Min'].default_value = 0.0; rfac.inputs['From Max'].default_value = 0.8
    L(sparse.outputs[0], rfac.inputs['Value'])

    # --- ice: blue glacial
    n_ice = noise((-900, -900), 1 / 30.0, 5)
    ramp_i = _n(nt, 'ShaderNodeValToRGB', (-650, -900))
    ramp_i.color_ramp.elements[0].color = (0.20, 0.45, 0.66, 1)
    ramp_i.color_ramp.elements[1].color = (0.55, 0.76, 0.88, 1)
    L(n_ice.outputs['Fac'], ramp_i.inputs[0])
    water_col = (0.035, 0.06, 0.08, 1)

    # --- colour chain: snow -> rock -> ice -> water
    m1 = _mix(nt, (0, 700)); f, a, b, o1 = _mix_io(m1)
    L(rfac.outputs[0], f); L(ramp_s.outputs[0], a); L(ramp_r.outputs[0], b)
    m2 = _mix(nt, (200, 700)); f, a, b, o2 = _mix_io(m2)
    L(ice, f); L(o1, a); L(ramp_i.outputs[0], b)
    m3 = _mix(nt, (400, 700)); f, a, b, o3 = _mix_io(m3)
    L(water, f); L(o2, a); b.default_value = water_col
    L(o3, bsdf.inputs['Base Color'])

    # --- roughness chain
    r1 = _mix(nt, (0, 300), 'FLOAT'); f, a, b, ro1 = _mix_io(r1)
    L(rfac.outputs[0], f); L(snow_rgh2.outputs[0], a); b.default_value = 0.88
    r2 = _mix(nt, (200, 300), 'FLOAT'); f, a, b, ro2 = _mix_io(r2)
    L(ice, f); L(ro1, a); b.default_value = 0.12
    r3 = _mix(nt, (400, 300), 'FLOAT'); f, a, b, ro3 = _mix_io(r3)
    L(water, f); L(ro2, a); b.default_value = 0.6
    L(ro3, bsdf.inputs['Roughness'])

    # --- bump from rock noise, stronger on rock
    bump = _n(nt, 'ShaderNodeBump', (900, -300))
    bump.inputs['Distance'].default_value = 0.4
    L(rfac.outputs[0], bump.inputs['Strength'])
    L(n_rock.outputs['Fac'], bump.inputs['Height'])
    L(bump.outputs['Normal'], bsdf.inputs['Normal'])
    try:
        bsdf.inputs['Subsurface Weight'].default_value = 0.0
        bsdf.inputs['Specular IOR Level'].default_value = 0.5
    except KeyError:
        pass

    L(bsdf.outputs[0], out.inputs['Surface'])
    add_distance_fog(mat, bsdf.outputs[0])


def terrain_material():
    return get_or_create(TERRAIN_MAT, _build_terrain)


def set_offset(offset_x, offset_y):
    """Called by streaming on re-base: keep the shader's texture space continuous."""
    mat = bpy.data.materials.get(TERRAIN_MAT)
    if mat is None or mat.node_tree is None:
        return
    nodes = mat.node_tree.nodes
    if 'TerrainOffsetX' in nodes:
        nodes['TerrainOffsetX'].outputs[0].default_value = math.fmod(offset_x, OFFSET_PERIOD)
        nodes['TerrainOffsetY'].outputs[0].default_value = math.fmod(offset_y, OFFSET_PERIOD)


# --------------------------------------------------------------------------- world / sky
def setup_world(scene):
    w = bpy.data.worlds.get('PolarSky') or bpy.data.worlds.new('PolarSky')
    scene.world = w
    if not w.node_tree:
        try:
            w.use_nodes = True
        except Exception:
            pass
    nt = w.node_tree
    nt.nodes.clear()
    L = nt.links.new
    out = _n(nt, 'ShaderNodeOutputWorld', (600, 0))
    bg = _n(nt, 'ShaderNodeBackground', (400, 0))
    tc = _n(nt, 'ShaderNodeTexCoord', (-600, 0))
    sep = _n(nt, 'ShaderNodeSeparateXYZ', (-400, 0))
    L(tc.outputs['Generated'], sep.inputs[0])          # world: Generated = view direction
    ramp = _n(nt, 'ShaderNodeValToRGB', (-150, 0))
    cr = ramp.color_ramp
    cr.elements[0].position = 0.0; cr.elements[0].color = (0.60, 0.66, 0.74, 1)   # below horizon
    cr.elements[1].position = 1.0; cr.elements[1].color = (0.16, 0.30, 0.58, 1)   # zenith
    e = cr.elements.new(0.5); e.color = (*HAZE_COLOR, 1)                           # horizon haze
    e = cr.elements.new(0.53); e.color = (0.93, 0.80, 0.72, 1)                     # low-sun glow band
    e = cr.elements.new(0.62); e.color = (0.52, 0.66, 0.84, 1)
    mr = _n(nt, 'ShaderNodeMapRange', (-250, 0))
    mr.inputs['From Min'].default_value = -1.0; mr.inputs['From Max'].default_value = 1.0
    L(sep.outputs['Z'], mr.inputs['Value']); L(mr.outputs[0], ramp.inputs[0])
    L(ramp.outputs[0], bg.inputs['Color'])
    bg.inputs['Strength'].default_value = 0.6
    L(bg.outputs[0], out.inputs['Surface'])
    w.mist_settings.start = 500.0
    w.mist_settings.depth = 90000.0
    w.mist_settings.falloff = 'QUADRATIC'
    for vl in scene.view_layers:
        vl.use_pass_mist = True

    sun = bpy.data.objects.get('Sun')
    if sun is None:
        sd = bpy.data.lights.new('Sun', 'SUN')
        sun = bpy.data.objects.new('Sun', sd)
        scene.collection.objects.link(sun)
    sun.data.energy = 4.5
    sun.data.color = (1.0, 0.86, 0.72)
    sun.data.angle = math.radians(0.53)
    # Sun light points along its local -Z. Elevation e above horizon, azimuth a (cw from north).
    el = math.radians(SUN_ELEVATION_DEG); az = math.radians(SUN_AZIMUTH_DEG)
    sun.rotation_mode = 'XYZ'
    sun.rotation_euler = (math.pi / 2 - el, 0.0, math.pi - az)
    return w, sun
