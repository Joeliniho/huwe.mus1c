"""Carga real: tarjeta USB en modo rápido, todos los pedales + NAM Rig, en silencio (--mudo). Cuenta cortes."""
import json
import subprocess
import sys
import time
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))
from pedales import por_defecto  # noqa: E402

p = subprocess.Popen([sys.executable, str(RAIZ / "amp_motor.py"), "--mudo"], cwd=RAIZ, stdin=subprocess.PIPE,
                     stdout=subprocess.PIPE, text=True, encoding="utf-8")


def enviar(**m):
    p.stdin.write(json.dumps(m) + "\n")
    p.stdin.flush()


def leer(saltar_niveles=True):
    while True:
        r = json.loads(p.stdout.readline())
        if not (saltar_niveles and "nivel" in r):
            return r


r = leer()
ent = next(i for i, n in r["entradas"] if "USB AUDIO" in n)
sal = next(i for i, n in r["salidas"] if "USB AUDIO" in n)
for buffer in (64, 128, 256):
    enviar(cmd="arrancar", entrada=ent, salida=sal, buffer=buffer, modo="rapido")
    print(buffer, leer())
    v = por_defecto()
    for k in v:
        v[k]["on"] = True
    enviar(cmd="config", pedales=v)
    enviar(cmd="plugin", ruta=r"C:\Program Files\Common Files\VST3\NAM Rig.vst3\Contents\x86_64-win\NAM Rig.vst3")
    leer()
    t = time.time()
    while time.time() - t < 2:
        n = leer(False)
    antes = n.get("fallos", 0)
    while time.time() - t < 12:
        n = leer(False)
    print(f"   cortes con todo cargado: {n['fallos'] - antes} en 10 s (al arrancar: {antes})")
    enviar(cmd="parar")
    leer()
enviar(cmd="salir")
p.wait(10)
