import bpy, numpy as np
bpy.ops.wm.read_factory_settings(use_empty=True)
sc=bpy.context.scene
sc.sequence_editor_create()
st=sc.sequence_editor.strips.new_movie("m", r"C:\Users\leosp\Documents\Polar Bear Running.mp4", 1, 1)
print("STRIP", st.frame_final_duration, st.elements[0].orig_width if st.elements else None)
sc.render.resolution_x, sc.render.resolution_y = 800, 500
sc.render.image_settings.file_format='PNG'
for f in (1, 60):
    sc.frame_set(f); sc.render.filepath=rf"{r'C:/Users/leosp/AppData/Local/Temp/claude/C--Users-leosp-Documents-GitHub-Hockey-202609/adcca42e-ad80-4670-abe5-ecf9d0929f1f/scratchpad'}/dec{f}.png"
    bpy.ops.render.render(write_still=True)
