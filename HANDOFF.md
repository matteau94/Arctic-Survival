# Arctic Survival — Handoff

State as of 2026-09-26. Written for a new agent picking up this project with no chat history.

| Asset | Status | Game file |
|---|---|---|
| Arctic Fox | Done. It sets the quality bar for every other asset. | `ArcticFox_Animated.glb` |
| Polar Bear | Done. The last mouth fix hasn't been reviewed. | `Polar Bear Animated.glb` |
| Orca | Done. `Orca Breach - side.mp4` is out of date. | `Orca_Animated.glb` |
| Fish | Done | `Fish Animated.glb` |
| Penguin | WIP. The v2 pass was stopped partway, and `penguin_build.py` has untested edits. | `Penguin_Animated.glb` |
| Human | WIP, paused. Animations exist only on a capsule stand-in. | none yet |
| Terrain / World | WIP | `terrain/`, `build_world.py` |

## Repo layout
- The root holds the current `.blend` sources, `.glb` exports, preview `.mp4`s and the build and animation scripts for each asset.
- `textures/` holds the PBR maps and `Scenery/` holds the prop `.glb`s.
- `Archive/` holds superseded early versions that were moved in from `Documents\`.
- `dev-scripts/<session-id>-<topic>/` holds working scripts copied from each Claude session's temp scratchpad. Iterations, tests and render helpers are mixed together; the sections below say which ones matter.
  - `dev-scripts/d7c0e9bb-arctic-fox/recovered-foxwork/` was rebuilt from the Write calls in the fox session's transcript. The originals were deleted, and later Edit-tool changes may be missing.
- Git LFS tracks `.blend`, `.glb`, `.png`, `.jpg`, `.hdr`, `.exr` and `.mp4` files. The `.blend1` backups are ignored.
- The full chat transcripts are in `C:\Users\leosp\.claude\projects\C--Users-leosp-Documents-Blender-Artic-Survival\<session-id>.jsonl`. Search them with grep; they're too large to read whole.

## Tooling
- Blender 5.2 runs headless: `"C:\Program Files\Blender Foundation\Blender 5.2\blender.exe" -b file.blend --python script.py`
- Python is Blender's bundled copy, `...\Blender 5.2\5.2\python\bin\python.exe`. There's no system Python.
- Never kill every `blender.exe`. Stop only the processes you started.

## Project conventions (from the auto-memory files)

Memory lives in `C:\Users\leosp\.claude\projects\C--Users-leosp-Documents-Blender-Artic-Survival\memory\` (index: MEMORY.md).
- **Modeling in Blender** (`modeling-in-blender.md`): every modeling, rigging, animation or mesh-edit prompt is done in Blender. Don't ask which tool to use. Script Blender headless (`blender -b --python ...`) and export to the project format (usually .glb).
- **Quality bar** (`arcticfox-quality-bar.md`): `ArcticFox_Animated.glb` is the reference (sculpted anatomy, detailed albedo and normal maps, ~25k verts, 34 bones, 4 polished clips). The user's words: "make it as good as the arctic fox, if not better. PUSH YOURSELF AND YOUR AGENTS". A smooth procedural loft with flat colours (penguin-style) was rejected. Render new assets next to the fox under the same lights and camera, and iterate.
- **Subagents** (`subagent-per-task.md`, which overrides the older "at most 3" in the fox note): give each sub-task its own subagent, **at most 3-4 running at once**, and queue the rest. The lead writes the shared contract/core first. Each agent owns its own files, and they chain through `blender -b X.blend --python a.py --python b.py`.
- **No final previews** (`no-final-previews.md`): don't render preview MP4s or contact sheets at the end of a task, because the user said "I can look at it on my own." A full preview pass takes ~15 min. Use `--no-preview` flags (e.g. `orca_export.py -- --no-preview`, `human_export.py -- --no-preview`) and tell subagents the same. Small test renders while tuning are fine. Report numbers, not pictures.
- **Human asset WIP** (`human-asset-wip.md`): the resume note for the paused human asset (summarised below).
- Tooling: Blender 5.2 is at `"C:\Program Files\Blender Foundation\Blender 5.2\blender.exe"`, and its bundled Python (with numpy) is at `...\Blender 5.2\5.2\python\bin\python.exe`. There is no system python and no ffmpeg (the human export agent built contact sheets through Blender's VSE instead). Headless EEVEE runs at ~1-2 s/frame.


## Polar Bear

**Status:** Done and in use. Run, Walk and Idle are finished. The mouth has gone through many rounds of fixes; the last one (lip flush) Claude graded **B** ("could use a little work") and no reviewer has scored it since. Known cosmetic issues are listed under Open issues.

**Files** (project root, checked on disk 2026-09-26)
- Source model: `Polar Bear.glb`. It is static, has no skin or animations, is byte-identical to `Archive/Polar Bear.glb`, and must never be edited. Every build starts from it.
- `Polar Bear Running.blend`: rig plus the `Run` action. Scene 60 fps, frames 1-22.
- `Polar Bear Walking.blend`: same rig, with `Walk` active and `Run` kept as a fake user. Frames 1-56. Idle is **not** saved in either blend.
- Game exports:
  - **`Polar Bear Animated.glb`** is the main game file. It holds `Idle`, `Run` and `Walk`, on a 37-joint skin.
  - `Polar Bear Running.glb` has only `Run`; `Polar Bear Walking.glb` has only `Walk`.
- Mesh: `PolarBear`, about 10.4k verts and 18.4k tris, one material `Material_0`. Its textures are packed inside the blend and embedded in the glb (4× 2048² images); there are no external texture files. The vertex-colour attribute `LipLine` exports as `COLOR_0`. **The engine material must multiply vertex colour, or the black lip line disappears.**
- Scale: the rig `PolarBearRig` is built at 100× (1 unit = 1 cm) and the armature object is scaled 0.01. The exported bear is tiny: about 0.15 m long, 0.077 m tall, facing −Y. Scale it up in the engine.
- Previews (EEVEE, re-rendered after the lip-flush fix):
  - `Polar Bear Running.mp4` and `Polar Bear Running - side.mp4`
  - `Polar Bear Walking.mp4` and `Polar Bear Walking - side.mp4`
  - There is no Idle video in the project.
- Superseded, in `Archive/`: the 09-22 run (`Polar Bear Running.blend/.glb/.mp4`, `- side.mp4`, and an old `polar_bear_run.py` from before the mouth/ear changes).

**Animations** (checked in the blend files and by parsing the glb files)
| Clip | fps | Keys | Loop | Duration in glb | In-place speed at model scale |
|---|---|---|---|---|---|
| `Run` | 60 | frames 1-23 (last key = first) | 22-frame loop, 0.367 s | 0.383 s | about 0.43 m/s |
| `Walk` | 60 | frames 1-57 | 56-frame loop, 0.93 s | 0.95 s | 0.075 m/s |
| `Idle` | 60 | 300 frames | 5 s loop | 5.017 s | stationary; exists **only** in `Polar Bear Animated.glb` |

- All clips are in place (no root motion). Multiply the speeds by whatever scale you use in the engine.
- The Run gait is a transverse gallop at about 2.7 strides/s. Footfall timing was matched frame by frame (both 24 fps) to real footage of a polar bear chasing a reindeer (YouTube 9WpBLwIGhVc).
- The Walk is a lateral sequence: LH, LF, RH, RF, about 70% duty factor.
- The Idle stands four-square with breathing, a side-to-side weight shift, head scans and a nose-up sniff.
- The rig has 37 bones: root, body, lumbar, pelvis, belly, thorax, neck, head, jaw, ear.L/R, then per leg scapula/humerus/radius/manus/digits (fore) or femur/tibia/pes/digits (hind), plus `ctrl.*`/`ctrl_toe.*` IK paw controls.

**How it was built** (all headless: `blender -b <file> --python <script>`)
1. **`polar_bear_run.py`** (root) is standalone:
   - Imports `Polar Bear.glb`.
   - Builds the anatomical skeleton at 100×, with joints measured from mesh slices on a 1 cm grid.
   - Bone-heat weights, then custom ear weights.
   - Adds IK paw controls, keys `Run`, and corrects paw height so each sole touches the ground.
   - Writes `Polar Bear Running.blend/.glb`. Tunables are at the top: `CYCLE`, `SWEEP`, `TOUCH`, `DUTY`, `SWING`, `JAW_*`, `EARS_BACK`.
2. **`polar_bear_walk.py`** (root) is *not* standalone. It runs on the Running blend with the rig loaded, adds `Walk` and keeps `Run`. It was originally run live through the BlenderMCP socket (port 9876); `Polar Bear Walking.blend` is the result.
3. **`polar_bear_mouth.py`** (root) bakes the closed mouth into the rest shape of the rigged mesh:
   - Jaw closed −30°.
   - Lip seam snapped onto a smooth `line_z(y)` curve, a Taubin relax, and the `LipLine` vertex colour painted.
   - It rebuilds from the original open-mouth geometry every time (stored in the mesh attribute `rest_open`), so it is safe to re-run.
   - It auto-runs these extension hooks, in order:
     - `polar_bear_mouth_1_corners.py`: no smile at the corners.
     - `_2_crease.py`: sharp geometric crease where the lips meet.
     - `_3_lipband.py`: black lip band (colour hook).
     - `_4_philtrum.py`: groove under the nose.
     - `_5_lipflush.py`: the upper lip no longer juts past the lower one.
   - Order matters: the lipband resets the lip-area colour, so it must run before the philtrum.
4. **Idle:** `polar_bear_idle.py` exists **only in the scratchpad** (`dev-scripts/adcca42e-*/polar_bear_idle.py`) and has hard-coded absolute paths. Run it on `Polar Bear Walking.blend`. It keys `Idle`, execs `polar_bear_mouth.py`, and exports `Polar Bear Animated.glb` without saving the blend.
5. **Final re-export pipeline** (what the session actually ran; `S` = scratchpad):
   ```
   blender -b "Polar Bear Running.blend" --python polar_bear_mouth.py --python $S/mouth/save_export.py -- Run "Polar Bear Running.glb"
   blender -b "Polar Bear Walking.blend" --python polar_bear_mouth.py --python $S/mouth/save_export.py -- Walk "Polar Bear Walking.glb"
   blender -b "Polar Bear Walking.blend" --python $S/polar_bear_idle.py      # -> Polar Bear Animated.glb
   ```
   - `save_export.py` saves the blend and exports with ACTIVE_ACTIONS and force sampling.
   - The full rebuild from scratch is run → walk → mouth → idle.
6. **Previews and helpers** in the scratchpad:
   - EEVEE video scripts: `preview_run_as_ee.py`, `preview_run_as_side_ee.py`, `preview_walk_ee.py`, `preview_walk_side_ee.py`. They use the Standard view transform, not AgX, which made the fur look tan.
   - Contact sheets: `v3/contact.py`, `v3/contact_walk.py`.
   - Joint measurement: `v3/joints.py`, `v3/slices.py`.
   - Mouth extension working copies and variants are in `ext/` and `flush/`. The finals were copied to root as `polar_bear_mouth_N_*.py`.
   - `faststart.py` moves the MP4 moov atom to the front. Blender's MP4s played as a black screen in the user's player until they were remuxed with it.

**Style/quality decisions & user feedback**
- The user rejected the first run as "doesn't look realistic", then asked to "literally synch one leg at a time to a real video". Then: "reanimate from scratch… think about the locomotor systems… (BUT DON'T MAKE THEM ON THE ASSET)". That means the anatomy lives in bones only, and no geometry is added.
- Motion that satisfied the user:
  - Head carried low.
  - The scapula swings along the ribs (bears have no clavicle).
  - Pigeon-toed forepaws.
  - Hind paws land heel first.
  - Planted legs 70-95% extended, not crouched.
  - Zero foot slide: planted paws move back at exactly the travel speed.
- Mouth history (the most contentious area):
  - Rejected "looks like a smile / curls up in the back".
  - A panting open-mouth "chase" face, then rejected "shouldn't always hang open". **The mouth is now always closed in every clip; do not add panting.**
  - Rejected "top lip shouldn't go over the bottom one". Keep them flush, even though an AI reviewer said real bears overhang slightly.
  - Rejected "zig-zag wavy line". Wants one clearly defined smooth lip line.
- The user wants independent review: "ask an opus 5.5 agent with no context". The exact question they want asked is "Does the mouth of this animated polar bear look EXACTLY like a real polar bear?"
  - Fresh reviewers scored 3 → 4 → 5/10, then "No" with 5 points.
  - Points 1, 2, 4 and 5 were fixed. Point 3 (the chin is too big and round) was **not** addressed.
- Grading scale the user set: A identical, B could use a little work, C about 30 min to fix, D made it worse, F much worse. Apply a fix only if it is an improvement.
- The user likes one subagent per sub-fix in parallel, with ext hook files merged afterwards, and wants time estimates when asked.
- Keep the Idle only in `Polar Bear Animated.glb`; the user said "store it only" there.
- **Never glob-delete `*.blend1`.** An earlier cleanup permanently deleted the user's `ArcticFox_Animated.blend1`. Delete only the backups you created, by exact name.

**Open issues / next steps**
- Mouth:
  - The final lip-flush version has not had an independent re-score.
  - The lower-lip dark rim reads slightly beaded or thick in close 3/4 view.
  - The upper lip slopes back a bit steeply under the nose.
  - The chin is full or round (reviewer point 3, open). Mesh resolution around the mouth is coarse, which caps sharpness.
- Deformation:
  - The left buttock bulges when the thigh swings forward (Run).
  - The HR paw lifts about 2 mm early at push-off.
  - A faint chest crease and hind-thigh bunching were noted in earlier versions.
- Rebuild fragility:
  - Move `polar_bear_idle.py` and `mouth/save_export.py` into the repo root, and replace their absolute paths with paths next to the blend.
  - `polar_bear_walk.py` needs the Running blend loaded; it cannot rebuild from the glb.
- No Idle preview video exists. Idle is not in any `.blend`; it is regenerated each time.
- Possible next clips (the user has not asked for any): swim, attack or swipe, turn.

## Arctic Fox

**Status:** Done. 8 clips are exported, and the fox is the project's **quality bar**: new animals must match or beat it (see memory). Minor known issues are listed under Open issues.

**Files** (project root, checked 2026-09-26)
- **`ArcticFox_Animated.blend`** is the current source. It holds all 8 actions, each on its own **muted** NLA track (this is how they all export), with `ArcticFox_Trot` active. Scene 30 fps.
  - It also contains the hidden `RedFox_Reference` mesh (the untouched converted source, which carries the `KeepMask` vertex colour).
  - Plus the `FoxPreviewCam`, `StageFloor`, `StageWall` and `StageSun` preview objects.
  - Its mtime (09:58 local) is later than the glb's (09:37); another session may have opened and saved it. Re-export if in doubt.
- **`ArcticFox_Animated.glb`** is the game export: mesh `ArcticFox`, 34-joint skin, 8 animations, embedded textures.
- **`ArcticFox_Working.blend`** is superseded. It is the older state with only the 4 locomotion actions (formerly `Documents/ArcticFox_FromGLB.blend`). `.blend1` backups of both blends exist.
- Mesh and texture:
  - `ArcticFox`: 24.5k verts, about 31k tris, material `ArcticFox_Fur`, parented to `FoxRig`.
  - It is about 1.02 m long and 0.42 m tall, faces −Y, with its origin on the ground. Scale is real-world, so no rescale is needed.
  - Recoloured base colour: **`textures/ArcticFox_BaseColor.png`** (2048², relative path `//textures\...`).
  - The normal, roughness and other maps are the original Fox.glb images, packed in the blend (`Image_0..3`).
