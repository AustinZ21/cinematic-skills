"""Contact sheet: N evenly spaced frames (or given times) from a video in one image, labelled with timestamps.
An agent can't watch a film in real time; this is how it (and you) review pacing and continuity at a glance.

usage:
  python contact_sheet.py film.mp4 --n 24 --cols 6 --out sheet.jpg
  python contact_sheet.py film.mp4 --at 2.4 4.3 12.0 30.7 --out shots.jpg
"""
import argparse, json, subprocess
import numpy as np
from PIL import Image, ImageDraw


def info(path):
    out = subprocess.run(['ffprobe', '-v', 'error', '-select_streams', 'v:0', '-show_entries', 'stream=width,height:format=duration',
                          '-of', 'json', path], capture_output=True, text=True, check=True).stdout
    j = json.loads(out)
    return j['streams'][0]['width'], j['streams'][0]['height'], float(j['format']['duration'])


def grab(path, t, w, h):
    raw = subprocess.run(['ffmpeg', '-v', 'error', '-ss', f'{t:.3f}', '-i', path, '-frames:v', '1', '-vf', f'scale={w}:{h}',
                          '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-'], capture_output=True, check=True).stdout
    return Image.fromarray(np.frombuffer(raw, np.uint8).reshape(h, w, 3))


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('video')
    ap.add_argument('--n', type=int, default=24)
    ap.add_argument('--at', type=float, nargs='*', help='explicit timestamps (seconds)')
    ap.add_argument('--cols', type=int, default=6)
    ap.add_argument('--thumb', type=int, default=320, help='thumbnail width')
    ap.add_argument('--out', default='contact_sheet.jpg')
    a = ap.parse_args()

    W, H, dur = info(a.video)
    times = a.at or list(np.linspace(0, dur, a.n + 2)[1:-1])
    tw = a.thumb; th = int(round(tw * H / W / 2) * 2)
    rows = (len(times) + a.cols - 1) // a.cols
    sheet = Image.new('RGB', (a.cols * (tw + 8) + 8, rows * (th + 30) + 8), (12, 12, 14))
    d = ImageDraw.Draw(sheet)
    for i, t in enumerate(times):
        x, y = 8 + (i % a.cols) * (tw + 8), 8 + (i // a.cols) * (th + 30)
        sheet.paste(grab(a.video, t, tw, th), (x, y))
        d.text((x, y + th + 6), f'{t:7.2f}s', fill=(230, 220, 200))
    sheet.save(a.out, quality=90)
    print(f'{len(times)} frames -> {a.out}')


if __name__ == '__main__':
    main()
