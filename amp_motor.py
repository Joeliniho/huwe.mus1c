"""Motor del Amplificador: guitarra → pedales (+ plugin VST3) → altavoces, en directo.

Va en un proceso aparte para que la ventana del plugin y el audio no bloqueen la app.
Recibe órdenes en JSON por stdin (una por línea) y contesta en JSON por stdout.
"""
import base64
import json
import math
import queue
import sys
import threading
import time
import traceback

import numpy as np
import pedalboard as pb
import sounddevice as sd
import soundfile as sf

from pedales import PEDALES, por_defecto

# Talk box, trémolo y volumen van aparte (se calculan bloque a bloque), no en la cadena.
APARTE = ("talk", "trem", "master")
ORDEN = [pid for pid, _, _ in PEDALES if pid not in APARTE]
# Formantes (Hz) de las vocales: el talk box pasa de «u» (boca cerrada) a «a» (abierta) según lo fuerte que toques.
VOCAL_U = (320, 800, 2240)
VOCAL_A = (760, 1150, 2500)
ORDEN.insert(ORDEN.index("eq"), "plugin")  # el ampli del plugin va después de los pedales de entrada


MODOS = {"rapido": "WDM-KS", "compatible": "WASAPI"}


def dispositivos(modo="rapido"):
    """«rapido» = WDM-KS (~20 ms ida y vuelta, se queda la tarjeta para él solo);
    «compatible» = WASAPI compartido (~45 ms, convive con el resto de sonidos del PC)."""
    api = next(i for i, h in enumerate(sd.query_hostapis()) if MODOS[modo] in h["name"])
    ent, sal = [], []
    for d in sd.query_devices():
        if d["hostapi"] == api:
            if d["max_input_channels"] > 0:
                ent.append([d["index"], d["name"]])
            if d["max_output_channels"] > 0:
                sal.append([d["index"], d["name"]])
    return ent, sal


def decir(**datos):
    sys.stdout.write(json.dumps(datos) + "\n")
    sys.stdout.flush()


def db(x):
    return 20 * math.log10(max(x, 1e-4))


