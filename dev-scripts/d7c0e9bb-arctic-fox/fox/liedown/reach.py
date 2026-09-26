exec(open(r"C:/Users/leosp/AppData/Local/Temp/claude/C--Users-leosp-Documents-Blender-Artic-Survival/d7c0e9bb-db31-445d-9968-dc877601a0b7/scratchpad/fox/liedown/pp.py").read())
P.update(sit_cp=-0.45)
exec(open(r"C:/Users/leosp/AppData/Local/Temp/claude/C--Users-leosp-Documents-Blender-Artic-Survival/d7c0e9bb-db31-445d-9968-dc877601a0b7/scratchpad/fox/liedown/ld.py").read())
out=[]
for f in range(N+1):
    r={}; solve(pose(f/N,f), r); out.append("%d:%.3f%s"%(f, r['reach'], ''.join(sorted(r.get('short',[])))))
print(' '.join(out))
