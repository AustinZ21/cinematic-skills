# Pitfalls: every real failure from HOME, and the fix

## Look and story

| Symptom | Cause | Fix |
|---|---|---|
| "It feels like images switching, not a film" | zooming flat stills; nothing moves inside the frame | depth parallax + motion blur, and something alive in every shot (sprites, plumes, water, energy) |
| Shots feel randomly fast and slow | inconsistent zoom rates between shots | constant log-zoom rate inside a flow; match speed across cuts |
| Three shots in a row feel rushed | too many shots per bar | drop a shot rather than squeeze it |
| Ships look parked, crew look like a photo | the plate is a frozen moment | move what can move; leave people still unless you can animate them well (HOME's crew stayed still on purpose) |
| "That container looks like it's going to fall" | an animated object with weight moved unnaturally | leave heavy things exactly where the painting has them |
| Title card looks cheap | flat black background | starfield plate with parallax (`make_starfield.py`) |
| A white flash nobody asked for | a transition or a bright CG frame | never add flashes unprompted; run `flash_check.py` on every render |

## Depth renderer

| Symptom | Cause | Fix |
|---|---|---|
| Whole shot renders darker than the plate | sub-frame accumulation blended the canvas alpha too | blend colour only: `blendFuncSeparate(SRC_ALPHA, ONE_MINUS_SRC_ALPHA, ZERO, ONE)` (already in depthshot.js) |
| Near truss "melts into glass" | parallax too strong on a near structure | reduce `px`/`pz`; dilate the depth; frame the near object off the moving edge |
| Planet rings bend and warp | false relief in the depth map of a thin planar object | `pz: 0`, tiny or no `px` |
| Grey smear where an object was cut out | inpainting failed behind a large cut-out | fill from a matching texture (aligned + Lab colour-matched), or don't cut it out at all |
| Sprite detection grabbed a platform and a city chunk | automatic "dark blob" detection | pick sprites by known positions and appearance; special-case small ones |
| Ripples on the road, the banks and the rocks | water mask by colour threshold alone | seeded connected growth + glitter + rock exclusion + river polygon + erode (`water_mask.py`) |
| Some cables have no pulse halfway up | the line mask broke into segments | long vertical closing (220 px at 1080 wide worked) |
| The station itself glows | line detector hit station details | depth filter (keep far lines only) + x-range limit (`energy_mask.py`) |
| The glow swallows the subject | glow too strong / uncapped | thin mask, small glow, capped (`min(..., 0.75)`) |

## Blender (5.x, headless Python)

| Symptom | Cause | Fix |
|---|---|---|
| `enum "FRACTION" not found` on a Math node | scalar and vector math use different names | scalar `ShaderNodeMath`: `FRACT`; vector `ShaderNodeVectorMath`: `FRACTION` |
| Compositor setup does nothing | 5.x moved it | `tree = bpy.data.node_groups.new('Comp', 'CompositorNodeTree'); scene.compositing_node_group = tree` |
| Glare node settings fail | 5.x glare parameters are input sockets now | set `node.inputs[...]` values, not properties |
| Mix node inputs/outputs wrong | `ShaderNodeMix` has typed duplicate sockets | colour mix uses inputs 6/7 and output 2 |
| Scene build takes minutes | `bpy.ops` primitive creation in loops | build meshes with bmesh / numpy `foreach_set` |
| Camera roll is wrong for the shot | look-at alone doesn't control roll | solve roll so a chosen object axis reads at a chosen screen angle (`look_axis()` in the example) |
| Planet lit evenly, no day/night line | an emissive atmosphere shell was lighting it | make the shell emission camera-ray only; derive the lit side from geometry; use `Facing^7` for the rim, not `1-Facing` |
| Camera ends up inside the planet | absolute camera positions | position the camera relative to the hero object |
| Plume gradient reversed | Generated texture coordinates run the other way | flip the Generated Y |
| Download from the official mirror returns 403 | blocked scripted download | use another official Blender mirror and verify the SHA256 |

## ffmpeg

| Symptom | Cause | Fix |
|---|---|---|
| Magenta cast after grading | `lutrgb` + blend on the wrong pixel format | convert to `format=gbrp` first, use `colorlevels`/`colorbalance`/`eq` |
| Grade applies to the whole film | filter without a time gate | `enable='between(t,a,b)'` per filter |
| Colours shift between preview and player | missing colour metadata | tag bt709: `-color_primaries bt709 -color_trc bt709 -colorspace bt709` |

## Process

- An agent can't watch in real time or hear. It checks frames, contact sheets, flash scans and loudness numbers.
  A human must watch the final at full speed with sound.
- Notes work when they're physical and timed ("s04-s06 cut too fast, drop s05"); adjectives ("more cinematic") don't.
- Keep a list of the director's standing preferences (for HOME: no flashes, no text on in-world screens, heavy
  objects stay still, music only) and check every render against it.
