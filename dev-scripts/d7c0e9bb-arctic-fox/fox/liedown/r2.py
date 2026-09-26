P = {}
exec(open(r"C:/Users/leosp/AppData/Local/Temp/claude/C--Users-leosp-Documents-Blender-Artic-Survival/d7c0e9bb-db31-445d-9968-dc877601a0b7/scratchpad/fox/liedown/ld.py").read())
# rest tail clearance: mesh near tail bones
ob = bpy.data.objects['ArcticFox']
rep={}; M = solve({}, rep)
import collections
vg = {g.index: g.name for g in ob.vertex_groups}
lo = collections.defaultdict(lambda: 9)
for v in ob.data.vertices:
    if not v.groups: continue
    g = max(v.groups, key=lambda g: g.weight); n = vg[g.group]
    lo[n] = min(lo[n], v.co.z)
for k in range(1,7):
    n='tail%d'%k; print(n, 'bone z %.3f'%BL[n].head_local.z, 'lowest mesh %.3f'%lo[n], 'clear %.3f'%(BL[n].head_local.z-lo[n]))
for n in ['hips','spine1','spine2','chest','forearm.L','upperarm.L','thigh.L','shin.L','hock.L','neck1','head']:
    print(n, 'bone z %.3f'%BL[n].head_local.z, 'lowest mesh %.3f'%lo.get(n,9))
