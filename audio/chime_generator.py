import numpy as np, wave

SR = 44100

def tone(freq, dur, harmonics, decay, attack=0.006):
    n = int(SR*dur)
    t = np.arange(n)/SR
    sig = np.zeros(n)
    for mult, amp in harmonics:
        sig += amp*np.sin(2*np.pi*freq*mult*t)
    # exponential decay = bell-like
    env = np.exp(-t*decay)
    # soft attack so there is no click
    a = int(SR*attack)
    if a > 0:
        env[:a] *= np.linspace(0, 1, a)**2
    return sig*env

def silence(dur):
    return np.zeros(int(SR*dur))

def build(pair, gap_in_pair, pause, cycles=4):
    """pair = list of tone arrays making one 'double beep'"""
    seq = []
    for c in range(cycles):
        seq.append(pair[0]); seq.append(silence(gap_in_pair))
        seq.append(pair[1])
        if c < cycles-1:
            seq.append(silence(pause))
    return np.concatenate(seq)

def save(name, sig):
    sig = sig/np.max(np.abs(sig))*0.85
    pcm = (sig*32767).astype(np.int16)
    with wave.open(name,'w') as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR)
        w.writeframes(pcm.tobytes())
    print(name, '%.2fs' % (len(sig)/SR))

# ---- A: rising two-note bell (A5 -> E6). Warm, musical, unmistakably an alert.
H = [(1,1.0),(2,0.35),(3,0.12)]
A = build([tone(880,0.42,H,7.0), tone(1318.5,0.55,H,6.0)], 0.055, 3.0)
save('chimeA_rising_bell.wav', A)

# ---- B: same-note soft double tap (C6). Closer to a classic monitor, softened.
H2 = [(1,1.0),(2,0.22),(4,0.06)]
b1 = tone(1046.5,0.30,H2,11.0); b2 = tone(1046.5,0.30,H2,11.0)
B = build([b1,b2], 0.09, 3.0)
save('chimeB_double_tap.wav', B)

# ---- C: falling two-note (E6 -> A5). Gentler, less urgent.
C = build([tone(1318.5,0.40,H,7.5), tone(880,0.60,H,5.5)], 0.055, 3.0)
save('chimeC_falling_bell.wav', C)
