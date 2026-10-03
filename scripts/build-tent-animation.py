"""Standalone editable tent animation; run in a factory-startup Blender process."""
import bpy
import math
from pathlib import Path
from mathutils import Vector

ROOT = Path(__file__).resolve().parents[1]
bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete(use_global=False)
scene = bpy.context.scene
scene.render.fps = 30
scene.frame_start = 1
scene.frame_end = 240
bpy.context.preferences.filepaths.save_version = 0

def material(name, color, metallic=0):
    m = bpy.data.materials.new(name)
    m.diffuse_color = (*color, 1)
    m.use_nodes = True
    shader = next(n for n in m.node_tree.nodes if n.type == 'BSDF_PRINCIPLED')
    shader.inputs['Base Color'].default_value = (*color, 1)
    shader.inputs['Roughness'].default_value = .75 if not metallic else .3
    shader.inputs['Metallic'].default_value = metallic
    return m

canvas = material('Expedition orange canvas', (.58, .22, .055))
trim = material('Charcoal seams', (.035, .045, .05))
metal = material('Zipper hardware', (.55, .6, .62), .8)
snow = material('Snow display ground', (.72, .8, .86))

def mesh(name, vertices, faces, mat):
    data = bpy.data.meshes.new(name)
    data.from_pydata(vertices, [], faces)
    data.update()
    obj = bpy.data.objects.new(name, data)
    scene.collection.objects.link(obj)
    obj.data.materials.append(mat)
    return obj

def cube(name, location, scale, mat):
    bpy.ops.mesh.primitive_cube_add(size=1, location=location)
    obj = bpy.context.object
    obj.name = name
    obj.scale = scale
    obj.data.materials.append(mat)
    return obj

def rod(name, a, b, radius, mat):
    a, b = Vector(a), Vector(b)
    bpy.ops.mesh.primitive_cylinder_add(vertices=12, radius=radius, depth=(b-a).length, location=(a+b)/2)
    obj = bpy.context.object
    obj.name = name
    obj.rotation_euler = (b-a).to_track_quat('Z', 'Y').to_euler()
    obj.data.materials.append(mat)
    return obj

# Blender Z is up; the entrance faces negative Y.
w, d, h = 1.68, 1.89, 3.0
body = mesh('Tent_Canvas', [(-w,-d,0),(w,-d,0),(0,-d,h),(-w,d,0),(w,d,0),(0,d,h)], [(0,3,5,2),(2,5,4,1),(3,4,5)], canvas)
solid = body.modifiers.new('Canvas thickness', 'SOLIDIFY'); solid.thickness = .008
cube('Groundsheet', (0,0,.012), (w*2,d*2,.024), trim)
for y in [-d,d]:
    for sign in [-1,1]:
        rod('Tent pole', (sign*w,y,0),(0,y,h),.022,metal)
rod('Ridge pole',(0,-d,h),(0,d,h),.022,metal)

# Reference: Hilleberg, "How do I roll my outer tent door?"
# Sampled shape keys preserve the free fabric as a curled strip instead of
# scaling the entire door into a thin triangle. Outer sewn edges stay fixed.
def ease(t):
    t=max(0,min(1,t)); return t*t*(3-2*t)

def motion(frame):
    unzip=ease((frame-10)/38) if frame<150 else 1-ease((frame-166)/38)
    roll=ease((frame-50)/40) if frame<125 else 1-ease((frame-125)/40)
    return unzip,roll

def cloth(sign,u,z,frame):
    unzip,roll=motion(frame)
    edge=w*(1-z/h)
    released=ease((unzip*h-z)/.18)
    # Small relaxed folds once the zipper has passed this height.
    gap=.055*(1-u)*(1-z/h)*released
    length=edge*u
    gathered=edge*.90*roll
    x=length; y=-d-.025
    if length<gathered:
        radius=.035+.012*roll
        angle=(gathered-length)/radius
        # A shallow spiral gives successive layers thickness.
        radius+=.0015*angle
        x=gathered-radius*math.sin(angle)
        y-=radius*(1-math.cos(angle))
    else:
        y-=.016*math.sin(u*math.pi*5+z*3)*math.sin(math.pi*u)*released*(1-roll)
    return (sign*(x+gap*(1-roll)),y,z-.025*math.sin(math.pi*u)*released*(1-roll))