- Superseded, in `Archive/`:
  - `Fox.glb`: the user-supplied red fox, the source of the current model.
  - `ArcticFox.blend` plus `ArcticFox_Textures/` (AO, BaseColor, Normal, Roughness). This is the first fox, **built from scratch** out of metaballs, voxel remesh and baked textures, with a separate hinged `FoxJaw`, tongue, teeth, eyes and nose. The user abandoned it when they provided `Fox.glb`. It still has unfixed red specks on the chest from a UV overlap.
- No preview MP4s: the user said "don't need to render", and the frames were deleted in cleanup.

**Animations** (checked in the blend and glb; 30 fps; the action custom props `speed_m_per_s`, `loop_frames` and `looping` exist in the blend only, not in the glb)
| Clip | Frames (keys) | Length | Type | Speed |
|---|---|---|---|---|
| `ArcticFox_Idle` | 0-90 | 3.0 s | loop | 0 |
| `ArcticFox_Walk` | 0-26 | 0.867 s | loop | 0.35 m/s |
| `ArcticFox_Trot` | 0-16 | 0.533 s | loop | 0.938 m/s |
| `ArcticFox_Gallop` | 0-11 | 0.367 s | loop | 2.091 m/s |
| `ArcticFox_Sniff` | 0-120 | 4.0 s | loop | 0 |
| `ArcticFox_Dig` | 0-24 | 0.8 s | loop | 0 |
| `ArcticFox_Pounce` | 0-58 | 1.933 s | one-shot | 0 (the body travels about 0.5 m forward inside the clip) |
| `ArcticFox_LieDown` | 0-72 | 2.4 s | one-shot | 0 (starts at rest pose, so it blends from Idle) |

