#!/usr/bin/env python3
"""Offline clone of TEA-Online's `extend/tools/image/editor` (Image Editor & Indexer).

The web tool is a generic PNG -> indexed-PNG converter: crop, resize, optional
blur, colour quantisation, dithering and a magenta transparency slot.  It never
touches a Forbidden Memories file; its output is what you then feed to the
tools that DO (image/massive/cards, image/builder, image/specsmix, ...).

This is a byte-level port of the `TextureIndexer` component in the site's
chunk-common (median cut + 5 k-means passes, the same resize kernels, the same
Bayer matrix, the same "transparent = palette index 0 = magenta" convention).

    ./index_texture.py in.png out.png --size 102x96 --colors 256
    ./index_texture.py in.png out.png --size 40x32 --colors 64 --dither floyd
    ./index_texture.py in.png out.png --size 64x64 --colors 16 \
        --crop 10,10,200,200 --resize lanczos3 --smooth 2

Defaults match the web UI: 64x64, 16 colours, resize "auto", dither "none".
Size presets offered by the UI (all real game textures):
    8x8   40x32 (mini card art)   102x96 (card art)   320x168   256x256
"""

import argparse
import sys

import numpy as np

try:
    from PIL import Image
except ImportError:  # pragma: no cover
    sys.exit("needs Pillow")

# ------------------------------------------------------------ resize kernels

def _box(t):      return 1.0 if abs(t) <= 0.5 else 0.0
def _triangle(t): t = abs(t); return 1 - t if t < 1 else 0.0
def _catmullrom(t):
    t = abs(t)
    if t < 1: return 1.5 * t ** 3 - 2.5 * t ** 2 + 1
    if t < 2: return -0.5 * t ** 3 + 2.5 * t ** 2 - 4 * t + 2
    return 0.0
def _sinc(t):
    if t == 0: return 1.0
    x = np.pi * t
    return np.sin(x) / x
def _lanczos3(t): t = abs(t); return _sinc(t) * _sinc(t / 3) if t < 3 else 0.0
def _lanczos2(t): t = abs(t); return _sinc(t) * _sinc(t / 2) if t < 2 else 0.0
def _mitchell(t):
    t = abs(t); B = C = 1 / 3
    if t < 1:
        return ((12 - 9 * B - 6 * C) * t ** 3 + (12 * B - 18 + 6 * C) * t ** 2 + (6 - 2 * B)) / 6
    if t < 2:
        return ((-B - 6 * C) * t ** 3 + (6 * B + 30 * C) * t ** 2
                + (-12 * B - 48 * C) * t + (8 * B + 24 * C)) / 6
    return 0.0
def _gaussian(t): s = 0.8; return float(np.exp(-t * t / (2 * s * s)))

KERNELS = {
    "box": (_box, 0.5), "triangle": (_triangle, 1.0),
    "catmullrom": (_catmullrom, 2.0), "mitchell": (_mitchell, 2.0),
    "lanczos2": (_lanczos2, 2.0), "lanczos3": (_lanczos3, 3.0),
    "gaussian": (_gaussian, 2.5),
}
SMOOTH_SIGMA = [0, 0.4, 0.8, 1.3]          # `N` in the chunk


def _weights(src, dst, algo):
    fn, radius = KERNELS[algo]
    ratio = dst / src
    scale = 1 / ratio if ratio < 1 else 1.0
    rad = radius * scale
    rows = []
    for i in range(dst):
        centre = (i + 0.5) / ratio
        lo, hi = int(np.floor(centre - rad)), int(np.ceil(centre + rad))
        acc = {}
        total = 0.0
        for p in range(lo, hi + 1):
            wgt = fn((p + 0.5 - centre) / scale)
            if wgt != 0.0:
                q = min(max(p, 0), src - 1)
                acc[q] = acc.get(q, 0.0) + wgt
                total += wgt
        idxs = sorted(acc)
        rows.append((np.array(idxs, np.int64),
                     np.array([acc[i2] / total for i2 in idxs], np.float64)))
    return rows


def resize_filtered(rgba, sw, sh, dw, dh, algo):
    """Premultiplied separable resize -- the chunk's T()/R() pair."""
    a = rgba.astype(np.float64)
    pm = a.copy()
    pm[..., :3] *= (a[..., 3:4] / 255.0)

    tmp = np.zeros((sh, dw, 4))
    for j, (idxs, wts) in enumerate(_weights(sw, dw, algo)):
        tmp[:, j, :] = (pm[:, idxs, :] * wts[None, :, None]).sum(axis=1)

    out = np.zeros((dh, dw, 4))
    for i, (idxs, wts) in enumerate(_weights(sh, dh, algo)):
        out[i, :, :] = (tmp[idxs, :, :] * wts[:, None, None]).sum(axis=0)

    alpha = out[..., 3]
    res = np.zeros((dh, dw, 4))
    keep = alpha > 1e-4
    res[..., 3] = alpha
    scale = np.where(keep, alpha / 255.0, 1.0)
    for c in range(3):
        res[..., c] = np.where(keep, out[..., c] / scale, 0.0)
    res[~keep] = 0
    return np.clip(np.round(res), 0, 255).astype(np.uint8)


