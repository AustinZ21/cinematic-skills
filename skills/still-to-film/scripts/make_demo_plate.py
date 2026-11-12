"""Procedural demo plate for templates/depth-shot: a canyon at dusk with a river, its exact depth map, a water mask,
an energy (tether) mask and a small craft sprite. No external images: everything is drawn here, deterministically.

usage: python make_demo_plate.py --out ../templates/depth-shot/assets
writes demo_hd.jpg (2160x2160), demo_depth.png, demo_water.png, demo_energy.png (1080x1080), craft.png
"""
import argparse, os
import numpy as np
from PIL import Image, ImageDraw, ImageFilter
from scipy.ndimage import gaussian_filter


def fbm(shape, rng, octaves=5, base=4):
    h, w = shape
    out = np.zeros(shape, np.float32)
    amp = 1.0
    for o in range(octaves):
        n = base * 2 ** o
        g = rng.random((n + 1, n + 1)).astype(np.float32)
        out += amp * np.array(Image.fromarray(g).resize((w, h), Image.BICUBIC))
        amp *= 0.5
    return (out - out.min()) / (out.max() - out.min())


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--out', default='assets')
    ap.add_argument('--size', type=int, default=2160, help='plate size (square); depth/masks are half')
    ap.add_argument('--seed', type=int, default=11)
    a = ap.parse_args()
    S = a.size; rng = np.random.default_rng(a.seed)
    yy, xx = np.mgrid[0:S, 0:S].astype(np.float32) / S

    # sky: dusk gradient + sun glow
    col = np.zeros((S, S, 3), np.float32)
    top, hor = np.array([0.05, 0.06, 0.10]), np.array([0.85, 0.55, 0.30])
    t = np.clip(yy / 0.55, 0, 1)[..., None]
    col[:] = top * (1 - t) + hor * t
    sun = np.exp(-(((xx - 0.62) ** 2 + (yy - 0.47) ** 2) / 0.004))[..., None]
    col += sun * np.array([1.0, 0.8, 0.5]) + 0.25 * np.exp(-(((xx - 0.62) ** 2 + (yy - 0.47) ** 2) / 0.05))[..., None] * np.array([1.0, 0.6, 0.3])
    depth = np.zeros((S, S), np.float32)

    # ridges back to front: each is a silhouette line; nearer ridges are darker, more textured, higher depth
    tex = fbm((S, S), rng, 6, 6)
    ridges = [(0.50, 0.04, 0.15, [0.30, 0.22, 0.24]), (0.56, 0.06, 0.35, [0.20, 0.15, 0.16]),
              (0.64, 0.09, 0.60, [0.13, 0.10, 0.10]), (0.75, 0.12, 0.85, [0.08, 0.06, 0.06])]
    for k, (base, amp, d, c) in enumerate(ridges):
        line = base - amp * fbm((1, S), rng, 5, 3)[0] - 0.02 * k * np.sin(xx[0] * (3 + k))
        # carve a valley in the middle for the river
        line = line + 0.10 * (1 - k / 4) * np.exp(-((xx[0] - 0.5) / (0.12 + 0.05 * k)) ** 2)
        m = yy > line[None, :]
        shade = np.array(c) * (0.7 + 0.6 * tex[..., None]) * (1 + 0.6 * sun * (1 - k / 4))
        lit = 0.15 * np.clip(1 - (yy - line[None, :]) / 0.05, 0, 1)[..., None] * np.array([1.0, 0.7, 0.4]) * (1 - k / 5)
        col = np.where(m[..., None], shade + lit, col)
        depth = np.where(m, d + 0.12 * (yy - base), depth)

    # river: a band winding down the middle of the valley floor
    cx = 0.5 + 0.05 * np.sin(yy * 9) * (yy - 0.6)
    width = np.clip((yy - 0.62) * 0.55, 0, None)
    river = (np.abs(xx - cx) < width) & (yy > 0.63)
    sky_ref = np.array([0.80, 0.52, 0.32]) * (0.6 + 0.4 * gaussian_filter(rng.random((S, S)).astype(np.float32), 3)[..., None])
    col = np.where(river[..., None], sky_ref * (0.5 + 0.5 * np.clip((yy[..., None] - 0.6) * 2, 0, 1)), col)
    depth = np.where(river, 0.55 + 0.45 * (yy - 0.63) / 0.37, depth)

    # foreground rock pillar on the left (strong parallax subject) and tethers in the far sky (energy mask demo)
    pil = (xx < 0.10 + 0.04 * np.sin(yy * 20) * 0.3) & (yy > 0.22)
    col = np.where(pil[..., None], np.array([0.05, 0.04, 0.04]) * (0.6 + 0.8 * tex[..., None]), col)
    depth = np.where(pil, 0.97, depth)
    energy = np.zeros((S, S), bool)
    for x0 in (0.70, 0.74, 0.79, 0.85, 0.88):
        ln = (np.abs(xx - x0) < 0.0012) & (yy < 0.52) & (yy > 0.05)
        col = np.where(ln[..., None], col * 0.4 + np.array([0.75, 0.62, 0.45]) * 0.6, col)
        energy |= ln

    # a little haze and grain
    col = col + 0.04 * (1 - depth[..., None]) * np.array([1.0, 0.7, 0.5])
    col += rng.normal(0, 0.012, col.shape)
    os.makedirs(a.out, exist_ok=True)
    Image.fromarray((np.clip(col, 0, 1) ** (1 / 1.15) * 255).astype(np.uint8)).save(os.path.join(a.out, 'demo_hd.jpg'), quality=92)
    h = S // 2
    from scipy.ndimage import grey_dilation
    soft = gaussian_filter(grey_dilation(depth, size=(9, 9)), 7)    # same treatment as prep_plate.py: grow near edges, soften steps
    dimg = Image.fromarray((np.clip(soft, 0, 1) * 255).astype(np.uint8)).resize((h, h), Image.LANCZOS)
    dimg.save(os.path.join(a.out, 'demo_depth.png'))
    wm = gaussian_filter(river.astype(np.float32), 2)
    Image.fromarray((wm * 255).astype(np.uint8)).resize((h, h), Image.LANCZOS).save(os.path.join(a.out, 'demo_water.png'))
    Image.fromarray((energy * 255).astype(np.uint8)).resize((h, h), Image.BILINEAR).save(os.path.join(a.out, 'demo_energy.png'))

    # craft sprite: a small dark wedge with a hot engine glow, on transparency
    sp = Image.new('RGBA', (256, 128), (0, 0, 0, 0)); d = ImageDraw.Draw(sp)
    glow = Image.new('RGBA', (256, 128), (0, 0, 0, 0)); ImageDraw.Draw(glow).ellipse((6, 52, 70, 76), fill=(255, 190, 120, 230))
    sp.alpha_composite(glow.filter(ImageFilter.GaussianBlur(9)))
    d.polygon([(40, 58), (230, 64), (40, 72)], fill=(22, 20, 24, 255)); d.polygon([(70, 64), (150, 40), (170, 64)], fill=(30, 28, 32, 255))
    d.line([(60, 64), (220, 64)], fill=(255, 210, 160, 200), width=1)
    sp.save(os.path.join(a.out, 'craft.png'))
    print('demo assets ->', a.out)


if __name__ == '__main__':
    main()
