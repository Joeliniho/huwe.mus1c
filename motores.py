"""huwe.mus1c — los tres motores: masterizar, limpiar voz y audio a tablatura.

Licencia: GPLv3 (por Matchering). Ver README.
"""
import os
import subprocess
import sys
import types
from pathlib import Path

import numpy as np
import soundfile as sf

from idioma import L

SIN_VENTANA = 0x08000000 if sys.platform == "win32" else 0
# Empaquetada (PyInstaller) los archivos van en _MEIPASS; si no, junto a este archivo.
BASE = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent))
MODELO_DF = BASE / "modelos" / "DeepFilterNet3"  # incluido para que funcione sin internet


def _ffmpeg():
    import imageio_ffmpeg
    return imageio_ffmpeg.get_ffmpeg_exe()


def cargar(ruta, sr, canales=2):
    """Lee cualquier audio o vídeo (mp3, wav, flac, m4a, mp4…) → array float32 (muestras, canales)."""
    cmd = [_ffmpeg(), "-v", "error", "-i", str(ruta), "-vn", "-f", "f32le",
           "-ac", str(canales), "-ar", str(sr), "-"]
    datos = subprocess.run(cmd, capture_output=True, check=True, creationflags=SIN_VENTANA).stdout
    return np.frombuffer(datos, dtype=np.float32).reshape(-1, canales).copy()


def _a_wav(ruta, carpeta, sr=44100):
    """Matchering quiere WAV: convierte lo que sea a un WAV temporal."""
    destino = Path(carpeta) / (Path(ruta).stem + "_tmp.wav")
    sf.write(destino, cargar(ruta, sr), sr, subtype="FLOAT")
    return destino


def hay_gpu():
    try:
        import torch
        return torch.cuda.is_available()
    except Exception:
        return False


# ───────────────────────── 1. Masterizar con referencia ─────────────────────────

def masterizar(cancion, referencia, salida, aviso=print):
    import matchering as mg
    salida = Path(salida)
    tmp = salida.parent
    aviso(L("Preparando los audios…", "Preparing the audio…"))
    a = _a_wav(cancion, tmp)
    b = _a_wav(referencia, tmp)
    try:
        mg.log(lambda m: aviso(m))
        mg.process(target=str(a), reference=str(b), results=[mg.pcm24(str(salida))])
    finally:
        for f in (a, b):
            f.unlink(missing_ok=True)
    return salida


# ───────────────────────── 2. Limpiar voz y grabaciones ─────────────────────────

_df = None


def _cargar_df():
    """DeepFilterNet 3. Su df.io usa una API vieja de torchaudio: la sustituimos (solo usamos enhance)."""
    global _df
    if _df is None:
        if "torchaudio.backend.common" not in sys.modules:
            import torchaudio  # noqa: F401
            back = types.ModuleType("torchaudio.backend")
            comun = types.ModuleType("torchaudio.backend.common")
            comun.AudioMetaData = object
            back.common = comun
            sys.modules["torchaudio.backend"] = back
            sys.modules["torchaudio.backend.common"] = comun
        import df.logger
        df.logger.get_commit_hash = lambda: None  # llama a git, que no tiene por qué estar instalado
        from df.enhance import enhance, init_df
        propio = None
        if (MODELO_DF / "config.ini").exists():
            # DeepFilterNet puede reescribir su config: se copia a una carpeta con permiso de escritura
            import shutil
            from idioma import CARPETA
            destino = CARPETA / "modelos" / "DeepFilterNet3"
            if not (destino / "config.ini").exists():
                shutil.copytree(MODELO_DF, destino, dirs_exist_ok=True)
            propio = str(destino)
        modelo, estado, _ = init_df(model_base_dir=propio, log_file=None, log_level="ERROR")
        _df = (modelo, estado, enhance)
    return _df


