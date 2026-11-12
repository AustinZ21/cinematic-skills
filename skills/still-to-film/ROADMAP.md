# still-to-film roadmap

v0.1 is the HOME pipeline with the paths and shot-specific numbers taken out. What works today:
plates (`prep_plate.py`), the renderer (`depthshot.js`) and its template, water and energy masks, starfield plates,
finishing, flash QA and contact sheets. What isn't generalised yet:

## Next

- **Animatic generator.** HOME's film was generated from a Python table of shots (start bar, length, plate, camera,
  label) into one HyperFrames `index.html`, with review labels and a clock that switch off for the final. That
  generator is still HOME-specific; it should become `scripts/build_film.py <shots.yaml>`.
- **Shot spec -> camera.** Translate a `shot-director` six-layer spec ("slow push from wide to medium, stop on her
  eyes, slight roll left") into a `cam(u)` function automatically.
- **Sprite extraction.** HOME cut far ships out of a plate by known positions and darkness, then inpainted the sky.
  Needs a general `cutout.py` (SAM-style segmentation + inpaint + alpha export).
- **Sway mask helper.** Currently hand-painted; could be seeded like the water mask (foliage hue, cables).
- **Rack focus.** Depth-weighted blur in the shader to move focus between depth planes.
- **Plate extension.** Outpaint a plate so pans, tilts and small orbits don't run out of picture.

## Later

- CG tunnel / jump effects used in HOME (canvas) as reusable components.
- A Blender kit instead of one example: hull lathe, lattice booms, plumes, a habitat ring, a transparent-sprite render
  preset.
- Loudness normalisation to a target (EBU R128) in `finish.py`.
- Automatic per-shot colour matching (match each shot's histogram to a reference shot) instead of hand values.
- Tests: render the template in CI and compare frames.

Contributions welcome; keep every frame deterministic and every script argument-driven.
