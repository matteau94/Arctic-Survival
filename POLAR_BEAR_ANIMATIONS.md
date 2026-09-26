# Polar bear animations

`Polar Bear Animated.glb` is the combined runtime asset. The Blender source is
`Polar Bear Animated.blend`. The closed-mouth mesh is inherited from
`Polar Bear Walking.blend`; animation generation does not modify facial geometry.

| Clip | Motion | Playback |
| --- | --- | --- |
| Idle | Planted stance, breathing, head scan and scenting | Loop, 5 s |
| Run | Existing running motion | Loop |
| Walk | Existing walking motion | Loop |
| Swim | Alternating forepaw paddles, relaxed hindlegs | Loop, 1.2 s |
| ShakeOff | Head-led axial shake and damped recovery | Once, 1.8 s |
| SitStand | Lower to seated hold, then return to standing | Once, 3 s |

New clip scripts were revised by separate Astra agents using low reasoning.
All clips use the same rig. Source animation rate is 60 fps. Loop builders include
a duplicate endpoint; exported duration can include an additional initial frame.
Swim is an in-place motion intended to be positioned at the game's water surface.

## Rebuild

Open `Polar Bear Walking.blend` and execute `build_polar_bear_animated.py` in Blender.
It writes candidate assets into `dev-scripts/astra-combined`. Review these before
replacing the root asset. The builder reuses the original Idle motion without
rerunning its historical mouth-edit or export steps.

`render_polar_bear_clips.py` renders previews from an already-open combined scene.
Pass clip names after `--`; add `video` to render MP4s as well as key poses.
Preview scenery is not included in the exported bear asset.
