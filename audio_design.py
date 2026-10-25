"""Original royalty-free procedural mystery BGM and contextual SFX.

No repetitive pops. One deep impact at 3.0s, soft ambient swells at
selected B-roll cuts. Outputs mono WAV, 44.1 kHz for existing FFmpeg mixer.
"""
import numpy as np

RATE = 44100


def fade_envelope(count, seconds=1.2):
    x = np.ones(count, dtype=np.float32)
    fade = min(count//2, int(seconds*RATE))
    if fade > 1:
        x[:fade] = np.linspace(0,1,fade)
        x[-fade:] = np.linspace(1,0,fade)
    return x


def mystery_bed(duration, rate=RATE):
    """Evolving suspense: low drone, minor intervals, breath-like slow swells."""
    n = int((duration+.15)*rate)
    t = np.arange(n, dtype=np.float32)/rate
    frequencies = (55, 65.406, 82.407, 110)
    harmonics = sum(np.sin(2*np.pi*f*t + i*.6)*(0.12/(i+1))
                    for i,f in enumerate(frequencies))
    pulsation = .70+.30*np.sin(2*np.pi*.22*t)
    filtered = np.sin(2*np.pi*130*t + 1.8*np.sin(2*np.pi*.09*t))*.016
    bed = (harmonics*pulsation+filtered)*fade_envelope(n)
    return np.clip(bed, -.8, .8).astype('float32')


def fx_track(duration, cuts, rate=RATE):
    n = int((duration+.15)*rate)
    out = np.zeros(n,dtype=np.float32)
    def insert(at, sound):
        start=int(at*rate)
        if start >= n or start<0: return
        size=min(len(sound),n-start)
        out[start:start+size]+=sound[:size].astype(np.float32)

    # Hook ending: cinematic bass impact with a short distorted low thud.
    impact_length=int(.9*rate)
    t=np.arange(impact_length,dtype=np.float32)/rate
    freq_phase=2*np.pi*(95*t-36*t*t)
    impact=(.33*np.sin(freq_phase)+.12*np.sin(2*np.pi*42*t))
    impact*=np.exp(-6*t)
    insert(3.0,impact)

    # Sparse gentle "ocean air" at selected scene transitions.
    useful=[c for i,c in enumerate(cuts) if i>0 and i%3==0]
    for index, at in enumerate(useful):
        length=int(.45*rate)
        x=np.arange(length,dtype=np.float32)/rate
        rng=np.random.default_rng(850+index)
        noise=rng.normal(0,1,length).astype('float32')
        smoothing=np.convolve(noise,np.ones(160,dtype=np.float32)/160,
                              mode='same')
        air=.28*smoothing*np.sin(np.pi*x/.45)**2
        insert(at,air)
    return np.clip(out,-.85,.85)


def make_soundtracks(duration, cuts, writer, work):
    writer(work/'music.wav', mystery_bed(duration), RATE)
    writer(work/'effects.wav', fx_track(duration,cuts), RATE)
