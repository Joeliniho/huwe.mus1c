"""Prueba el motor del Amplificador con dispositivos virtuales (Steam), para que no suene nada en casa."""
import json
import subprocess
import sys
import time
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
p = subprocess.Popen([sys.executable, str(RAIZ / "amp_motor.py")], cwd=RAIZ, stdin=subprocess.PIPE,
                     stdout=subprocess.PIPE, text=True, encoding="utf-8")


def enviar(**m):
    p.stdin.write(json.dumps(m) + "\n")
    p.stdin.flush()


def leer():
    while True:
        r = json.loads(p.stdout.readline())
        if "nivel" not in r:
            break
    print("←", {k: (v if k not in ("datos",) else f"{len(v)} chars") for k, v in r.items()})
    return r


r = leer()
ent = next(i for i, n in r["entradas"] if "Steam" in n)
sal = next(i for i, n in r["salidas"] if "Steam Streaming Speakers" in n)
enviar(cmd="arrancar", entrada=ent, salida=sal, buffer=256)
while "nivel" in (r := leer()):
    pass
enviar(cmd="grabar", ruta=str(Path(__file__).parent / "salida" / "grabacion_amp.wav"))
from pedales import por_defecto  # noqa: E402
sys.path.insert(0, str(RAIZ))
v = por_defecto()
v["drive"]["on"] = True
v["trem"]["on"] = True
enviar(cmd="config", pedales=v)
time.sleep(0.5)
for nombre in ("TONE3000", "NAM Rig"):
    enviar(cmd="plugin", ruta=rf"C:\Program Files\Common Files\VST3\{nombre}.vst3\Contents\x86_64-win\{nombre}.vst3")
    leer()
    enviar(cmd="estado", id=1)
    leer()
time.sleep(1)
enviar(cmd="plugin", ruta=None)
leer()
enviar(cmd="parar")
leer()
enviar(cmd="salir")
p.wait(10)
print("salida", p.returncode)