def limpiar(entrada, salida, intensidad=100, aviso=print):
    """intensidad 0-100: 100 = quita todo el ruido que pueda; menos = más natural."""
    import torch
    aviso(L("Cargando la IA de limpieza…", "Loading the cleanup AI…"))
    modelo, estado, enhance = _cargar_df()
    sr = estado.sr()
    audio = cargar(entrada, sr, canales=1)[:, 0]
    aviso(L("Limpiando", "Cleaning") + f" ({'GPU' if hay_gpu() else 'CPU'})…")
    # Límite de atenuación: con 100 no hay límite; con 0 apenas toca nada.
    limite = None if intensidad >= 100 else 6 + intensidad * 0.5
    trozo = sr * 60  # de minuto en minuto para no llenar la memoria
    partes = []
    for i in range(0, len(audio), trozo):
        t = torch.from_numpy(audio[i:i + trozo]).unsqueeze(0)
        with torch.no_grad():
            partes.append(enhance(modelo, estado, t, atten_lim_db=limite).squeeze(0).cpu().numpy())
        aviso(f"{min(100, int((i + trozo) / len(audio) * 100))} %")
    limpio = np.concatenate(partes)
    sf.write(salida, limpio, sr, subtype="PCM_24")
    return Path(salida)


# ───────────────────────── 3. Audio a MIDI y tablatura ─────────────────────────

AFINACION = [40, 45, 50, 55, 59, 64]  # E2 A2 D3 G3 B3 E4 (6.ª → 1.ª)
NOMBRES = ["E", "A", "D", "G", "B", "e"]
TRASTES = 22


def a_notas(entrada, carpeta, aviso=print):
    os.environ.setdefault("TF_CPP_MIN_LOG_LEVEL", "3")
    from basic_pitch import ICASSP_2022_MODEL_PATH, FilenameSuffix, build_icassp_2022_model_path
    from basic_pitch.inference import predict
    try:  # ONNX: no necesita TensorFlow (la versión instalable va sin él)
        import onnxruntime  # noqa: F401
        ICASSP_2022_MODEL_PATH = build_icassp_2022_model_path(FilenameSuffix.onnx)
    except ImportError:
        pass
    carpeta = Path(carpeta)
    aviso(L("Escuchando las notas…", "Listening for notes…"))
    wav = _a_wav(entrada, carpeta, sr=22050)
    try:
        _, midi, notas = predict(str(wav), ICASSP_2022_MODEL_PATH,
                                 minimum_note_length=80, minimum_frequency=70, maximum_frequency=1400)
    finally:
        wav.unlink(missing_ok=True)
    ruta_midi = carpeta / (Path(entrada).stem + ".mid")
    midi.write(str(ruta_midi))
    notas = sorted((float(n[0]), float(n[1]), int(n[2]), float(n[3])) for n in notas)
    return ruta_midi, quitar_armonicos(notas)


ARMONICOS = {12, 19, 24, 28, 31, 34, 36}  # octava, quinta+octava, 2 octavas…


def quitar_armonicos(notas):
    """Basic Pitch a veces oye los armónicos de una cuerda como notas aparte (más flojas): fuera."""
    buenas = []
    for ini, fin, nota, amp in notas:
        tapada = any(abs(ini - i2) < 0.06 and (nota - n2) in ARMONICOS and amp < a2 * 0.75
                     for i2, _, n2, a2 in notas)
        if not tapada:
            buenas.append((ini, fin, nota, amp))
    return buenas


def _posiciones(nota):
    return [(c, nota - abierta) for c, abierta in enumerate(AFINACION) if 0 <= nota - abierta <= TRASTES]


