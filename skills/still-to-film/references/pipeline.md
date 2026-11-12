# Pipeline, stage by stage

The order matters: each stage is cheap to change before the next one is built on it. HOME (a 2:03 vertical sci-fi short,
14 shots, 60 fps) went through 11 animatic versions and 5 rough cuts; almost all of the real decisions happened in the
animatic, not in production.

## 0. Story before stills

Three beautiful frames are a world, not a story. Before touching any image, write the beats: where we leave, how we
travel, where we arrive. Each still must exist for one beat. Plan the shots with the `shot-director` skill (six-layer
shot specs, one main move per shot, start/end/holds, time and space).

Decide the delivery: aspect (HOME was 1080x1620, 2:3), fps (30 for review, 60 for final), length, and the music.
The music's tempo becomes the edit grid: at 125 BPM a bar is 1.92 s, so every shot is a whole number of bars.

## 1. Stills

- Collect the source images and generate the missing beats (any image model). Every new still must match the others'
  light direction, palette, lens feel and aspect, or the cut gives it away.
- Credit borrowed images. Don't ship other people's images in a public repo.
- Expect to drop some. HOME cut one of its three original images and replaced the generated mothership stills with a
  procedural Blender model, because a painting of a ship can't fly into frame.

## 2. Plates

For every still that will become a depth shot:

```bash
python scripts/prep_plate.py still.png --out assets --name hangar --frame 1080x1620
```

- `_hd.jpg`: 4x super-resolution (Swin2SR), stored at 2x the frame so pushes stay sharp. For a long push, store 3x.
- `_depth.png`: Depth Anything V2 at frame size, near = bright, slightly dilated and blurred.
- Look at the depth map. Fix obvious errors before animating (paint over it, or flatten areas that should be one plane).

Optional layers:
- **Water**: `scripts/water_mask.py` (seeded colour growth, glitter, polygon, erode). Preview it over the plate.
- **Energy lines**: `scripts/energy_mask.py` (thin vertical lines + depth filter).
- **Sway**: a hand-painted grey mask of things that should move a little (foliage, cloth, cables), driven by `swayFn`.
- **Sprites**: cut moving things out of the plate (ships, vehicles) with an alpha PNG, fill the hole behind them
  (inpaint, or leave it if the sprite never moves far), and fly them through the same camera. If the cut-out is
  large or the fill is ugly, leave the object in the plate; a static object is better than a smeared hole.

## 3. Animatic

Build the whole film rough before polishing any shot: every shot on the beat grid, rough camera moves, title cards,
music. Review it as a film (contact sheets + watching), cut shots ruthlessly, fix pacing. HOME cut a dome, a dock, a port,
an axis dive, a sun window and a slow valley shot here. Each looked fine alone and made the film worse.

Review mode helps: burn a label (shot id + note) and a clock into each shot so notes can be precise ("s14 31-43 s:
push faster, roll left to -30, container stays put"). Turn them off for the final.

## 4. Look test

Take one representative shot all the way to final: plate quality, camera, motion inside the frame, grade. It tells you
whether the look works before you commit the other thirteen shots to it.

## 5. Production

Per shot, in HyperFrames (see `templates/depth-shot/`):
- depth shot with `depthshot.js`: camera function `cam(u)`, motion blur `sub: 6`, shutter about one frame
- motion inside the frame: sprites, plumes, water, sway, energy. A camera moving over a frozen world reads as a slideshow
- CG inserts where a still can't do the job (ships flying in, tunnels, effects): Blender (see `examples/blender/`),
  WebGL or canvas; render them to video and place them as timed `<video muted>` clips
- title cards over a real background (a starfield plate from `scripts/make_starfield.py`), never flat black

Keep every frame a pure function of time: no clocks, no unseeded randomness. Then renders are repeatable and review
notes stay valid.

## 6. Finish

One ffmpeg pass: per-shot colour matching, a film-wide look, grain, vignette, music fade (`scripts/finish.py`,
details in `finishing.md`).

## 7. QA

- `scripts/flash_check.py final.mp4`: every frame scanned for white flashes and luma spikes
- `scripts/contact_sheet.py final.mp4 --n 24`: pacing and continuity at a glance
- audio: mean and peak loudness (`ffmpeg -af volumedetect`)
- an agent can't watch in real time or hear. A human watches the final at full speed with sound before it ships
