"""Viral-format scenes for the engine (mixed into engine.Video).

  chat    {"name": "Bank", "messages": [{"from": "me", "text": "..."}, {"from": "them", "text": "..."}]}
          iMessage-style text conversation, one bubble per beat. Funny intros: me vs my bank / my mum / my optician.
  pov     {"text": "POV: ...", "image": "assets/cutouts/x.png" (optional)}
          TikTok caption boxes typed word by word over a slowly zooming product.
  glitch  {"lines": ["WAIT.", "DON'T BUY", "GLASSES YET"]}   glitchy RGB-split hook, lines land on the beat
  rate    {"title": "RATING FRAMES", "score": "10/10", + product fields}   card, then a stamp slams on it
  guess   {"question": "GUESS THE PRICE", + product fields incl. price (and was)}   price hidden, then revealed
  search  {"query": "designer glasses leicester", "result": "The Eye Centre", "url": "theeyecentre.com",
           "lines": ["Gucci, Tom Ford, Saint Laurent & more", "Independent opticians since 1974"]}
          a search bar types the query, then the result card drops in
"""
import math, random
import numpy as np
from PIL import Image, ImageDraw
from lib import *

RED2 = (214, 32, 44)
IOS_BG = (242, 242, 247)
IOS_BLUE = (10, 132, 255)
IOS_GREY = (229, 229, 234)


def _fit(txt, fname, maxw, maxh, size=400, track=4):
    f = font('dm', size, 'Bold') if fname == 'dm' else font(fname, size)
    m = text_mask(txt, f, track=track)
    s = min(maxw / m.width, maxh / m.height, 1.0 if size <= 120 else 9)
    return m.resize((max(1, int(m.width * s)), max(1, int(m.height * s))), Image.LANCZOS)


def wrap(txt, fnt, maxw):
    words, lines, cur = txt.split(), [], ''
    for w in words:
        t = (cur + ' ' + w).strip()
        if fnt.getlength(t) <= maxw or not cur: cur = t
        else: lines.append(cur); cur = w
    if cur: lines.append(cur)
    return lines


