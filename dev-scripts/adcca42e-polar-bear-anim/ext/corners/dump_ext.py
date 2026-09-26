def _dump(g):
    import numpy as _np
    _np.savez(r"C:/Users/leosp/AppData/Local/Temp/claude/C--Users-leosp-Documents-GitHub-Hockey-202609/adcca42e-ad80-4670-abe5-ecf9d0929f1f/scratchpad/ext/corners/dump.npz", Q=g["Q"], R=g["R"], J=g["JWu"])
    import pickle
    pickle.dump([list(map(int,a)) for a in g["nbr"]], open(r"C:/Users/leosp/AppData/Local/Temp/claude/C--Users-leosp-Documents-GitHub-Hockey-202609/adcca42e-ad80-4670-abe5-ecf9d0929f1f/scratchpad/ext/corners/nbr.pkl","wb"))
HOOKS["shape"].append(_dump)
