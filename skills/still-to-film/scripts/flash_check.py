"""QA: find white flashes and sudden brightness spikes in a rendered video (every frame, not samples).

A flash nobody asked for is the most common "it looks cheap" note. This decodes the whole video small and grey,
then flags frames that are (a) near white, or (b) much brighter than the frames around them.

usage:
  python flash_check.py film.mp4
  python flash_check.py film.mp4 --white 200 --jump 40 --csv luma.csv
Exit code 1 if anything is flagged (handy in a render script).
"""
import argparse, json, subprocess, sys
import numpy as np


def probe(path):
    out = subprocess.run(['ffprobe', '-v', 'error', '-select_streams', 'v:0', '-show_entries', 'stream=r_frame_rate',
                          '-of', 'json', path], capture_output=True, text=True, check=True).stdout
    n, d = json.loads(out)['streams'][0]['r_frame_rate'].split('/')
    return float(n) / float(d)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('video')
    ap.add_argument('--white', type=float, default=200, help='mean luma (0-255) that counts as a white frame')
    ap.add_argument('--jump', type=float, default=40, help='luma rise above the local median that counts as a flash')
    ap.add_argument('--window', type=int, default=9, help='frames in the local median window')
    ap.add_argument('--csv', help='write per-frame mean luma')
    a = ap.parse_args()

    fps = probe(a.video)
    w, h = 64, 64
    raw = subprocess.run(['ffmpeg', '-v', 'error', '-i', a.video, '-vf', f'scale={w}:{h}', '-f', 'rawvideo', '-pix_fmt', 'gray', '-'],
                         capture_output=True, check=True).stdout
    fr = np.frombuffer(raw, np.uint8).reshape(-1, h, w).astype(np.float32)
    luma = fr.mean((1, 2))
    peak = np.percentile(fr.reshape(len(fr), -1), 95, axis=1)
    pad = a.window // 2
    padded = np.pad(luma, pad, mode='edge')
    med = np.array([np.median(padded[i:i + a.window]) for i in range(len(luma))])
    flag = (luma > a.white) | (luma - med > a.jump) | ((peak > 250) & (luma - med > a.jump * 0.6))
    if a.csv:
        np.savetxt(a.csv, np.c_[np.arange(len(luma)) / fps, luma, med], delimiter=',', header='t,luma,median', comments='', fmt='%.3f')
    print(f'{len(luma)} frames @ {fps:.2f} fps, mean luma {luma.mean():.1f}, max {luma.max():.1f}')
    if not flag.any():
        print('no flashes found')
        return 0
    idx = np.nonzero(flag)[0]
    runs = np.split(idx, np.nonzero(np.diff(idx) > 1)[0] + 1)
    for r in runs:
        print(f'FLASH {r[0] / fps:8.3f}s - {r[-1] / fps:8.3f}s  frames {r[0]}-{r[-1]}  luma {luma[r].max():.0f} (local {med[r].min():.0f})')
    return 1


if __name__ == '__main__':
    sys.exit(main())
