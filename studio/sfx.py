import numpy as np, wave
SR = 44100
rng = np.random.default_rng(11)

class Track:
    def __init__(self, dur): self.N = int(SR * dur); self.out = np.zeros(self.N)
    def add(self, sig, t):
        i = int(t * SR)
        if i >= self.N or i < 0: return
        j = min(self.N, i + len(sig)); self.out[i:j] += sig[:j - i]
    def save(self, path, fade=0.6, drive=0.9):
        o = np.tanh(self.out * drive); fl = int(fade * SR)
        o[-fl:] *= np.linspace(1, 0, fl); o = o / (np.max(np.abs(o)) + 1e-9) * .89
        with wave.open(path, 'wb') as w:
            w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR); w.writeframes((o * 32767).astype(np.int16).tobytes())

def env(n, a=.002, d=.2):
    t = np.arange(n) / SR; return np.minimum(1, t / a) * np.exp(-t / d)

def kick(g=1.0, d=.16):
    n = int(.4 * SR); t = np.arange(n) / SR; f = 45 + 110 * np.exp(-t * 28)
    return np.sin(2 * np.pi * np.cumsum(f) / SR) * env(n, .001, d) * g

def snare(g=.6):
    n = int(.25 * SR); t = np.arange(n) / SR; s = rng.standard_normal(n)
    s = s - np.convolve(s, np.ones(40) / 40, 'same')
    return (s * env(n, .001, .07) + np.sin(2 * np.pi * 190 * t) * env(n, .001, .05) * .6) * g

def hat(g=.15):
    n = int(.06 * SR); s = rng.standard_normal(n); s = s - np.convolve(s, np.ones(4) / 4, 'same')
    return s * env(n, .0005, .015) * g

def bass(freq, dur, g=.42):
    n = int(dur * SR); t = np.arange(n) / SR
    s = np.sin(2 * np.pi * freq * t) + .3 * np.sin(2 * np.pi * freq * 2 * t)
    return s * np.minimum(1, t / .01) * np.exp(-t / (dur * .7)) * g

def impact(g=1.0, d=.5):
    n = int(1.4 * SR); t = np.arange(n) / SR
    low = np.sin(2 * np.pi * (38 + 60 * np.exp(-t * 9)) * t) * np.exp(-t / d)
    nz = np.convolve(rng.standard_normal(n), np.ones(30) / 30, 'same') * np.exp(-t / .18)
    return (low * .9 + nz * .9) * g

def whoosh(dur=.26, g=.35):
    n = int(dur * SR); t = np.arange(n) / SR; nz = rng.standard_normal(n)
    k = np.linspace(40, 4, n); o = np.zeros(n); acc = 0
    for i in range(n): acc += (nz[i] - acc) / k[i]; o[i] = acc
    return o * np.sin(np.pi * t / dur) ** 2 * g * 3

def blip(f0=1320, g=.22, d=.04):
    n = int(.15 * SR); t = np.arange(n) / SR
    return np.sin(2 * np.pi * (f0 - 500 * t / .15) * t) * env(n, .001, d) * g

def click(g=.4):
    n = int(.03 * SR); return rng.standard_normal(n) * env(n, .0003, .004) * g

def riser(dur, g=.25):
    n = int(dur * SR); t = np.arange(n) / SR; f = 200 + 1600 * (t / dur) ** 2
    return (np.sin(2 * np.pi * np.cumsum(f) / SR) * .4 + rng.standard_normal(n) * .3) * (t / dur) ** 2 * g

def bell(freq, g=.3, d=1.2):
    n = int(d * 1.5 * SR); t = np.arange(n) / SR
    s = sum(a * np.sin(2 * np.pi * freq * m * t) * np.exp(-t / (d / m ** .5)) for m, a in [(1, 1), (2.01, .45), (3.0, .2), (4.2, .1)])
    return s * np.minimum(1, t / .004) * g

def pad(freqs, dur, g=.12):
    n = int(dur * SR); t = np.arange(n) / SR
    s = sum(np.sin(2 * np.pi * f * t) + .3 * np.sin(2 * np.pi * f * 2.003 * t) for f in freqs)
    e = np.minimum(1, t / .6) * np.minimum(1, (dur - t) / .8)
    return s * e * g

def coin(g=.25):
    n = int(.35 * SR); t = np.arange(n) / SR
    f = np.where(t < .06, 1975, 2637)
    return np.sign(np.sin(2 * np.pi * np.cumsum(f) / SR)) * env(n, .001, .12) * g * .5
