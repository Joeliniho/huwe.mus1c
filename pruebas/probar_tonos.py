"""Pasa el riff de prueba por cada tono de fábrica (sin tarjeta de sonido) y guarda un WAV por tono."""
import sys
import types
from pathlib import Path

import numpy as np
import soundfile as sf

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))
import amp_motor  # noqa: E402
from pedales import FABRICA  # noqa: E402

SAL = RAIZ / "pruebas" / "salida" / "tonos"
SAL.mkdir(parents=True, exist_ok=True)
x, sr = sf.read(RAIZ / "pruebas" / "salida" / "riff.wav", dtype="float32")
x = x[:, :1] * 1.5
ok = types.SimpleNamespace(input_overflow=False, output_underflow=False)
for t in FABRICA:
    m = amp_motor.Motor()
    m.sr = sr
    m.config(t["pedales"])
    salida, B = [], 128
    for i in range(0, len(x) - B, B):
        out = np.zeros((B, 2), np.float32)
        m.procesar(x[i:i + B], out, B, None, ok)
        salida.append(out)
    y = np.concatenate(salida)
    nombre = t["nombre"][1]
    sf.write(SAL / f"{nombre}.wav", y, sr)
    pico = 20 * np.log10(np.abs(y).max() + 1e-9)
    rms = 20 * np.log10(np.sqrt(np.mean(y ** 2)) + 1e-9)
    print(f"{nombre:16s} pico {pico:6.1f} dB · media {rms:6.1f} dB · NaN: {bool(np.isnan(y).any())}")
