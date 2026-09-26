import bpy, math
from mathutils import Quaternion
bpy.ops.wm.open_mainfile(filepath=r"C:\Users\leosp\Documents\Blender\Artic-Survival\Fish_Rigged.blend")
arm=bpy.data.objects["FishRig"]; pb=arm.pose.bones
def rot(n, axis, deg):
    p=pb[n]; p.rotation_mode='QUATERNION'
    r=p.bone.matrix_local.to_quaternion()
    p.rotation_quaternion = r.inverted() @ Quaternion(axis, math.radians(deg)) @ r
for n,d in [("spine_02",8),("spine_03",10),("spine_04",12),("spine_05",14),("caudal",14),("caudal_tip",10),("spine_01",-6)]:
    rot(n,(0,0,1),d)
rot("pectoral.L",(0,0,1),35); rot("operculum.L",(0,0,1),-12); rot("jaw",(1,0,0),15); rot("dorsal",(0,0,1),20)
import os; bpy.ops.wm.save_as_mainfile(filepath=os.path.join(os.path.dirname(os.path.abspath(__file__)), "posed.blend"))