def resize_nearest(rgba, sw, sh, dw, dh):
    ys = np.minimum(sh - 1, ((np.arange(dh) + 0.5) * sh / dh).astype(int))
    xs = np.minimum(sw - 1, ((np.arange(dw) + 0.5) * sw / dw).astype(int))
    return rgba[ys][:, xs]


def blur(rgba, sigma):
    if sigma <= 0:
        return rgba
    rad = max(1, int(np.ceil(2 * sigma)))
    k = np.exp(-(np.arange(-rad, rad + 1) ** 2) / (2 * sigma * sigma))
    k /= k.sum()
    a = rgba.astype(np.float64)
    pm = a.copy()
    pm[..., :3] *= (a[..., 3:4] / 255.0)
    h, w, _ = pm.shape
    pad = np.pad(pm, ((0, 0), (rad, rad), (0, 0)), mode="edge")
    tmp = sum(pad[:, i:i + w, :] * k[i] for i in range(2 * rad + 1))
    pad = np.pad(tmp, ((rad, rad), (0, 0), (0, 0)), mode="edge")
    out = sum(pad[i:i + h, :, :] * k[i] for i in range(2 * rad + 1))
    alpha = out[..., 3]
    res = np.zeros_like(out)
    keep = alpha > 1e-4
    res[..., 3] = alpha
    for c in range(3):
        res[..., c] = np.where(keep, out[..., c] / np.where(keep, alpha / 255.0, 1), 0)
    res[~keep] = 0
    return np.clip(np.round(res), 0, 255).astype(np.uint8)


# ------------------------------------------------------------- quantisation

BAYER = np.array([[0, 8, 2, 10], [12, 4, 14, 6], [3, 11, 1, 9], [15, 7, 13, 5]])


def histogram(rgba):
    """The chunk's F(): opaque pixels only, capped at 20000 distinct colours."""
    flat = rgba.reshape(-1, 4)
    has_alpha = bool((flat[:, 3] < 128).any())
    opaque = flat[flat[:, 3] >= 128][:, :3]
    if len(opaque) == 0:
        return [], has_alpha
    keys = (opaque[:, 0].astype(np.int64) << 16) | \
           (opaque[:, 1].astype(np.int64) << 8) | opaque[:, 2]
    uniq, first, counts = np.unique(keys, return_index=True, return_counts=True)
    order = np.argsort(first)                       # JS Map keeps insertion order
    items = [(int(uniq[i] >> 16), int((uniq[i] >> 8) & 255), int(uniq[i] & 255),
              int(counts[i])) for i in order]
    if len(items) > 20000:
        step = len(items) / 20000
        items = [items[int(v * step)] for v in range(20000)]
    return items, has_alpha


def median_cut(items, n):
    if not items:
        return [(0, 0, 0)]
    if len(items) <= n:
        return [(r, g, b) for r, g, b, _c in items]
    boxes = [list(items)]
    while len(boxes) < n:
        target, best = -1, -1
        for i, box in enumerate(boxes):
            if len(box) > 1 and len(box) > best:
                best, target = len(box), i
        if target < 0:
            break
        box = boxes[target]
        rng = [max(p[c] for p in box) - min(p[c] for p in box) for c in range(3)]
        axis = 0 if rng[0] >= rng[1] and rng[0] >= rng[2] else (
            1 if rng[1] >= rng[0] and rng[1] >= rng[2] else 2)
        box.sort(key=lambda p: p[axis])
        total = sum(p[3] for p in box)
        acc, cut = 0, 0
        for i, p in enumerate(box):
            acc += p[3]
            if acc >= total / 2:
                cut = i + 1
                break
        cut = max(1, min(cut, len(box) - 1))
        boxes[target:target + 1] = [box[:cut], box[cut:]]
    out = []
    for box in boxes:
        tot = sum(p[3] for p in box) or 1
        out.append(tuple(int(round(sum(p[c] * p[3] for p in box) / tot))
                         for c in range(3)))
    return out


def kmeans(items, palette, rounds=5):
    pal = np.array(palette, np.float64)
    pts = np.array([[r, g, b] for r, g, b, _c in items], np.float64)
    wts = np.array([c for *_x, c in items], np.float64)
    for _ in range(rounds):
        d = ((pts[:, None, :] - pal[None, :, :]) ** 2).sum(axis=2)
        near = d.argmin(axis=1)
        for k in range(len(pal)):
            m = near == k
            if m.any():
                pal[k] = np.round((pts[m] * wts[m, None]).sum(0) / wts[m].sum())
    return [tuple(int(v) for v in p) for p in pal]