class ViralScenes:
    # ---------------------------------------------------------------- chat
    def bubble(self, text, me):
        key = ('bubble', text, me)
        if key in self.cache: return self.cache[key]
        f = font('dm', 50, 'Medium'); lines = wrap(text, f, 720)
        ms = [text_mask(l, f) for l in lines]; lh = 64
        w = max(m.width for m in ms) + 72; h = lh * len(ms) + 44
        bg = IOS_BLUE if me else IOS_GREY; fg = (255, 255, 255) if me else (0, 0, 0)
        im = round_rect((w, h), 44, bg)
        for j, m in enumerate(ms): im.alpha_composite(fill(m, fg), (36, 22 + j * lh + (lh - m.height) // 2))
        self.cache[key] = im; return im

    def typing_dots(self, t):
        im = round_rect((170, 100), 50, IOS_GREY); d = ImageDraw.Draw(im)
        for k in range(3):
            a = .35 + .65 * max(0, math.sin(t * 9 - k * .9))
            c = int(140 - 60 * a); r = 12 + 3 * a
            d.ellipse((42 + k * 43 - r, 50 - r, 42 + k * 43 + r, 50 + r), fill=(c, c, c, 255))
        return im

    def s_chat(self, i, sc, lt, dur):
        c = Image.new('RGBA', (W, H), IOS_BG + (255,))
        place(c, self.logo_dark, W / 2, 130)
        # contact header
        hdr = self.txt(('chathdr', i), lambda: self._chat_header(sc.get('name', 'Mum')))
        c.alpha_composite(hdr, (0, 220))
        msgs = sc['messages']; n = len(msgs); per = max(.5, (dur - .4) / n)
        shown, y_items = [], []
        y = 600
        for j, m in enumerate(msgs):
            t0 = j * per + (.35 if m.get('from') != 'me' else .1)
            me = m.get('from') == 'me'
            if lt < t0:
                if not me and lt >= t0 - .35 and (j == 0 or lt >= (j - 1) * per + .3):
                    y_items.append(('dots', None, y, 0, False))
                break
            b = self.bubble(m['text'], me)
            y_items.append(('b', b, y, lt - t0, me)); y += b.height + 26
        bottom = max((yy + (b.height if kind == 'b' else 100) for kind, b, yy, u, me in y_items), default=0)
        shift = max(0, bottom - 1640)
        for kind, b, yy, u, me in y_items:
            if kind == 'dots':
                place(c, self.typing_dots(lt), 60 + 85, yy - shift + 50); continue
            p = prog(u, 0, .22); sc_ = lerp(.55, 1, ease_back(p)) if p < 1 else 1
            x = W - 50 - b.width / 2 if me else 50 + b.width / 2
            place(c, b, x + (1 - p) * (60 if me else -60), yy - shift + b.height / 2, scale=sc_, alpha=clamp(p * 2.5))
        return c

    def _chat_header(self, name):
        im = Image.new('RGBA', (W, 250), (249, 249, 251, 255)); d = ImageDraw.Draw(im)
        d.line([(0, 249), (W, 249)], fill=(210, 210, 215, 255), width=2)
        d.ellipse((W / 2 - 62, 18, W / 2 + 62, 142), fill=(160, 165, 178, 255))
        ini = fill(text_mask(name[:1].upper(), font('dm', 64, 'Bold')), (255, 255, 255))
        im.alpha_composite(ini, (int(W / 2 - ini.width / 2), int(80 - ini.height / 2)))
        nm = fill(text_mask(name, font('dm', 40, 'Medium')), (20, 20, 20))
        im.alpha_composite(nm, (int(W / 2 - nm.width / 2), 168))
        d.line([(60, 80), (36, 104), (60, 128)], fill=IOS_BLUE + (255,), width=9, joint='curve')
        return im

    # ---------------------------------------------------------------- pov
    def caption_block(self, text, nwords):
        key = ('cap', text, nwords)
        if key in self.cache: return self.cache[key]
        f = font('dm', 64, 'Bold'); full = wrap(text, f, 860)
        words_left = nwords; rows = []
        for line in full:
            ws = line.split()
            if words_left <= 0: break
            rows.append(' '.join(ws[:words_left])); words_left -= len(ws)
        lh = 96; boxes = []
        for r in rows:
            m = text_mask(r, f); b = round_rect((m.width + 56, lh), 22, (255, 255, 255))
            b.alpha_composite(fill(m, (0, 0, 0)), (28, (lh - m.height) // 2)); boxes.append(b)
        w = max(b.width for b in boxes) if boxes else 1
        im = Image.new('RGBA', (w, max(1, lh * len(boxes) - 6 * max(0, len(boxes) - 1))), (0, 0, 0, 0))
        for j, b in enumerate(boxes): im.alpha_composite(b, ((w - b.width) // 2, j * (lh - 6)))
        self.cache[key] = im; return im

    def s_pov(self, i, sc, lt, dur):
        c, bgcol = self.bg(i, lt); self.top_logo(c, bgcol)
        if sc.get('image'):
            im = self.img(sc['image']); s = 900 / im.width
            z = s * (1 + .08 * lt / dur)
            place(c, im, W / 2, 1180 - 18 * math.sin(lt * 2.2), scale=z * ease_out(prog(lt, 0, .4)) if lt < .4 else z, alpha=ease_out(prog(lt, 0, .3)))
        n = len(sc['text'].split()); k = min(n, 1 + int(lt / max(.12, min(.22, (dur * .55) / n))))
        cap = self.caption_block(sc['text'], k)
        c.alpha_composite(cap, (int(W / 2 - cap.width / 2), 420))
        return c

    # ---------------------------------------------------------------- glitch
    def s_glitch(self, i, sc, lt, dur):
        c = Image.new('RGBA', (W, H), BLACK + (255,)); place(c, self.logo, W / 2, 190)
        lines = sc['lines']; per = max(.5, dur / len(lines)); k = min(len(lines) - 1, int(lt / per))
        ms = [self.txt(('gl', i, j), lambda line=line: _fit(line, 'Anton', 960, 320 if len(lines) > 1 else 520, size=320)) for j, line in enumerate(lines)]
        gap = 36; total = sum(m.height for m in ms) + gap * (len(ms) - 1); y = 930 - total / 2
        for j, m in enumerate(ms):
            cy = y + m.height / 2; y += m.height + gap
            if j > k: continue
            col = RED2 if j == len(lines) - 1 else (255, 255, 255)
            place(c, fill(m, col), W / 2, cy)
        u = lt - k * per
        g = max(math.exp(-u * 7), .15 if (int(lt * 13) % 9 == 0) else 0)
        if g < .02: return c
        a = np.asarray(c.convert('RGB')).copy(); rng = np.random.default_rng(int(lt * 30) + i * 97)
        dx = int(26 * g) + 2
        out = a.copy(); out[:, :, 0] = np.roll(a[:, :, 0], dx, axis=1); out[:, :, 2] = np.roll(a[:, :, 2], -dx, axis=1)
        for _ in range(int(10 * g) + 1):
            y0 = int(rng.integers(300, H - 300)); hh = int(rng.integers(10, 90)); sh = int(rng.integers(-120, 120) * g)
            out[y0:y0 + hh] = np.roll(out[y0:y0 + hh], sh, axis=1)
        out[::4] = (out[::4] * (1 - .25 * g)).astype(np.uint8)
        return Image.fromarray(out, 'RGB').convert('RGBA')

    # ---------------------------------------------------------------- rate
    def stamp(self, text):
        key = ('stamp', text)
        if key in self.cache: return self.cache[key]
        m = _fit(text, 'Anton', 520, 220, size=240); w, h = m.width + 90, m.height + 70
        im = Image.new('RGBA', (w, h), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
        d.rounded_rectangle((4, 4, w - 5, h - 5), 26, outline=RED2 + (255,), width=12)
        im.alpha_composite(fill(m, RED2), ((w - m.width) // 2, (h - m.height) // 2))
        self.cache[key] = im; return im

    def s_rate(self, i, sc, lt, dur):
        c, bgcol = self.bg(i, lt)
        if self.st['bg'] == 'punch': c = Image.new('RGBA', (W, H), BLACK + (255,)); bgcol = BLACK
        self.top_logo(c, bgcol)
        t = self.txt(('rt', i), lambda: _fit(sc.get('title', 'RATING FRAMES'), self.st['head'] if self.st['bg'] == 'cream' else 'Anton', 940, 150, size=150))
        place(c, self.head_fill(t, bgcol, accent=True), W / 2, 400, alpha=self.enter(lt, 0, .3))
        cd = self.card(sc); pin = ease_out(prog(lt, .1, .3))
        t_hit = min(1.1, dur * .45); ps = prog(lt, t_hit, .14)
        shake = 18 * math.exp(-(lt - t_hit) * 14) if lt > t_hit else 0
        place(c, cd, W / 2 + (1 - pin) * 900 + math.sin(lt * 80) * shake, 1040 + math.cos(lt * 70) * shake)
        if ps > 0:
            place(c, self.stamp(sc.get('score', '10/10')), W / 2 + 170, 1580, scale=lerp(2.4, 1, ease_in(ps)), rot=-12, alpha=clamp(ps * 3))
        if self.st['bg'] == 'dark': flash(c, lt, t_hit + .14, peak=.35)
        return c

    # ---------------------------------------------------------------- guess
    def s_guess(self, i, sc, lt, dur):
        c, bgcol = self.bg(i, lt)
        if self.st['bg'] == 'punch': c = Image.new('RGBA', (W, H), BLACK + (255,)); bgcol = BLACK
        self.top_logo(c, bgcol)
        q = self.txt(('gq', i), lambda: _fit(sc.get('question', 'GUESS THE PRICE'), self.st['head'] if self.st['bg'] == 'cream' else 'Anton', 940, 160, size=150))
        place(c, self.head_fill(q, bgcol, accent=True), W / 2, 400, alpha=self.enter(lt, 0, .3))
        cd = self.card(sc, show_price=False); pin = ease_out(prog(lt, .1, .35))
        place(c, cd, W / 2, 960 + (1 - pin) * 200, alpha=pin)
        t_rev = dur * .62
        if lt < t_rev:
            dots = '?' * (1 + int(lt * 4) % 3)
            m = self.txt(('gd', dots), lambda: _fit('£' + dots, 'Anton', 500, 150, size=150))
            pulse = 1 + .05 * math.sin(lt * 14)
            pill = self.txt(('gpill',), lambda: round_rect((560, 200), 100, self.st['pill']))
            place(c, pill, W / 2, 1560, scale=pulse * pin)
            place(c, fill(m, self.st['pill_fg']), W / 2, 1560, scale=pulse * pin)
        else:
            u = lt - t_rev
            pm = self.txt(('gp', i), lambda: _fit(sc['price'], 'Anton', 800, 230, size=230))
            p = prog(u, 0, .16)
            place(c, fill(pm, RED2 if self.st['bg'] != 'cream' else (27, 46, 27)) if self.st['bg'] != 'dark' else gold_fill(pm), W / 2, 1560, scale=lerp(2, 1, ease_in(p)), alpha=clamp(p * 3))
            if sc.get('was'):
                wm = self.txt(('gw', i), lambda: text_mask('was ' + sc['was'], font('dm', 52, 'Medium')))
                wi = fill(wm, self.st['muted']); d = ImageDraw.Draw(wi)
                d.line([(wi.width * .22, wi.height * .55), (wi.width, wi.height * .55)], fill=self.st['muted'] + (255,), width=4)
                place(c, wi, W / 2, 1730, alpha=self.enter(u, .2, .3))
            self.confetti(c, u)
            flash(c, u, 0, peak=.45)
        return c

    def confetti(self, c, u):
        if u > 1.6: return
        if not hasattr(self, '_conf'):
            r = random.Random(7)
            self._conf = [dict(a=r.uniform(-math.pi, 0), v=r.uniform(900, 1900), col=r.choice([GOLD, RED2, (255, 255, 255), TEAL]),
                               s=r.uniform(14, 26), rot=r.uniform(0, 6), vr=r.uniform(-12, 12)) for _ in range(70)]
        d = ImageDraw.Draw(c)
        for p in self._conf:
            x = W / 2 + math.cos(p['a']) * p['v'] * u; y = 1560 + math.sin(p['a']) * p['v'] * u + 1600 * u * u
            if not (0 < x < W and 0 < y < H): continue
            s = p['s']; ang = p['rot'] + p['vr'] * u; dx, dy = math.cos(ang) * s, math.sin(ang) * s * .5
            d.polygon([(x - dx, y - dy), (x + dy, y - dx), (x + dx, y + dy), (x - dy, y + dx)], fill=p['col'] + (int(255 * clamp(1.6 - u)),))

    # ---------------------------------------------------------------- search
    def s_search(self, i, sc, lt, dur):
        c, bgcol = self.bg(i, lt); self.top_logo(c, bgcol)
        q = sc['query']; t_type = min(1.8, dur * .45); n = int(len(q) * clamp(lt / t_type))
        bar = self.txt(('sbar',), lambda: round_rect((940, 140), 70, (255, 255, 255), shadow=14))
        b = bar.copy(); d = ImageDraw.Draw(b); pad = (b.width - 940) // 2
        cx, cy = pad + 80, b.height // 2
        d.ellipse((cx - 24, cy - 30, cx + 18, cy + 12), outline=(110, 110, 110, 255), width=7)
        d.line([(cx + 12, cy + 6), (cx + 34, cy + 28)], fill=(110, 110, 110, 255), width=8)
        f = font('dm', 50, 'Medium'); txt = q[:n]
        x = pad + 140
        if txt:
            m = text_mask(txt, f); s = min(1, 720 / m.width)
            if s < 1: m = m.resize((int(m.width * s), int(m.height * s)), Image.LANCZOS)
            b.alpha_composite(fill(m, (30, 30, 30)), (x, cy - m.height // 2)); x += m.width + 6
        if lt < t_type + .3 or int(lt * 3) % 2 == 0:
            d.line([(x + 4, cy - 34), (x + 4, cy + 34)], fill=IOS_BLUE + (255,), width=5)
        place(c, b, W / 2, 620, scale=ease_back(prog(lt, 0, .3)))
        pr = prog(lt, t_type + .3, .35)
        if pr > 0:
            card = self.txt(('sres', i), lambda: self._result_card(sc))
            place(c, card, W / 2, 1060 + 120 * (1 - ease_out(pr)), alpha=ease_out(pr))
        return c

    def _result_card(self, sc):
        w, h = 940, 520; im = round_rect((w, h), 34, (255, 255, 255), shadow=20); pad = (im.width - w) // 2
        ic = logo_icon(110); im.alpha_composite(ic, (pad + 50, pad + 50))
        t = fill(text_mask(sc.get('result', 'The Eye Centre'), font('Gelasio', 62)), INK); im.alpha_composite(t, (pad + 190, pad + 52))
        u = fill(text_mask(sc.get('url', 'theeyecentre.com'), font('dm', 36, 'Medium')), (26, 115, 82)); im.alpha_composite(u, (pad + 190, pad + 128))
        y = pad + 220
        for line in sc.get('lines', [])[:3]:
            m = text_mask(line, font('dm', 42, 'Medium')); s = min(1, (w - 120) / m.width)
            if s < 1: m = m.resize((int(m.width * s), int(m.height * s)), Image.LANCZOS)
            d = ImageDraw.Draw(im); d.ellipse((pad + 56, y + m.height // 2 - 9, pad + 74, y + m.height // 2 + 9), fill=TEAL + (255,))
            im.alpha_composite(fill(m, (60, 64, 67)), (pad + 100, y)); y += m.height + 40
        return im

    # ---------------------------------------------------------------- sounds for these scenes
    def viral_audio(self, tr, sfx):
        for i, (a, e, sc) in enumerate(self.scenes):
            t = sc['type']; dur = e - a
            if t == 'chat':
                n = len(sc['messages']); per = max(.5, (dur - .4) / n)
                for j, m in enumerate(sc['messages']):
                    me = m.get('from') == 'me'; t0 = a + j * per + (.35 if not me else .1)
                    tr.add(sfx.blip(1500 if me else 1100, .3, .05), t0)
            elif t == 'pov':
                n = len(sc['text'].split()); step = max(.12, min(.22, (dur * .55) / n))
                for j in range(n): tr.add(sfx.click(.35), a + j * step)
            elif t == 'glitch':
                n = len(sc['lines']); per = dur / n
                for j in range(n): tr.add(sfx.snare(.7), a + j * per); tr.add(sfx.impact(.6, .25), a + j * per)
            elif t == 'rate':
                tr.add(sfx.whoosh(.22, .3), a); tr.add(sfx.impact(1.0, .4), a + min(1.1, dur * .45))
            elif t == 'guess':
                tr.add(sfx.riser(dur * .62 - .1, .3), a + .1); tr.add(sfx.impact(.9, .35), a + dur * .62); tr.add(sfx.coin(.35), a + dur * .62)
            elif t == 'search':
                t_type = min(1.8, dur * .45); n = len(sc['query'])
                for j in range(n): tr.add(sfx.click(.3), a + t_type * j / n)
                tr.add(sfx.blip(1320, .25), a + t_type + .3)
