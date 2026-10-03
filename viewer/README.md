# Arctic Survival browser game

## Habitat waypoints

Fox dens and penguin nesting colonies have floating icons anchored above their
world locations, each with its name and live distance in metres. Icons move with
the camera, remain visible through terrain, and disappear when behind you or
outside the screen. The compass-style locator strip has been removed.
Press **Esc** to release the
cursor and use the **Locations** list to pin or unpin sites, then resume the
expedition. Marker preferences are saved in this browser. Outdoor waypoints
are hidden while using inventory or inside a tent.

The saved terrain supplies four den entrances and one nesting colony. The browser
adds deterministic visible habitat geometry to target 40 dens and 10 colonies,
concentrating new sites around the spawn at roughly one tenth of the original
habitat spread. Original sites remain. New sites are placed on sampled terrain;
they do not add new animal actors. This detail is generated in memory rather
than saved into the Blender world.
Sites that cannot pass dry-ground, ice, slope, clearance and spacing checks are
omitted rather than represented by markers without geometry. The console reports
any shortfall; actual generated counts are in `scene.userData.habitatDensity`.
`viewer/data/waypoints.json` is refreshed by the normal terrain exporter. To
refresh just habitat coordinates without rewriting terrain geometry, run Blender
with `--background --factory-startup --disable-autoexec Terrain_World.blend
--python-exit-code 1 --python scripts/export-habitat-waypoints.py`.


For public Vercel hosting, see [the deployment guide](../README.md).

Open http://127.0.0.1:8765 while the Node server is running.

To restart from the project directory: `node viewer/server.cjs`.

Click **Enter world** to control the human survivor and lock the mouse cursor.
Press **E** or click **Inventory [E]** to open the climber's backpack. It holds
up to 24 stacks and 20 kg, begins with basic expedition supplies, and saves its
contents in this browser. Select an item to inspect it; discarding requires
confirmation and permanently removes one item. Inventory pauses the expedition
and releases the cursor. Close it with **E**, **Esc**, or **Close**, then click
**Resume expedition** to continue.

You start with a small tent and sleeping bag. Select either in **Inventory**,
then **Place on ground**. Look and move to position the preview in front of you,
press **R** to rotate, and click when it is green to place. **Esc** cancels without
using the item. Placement needs dry, clear, gently sloping ground; a sleeping bag
can fit inside the tent. Placement removes one item from the backpack and saves
the campsite together with inventory in this browser. Older inventory saves get
the camping kit once; if that exceeds capacity, remove items before adding more.
Sleeping effects, packing up, consuming supplies, and gathering are not implemented.

Placing a tent starts an 8.5-second setup animation: reach for the backpack,
carry the packed tent, unroll its groundsheet, and raise the canvas. Movement is
held during setup; mouse look stays available. Esc cancels and keeps the tent
in inventory. Opening inventory also cancels; losing focus pauses setup until
you resume. The tent is consumed and saved only after assembly completes.
Move the mouse to turn the survivor and look up or down. A centered third-person
camera follows behind the character, similar to Minecraft's rear third-person
view, and moves closer when terrain or buildings obstruct it.

WASD or arrow keys move relative to your facing direction; Shift runs and holding
C crouches. Press Esc to pause and release the cursor, then click **Resume
expedition** to continue. Pausing freezes movement, animal AI, and animations.
Animation clips switch automatically. The world has no animal selection menu.
The survivor's step cadence follows movement speed. Boot contact adapts to slopes,
and sampled sole contact presses geometric heel/toe depressions into a local snow
mesh in any pose. The depth map is bounded and repeated contact cannot deepen a
hole indefinitely. Turning in place uses short steps while the body follows the
camera smoothly, then settles back to idle.

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

Walk to the tent's front zipper and press **F** to unzip and enter a separate, warmly lit 7 x 8 metre interior. Use WASD or arrows to walk inside. Approach the interior zipper and press **F** to return to your entry position outside. E still opens inventory; camping equipment placement is currently outdoors only. Tent walls block walking through the canvas. Reloading starts outdoors; saved tents remain.
