# Finishing: one ffmpeg pass

`scripts/finish.py` builds the command from arguments (`--print` shows it). `scripts/finish.sh` is the literal HOME version.

## 1. Match the shots

Stills from different sources disagree: one runs warm and saturated, one is flat and cool. Fix each over its time range
before the film-wide look, with `eq` and `colorbalance` gated by `enable='between(t,start,end)'`.

What HOME needed:

| Shot | Problem | Fix |
|---|---|---|
| hangar (generated) | warm, oversaturated next to the originals | `sat 0.78`, `rm -0.04`, `bm +0.04` |
| hull (generated) | slightly warm | `sat 0.88`, `rm -0.03`, `bm +0.03` |
| river, ring, planet (bright gold) | a touch hot | `sat 0.93 to 0.95` |
| Blender inserts | too clean next to painted stills | extra grain `noise=alls=5` over their range |

Judge on a contact sheet with neighbouring shots side by side, not shot by shot.

## 2. One look over everything

- `colorbalance=rs=-0.025:gs=-0.005:bs=0.04:rh=0.035:gh=0.01:bh=-0.03`: cool shadows, warm highlights
- `eq=contrast=1.04:saturation=0.97`
- `noise=alls=3:allf=t`: fine temporal grain (hides banding, glues CG to paintings)
- `vignette=angle=PI/5.8`: soft
- work in `format=gbrp`, output `bt709` limited range, `yuv420p`

## 3. Sound

- Music: fade on a quarter-sine from the title to the end (`afade=t=out:st=<title>:d=<rest>:curve=qsin`).
- Level: HOME's final sat 3 dB lower than the source track (mean about -20 dB, peak about -6 dB). Check with
  `ffmpeg -i final.mp4 -af volumedetect -f null -`.
- Sound effects are optional. HOME tried procedural whooshes and booms and shipped music only; ask before adding.

## 4. Encode

`libx264 -crf 19 -preset slow -maxrate 16M -bufsize 32M`, AAC 256k, `+faststart`. Also export a small preview
(720p, 30 fps) for sharing and review.
