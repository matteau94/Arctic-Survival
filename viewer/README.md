# Local Arctic viewer

Open http://127.0.0.1:8765 while the Node server is running.

To restart from the project directory: `node viewer/server.cjs`.

Click a species to focus it; click again or use Next animal to cycle individuals.
Drag to orbit, scroll to zoom, right-drag to pan. WASD travels, Shift speeds up,
and + / - changes travel speed. The animation menu plays the selected asset's clips.
Pause stops all animation. Water can be hidden for underwater viewing.

This is an interactive browser rendering of the saved 25-chunk Blender scene,
not a screen broadcast or an unlimited procedural world. Orca pursuits are scripted.
To refresh the terrain and placements after changing the Blender file:

`blender -b Terrain_World.blend --python viewer/export_viewer.py`

The browser uses the original GLB files and locally stored Three.js 0.170.0 modules.
The server binds only to the local computer and permits viewer files and the seven
asset GLBs, rather than exposing the entire project directory.