class Motor:
    def __init__(self):
        self.valores = por_defecto()
        self.cadena = pb.Pedalboard([])
        self.stream = None
        self.plugin = None
        self.plugin_ruta = None
        self.sr = 48000
        self.fase = 0.0
        self.pico_in = self.pico_out = 0.0
        self.grabando = None
        self.fallos = 0
        self.mudo = "--mudo" in sys.argv  # para las pruebas: procesa todo pero no suena
        self.objetos = {
            "gate": [pb.NoiseGate(threshold_db=-58, ratio=10, attack_ms=1, release_ms=90)],
            "comp": [pb.Compressor(threshold_db=-18, ratio=3, attack_ms=6, release_ms=120), pb.Gain(4)],
            "drive": [pb.HighpassFilter(140), pb.Distortion(18), pb.LowpassFilter(4500), pb.Gain(-8)],
            "eq": [pb.LowShelfFilter(200, 0, 0.7), pb.PeakFilter(800, 0, 0.7), pb.HighShelfFilter(3200, 0, 0.7)],
            "cab": [pb.HighpassFilter(80), pb.PeakFilter(120, 2, 1.0), pb.PeakFilter(2400, 3, 1.0),
                    pb.LowpassFilter(5200)],
            "chorus": [pb.Chorus(rate_hz=0.8, depth=0.35, centre_delay_ms=7, feedback=0, mix=0.4)],
            "delay": [pb.Delay(delay_seconds=0.38, feedback=0.3, mix=0.25)],
            "reverb": [pb.Reverb(room_size=0.45, damping=0.5, wet_level=0.22, dry_level=0.9, width=1)],
            "master": [pb.Gain(-6), pb.Limiter(threshold_db=-1, release_ms=80)],
        }
        self.final = pb.Pedalboard(self.objetos["master"])
        self.formantes = [pb.PeakFilter(f, 16, 7.0) for f in VOCAL_U]
        self.boca = pb.Pedalboard([pb.HighpassFilter(180), *self.formantes, pb.LowpassFilter(3800), pb.Gain(-14)])
        self.envolvente = 0.0
        for pid in self.objetos:
            self.aplicar(pid)
        self.rehacer()
        threading.Thread(target=self.medidores, daemon=True).start()

    # ── parámetros ──
    def aplicar(self, pid):
        v, o = self.valores[pid], self.objetos.get(pid)
        if pid == "gate":
            o[0].threshold_db = v["umbral"]
        elif pid == "comp":
            o[0].threshold_db, o[0].ratio, o[1].gain_db = v["umbral"], max(1, v["ratio"]), v["nivel"]
        elif pid == "drive":
            o[1].drive_db, o[2].cutoff_frequency_hz, o[3].gain_db = v["drive"], v["tono"], v["nivel"]
        elif pid == "eq":
            o[0].gain_db, o[1].gain_db, o[2].gain_db = v["graves"], v["medios"], v["agudos"]
        elif pid == "cab":
            o[3].cutoff_frequency_hz = v["brillo"]
        elif pid == "chorus":
            o[0].rate_hz, o[0].depth, o[0].mix = v["vel"], v["prof"] / 100, v["mezcla"] / 100
        elif pid == "delay":
            o[0].delay_seconds, o[0].feedback, o[0].mix = v["tiempo"] / 1000, v["repes"] / 100, v["mezcla"] / 100
        elif pid == "reverb":
            o[0].room_size, o[0].wet_level = v["sala"] / 100, v["mezcla"] / 100 * 0.6
            o[0].dry_level = 1 - v["mezcla"] / 100 * 0.3
        elif pid == "master":
            o[0].gain_db = v["vol"]

    def rehacer(self):
        nueva = []
        for pid in ORDEN:
            if pid == "plugin":
                if self.plugin is not None:
                    nueva.append(self.plugin)
            elif self.valores[pid]["on"]:
                nueva.extend(self.objetos[pid])
        # cadena nueva con los mismos pedales (conservan su estado); el cambio de referencia es atómico
        self.cadena = pb.Pedalboard(nueva)

    def config(self, pedales):
        cambio_on = any(self.valores[p]["on"] != pedales[p]["on"] for p in pedales if p in self.valores)
        for pid, v in pedales.items():
            if pid in self.valores:
                self.valores[pid].update(v)
                self.aplicar(pid)
        if cambio_on:
            self.rehacer()

    # ── audio ──
    def procesar(self, entrada, salida, frames, tiempo, status):
        if status.input_overflow or status.output_underflow:
            self.fallos += 1
        x = entrada[:, :1].T  # la guitarra entra por un canal
        self.pico_in = max(self.pico_in, float(np.abs(x).max()) if frames else 0)
        x = np.repeat(x, 2, axis=0)
        try:
            y = self.cadena.process(x, self.sr, buffer_size=frames, reset=False)
        except Exception:
            y = x * 0
        if y.shape[0] == 1:
            y = np.repeat(y, 2, axis=0)
        t = self.valores["talk"]
        if t["on"]:
            y = self.talk_box(x, y, frames, t)
        v = self.valores["trem"]
        if v["on"]:
            fases = self.fase + np.arange(frames) * v["vel"] / self.sr
            self.fase = float(fases[-1] + v["vel"] / self.sr) % 1.0
            y = y * (1 - v["prof"] / 100 * (0.5 + 0.5 * np.sin(2 * np.pi * fases)))
        y = self.final.process(y.astype(np.float32), self.sr, buffer_size=frames, reset=False)
        salida[:] = 0 if self.mudo else y[:2, :frames].T
        self.pico_out = max(self.pico_out, float(np.abs(y).max()) if frames else 0)
        if self.grabando is not None:
            self.grabando.put(salida.copy())

    def talk_box(self, x, y, frames, t):
        """Envolvente de la púa → abre la «boca» (formantes de u → a): el «uaaa» del talk box."""
        pico = float(np.abs(x).max()) if frames else 0.0
        caida = math.exp(-frames / (self.sr * 0.18))  # la boca se cierra en ~0,2 s
        self.envolvente = max(pico, self.envolvente * caida)
        # sensibilidad: con más, se abre del todo tocando más suave
        umbral = -50 + (100 - t["sens"]) * 0.35
        abierta = min(1.0, max(0.0, (db(self.envolvente) - umbral) / 24)) * t["boca"] / 100
        for f, u, a in zip(self.formantes, VOCAL_U, VOCAL_A):
            f.cutoff_frequency_hz = u + (a - u) * abierta
        h = self.boca.process(y.astype(np.float32), self.sr, buffer_size=frames, reset=False)
        m = t["mezcla"] / 100
        return y * (1 - m) + h * m * 2.2

    def arrancar(self, entrada, salida, buffer, modo="rapido"):
        self.parar()
        extra = None
        if modo == "compatible":
            self.sr = 48000
            extra = (sd.WasapiSettings(auto_convert=True), sd.WasapiSettings(auto_convert=True))
        else:
            self.sr = int(sd.query_devices(salida)["default_samplerate"])
        self.fallos = 0
        self.stream = sd.Stream(device=(entrada, salida), samplerate=self.sr, blocksize=int(buffer),
                                channels=(1, 2), dtype="float32", latency="low", callback=self.procesar,
                                extra_settings=extra)
        self.stream.start()
        lat = (self.stream.latency[0] + self.stream.latency[1]) * 1000
        decir(ok="start", sample_rate=self.sr, latencia_ms=round(lat, 1))

    def parar(self):
        self.parar_grabacion()
        if self.stream is not None:
            try:
                self.stream.stop()
                self.stream.close()
            finally:
                self.stream = None

    def grabar(self, ruta):
        self.parar_grabacion()
        cola = queue.Queue()

        def escribir():
            with sf.SoundFile(ruta, "w", self.sr, 2, "PCM_24") as f:
                while True:
                    bloque = cola.get()
                    if bloque is None:
                        break
                    f.write(bloque)
            decir(ok="grabado", ruta=ruta)
        self.hilo_grab = threading.Thread(target=escribir, daemon=True)
        self.hilo_grab.start()
        self.grabando = cola

    def parar_grabacion(self):
        if self.grabando is not None:
            cola, self.grabando = self.grabando, None
            cola.put(None)
            self.hilo_grab.join(5)

    def medidores(self):
        while True:
            time.sleep(0.05)
            if self.stream is not None:
                decir(nivel=[round(db(self.pico_in), 1), round(db(self.pico_out), 1)], fallos=self.fallos)
                self.pico_in = self.pico_out = 0.0

    def poner_plugin(self, ruta):
        if not ruta:
            self.plugin, self.plugin_ruta = None, None
        else:
            self.plugin = pb.load_plugin(ruta)
            self.plugin_ruta = ruta
        self.rehacer()
        decir(ok="plugin", nombre=self.plugin.name if self.plugin else None)


