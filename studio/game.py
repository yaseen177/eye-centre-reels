"""Video-game "mission" scenes for the engine (mixed into engine.Video). An ORIGINAL game look: our own HUD,
fonts and colours. Never copy a real game's logo, font, characters, screens or wording (e.g. no "Mission passed /
Respect +", no wanted stars, no health/armour bars) and never name a game in the video or caption.

  mission  {"title": "NEW MISSION", "text": "Find frames that actually suit your face",
            "objective": "Get to 56 High Street, Leicester", "level": "LV 74"}
           cinematic title card + typed briefing + objective box + animated minimap with our pin
  loot     {"title": "ITEM FOUND", "rarity": "LEGENDARY" | "EPIC" | "RARE", + product fields (image, brand, name, price, was),
            "stats": [["DRIP", 100], ["MAIN CHARACTER", 95], ["WALLET DAMAGE", 30]]}
           light rays + rarity ribbon + product card + stat bars filling up (stats are playful opinion, never reviews)
  complete {"lines": ["MISSION", "COMPLETE"], "reward": "30% OFF DESIGNER FRAMES", "xp": "+100 STYLE"}
           slam + shine + reward pill (reward must be a LIVE Shopify offer or a real feature) + floating XP
"""
import math, random
import numpy as np
from PIL import Image, ImageDraw, ImageFilter
from lib import *

RARITY = {'LEGENDARY': (232, 190, 90), 'EPIC': (176, 110, 245), 'RARE': (70, 160, 255), 'COMMON': (190, 190, 190)}
HUD_BG = (12, 14, 18)


def _fit(txt, fname, maxw, maxh, size=400, track=4):
    f = font('dm', size, 'Bold') if fname == 'dm' else font(fname, size)
    m = text_mask(txt, f, track=track)
    s = min(maxw / m.width, maxh / m.height, 1.0 if size <= 120 else 9)
    return m.resize((max(1, int(m.width * s)), max(1, int(m.height * s))), Image.LANCZOS)


def _wrap(txt, fnt, maxw):
    words, lines, cur = txt.split(), [], ''
    for w in words:
        t = (cur + ' ' + w).strip()
        if fnt.getlength(t) <= maxw or not cur: cur = t
        else: lines.append(cur); cur = w
    if cur: lines.append(cur)
    return lines


