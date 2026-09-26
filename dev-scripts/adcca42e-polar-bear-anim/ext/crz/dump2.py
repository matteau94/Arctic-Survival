def _dump2(g):
    np = g["np"]; me = g["me"]; inv = g["inv"]
    lp = np.zeros(len(me.data.loops), dtype=np.int64); me.data.loops.foreach_get("vertex_index", lp)
    ls = np.zeros(len(me.data.polygons), dtype=np.int64); me.data.polygons.foreach_get("loop_start", ls)
    lt = np.zeros(len(me.data.polygons), dtype=np.int64); me.data.polygons.foreach_get("loop_total", lt)
    np.savez(r"C:/Users/leosp/AppData/Local/Temp/claude/C--Users-leosp-Documents-GitHub-Hockey-202609/adcca42e-ad80-4670-abe5-ecf9d0929f1f/scratchpad/ext/crz/dump2.npz",
             Q=g["Q"], R=g["R"], J=g["JWu"], lp=inv[lp], ls=ls, lt=lt,
             lz=np.array([g["line_z"](y) for y in g["Q"][:,1]]))
HOOKS["shape"].append(_dump2)