def main():
    motor = Motor()
    hilo_principal = queue.Queue()
    cerrar_editor = threading.Event()

    def leer():
        for linea in sys.stdin:
            try:
                m = json.loads(linea)
            except ValueError:
                continue
            c = m.get("cmd")
            try:
                if c == "config":
                    motor.config(m["pedales"])
                elif c == "grabar":
                    if m.get("ruta"):
                        motor.grabar(m["ruta"])
                    else:
                        motor.parar_grabacion()
                elif c == "estado":
                    raw = motor.plugin.raw_state if motor.plugin is not None else b""
                    decir(ok="estado", id=m.get("id"), ruta=motor.plugin_ruta,
                          datos=base64.b64encode(raw).decode())
                else:  # lo que toca al audio o al plugin, en el hilo principal
                    if c in ("plugin", "parar", "salir", "arrancar"):
                        cerrar_editor.set()
                    hilo_principal.put(m)
            except Exception as e:
                decir(error=str(e))
        hilo_principal.put({"cmd": "salir"})

    threading.Thread(target=leer, daemon=True).start()
    ent, sal = dispositivos()
    decir(ok="listo", entradas=ent, salidas=sal)
    while True:
        m = hilo_principal.get()
        c = m.get("cmd")
        try:
            if c == "dispositivos":
                ent, sal = dispositivos(m.get("modo", "rapido"))
                decir(ok="dispositivos", entradas=ent, salidas=sal)
            elif c == "arrancar":
                motor.arrancar(m.get("entrada"), m.get("salida"), m.get("buffer", 128), m.get("modo", "rapido"))
            elif c == "parar":
                motor.parar()
                decir(ok="parar")
            elif c == "plugin":
                motor.poner_plugin(m.get("ruta"))
                if m.get("datos") and motor.plugin is not None:
                    motor.plugin.raw_state = base64.b64decode(m["datos"])
            elif c == "editor" and motor.plugin is not None:
                cerrar_editor.clear()
                decir(ok="editor_abierto")
                motor.plugin.show_editor(cerrar_editor)
                decir(ok="editor_cerrado")
            elif c == "salir":
                motor.parar()
                break
        except Exception as e:
            traceback.print_exc(file=sys.stderr)
            decir(error=str(e), cmd=c)


if __name__ == "__main__":
    main()
