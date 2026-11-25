"""Real-shop photo scenes for the engine (mixed into engine.Video).

  shop  {"image": "assets/store/brand-wall.jpg", "mode": "pan" | "print",
         "from": [0.1, 0.5], "to": [0.9, 0.5],     # pan only: focus point (fractions of the photo) at start / end
         "zoom": [1.0, 1.12],                       # slow push-in (start, end)
         "tag": "56 HIGH STREET, LEICESTER",        # optional pin pill
         "text": "COME SAY HI",                     # optional headline (1-4 words)
         "sub": "Independent opticians since 1974", # optional line
         "caption": "Our shop, Leicester"}          # print only: written on the white strip under the photo
  pan   = full-screen Ken Burns over a photo of the shop (best for the 4:3 interior shots), darkened at the
          top for the logo and at the bottom for the words.
  print = the photo as a white-bordered print that drops onto the style background and slowly zooms
          (best for the storefront, which is wide).
Only use the cleaned photos in studio/assets/store/ (see studio/store_prep.py and studio/assets/store/photos.json).
"""
import math
import numpy as np
from PIL import Image, ImageDraw, ImageFilter
from lib import *


def _fit(txt, fname, maxw, maxh, size=400, track=4):
    f = font('dm', size, 'Bold') if fname == 'dm' else font(fname, size)
    m = text_mask(txt, f, track=track)
    s = min(maxw / m.width, maxh / m.height, 1.0 if size <= 120 else 9)
    return m.resize((max(1, int(m.width * s)), max(1, int(m.height * s))), Image.LANCZOS)


