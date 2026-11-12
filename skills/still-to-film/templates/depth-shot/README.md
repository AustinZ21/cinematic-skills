# depth-shot: one depth-parallax shot in HyperFrames

A minimal, working composition: a still plus its depth map rendered through a virtual camera, with flowing water,
energy pulses on thin lines, and a sprite flying through the same camera. 6 seconds, 1080x1080, 30 fps.

```bash
npx --yes hyperframes@0.9.34 lint                 # 0 errors expected (1 structural warning about the nested canvas is fine)
npx --yes hyperframes@0.9.34 snapshot --at 0.5,3,5.8
npx --yes hyperframes@0.9.34 render               # writes an mp4 under renders/
```

## Files

| File | What it is |
|---|---|
| `index.html` | the composition: one timed clip with a canvas, hidden `<img>` textures, one paused GSAP timeline |
| `assets/depthshot.js` | copy of `../../assets/depthshot.js` (the renderer). Keep them in sync |
| `assets/demo_hd.jpg` | procedural colour plate (2160x2160) |
| `assets/demo_depth.png` | its depth map, near = bright (1080x1080) |
| `assets/demo_water.png`, `demo_energy.png` | masks for flowing water and the energy pulses |
| `assets/craft.png` | a sprite on transparency |

All demo images are drawn by `../../scripts/make_demo_plate.py`; regenerate with
`python ../../scripts/make_demo_plate.py --out assets`.

## Use your own still

```bash
python ../../scripts/prep_plate.py my_still.png --out assets --name shot1 --frame 1080x1080
python ../../scripts/water_mask.py assets/shot1_hd.jpg --seeds 0.5,0.85 --size 1080x1080 --out assets/shot1_water.png --preview check.jpg
```

Point the `<img>` tags at `shot1_hd.jpg` / `shot1_depth.png`, then write the camera as a function of `u` (0 to 1 over the
shot). Parameters and safe ranges: `../../references/depth-renderer.md`.

## The contract this follows

- one timed element per shot: `class="clip"` with `data-start` / `data-duration`
- textures decode **before** the timeline is built; then `window.__timelines["main"] = tl`
- every frame is a pure function of timeline time (no clocks, no random), so renders are identical
