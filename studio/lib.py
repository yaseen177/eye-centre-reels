import math, random, io
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter
import cairosvg

W, H, FPS = 1080, 1920, 30
import os
F = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'fonts') + '/'
DMS = F + 'DMSans.ttf'

BLACK = (10, 10, 10)
GOLD = (200, 169, 110)
GOLD_L = (238, 214, 160)
GOLD_D = (150, 120, 70)
CREAM = (253, 246, 236)
RED = (155, 35, 53)
INK = (26, 36, 32)
TEAL = (42, 170, 138)

_fc = {}
def font(name, size, var=None):
    k = (name, size, var)
    if k not in _fc:
        if name == 'dm':
            f = ImageFont.truetype(DMS, size)
            f.set_variation_by_name(var or 'Regular')
        else:
            f = ImageFont.truetype(F + name + '.ttf', size)
        _fc[k] = f
    return _fc[k]

def clamp(x, a=0.0, b=1.0): return max(a, min(b, x))
def prog(t, t0, d): return clamp((t - t0) / d) if d > 0 else (1.0 if t >= t0 else 0.0)
def ease_out(x): return 1 - (1 - x) ** 3
def ease_in(x): return x ** 3
def ease_inout(x): return 4 * x ** 3 if x < .5 else 1 - (-2 * x + 2) ** 3 / 2
def ease_back(x, s=1.9):
    x = x - 1
    return 1 + (s + 1) * x ** 3 + s * x ** 2
def lerp(a, b, x): return a + (b - a) * x

def text_mask(txt, fnt, track=0):
    """Tight 'L' mask of text with letter tracking (px)."""
    if track == 0:
        l, t, r, b = fnt.getbbox(txt)
        m = Image.new('L', (r - l + 4, b - t + 4), 0)
        ImageDraw.Draw(m).text((-l + 2, -t + 2), txt, font=fnt, fill=255)
        return m
    widths = [fnt.getlength(c) for c in txt]
    total = int(sum(widths) + track * (len(txt) - 1)) + 8
    asc, desc = fnt.getmetrics()
    m = Image.new('L', (total, asc + desc + 8), 0)
    d = ImageDraw.Draw(m); x = 4
    for c, w in zip(txt, widths):
        d.text((x, 4), c, font=fnt, fill=255); x += w + track
    bb = m.getbbox()
    return m.crop((max(0, bb[0] - 2), max(0, bb[1] - 2), bb[2] + 2, bb[3] + 2))

def fill(mask, color):
    im = Image.new('RGBA', mask.size, color + (255,))
    im.putalpha(mask); return im

def gold_fill(mask, top=GOLD_L, mid=GOLD, bot=GOLD_D):
    w, h = mask.size
    y = np.linspace(0, 1, h)[:, None]
    c = np.zeros((h, 1, 3))
    for i in range(3):
        c[:, 0, i] = np.where(y[:, 0] < .55, top[i] + (mid[i] - top[i]) * (y[:, 0] / .55),
                              mid[i] + (bot[i] - mid[i]) * ((y[:, 0] - .55) / .45))
    arr = np.repeat(c, w, axis=1).astype(np.uint8)
    im = Image.fromarray(arr, 'RGB').convert('RGBA'); im.putalpha(mask); return im

def with_alpha(im, a):
    if a >= 0.999: return im
    im = im.copy(); al = im.getchannel('A').point(lambda v: int(v * a)); im.putalpha(al); return im

def place(canvas, im, cx, cy, scale=1.0, alpha=1.0, rot=0.0):
    if alpha <= 0.003 or scale <= 0.01: return
    if abs(scale - 1) > 1e-3:
        im = im.resize((max(1, int(im.width * scale)), max(1, int(im.height * scale))), Image.LANCZOS)
    if abs(rot) > 0.01:
        im = im.rotate(rot, resample=Image.BICUBIC, expand=True)
    im = with_alpha(im, alpha)
    canvas.alpha_composite(im, (int(cx - im.width / 2), int(cy - im.height / 2)))

def place_clip(canvas, im, x, y):
    """alpha_composite allowing negative / off-canvas positions."""
    x, y = int(x), int(y)
    sx0, sy0 = max(0, -x), max(0, -y)
    sx1, sy1 = min(im.width, W - x), min(im.height, H - y)
    if sx1 <= sx0 or sy1 <= sy0: return
    canvas.alpha_composite(im.crop((sx0, sy0, sx1, sy1)), (x + sx0, y + sy0))

def bg_black(glow_y=0.42, strength=0.22, glow=GOLD):
    yy, xx = np.mgrid[0:H, 0:W]
    d = np.sqrt(((xx - W / 2) / (W * .75)) ** 2 + ((yy - H * glow_y) / (H * .42)) ** 2)
    g = np.clip(1 - d, 0, 1) ** 2 * strength
    arr = np.zeros((H, W, 3))
    for i in range(3): arr[:, :, i] = BLACK[i] + (glow[i] - BLACK[i]) * g
    vign = np.clip(1 - (np.sqrt(((xx - W / 2) / W) ** 2 + ((yy - H / 2) / H) ** 2) - .35) * .9, .55, 1)
    arr *= vign[:, :, None]
    return Image.fromarray(arr.astype(np.uint8), 'RGB').convert('RGBA')

