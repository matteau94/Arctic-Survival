# Locomotion handoff

Validated in background Blender 5.2.2 against the real Human_Rigged.blend (73,641 vertices), every integer frame including the duplicated endpoint. No model or Human_Animated output was saved or overwritten.

## Changes
- human_anim_locomotion.py: outsole-measured heel and toe-tip pivots; corrected terminal swing to acquire ground velocity and landing orientation before contact; 0.2 mm sole allowance for measured foot/toe skinning compression; walking arm abduction 8 degrees, running 10 degrees with reduced crossover for winter gear/pack clearance. Existing torso leans retained (Walk 8 degrees, Run 13 degrees). No rig changes.
- dev-scripts/3c568333-human/loco/diagnose_loco.py: correct inverse-rest transform for contact probes; all-frame evaluated mesh sampling; exact vertex IDs, weights, phase and loop error; exporter-style contact slip plus a separate all-vertices-within-5-mm measure.
- measure_boot.py: reproducible boot geometry measurements.
- baseline.json / baseline.log: pre-fix evidence; diagnostic.json / diagnostic.log: final evidence.

## Root causes
Original worst Walk vertex 47193 (toe.R 100%) at phase 0.612903, -16.617 mm. Run vertex 44775 (toe.L 100%) at phase 0.272727, -16.232 mm. Full-frame CrouchWalk worst vertex 47189 (toe.R 100%) at phase 0.6625, -9.539 mm (even-frame sampling had missed it). Outsole toe vertices extend beyond the skeleton's toe tail pivot. The heel also extends past the hardcoded 50 mm probe. Final compression before allowance was only 0.113 mm at vertices weighted 75.9% toe / 24.1% foot.

Late-swing Hermite endpoint velocity did not ensure finite-frame contact speed. Acquiring both horizontal trajectory and orientation before landing fixes that without changing cadence or speed.

## Final measured results
| Clip | Frames | Speed m/s | Minimum mesh z mm | Proxy slip mm/frame | All near-ground vertices slip mm/frame | Loop error mm |
|---|---:|---:|---:|---:|---:|---:|
| Walk | 62 | 1.30 | +0.087 | 0.351 | 1.983 | 0 |
| Run | 44 | 4.50 | +0.103 | 0.078 | 2.191 | 0 |
| CrouchWalk | 80 | 0.90 | +0.088 | 0.329 | 0.714 | 0 |

All requested penetration failures and the crouch slip failure pass on the real mesh. The broader mesh-near-ground metric still exceeds 1.5 mm/frame for rolling/lifting vertices in Walk and Run; do not present this as every vertex passing. It includes vertices up to 5 mm above ground, including toe-off/rocker movement. Subframe interpolation and export roundtrip were not validated here.

Pack/clothing interference remains pending the model agent's updated mesh. The tested mesh still has 73,641 vertices. Arm clearance is a preparatory pose change, not proof that the final pack does not intersect. Re-run this diagnostic and a visual/full-cycle garment/pack clearance review once that asset arrives; coordinate any rig changes through the user.

Reproduce from workspace:
`& 'C:/Program Files/Blender Foundation/Blender 5.2/blender.exe' -b Human_Rigged.blend --python human_anim_locomotion.py --python dev-scripts/3c568333-human/loco/diagnose_loco.py`
