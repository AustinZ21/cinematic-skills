"""Deterministic deep-space plates for title cards and space backgrounds (crisp: rendered at 2x, downsampled).

  sky_far.jpg  : dense fine stars, denser along a faint diagonal galactic band, near-black ground
  sky_near.png : sparse brighter stars with soft halos on transparency (a parallax layer to drift over sky_far)

usage:
  python make_starfield.py --out assets --frame 1080x1620              # plates 1.2x the frame, room to drift
  python make_starfield.py --out assets --frame 1920x1080 --seed 7 --margin 1.3
"""
import argparse, os
import numpy as np
from PIL import Image
from scipy.ndimage import gaussian_filter


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--out', default='assets')
    ap.add_argument('--frame', default='1080x1620', help='composition size WxH')
    ap.add_argument('--margin', type=float, default=1.2, help='plate size relative to the frame (for drift/zoom)')
    ap.add_argument('--seed', type=int, default=20261111)
    ap.add_argument('--density', type=float, default=1.0, help='star count multiplier')
    a = ap.parse_args()

    fw, fh = map(int, a.frame.lower().split('x'))
    S = 2
    W, H = int(fw * a.margin) * S, int(fh * a.margin) * S
    rng = np.random.default_rng(a.seed)
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    u = (xx / W - 0.5) * 0.8 + (yy / H - 0.5) * 0.55
    band = np.exp(-((u + 0.03 * np.sin(yy / H * 7.0)) / 0.11) ** 2).astype(np.float32)
    k = (W * H) / (2592 * 3888)                          # scale counts with area (HOME plate = 1296x1944 at 2x)

    def place(n, density=None):
        if density is None:
            return rng.uniform(0, W, n), rng.uniform(0, H, n)
        p = density.ravel() / density.sum()
        idx = rng.choice(p.size, n, p=p)
        return (idx % W) + rng.random(n), (idx // W) + rng.random(n)

    def splat(acc, xs, ys, b, col):
        np.add.at(acc, (ys.astype(int).clip(0, H - 1), xs.astype(int).clip(0, W - 1)), col * b[:, None])

    def colours(n):
        t = rng.random(n)[:, None]
        return np.where(t < 0.22, [1.0, 0.86, 0.68], np.where(t > 0.82, [0.78, 0.87, 1.0], [1.0, 0.98, 0.94])).astype(np.float32)

    far = np.zeros((H, W, 3), np.float32)
    n_bg, n_band = int(14000 * k * a.density), int(22000 * k * a.density)
    xs, ys = place(n_bg); splat(far, xs, ys, (0.02 * (0.5 / 0.02) ** (rng.random(n_bg) ** 4.0)).astype(np.float32), colours(n_bg))
    dens = band ** 1.5 + 0.02
    xs, ys = place(n_band, dens)
    splat(far, xs, ys, (0.015 * (0.25 / 0.015) ** (rng.random(n_band) ** 4.0)).astype(np.float32), colours(n_band))
    far = gaussian_filter(far, (0.55 * S, 0.55 * S, 0)) * (2 * np.pi * (0.55 * S) ** 2)
    far += gaussian_filter(band, 40 * S)[..., None] * np.array([0.020, 0.017, 0.014], np.float32) + np.array([0.0015, 0.0018, 0.0028], np.float32)

    near = np.zeros((H, W, 3), np.float32)
    n_near = max(8, int(55 * k * a.density))
    xs, ys = place(n_near); splat(near, xs, ys, (0.4 * (3.0 / 0.4) ** (rng.random(n_near) ** 3.0)).astype(np.float32), colours(n_near))
    near = gaussian_filter(near, (0.7 * S, 0.7 * S, 0)) * (2 * np.pi * (0.7 * S) ** 2) \
        + gaussian_filter(near, (3.5 * S, 3.5 * S, 0)) * (2 * np.pi * (3.5 * S) ** 2) * 0.05

    tone = lambda x: 1 - np.exp(-x * 1.8)
    down = lambda x: x.reshape(H // S, S, W // S, S, -1).mean((1, 3))
    os.makedirs(a.out, exist_ok=True)
    Image.fromarray((np.clip(down(tone(far)), 0, 1) ** (1 / 2.2) * 255 + 0.5).astype(np.uint8)).save(os.path.join(a.out, 'sky_far.jpg'), quality=96, subsampling=0)
    nt = down(tone(near)); al = np.clip(nt.max(-1) * 1.3, 0, 1)
    rgba = np.dstack([np.clip(nt / np.maximum(al[..., None], 1e-4), 0, 1) ** (1 / 2.2), al ** (1 / 2.2)])
    Image.fromarray((rgba * 255 + 0.5).astype(np.uint8), 'RGBA').save(os.path.join(a.out, 'sky_near.png'))
    print(f'sky plates {W // S}x{H // S} -> {a.out}')


if __name__ == '__main__':
    main()
