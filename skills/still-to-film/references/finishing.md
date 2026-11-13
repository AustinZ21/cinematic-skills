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

## 5. Delivery for social (X and similar)

- **The first frame is the thumbnail.** Custom covers are not always offered at upload, so frame 0 must already be
  the cover: never black, title complete, subject in place. If the film opens with text that types or fades in,
  either start with it fully on, or make the opening frame a finished composition without it.
- **Aspect.** 4:5 (1080x1350) is the safest portrait size in a feed; 9:16 can be cropped at the sides in some
  fullscreen players. 16:9 is fine for landscape films. Decide before shooting, not at export.
- **Watermark or signature.** In empty space near the subject, not in a corner (corners get cropped first) and not
  on the subject.
- **Sound.** Licensed recordings only; keep the credit line. The agent can't listen: look at a spectrogram
  (`ffmpeg -i clip.mp3 -lavfi showspectrumpic=s=1200x400 spec.png`) to catch speech or surprises, and find hits
  from the waveform before cutting to them. Aim for about -16 LUFS integrated for phone playback
  (`ffmpeg -i final.mp4 -af loudnorm=print_format=summary -f null -`), and say that a person still has to listen.
- **Size.** Keep a copy under the platform's upload and preview limits; re-encode with a higher CRF rather than
  lowering the resolution.
