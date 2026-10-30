"""Prueba el motor del Amplificador dentro del .exe empaquetado (en silencio, con --mudo)."""
import json
import subprocess
import sys
import time

exe = sys.argv[1]
p = subprocess.Popen([exe, "--amp-motor", "--mudo"], stdin=subprocess.PIPE, stdout=subprocess.PIPE, text=True,
                     encoding="utf-8")


def enviar(**m):
    p.stdin.write(json.dumps(m) + "\n")
    p.stdin.flush()


def leer():
    while True:
        r = json.loads(p.stdout.readline())
        if "nivel" not in r:
            return r


r = leer()
print("dispositivos:", len(r["entradas"]), "entradas,", len(r["salidas"]), "salidas")
ent = next(i for i, n in r["entradas"] if "USB AUDIO" in n)
sal = next(i for i, n in r["salidas"] if "USB AUDIO" in n)
enviar(cmd="arrancar", entrada=ent, salida=sal, buffer=128)
print(leer())
enviar(cmd="plugin", ruta=r"C:\Program Files\Common Files\VST3\TONE3000.vst3\Contents\x86_64-win\TONE3000.vst3")
print(leer())
time.sleep(2)
enviar(cmd="parar")
print(leer())
enviar(cmd="salir")
p.wait(10)
print("salida", p.returncode)
