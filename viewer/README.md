# Local Arctic viewer

For public Vercel hosting, see [the deployment guide](../README.md).

Open http://127.0.0.1:8765 while the Node server is running.

To restart from the project directory: `node viewer/server.cjs`.

You control the human survivor. WASD or arrow keys move relative to the camera;
Shift runs and holding C crouches. Drag to orbit and scroll to zoom. R or
Control human restores the following camera after inspecting another asset.
Pause freezes both movement and animations. Animation clips switch automatically.

Animals run local state-based AI: land animals roam, foxes and penguins flee
nearby players, bears approach and stop nearby, fish swim, and orcas follow fish.
Land movement respects terrain, shorelines, steep slopes, and building bounds.
These are simple steering behaviors, without combat or full pathfinding.
The saved 25-chunk scene is finite; movement stops at its terrain boundary.
To refresh the terrain and placements after changing the Blender file:

`blender -b Terrain_World.blend --python viewer/export_viewer.py`

The browser uses the original GLB files and locally stored Three.js 0.170.0 modules.
The server binds only to the local computer and permits viewer files and the eight
asset GLBs, rather than exposing the entire project directory.
