# The Blender route: full CG, headless

Use this when the shot can't come from a still or from a browser renderer: the subject must be seen from many sides,
light has to bounce for real (glass, metal, volumes, soft shadows), or things must fall, break, pile up or flow.
Everything else in this skill still applies: plan with `shot-director`, review with stills, finish with `finish.py`.

The working method below is adapted from Mr Tactical's guide (see `NOTICE.md`) and from what HOME and later films
taught us. `examples/blender/mothership.py` is a worked script; `pitfalls.md` lists the Blender 5.x API traps.

## When to choose it

| Need | Depth shot (still) | WebGL / canvas | Blender (Cycles) |
|---|---|---|---|
| Camera stays inside one picture | yes | | |
| Abstract, graphic, type-led, fast to iterate (seconds per frame) | | yes | |
| Subject seen from several sides, hero product or object | | sometimes | yes |
| Real light transport: glass, metal, fog, volumes, soft shadows | | faked | yes |
| Physics: fall, bounce, shatter, pile, cloth, fluid | | | yes |
| Hours of render time are acceptable | | | required |

Mixing is normal: Blender for the hero object or a transparent sprite, the browser for type, grade and assembly.

## Rules

1. **Headless only.** `blender -b --factory-startup -P script.py -- <args>`, at low process priority so the machine
   stays usable. Never open the UI. The whole scene is code: geometry, materials, lights, camera, animation, physics.
   Seed every random generator.
2. **Check the render device, don't assume it.** Background Blender uses the CPU until the script enables the GPU.
   Enable it, enable GPU denoising, and print the device actually used at the start of every run.
3. **One folder per film.** Scripts, `tests/` stills, `renders/<shot>/` frames and the final all live in it.
4. **Assets.** Build in code first. CC0 textures and models (e.g. Poly Haven) are fine when the brief allows; ask
   before downloading anything, keep the licence line, and credit where the licence asks for it.
5. **Subject before everything.** A detailed, specific subject ("an oak with thousands of separate leaves"), never a
   primitive standing in for one. Default stage when the brief gives none: a plain backdrop with soft even light, so
   the subject carries the frame.
6. **Physics is real or absent.** Anything that falls, bounces or breaks is simulated; nothing passes through the
   floor or another object. Check the contact frames in stills.
7. **Camera close.** One sealed move (push or orbit), subject large in frame. No wide shots where it is a dot.

## The loop (do not skip to the final)

1. **Target frame.** Rough scene, then one still of the best moment taken as far as it will go. Everything else is
   aimed at that picture. (Same idea as the look test in `pipeline.md`.)
2. **Key-moment stills.** Start, the big moment, the end, at reduced size and samples.
3. **Look honestly.** Flat materials, harsh light, floating or intersecting objects, camera too far, subject too small.
4. **Fix, re-render the same frames, compare** with the target and with the previous round. At least three rounds.
5. **Motion preview.** The whole shot at low resolution and low samples to judge movement and timing.
6. **Final.** Cycles, denoiser on, frames to disk (so a crash loses one frame, not the film), then ffmpeg:
   H.264, `yuv420p`, AAC. Make a 12-frame contact sheet (`scripts/contact_sheet.py`).

Show nothing until it matches the plan and no fault is visible in the stills. Say what could not be checked.

## Delegating the build

On harnesses with sub-agents, the lead writes the plan and reviews; one sub-agent builds the whole film. The
sub-agent sees only its brief, so paste in: the plan, the rules above, the loop, the delivery spec and the folder.
The lead reviews the test stills before the final render and sends back concrete notes ("leaves read as flat
paper", "cube passes through the floor at 8 s", "camera too far at the end").

A long render can take hours: say so, and ask the person to keep the machine awake.

## Planning template

| Part | Write down |
|---|---|
| Subject | what it is, in enough detail to model |
| Look | backdrop, light, palette |
| Story | a timeline in seconds: `0-3 s still · 3-12 s shaken, leaves fall and pile up` |
| Physics | what is simulated, what must never intersect |
| Camera | one move, start and end frame (from `shot-director`) |
| Format | size, fps, length, sound or silent, watermark |

Get a yes on the plan before building.
