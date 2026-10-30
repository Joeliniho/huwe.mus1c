"""Prueba los tres motores con audios sintéticos (una melodía de guitarra hecha por código)."""
import sys
import time
from pathlib import Path

import numpy as np
import soundfile as sf

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import motores  # noqa: E402

SR = 44100
OUT = Path(__file__).resolve().parent / "salida"
OUT.mkdir(exist_ok=True)


def cuerda(midi, dur, sr=SR):
    """Karplus-Strong: suena a cuerda pulsada."""
    f = 440 * 2 ** ((midi - 69) / 12)
    n = int(sr / f)
    buf = np.random.uniform(-1, 1, n)
    out = np.empty(int(dur * sr))
    for i in range(len(out)):
        out[i] = buf[i % n]
        buf[i % n] = 0.996 * 0.5 * (buf[i % n] + buf[(i + 1) % n])
    return out


def melodia(notas, bpm=100):
    negra = 60 / bpm
    pistas = []
    for n, d in notas:
        pistas.append(cuerda(n, d * negra) if n else np.zeros(int(d * negra * SR)))
    return np.concatenate(pistas)


np.random.seed(1)
riff = [(52, .5), (55, .5), (57, .5), (59, .5), (57, .5), (55, .5), (52, 1), (0, .5),
        (64, .5), (62, .5), (59, .5), (57, .5), (55, .5), (57, 1.5)] * 2
seco = melodia(riff) * 0.3
estereo = np.stack([seco, seco], axis=1)
sf.write(OUT / "riff.wav", estereo, SR)
ref = np.tanh(estereo * 4) * 0.9  # «canción comercial»: más fuerte y saturada
sf.write(OUT / "referencia.wav", np.concatenate([ref, ref]), SR)
ruido = np.random.normal(0, 0.03, len(seco)) + 0.02 * np.sin(2 * np.pi * 50 * np.arange(len(seco)) / SR)
sf.write(OUT / "riff_con_ruido.wav", seco + ruido, SR)

t = time.time()
motores.masterizar(OUT / "riff.wav", OUT / "referencia.wav", OUT / "riff_master.wav", aviso=lambda m: None)
a, _ = sf.read(OUT / "riff.wav")
b, _ = sf.read(OUT / "riff_master.wav")
r, _ = sf.read(OUT / "referencia.wav")
rms = lambda x: 20 * np.log10(np.sqrt(np.mean(x ** 2)))  # noqa: E731
print(f"MASTER  {time.time()-t:.1f}s  original {rms(a):.1f} dB → master {rms(b):.1f} dB (referencia {rms(r):.1f} dB)")

t = time.time()
motores.limpiar(OUT / "riff_con_ruido.wav", OUT / "riff_limpio.wav", aviso=lambda m: None)
sucio = motores.cargar(OUT / "riff_con_ruido.wav", 48000, 1)[:, 0]
limpio, _ = sf.read(OUT / "riff_limpio.wav")
silencio = slice(int(48000 * 2.15), int(48000 * 2.4))  # el hueco del riff
print(f"LIMPIAR {time.time()-t:.1f}s  ruido en el hueco: {rms(sucio[silencio]):.1f} dB → {rms(limpio[silencio]):.1f} dB  GPU={motores.hay_gpu()}")

t = time.time()
midi, tab, n = motores.audio_a_tab(OUT / "riff.wav", OUT, aviso=lambda m: None)
print(f"TAB     {time.time()-t:.1f}s  {n} notas (esperadas {sum(1 for x, _ in riff if x)})")
print(tab.read_text(encoding="utf-8"))
