# Arctic Survival browser game

## Handaxe and wood

Open **E → Handaxe → Equip / Hold**, resume outdoors, face a streamed conifer
within **1.65 m of its trunk**, and **left click**. Equip replaces held Trail food;
both items remain in the backpack. Use **Put away** to free your hands for P/petting.
F/shelter/feed and G/follow/stay retain their existing roles.

Four hits fell a conifer and add **3 Wood**, **0.5 kg each**, stacks of **12**.
The final hit requires room for the whole reward (weight and stack slots). A
visible refusal leaves the tree at 3/4 hits so you can make room and retry.
Wood is carried material only; there is no crafting or axe durability.

The loaded `Human_Attack` clip supplies the swing: 0–0.40 s anticipation,
0.40–0.54 s strike, impact at 0.54 s, recovery to its loaded duration (currently
1.30 s). Movement is locked for the swing; the existing mixer advances it once
per frame. Opening UI, losing focus, shelter entry, spectator mode, death or
changing held equipment cancels the swing. Cancellation restores full-weight
idle with a zero-time mixer evaluation and retains the remaining cooldown.
Reach, facing, resident tree identity and terrain/obstacle/trunk LOS are checked
again at impact from the player. The target must also be inside the camera
frustum and pass camera-to-contact LOS at selection and impact. That segment is
capped at **7.5 m**: the existing 4.5 m camera boom + 2.5 m player LOS limit +
0.5 m camera aim-height offset. Both segments ignore only the target trunk.

Felled IDs use expedition seed, cell and original candidate index. Up to **512**
are retained until the expedition ends; reaching the limit refuses further
chopping rather than evicting IDs and regrowing harvested trees. Up to **64**
partial damage records are retained; those clear when their render chunk leaves
the stream. A fall shares the tree geometry/material, tilts for 1.25 s, then
settles/sinks and disappears at 2 s; at most **4** falls exist. Collision and LOS
remove the harvested trunk at reward commit. Falling trees are cosmetic.

Source cost bounds: targeting reads at most 9 resident chunks / 72 candidates
without generating plans; prompt scans run at most once per 0.15 active seconds,
plus fresh click/impact checks. Player LOS takes at most 14 terrain samples;
camera LOS takes at most 39, including both endpoints (53 combined). The helper
has a hard ceiling of 64 terrain reads per segment, uses existing obstacle lists
and cached local tree queries, and fails closed on unknown cells without
synchronous generation or scene mesh raycasts. Falling visuals update at most
4 transforms per active frame.
Existing streaming caps remain 25 chunks / 200 standing instance slots, four
plans and one chunk upload per frame. These are source bounds, not measurements.

## Cold and shelter

Exposure starts at 0 and increases by 1 per active outdoor game second. At 360
the expedition ends from cold. Cold shares movement's delta capped at 0.05 seconds
per frame: at 10 FPS, six game minutes take about twelve real minutes. The HUD
shows exposure and approximate remaining outdoor game time to one decimal
second at each update (at most once per second except immediate shelter/pause state changes), with warnings
at 120 and 240. Use E to place your tent, then approach its zipper and press F,
or approach a fox den entrance and press F. A bare tent holds exposure steady without
recovering. Inside, use E → Sleeping bag → Place to enable recovery of 3 exposure
seconds per active game second in that tent; a den interior recovers 1, down to 0.
Bags in inventory, previews, outdoors or another tent do not warm the occupied tent.
Deployed gear cannot be packed up or moved during the expedition.
Setup and door entry count outdoors until actually
inside; exiting uses the actual inside state too. Setup plus the entry transition
to inside takes 11.15 game seconds, plus positioning time; this is not a guaranteed
rescue duration. There are no movement penalties.

Loading, pause, inventory, tab blur and spectator mode freeze exposure and
recovery; returning from spectator retains exposure. Death blocks play and
interactions. Only clicking **Restart fresh expedition** reloads from the death
screen, starting with a fresh world, backpack and zero exposure.

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
up to 24 stacks and 20 kg and begins with basic expedition supplies. Inventory
lasts only for the current session. Select an item to inspect it; discarding requires
confirmation and permanently removes one item. Inventory pauses the expedition
and releases the cursor. Close it with **E**, **Esc**, or **Close**, then click
**Resume expedition** to continue.

You start with a small tent and sleeping bag. Select either in **Inventory**,
then **Place**. Look and move to position the preview in front of you,
press **R** to rotate, and click when it is green to place. **Esc** cancels without
using the item. Placement needs dry, clear, gently sloping ground; a sleeping bag
must be placed from inside the tent to provide warmth. Placement removes one item from the backpack and keeps
the campsite only for the current session. Reloading starts a fresh world with
fresh starter supplies, including the tent and sleeping bag; previous camps are cleared.
Sleeping effects, packing up, consuming supplies, and gathering are not implemented.

Placing a tent starts an 8.5-second setup animation: reach for the backpack,
carry the packed tent, unroll its groundsheet, and raise the canvas. Movement is
held during setup; mouse look stays available. Esc cancels and keeps the tent
in inventory. Opening inventory also cancels; losing focus pauses setup until
you resume. The tent is removed from inventory and placed for this session only after assembly completes.
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

Walk to the tent's front zipper and press **F** to unzip and enter a separate, warmly lit 7 x 8 metre interior. Use WASD or arrows to walk inside. Approach the interior zipper and press **F** to return to your entry position outside. E opens inventory; place your sleeping bag inside to restore warmth. The bare tent only prevents further cold exposure. Tent walls block walking through the canvas. Reloading starts outdoors in a fresh world with fresh starter supplies; previous tents do not remain.
