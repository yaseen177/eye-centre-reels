"""The Eye Centre video engine: JSON spec -> 1080x1920 MP4 with music.

    python3 -I studio/engine.py spec.json out.mp4            # render
    python3 -I studio/engine.py spec.json out.png --frames   # contact sheet of key frames (check before rendering)

Spec:
{
  "style": "gold" | "cream" | "punch",          # gold = black & gold, cream = luxury, punch = red/black/white
  "scenes": [ {"type": ..., "dur": seconds, ...}, ... ]      # dur is rounded to the beat (0.5 s)
}
Scene types (every scene shows the logo at the top; "end" shows it large):
  hook     {"lines": ["STOP", "SCROLLING"]}                  each line slams in on the beat (keep lines 1-3 words)
  big      {"text": "30%", "sub": "OFF DESIGNER FRAMES", "small": "online & in store"}
  product  {"image": "assets/cutouts/x.png", "brand": "GUCCI", "name": "GG2270S", "price": "£350", "was": "£500", "badge": "30% OFF"}
           price/was/badge optional. Only use prices read from Shopify today.
  versus   {"question": "Which would you pick?", "a": {product fields}, "b": {product fields}}
  feature  {"icon": "home|tryon|lens|varifocal|pay|check|calendar|delivery|spark", "title": "...", "sub": "..."}
  list     {"title": "...", "items": ["...", "..."]}         up to 5 short items, revealed one per beat
  + viral formats (chat, pov, glitch, rate, guess, search): see studio/viral.py
  end      {"headline": "...", "sub": "...", "cta": "theeyecentre.com", "small": ["line", "line"]}
"""
import sys, os, json, subprocess, tempfile
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from lib import *
import sfx
from viral import ViralScenes

HERE = os.path.dirname(os.path.abspath(__file__))
RED2 = (214, 32, 44)
STYLES = {
    'gold':  dict(bg='dark', fg=CREAM, accent='gold', muted=(200, 192, 180), card=(255, 255, 255), card_fg=INK, badge_bg=BLACK, badge_fg=GOLD, logo_txt=(255, 255, 255), pill=GOLD, pill_fg=BLACK, head='Anton', music='beat'),
    'punch': dict(bg='punch', fg=(255, 255, 255), accent='red', muted=(200, 200, 200), card=(255, 255, 255), card_fg=BLACK, badge_bg=RED2, badge_fg=(255, 255, 255), logo_txt=(255, 255, 255), pill=(255, 255, 255), pill_fg=BLACK, head='Anton', music='beat'),
    'cream': dict(bg='cream', fg=(27, 46, 27), accent='goldtext', muted=(110, 112, 100), card=(255, 255, 255), card_fg=(27, 46, 27), badge_bg=(27, 46, 27), badge_fg=(245, 241, 232), logo_txt=INK, pill=(27, 46, 27), pill_fg=(245, 241, 232), head='CG500', music='soft'),
}
CREAM_BG = (245, 241, 232)


# ------------------------------------------------------------------ helpers
def accent_fill(mask, st):
    if st['accent'] == 'gold': return gold_fill(mask)
    if st['accent'] == 'goldtext': return gold_fill(mask, top=(200, 170, 110), mid=(138, 118, 80), bot=(96, 80, 50))
    return fill(mask, RED2)

def fit(txt, fname, maxw, maxh, size=400, track=4):
    m = text_mask(txt, font(fname, size) if fname != 'dm' else font('dm', size, 'Bold'), track=track)
    s = min(maxw / m.width, maxh / m.height, 1.0 if size <= 120 else 9)
    return m.resize((max(1, int(m.width * s)), max(1, int(m.height * s))), Image.LANCZOS)