samples=sorted(set([1,10,48,50,90,125,165,166,204,240]+list(range(10,205,4))))
for sign,name in [(-1,'Left'),(1,'Right')]:
    rows,cols=32,48
    params=[(col/cols,h*row/rows) for row in range(rows+1) for col in range(cols+1)]
    verts=[cloth(sign,u,z,1) for u,z in params]
    faces=[]
    for row in range(rows):
        for col in range(cols):
            a=row*(cols+1)+col
            faces.append((a,a+1,a+cols+2,a+cols+1))
    obj=mesh('Door_Flap_'+name,verts,faces,canvas)
    obj.shape_key_add(name='Closed')
    for j,frame in enumerate(samples):
        key=obj.shape_key_add(name=f'Cloth_{frame:03d}')
        for point,(u,z) in zip(key.data,params): point.co=cloth(sign,u,z,frame)
        before=samples[j-1] if j else frame-1
        after=samples[j+1] if j+1<len(samples) else frame+1
        for f,v in [(before,0),(frame,1),(after,0)]:
            key.value=v;key.keyframe_insert('value',frame=f)
    for poly in obj.data.polygons:poly.use_smooth=True
    thick=obj.modifiers.new('Thin ripstop fabric','SOLIDIFY');thick.thickness=.0015
    # The zipper tape follows the actual free cloth edge at every height.
    tapeparams=[(u,h*row/64) for row in range(65) for u in [0,.014]]
    tapeverts=[cloth(sign,u,z,1) for u,z in tapeparams]
    tape=mesh('Sewn zipper tape '+name,tapeverts,[(i,i+1,i+3,i+2) for i in range(0,128,2)],trim)
    tape.shape_key_add(name='Closed')
    for j,frame in enumerate(samples):
        key=tape.shape_key_add(name=f'Tape_{frame:03d}')
        for point,(u,z) in zip(key.data,tapeparams):
            x,y,zz=cloth(sign,u,z,frame);point.co=(x,y-.003,zz)
        for f,v in [(samples[j-1] if j else frame-1,0),(frame,1),(samples[j+1] if j+1<len(samples) else frame+1,0)]:
            key.value=v;key.keyframe_insert('value',frame=f)
    # Small retention loop/toggle at the outside seam.
    z=1.15;edge=w*(1-z/h)
    rod('Door tie toggle '+name,(sign*(edge-.1),-d-.13,z),(sign*(edge+.02),-d-.13,z),.012,trim)

pull=cube('Zipper_Slider',(0,-d-.07,.08),(.04,.026,.065),metal)
for frame,z in [(1,.08),(10,.08),(48,2.96),(166,2.96),(204,.08),(240,.08)]:
    pull.location.z=z;pull.keyframe_insert('location',frame=frame)
# Actual-size dangling pull, not an oversized scaled ring.
bpy.ops.mesh.primitive_torus_add(major_radius=.023,minor_radius=.0035,major_segments=16,minor_segments=6,location=(0,-d-.09,.035))
ring=bpy.context.object;ring.name='Zipper pull loop';ring.rotation_euler.x=math.pi/2;ring.data.materials.append(metal)
for frame,z in [(1,.035),(10,.035),(48,2.915),(166,2.915),(204,.035),(240,.035)]:
    ring.location.z=z;ring.keyframe_insert('location',frame=frame)

# Tension details and subtle fabric grain make the closed tent read as cloth.
shader=next(n for n in canvas.node_tree.nodes if n.type=='BSDF_PRINCIPLED')
noise=canvas.node_tree.nodes.new('ShaderNodeTexNoise');noise.inputs['Scale'].default_value=220
bump=canvas.node_tree.nodes.new('ShaderNodeBump');bump.inputs['Strength'].default_value=.12;bump.inputs['Distance'].default_value=.008
canvas.node_tree.links.new(noise.outputs['Fac'],bump.inputs['Height']);canvas.node_tree.links.new(bump.outputs['Normal'],shader.inputs['Normal'])
for sign in [-1,1]:
    for y in [-d,d]:
        rod('Guy line',(sign*.8,y,1.55),(sign*2.4,y*1.35,.025),.005,trim)
        rod('Snow stake',(sign*2.4,y*1.35,0),(sign*2.45,y*1.35,.2),.012,metal)

cube('Display snow',(0,0,-.10),(12,12,.16),snow)
bpy.ops.object.camera_add(location=(3.8,-8.5,3.5))
camera=bpy.context.object;camera.name='Entrance preview camera'
camera.rotation_euler=(Vector((0,-.3,1.4))-camera.location).to_track_quat('-Z','Y').to_euler()
camera.data.lens=48;scene.camera=camera
bpy.ops.object.light_add(type='AREA',location=(2,-4,7))
light=bpy.context.object;light.data.energy=1500;light.data.shape='DISK';light.data.size=5
light.rotation_euler=(Vector((0,0,1))-light.location).to_track_quat('-Z','Y').to_euler()
scene.world.color=(.3,.3,.3)
for name,frame in [('CLOSED',1),('Unzip',10),('Roll fabric outward',50),('OPEN',90),('Unroll fabric',125),('Zip shut',166),('CLOSED again',204)]:
    scene.timeline_markers.new(name,frame=frame)
scene['Animation instructions']='Space plays: frames 1–75 opening, 75–120 hold, 120–188 closing. Shape keys and zipper transforms are editable.'
scene.frame_set(1)
for screen in bpy.data.screens:
    for area in screen.areas:
        if area.type=='VIEW_3D':
            area.spaces.active.region_3d.view_perspective='CAMERA'
            area.spaces.active.shading.color_type='MATERIAL'
out=ROOT/'Scenery'/'Tent_Opening_Closing.blend'
bpy.ops.wm.save_as_mainfile(filepath=str(out),compress=True)
print('SAVED',out,'BYTES',out.stat().st_size)