class GameScenes:
    # ------------------------------------------------------------ shared HUD bits
    def _game_bg(self, i, lt):
        c, bgcol = self.bg(i, lt)
        if self.st['bg'] != 'dark':                       # game scenes always sit on a dark HUD backdrop
            if ('gbg',) not in self.cache: self.cache[('gbg',)] = bg_black(glow_y=.45, strength=.18)
            c = self.cache[('gbg',)].copy(); bgcol = None
        # faint scanlines + corner brackets
        k = ('scan',)
        if k not in self.cache:
            s = Image.new('RGBA', (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(s)
            for y in range(0, H, 6): d.line([(0, y), (W, y)], fill=(0, 0, 0, 34))
            g = GOLD + (150,); L = 70; m = 40
            for (x, y, dx, dy) in [(m, m + 300, 1, 1), (W - m, m + 300, -1, 1), (m, H - m - 80, 1, -1), (W - m, H - m - 80, -1, -1)]:
                d.line([(x, y), (x + dx * L, y)], fill=g, width=5); d.line([(x, y), (x, y + dy * L)], fill=g, width=5)
            self.cache[k] = s
        c.alpha_composite(self.cache[k])
        return c, bgcol

    def _xp_bar(self, c, frac, label, y=300):
        w = 520; x = (W - w) // 2
        ov = Image.new('RGBA', (W, 60), (0, 0, 0, 0)); ImageDraw.Draw(ov).rounded_rectangle((x, 10, x + w, 32), 11, fill=(255, 255, 255, 45))
        c.alpha_composite(ov, (0, y - 10)); d = ImageDraw.Draw(c)
        if frac > 0: d.rounded_rectangle((x, y, x + max(22, int(w * frac)), y + 22), 11, fill=GOLD + (255,))
        m = fill(text_mask(label, font('dm', 26, 'Bold'), track=8), (220, 214, 200))
        c.alpha_composite(m, (x, y - 40))

    def _minimap(self, t, D=330):
        """Original circular minimap: stylised streets, a moving arrow heading for our teal pin."""
        k = ('mapbase', D)
        if k not in self.cache:
            S = 3; im = Image.new('RGBA', (D * S, D * S), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
            d.ellipse((0, 0, D * S - 1, D * S - 1), fill=(28, 32, 38, 235))
            rng = random.Random(7)
            for _ in range(7):                                    # blocks
                x0, y0 = rng.uniform(.05, .7) * D * S, rng.uniform(.05, .7) * D * S
                d.rectangle((x0, y0, x0 + rng.uniform(.12, .25) * D * S, y0 + rng.uniform(.1, .22) * D * S), fill=(40, 46, 54, 255))
            for (a, b) in [((.0, .55), (1, .5)), ((.45, 0), (.5, 1)), ((.0, .2), (1, .3)), ((.15, 0), (.25, 1)), ((.7, 0), (.85, 1))]:
                d.line([(a[0] * D * S, a[1] * D * S), (b[0] * D * S, b[1] * D * S)], fill=(92, 100, 112, 255), width=7 * S)
            mask = Image.new('L', im.size, 0); ImageDraw.Draw(mask).ellipse((0, 0, D * S - 1, D * S - 1), fill=255)
            im.putalpha(Image.fromarray(np.minimum(np.asarray(im.getchannel('A')), np.asarray(mask))))
            d = ImageDraw.Draw(im); d.ellipse((0, 0, D * S - 1, D * S - 1), outline=GOLD + (255,), width=6 * S)
            self.cache[k] = im.resize((D, D), Image.LANCZOS)
        im = self.cache[k].copy(); d = ImageDraw.Draw(im)
        px, py = D * .72, D * .3                                   # our shop
        u = ease_inout(clamp(t / 2.2))
        ax, ay = lerp(D * .3, px - 18, u), lerp(D * .78, py + 30, u)
        ang = math.atan2(py - ay, px - ax)
        pts = [(ax + 22 * math.cos(ang), ay + 22 * math.sin(ang)), (ax + 14 * math.cos(ang + 2.5), ay + 14 * math.sin(ang + 2.5)),
               (ax + 14 * math.cos(ang - 2.5), ay + 14 * math.sin(ang - 2.5))]
        d.polygon(pts, fill=(255, 255, 255, 255))
        r = 15 + 4 * (math.sin(t * 6) + 1)
        d.ellipse((px - r * 1.8, py - r * 1.8, px + r * 1.8, py + r * 1.8), outline=TEAL + (140,), width=3)
        d.ellipse((px - r, py - r, px + r, py + r), fill=TEAL + (255,))
        d.ellipse((px - 6, py - 6, px + 6, py + 6), fill=(255, 255, 255, 255))
        return im

    # ------------------------------------------------------------ mission
    def s_mission(self, i, sc, lt, dur):
        c, bgcol = self._game_bg(i, lt); self.top_logo(c, None)
        if sc.get('level'): self._xp_bar(c, .2 + .55 * ease_out(prog(lt, .2, 1.2)), sc['level'] + '  ·  STYLE XP')
        # title with rules above/below
        tm = self.txt(('gm_t', i), lambda: _fit(sc.get('title', 'NEW MISSION'), 'Anton', 900, 230, size=230, track=10))
        p = prog(lt, 0, .28); ti = gold_fill(tm)
        place(c, ti, W / 2, 610, scale=lerp(1.5, 1, ease_in(p)) if p < 1 else 1, alpha=clamp(p * 3))
        lw = int(820 * ease_out(prog(lt, .2, .35))); d = ImageDraw.Draw(c)
        if lw > 2:
            for y in (470, 750): d.line([(W / 2 - lw / 2, y), (W / 2 + lw / 2, y)], fill=GOLD + (255,), width=4)
        if 0 < prog(lt, .45, .5) < 1:
            sh = shine(tm, prog(lt, .45, .5)); c.alpha_composite(sh, (int(W / 2 - sh.width / 2), int(610 - sh.height / 2)))
        # typed briefing
        if sc.get('text'):
            f = font('dm', 58, 'Medium'); lines = _wrap(sc['text'], f, 900)
            total = len(sc['text']); n = int(total * clamp((lt - .6) / max(.4, dur * .38)))
            y = 830; shown = 0; cur = None
            for ln in lines:
                part = ln[:max(0, n - shown)]; shown += len(ln) + 1
                x0 = W / 2 - f.getlength(ln) / 2
                if part:
                    m = fill(text_mask(part, f), (255, 255, 255)); c.alpha_composite(m, (int(x0), y))
                    cur = (x0 + f.getlength(part) + 8, y)
                y += 76
            if n < total and lt > .6 and int(lt * 4) % 2 == 0:
                cx, cy = cur if cur else (W / 2, 830)
                d.rectangle((cx, cy + 4, cx + 7, cy + 62), fill=GOLD + (255,))
        # objective box + minimap
        if sc.get('objective'):
            po = self.enter(lt, dur * .5, .3)
            if po > 0:
                k = ('gm_obj', i)
                if k not in self.cache:
                    lab = fill(text_mask('OBJECTIVE', font('dm', 28, 'Bold'), track=10), GOLD)
                    om = fill(_fit(sc['objective'], 'dm', 560, 46, size=44, track=0), (255, 255, 255))
                    box = round_rect((max(lab.width, om.width) + 70, 150), 18, HUD_BG)
                    ImageDraw.Draw(box).rectangle((0, 18, 8, 132), fill=GOLD + (255,))
                    box.alpha_composite(lab, (36, 26)); box.alpha_composite(om, (36, 74)); self.cache[k] = box
                box = self.cache[k]
                place(c, box, 70 + box.width / 2 - 40 * (1 - po), 1590, alpha=po)
            mp = self._minimap(max(0, lt - dur * .45))
            place(c, mp, W - 80 - mp.width / 2, 1270, scale=lerp(.6, 1, ease_back(self.enter(lt, dur * .45, .35))), alpha=self.enter(lt, dur * .45, .2))
        flash(c, lt, .28, peak=.4)
        return c

    # ------------------------------------------------------------ loot
    def _rays(self, col, t):
        k = ('rays', col)
        if k not in self.cache:
            S = 1300; im = Image.new('RGBA', (S, S), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
            for j in range(16):
                a0 = j * math.tau / 16; a1 = a0 + math.tau / 40
                d.polygon([(S / 2, S / 2), (S / 2 + S * math.cos(a0), S / 2 + S * math.sin(a0)), (S / 2 + S * math.cos(a1), S / 2 + S * math.sin(a1))], fill=col + (60,))
            yy, xx = np.mgrid[0:S, 0:S]; r = np.sqrt((xx - S / 2) ** 2 + (yy - S / 2) ** 2) / (S / 2)
            a = np.asarray(im.getchannel('A')).astype(float) * np.clip(1.15 - r, 0, 1)
            im.putalpha(Image.fromarray(a.astype(np.uint8))); self.cache[k] = im
        return self.cache[k].rotate(t * 14, resample=Image.BILINEAR)

    def s_loot(self, i, sc, lt, dur):
        c, bgcol = self._game_bg(i, lt); self.top_logo(c, None)
        rar = sc.get('rarity', 'LEGENDARY').upper(); col = RARITY.get(rar, GOLD)
        pin = ease_back(prog(lt, .05, .4))
        place(c, self._rays(col, lt), W / 2, 950, scale=lerp(.3, 1, pin), alpha=clamp(pin))
        tm = self.txt(('gl_t', i), lambda: _fit(sc.get('title', 'ITEM FOUND'), 'Anton', 900, 150, size=150, track=6))
        place(c, fill(tm, (255, 255, 255)), W / 2, 365, alpha=self.enter(lt, 0, .25))
        # rarity ribbon
        k = ('gl_r', i)
        if k not in self.cache:
            rm = fill(text_mask(rar + ' ITEM', font('dm', 40, 'Bold'), track=14), HUD_BG)
            rb = round_rect((rm.width + 90, 74), 37, col); rb.alpha_composite(rm, ((rb.width - rm.width) // 2, (74 - rm.height) // 2))
            self.cache[k] = rb
        place(c, self.cache[k], W / 2, 498, scale=ease_back(prog(lt, .25, .3)))
        cd = self.card(sc, w=820, h=700)
        place(c, cd, W / 2, 955, scale=lerp(.4, 1, pin), alpha=clamp(pin * 2))
        # stats
        stats = sc.get('stats', [])[:3]
        for j, (lab, val) in enumerate(stats):
            pj = ease_out(prog(lt, .7 + j * .22, .45)); y = 1380 + j * 92
            if pj <= 0: continue
            lm = self.txt(('gl_s', i, j), lambda lab=lab: fill(text_mask(lab.upper(), font('dm', 30, 'Bold'), track=6), (230, 224, 210)))
            c.alpha_composite(with_alpha(lm, pj), (150, y))
            x0, x1 = 150, W - 260
            ov = Image.new('RGBA', (W, 40), (0, 0, 0, 0)); ImageDraw.Draw(ov).rounded_rectangle((x0, 10, x1, 30), 10, fill=(255, 255, 255, 45))
            c.alpha_composite(ov, (0, y + 34)); d = ImageDraw.Draw(c)
            d.rounded_rectangle((x0, y + 44, x0 + max(20, int((x1 - x0) * val / 100 * pj)), y + 64), 10, fill=col + (255,))
            vm = fill(text_mask(str(int(val * pj)), font('Anton', 56)), col)
            c.alpha_composite(vm, (W - 230, y + 6))
        if 0 < prog(lt, .25, .12): flash(c, lt, .3, peak=.35, col=col)
        return c

    # ------------------------------------------------------------ complete
    def s_complete(self, i, sc, lt, dur):
        c, bgcol = self._game_bg(i, lt); self.top_logo(c, None)
        lines = sc.get('lines', ['MISSION', 'COMPLETE'])
        ys = [640, 860]
        for j, ln in enumerate(lines[:2]):
            m = self.txt(('gc', i, j), lambda ln=ln: _fit(ln, 'Anton', 960, 260, size=260, track=8))
            p = prog(lt, j * .22, .2); im = gold_fill(m) if j == len(lines) - 1 else fill(m, (255, 255, 255))
            sh = 16 * math.exp(-(lt - j * .22 - .2) * 12) if lt > j * .22 + .2 else 0
            place(c, im, W / 2 + math.sin(lt * 80) * sh, ys[j], scale=lerp(2.0, 1, ease_in(p)) if p < 1 else 1, alpha=clamp(p * 3))
        m2 = self.txt(('gc', i, 1), lambda: _fit(lines[-1], 'Anton', 960, 260, size=260, track=8))
        if 0 < prog(lt, .7, .55) < 1:
            s2 = shine(m2, prog(lt, .7, .55)); c.alpha_composite(s2, (int(W / 2 - s2.width / 2), int(ys[1] - s2.height / 2)))
        if sc.get('reward'):
            lab = self.txt(('gc_l', i), lambda: fill(text_mask('REWARD UNLOCKED', font('dm', 34, 'Bold'), track=14), GOLD))
            pr = self.enter(lt, .6, .3); place(c, lab, W / 2, 1080, alpha=pr)
            k = ('gc_p', i)
            if k not in self.cache:
                u = fill(_fit(sc['reward'], 'Anton', 820, 80, size=80, track=4), BLACK)
                pill = round_rect((u.width + 120, 130), 65, GOLD); pill.alpha_composite(u, ((pill.width - u.width) // 2, (130 - u.height) // 2))
                self.cache[k] = pill
            place(c, self.cache[k], W / 2, 1200, scale=ease_back(prog(lt, .75, .35)))
        if sc.get('xp'):
            px = prog(lt, 1.0, 1.2)
            if px > 0:
                xm = self.txt(('gc_x', i), lambda: fill(text_mask(sc['xp'], font('Anton', 90), track=4), (120, 230, 170)))
                place(c, xm, W / 2, 1520 - 110 * ease_out(px), alpha=clamp(px * 4) * (1 - clamp((px - .7) / .3)))
        flash(c, lt, .42, peak=.55)
        self.sparkles(c, lt + 9, .5)
        if lt > .42: self.confetti(c, lt - .42)
        return c

    def game_audio(self, tr, sfx):
        for i, (a, e, sc) in enumerate(self.scenes):
            t, dur = sc['type'], e - a
            if t == 'mission':
                tr.add(sfx.impact(.9, .4), a); tr.add(sfx.whoosh(.3, .3), a + .2)
                n = len(sc.get('text', ''))
                for j in range(0, n, 3): tr.add(sfx.click(.25), a + .6 + max(.4, dur * .38) * j / max(1, n))
                tr.add(sfx.blip(880, .25), a + dur * .5); tr.add(sfx.blip(1320, .2), a + dur * .5 + .1)
            elif t == 'loot':
                tr.add(sfx.riser(.3, .25), a); tr.add(sfx.coin(.35), a + .3); tr.add(sfx.bell(1318.5, .2, .8), a + .32)
                for j in range(len(sc.get('stats', [])[:3])): tr.add(sfx.blip(990 + 160 * j, .18), a + .7 + j * .22)
            elif t == 'complete':
                tr.add(sfx.impact(.8, .3), a); tr.add(sfx.impact(1.0, .45), a + .22)
                for j, f in enumerate([523.25, 659.25, 783.99, 1046.5]): tr.add(sfx.bell(f, .22, .9), a + .42 + j * .09)
                tr.add(sfx.coin(.3), a + .8)