def _pin(D, col):
    S = 4; im = Image.new('RGBA', (D * S, D * S), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    r = D * S * .32; cx = D * S / 2; cy = D * S * .38
    d.ellipse((cx - r, cy - r, cx + r, cy + r), fill=col + (255,))
    d.polygon([(cx - r * .82, cy + r * .5), (cx + r * .82, cy + r * .5), (cx, D * S * .95)], fill=col + (255,))
    rr = r * .42; d.ellipse((cx - rr, cy - rr, cx + rr, cy + rr), fill=(0, 0, 0, 0))
    return im.resize((D, D), Image.LANCZOS)


class StoreScenes:
    def _photo(self, path):
        k = ('photo', path)
        if k not in self.cache: self.cache[k] = self.img(path).convert('RGB')
        return self.cache[k]

    def _cover(self, img, fx, fy, zoom, size=(W, H)):
        """Crop-to-fill `size` from img, focused on (fx, fy) (fractions), zoomed in by `zoom`."""
        ow, oh = size; iw, ih = img.size
        s = max(ow / iw, oh / ih) * zoom
        ww, wh = ow / s, oh / s
        x0 = clamp(fx * iw - ww / 2, 0, iw - ww); y0 = clamp(fy * ih - wh / 2, 0, ih - wh)
        return img.transform(size, Image.AFFINE, (1 / s, 0, x0, 0, 1 / s, y0), resample=Image.BICUBIC)

    def _shade(self):
        k = ('shade',)
        if k not in self.cache:
            a = np.zeros((H, 1), float); y = np.arange(H)[:, None]
            a += np.clip(1 - y / 420, 0, 1) ** 1.6 * 170                  # top, for the logo
            a += np.clip((y - 1050) / 870, 0, 1) ** 1.3 * 225             # bottom, for the words
            al = np.repeat(a, W, 1).astype(np.uint8)
            im = Image.new('RGBA', (W, H), (8, 8, 8, 255)); im.putalpha(Image.fromarray(al, 'L'))
            yy, xx = np.mgrid[0:H, 0:W]
            v = np.clip((np.sqrt(((xx - W / 2) / W) ** 2 + ((yy - H / 2) / H) ** 2) - .42) * 260, 0, 90).astype(np.uint8)
            vig = Image.new('RGBA', (W, H), (0, 0, 0, 255)); vig.putalpha(Image.fromarray(v, 'L'))
            im.alpha_composite(vig); self.cache[k] = im
        return self.cache[k]

    def _tag(self, i, text, dark_text=True):
        k = ('shoptag', i, text)
        if k not in self.cache:
            fg = INK if dark_text else (255, 255, 255)
            m = fill(text_mask(text.upper(), font('dm', 34, 'Bold'), track=6), fg)
            pin = _pin(44, TEAL)
            pill = round_rect((m.width + 130, 84), 42, (255, 255, 255) if dark_text else INK)
            pill.alpha_composite(pin, (30, (pill.height - pin.height) // 2))
            pill.alpha_composite(m, (88, (pill.height - m.height) // 2))
            self.cache[k] = pill
        return self.cache[k]

    def s_shop(self, i, sc, lt, dur):
        mode = sc.get('mode', 'pan')
        img = self._photo(sc['image'])
        z0, z1 = sc.get('zoom', [1.0, 1.1]); u = clamp(lt / dur)
        punch = .14 * (1 - ease_out(prog(lt, 0, .45)))                   # quick push on the cut
        if mode == 'pan':
            f0, f1 = sc.get('from', [.15, .5]), sc.get('to', [.85, .5]); e = ease_inout(u)
            c = self._cover(img, lerp(f0[0], f1[0], e), lerp(f0[1], f1[1], e), lerp(z0, z1, u) + punch).convert('RGBA')
            c.alpha_composite(self._shade())
            place(c, self.logo, W / 2, 190)
            y_tag, y_text, y_sub, on_photo = 1440, 1580, 1720, True
            bgcol = None
        else:
            c, bgcol = self.bg(i, lt); self.top_logo(c, bgcol)
            pw = 920; ph = int(pw * min(.75, img.height / img.width))
            inner = self._cover(img, .5, .5, lerp(z0, z1, u), (pw, ph))
            cap = sc.get('caption')
            bot = 130 if cap else 34
            pr = Image.new('RGBA', (pw + 68, ph + 34 + bot), (255, 255, 255, 255)); pr.paste(inner, (34, 34))
            if cap:
                cm = self.txt(('shopcap', i), lambda: _fit(cap, 'CG500i', pw - 40, 80, size=64, track=0))
                pr.alpha_composite(fill(cm, (40, 40, 40)), ((pr.width - cm.width) // 2, 34 + ph + (bot - cm.height) // 2))
            sh = Image.new('RGBA', (pr.width + 80, pr.height + 80), (0, 0, 0, 0))
            ImageDraw.Draw(sh).rectangle((40, 52, 40 + pr.width, 52 + pr.height), fill=(0, 0, 0, 120))
            sh = sh.filter(ImageFilter.GaussianBlur(18)); sh.alpha_composite(pr, (40, 40))
            pd = ease_back(prog(lt, 0, .5)); rot = lerp(-9, -2.5, ease_out(prog(lt, 0, .7)))
            place(c, sh, W / 2, lerp(-500, 900, pd) if pd < 1 else 900, rot=rot, alpha=clamp(prog(lt, 0, .15) * 2))
            y_tag, y_text, y_sub, on_photo = 1395, 1530, 1660, False
            if sc.get("text"): y_tag = 395                                 # headline goes under the print, tag above it
        # words
        if sc.get('tag'):
            tg = self._tag(i, sc['tag'], dark_text=True)
            pt = self.enter(lt, .35, .3); place(c, tg, W / 2, y_tag + 30 * (1 - pt), alpha=pt)
        if sc.get('text'):
            tm = self.txt(('shoptx', i), lambda: _fit(sc['text'], 'Anton' if self.st['head'] == 'Anton' or on_photo else self.st['head'], 940, 190, size=170))
            ti = fill(tm, (255, 255, 255)) if on_photo else self.head_fill(tm, bgcol, accent=True)
            pe = prog(lt, .55, .25)
            place(c, ti, W / 2, y_text, scale=lerp(1.4, 1, ease_in(pe)) if pe < 1 else 1, alpha=clamp(pe * 3))
        if sc.get('sub'):
            sm = self.txt(('shopsub', i), lambda: _fit(sc['sub'], 'CG500i', 940, 90, size=66, track=0))
            col = CREAM if on_photo else (self.st['muted'] if bgcol is None else self.fg_on(bgcol))
            ps = self.enter(lt, .85, .4); place(c, fill(sm, col), W / 2, y_sub + 20 * (1 - ps), alpha=ps)
        if mode == 'pan' or self.st['bg'] == 'dark': flash(c, lt, 0, dur=.22, peak=.45)
        return c

    def store_audio(self, tr, sfx):
        for i, (a, e, sc) in enumerate(self.scenes):
            if sc['type'] == 'shop':
                tr.add(sfx.whoosh(.3, .35), max(0, a - .08))
                if sc.get('text'): tr.add(sfx.impact(.6, .25), a + .55)