def a_tablatura(notas, tempo=None, por_linea=16):
    """Elige cuerda y traste para cada nota buscando el camino que menos mueve la mano."""
    if not notas:
        return L("(no se han detectado notas)", "(no notes detected)")
    # Agrupa notas que suenan a la vez (acordes) en golpes.
    golpes = []
    for ini, fin, nota, amp in notas:
        if golpes and ini - golpes[-1][0] < 0.035:
            golpes[-1][1].append(nota)
        else:
            golpes.append([ini, [nota]])

    def opciones(grupo):
        # Cada nota de un acorde en una cuerda distinta; si no cabe, se quitan las más agudas.
        grupo = sorted(set(grupo))[:6]
        res = []

        def rec(i, usadas, acc):
            if len(res) > 60:
                return
            if i == len(grupo):
                res.append(tuple(acc))
                return
            for c, t in _posiciones(grupo[i]):
                if c not in usadas:
                    rec(i + 1, usadas | {c}, acc + [(c, t)])
        rec(0, frozenset(), [])
        return res or [tuple()]

    def coste_forma(f):
        pis = [t for _, t in f if t > 0]
        abierto = sum(1 for _, t in f if t == 0)
        ancho = (max(pis) - min(pis)) if pis else 0
        return (ancho * 3 if ancho <= 4 else 50) + (sum(pis) / len(pis) if pis else 0) * 0.15 - abierto * 0.3

    def centro(f):
        pis = [t for _, t in f if t > 0]
        return sum(pis) / len(pis) if pis else None

    # Programación dinámica (Viterbi) sobre las formas posibles de cada golpe.
    capas = [opciones(g[1]) for g in golpes]
    costes = [coste_forma(f) for f in capas[0]]
    atras = []
    for k in range(1, len(capas)):
        nuevos, ptrs = [], []
        for f in capas[k]:
            cf, mejor, idx = centro(f), None, 0
            for j, fa in enumerate(capas[k - 1]):
                ca = centro(fa)
                salto = abs(cf - ca) if cf is not None and ca is not None else 0
                v = costes[j] + salto * 1.2
                if mejor is None or v < mejor:
                    mejor, idx = v, j
            nuevos.append(mejor + coste_forma(f))
            ptrs.append(idx)
        costes = nuevos
        atras.append(ptrs)
    i = int(np.argmin(costes))
    elegidas = [None] * len(capas)
    for k in range(len(capas) - 1, -1, -1):
        elegidas[k] = capas[k][i]
        if k:
            i = atras[k - 1][i]

    # Rejilla: semicorcheas si sabemos el tempo; si no, cada golpe una columna.
    if tempo:
        paso = 60 / tempo / 4
        columnas = {}
        for (ini, _), forma in zip(golpes, elegidas):
            col = int(round((ini - golpes[0][0]) / paso))
            columnas.setdefault(col, forma)
        total = max(columnas) + 1
        secuencia = [columnas.get(c) for c in range(total)]
    else:
        secuencia = elegidas
        por_linea = 24

    lineas = []
    for base in range(0, len(secuencia), por_linea):
        trozo = secuencia[base:base + por_linea]
        filas = []
        for cuerda in range(5, -1, -1):
            celdas = []
            for forma in trozo:
                t = dict(forma).get(cuerda) if forma else None
                celdas.append(f"{t}".ljust(2, "-") if t is not None else "--")
            filas.append(f"{NOMBRES[cuerda]}|" + "-".join(celdas) + "-|")
        lineas.append("\n".join(filas))
    return "\n\n".join(lineas)


def calcular_tempo(entrada):
    try:
        import librosa
        y = cargar(entrada, 22050, canales=1)[:, 0]
        tempo, _ = librosa.beat.beat_track(y=y, sr=22050)
        tempo = float(np.atleast_1d(tempo)[0])
        while tempo > 160:  # el detector suele dar el doble
            tempo /= 2
        while tempo < 60:
            tempo *= 2
        return round(tempo)
    except Exception:
        return None


def audio_a_tab(entrada, carpeta, aviso=print):
    carpeta = Path(carpeta)
    ruta_midi, notas = a_notas(entrada, carpeta, aviso)
    aviso(L("Buscando el tempo…", "Finding the tempo…"))
    tempo = calcular_tempo(entrada)
    aviso(L("Colocando las notas en el mástil…", "Placing the notes on the fretboard…"))
    tab = a_tablatura(notas, tempo)
    cab = (f"{Path(entrada).name}\n" + L("Afinación estándar (EADGBE)", "Standard tuning (EADGBE)")
           + (L(f" · tempo ≈ {tempo:.0f} BPM · cada guion = semicorchea",
                f" · tempo ≈ {tempo:.0f} BPM · each dash = 16th note") if tempo else "") + "\n\n")
    ruta_tab = carpeta / (Path(entrada).stem + L(" - tablatura.txt", " - tab.txt"))
    ruta_tab.write_text(cab + tab + "\n", encoding="utf-8")
    return ruta_midi, ruta_tab, len(notas)
