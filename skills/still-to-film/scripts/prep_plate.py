"""Turn one still into a depth-shot plate: a 4x super-resolved colour plate and a depth map.

  <name>_hd.jpg     Swin2SR x4 (real-world model), resized to --hd (default: 2x the frame)
  <name>_depth.png  Depth Anything V2 Large, 8-bit grey, near = bright, at --frame size,
                    lightly dilated + blurred so near edges don't halo when the parallax opens

usage:
  python prep_plate.py still.png --out assets --frame 1080x1620
  python prep_plate.py still.png --out assets --name hangar --frame 1920x1080 --hd 3840x2160
  python prep_plate.py still.png --out assets --frame 1080x1620 --no-upscale      # depth only

Runs on CUDA if available (fp16), otherwise CPU (slow but works). Models download from Hugging Face on first run:
  caidas/swin2SR-realworld-sr-x4-64-bsrgan-psnr, depth-anything/Depth-Anything-V2-Large-hf
"""
import argparse, os
import numpy as np
import torch
from PIL import Image, ImageOps
from scipy import ndimage as ndi

Image.MAX_IMAGE_PIXELS = None


def wh(s):
    w, h = s.lower().split('x')
    return int(w), int(h)


def cover(im, size):
    """resize + centre-crop to exactly size (like CSS object-fit: cover)"""
    return ImageOps.fit(im, size, Image.LANCZOS, centering=(0.5, 0.5))


def upscale(img, device, tile=192, pad=16):
    from transformers import Swin2SRForImageSuperResolution
    half = device == 'cuda'
    model = Swin2SRForImageSuperResolution.from_pretrained('caidas/swin2SR-realworld-sr-x4-64-bsrgan-psnr').to(device).eval()
    if half:
        model = model.half()
    S = 4
    a = torch.from_numpy(np.asarray(img).astype(np.float32) / 255).permute(2, 0, 1)[None]
    _, _, H, W = a.shape
    out = torch.zeros(1, 3, H * S, W * S)
    with torch.no_grad():
        for y in range(0, H, tile):
            for x in range(0, W, tile):
                y0, x0, y1, x1 = max(0, y - pad), max(0, x - pad), min(H, y + tile + pad), min(W, x + tile + pad)
                t = a[:, :, y0:y1, x0:x1]
                ph, pw = (-t.shape[2]) % 8, (-t.shape[3]) % 8
                t = torch.nn.functional.pad(t, (0, pw, 0, ph), mode='reflect').to(device)
                if half:
                    t = t.half()
                r = model(pixel_values=t).reconstruction.float().cpu().clamp(0, 1)[:, :, :(y1 - y0) * S, :(x1 - x0) * S]
                ty, tx = min(H, y + tile), min(W, x + tile)
                out[:, :, y * S:ty * S, x * S:tx * S] = r[:, :, (y - y0) * S:(ty - y0) * S, (x - x0) * S:(tx - x0) * S]
    return Image.fromarray((out[0].permute(1, 2, 0).numpy() * 255 + 0.5).astype(np.uint8))


def depth_map(img, size, device, dilate=5, blur=1.2):
    from transformers import pipeline
    est = pipeline('depth-estimation', model='depth-anything/Depth-Anything-V2-Large-hf', device=0 if device == 'cuda' else -1)
    d = est(img)['predicted_depth']
    d = d[None, None] if d.ndim == 2 else d[None]
    d = torch.nn.functional.interpolate(d.float(), size=(size[1], size[0]), mode='bicubic', align_corners=False)[0, 0].cpu().numpy()
    lo, hi = np.percentile(d, 0.5), np.percentile(d, 99.5)
    dn = np.clip((d - lo) / max(hi - lo, 1e-6), 0, 1)          # Depth Anything returns relative disparity: near = large
    if dilate > 1:
        dn = ndi.grey_dilation(dn, size=(dilate, dilate))      # grow near objects a little: no halo when parallax opens
    if blur > 0:
        dn = ndi.gaussian_filter(dn, blur)
    return Image.fromarray((dn * 255 + 0.5).astype(np.uint8))


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('image')
    ap.add_argument('--out', default='assets', help='output folder')
    ap.add_argument('--name', help='plate name (default: image file stem)')
    ap.add_argument('--frame', type=wh, required=True, help='composition size, e.g. 1080x1620 (sets crop aspect and depth size)')
    ap.add_argument('--hd', type=wh, help='colour plate size (default: 2x frame)')
    ap.add_argument('--depth-size', type=wh, help='depth map size (default: frame)')
    ap.add_argument('--no-upscale', action='store_true', help='skip super-resolution, just crop/resize the still')
    ap.add_argument('--dilate', type=int, default=5)
    ap.add_argument('--blur', type=float, default=1.2)
    a = ap.parse_args()

    device = 'cuda' if torch.cuda.is_available() else 'cpu'
    name = a.name or os.path.splitext(os.path.basename(a.image))[0]
    hd = a.hd or (a.frame[0] * 2, a.frame[1] * 2)
    dsz = a.depth_size or a.frame
    os.makedirs(a.out, exist_ok=True)

    src = Image.open(a.image).convert('RGB')
    src = cover(src, (round(src.height * a.frame[0] / a.frame[1]), src.height) if src.width / src.height > a.frame[0] / a.frame[1]
                else (src.width, round(src.width * a.frame[1] / a.frame[0])))     # crop to the frame aspect, keep resolution
    plate = src if a.no_upscale else upscale(src, device)
    plate.resize(hd, Image.LANCZOS).save(os.path.join(a.out, f'{name}_hd.jpg'), quality=92)
    depth_map(src.resize(dsz, Image.LANCZOS), dsz, device, a.dilate, a.blur).save(os.path.join(a.out, f'{name}_depth.png'))
    print(f'{name}: {hd[0]}x{hd[1]} plate, {dsz[0]}x{dsz[1]} depth -> {a.out} ({device})')


if __name__ == '__main__':
    main()
