# Human model refinement handoff

## Scope
`human_build.py`, `Human_Rigged.blend`, and `textures/Human_BaseColor.png`, `Human_Normal.png`, `Human_ORM.png` are the model deliverables. Animation and export scripts are not edited. The coordinator must integrate and export the revised rigged blend.

## Supplied anatomical reference
The builder genuinely imports `Human skeleton.glb` on every rebuild. The source is a single anatomical mesh (59,670 vertices), not the 66-bone animation armature. Its measured height is 0.261501789 m. A uniform scale of 6.8450775 maps its floor/crown to z=0/1.790 m; its X bounding-box midpoint is centered. Z-up and -Y facing are retained. The source's relaxed arm pose is retained: it is not claimed to match the animation A-pose.

The builder measures skull cross-sections around each head contour. Measured skull half-width plus 6 mm of soft tissue guides skin width, with bounded corrections and a reduced blend near the eyes to preserve eyelid fit. Actual old/new widths, transform, and source SHA256 are saved in `human_qa_checkpoint/Human_alignment.json` and an embedded Blender text. The imported anatomy stays hidden in `REFERENCE_ONLY__Supplied_Anatomy`; it is not parented to HumanRig. Export only Human and HumanRig. This is a cranial proportion guide, not a reconstruction of the body's skin from the source skeleton.

## Winter equipment
The model includes the insulated parka, fur-trimmed hood, beanie, scarf, warm trousers, gloves, gaiters and boots. New pack components include a main load body, reinforced base, top lid, front and side compartments, padded shoulder harness, sternum strap, padded hip belt, buckles, compression webbing, carry handle, and a sleeping mat with spiral ends and attachment straps.

Pack components are part of the Human mesh. The load is weighted 75% spine_02 / 25% spine_03; shoulder harness sections blend up to 25% toward the corresponding clavicle. No rig bones or bone rest positions are changed. This maintains the existing animation interface but does not substitute for checking pack intersections through every action.

## Face and materials
Defined irises, limbal rings and pupils replace blank eyes. Skin has cheek/nose warmth, lip coloration, subtle under-eye variation and stubble. Hair shell boundaries blend toward underlying skin, and beard/temple shells use the full head grid. Lash geometry is shortened and thinned. Material-specific roughness replaces the previous part-index gradient. Bake-only vertex colors are removed after baking to prevent double multiplication in downstream glTF.

## Review artifacts
Before head, source anatomy, refined face, full body front, back, and rear three-quarter renders live in `human_qa_checkpoint/Human_*.png`. Review logs record rig endpoint agreement, skin-weight sums, map statistics, and mesh counts.

## Limitations
This remains a stylized procedural character. Fur and hair are surface shells, not groomed strands. The supplied anatomy guides skull width; the existing body and animation rig proportions are retained. Full action/contact/collision review and final GLB export are coordinator work. Do not interpret increased geometry or texture noise as proof that visual quality surpasses the fox.

The UV mirror lookup now searches only the matching anatomical/clothing part, fixing unrelated pale triangle contamination in the parka atlas. Face selection also clears stale vertex/edge selections before unwrapping. Backpack parts use automatic projection; the final unwrap pass emitted no warnings. Directional hair/fur albedo detail is included. Human_Roughness.png is synchronized from ORM.G.

## Completed review
- Saved model: 117,461 vertices / 118,084 polygons, with 66 bones.
- Exact rest matrices and parents compared against the preserved pre-refinement blend: no changes. Shared-contract bone endpoints: no changes.
- Vertex weight sums range from 0.99899995 to 1.00100004 (existing 0.001 quantization); influence limit remains four.
- All PBR maps are 4096 x 4096. Normal detail check: 1.487; ORM AO mean: 0.4456; roughness standard deviation: 0.1265 at the builder's 1024-pixel probe.
- Source SHA256 still matches: 5f7269adc78290bd56101333725c9c7549ea390a16e98f372f9fcbef997a3a26.
- Eleven measured skull slices actually influence head construction.
- Final face, front, back and rear three-quarter renders were opened and inspected.
- Hipbelt and lower front harness now follow pelvis/spine_01, blending to chest/clavicle at the upper shoulders; the load body remains 75% spine_02 / 25% spine_03.
- The coarse eyebrow shells were recessed 0.4 mm beneath the skin after the bake, exposing the smoothly painted brows. Their hidden polygons retain existing topology and weights. The saved model and builder both include this correction; the bake-only brow AO was not rerun after this small geometry adjustment.
- Original pre-refinement blend is preserved as Human_before_refinement.blend. Animated blend/GLB and animation/export scripts were not edited by this model pass.

Visual result: the pack silhouette and equipment are coherent, the eyes now have readable pupils, and the major UV color contamination and eyebrow stair-step artifacts are corrected. This is an improved stylized game character, not a claim that it definitively surpasses the fox's visual quality. Hair/fur shells and some clothing edges remain visibly procedural in closeups.
