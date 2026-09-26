import bpy
bpy.ops.wm.open_mainfile(filepath=r"C:\Users\leosp\Documents\Blender\Artic-Survival\Polar Bear Walking.blend")
me = bpy.data.objects["PolarBear"]
for m in me.data.materials:
    print("MAT", m.name, m.users)
    for n in m.node_tree.nodes:
        print("  ", n.type, n.name, getattr(n, "image", None) and n.image.name)
    for l in m.node_tree.links:
        print("  LINK", l.from_node.name, l.from_socket.name, "->", l.to_node.name, l.to_socket.name)
print("color attrs", [a.name for a in me.data.color_attributes])
