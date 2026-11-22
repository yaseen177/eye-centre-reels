"""Cut a product photo out of a desktop (1440px) screenshot of a theeyecentre.com product page.

    python3 -I studio/cut.py <screenshot.webp|png> <out.png>

Finds the main product image box (top-left of the page), removes the slider arrows, the
"Ask an Expert" pill and the "1 / N" counter, and saves the frame on a transparent background.
Prints WARNING if the frame may be cropped on the site: view the cut-out and pick another product if it is.
"""
import sys
import numpy as np
from PIL import Image, ImageFilter

PAGE_BG = np.array([246, 249, 248])


def find_box(a):
    """Image box = the large area left of x~940 whose colour differs from the page background."""
    h, w, _ = a.shape
    y = 240                                   # a row inside the box, above most products
    row = np.abs(a[y, :1000] - PAGE_BG).sum(1)
    xs = np.where(row > 4)[0]
    xs = xs[(xs > 20) & (xs < 960)]
    if not len(xs): raise SystemExit('no image box found')
    x0, x1 = int(xs.min()), int(xs.max())
    col = np.abs(a[:900, x0 + 40] - PAGE_BG).sum(1)
    ys = np.where(col > 4)[0]
    ys = ys[(ys > 120) & (ys < 900)]
    y0, y1 = int(ys.min()), int(ys.max())
    return x0 + 2, y0 + 2, x1 - 2, y1 - 2


def cut(src, out, pad=20):
    a = np.asarray(Image.open(src).convert('RGB')).astype(int)
    bx0, by0, bx1, by1 = find_box(a)
    sub = a[by0:by1, bx0:bx1].copy()
    h, w = sub.shape[:2]
    bg = np.median(sub[5:30, 100:w - 100].reshape(-1, 3), axis=0)
    # teal "Ask an Expert" pill in the lower-left
    teal = (sub[:, :, 1] > sub[:, :, 0] + 40) & (sub[:, :, 1] > sub[:, :, 2] - 5)
    zone = np.zeros((h, w), bool); zone[max(0, h - 170):, :260] = True
    tm = np.array(Image.fromarray(((teal & zone) * 255).astype(np.uint8)).filter(ImageFilter.MaxFilter(9))) > 0
    if tm.any():
        ys, xs = np.where(tm); sub[ys.min() - 6:ys.max() + 8, :xs.max() + 8] = bg
    L, R = 36, 36                              # slider arrows sit at the box edges
    mask = np.ones((h, w), bool); mask[:, :L] = False; mask[:, w - R:] = False; mask[h - 45:, :] = False
    d = np.abs(sub - bg).sum(2); m = (d > 36) & mask
    if m.sum() < 2000: raise SystemExit('no product found in the box')
    ys, xs = np.where(m); x0, x1, y0, y1 = xs.min(), xs.max(), ys.min(), ys.max()
    # cropped on the site? product pixels inside the edge bands (outside the arrow rows)
    band = d > 36; band[h // 2 - 35:h // 2 + 35, :] = False; band[h - 45:, :] = False
    edge = band[:, :L].sum() > 60 or band[:, w - R:].sum() > 60 or y0 <= 3
    c = sub[max(0, y0 - pad):min(h, y1 + pad), max(L, x0 - pad):min(w - R, x1 + pad)]
    dd = np.abs(c - bg).sum(2).astype(float); alpha = np.clip((dd - 6) / 40, 0, 1)
    # drop the pale floor reflection some photos have (lower half only)
    lum = c.mean(2); k = np.clip((lum - 215) / 30, 0, 1); k[: int(c.shape[0] * .6)] = 0
    alpha *= (1 - k * 0.85)
    Image.fromarray(np.dstack([c.astype(np.uint8), (alpha * 255).astype(np.uint8)]), 'RGBA').save(out)
    print(f'saved {out} {c.shape[1]}x{c.shape[0]} box=({bx0},{by0},{bx1},{by1})' + ('  WARNING: touches edge' if edge else ''))
    return 0   # a WARNING is advisory: look at the cut-out before using it


if __name__ == '__main__':
    sys.exit(cut(sys.argv[1], sys.argv[2]))