def shine(mask, pos, width=0.12, angle=0.35, strength=0.85):
    """White diagonal band over a mask. pos 0..1 across the mask."""
    w, h = mask.size
    yy, xx = np.mgrid[0:h, 0:w]
    u = (xx / w) + (yy / h) * angle
    c = lerp(-0.3, 1.0 + angle + 0.3, pos)
    band = np.clip(1 - np.abs(u - c) / width, 0, 1) ** 2 * strength
    a = (np.asarray(mask).astype(float) / 255) * band
    im = Image.new('RGBA', (w, h), (255, 250, 235, 0))
    im.putalpha(Image.fromarray((a * 255).astype(np.uint8)))
    return im

def star(d, cx, cy, r, col):
    pts = []
    for i in range(8):
        a = math.pi / 4 * i
        rr = r if i % 2 == 0 else r * 0.22
        pts.append((cx + rr * math.cos(a), cy + rr * math.sin(a)))
    d.polygon(pts, fill=col)

def round_rect(size, radius, color, shadow=0):
    w, h = size
    pad = shadow * 3
    im = Image.new('RGBA', (w + pad * 2, h + pad * 2), (0, 0, 0, 0))
    if shadow:
        sh = Image.new('L', im.size, 0)
        ImageDraw.Draw(sh).rounded_rectangle((pad, pad + shadow // 2, pad + w, pad + h + shadow // 2), radius, fill=170)
        sh = sh.filter(ImageFilter.GaussianBlur(shadow))
        im = Image.new('RGBA', im.size, (0, 0, 0, 255)); im.putalpha(sh)
    ImageDraw.Draw(im).rounded_rectangle((pad, pad, pad + w, pad + h), radius, fill=color + (255,))
    return im

# ---------------- logo (from the brand lockup: teal circle, white glasses, Georgia-style wordmark)
GLASSES = ("M494.808,192.041l-9.598-0.161c0,0-8.412-25.989-56.914-27.898c-38.4-1.518-77.883,1.098-112.568,6.744c-27.018,4.386-38.022,22.044-43.646,21.946L256,192.412l-16.083,0.258c-5.625,0.098-16.629-17.559-43.646-21.946c-34.685-5.646-74.168-8.262-112.568-6.744c-48.501,1.910-56.914,27.898-56.914,27.898l-9.598,0.161c-9.651,0.154-17.350,8.108-17.188,17.762l0.301,18.769c0.119,7.227,4.676,13.649,11.466,16.125l6.257,2.287c0,0,10.462,33.419,26.745,61.458c23.159,39.869,65.200,42.954,109.189,38.428c61.286-6.310,74.008-64.459,79.094-81.703c9.913-33.628,22.946-29.830,22.946-29.830s13.033-3.798,22.946,29.830c5.086,17.244,17.808,75.393,79.094,81.703c43.989,4.526,86.029,1.441,109.188-38.428c16.283-28.038,26.744-61.458,26.744-61.458l6.258-2.287c6.789-2.476,11.347-8.898,11.466-16.125l0.301-18.769C512.158,200.149,504.459,192.195,494.808,192.041z "
           "M200.335,263.404c-2.938,7.884-6.446,15.559-10.284,23.121c-8.090,15.936-19.955,27.528-39.368,29.438c-8.038,0.791-15.051,1.224-21.438,1.330c-37.189,0.602-49.190-10.536-56.624-22.659c-11.557-18.875-16.863-35.476-18.867-48.851c-5.684-37.938,30.557-44.284,59.173-42.961c23.918,1.106,51.744,0.790,75.036,6.458c10.916,2.658,17.699,10.458,18.755,18.748C208.254,240.059,205.718,248.985,200.335,263.404z "
           "M458.246,245.782c-2.004,13.375-7.311,29.976-18.867,48.851c-7.433,12.124-19.434,23.261-56.624,22.659c-6.387-0.106-13.401-0.539-21.438-1.330c-19.413-1.910-31.278-13.502-39.368-29.438c-3.838-7.562-7.346-15.237-10.284-23.121c-5.383-14.418-7.919-23.345-6.384-35.378c1.057-8.290,7.839-16.090,18.756-18.748c23.292-5.667,51.117-5.352,75.036-6.458C427.688,201.499,463.930,207.844,458.246,245.782z")

def logo_icon(D):
    gw = D * 61 / 72
    svg = (f'<svg xmlns="http://www.w3.org/2000/svg" width="{D}" height="{D}" viewBox="0 0 {D} {D}">'
           f'<circle cx="{D/2}" cy="{D/2}" r="{D/2}" fill="#2aaa8a"/>'
           f'<g transform="translate({(D-gw)/2},{(D-gw)/2}) scale({gw/512})"><path fill="#ffffff" d="{GLASSES}"/></g></svg>')
    png = cairosvg.svg2png(bytestring=svg.encode(), output_width=D, output_height=D)
    return Image.open(io.BytesIO(png)).convert('RGBA')

def logo_lockup(D, text_col=(255, 255, 255)):
    ic = logo_icon(D)
    tm = text_mask('the eye centre', font('Gelasio', int(D * 0.36)))
    gap = int(D * 0.24)
    w = D + gap + tm.width; h = max(D, tm.height)
    im = Image.new('RGBA', (w, h), (0, 0, 0, 0))
    im.alpha_composite(ic, (0, (h - D) // 2))
    im.alpha_composite(fill(tm, text_col), (D + gap, (h - tm.height) // 2 + int(D * 0.02)))
    return im

def flash(canvas, t, t_hit, dur=0.18, col=(255, 240, 210), peak=0.55):
    p = (t - t_hit) / dur
    if 0 <= p <= 1:
        canvas.alpha_composite(Image.new('RGBA', (W, H), col + (int(255 * peak * (1 - p) ** 2),)))