def quantise(rgba, colors, dither):
    """The chunk's q(): returns (indices, palette, transparent_index)."""
    h, w, _ = rgba.shape
    items, has_alpha = histogram(rgba)
    slots = max(1, colors - 1) if has_alpha else colors
    pal = median_cut(items, slots)
    if len(items) > len(pal):
        pal = kmeans(items, pal, 5)
    full = ([(255, 0, 255)] + pal) if has_alpha else pal
    offset = 1 if has_alpha else 0
    tindex = 0 if has_alpha else None

    palarr = np.array(pal, np.float64)
    flat = rgba.reshape(-1, 4).astype(np.int32)
    idx = np.zeros(w * h, np.uint8)
    transparent = flat[:, 3] < 128 if has_alpha else np.zeros(w * h, bool)

    def nearest(px):
        d = ((px[:, None, :3] - palarr[None, :, :]) ** 2).sum(axis=2)
        return d.argmin(axis=1).astype(np.uint8) + offset

    if dither == "none":
        idx[~transparent] = nearest(flat[~transparent].astype(np.float64))
    elif dither == "ordered":
        g = 255 / np.cbrt(max(2, len(pal)))
        yy, xx = np.mgrid[0:h, 0:w]
        bias = (BAYER[yy & 3, xx & 3] / 16 - 0.5) * g
        px = np.clip(flat[:, :3].astype(np.float64) + bias.reshape(-1, 1), 0, 255)
        idx[~transparent] = nearest(px[~transparent])
    else:                                            # Floyd-Steinberg
        buf = flat[:, :3].astype(np.float64).reshape(h, w, 3)
        mask = (~transparent).reshape(h, w)
        for y in range(h):
            for x in range(w):
                if not mask[y, x]:
                    idx[y * w + x] = 0
                    continue
                cur = np.clip(buf[y, x], 0, 255)
                k = int(((cur - palarr) ** 2).sum(axis=1).argmin())
                idx[y * w + x] = k + offset
                err = cur - palarr[k]
                for dx, dy, wgt in ((1, 0, 7 / 16), (-1, 1, 3 / 16),
                                    (0, 1, 5 / 16), (1, 1, 1 / 16)):
                    nx, ny = x + dx, y + dy
                    if 0 <= nx < w and 0 <= ny < h and mask[ny, nx]:
                        buf[ny, nx] = np.clip(buf[ny, nx] + err * wgt, 0, 255)
    idx[transparent] = 0
    return idx.reshape(h, w), full, tindex


# -------------------------------------------------------------------- main --

def main():
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("src")
    p.add_argument("dst")
    p.add_argument("--size", default="64x64", help="WxH, each 1..1024")
    p.add_argument("--colors", type=int, default=16, help="2..256")
    p.add_argument("--crop", help="x,y,w,h in source pixels (default: whole image)")
    p.add_argument("--resize", default="auto",
                   choices=["auto", "nearest"] + sorted(KERNELS))
    p.add_argument("--dither", default="none", choices=("none", "ordered", "floyd"))
    p.add_argument("--smooth", type=int, default=0, choices=(0, 1, 2, 3),
                   help="edge smoothing: gaussian sigma 0/.4/.8/1.3")
    a = p.parse_args()

    dw, dh = (int(v) for v in a.size.lower().split("x"))
    dw, dh = max(1, min(1024, dw)), max(1, min(1024, dh))
    colors = max(2, min(256, a.colors))

    img = Image.open(a.src).convert("RGBA")
    rgba = np.array(img)
    if a.crop:
        cx, cy, cw, ch = (int(v) for v in a.crop.split(","))
        rgba = rgba[cy:cy + ch, cx:cx + cw]
    sh, sw = rgba.shape[:2]

    algo = a.resize
    if algo == "auto":
        algo = "lanczos3" if (dw * dh) / (sw * sh) < 1 else "nearest"
    rgba = (resize_nearest(rgba, sw, sh, dw, dh) if algo == "nearest"
            else resize_filtered(rgba, sw, sh, dw, dh, algo))
    rgba = blur(rgba, SMOOTH_SIGMA[a.smooth])

    idx, palette, tindex = quantise(rgba, colors, a.dither)

    out = Image.frombytes("P", (dw, dh), idx.tobytes())
    flat = []
    for r, g, b in palette:
        flat += [r, g, b]
    flat += [0, 0, 0] * (256 - len(palette))
    out.putpalette(flat)
    if tindex is not None:
        out.save(a.dst, transparency=tindex)
    else:
        out.save(a.dst)
    print(f"{a.src} -> {a.dst}: {dw}x{dh}, {len(palette)} colours, "
          f"resize={algo}, dither={a.dither}, "
          f"transparent index={tindex if tindex is not None else 'none'}")


if __name__ == "__main__":
    main()