- All clips are in place. The last key equals the first on loops.
- Bones (34): root, hips, spine1-2, chest, neck1-2, head, ear.L/R, scapula/upperarm/forearm/hand/toes_front .L/.R, tail1-6, thigh/shin/hock/toes_hind .L/.R.

**How it was built** (there is no root script. Work was done live in Blender through the **BlenderMCP socket, port 9876**, by exec-ing scratchpad scripts. Two scratchpad roots belong to session d7c0e9bb.)

*Model conversion (red fox → arctic fox), 09-22.* Scratchpad `C:\Users\leosp\AppData\Local\Temp\claude\C--Users-leosp-AppData-Roaming-Claude-scratch-workspaces-beda0dcd-…-scratch-2026-09-22-0b3d57\d7c0e9bb-…\scratchpad\`. This is **outside** the Artic-Survival temp dir; make sure it is copied too.
- `reimp.py` imports `Fox.glb` and applies the root transform. `scale.py` rescales to 0.9 m nose to tail and renames the object `ArcticFox`.
- `deform4.py` does the final reshape. It keeps the `RedFox_Reference` copy, and makes the ears about 30% shorter and rounder, the muzzle shorter, the legs about 20% shorter, the coat thicker with a neck ruff and cheeks, and the tail bushier. Earlier versions are `deform.py`-`deform3.py`; the `*.txt` files are snippets.
- `posbake.py` bakes a position map, and `recolor.py` repaints `Image_0` to a white winter coat, keeping the fur detail.
- `maskbake.py` builds the `KeepMask`, so the claws and paw pads keep their original colours.
- `rig.py` builds `FoxRig`. `weights5.py` does the final weights: island-aware, with separate fur shells for legs and body. `tuck.py`/`cull.py` tuck the shell rims 3-4 mm into the body and set backface culling so the shell seams are hidden.
- `anim.py` is an early gait draft.
- **Missing:** the final Idle/Walk/Trot/Gallop scripts and their data (`gaits.py`, `anim.py`, `sheet.py`, `final.py`, `deliver.py`, `video.py`, `vchunk.py`, `venc.py`, `isl.npy`, `posmap.npy`) lived in `C:\Users\leosp\AppData\Local\Temp\foxwork\`. That folder was **deleted** in cleanup.
  - Their original contents are recoverable only from the `Write` tool inputs in `~/.claude/projects/C--Users-leosp-Documents-Blender-Artic-Survival/d7c0e9bb-….jsonl`: grep `foxwork\\\\gaits.py`. Later in-place edits may not be captured.
  - Because of the missing `.npy` files, the conversion scripts are not re-runnable as they are. Treat `ArcticFox_Animated.blend` as the source of truth.

*New clips (Sniff, Dig, Pounce, LieDown), 09-26.* Scratchpad `…\C--Users-leosp-Documents-Blender-Artic-Survival\d7c0e9bb-…\scratchpad\fox\`.
- **`foxlib.py`** is the real animation toolkit. Exec it inside Blender with `FoxRig` loaded. You write `pose(t, f)`, which returns a dict of keys:
  - Body: `hips_off`, `hips`, `chest`, `flex`, `neck`, `neck_yaw`, `head` (gaze-stabilised).
  - Ears and tail: `ears`, `tail` (slopes in degrees), `tail_sway`.
  - Legs: `feet` (paw-ball targets), `pastern`, `toe`, `scap`, `knee_pole`.
- Then call `bake(name, frames, fn, loop, fps=30, speed)`. It solves the legs with 2-bone IK, reports reach (a value >1.0 means the paw falls short) and paw ground height (z ≈ 0.02 at rest), and puts the action on its own muted NLA track.
- `sheet(actions, view, count)` renders contact sheets. The docstring holds the coordinate conventions.
- Clip scripts: `sniff/pose.py` (+ `run.py`/`run2.py`), `dig/dig.py`, `pounce/clip.py` (+ `run.py`), `liedown/ld.py`. The `r*.py`, `probe.py` and `look*.py` files are iteration helpers.
- `open.py` opens `ArcticFox_Animated.blend` in the live session. `test.py` is a smoke test.
- **`save.py`** removes the test action and cameras, saves the blend, and exports the glb with `use_selection` on fox + rig, `export_animation_mode='ACTIONS'`, and force sampling. It then prints the clip list.
- To add a clip headless, run `blender -b ArcticFox_Animated.blend --python <clip script>`, where the clip script execs `foxlib.py`, calls `bake`, and then does the `save.py` steps.

**Style/quality decisions & user feedback**
- The original brief was to match the polar bear's style: smooth, semi-realistic sculpted forms, a warm off-white coat with fine fur grain, no hair strands. "DONT ANIMATE YET" at first.
- For the from-scratch fox the user asked for toes, baked textures and a hinged mouth interior. They then pivoted and supplied `Fox.glb` to convert instead.
- What the user asked for:
  - Arctic-fox conversion: shorter, rounder ears; shorter muzzle; shorter legs; thicker coat; bushier tail; white winter coat with no red-fox markings (no black stockings, no dark ear backs).
  - Keep the original claws and paw pads.
  - "Don't forget to add color": the texture must travel with the files.
  - Anatomy lives only in the rig (a scapula swing, digitigrade wrists and hocks, a gaze-stabilised head, tail follow-through); no geometry is added.
- File moves: the user got angry at slowness ("MOVE TEH FILES", "PRIORITIZE SPPED"). For file shuffling, be fast and don't overthink. They asked to delete unused files, which is how `foxwork\` and the preview frames were lost.
- For the new clips, the user wanted "3-4 new animations… one subagent per animation" with Claude choosing the behaviours. Claude chose real arctic-fox behaviours (mousing pounce, dig, sniff, lie down). The user accepted them without complaint.

**Open issues / next steps**
- Pounce:
  - At frame 41 (impact) the forelegs fold under the chest for one frame.
  - The chest sits very low in the final pin.
- LieDown: 8-11 fur verts at the tucked hind hock and the sternum sink up to 4-5 mm below the ground.
- Dig:
  - The chest is less low than in a real dig (limited to about 9° pitch before the front legs fold badly).
  - The forelegs look slightly rubbery mid-stroke.
- Sniff: the ears only pitch (the rig has no ear yaw), so "listening" is a forward/back flick. Consider adding ear yaw/roll bones.
- Separate fur shells:
  - A thin dark slit shows at the thigh-shell edge in Cycles only. It is hidden in EEVEE and in engines by backface culling. Keep culling on in the engine.
  - An airborne paw can fall up to about 1 cm short of its planned path, because RF sits further forward than LF in the source pose.
- Speeds are not in the glb. Hard-code them in the game controller (0.35 / 0.938 / 2.091 m/s).
- Optional work: pull the `foxwork` gait scripts back out of the JSONL into the repo, add a turn, jump, death or eat clip, and render a preview video. The user said "don't need to render" before, so ask first.


## Orca

**Status:** DONE (user accepted). The breach was re-tuned lower on 09-26. Known issues are minor: short teeth, fin roots sink into the flank when tucked, and one stale preview MP4.

**Files** (project root; all tracked in git as of the initial commit)
- Source rig: `Orca_Rigged.blend` (23:09, 09-25). Mesh `Orca`, 40,716 verts. Material `Orca_Skin`. Armature `OrcaRig` has 20 bones: root, body, chest, head, jaw, blowhole, pectoral_01/02.L/R, tail_01..05, fluke, fluke_tip.L/R, dorsal_01/02. The orca is about 6.1 m long in real metres, faces -Y, and +X is its left.
- Animated: `Orca_Animated.blend` (10:05, 09-26). Every `Orca_*` action sits on its own muted NLA track; `Orca_Swim` is the active action.
- Game asset: `Orca_Animated.glb` (43.7 MB, 10:06, 09-26). It re-imports with 42,352 verts because glTF splits vertices at UV seams, 20 bones and 3 embedded 4096² maps.
- Textures: `textures/Orca_BaseColor.png`, `Orca_Normal.png` and `Orca_ORM.png` (R=AO, G=rough, B=metal), all 4096², PNG.
- Previews: `Orca Swimming - side.mp4`, `Orca Bite - side.mp4`, `Orca Bite - 3q.mp4`, `Orca Surface - side.mp4` and `Orca Breach - side.mp4`, all from 23:10–23:15 on 09-25. **`Orca Breach - side.mp4` is STALE**: it shows the old high jump from before the retune. Either re-render it or ignore it.
- The `.blend1` backups for Orca_Animated and Orca_Rigged were deleted on 09-26. Orca_Rigged.blend1 was deleted by mistake; the user was told.

**Animations** (verified in both the .blend and the GLB; 60 fps; frames 0..N)
| Action | Frames | Sec | Loop | Game root motion |
|---|---|---|---|---|
| Orca_Swim | 0-180 | 3.0 | yes | move 3.0 m/s |
| Orca_SwimFast | 0-108 | 1.8 | yes | move 8.0 m/s |
| Orca_TurnL / Orca_TurnR | 0-180 | 3.0 | yes | 3.0 m/s + yaw 25°/s toward turn (TurnL = toward +X) |
| Orca_Idle | 0-240 | 4.0 | yes | none |
| Orca_Breach | 0-240 | 4.0 | no | root carries travel: (0,0,-2.5) -> (0,-13.43,-2.5); water at z=0 |
| Orca_Bite | 0-120 | 2.0 | no | none. Lunge, jaw about 34°, snap, 2 head shakes |
| Orca_Surface | 0-330 | 5.5 | no | root travels about 8.4 m along -Y; blowhole breaks z=0; roll-forward dive |

- Loops close exactly (last frame == first).
- Bite and Surface start and end on the Idle frame-0 pose. Breach starts and ends on the Swim frame-0 pose, with the root offset.
- Current breach: exits at 6.5 m/s at 60°, 1.15 s airtime, body-centre peak 1.6 m, snout peak 3.2 m. The fluke tips just clear the water (~8 cm) and it lands with a side slap.
- Old breach: 9 m/s at 72°, centre peak 3.7 m, 12.75 m of travel. Game code that uses 12.75 must change to 13.43.

**How it was built / re-run**
1. `blender -b --python orca_build.py` builds the mesh (lofts, a numpy "sculpt", mouth lining, conical teeth, eyes with lids, fins), bakes and paints the textures, rigs and weights. It writes `Orca_Rigged.blend` and `textures/Orca_*.png`. Each rebuild takes several minutes because of the 4K bakes.
2. Then run the chain:
   `blender -b Orca_Rigged.blend --python orca_anim_swim.py --python orca_anim_extra.py --python orca_export.py [-- --no-preview] [--no-qa] [--qa-dir <dir>]`
   - `orca_anim_swim.py`: Swim, SwimFast, TurnL/R, Breach. Its docstring cites the breach references.
   - `orca_anim_extra.py`: Idle, Bite, Surface.
   - `orca_export.py`: NLA tracks, saves the .blend, exports the GLB (ACTIONS mode, force-sampled), renders the MP4s, then runs QA. QA re-imports the GLB, runs 33 checks, compares against `ArcticFox_Animated.glb` and `Penguin_Animated.glb`, and writes a look sheet to --qa-dir (default `%TEMP%\orca_qa`). QA resets to factory settings, so it must run last.
   - The full chain takes about 15 minutes with previews. **Pass `--no-preview` by default** (see feedback below).
- Motion approach: a dorso-ventral travelling wave (a real cetacean stroke; up/down, not side-to-side). Damped-spring follow-through drives flukes, fluke tips, dorsal fin, pectorals and jaw. For loops the springs run over several cycles and the last cycle is kept. Heavy springs sit on the root channels to give the feel of a 4–6 t animal.
- Scratchpad-only scripts in session 7bb4c7a2 (not needed to rebuild):
  - `fox_look.py` / `fox_look_blend.py`: fox comparison lighting.
  - `orca_build_v1/v2/r1final/r2a.py`: earlier build snapshots.
  - `breachfix/` (`measure.py`, `endchk.py`, `orca_anim_swim.orig.py`): the pre-retune breach.
  - Many ed*.py / pec*.py probes.

**Style/quality decisions & user feedback**
- User: "look the same style as the other animated animals". The penguin scripts were the procedural template: one mesh, one material, PBR maps, real metres, facing -Y.
- User: "make it as good as the arctic fox, if not better. PUSH YOURSELF". The fox is the quality reference (~24.5k verts, 34 bones, sculpted anatomy, eyelids and irises, rich maps). This is saved in memory as the bar for new animals.
- Final comparison against the fox: 8 clips vs 4, 4K vs 2K maps, UV use 1.47 vs 1.20. The orca is behind on texel density (1072 vs 2707 px/m), BaseColor detail (1.24 vs 9.28) and normal strength (0.024 vs 0.096). This is deliberate: pushing the detail harder made the smooth wet skin look like orange peel or wood grain.
- Reviewer fixes applied:
  - Round white eye patch -> long, tilted teardrop.
  - Flat maroon mouth -> tongue, gums, ridged palate, dark throat.
  - Shark-triangle teeth -> ivory, conical, interlocking.
  - Fin seams hidden with custom normals.
  - Flat black -> charcoal with a grey saddle, rake scars and slightly yellowish whites.
- User chose to **keep the PNG textures** and the 43.7 MB GLB ("i have storage space"). Do NOT switch to JPEG.
- User: the orca "jumps too high". The breach was re-tuned against Halsey & Iosilevskii 2020 (J. Exp. Biol.), Segre et al. 2020 (eLife) and the Center for Whale Research.
- User: **"don't make a preview video or image at the end of task. i can look at it on my own."** Run with `--no-preview` and don't send contact sheets. Quick internal test renders are OK.
- User only wanted `Orca_Animated.blend1` deleted, not `Orca_Rigged.blend1` as well. Only delete exactly what is asked.

**Open issues / next steps**
- Teeth are short so they stay hidden when the mouth is closed. Tips peek out at about 6° jaw opening (Bite f24), and wide open they look small from a pure side view.
- Tucked pectorals (sprint, inside of turns, parts of the breach) sink slightly into the flank at their base. It isn't visible at game distance.
- Re-render the breach MP4 only if the user asks.

## Penguin

**Status:** WIP / interrupted. `Penguin_Animated.glb` has 9 clips and is usable. The user stopped a v2 "beat the fox" improvement pass partway through. `penguin_build.py` holds **untested** model/texture edits (last changed 10:52) made after the last rebuild (10:18).

**Files** (project root; all tracked in git)
- Build script: `penguin_build.py` (v2 rewrite, 10:52). It is untested since 10:18; if run, it overwrites `Penguin_Rigged.blend` and `textures/Penguin_*.png`.
- Rig: `Penguin_Rigged.blend` (10:18, 09-26). Mesh `Penguin`, 32,008 verts. Material `Penguin_Feathers`. `PenguinRig` has 18 bones: root, body, spine, chest, neck, head, jaw, flipper_upper/lower.L/R, tail, thigh/shin/foot.L/R. About 0.99 m tall, standing on z=0, facing -Y. A killed rebuild ran after 10:18; the file opened fine for verification.
- Animated: `Penguin_Animated.blend` (10:41) and `Penguin_Animated.glb` (19.1 MB, 10:41; 36,870 verts after re-import, 3 embedded 2048² maps). `Penguin_Animated.blend1` exists.
- Textures: `textures/Penguin_BaseColor.png`, `Penguin_Normal.png` and `Penguin_ORM.png`, 2048², from 10:18.
- Previews: `Penguin Walking - side.mp4`, `Penguin Running - side.mp4` and `Penguin Swimming - side.mp4` (10:44–10:48), rendered at low quality.
- Scratchpad backups in session b2f5e96f: `penguin_build_v2_backup.py` and `penguin_anim_orig.py` (the v1 4-clip script).

**Animations** (verified; 60 fps; frames 0..N; all in place; root loc/rot keyed in every clip)
| Action | Frames | Sec | Loop | Notes |
|---|---|---|---|---|
| Penguin_Idle | 0-240 | 4.0 | yes | breathing, weight shift, looks around, beak click, flipper flick |
| Penguin_Walk | 0-48 | 0.8 | yes | waddle; **move root 0.20 m/s** (feet planted via analytic 2-bone IK) |
| Penguin_Run | 0-28 | 0.47 | yes | flee waddle, pitched ~20° forward; **root 0.60 m/s** |
| Penguin_Slide | 0-48 | 0.8 | yes | belly toboggan, alternating kicks |
| Penguin_Swim | 0-60 | 1.0 | yes | flipper beats with feathering, feet as rudders |
| Penguin_Call | 0-300 | 5.0 | yes | emperor display call, jaw ~24° |
| Penguin_Peck | 0-180 | 3.0 | yes | folds ~105°, 3 pecks at the snow (beak touches the ground plane) |
| Penguin_Hop | 0-90 | 1.5 | yes | two-footed hop, ~0.13 m flight |
| Penguin_Death | 0-180 | 3.0 | NO | topples onto its right side; still from ~2.3 s, hold the last frame |

**How it was built / re-run**
1. `blender -b --python penguin_build.py` builds the lofted mesh (body, beak with separate mandibles, flippers, clawed webbed feet, tail fan, eyes), paints feathers in numpy (thousands of individual feathers; normal map derived from height), then rigs and weights. It writes `Penguin_Rigged.blend` and the textures. Takes about 2 min.
2. `blender -b Penguin_Rigged.blend --python penguin_anim.py [-- --no-preview]` builds all 9 clips on NLA tracks, saves `Penguin_Animated.blend`, exports the GLB and renders 3 MP4s. It also applies `_fix_stray_leg_weights()` as a safety net.
- The final re-import check on the 10:41 GLB never finished because the agent was stopped. This run's verification confirmed that all 9 clips, the frame ranges and the textures are present.

**Style/quality decisions & user feedback**
- v1 (00:25–01:25, 09-26): emperor penguin in the fox/bear/fish style, about 28k verts, 4 clips. Known weak spots:
  - The code-generated texture looks clean and less detailed than fur.
  - Slight bulge at the flipper root when the flippers are raised.
  - Claude noted that emperors are Antarctic, not Arctic; the user didn't respond to that.
- User (14:04): "make it much better and compare it to the arctic fox. IT IS A COMPETITION but don't tell the arctic fox agent that." Never mention the competition to any fox-related agent.
- v2 goals given to the model agent:
  - better silhouette (head, chest, belly)
  - wider orange ear patches
  - soft belly feathers, not "fish-scaly"
  - fix artifacts
  - tuck the feet in
  - keep bone names unchanged
- v2 animation agent: added Run, Call, Peck, Hop and Death (done).
- User: "assign subagents to each task". Later: "stop running subagents", "stop", then "make it so the blender copies ARE NOT running".
- Process-safety feedback (important): in v1, Claude force-killed ALL `blender.exe` processes, including the user's own session. Only kill processes you started, identified by PID or command line. Never kill the user's GUI Blender (it had Human_Stub.blend open) or other sessions' background jobs.

**Open issues / next steps**
- Decide with the user whether to finish v2. If so:
  1. Run `penguin_build.py` (untested edits).
  2. Render and inspect it against the fox.
  3. Re-run `penguin_anim.py -- --no-preview`.
  4. Re-import the GLB to check it.
  5. Do a fox side-by-side (the planned "third agent" step never happened).
- Alternatively, revert `penguin_build.py` to the scratchpad `penguin_build_v2_backup.py` or git HEAD. Git HEAD already contains the 10:52 edits, so check the diff first.
- The flipper-root bulge at high raise may still be there.

## Fish

**Status:** DONE. The user said "the fish is fine" and turned down rig upgrades. `Fish Animated.glb` has 9 clips with all fixes; the per-clip files were moved to the Recycle Bin at the user's request.

**Files** (project root; all tracked in git)
- `Fish.glb`: the ORIGINAL unrigged salmon (09-25 20:00). Keep it; it is the input to `fish_prep.py` and is superseded as a game asset by `Fish Animated.glb`.
- `Fish_Rigged.blend` (09:42, 09-26): mouth closed and rigged, with the smoothed weights from the Startle fix. `Fish_Rigged.blend1` (09-25) holds the old weights.
- Game asset: `Fish Animated.glb` (13.0 MB, 09:48). Source scene: `Fish Animated.blend` (09:47); a `.blend1` also exists.
- Scene layout: `RootNode` empty (scale 0.01, carried over from Fish.glb) > `FishRig` (21 bones) > mesh `Fish`, 12,912 verts, material `Material_0` with the original 2048² textures. Mesh-local units: snout y=-2.33, tail tip y=+3.61. The fish faces -Y.
- Rig bones: root, spine_01, head, jaw, operculum.L/R, eye.L/R, spine_02..05, caudal, caudal_tip, pectoral.L/R, pelvic.L/R, dorsal, adipose, anal.
- No textures folder entry and no MP4s. The per-clip `Fish <Clip>.blend/.glb/.mp4` files are gone (Recycle Bin).

**Animations** (verified in `Fish Animated.blend`; 60 fps; frames start at 1, and loops key frame N+1 == frame 1)
| Action | Frames | Sec | Loop | Notes |
|---|---|---|---|---|
| SwimCalm | 1-145 | 2.4 | yes | 3 tailbeats (1.25 Hz), 2 breaths, fin steering, eye gaze |
| SwimFlee | 1-25 | 0.4 | yes | 3 beats at 7.5 Hz, fins folded, mouth/gills never fully shut |
| Idle | 1-217 | 3.6 | yes | hover; pectorals scull alternately; 3 breaths; eye flicks |
| TurnLeft / TurnRight | 1-145 | 2.4 | yes | same tempo as SwimCalm; BEND 0.55, head lead 12°, bank 15°; Right = mirrored Left |
| Bite | 1-76 | 1.25 | no | coil, lunge, 24° gape, 3-frame snap, settle; **no head shake**; starts and ends on the rest pose |
| Startle | 1-28 | 0.47 | no | C-start in ~50 ms; last frame == SwimFlee frame 1, so chain straight into SwimFlee |
| Flop | 1-181 | 3.0 | yes | on its side on the ice: thrash, hop, gasp, plus yaw pivot about 42° and a slide (readable from above); lowest vertex kept at z=0 |
| Death | 1-195 | 3.25 | no | spasm, weakening beats, rolls belly-up about 188°; still from 2.8 s, hold the last frame |

- All clips stay in place; the game moves the fish.
- `fish_merge.py` exports without slide-to-zero, so in the GLB each clip starts at t=1/60 s. The standalone flee export used slide-to-zero. Harmless, but note it if exact timing matters.

**How it was built / re-run**
1. `blender -b --python fish_prep.py` reads `Fish.glb` and writes `Fish_Rigged.blend`.
   - Closes the mouth: rotates the lower jaw about 10° up about JAW_PIVOT, baked into the mesh.
   - Builds `FishRig`.
   - Computes weights. The body uses linear hat weights, window-smoothed along the body (the Startle fix), and stays exact at the head, jaw and gills.
2. Each clip script, `blender -b Fish_Rigged.blend --python fish_<clip>.py [-- --export]`, creates or replaces only its own action (with fake user). The clip scripts are `fish_swim_calm`, `fish_swim_flee`, `fish_idle`, `fish_turn` (both turns), `fish_bite`, `fish_startle`, `fish_flop` and `fish_death`.
   - `--export` writes a per-clip `Fish <Clip>.blend/.glb`. The user deleted those files; don't recreate them unless asked.
   - `--stills <dir>` renders check frames.
3. **The normal rebuild:** `blender -b Fish_Rigged.blend --python fish_merge.py`. It exec's all 8 clip scripts (it cuts off fish_swim_flee's save/export tail) and writes `Fish Animated.blend` and `Fish Animated.glb` (ACTIONS mode, force-sampled). If `fish_prep.py` changes, re-run step 1 and then the merge.
- Motion approach: a lateral travelling body wave, with amplitude growing toward the tail and per-beat variation; clips share the wave model so they blend.
- Scratchpad-only scripts in session fbcfbe27: probes and contact-sheet helpers (`sheet.py`, `render_views.py`, `mirrorchk.py`, `glbcheck.py`, `startle/patch.py`, `startle_fix/render.py`, `flee/opt.py`, …). None are needed to rebuild. The Startle agent saved a backup of the pre-fix `Fish_Rigged.blend` in that session's scratchpad.

**Style/quality decisions & user feedback**
- User's first instruction: "close the mouth of the fish" before any animation. The mouth must stay closed at rest.
- The user also said to "automatically assume every modeling prompt will be in blender" (saved to memory).
- Workflow the user asked for:
  - One subagent per animation.
  - Each subagent asks fresh no-context Opus reviewers for realism feedback. Two rounds for the swims; one round for the later clips; skipped for the fixes.
- User: **"no need to render. i can open file in 3d viewer"**. No preview videos; still frames only, for self-checks.
- User: **"the bite shouldn't shake its head"** (fish Bite only; the orca Bite does have head shakes).
- User declined rig upgrades ("no the fish is fine"): extra tail-stock spine bones and split caudal lobes.
- User: "fix all and assign one subagent per task". Fixes made:
  - Turns made stronger.
  - Startle C-bend lumps fixed through weight smoothing.
  - Flop made readable from a top-down camera.
- User: "delete all fish animation files not part of fish animated.glb". Claude moved 30 files to the Recycle Bin (recoverable).
- Process safety: the flee agent once ran `taskkill /F /IM blender.exe`, which killed every Blender on the machine. Never do this.

**Open issues / next steps**
- Rig limits, accepted by the user:
  - The tail stock thins on the inside of bends.
  - The caudal fin has a single bone, so it can't cup.
- Turn clips: around frame 25 the tail sweep is large. If it is too much in-game, lower `BEND` in `fish_turn.py` to about 0.45.
- Flop grounding was not re-measured after the pivot/slide change; check it in the viewer.
- Flop has no flip-over. Suggested option: a separate one-shot "flip" clip.
- Nobody has watched the combined 9-clip GLB in motion; each agent only checked stills.


## Human asset (arctic survivor) - WIP, PAUSED

**Status:** WIP, paused by the user on 2026-09-26 ~14:57Z ("finish now ... make a good point to continue from"). The rig and all 11 animation clips exist and run on the capsule stub. The real model (`human_build.py`) has geometry, weights and UVs, but its texture and final-save sections are empty placeholders, so **`Human_Rigged.blend` has never been produced**. Session 3c568333 is idle, and its 3 subagents were stopped by the user.

**Files** (project root). Everything listed was committed in `b1ef1cc Initial commit` (10:58 local):
- `human_rig.py` (lead-owned, DONE): the skeleton contract. `build_armature()` creates `HumanRig` with 66 bones (63 deform + `root` + grip sockets `prop.L/R`). Faces -Y, +X is the character's LEFT, metres, ~1.78 m tall, boot soles at z=0. A-pose (arms 40 deg below horizontal), quaternion pose bones. It includes face bones (jaw, eyes, upper/lower lids, brows), `hood_01>hood_02` down the back, 3-bone fingers and thumbs, and `thigh>shin>foot>toe`. Bone local axes are documented in the docstring (a positive local-X rotation curls a finger). `blender -b --python human_rig.py` writes `Human_Stub.blend` (rig plus a capsule mannequin `Human`).
- `human_build.py` (model agent, ~2200 lines, INCOMPLETE): builds the model from SDFs and lofts. The head has a detailed face, eyes, mouth interior, teeth, ears, and hair/beard/brow shells plus lashes. The outfit is a parka with pockets, sleeves, trousers, gaiters, boots and soles, a beanie with goggles and strap, the hood lying down with a fur ruff, a scarf loop and tail, five-finger gloves, and a belt with knife, sheath, pouch, toggles and cords. There are 25 part ids in the point attribute `part`. The file also contains skin weights (stress poses passed: walk, overhead, crossed arms, twist, kneel, fist, jaw, blink, brows) and UVs (ABF for organic parts, Smart UV for small hard parts, mirrored halves, per-part texel scaling). Placeholders `@@DOC@@` (line 6), `@@WEIGHTS@@` (1745, a stale marker because the weights section exists), `@@TEXTURES@@` and `@@FINAL@@` (end of file) are unfilled. `HUMAN_STAGE=geo` saves `Human_geo.blend` to `$HUMAN_SCRATCH`, which **defaults to the project dir**. Set `HUMAN_SCRATCH` to avoid writing into the project. `HUMAN_RES` (default 4096) sets the texture size. Intended outputs are `Human_Rigged.blend` and `textures/Human_{BaseColor,ORM,Normal}.png`; none exist yet.
- `human_anim_locomotion.py` (DONE on the stub, no STATUS block): `Human_Idle` (360f loop), `Human_Walk` (62f, 1.30 m/s), `Human_Run` (44f, 4.50 m/s), `Human_CrouchIdle` (300f), `Human_CrouchWalk` (80f, 0.90 m/s). All clips are 60 fps, keyed on every frame on every bone, linear, loops closed, and in place: `action["speed_mps"]` holds the speed and the game moves the object toward -Y. Legs use analytic 2-bone IK baked to FK with a heel/ball/toe-tip rocker foot model, and secondary motion uses damped springs. The long docstring covers the biomechanics. The agent's last state was "waiting for Human_Rigged.blend to validate on the real mesh". Flags: `-- --test-save <path>`.
- `human_anim_extra.py` (DONE on the stub, has a STATUS block): `Human_Gather` 210f, `Human_Attack` 78f, `Human_Throw` 114f, `Human_WarmHands` 240f loop, `Human_Hurt` 48f, `Human_Death` 156f. One-shots start and end on Idle frame 0. Event times in seconds are stored on the action as custom props (`event_grab/hit/release/impact`). Ground contact is calibrated against the real deformed mesh at runtime. Flags: `--test-save`, `--only A,B`.
- `human_export.py` (DONE on the stub, has a STATUS block). It puts each clip on its own NLA track, saves `Human_Animated.blend`, and exports `Human_Animated.glb` with 4 influences and extras. It optionally renders previews (`-- --no-preview` skips them, and **per the memory rule they should be skipped**). QA re-imports the GLB and produces a strict human-vs-ArcticFox scorecard ("beats fox: yes/no") plus a look sheet in `--qa-dir` (default `<temp>/human_qa`). The QA step wipes the session, so it must run last.
- Outputs currently on disk were **built from the STUB and are placeholders**. `Human_Animated.glb` (2.8 MB): one mesh `Human` with 19,800 verts (capsules), no materials or images, 66 joints, all 11 clips with speed/event extras. `Human_Animated.blend` is the same stub build. Stub preview MP4s: `Human Gather - 3q.mp4`, `Human Walking - side.mp4`, and `Human Attack - 3q.mp4` / `Human Throw - side.mp4`, **which are broken 48-byte files**. Delete or regenerate these after the real build.
- `Human skeleton.glb` (24 MB, user-supplied): **not a rig**. It is a 26 cm anatomical bone-mesh skeleton (60k verts, 5x2K textures, no armature or animation). Its only use is as an anatomy reference, scaled to 1.78 m to check joint placement. It is not used yet.
- Scratch dev scripts: `...\Temp\claude\...\3c568333-...\scratchpad\{model,loco,extra}\`. Examples are `model/posetest.py` (stress poses), `model/fox_render.py`, `model/uv_section.py`, `extra/fixstub.py` (fixes the stub weights), `extra/mp4sheet.py` (contact sheet from mp4 via VSE), `extra/slip.py` (foot slip), and `loco/verify.py`.

**Architecture / how to run:**
```
blender -b --python human_rig.py                                      # Human_Stub.blend (dev only)
blender -b --python human_build.py                                    # -> Human_Rigged.blend + textures (NOT working yet)
blender -b Human_Rigged.blend --python human_anim_locomotion.py --python human_anim_extra.py --python human_export.py -- --no-preview
```
The same chain runs on `Human_Stub.blend` in ~70 s with `--no-preview`. The animation scripts never save and only `human_export.py` writes files. The lead owns `human_rig.py`, and the other scripts import it and never edit it.

**Style/quality decisions & user feedback:**
- The user asked for "a very advanced human asset, identical in style to the other assets" and then said "push them hard, it needs to beat the fox". Targets given to the agents: 3+ render/critique rounds next to the fox, a dedicated close-up pass on the face (a weathered man, not a mannequin), layered clothing with real folds, and clean stress poses. Foot slide must stay under 5 mm, there must be no ground penetration, loops must close exactly, and knees must not pop. Clips need clear wind-up, impact and follow-through with facial reactions, and the death must settle on the ground without sinking. The final judgement is the strict scorecard's "beats fox" verdict.
- Look: weathered male survivor in a beanie with goggles, a parka with a fur-trimmed hood down, a scarf, five-finger gloves, boots, and a belt with knife and pouch. Movement is heavy and trudging (short steps, high snow steps, abducted arms from the bulky parka, cold hunch and shiver in the idle).

**Open issues / next steps:**
1. Finish `human_build.py`: write the `@@TEXTURES@@` section (4K BaseColor/ORM/Normal bakes; the agent was adding loft coords `lu/lv` to the ruff and scarf for strand/knit patterns) and `@@FINAL@@` (material and save `Human_Rigged.blend`), then fill `@@DOC@@` with a STATUS block. Remove the stale `@@WEIGHTS@@` marker. Check the vertex budget against the fox (~25k); the agent was already trimming beard, tuft and finger density.
2. Run the full chain on `Human_Rigged.blend`. Re-validate locomotion and extras on the real mesh (heel and ground calibration adapt to the mesh). Open items in the extras STATUS: the Throw right-foot yaw of 5 deg must keep the toe tip under 1.5 mm/frame, a 3rd critique pass is due on Hurt, WarmHands and Attack, and a debug `lie calib` print in `death()` should be removed.
3. Run the QA scorecard, and send failures back to the model until it reports "beats fox: yes".
4. `Human_Stub.blend` has broken weights (capsule islands split across bones). Devs used a scratch copy fixed by `extra/fixstub.py`.
5. Optionally scale `Human skeleton.glb` to 1.78 m and check joint placement in `human_rig.py`.

## Terrain / World (streamed arctic-antarctic continent) - WIP

**Status:** WIP. The user stopped all feature agents at ~14:59Z ("just finish now"), and session f8f3e1a5 is still open. It last asked the user whether to test and fix the stopped modules and rebuild. Streaming and materials are DONE. Mountains, valleys, rivers and ocean were stopped mid-work, but **all of them import and run**. I checked this on 2026-09-26 against a scratch copy: `build_world.py` built 25 chunks with features at the default spawn in 2.3 s and at a coastal spawn in 3.7 s, with no errors. `Terrain_World.blend` on disk is stale, built at 10:32 before most feature work.

**Files** (all committed in `b1ef1cc`, except that `terrain/mountains.py` has an uncommitted 3-line tuning diff: CIRQUE_BAND 0.10-0.30, PEAK_GAIN 1.45, MASSIF_POW 1.6):
- `terrain/config.py`: constants. 1 unit = 1 m, +X east, +Y north, +Z up, origin at the continent centre ("pole"). `CHUNK_SIZE` = 16 mi = 25,749.5 m. `VIEW_RADIUS = 2` gives a 5x5 grid. `CONTINENT_RADIUS` = 1400 mi (~2,250 km, continent ~2,800 mi across), `WORLD_RADIUS` = 2500 mi (open ocean beyond, ~310 chunks across). `PLATEAU_HEIGHT` = 2800 m, `SEA_LEVEL` = 0, `SEED` = 1337. `LOD_RES` = {ring 0: 257, ring 1: 129, ring 2: 65} verts per edge (~100 m / 200 m / 400 m spacing). `SPAWN` = (1,050,000, 420,000), which is chunk (40,16) **on the interior plateau at 2.5-4.7 km elevation, not coastal**.
- `terrain/noise.py`: vectorised deterministic perlin/fbm/ridged/warp/hash2. A harmless uint64 overflow RuntimeWarning appears in `hash2`.
- `terrain/network.py`: shared drainage network. Channels are zero-contours of warped noise, with major valleys spaced ~40-80 km and minor ones ~8-15 km apart. Valleys carve along it, rivers follow it, ridges sit between channels, and fjords open where it meets the sea.
- `terrain/world.py`: **the contract**. It sets the height pipeline order `ocean.continent` -> `+mountains.height` -> `valleys.carve` -> `rivers.carve` -> `ocean.coast`. `surface()` computes masks: snow/rock from slope, then each module overrides ice/water/etc. It also defines `ChunkContext`, `sample_chunk(cx,cy,lod)` with seam-exact sampling `X=(cx+i/(res-1))*CHUNK_SIZE`, and `chunk_of(x,y)`. Every module is a pure function of world metres, so chunks can be generated in any order.
- `terrain/mountains.py`: named ranges (Transantarctic ~3,200 m, Ellsworth ~3,600 m above the plateau) plus noise belts. The massif is ridged multifractal suppressed toward network channels, with Worley cirques and nunataks on 10 km cells. Low-frequency inputs sit on a world-aligned 500 m lattice. `chunk_objects` returns [].
- `terrain/valleys.py`: U-shaped glacial troughs. Major floors are 2-5 km wide and 1.5-2 km deep in ranges; minor tributaries hang above the trunk. Floors come from a smooth regional B-spline lattice so they drain toward the coast. API: `valley_info` (used by rivers), `floor_height`, `carve`, `surface`. The lead warned that "the valleys agent was mid-rewrite", but it runs.
- `terrain/rivers.py`: frozen trunk rivers 60-400 m wide, widening toward the coast, plus tributaries 40-110 m, meander warp, and frozen lakes. `chunk_objects` adds one merged `RiverIce` ribbon mesh per chunk for LOD <= RIBBON_MAX_LOD, with an alpha-clipped shader (`River_Ice`) that reconstructs a crisp outline.
- `terrain/ocean.py` (largest, ~56 KB): continent outline (star-shaped in warped space, so there are no stray islets) and ice-sheet dome. It also builds the shelf, slope and ~-3,750 m abyssal plain, coast types (ice cliff / rocky headland / beach), floating ice shelves, and fjords. `chunk_objects` builds the water plane, sea ice and icebergs (`Ocean_Water`, `Ocean_SeaIce`, `Ocean_Iceberg` materials; bergs instance 6 prototypes). `find_coastal_spawn()` returns (1,961,940, 752,276), chunk (76,29): land 15-30 km from a dramatic coast overlooking a fjord. **It is not yet wired into config/build.** Noise tables are cached to `terrain/__pycache__/ocean_tables_<hash>.npz` (gitignored).
- `terrain/streaming.py` (DONE): see Architecture. `terrain/materials.py` (DONE): shared `Terrain_Mat` (snow/rock/ice/water driven by the `surf` colour attribute, world-offset noise so there are no seams), `add_distance_fog()`, and `setup_world()` (polar sky, low sun ~8 deg, mist). Shared materials use a fake user so chunk cleanup never deletes them.
- `build_world.py`: writes `Terrain_World.blend` (generated, 9.3 MB, currently stale) and `export_chunks.py` writes `chunks/chunk_{cx}_{cy}.glb` plus `chunks/manifest.json` (generated, **never run**, and `chunks/` doesn't exist). `terrain/prof.out` is a gitignored profiler dump.
- Scratch dev scripts: `...\Temp\claude\...\f8f3e1a5-...\scratchpad\` (root: `test_stream.py`, `bench.py`, `run_export.py`, `stubs.py`...; subdirs `mtn/`, `ocean/`, `rivers/`).

**Architecture / how to run:**
```
blender -b --factory-startup --python build_world.py -- [--spawn X Y] [--out Terrain_World.blend] [--no-features]
blender -b --factory-startup --python export_chunks.py -- --center X Y [--radius 2] [--outdir chunks/] [--lod 0] [--no-features]
```
- Streaming (`ChunkManager`) keeps exactly (2*VIEW_RADIUS+1)^2 = 25 chunks around the `Player` empty (falling back to the scene camera). Each chunk is an empty `Chunk_{cx}_{cy}` in collection `TerrainChunks`, with child mesh `Terrain_{cx}_{cy}` and each module's `chunk_objects(ctx)`, built chunk-local and parented to `ctx.root`. LOD follows the Chebyshev ring and a chunk is rebuilt when its ring changes. Vertical skirts hide LOD cracks. Hysteresis is ~2 km past a border. The budget is at most 2 builds per update, nearest first, with a 0.12 s early stop; `load_all_now()` builds synchronously. Measured: the 5x5 grid loads in 2-4 s, a single chunk in <=0.6 s while walking, and a LOD0 chunk samples in ~0.3 s.
- Mesh data: built with numpy through `foreach_set`, with `surf` colour attribute RGBA = (snow, rock, ice, water) and seam-exact `custom_normal`.
- Floating origin: `scene["terrain_offset"]`. On re-base it shifts chunk roots, the Player (including location keys), free cameras and viewports. `Player["world_x"/"world_y"]` holds the true position; error was <5 cm after 3 re-bases.
- Live in the UI: the `.blend` holds a Text datablock `terrain_boot.py` (Register on) that adds the .blend folder to sys.path and calls `terrain.streaming.register()` (depsgraph, frame-change and load_post handlers plus a 0.25 s timer). The user must click **Allow Execution / Trust**, and the .blend must stay next to `terrain/`. Move the `Player` with G or keyframe it, and chunks stream in and out. `PlayerCam` sits at eye height, clip end 200 km.
- Game-engine path: `export_chunks.py` writes chunk-local GLBs (SW corner at the origin, glTF Y-up). Engine placement is `(origin_x, 0, -origin_y)`. The manifest holds chunk size, origins, lod/res and z-range. Shade from COLOR_0 = packed masks, since the procedural Blender shaders don't export. The engine should mirror streaming.py: keep the 5x5 grid around the player and use a floating origin.

**Style/quality decisions & user feedback:**
- User's brief: an arctic/antarctic setting "stretching for thousands of miles in each direction", rendering only ~2 chunks each way "similar to minecraft (chunk = 16 miles)", with mountains, frozen rivers, valleys, and "an ocean at the end of antartica".
- Process: one subagent per feature ("assign a subagent for each task"), at most 3-4 at a time. The run used streaming, mountains, valleys and ocean, with rivers queued. No preview renders; report numbers instead.
- Realism targets: Antarctic-like named ranges, nunataks, hanging tributary valleys, level river ice, ice cliffs, fjords, ice shelves, sea ice and bergs, and a coastal spawn that shows the ocean.

**Open issues / next steps:**
1. The lead offered to test the four stopped modules, fix or stub any broken ones, and rebuild; the user had not replied. They do run (checked above), but nobody has reviewed their quality or seams since the stop. Re-run the per-module validation scripts in the scratchpad (e.g. `rivers/seam.py`, `mtn/val.py`, `test_stream.py`).
2. Wire in the coastal spawn: set `config.SPAWN` to `ocean.find_coastal_spawn()` or pass `--spawn 1961940 752276`, then rebuild `Terrain_World.blend` with features.
3. Mountain height: the plateau (2,800) plus ranges peaked at ~4.7 km in the spawn chunk, and PEAK_GAIN was being tuned down (uncommitted diff). Decide the final values and commit.
4. Object count: the coastal 5x5 grid created 175 `Berg_*` objects plus 9 SeaIce, 14 Ocean and 6 RiverIce. The contract says to "keep object counts low", so consider merging bergs per chunk.
5. Run `export_chunks.py` once and check the GLBs and manifest. Decide on far-LOD/impostor handling beyond ring 2 (the horizon is currently just fog at ~64 km).
6. Commit after the rebuild (`Terrain_World.blend` is committed and will change).

