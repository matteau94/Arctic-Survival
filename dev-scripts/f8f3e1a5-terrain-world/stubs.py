"""Contract-conforming stand-ins for feature modules (for streaming tests)."""
import sys, types, numpy as np, bpy
def install():
    import terrain.noise as N
    from terrain.config import CONTINENT_RADIUS, PLATEAU_HEIGHT
    oc = types.ModuleType("terrain.ocean"); mt = types.ModuleType("terrain.mountains")
    va = types.ModuleType("terrain.valleys"); ri = types.ModuleType("terrain.rivers")
    def continent(X, Y):
        r = np.sqrt(X*X+Y*Y); land = np.clip((CONTINENT_RADIUS-r)/50000.0, 0, 1)
        return np.where(land > 0, PLATEAU_HEIGHT*np.sqrt(np.clip((CONTINENT_RADIUS-r)/CONTINENT_RADIUS,0,1)), -500.0), land
    oc.continent = continent; oc.coast = lambda X,Y,h,l: h
    def oc_objs(ctx):   # a per-chunk water plane with its own per-chunk material (tests cleanup)
        me = bpy.data.meshes.new(f"W_{ctx.cx}_{ctx.cy}")
        s = ctx.size; me.from_pydata([(0,0,0),(s,0,0),(s,s,0),(0,s,0)], [], [(0,1,2,3)])
        mat = bpy.data.materials.new(f"Wmat_{ctx.cx}_{ctx.cy}"); me.materials.append(mat)
        o = bpy.data.objects.new(f"Water_{ctx.cx}_{ctx.cy}", me); ctx.collection.objects.link(o); o.parent = ctx.root
        return [o]
    oc.chunk_objects = oc_objs
    mt.height = lambda X,Y,land: land * 1800.0 * N.ridged(X, Y, 5, 1/30000.0, 6)
    def mt_objs(ctx): raise RuntimeError("deliberately broken module")
    mt.chunk_objects = mt_objs
    va.carve = lambda X,Y,h,l: h; va.chunk_objects = lambda ctx: []
    ri.carve = lambda X,Y,h,l: h; ri.chunk_objects = lambda ctx: []
    import terrain
    for name, m in (("ocean", oc), ("mountains", mt), ("valleys", va), ("rivers", ri)):
        sys.modules["terrain."+name] = m; setattr(terrain, name, m)
