"""Film finish in one ffmpeg pass: per-shot colour matching, a film-wide look, grain, vignette, music fade.

Generated stills rarely match each other: some run warm and saturated, some flat. Fix each shot over its time
range first, then put one look over everything so it reads as one film.

usage:
  python finish.py raw.mp4 final.mp4
  python finish.py raw.mp4 final.mp4 --shot 4.32,5.76,sat=0.78,rm=-0.04,bm=0.04 --shot 61.44,76.8,sat=0.94 \
      --grain-shot 2.40,4.32,5 --fade-out 117.12 --music-gain -3
  python finish.py raw.mp4 final.mp4 --print        # only print the ffmpeg command

--shot start,end,key=value,...   keys: sat, contrast, bright, gamma (ffmpeg eq) and rs gs bs rm gm bm rh gh bh (colorbalance)
--look  cool shadows / warm highlights by default; --no-look to skip
Audio: music only (the input's audio track), optional gain and a quarter-sine fade to the end.
"""
import argparse, json, shlex, subprocess, sys

try:
    sys.stdout.reconfigure(encoding='utf-8')     # non-ASCII paths on Windows consoles
except Exception:
    pass

EQ = {'sat': 'saturation', 'contrast': 'contrast', 'bright': 'brightness', 'gamma': 'gamma'}
CB = {'rs', 'gs', 'bs', 'rm', 'gm', 'bm', 'rh', 'gh', 'bh'}


def duration(path):
    out = subprocess.run(['ffprobe', '-v', 'error', '-show_entries', 'format=duration', '-of', 'json', path],
                         capture_output=True, text=True, check=True).stdout
    return float(json.loads(out)['format']['duration'])


def shot_filters(spec):
    parts = spec.split(',')
    a, b = float(parts[0]), float(parts[1])
    en = f":enable='between(t,{a},{b})'"
    eq = [f'{EQ[k]}={v}' for k, v in (p.split('=') for p in parts[2:]) if k in EQ]
    cb = [f'{k}={v}' for k, v in (p.split('=') for p in parts[2:]) if k in CB]
    out = []
    if eq:
        out.append('eq=' + ':'.join(eq) + en)
    if cb:
        out.append('colorbalance=' + ':'.join(cb) + en)
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('input'); ap.add_argument('output')
    ap.add_argument('--shot', action='append', default=[], help='start,end,key=value,... (repeatable)')
    ap.add_argument('--grain-shot', action='append', default=[], help='start,end,strength: extra grain (e.g. CG inserts)')
    ap.add_argument('--no-look', action='store_true')
    ap.add_argument('--look', default='rs=-0.025:gs=-0.005:bs=0.04:rh=0.035:gh=0.01:bh=-0.03', help='colorbalance for the film look')
    ap.add_argument('--contrast', type=float, default=1.04); ap.add_argument('--sat', type=float, default=0.97)
    ap.add_argument('--grain', type=float, default=3, help='film-wide grain strength (ffmpeg noise alls)')
    ap.add_argument('--vignette', default='PI/5.8', help="vignette angle, or 'none'")
    ap.add_argument('--fade-out', type=float, help='music fade start (s); fades to the end')
    ap.add_argument('--music-gain', type=float, default=0.0, help='dB')
    ap.add_argument('--crf', type=int, default=19)
    ap.add_argument('--print', action='store_true', help='print the command instead of running it')
    a = ap.parse_args()

    v = ['format=gbrp']                                  # do the colour work in RGB (yuv + lutrgb gave a magenta cast)
    for s in a.shot:
        v += shot_filters(s)
    for g in a.grain_shot:
        s0, s1, st = g.split(',')
        v.append(f"noise=alls={st}:allf=t:enable='between(t,{s0},{s1})'")
    if not a.no_look:
        v += [f'colorbalance={a.look}', f'eq=contrast={a.contrast}:saturation={a.sat}']
    if a.grain > 0:
        v.append(f'noise=alls={a.grain}:allf=t')
    if a.vignette != 'none':
        v.append(f'vignette=angle={a.vignette}')
    v += ['scale=out_color_matrix=bt709:out_range=tv', 'format=yuv420p']

    af = []
    if a.fade_out is not None:
        af.append(f'afade=t=out:st={a.fade_out}:d={max(0.1, duration(a.input) - a.fade_out):.3f}:curve=qsin')
    if a.music_gain:
        af.append(f'volume={a.music_gain}dB')
    fc = '[0:v]' + ','.join(v) + '[v]' + (';[0:a]' + ','.join(af) + '[a]' if af else '')
    cmd = ['ffmpeg', '-v', 'error', '-y', '-i', a.input, '-filter_complex', fc, '-map', '[v]', '-map', '[a]' if af else '0:a?',
           '-c:v', 'libx264', '-crf', str(a.crf), '-preset', 'slow', '-maxrate', '16M', '-bufsize', '32M',
           '-color_primaries', 'bt709', '-color_trc', 'bt709', '-colorspace', 'bt709',
           '-c:a', 'aac', '-b:a', '256k', '-movflags', '+faststart', a.output]
    if a.print:
        print(' '.join(shlex.quote(c) for c in cmd)); return
    subprocess.run(cmd, check=True)
    print('wrote', a.output)


if __name__ == '__main__':
    main()
