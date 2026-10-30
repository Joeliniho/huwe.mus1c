"""Abre la ventana, hace las herramientas con los audios de prueba y guarda capturas.

Uso: probar_ventana.py [en|es]   (el Amplificador no se enciende: sonaría el micro por los altavoces)
"""
import importlib.util
import sys
import time
from pathlib import Path

AQUI = Path(__file__).resolve().parent
sys.path.insert(0, str(AQUI.parent))
import idioma  # noqa: E402

idioma.ACTUAL = sys.argv[1] if len(sys.argv) > 1 else "en"
spec = importlib.util.spec_from_file_location("app", AQUI.parent / "huwe.mus1c.pyw")
app_mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(app_mod)

from PySide6.QtWidgets import QApplication  # noqa: E402

SAL = AQUI / "salida"
CAP = AQUI / "capturas"
CAP.mkdir(exist_ok=True)
LANG = idioma.ACTUAL

app = QApplication(sys.argv)
app.setStyleSheet(app_mod.ESTILO)
v = app_mod.Ventana()
v.show()


def esperar(seg=0.5, hasta=None):
    t = time.time()
    while time.time() - t < seg or (hasta and not hasta()):
        app.processEvents()
        time.sleep(0.02)
        if time.time() - t > 300:
            raise TimeoutError


esperar(3)  # el motor del ampli arranca y manda los dispositivos
v.grab().save(str(CAP / f"{LANG}_0_amp.png"))
amp = v.paginas.widget(0)
amp.tono.setCurrentIndex(1)
amp.cargar_tono()
esperar(0.5)
v.grab().save(str(CAP / f"{LANG}_0_amp_tremolo.png"))
print("entrada:", amp.entrada.currentText(), "| salida:", amp.salida.currentText(), "|", amp.estado.text())

trabajos = [
    (1, lambda p: (p.cancion.poner(SAL / "riff.wav"), p.ref.poner(SAL / "referencia.wav"))),
    (2, lambda p: p.audio.poner(SAL / "riff_con_ruido.wav")),
    (3, lambda p: p.audio.poner(SAL / "riff.wav")),
]
for i, preparar in trabajos:
    v.lista.setCurrentRow(i)
    p = v.paginas.widget(i)
    preparar(p)
    esperar(0.3)
    p.lanzar()
    esperar(0.2, hasta=lambda: p.hilo is None)
    esperar(0.8)
    print(i, p.estado.text())
    v.grab().save(str(CAP / f"{LANG}_{i}_hecho.png"))
amp.cerrar()
sys.stdout.flush()
v.close()
