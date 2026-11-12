# depthshot.js: the depth-parallax renderer

A WebGL2 fragment shader that, for each output pixel, walks backwards through the camera to find which plate pixel
lands there, using the depth map (14 fixed-point iterations). Near pixels move more than far pixels, so a moving
camera produces real parallax from a single still. Motion blur averages `sub` sub-frames across `shutter` seconds.

## Camera parameters, returned by `cam(u)` with u = 0..1 over the shot

| Param | What it does | Camera move it gives | Typical range |
|---|---|---|---|
| `vx`, `vy` | view centre in plate uv (0.5, 0.5 = centre) | small pan / tilt feel, reframing | ±0.1 from centre over a shot |
| `lz` | ln(zoom). 0 = plate fills frame, 0.69 = 2x | zoom on its own (flat, even) | 0 to 1.6 (HOME's longest push: 0 to 1.61) |
| `pz` | extra magnification per depth unit around `dref` | turns a zoom into a dolly: near grows faster than far | 0 to 0.5; 0 for flat subjects |
| `px`, `py` | parallax offset per depth unit | truck (sideways) / pedestal (up-down) | ±0.05; above that, near edges tear |
| `roll` | rotation in degrees around the view centre | barrel roll, or a Dutch angle if it holds | HOME's crane shot: 0 to -30 |
| `dref` (option) | depth that stays put | put it on the subject | 0.3 to 0.6 |

How the moves map:
- **Zoom**: `lz` only. Use for crash zooms or a deliberately optical look.
- **Push in (dolly)**: `lz` and `pz` together. `pz` is what sells "the camera moved".
- **Pull out**: the same, decreasing. End wide enough that the plate edges never show (`lz` stays > 0 if the plate is
  exactly the frame size; give yourself margin by storing the plate larger).
- **Truck / pedestal**: `px` / `py`, small. Pair with a little `lz` so the frame edge never reveals.
- **Roll**: `roll`. Combine with a push for a spiralling move (HOME's crane shot).
- **Dolly zoom**: keep the subject's size by holding `lz` while raising `pz`, with `dref` on the subject. The
  background stretches or crushes around a subject that stays the same size.
- **Pan / tilt beyond about 10% of the frame**: not possible from one still; you run out of picture. Cut instead,
  or extend the plate first (outpainting).
- **Orbit**: not possible beyond a few degrees. Fake a quarter-orbit feel with truck + opposite `vx` drift.

Easing: write it in `cam(u)`. Constant log-zoom rate (`lz` linear in u) feels like a steady dolly. `u*u*(3-2u)` for an
ease in/out. Accelerating dives: `lz = k * u^2.3`. Speed must stay continuous across cuts if the film is one flow.

## Motion blur

`sub: 6` sub-frames and `shutter` of about one frame (1/60 at 60 fps; HOME used 0.0125 s) look natural.
Fast moves need it; without it a push strobes.

## Motion inside the frame

- **Water** (`water`, `flow: [x, y]`, `flowAmt`): noise-offset sampling inside the mask plus moving glints.
  `flowAmt` 0.0025 to 0.004. Narrow ripples look like water; wide ones look like heat haze. Mask carefully
  (`scripts/water_mask.py`), the effect will happily ripple a road.
- **Sway** (`sway`, `swayFn: t => [x, y]`): displaces the masked region by a small vector over time. Foliage, hanging
  loads, cables. Keep it tiny; anything that should be rigid must not be in the mask.
- **Energy** (`energy`): light pulses travelling up a line mask, each column on its own phase, with a soft capped
  glow. The cap keeps the glow from swallowing the subject.
- **Sprites** (`sprites: [{img, at(u, t) -> {x, y, d, size, rot, alpha}}]`): an alpha PNG placed at plate uv `(x, y)`
  and depth `d`, projected through the same camera (`fwd()`), so it gets the same parallax and roll. Use for ships,
  vehicles, cut-out objects, engine plumes (flicker `alpha` with two incommensurate sines).

## Safe ranges and how shots break

- **Tearing**: when a near object separates from the background, the revealed area has no pixels and the shader
  stretches the edge into "melted glass". Limits: keep `px`/`py` small, `pz` modest, and don't push past near
  structures that sit at the frame edge. Dilating the depth map (prep_plate does) moves the stretch into the
  background, where it shows less.
- **Thin planar things** (planet rings, glass, flat signs, water seen from above): depth estimators give them false
  relief, and parallax warps them. Use `pz: 0` (flat) and a very small `px`, or none.
- **Lines crossing a depth edge** (cables, tethers, poles) kink where the depth changes. Keep them within one
  depth layer, or keep the move small.
- **Plate edges**: any combination of `vx`, `px` and roll can expose the border. Check the first and last frame
  and the extremes of any oscillation.

## Wiring it into HyperFrames

See `templates/depth-shot/index.html`: one `<canvas>` inside a timed clip, hidden `<img>` textures, one paused
GSAP timeline, `depthShot({... timeline: tl})` called after every image has decoded, then
`window.__timelines["main"] = tl`.
