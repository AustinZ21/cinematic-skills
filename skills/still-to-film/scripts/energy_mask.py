"""Energy mask for depthshot.js: thin, roughly vertical light lines (cables, tethers, beams) that pulses run along.

Method (what worked on HOME's station shots, after the first try had gaps and lit up the station itself):
  1. thin-line filter: brightness minus a horizontal opening keeps only lines a few pixels wide
  2. vertical closing (long) joins the broken segments, so no cable is missing its pulse halfway up
  3. keep only tall, narrow components
  4. depth filter: keep lines that are far away (behind the subject), so the foreground structure never glows
  5. optional x-range: restrict to part of the frame

usage:
  python energy_mask.py plate_hd.jpg --depth plate_depth.png --out plate_energy.png --size 1080x1620
  python energy_mask.py plate_hd.jpg --depth plate_depth.png --max-depth 0.25 --xmin 0.3 --close 220 --out e.png
Tune --max-depth first (0.25 kept only the far cables on one shot, 0.80 on another), then --close.
In the renderer the glow is capped; keep the mask thin rather than turning the glow down.
"""
import argparse
import numpy as np, cv2
from scipy import ndimage as ndi


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('plate')
    ap.add_argument('--depth', help='depth map (near = bright); enables the depth filter')
    ap.add_argument('--out', required=True)
    ap.add_argument('--size', help='output WxH (default: plate size; use the depth-map size)')
    ap.add_argument('--width', type=int, default=9, help='max line width in px for the thin-line filter')
    ap.add_argument('--thresh', type=float, default=10, help='thin-line response threshold (0-255)')
    ap.add_argument('--close', type=int, default=220, help='vertical closing length in px (joins gaps)')
    ap.add_argument('--min-height', type=float, default=0.06, help='min component height, fraction of frame')
    ap.add_argument('--max-depth', type=float, default=0.5, help='keep lines with depth below this (0 far, 1 near)')
    ap.add_argument('--xmin', type=float, default=0.0)
    ap.add_argument('--xmax', type=float, default=1.0)
    ap.add_argument('--preview', help='write the plate with the mask tinted, to check it')
    a = ap.parse_args()

    bgr = cv2.imread(a.plate, cv2.IMREAD_COLOR)
    if a.size:
        w, h = map(int, a.size.lower().split('x')); bgr = cv2.resize(bgr, (w, h), interpolation=cv2.INTER_AREA)
    H, W = bgr.shape[:2]
    g = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY)
    tophat = cv2.morphologyEx(g, cv2.MORPH_TOPHAT, cv2.getStructuringElement(cv2.MORPH_RECT, (a.width, 1)))
    m = tophat > a.thresh
    m = cv2.morphologyEx(m.astype(np.uint8), cv2.MORPH_OPEN, cv2.getStructuringElement(cv2.MORPH_RECT, (1, 9))).astype(bool)
    m = cv2.morphologyEx(m.astype(np.uint8), cv2.MORPH_CLOSE, cv2.getStructuringElement(cv2.MORPH_RECT, (1, max(3, a.close)))).astype(bool)

    lab_id, n = ndi.label(m)
    objs = ndi.find_objects(lab_id)
    keep = np.zeros(n + 1, bool)
    for i, sl in enumerate(objs, 1):
        hh, ww = sl[0].stop - sl[0].start, sl[1].stop - sl[1].start
        keep[i] = hh >= a.min_height * H and hh >= 4 * ww
    m = keep[lab_id]

    if a.depth:
        d = cv2.resize(cv2.imread(a.depth, cv2.IMREAD_GRAYSCALE), (W, H), interpolation=cv2.INTER_AREA).astype(np.float32) / 255
        m &= d < a.max_depth
    xs = np.arange(W) / W
    m &= ((xs >= a.xmin) & (xs <= a.xmax))[None, :]
    out = cv2.dilate(m.astype(np.uint8) * 255, np.ones((1, 2), np.uint8))
    cv2.imwrite(a.out, out)
    if a.preview:
        tint = bgr.copy(); tint[m] = (0, 0, 255)
        cv2.imwrite(a.preview, tint)
    print(f'energy mask {W}x{H}: {int(keep.sum())} lines, {m.mean() * 100:.2f}% of frame -> {a.out}')


if __name__ == '__main__':
    main()
