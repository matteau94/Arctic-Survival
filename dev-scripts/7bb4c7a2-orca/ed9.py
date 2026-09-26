p = r"C:\Users\leosp\Documents\Blender\Artic-Survival\orca_build.py"
t = open(p, encoding="utf8").read()
def rep(a, b):
    global t
    assert t.count(a) == 1, ("NOT FOUND/UNIQUE", a[:90])
    t = t.replace(a, b)
i = t.index('"""Model, texture'); j = t.index('"""\nimport bpy')
t = t[:i] + '''"""Model, texture and rig an orca (killer whale) in the style of the other Artic-Survival animals.

    blender -b --python orca_build.py        (writes Orca_Rigged.blend + textures/Orca_*.png)

Real-world metres, ~6.1 m long (adult), body axis on z = 0, facing -Y (so +X is its left side).
~40k verts, one object 'Orca', one material 'Orca_Skin', armature 'OrcaRig'.

1. Mesh (one object, one material, like the fox / bear / fish / penguin): subdivided lofts
     body      snout -> melon -> barrel -> keeled, laterally compressed tail stock as one ring
               loft (rings packed densely at the snout, eye and blowhole); the ring vertex on the
               lip line is split from the snout back to the mouth corner so the lower jaw opens.
               A numpy 'sculpt' pass then displaces it along its normals: melon + rostrum
               crease, mouth-line groove curving up at the gape, lower-lip bead, chin, eye
               socket / brow / cheek, crescent blowhole (slit, raised rear lip, nasal plug),
               throat folds, epaxial / hypaxial muscle masses, dorsal and ventral tail keels,
               genital / umbilical slits
     mouth     a soft interior 'plug' inside the head (seen through the open jaw) + conical teeth
               sitting between plug and skin (hidden when the jaw is closed)
     eyes      eyeballs with a painted iris / pupil (glassy roughness) and almond eyelid skirts
               draped onto the sculpted skin
     fins      tall back-leaning dorsal fin (flared root, thin wavy trailing edge), broad paddle
               pectorals with faint digit ridges, flukes with a median notch, thin trailing edge
               and slightly drooping tips
   Every part carries a 'part' point attribute used when texturing and weighting.
2. Textures (2048^2, PBR like the other assets): object-space position / normal / part /
   noise / AO are baked from the mesh and the pattern is painted from them in numpy: charcoal
   back (darker along the spine, lighter flank mottling), white lower jaw / throat / belly /
   flank lobes, oval eye patch, feathered striated grey saddle, rake-mark scars, diatom tint,
   white fluke undersides.  A height map (wrinkles at eye / blowhole / gape / armpit, throat
   folds, scars, slits) plus procedural micro-pores is baked through a bump node into the
   tangent-space normal map.
     textures/Orca_BaseColor.png, Orca_ORM.png (R=AO, G=roughness, B=metal), Orca_Normal.png
3. Rig 'OrcaRig':
     root (no deform)
       body > chest > head > jaw                    (jaw: local -X rotation opens the mouth)
       head > blowhole                              (local +X rotation lifts the rear lip = open)
       body > tail_01 > tail_02 > tail_03 > tail_04 > tail_05 > fluke > fluke_tip.L / fluke_tip.R
                                                    (fluke_tip: local X rotation curls the blade tip)
       body > dorsal_01 > dorsal_02
       chest > pectoral_01.L/R > pectoral_02.L/R
''' + t[j:]
# thin dark lip margin: move the white boundary just below the lip-split seam
rep("""THR = [(0.00, PHI_M), (0.095, PHI_M),""", """THR = [(0.00, PHI_M + 0.05), (0.095, PHI_M + 0.05),""")
# no pinch at the snout pole
rep("""    d -= 0.009 * g(sv, 0.016, 0.008) * g(ang, 0.0, 1.1) * (sv > 0.004)""",
    """    d -= 0.008 * g(sv, 0.018, 0.008) * g(ang, 0.0, 1.1) * smoothstep(0.006, 0.013, sv)""")
open(p, "w", encoding="utf8").write(t)
print("edited ed9")