def make_bg(kind):
    if kind == 'dark': return bg_black()
    if kind == 'cream':
        yy, xx = np.mgrid[0:H, 0:W]
        d = np.sqrt(((xx - W / 2) / W) ** 2 + ((yy - H * .45) / H) ** 2); k = np.clip(1 - d * .35, .82, 1)
        arr = np.zeros((H, W, 3))
        for i in range(3): arr[:, :, i] = CREAM_BG[i] * k + (1 - k) * 200
        arr += np.random.default_rng(5).normal(0, 1.6, arr.shape)
        return Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8), 'RGB').convert('RGBA')
    return Image.new('RGBA', (W, H), BLACK + (255,))

ICONS = {}
def icon(name, col, D=280):
    """Simple line icons drawn with PIL."""
    k = (name, col, D)
    if k in ICONS: return ICONS[k]
    S = 4; im = Image.new('RGBA', (D * S, D * S), (0, 0, 0, 0)); d = ImageDraw.Draw(im); c = col + (255,); w = 9 * S
    def P(x, y): return (x * D * S, y * D * S)
    if name == 'home':
        d.line([P(.15, .5), P(.5, .18), P(.85, .5)], fill=c, width=w, joint='curve')
        d.rectangle([P(.25, .48), P(.75, .85)], outline=c, width=w); d.rectangle([P(.43, .62), P(.57, .85)], outline=c, width=w)
    elif name in ('tryon', 'spark'):
        d.ellipse([P(.2, .15), P(.8, .75)], outline=c, width=w)
        for (a, b) in [((.35, .45), (.45, .45)), ((.55, .45), (.65, .45))]: d.line([P(*a), P(*b)], fill=c, width=w)
        d.arc([P(.38, .48), P(.62, .64)], 20, 160, fill=c, width=w)
        d.line([P(.5, .8), P(.5, .92)], fill=c, width=w); d.line([P(.38, .92), P(.62, .92)], fill=c, width=w)
    elif name in ('lens', 'varifocal'):
        d.ellipse([P(.08, .3), P(.45, .7)], outline=c, width=w); d.ellipse([P(.55, .3), P(.92, .7)], outline=c, width=w)
        d.arc([P(.4, .38), P(.6, .55)], 200, 340, fill=c, width=w)
        if name == 'varifocal':
            for x0 in (.12, .59): d.line([P(x0, .52), P(x0 + .3, .52)], fill=c, width=w // 2)
    elif name == 'pay':
        d.rounded_rectangle([P(.12, .25), P(.88, .75)], radius=10 * S, outline=c, width=w)
        d.line([P(.12, .4), P(.88, .4)], fill=c, width=w); d.line([P(.22, .6), P(.45, .6)], fill=c, width=w)
    elif name == 'check':
        d.ellipse([P(.12, .12), P(.88, .88)], outline=c, width=w)
        d.line([P(.3, .52), P(.45, .66), P(.72, .36)], fill=c, width=w, joint='curve')
    elif name == 'calendar':
        d.rounded_rectangle([P(.15, .22), P(.85, .85)], radius=8 * S, outline=c, width=w)
        d.line([P(.15, .4), P(.85, .4)], fill=c, width=w)
        for x in (.32, .68): d.line([P(x, .12), P(x, .3)], fill=c, width=w)
        d.line([P(.35, .62), P(.47, .72), P(.66, .52)], fill=c, width=w, joint='curve')
    elif name == 'delivery':
        d.rectangle([P(.08, .3), P(.6, .68)], outline=c, width=w)
        d.line([P(.6, .42), P(.78, .42), P(.92, .55), P(.92, .68), P(.6, .68)], fill=c, width=w, joint='curve')
        for x in (.25, .75): d.ellipse([P(x - .07, .64), P(x + .07, .78)], outline=c, width=w)
    else:
        star(d, D * S / 2, D * S / 2, D * S * .4, c)
    ICONS[k] = im.resize((D, D), Image.LANCZOS); return ICONS[k]


# ------------------------------------------------------------------ the renderer
class Video(ViralScenes):
    def __init__(self, spec, base_dir):
        self.spec = spec; self.base = base_dir
        self.st = STYLES[spec.get('style', 'gold')]
        self.BG = make_bg(self.st['bg'])
        self.logo = logo_lockup(76, self.st['logo_txt'])
        self.logo_big = logo_lockup(140, self.st['logo_txt'])
        self.logo_dark = logo_lockup(76, INK)
        self.scenes = []; t = 0.0
        for sc in spec['scenes']:
            d = max(1.0, round(float(sc.get('dur', 2.0)) * 2) / 2)
            self.scenes.append((t, t + d, sc)); t += d
        self.total = t
        self.cache = {}
        random.seed(3)
        self.sparks = [dict(x=random.uniform(80, W - 80), y=random.uniform(250, 1500), r=random.uniform(6, 15),
                            ph=random.uniform(0, 6.28), sp=random.uniform(1.5, 3.5), vy=random.uniform(15, 45)) for _ in range(26)]

    # -- shared
    def img(self, path):
        if path not in self.cache:
            p = path if os.path.isabs(path) else os.path.join(self.base, path)
            if not os.path.exists(p): p = os.path.join(HERE, path)
            self.cache[path] = Image.open(p).convert('RGBA')
        return self.cache[path]

    def txt(self, key, fn):
        if key not in self.cache: self.cache[key] = fn()
        return self.cache[key]

    def bg(self, i, lt):
        st = self.st
        if st['bg'] == 'punch':
            cols = [RED2, BLACK, (255, 255, 255)]
            c = Image.new('RGBA', (W, H), cols[i % 3] + (255,))
            return c, cols[i % 3]
        c = self.BG.copy()
        if st['bg'] == 'dark': self.sparkles(c, lt + i * 3, .55)
        return c, None

    def sparkles(self, c, t, alpha):
        layer = Image.new('RGBA', (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(layer)
        for s in self.sparks:
            tw = (math.sin(t * s['sp'] + s['ph']) + 1) / 2; a = int(255 * alpha * tw ** 2)
            if a > 8: star(d, s['x'], (s['y'] - t * s['vy']) % 1500 + 200, s['r'] * (.5 + tw * .6), GOLD_L + (a,))
        c.alpha_composite(layer)

    def fg_on(self, bgcol):
        """text colour for punch backgrounds"""
        if bgcol is None: return self.st['fg']
        return BLACK if bgcol == (255, 255, 255) else (255, 255, 255)

    def head_fill(self, mask, bgcol, accent=False):
        if self.st['bg'] == 'punch':
            if accent and bgcol != RED2: return fill(mask, RED2)
            return fill(mask, self.fg_on(bgcol))
        return accent_fill(mask, self.st) if accent else fill(mask, self.st['fg'])

    def top_logo(self, c, bgcol):
        lg = self.logo_dark if (bgcol == (255, 255, 255) or self.st['bg'] == 'cream') else self.logo
        place(c, lg, W / 2, 190)

    def enter(self, lt, t0=0.0, d=.25):
        return ease_out(prog(lt, t0, d))

    # -- scenes
    def s_hook(self, i, sc, lt, dur):
        lines = sc['lines']; per = max(.5, dur / len(lines))
        k = min(len(lines) - 1, int(lt / per)); u = lt - k * per
        c, bgcol = self.bg(i + k, lt) if self.st['bg'] == 'punch' else self.bg(i, lt)
        self.top_logo(c, bgcol)
        if self.st['bg'] == 'punch':
            m = self.txt(('hook', i, k), lambda: fit(lines[k], 'Anton', 960, 640))
            im = self.head_fill(m, bgcol, accent=(k == len(lines) - 1 and bgcol == (255, 255, 255)))
            p = prog(u, 0, .12); sh = (1 - p) * 14
            place(c, im, W / 2 + math.sin(u * 90) * sh, H / 2 - 40 + math.cos(u * 70) * sh, scale=lerp(1.18, 1, ease_out(p)))
            return c
        fname = self.st['head']
        ms = [self.txt(('hook', i, j), lambda line=line: fit(line, fname, 940, 300 if len(lines) > 1 else 460, size=300)) for j, line in enumerate(lines)]
        gap = 40; total = sum(m.height for m in ms) + gap * (len(ms) - 1); y = 880 - total / 2
        for j, m in enumerate(ms):
            cy = y + m.height / 2; y += m.height + gap
            if j > k: continue
            im = self.head_fill(m, bgcol, accent=(j == len(lines) - 1))
            pj = prog(lt, j * per, .22)
            if self.st['bg'] == 'cream':
                place(c, im, W / 2, cy + 30 * (1 - ease_out(pj)), alpha=ease_out(pj))
            else:
                place(c, im, W / 2, cy, scale=lerp(1.6, 1, ease_in(pj)) if pj < 1 else 1, alpha=clamp(pj * 3))
        if self.st['bg'] == 'dark': flash(c, u, 0, peak=.3)
        return c

    def s_big(self, i, sc, lt, dur):
        c, bgcol = self.bg(i, lt); self.top_logo(c, bgcol)
        m = self.txt(('big', i), lambda: fit(sc['text'], self.st['head'] if self.st['bg'] == 'cream' else 'Anton', 960, 560, size=480))
        im = self.head_fill(m, bgcol, accent=True)
        p = prog(lt, 0, .2)
        if self.st['bg'] == 'cream':
            place(c, im, W / 2, 800, alpha=ease_out(prog(lt, 0, .6)), scale=1 + .02 * ease_out(prog(lt, 0, 2)))
        else:
            place(c, im, W / 2, 800, scale=lerp(2.2, 1, ease_in(p)) if p < 1 else 1 + .04 * math.exp(-(lt - .2) * 8) * math.cos((lt - .2) * 30), alpha=clamp(p * 3))
            if 0 < prog(lt, 1.0, .55) < 1 and self.st['bg'] == 'dark':
                sh = shine(m, prog(lt, 1.0, .55)); c.alpha_composite(sh, (int(W / 2 - sh.width / 2), int(800 - sh.height / 2)))
        if sc.get('sub'):
            ms = self.txt(('bigsub', i), lambda: fit(sc['sub'], 'dm' if self.st['bg'] == 'cream' else 'Anton', 940, 170 if self.st['bg'] != 'cream' else 60, size=170 if self.st['bg'] != 'cream' else 52, track=10 if self.st['bg'] == 'cream' else 6))
            pe = self.enter(lt, .5, .3); place(c, self.head_fill(ms, bgcol), W / 2, 1160 + 30 * (1 - pe), alpha=pe)
        if sc.get('small'):
            mm = self.txt(('bigsmall', i), lambda: text_mask(sc['small'], font('CG500i', 64)))
            pe = self.enter(lt, .8, .4); place(c, fill(mm, self.st['muted'] if bgcol is None else self.fg_on(bgcol)), W / 2, 1290 + 20 * (1 - pe), alpha=pe)
        if self.st['bg'] == 'dark': flash(c, lt, .2, peak=.5)
        return c

    def card(self, prod, w=900, h=760, show_price=True):
        key = ('card', json.dumps(prod, sort_keys=True), w, h)
        if key in self.cache: return self.cache[key]
        st = self.st; cd = round_rect((w, h), 34, st['card'], shadow=26); pad = (cd.width - w) // 2
        im = self.img(prod['image']); s = min((w - 120) / im.width, (h * .55) / im.height)
        im2 = im.resize((int(im.width * s), int(im.height * s)), Image.LANCZOS)
        cd.alpha_composite(im2, (pad + (w - im2.width) // 2, pad + int(h * .1) + int((h * .55 - im2.height) / 2)))
        y = pad + int(h * .7)
        if prod.get('brand'):
            b = fill(text_mask(prod['brand'].upper(), font('dm', 44 if w > 600 else 34, 'Bold'), track=12), st['card_fg']); cd.alpha_composite(b, (pad + (w - b.width) // 2, y)); y += b.height + 14
        if prod.get('name'):
            n = fill(text_mask(prod['name'], font('dm', 34 if w > 600 else 28, 'Medium')), (110, 110, 110)); cd.alpha_composite(n, (pad + (w - n.width) // 2, y)); y += n.height + 16
        if show_price and prod.get('price'):
            pm = fill(text_mask(prod['price'], font('dm', 50 if w > 600 else 40, 'Bold')), RED if prod.get('was') else st['card_fg'])
            if prod.get('was'):
                wm = text_mask(prod['was'], font('dm', 36 if w > 600 else 30)); wi = fill(wm, (150, 150, 150))
                dw = ImageDraw.Draw(wi); dw.line([(0, wi.height * .55), (wi.width, wi.height * .55)], fill=(150, 150, 150, 255), width=3)
                tot = wi.width + 18 + pm.width; x = pad + (w - tot) // 2
                cd.alpha_composite(wi, (x, y + (pm.height - wi.height) // 2)); cd.alpha_composite(pm, (x + wi.width + 18, y))
            else:
                cd.alpha_composite(pm, (pad + (w - pm.width) // 2, y))
        self.cache[key] = cd; return cd

    def badge(self, text, D=250):
        key = ('badge', text, D)
        if key in self.cache: return self.cache[key]
        st = self.st; im = Image.new('RGBA', (D, D), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
        d.ellipse((0, 0, D - 1, D - 1), fill=st['badge_bg'] + (255,))
        d.ellipse((10, 10, D - 11, D - 11), outline=(GOLD if st['bg'] != 'punch' else (255, 255, 255)) + (255,), width=4)
        words = text.split(' ', 1)
        t1 = fill(fit(words[0], 'Anton', D * .7, D * .36, size=200), st['badge_fg'])
        im.alpha_composite(t1, ((D - t1.width) // 2, int(D * (.2 if len(words) > 1 else .32))))
        if len(words) > 1:
            t2 = fill(fit(words[1].upper(), 'Anton', D * .62, D * .2, size=120, track=4), st['badge_fg'] if st['bg'] == 'punch' else CREAM)
            im.alpha_composite(t2, ((D - t2.width) // 2, int(D * .6)))
        self.cache[key] = im; return im

    def s_product(self, i, sc, lt, dur):
        c, bgcol = self.bg(i, lt)
        if self.st['bg'] == 'punch': c = Image.new('RGBA', (W, H), (255, 255, 255, 255)); bgcol = (255, 255, 255)
        self.top_logo(c, bgcol)
        cd = self.card(sc)
        pin = ease_out(prog(lt, 0, .25)); pout = ease_in(prog(lt, dur - .16, .16)) if not sc.get('last') else 0
        if self.st['bg'] == 'cream':
            place(c, cd, W / 2, 1000 - 14 * math.sin(lt / dur * math.pi), alpha=pin * (1 - pout))
            x = W / 2
        else:
            x = W / 2 + (1 - pin) * 900 - pout * 1000
            place_clip(c, cd, x - cd.width / 2, 1000 - cd.height / 2)
        if sc.get('badge'):
            ps = prog(lt, .25, .2)
            if ps > 0: place(c, self.badge(sc['badge']), x + 380, 1000 - 360, scale=ease_back(ps) * .95, rot=12, alpha=1 - pout)
        if sc.get('headline'):
            m = self.txt(('ph', i), lambda: fit(sc['headline'], self.st['head'] if self.st['bg'] == 'cream' else 'Anton', 940, 130, size=150))
            place(c, self.head_fill(m, bgcol, accent=True), W / 2, 420, alpha=self.enter(lt, 0, .3))
        return c

    def s_versus(self, i, sc, lt, dur):
        c, bgcol = self.bg(i, lt)
        if self.st['bg'] == 'punch': c = Image.new('RGBA', (W, H), BLACK + (255,)); bgcol = BLACK
        self.top_logo(c, bgcol)
        q = self.txt(('vq', i), lambda: fit(sc.get('question', 'Which would you pick?'), self.st['head'] if self.st['bg'] == 'cream' else 'Anton', 940, 220, size=150))
        place(c, self.head_fill(q, bgcol, accent=True), W / 2, 420, alpha=self.enter(lt, 0, .3))
        for j, key in enumerate(('a', 'b')):
            cd = self.card(sc[key], w=480, h=640)
            p = ease_out(prog(lt, .3 + j * .3, .3))
            x = (W / 2 - 250) if j == 0 else (W / 2 + 250)
            place(c, cd, x + (1 - p) * (-600 if j == 0 else 600), 1050, alpha=p)
            lab = self.txt(('vl', j), lambda: fill(fit(key.upper(), 'Anton', 120, 120, size=120), self.st['badge_fg']))
            bd = Image.new('RGBA', (130, 130), (0, 0, 0, 0)); ImageDraw.Draw(bd).ellipse((0, 0, 129, 129), fill=self.st['badge_bg'] + (255,))
            bd.alpha_composite(lab, ((130 - lab.width) // 2, (130 - lab.height) // 2))
            place(c, bd, x, 1050 - 330, scale=ease_back(prog(lt, .6 + j * .3, .2)))
        pc = self.enter(lt, 1.4, .4)
        cm = self.txt(('vc', i), lambda: text_mask('Comment A or B 👇'.replace(' 👇', ''), font('dm', 44, 'Bold'), track=4))
        place(c, fill(cm, self.fg_on(bgcol) if bgcol else self.st['fg']), W / 2, 1450, alpha=pc)
        return c

    def s_feature(self, i, sc, lt, dur):
        c, bgcol = self.bg(i, lt); self.top_logo(c, bgcol)
        col = self.fg_on(bgcol) if bgcol else (GOLD if self.st['bg'] == 'dark' else (138, 118, 80))
        if self.st['bg'] == 'punch' and bgcol == (255, 255, 255): col = RED2
        ic = icon(sc.get('icon', 'spark'), col)
        pi = ease_back(prog(lt, 0, .35)); place(c, ic, W / 2, 680, scale=pi)
        t = self.txt(('ft', i), lambda: fit(sc['title'], self.st['head'] if self.st['bg'] == 'cream' else 'Anton', 940, 300, size=140))
        pe = self.enter(lt, .25, .35); place(c, self.head_fill(t, bgcol, accent=False), W / 2, 980 + 30 * (1 - pe), alpha=pe)
        if sc.get('sub'):
            s = self.txt(('fs', i), lambda: fit(sc['sub'], 'CG500i', 900, 200, size=72, track=0))
            pe2 = self.enter(lt, .5, .4)
            place(c, fill(s, self.st['muted'] if bgcol is None else self.fg_on(bgcol)), W / 2, 1180 + 20 * (1 - pe2), alpha=pe2)
        return c

    def s_list(self, i, sc, lt, dur):
        c, bgcol = self.bg(i, lt); self.top_logo(c, bgcol)
        t = self.txt(('lt', i), lambda: fit(sc['title'], self.st['head'] if self.st['bg'] == 'cream' else 'Anton', 940, 220, size=130))
        place(c, self.head_fill(t, bgcol, accent=True), W / 2, 480, alpha=self.enter(lt, 0, .3))
        items = sc['items'][:5]; per = max(.35, (dur - .8) / max(1, len(items)))
        for j, it in enumerate(items):
            p = self.enter(lt, .4 + j * per, .25)
            if p <= 0: continue
            m = self.txt(('li', i, j), lambda: fit(it, 'dm', 880, 64, size=56, track=0))
            col = self.st['fg'] if bgcol is None else self.fg_on(bgcol)
            row = Image.new('RGBA', (min(W - 120, m.width + 90), 80), (0, 0, 0, 0)); d = ImageDraw.Draw(row)
            ac = GOLD if self.st['bg'] == 'dark' else (RED2 if self.st['bg'] == 'punch' else (138, 118, 80))
            d.ellipse((6, 22, 42, 58), fill=ac + (255,)); d.line([(15, 40), (22, 48), (34, 31)], fill=(255, 255, 255, 255), width=5)
            row.alpha_composite(fill(m, col), (70, (80 - m.height) // 2))
            place(c, row, W / 2 + (1 - p) * 60, 700 + j * 130, alpha=p)
        return c

    def s_end(self, i, sc, lt, dur):
        c, bgcol = self.bg(i, lt)
        if self.st['bg'] == 'punch': c = Image.new('RGBA', (W, H), BLACK + (255,)); bgcol = BLACK
        lg = self.logo_big if self.st['bg'] != 'cream' else logo_lockup(140, INK)
        pl = self.enter(lt, 0, .45); place(c, lg, W / 2, 470 + 30 * (1 - pl), alpha=pl)
        if sc.get('headline'):
            m = self.txt(('eh', i), lambda: fit(sc['headline'], self.st['head'] if self.st['bg'] == 'cream' else 'Anton', 940, 150, size=130))
            p = prog(lt, .4, .2)
            place(c, self.head_fill(m, bgcol, accent=True), W / 2, 760, scale=lerp(1.5, 1, ease_in(p)) if (p < 1 and self.st['bg'] != 'cream') else 1, alpha=clamp(p * 3))
        if sc.get('sub'):
            s = self.txt(('es', i), lambda: fit(sc['sub'], 'CG500i', 940, 80, size=58, track=0))
            pe = self.enter(lt, .7, .4); place(c, fill(s, self.st['fg'] if bgcol is None else self.fg_on(bgcol)), W / 2, 900 + 20 * (1 - pe), alpha=pe)
        pp = ease_back(prog(lt, 1.0, .3))
        if pp > 0:
            u = fill(text_mask(sc.get('cta', 'theeyecentre.com'), font('dm', 50, 'Bold'), track=2), self.st['pill_fg'])
            pill = self.txt(('pill',), lambda: round_rect((max(640, u.width + 120), 120), 60, self.st['pill']))
            pill = pill.copy(); pill.alpha_composite(u, ((pill.width - u.width) // 2, (pill.height - u.height) // 2))
            pulse = 1 + .035 * max(0, math.cos((lt - 1) * math.pi * 4)) ** 8 if lt > 1.3 else 1
            place(c, pill, W / 2, 1060, scale=pp * pulse)
        ps = self.enter(lt, 1.3, .5)
        y = 1200
        for j, line in enumerate(sc.get('small', [])[:3]):
            m = self.txt(('esm', i, j), lambda: fit(line, 'dm', 960, 40, size=28, track=0))
            place(c, fill(m, (150, 148, 140)), W / 2, y + j * 42, alpha=ps)
        if self.st['bg'] == 'dark': self.sparkles(c, lt + 50, .4)
        return c

    def frame(self, t):
        for i, (a, b, sc) in enumerate(self.scenes):
            if a <= t < b or i == len(self.scenes) - 1:
                fn = getattr(self, 's_' + sc['type'])
                return fn(i, sc, t - a, b - a)

    # -- audio
    def audio(self, path):
        tr = sfx.Track(self.total)
        soft = self.st['music'] == 'soft'
        roots = [55.0, 43.65, 65.41, 49.0]
        if soft:
            chords = [[110, 130.81, 164.81], [87.31, 110, 130.81], [130.81, 164.81, 196], [98, 123.47, 146.83]]
            t = 0; k = 0
            while t < self.total: tr.add(sfx.pad(chords[k % 4], 2.3, .07), t); t += 2.1; k += 1
        b = 0
        while b * .5 < self.total - .5:
            t = b * .5
            if soft:
                if t >= 2: tr.add(sfx.kick(.4, .12), t)
                if b % 2 and t >= 2: tr.add(sfx.hat(.07), t)
            else:
                tr.add(sfx.kick(.9), t); tr.add(sfx.hat(), t + .25)
                if b % 2: tr.add(sfx.snare(.45), t)
                tr.add(sfx.bass(roots[(b // 4) % 4], .45, .35), t)
            b += 1
        notes = [659.25, 783.99, 880, 987.77, 1046.5, 1174.66]
        for i, (a, e, sc) in enumerate(self.scenes):
            if soft: tr.add(sfx.bell(notes[i % len(notes)], .18, 1.2), a)
            else:
                if sc['type'] in ('hook', 'big', 'end'): tr.add(sfx.impact(.9 if sc['type'] != 'hook' else .6, .35), a + (0.2 if sc['type'] == 'big' else 0))
                if sc['type'] == 'hook':
                    n = len(sc['lines']); per = (e - a) / n
                    for j in range(1, n): tr.add(sfx.impact(.5, .2), a + j * per)
                if sc['type'] == 'product': tr.add(sfx.whoosh(.22, .3), a - .06); tr.add(sfx.blip(), a + .25)
                if sc['type'] == 'list':
                    for j in range(len(sc['items'][:5])): tr.add(sfx.blip(990 + 110 * j, .16), a + .4 + j * max(.35, (e - a - .8) / max(1, len(sc['items'][:5]))))
        self.viral_audio(tr, sfx)
        tr.save(path, fade=.8 if soft else .6, drive=.7 if soft else .9)


def render(spec, out, base_dir):
    v = Video(spec, base_dir)
    tmpd = tempfile.mkdtemp()
    silent = os.path.join(tmpd, 'v.mp4'); wav = os.path.join(tmpd, 'a.wav')
    n = int(round(v.total * FPS))
    p = subprocess.Popen(['ffmpeg', '-y', '-loglevel', 'error', '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-s', f'{W}x{H}', '-r', str(FPS), '-i', '-',
                          '-c:v', 'libx264', '-preset', 'veryfast', '-crf', '19', '-pix_fmt', 'yuv420p', silent], stdin=subprocess.PIPE)
    for i in range(n): p.stdin.write(v.frame(i / FPS).convert('RGB').tobytes())
    p.stdin.close()
    if p.wait() != 0: raise SystemExit('ffmpeg failed')
    v.audio(wav)
    tmp_out = out + '.tmp.mp4'
    subprocess.check_call(['ffmpeg', '-y', '-loglevel', 'error', '-i', silent, '-i', wav, '-map', '0:v', '-map', '1:a', '-c:v', 'copy',
                           '-c:a', 'aac', '-b:a', '192k', '-shortest', '-movflags', '+faststart', tmp_out])
    os.replace(tmp_out, out)
    print(f'rendered {out}  {v.total:.1f}s')


def contact(spec, out, base_dir):
    v = Video(spec, base_dir); fr = []
    for a, b, sc in v.scenes: fr.append(v.frame(a + min(b - a - .05, max(.9, (b - a) * .7))).convert('RGB').resize((270, 480)))
    m = Image.new('RGB', (270 * len(fr), 480))
    for i, f in enumerate(fr): m.paste(f, (i * 270, 0))
    m.save(out); print(f'contact sheet {out}  {len(fr)} scenes, {v.total:.1f}s')


if __name__ == '__main__':
    spec_path, out = sys.argv[1], sys.argv[2]
    spec = json.load(open(spec_path))
    base = os.path.dirname(os.path.abspath(spec_path))
    if '--frames' in sys.argv: contact(spec, out, base)
    else: render(spec, out, base)
