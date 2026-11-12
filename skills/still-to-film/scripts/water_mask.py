"""Water mask for depthshot.js (flowing ripples + glints only where there is water).

Method (what worked on HOME's river shot, after the first try rippled the road, the banks and the rocks):
  1. seed points you pick on the water (normalised x,y); the mask grows from them through pixels whose
     Lab colour is close to the seeds' colour, and must stay connected to a seed
  2. add specular glitter (small bright points) that sit inside the grown water region
  3. drop rocks / banks: dark, textured pixels, and anything outside an optional polygon
  4. erode a few pixels (keeps ripples off the shoreline), then feather

usage:
  python water_mask.py plate_hd.jpg --seeds 0.55,0.80 0.62,0.66 --out river_water.png --size 1080x1620
  python water_mask.py plate_hd.jpg --seeds 0.5,0.9 --poly 0.2,1 0.45,0.5 0.7,0.5 0.95,1 --tol 16 --erode 9 --out water.png
Check the result over the plate (--preview preview.jpg) before rendering. Water that changes brightness along its
length (sky reflection near the horizon, shadow near the camera) needs seeds along that gradient, or a higher --tol.
"""
import argparse
import numpy as np, cv2
from scipy import ndimage as ndi


def pair(s):
    x, y = s.split(',')
    return float(x), float(y)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('plate')
    ap.add_argument('--seeds', type=pair, nargs='+', required=True, help='normalised x,y points on the water')
    ap.add_argument('--out', required=True)
    ap.add_argument('--size', help='output WxH (default: plate size; use the depth-map size)')
    ap.add_argument('--tol', type=float, default=14, help='Lab distance from the seed colour (default 14)')
    ap.add_argument('--poly', type=pair, nargs='*', help='optional polygon (normalised x,y) the water must stay inside')
    ap.add_argument('--erode', type=int, default=9, help='pixels to pull back from the shore (at output size)')
    ap.add_argument('--feather', type=float, default=2.0)
    ap.add_argument('--preview', help='write the plate with the mask tinted, to check it')
    a = ap.parse_args()

    bgr = cv2.imread(a.plate, cv2.IMREAD_COLOR)
    if a.size:
        w, h = map(int, a.size.lower().split('x')); bgr = cv2.resize(bgr, (w, h), interpolation=cv2.INTER_AREA)
    H, W = bgr.shape[:2]
    lab = cv2.cvtColor(cv2.GaussianBlur(bgr, (0, 0), 1.5), cv2.COLOR_BGR2LAB).astype(np.float32)
    seeds = [(min(W - 1, int(x * W)), min(H - 1, int(y * H))) for x, y in a.seeds]
    ref = np.mean([lab[y, x] for x, y in seeds], axis=0)
    close = np.linalg.norm(lab - ref, axis=2) < a.tol

    grey = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY).astype(np.float32)
    glitter = (grey > np.percentile(grey, 97)) & (grey - cv2.GaussianBlur(grey, (0, 0), 6) > 25)
    cand = close | glitter
    lab_id, _ = ndi.label(ndi.binary_closing(cand, iterations=2))
    keep = {lab_id[y, x] for x, y in seeds} - {0}
    m = np.isin(lab_id, list(keep))

    texture = cv2.GaussianBlur(np.abs(cv2.Laplacian(grey, cv2.CV_32F)), (0, 0), 3)
    rocks = (grey < np.percentile(grey[m], 15) if m.any() else grey < 0) & (texture > np.percentile(texture, 80))
    m &= ~rocks
    if a.poly:
        poly = np.zeros((H, W), np.uint8)
        cv2.fillPoly(poly, [np.array([(int(x * W), int(y * H)) for x, y in a.poly], np.int32)], 1)
        m &= poly.astype(bool)
    m = ndi.binary_fill_holes(ndi.binary_opening(m, iterations=1))
    if a.erode:
        m = ndi.binary_erosion(m, iterations=a.erode)
    out = cv2.GaussianBlur(m.astype(np.float32), (0, 0), a.feather) if a.feather else m.astype(np.float32)
    cv2.imwrite(a.out, (np.clip(out, 0, 1) * 255).astype(np.uint8))
    if a.preview:
        tint = bgr.copy(); tint[m] = (0.5 * tint[m] + 0.5 * np.array([255, 120, 0])).astype(np.uint8)
        cv2.imwrite(a.preview, tint)
    print(f'water mask {W}x{H}: {m.mean() * 100:.1f}% of frame -> {a.out}')


if __name__ == '__main__':
    main()
