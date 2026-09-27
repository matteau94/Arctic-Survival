# Arctic Survival browser game

For public Vercel hosting, see [the deployment guide](../README.md).

Open http://127.0.0.1:8765 while the Node server is running.

To restart from the project directory: `node viewer/server.cjs`.

Click **Enter world** to control the human survivor and lock the mouse cursor.
Move the mouse to turn the survivor and look up or down. A centered third-person
camera follows behind the character, similar to Minecraft's rear third-person
view, and moves closer when terrain or buildings obstruct it.

WASD or arrow keys move relative to your facing direction; Shift runs and holding
C crouches. Press Esc to pause and release the cursor, then click **Resume
expedition** to continue. Pausing freezes movement, animal AI, and animations.
Animation clips switch automatically. The world has no animal selection menu.

The corner FPS counter shows the measured frame rate. Rendering starts at native
CSS-pixel resolution and lowers resolution while playing if frame times are high.
Terrain tiles outside the camera view are culled. Distant animals are hidden and
their simulation freezes beyond 1,000 metres; nearby animals resume automatically.
Animation updates are less frequent at a distance. These choices target 30 FPS;
the achieved rate still depends on the GPU, browser, and viewport size.

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
