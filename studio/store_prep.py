"""Clean + grade the shop photos Abbas sent (Nov 2026) into studio/assets/store/.

    python3 -I studio/store_prep.py <folder with the original jpgs> studio/assets/store

The originals are NOT kept in this (public) repo: they show a brand campaign poster of a real model,
ad cards with real people, a passer-by / reflections, a Mulberry card and in-store % stickers.
Every edit below removes one of those. Only the cleaned files in studio/assets/store/ may be used.
"""
import sys, os
import numpy as np
from PIL import Image, ImageFilter, ImageEnhance, ImageDraw

def wall_fill(im, box, side='both', w=24, left_until=None):
    """Paint a box with the plain wall around it: per row, blend left-side and right-side wall colours across the box.
    left_until: below this row the left side is not wall (a cabinet), so keep the last left colour and follow the right side's shading."""
    a = np.asarray(im).astype(float); x0, y0, x1, y1 = box
    xs = np.linspace(0, 1, x1 - x0)[:, None]; Llast = Rlast = None
    for y in range(y0, y1):
        R = np.median(a[y, x1 + 4:x1 + 4 + w], axis=0)
        if side == 'right' or x0 < 8: L = R
        elif left_until is not None and y >= left_until: L = Llast + (R - Rlast)
        else:
            L = np.median(a[y, x0 - 4 - w:x0 - 4], axis=0); Llast, Rlast = L, R
        a[y, x0:x1] = L * (1 - xs) + R * xs
    a[y0:y1, x0:x1] += np.random.default_rng(1).normal(0, 1.2, a[y0:y1, x0:x1].shape)
    out = Image.fromarray(np.clip(a, 0, 255).astype(np.uint8))
    m = Image.new('L', im.size, 0); ImageDraw.Draw(m).rectangle(box, fill=255); m = m.filter(ImageFilter.GaussianBlur(4))
    return Image.composite(out, im, m)

def blur(im, box, r=14, feather=6):
    m = Image.new('L', im.size, 0); ImageDraw.Draw(m).rectangle(box, fill=255); m = m.filter(ImageFilter.GaussianBlur(feather))
    return Image.composite(im.filter(ImageFilter.GaussianBlur(r)), im, m)

def sticker(im, box, r=9):
    """Blur + desaturate a small % sticker so it reads as nothing."""
    x0, y0, x1, y1 = box; reg = im.crop(box).convert('L').convert('RGB')
    base = im.copy(); base.paste(reg, (x0, y0))
    return blur(base, box, r, feather=4)

def grade(im, warm=1.0):
    im = ImageEnhance.Contrast(im).enhance(1.07)
    im = ImageEnhance.Color(im).enhance(1.12)
    a = np.asarray(im).astype(float)
    a[:, :, 0] *= 1 + .025 * warm; a[:, :, 2] *= 1 - .03 * warm
    return Image.fromarray(np.clip(a, 0, 255).astype(np.uint8))

JOBS = {
    # out name: (source file, [edits], crop)
    'storefront.jpg': ('ebcddf7e-image.jpg', [
        ('blur', (570, 420, 612, 520), 10),        # person inside the doorway
        ('blur', (1070, 420, 1150, 480), 8),       # distant passers-by
    ], (0, 9, 1170, 776)),
    'brand-wall.jpg': ('72e51e5d-image.jpg', [
        ('wall', (0, 0, 392, 242), 'right'),       # campaign poster (real model)
        ('wall', (0, 330, 400, 362), 'right'),     # poster edge under the SALE sign
        ('blur', (452, 468, 512, 578), 12),        # passer-by reflected in the mirror
        ('blur', (305, 795, 405, 915), 14),        # Mulberry ad card (not in online content)
        ('sticker', (1205, 540, 1255, 580), 9),       # % stickers (offer not verified)
        ('sticker', (1283, 540, 1328, 580), 9),
    ], None),
    'rayban-wall.jpg': ('f6761fe8-image.jpg', [
        ('wall', (385, 30, 528, 214), 'both'),    # ad card with a real model
        ('blur', (636, 395, 684, 485), 10),        # passer-by outside the door
        ('sticker', (100, 492, 160, 532), 9),         # % stickers
        ('sticker', (472, 500, 528, 542), 9),
        ('sticker', (852, 638, 898, 674), 9),
    ], None),
    'shop-floor.jpg': ('0789cebc-image.jpg', [
        ('wall', (508, 50, 790, 402), 'cab'),      # campaign poster (real model); Ray-Ban cabinet on its left below y=268
        ('blur', (535, 455, 800, 482), 10),        # poster edge under the SALE sign
        ('blur', (718, 762, 778, 838), 12),        # Mulberry ad card
        ('sticker', (1410, 608, 1455, 640), 8),       # % stickers
        ('sticker', (1485, 606, 1530, 640), 8),
    ], None),
}

if __name__ == '__main__':
    src, dst = sys.argv[1], sys.argv[2]; os.makedirs(dst, exist_ok=True)
    for name, (f, edits, crop) in JOBS.items():
        im = Image.open(os.path.join(src, f)).convert('RGB')
        for kind, box, arg in edits:
            im = (wall_fill(im, box, 'both', left_until=266) if arg == 'cab' else wall_fill(im, box, arg)) if kind == 'wall' else sticker(im, box, arg) if kind == 'sticker' else blur(im, box, arg)
        if crop: im = im.crop(crop)
        im = grade(im, warm=1.4 if name == 'storefront.jpg' else 1.0)
        im.save(os.path.join(dst, name), quality=90)
        print('saved', name, im.size)
