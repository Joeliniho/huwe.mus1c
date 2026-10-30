"""huwe.mus1c — estudio de audio todo en uno, gratis y de código abierto.

Amplificador de guitarra en directo · Masterizar con referencia · Limpiar voz y ruido ·
Audio a MIDI y tablatura. Inglés y español. Licencia GPLv3.
"""
import json
import os
import re
import sys
import time
import traceback
from pathlib import Path

os.environ.setdefault("TF_CPP_MIN_LOG_LEVEL", "3")
if "--amp-motor" not in sys.argv:  # el .exe sin consola no tiene stdout/stderr y algunas librerías escriben ahí
    for _n in ("stdout", "stderr"):
        if getattr(sys, _n) is None:
            setattr(sys, _n, open(os.devnull, "w", encoding="utf-8"))

from PySide6.QtCore import QProcess, QRectF, Qt, QThread, QTimer, QUrl, Signal
from PySide6.QtGui import QColor, QDesktopServices, QFont, QIcon, QPainter, QPen, QPixmap
import sounddevice as sd
from PySide6.QtWidgets import (QApplication, QComboBox, QFileDialog, QFrame, QGridLayout,
                               QHBoxLayout, QInputDialog, QLabel, QListWidget, QListWidgetItem,
                               QMainWindow, QMessageBox, QPlainTextEdit, QProgressBar, QPushButton,
                               QScrollArea, QSizePolicy, QSlider, QStackedWidget, QVBoxLayout,
                               QWidget)

AQUI = Path(__file__).resolve().parent
sys.path.insert(0, str(AQUI))
import idioma  # noqa: E402
import motores  # noqa: E402
from idioma import L  # noqa: E402
from pedales import FABRICA, PEDALES, por_defecto  # noqa: E402

NOMBRE = "huwe.mus1c"
VERSION = "0.3"
EXTENSIONES = {".wav", ".mp3", ".flac", ".ogg", ".m4a", ".aac", ".aiff", ".aif", ".wma",
               ".opus", ".mp4", ".mov", ".mkv", ".webm"}
FILTRO = L("Audio o vídeo", "Audio or video") + " (" + " ".join("*" + e for e in sorted(EXTENSIONES)) + \
    ");;" + L("Todo", "All files") + " (*.*)"
CARPETA_VST3 = Path(os.environ.get("COMMONPROGRAMFILES", r"C:\Program Files\Common Files")) / "VST3"
TONOS = idioma.CARPETA / "tones"
GRABACIONES = Path.home() / "Music" / NOMBRE
# Amplis gratis recomendados: (nombre, web oficial)
AMPLIS = [("TONE3000", "https://www.tone3000.com/plugin"),
          ("NAM Rig", "https://www.tone3000.com/blog/jordan-valeriote-nam-rig")]

FONDO, PANEL, PANEL2, BORDE = "#0f1012", "#17181c", "#1e2025", "#2a2d34"
TEXTO, TENUE, ACENTO, ACENTO2 = "#ececef", "#8a8d97", "#ff8a3d", "#ffb37f"

ESTILO = f"""
* {{ font-family: 'Segoe UI'; color: {TEXTO}; }}
QMainWindow, #raiz, QScrollArea, #pagina {{ background: {FONDO}; border: none; }}
#lateral {{ background: {PANEL}; border-right: 1px solid {BORDE}; }}
#marca {{ font-size: 22px; font-weight: 800; letter-spacing: 0.5px; }}
#marca2 {{ color: {TENUE}; font-size: 12px; }}
QListWidget {{ background: transparent; border: none; outline: 0; font-size: 15px; }}
QListWidget::item {{ padding: 12px 14px; border-radius: 10px; margin: 2px 0; color: {TENUE}; }}
QListWidget::item:hover {{ background: {PANEL2}; color: {TEXTO}; }}
QListWidget::item:selected {{ background: {PANEL2}; color: {TEXTO}; border-left: 3px solid {ACENTO}; }}
#pie {{ color: {TENUE}; font-size: 11px; }}
#titulo {{ font-size: 28px; font-weight: 800; }}
#subtitulo {{ color: {TENUE}; font-size: 14px; }}
#seccion {{ color: {TENUE}; font-size: 11px; font-weight: 700; letter-spacing: 1px; }}
#zona {{ background: {PANEL}; border: 2px dashed {BORDE}; border-radius: 14px; }}
#zona[lleno="true"] {{ border: 1px solid {BORDE}; }}
#zona[encima="true"] {{ border: 2px dashed {ACENTO}; background: #1f1813; }}
#zonaTitulo {{ font-size: 15px; font-weight: 700; }}
#zonaAyuda {{ color: {TENUE}; font-size: 13px; }}
#tarjeta {{ background: {PANEL}; border: 1px solid {BORDE}; border-radius: 14px; }}
#pedal {{ background: {PANEL}; border: 1px solid {BORDE}; border-radius: 14px; }}
#pedal[on="true"] {{ border: 1px solid #5a3a22; background: #1b1714; }}
#pedalNombre {{ font-size: 14px; font-weight: 800; }}
#aviso {{ color: #ffcf8a; font-size: 12px; }}
QPushButton {{ background: {PANEL2}; border: 1px solid {BORDE}; border-radius: 9px;
              padding: 9px 16px; font-size: 13px; font-weight: 600; }}
QPushButton:hover {{ border-color: #444852; }}
QPushButton:disabled {{ color: #55585f; }}
QPushButton#principal {{ background: {ACENTO}; color: #1a0e05; border: none; font-size: 15px;
                        font-weight: 800; padding: 13px 26px; }}
QPushButton#principal:hover {{ background: {ACENTO2}; }}
QPushButton#principal:disabled {{ background: #3a2c22; color: #7c6a5c; }}
QPushButton#principal:checked {{ background: #3ddc84; color: #04180c; }}
QPushButton#ab {{ min-width: 110px; }}
QPushButton#ab:checked {{ background: {ACENTO}; color: #1a0e05; border: none; }}
QPushButton#led {{ min-width: 18px; max-width: 18px; min-height: 18px; max-height: 18px; padding: 0;
                  border-radius: 9px; background: #2c2e35; border: 1px solid #3a3d46; }}
QPushButton#led:checked {{ background: {ACENTO}; border: 1px solid {ACENTO2}; }}
QPushButton#grabar:checked {{ background: #e5484d; color: white; border: none; }}
QComboBox {{ background: {PANEL2}; border: 1px solid {BORDE}; border-radius: 8px; padding: 7px 10px;
            font-size: 13px; min-width: 150px; }}
QComboBox QAbstractItemView {{ background: {PANEL2}; border: 1px solid {BORDE};
                               selection-background-color: #3a2c22; }}
QComboBox::drop-down {{ border: none; width: 22px; }}
QProgressBar {{ background: {PANEL2}; border: none; border-radius: 4px; height: 8px; }}
QProgressBar::chunk {{ background: {ACENTO}; border-radius: 4px; }}
QSlider::groove:horizontal {{ height: 6px; background: {PANEL2}; border-radius: 3px; }}
QSlider::sub-page:horizontal {{ background: {ACENTO}; border-radius: 3px; }}
QSlider::handle:horizontal {{ background: {TEXTO}; width: 16px; margin: -6px 0; border-radius: 8px; }}
QPlainTextEdit {{ background: {PANEL}; border: 1px solid {BORDE}; border-radius: 12px; padding: 10px;
                 font-family: 'Cascadia Mono', 'Consolas'; font-size: 13px; }}
#estado {{ color: {TENUE}; font-size: 13px; }}
QScrollBar:vertical {{ background: transparent; width: 10px; }}
QScrollBar::handle:vertical {{ background: {BORDE}; border-radius: 5px; min-height: 30px; }}
QScrollBar::add-line, QScrollBar::sub-line {{ height: 0; }}
"""


def icono():
    """Icono dibujado: cuadrado redondeado con una onda."""
    pm = QPixmap(256, 256)
    pm.fill(Qt.transparent)
    p = QPainter(pm)
    p.setRenderHint(QPainter.Antialiasing)
    p.setBrush(QColor("#17181c"))
    p.setPen(Qt.NoPen)
    p.drawRoundedRect(8, 8, 240, 240, 56, 56)
    alturas = [40, 90, 150, 110, 180, 120, 70, 130, 60]
    x = 128 - (len(alturas) * 24 - 8) / 2
    for i, h in enumerate(alturas):
        p.setBrush(QColor(ACENTO if i in (2, 4, 7) else "#ececef"))
        p.drawRoundedRect(QRectF(x + i * 24, 128 - h / 2, 16, h), 8, 8)
    p.end()
    return pm


def nombre_libre(ruta):
    """No machacar nada: «x.wav» → «x (2).wav» si ya existe."""
    ruta = Path(ruta)
    n, candidato = 2, ruta
    while candidato.exists():
        candidato = ruta.with_name(f"{ruta.stem} ({n}){ruta.suffix}")
        n += 1
    return candidato


def onda(ruta, puntos=600):
    """Picos del audio para dibujarlo (rápido: se lee a 4 kHz)."""
    import numpy as np
    a = motores.cargar(ruta, 4000, 1)[:, 0]
    if len(a) == 0:
        return [], 0
    trozos = np.array_split(np.abs(a), min(puntos, len(a)))
    picos = [float(t.max()) if len(t) else 0 for t in trozos]
    m = max(picos) or 1
    return [v / m for v in picos], len(a) / 4000


def mmss(seg):
    seg = int(seg)
    return f"{seg // 60}:{seg % 60:02d}"


def abrir_en_carpeta(ruta):
    if ruta:
        import subprocess
        subprocess.Popen(["explorer", "/select,", str(ruta)])


def plugins_vst3():
    """VST3 instalados → {nombre: ruta del binario}. Los amplis recomendados, primero."""
    encontrados = {}
    for b in sorted(CARPETA_VST3.glob("*.vst3")) if CARPETA_VST3.exists() else []:
        if b.is_dir():
            dentro = b / "Contents" / "x86_64-win" / b.name
            if dentro.exists():
                encontrados[b.stem] = str(dentro)
        else:
            encontrados[b.stem] = str(b)
    orden = [n for n, _ in AMPLIS if n in encontrados]
    return {n: encontrados[n] for n in orden + [n for n in encontrados if n not in orden]}


# ───────────────────────────── piezas ─────────────────────────────

class Hilo(QThread):
    aviso = Signal(str)
    hecho = Signal(object)
    fallo = Signal(str)

    def __init__(self, tarea):
        super().__init__()
        self.tarea = tarea

    def run(self):
        try:
            self.hecho.emit(self.tarea(self.aviso.emit))
        except Exception as e:
            traceback.print_exc()
            self.fallo.emit(str(e) or e.__class__.__name__)


class Onda(QWidget):
    """Dibuja la forma de onda; si tiene posición, pinta lo reproducido y deja saltar con un clic."""
    saltar = Signal(float)

    def __init__(self, alto=56):
        super().__init__()
        self.picos, self.pos = [], None
        self.setMinimumHeight(alto)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

    def poner(self, picos):
        self.picos = picos
        self.update()

    def posicion(self, fraccion):
        self.pos = fraccion
        self.update()

    def mousePressEvent(self, e):
        if self.pos is not None and self.width():
            self.saltar.emit(max(0.0, min(1.0, e.position().x() / self.width())))

    def paintEvent(self, _):
        if not self.picos:
            return
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        w, h = self.width(), self.height()
        paso = w / len(self.picos)
        for i, v in enumerate(self.picos):
            x = i * paso
            jugado = self.pos is not None and x / w <= self.pos
            p.setPen(Qt.NoPen)
            p.setBrush(QColor(ACENTO if jugado else "#4a4d57"))
            alto = max(1.5, v * (h - 4))
            p.drawRect(QRectF(x, h / 2 - alto / 2, max(1.0, paso * 0.7), alto))
        if self.pos is not None:
            p.setPen(QColor(TEXTO))
            p.drawLine(int(self.pos * w), 0, int(self.pos * w), h)
        p.end()


class Zona(QFrame):
    """Caja donde se arrastra (o se elige) un archivo."""
    cambiado = Signal()

    def __init__(self, titulo, ayuda):
        super().__init__()
        self.setObjectName("zona")
        self.setAcceptDrops(True)
        self.setCursor(Qt.PointingHandCursor)
        self.ruta = None
        self.titulo_base = titulo
        self.setMinimumHeight(118)
        caja = QVBoxLayout(self)
        caja.setContentsMargins(20, 16, 20, 16)
        caja.setSpacing(6)
        self.titulo = QLabel(titulo)
        self.titulo.setObjectName("zonaTitulo")
        self.ayuda = QLabel(ayuda)
        self.ayuda.setObjectName("zonaAyuda")
        self.ayuda.setWordWrap(True)
        self.onda = Onda(40)
        self.onda.hide()
        caja.addWidget(self.titulo)
        caja.addWidget(self.ayuda)
        caja.addWidget(self.onda)

    def _marcar(self, prop, valor):
        self.setProperty(prop, valor)
        self.style().unpolish(self)
        self.style().polish(self)

    @staticmethod
    def _valida(e):
        urls = e.mimeData().urls()
        if len(urls) == 1 and urls[0].isLocalFile():
            r = Path(urls[0].toLocalFile())
            if r.suffix.lower() in EXTENSIONES:
                return r
        return None

    def dragEnterEvent(self, e):
        if self._valida(e):
            e.acceptProposedAction()
            self._marcar("encima", True)

    def dragLeaveEvent(self, _):
        self._marcar("encima", False)

    def dropEvent(self, e):
        self._marcar("encima", False)
        r = self._valida(e)
        if r:
            self.poner(r)

    def mousePressEvent(self, _):
        r, _ = QFileDialog.getOpenFileName(self, self.titulo_base, str(Path.home() / "Music"), FILTRO)
        if r:
            self.poner(Path(r))

    def poner(self, ruta):
        self.ruta = Path(ruta)
        self.titulo.setText(f"{self.titulo_base}:  {self.ruta.name}")
        try:
            picos, dur = onda(self.ruta)
            self.ayuda.setText(f"{mmss(dur)} · {self.ruta.parent}  —  "
                               + L("clic o arrastra otro para cambiarlo", "click or drop another to replace it"))
            self.onda.poner(picos)
            self.onda.show()
        except Exception:
            self.ayuda.setText(L("No se ha podido leer este archivo. Prueba con otro.",
                                 "Couldn't read this file. Try another one."))
            self.ruta = None
            self.onda.hide()
        self._marcar("lleno", self.ruta is not None)
        self.cambiado.emit()


class Comparador(QFrame):
    """Reproductor A/B: los dos audios cargados a la par; se cambia cuál suena sin perder el sitio."""
    SR = 48000

    def __init__(self):
        super().__init__()
        self.setObjectName("tarjeta")
        self.audios = [None, None]
        self.pos = 0
        self.stream = None
        self.cual = 1
        caja = QVBoxLayout(self)
        caja.setContentsMargins(18, 16, 18, 16)
        caja.setSpacing(10)
        fila = QHBoxLayout()
        self.txt_play, self.txt_pausa = "▶  " + L("Escuchar", "Play"), "❚❚  " + L("Pausa", "Pause")
        self.play = QPushButton(self.txt_play)
        self.play.clicked.connect(self.alternar)
        self.btn = []
        for i, txt in enumerate((L("A · Original", "A · Original"), L("B · Resultado", "B · Result"))):
            b = QPushButton(txt)
            b.setObjectName("ab")
            b.setCheckable(True)
            b.clicked.connect(lambda _=False, k=i: self.elegir(k))
            self.btn.append(b)
        self.tiempo = QLabel("0:00")
        self.tiempo.setObjectName("estado")
        fila.addWidget(self.play)
        fila.addSpacing(8)
        fila.addWidget(self.btn[0])
        fila.addWidget(self.btn[1])
        fila.addStretch()
        fila.addWidget(self.tiempo)
        self.onda = Onda(64)
        self.onda.saltar.connect(self.ir)
        caja.addLayout(fila)
        caja.addWidget(self.onda)
        self.reloj = QTimer(self, interval=60, timeout=self._tic)

    def cargar(self, original, resultado):
        import numpy as np
        self.parar()
        a, b = (motores.cargar(r, self.SR, 2) for r in (original, resultado))
        n = max(len(a), len(b))
        self.audios = [np.pad(x, ((0, n - len(x)), (0, 0))) for x in (a, b)]
        self.pos = 0
        picos, _ = onda(resultado)
        self.onda.poner(picos)
        self.onda.posicion(0)
        self.elegir(1)
        self._tic()

    def elegir(self, k):
        self.cual = k
        for i in range(2):
            self.btn[i].setChecked(i == k)

    def _sonar(self, salida, frames, tiempo, status):
        audio = self.audios[self.cual]
        trozo = audio[self.pos:self.pos + frames]
        salida[:len(trozo)] = trozo
        salida[len(trozo):] = 0
        self.pos += frames
        if self.pos >= len(audio):
            raise sd.CallbackStop

    def sonando(self):
        return self.stream is not None and self.stream.active

    def alternar(self):
        if self.audios[0] is None:
            return
        if self.sonando():
            self.parar(volver=False)
        else:
            if self.pos >= len(self.audios[0]):
                self.pos = 0
            self.stream = sd.OutputStream(samplerate=self.SR, channels=2, dtype="float32", callback=self._sonar)
            self.stream.start()
            self.play.setText(self.txt_pausa)
            self.reloj.start()

    def ir(self, fraccion):
        if self.audios[0] is not None:
            self.pos = int(fraccion * len(self.audios[0]))
            self._tic()

    def parar(self, volver=True):
        if self.stream is not None:
            self.stream.close()
            self.stream = None
        if volver:
            self.pos = 0
        self.play.setText(self.txt_play)
        self.reloj.stop()

    def _tic(self):
        if self.audios[0] is None:
            return
        total = len(self.audios[0])
        self.onda.posicion(min(1.0, self.pos / total))
        self.tiempo.setText(f"{mmss(self.pos / self.SR)} / {mmss(total / self.SR)}")
        if self.reloj.isActive() and not self.sonando():
            self.parar(volver=self.pos >= total)


class Rueda(QWidget):
    """Rueda de pedal: arrastra arriba/abajo o usa la rueda del ratón; doble clic = valor de fábrica."""
    cambiada = Signal()

    def __init__(self, nombre, minimo, maximo, defecto, unidad):
        super().__init__()
        self.nombre, self.min, self.max, self.defecto, self.unidad = nombre, minimo, maximo, defecto, unidad
        self.valor = defecto
        self.setFixedSize(78, 92)
        self.setCursor(Qt.SizeVerCursor)
        self.setToolTip(L("Arrastra arriba/abajo · doble clic: valor inicial",
                          "Drag up/down · double-click: reset"))
        self._y = None

    def poner(self, v, avisar=False):
        self.valor = max(self.min, min(self.max, v))
        self.update()
        if avisar:
            self.cambiada.emit()

    def texto(self):
        v = self.valor
        if self.unidad == "Hz" and v >= 1000:
            return f"{v / 1000:.1f}k"
        if abs(self.max - self.min) <= 20 and self.unidad not in ("dB",):
            return f"{v:.1f}{self.unidad}"
        return f"{v:.0f}{'' if self.unidad in ('%', 'Hz') else ' '}{self.unidad}"

    def mousePressEvent(self, e):
        self._y = e.position().y()

    def mouseMoveEvent(self, e):
        if self._y is not None:
            dy = self._y - e.position().y()
            self._y = e.position().y()
            fino = 0.25 if e.modifiers() & Qt.ShiftModifier else 1
            self.poner(self.valor + dy * (self.max - self.min) / 160 * fino, True)

    def mouseReleaseEvent(self, _):
        self._y = None

    def mouseDoubleClickEvent(self, _):
        self.poner(self.defecto, True)

    def wheelEvent(self, e):
        self.poner(self.valor + (1 if e.angleDelta().y() > 0 else -1) * (self.max - self.min) / 40, True)

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        r = QRectF(15, 6, 48, 48)
        p.setPen(QPen(QColor("#2c2e35"), 5, Qt.SolidLine, Qt.RoundCap))
        p.drawArc(r, 225 * 16, -270 * 16)
        frac = (self.valor - self.min) / (self.max - self.min)
        p.setPen(QPen(QColor(ACENTO), 5, Qt.SolidLine, Qt.RoundCap))
        p.drawArc(r, 225 * 16, int(-270 * frac * 16))
        p.setPen(QColor(TEXTO))
        f = p.font()
        f.setPointSize(8)
        f.setBold(True)
        p.setFont(f)
        p.drawText(QRectF(0, 20, 78, 20), Qt.AlignCenter, self.texto())
        f.setBold(False)
        p.setFont(f)
        p.setPen(QColor(TENUE))
        p.drawText(QRectF(0, 60, 78, 28), Qt.AlignHCenter | Qt.AlignTop, self.nombre)
        p.end()


class Medidor(QWidget):
    """Barra de nivel de -60 a 0 dB."""

    def __init__(self, etiqueta):
        super().__init__()
        self.etiqueta, self.db = etiqueta, -90.0
        self.setFixedHeight(16)
        self.setMinimumWidth(140)

    def poner(self, db):
        self.db = db
        self.update()

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        p.setPen(QColor(TENUE))
        p.drawText(QRectF(0, 0, 32, 16), Qt.AlignVCenter, self.etiqueta)
        w = self.width() - 36
        p.setPen(Qt.NoPen)
        p.setBrush(QColor(PANEL2))
        p.drawRoundedRect(QRectF(36, 4, w, 8), 4, 4)
        frac = max(0.0, min(1.0, (self.db + 60) / 60))
        color = "#e5484d" if self.db > -1 else ("#ffcf4a" if self.db > -9 else "#3ddc84")
        p.setBrush(QColor(color))
        p.drawRoundedRect(QRectF(36, 4, w * frac, 8), 4, 4)
        p.end()


class Pedal(QFrame):
    cambiado = Signal()

    def __init__(self, pid, nombres, ruedas):
        super().__init__()
        self.pid = pid
        self.setObjectName("pedal")
        caja = QVBoxLayout(self)
        caja.setContentsMargins(14, 12, 14, 10)
        caja.setSpacing(6)
        cab = QHBoxLayout()
        nombre = QLabel(L(*nombres))
        nombre.setObjectName("pedalNombre")
        self.led = QPushButton()
        self.led.setObjectName("led")
        self.led.setCheckable(True)
        self.led.setCursor(Qt.PointingHandCursor)
        self.led.setToolTip(L("Encender / apagar", "On / off"))
        self.led.toggled.connect(self._led)
        cab.addWidget(nombre)
        cab.addStretch()
        cab.addWidget(self.led)
        caja.addLayout(cab)
        fila = QHBoxLayout()
        fila.setSpacing(0)
        self.ruedas = {}
        for rid, es, en, mn, mx, df, ud in ruedas:
            r = Rueda(L(es, en), mn, mx, df, ud)
            r.cambiada.connect(self.cambiado)
            self.ruedas[rid] = r
            fila.addWidget(r)
        fila.addStretch()
        caja.addLayout(fila)

    def _led(self, on):
        self.setProperty("on", on)
        self.style().unpolish(self)
        self.style().polish(self)
        self.cambiado.emit()

    def valores(self):
        return {"on": self.led.isChecked(), **{k: r.valor for k, r in self.ruedas.items()}}

    def poner(self, v):
        self.led.blockSignals(True)
        self.led.setChecked(bool(v.get("on")))
        self.led.blockSignals(False)
        self._led_estilo()
        for k, r in self.ruedas.items():
            if k in v:
                r.poner(v[k])

    def _led_estilo(self):
        self.setProperty("on", self.led.isChecked())
        self.style().unpolish(self)
        self.style().polish(self)


# ───────────────────────────── herramientas de archivos ─────────────────────────────

class Herramienta(QWidget):
    titulo = subtitulo = boton = ""

    def __init__(self):
        super().__init__()
        self.setObjectName("pagina")
        self.hilo = None
        self.caja = QVBoxLayout(self)
        self.caja.setContentsMargins(40, 34, 40, 30)
        self.caja.setSpacing(14)
        t = QLabel(self.titulo)
        t.setObjectName("titulo")
        s = QLabel(self.subtitulo)
        s.setObjectName("subtitulo")
        s.setWordWrap(True)
        self.caja.addWidget(t)
        self.caja.addWidget(s)
        self.caja.addSpacing(8)
        self.montar()
        fila = QHBoxLayout()
        self.ir = QPushButton(self.boton)
        self.ir.setObjectName("principal")
        self.ir.setCursor(Qt.PointingHandCursor)
        self.ir.clicked.connect(self.lanzar)
        self.estado = QLabel("")
        self.estado.setObjectName("estado")
        self.estado.setWordWrap(True)
        fila.addWidget(self.ir)
        fila.addSpacing(14)
        fila.addWidget(self.estado, 1)
        self.caja.addLayout(fila)
        self.barra = QProgressBar()
        self.barra.setTextVisible(False)
        self.barra.setFixedHeight(8)
        self.barra.hide()
        self.caja.addWidget(self.barra)
        self.resultado = QWidget()
        self.rcaja = QVBoxLayout(self.resultado)
        self.rcaja.setContentsMargins(0, 8, 0, 0)
        self.rcaja.setSpacing(10)
        self.resultado.hide()
        self.montar_resultado()
        self.caja.addWidget(self.resultado, 1)
        self.caja.addStretch()
        self.actualizar()

    def seccion(self, texto):
        lab = QLabel(texto.upper())
        lab.setObjectName("seccion")
        return lab

    def actualizar(self):
        self.ir.setEnabled(self.listo() and self.hilo is None)

    def lanzar(self):
        self.antes()
        self.resultado.hide()
        self.ir.setEnabled(False)
        self.estado.setStyleSheet("")
        self.barra.setRange(0, 0)
        self.barra.show()
        self.hilo = Hilo(self.tarea())
        self.hilo.aviso.connect(self.aviso)
        self.hilo.hecho.connect(self._hecho)
        self.hilo.fallo.connect(self._fallo)
        self.hilo.finished.connect(self._fin)
        self.hilo.start()

    def aviso(self, txt):
        txt = str(txt).strip()
        if txt.endswith("%") and txt[:-1].strip().isdigit():
            self.barra.setRange(0, 100)
            self.barra.setValue(int(txt[:-1]))
        else:
            self.estado.setText(txt)

    def _hecho(self, res):
        self.barra.hide()
        self.mostrar(res)
        self.resultado.show()

    def _fallo(self, msg):
        self.barra.hide()
        self.estado.setStyleSheet("color: #ff6b6b;")
        self.estado.setText(L("No ha salido: ", "Something went wrong: ") + msg)

    def _fin(self):
        self.hilo = None
        self.actualizar()

    def botones_archivo(self, ruta, extra=()):
        fila = QHBoxLayout()
        for texto, accion in [("📂  " + L("Abrir carpeta", "Show in folder"), lambda: abrir_en_carpeta(ruta())),
                              *extra]:
            b = QPushButton(texto)
            b.clicked.connect(accion)
            fila.addWidget(b)
        fila.addStretch()
        return fila

    def montar(self): ...
    def montar_resultado(self): ...
    def listo(self): return False
    def antes(self): ...
    def tarea(self): ...
    def mostrar(self, res): ...


class Masterizar(Herramienta):
    icono = "🎛️"
    titulo = L("Masterizar", "Master")
    subtitulo = L("Tu canción suena como la que más te guste: mismo volumen, mismo brillo, misma pegada. "
                  "Elige una canción de referencia del estilo que buscas.",
                  "Make your song sound like the one you love: same loudness, same brightness, same punch. "
                  "Pick a finished reference track in the style you're going for.")
    boton = L("Masterizar", "Master it")

    def montar(self):
        self.cancion = Zona(L("Tu canción", "Your song"),
                            L("Arrastra aquí tu mezcla (WAV, MP3, FLAC…) o haz clic para elegirla.",
                              "Drop your mix here (WAV, MP3, FLAC…) or click to choose it."))
        self.ref = Zona(L("Referencia", "Reference"),
                        L("Una canción terminada que suene como quieres que suene la tuya.",
                          "A finished song that sounds the way you want yours to sound."))
        for z in (self.cancion, self.ref):
            z.cambiado.connect(self.actualizar)
            self.caja.addWidget(z)

    def montar_resultado(self):
        self.rcaja.addWidget(self.seccion(L("Compara: A es tu mezcla, B el máster",
                                            "Compare: A is your mix, B is the master")))
        self.comp = Comparador()
        self.rcaja.addWidget(self.comp)
        self.rcaja.addLayout(self.botones_archivo(lambda: self.salida))

    def listo(self):
        return bool(self.cancion.ruta and self.ref.ruta)

    def antes(self):
        self.comp.parar()
        c = self.cancion.ruta
        self.salida = nombre_libre(c.with_name(f"{c.stem} ({L('máster', 'master')}).wav"))

    def tarea(self):
        c, r, s = self.cancion.ruta, self.ref.ruta, self.salida
        pasos = {"loading": L("Leyendo los audios…", "Reading the audio…"),
                 "matching levels": L("Igualando el volumen…", "Matching loudness…"),
                 "matching frequencies": L("Igualando el brillo…", "Matching tone…"),
                 "correcting levels": L("Ajustando los niveles…", "Correcting levels…"),
                 "final processing": L("Puliendo el final…", "Final processing…"),
                 "saving": L("Guardando…", "Saving…")}

        def t(aviso):
            def traducir(m):
                ml = str(m).lower()
                for clave, txt in pasos.items():
                    if clave in ml:
                        aviso(txt)
                        return
            motores.masterizar(c, r, s, aviso=traducir)
            return s
        return t

    def mostrar(self, salida):
        self.estado.setText(f"✓ {L('Listo', 'Done')}: {salida.name}  "
                            + L("(WAV 24 bits, junto a tu canción)", "(24-bit WAV, next to your song)"))
        self.comp.cargar(self.cancion.ruta, salida)


class Limpiar(Herramienta):
    icono = "🎙️"
    titulo = L("Limpiar voz", "Clean up")
    subtitulo = L("Quita ruido de fondo, zumbidos, ventiladores y eco de habitación con IA. "
                  "Ideal para voces, podcasts, notas de voz y grabaciones con el móvil.",
                  "Remove background noise, hum, fans and room echo with AI. "
                  "Great for vocals, podcasts, voice notes and phone recordings.")
    boton = L("Limpiar", "Clean it")

    def montar(self):
        self.audio = Zona(L("Grabación", "Recording"),
                          L("Arrastra aquí la voz o grabación que quieras limpiar.",
                            "Drop the vocal or recording you want to clean up."))
        self.audio.cambiado.connect(self.actualizar)
        self.caja.addWidget(self.audio)
        tarjeta = QFrame()
        tarjeta.setObjectName("tarjeta")
        fila = QHBoxLayout(tarjeta)
        fila.setContentsMargins(18, 14, 18, 14)
        fila.addWidget(QLabel(L("Intensidad", "Strength")))
        fila.addSpacing(10)
        suave = QLabel(L("Natural", "Natural"))
        suave.setObjectName("estado")
        fila.addWidget(suave)
        self.intensidad = QSlider(Qt.Horizontal)
        self.intensidad.setRange(0, 100)
        self.intensidad.setValue(100)
        fila.addWidget(self.intensidad, 1)
        tope = QLabel(L("A tope", "Max"))
        tope.setObjectName("estado")
        fila.addWidget(tope)
        self.caja.addWidget(tarjeta)

    def montar_resultado(self):
        self.rcaja.addWidget(self.seccion(L("Compara: A es la grabación, B la limpia",
                                            "Compare: A is the recording, B is the clean one")))
        self.comp = Comparador()
        self.rcaja.addWidget(self.comp)
        self.rcaja.addLayout(self.botones_archivo(lambda: self.salida))

    def listo(self):
        return bool(self.audio.ruta)

    def antes(self):
        self.comp.parar()
        a = self.audio.ruta
        self.salida = nombre_libre(a.with_name(f"{a.stem} ({L('limpio', 'clean')}).wav"))

    def tarea(self):
        a, s, i = self.audio.ruta, self.salida, self.intensidad.value()
        return lambda aviso: motores.limpiar(a, s, intensidad=i, aviso=aviso)

    def mostrar(self, salida):
        self.estado.setText(f"✓ {L('Listo', 'Done')}: {Path(salida).name}  "
                            + L("(junto a la grabación)", "(next to the recording)"))
        self.comp.cargar(self.audio.ruta, salida)


class Tablatura(Herramienta):
    icono = "🎼"
    titulo = L("A tablatura", "To tab")
    subtitulo = L("Saca las notas de un riff o una canción: te da la tablatura de guitarra y un MIDI "
                  "para abrirlo en Reaper o cualquier programa. Funciona mejor con un solo instrumento.",
                  "Get the notes out of a riff or a song: you get guitar tab and a MIDI file for Reaper "
                  "or any DAW. Works best with a single instrument.")
    boton = L("Sacar notas", "Get the notes")

    def montar(self):
        self.audio = Zona(L("Audio", "Audio"), L("Arrastra aquí un riff, un solo o una canción.",
                                                 "Drop a riff, a solo or a song here."))
        self.audio.cambiado.connect(self.actualizar)
        self.caja.addWidget(self.audio)

    def montar_resultado(self):
        self.rcaja.addWidget(self.seccion(L("Tablatura (afinación estándar)", "Tab (standard tuning)")))
        self.tab = QPlainTextEdit()
        self.tab.setReadOnly(True)
        self.tab.setLineWrapMode(QPlainTextEdit.NoWrap)
        self.tab.setMinimumHeight(260)
        self.rcaja.addWidget(self.tab, 1)
        self.rcaja.addLayout(self.botones_archivo(lambda: self.midi, extra=[
            ("🎹  " + L("Abrir MIDI", "Open MIDI"),
             lambda: QDesktopServices.openUrl(QUrl.fromLocalFile(str(self.midi)))),
            ("📋  " + L("Copiar tablatura", "Copy tab"),
             lambda: QApplication.clipboard().setText(self.tab.toPlainText())),
        ]))

    def listo(self):
        return bool(self.audio.ruta)

    def tarea(self):
        a = self.audio.ruta
        return lambda aviso: motores.audio_a_tab(a, a.parent, aviso=aviso)

    def mostrar(self, res):
        self.midi, ruta_tab, n = res
        self.tab.setPlainText(ruta_tab.read_text(encoding="utf-8"))
        self.estado.setText(f"✓ {n} {L('notas', 'notes')} · "
                            + L(f"guardado «{ruta_tab.name}» y «{self.midi.name}»",
                                f"saved “{ruta_tab.name}” and “{self.midi.name}”"))


# ───────────────────────────── amplificador en directo ─────────────────────────────

class Amplificador(QScrollArea):
    icono = "🎸"
    titulo = L("Amplificador", "Amp")

    def __init__(self):
        super().__init__()
        self.setWidgetResizable(True)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.proc = None
        self.encendido = False
        self.plugins = plugins_vst3()
        self.pendiente_guardar = None
        self.tonos_usuario = {}

        pagina = QWidget()
        pagina.setObjectName("pagina")
        self.setWidget(pagina)
        caja = QVBoxLayout(pagina)
        caja.setContentsMargins(40, 34, 40, 30)
        caja.setSpacing(14)
        t = QLabel(self.titulo)
        t.setObjectName("titulo")
        s = QLabel(L("Enchufa la guitarra y suena en directo: pedales, amplis gratis (TONE3000, NAM Rig) y "
                     "tus propios tonos. Sin pruebas que caducan.",
                     "Plug in your guitar and play live: pedals, free amp sims (TONE3000, NAM Rig) and "
                     "your own tones. No trials that expire."))
        s.setObjectName("subtitulo")
        s.setWordWrap(True)
        caja.addWidget(t)
        caja.addWidget(s)

        # ── conexión ──
        conexion = QFrame()
        conexion.setObjectName("tarjeta")
        g = QGridLayout(conexion)
        g.setContentsMargins(18, 16, 18, 16)
        g.setHorizontalSpacing(12)
        g.setVerticalSpacing(10)
        self.entrada, self.salida = QComboBox(), QComboBox()
        self.modo = QComboBox()
        self.modo.addItem(L("Rápido (~20 ms)", "Low latency (~20 ms)"), "rapido")
        self.modo.addItem(L("Compatible (~45 ms)", "Compatible (~45 ms)"), "compatible")
        self.buffer = QComboBox()
        for b in (64, 128, 256, 512):
            self.buffer.addItem(str(b), b)
        self.buffer.setCurrentIndex(1)
        for c in (self.entrada, self.salida, self.modo, self.buffer):
            # que los nombres largos de dispositivo no ensanchen la página
            c.setSizeAdjustPolicy(QComboBox.AdjustToMinimumContentsLengthWithIcon)
            c.setMinimumContentsLength(6)
            c.setStyleSheet("min-width: 60px;")
            c.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        for col, (txt, w) in enumerate([(L("Entrada (guitarra)", "Input (guitar)"), self.entrada),
                                        (L("Salida (altavoces)", "Output (speakers)"), self.salida),
                                        (L("Modo", "Mode"), self.modo), ("Buffer", self.buffer)]):
            lab = QLabel(txt.upper())
            lab.setObjectName("seccion")
            g.addWidget(lab, 0, col)
            g.addWidget(w, 1, col)
        self.boton = QPushButton("⏻  " + L("Encender", "Turn on"))
        self.boton.setObjectName("principal")
        self.boton.setCheckable(True)
        self.boton.setCursor(Qt.PointingHandCursor)
        self.boton.clicked.connect(self.alternar)
        g.addWidget(self.boton, 0, 4, 2, 1)
        self.med_in, self.med_out = Medidor("IN"), Medidor("OUT")
        g.addWidget(self.med_in, 2, 0, 1, 2)
        g.addWidget(self.med_out, 2, 2, 1, 3)
        self.estado = QLabel("")
        self.estado.setObjectName("estado")
        self.estado.setWordWrap(True)
        g.addWidget(self.estado, 3, 0, 1, 5)
        aviso = QLabel("⚠ " + L("Toca con altavoces o auriculares con cable: los Bluetooth tienen retraso. "
                                "Empieza con el volumen bajo.",
                                "Play through speakers or wired headphones: Bluetooth adds delay. "
                                "Start with the volume low."))
        aviso.setObjectName("aviso")
        aviso.setWordWrap(True)
        g.addWidget(aviso, 4, 0, 1, 5)
        self.modo.currentIndexChanged.connect(self.pedir_dispositivos)
        caja.addWidget(conexion)

        # ── ampli (plugin) y tonos ──
        fila = QHBoxLayout()
        fila.setSpacing(12)
        ampli = QFrame()
        ampli.setObjectName("tarjeta")
        a = QVBoxLayout(ampli)
        a.setContentsMargins(18, 14, 18, 14)
        a.addWidget(self.etiqueta(L("Ampli", "Amp sim")))
        fa = QHBoxLayout()
        self.plugin = QComboBox()
        self.plugin.setSizeAdjustPolicy(QComboBox.AdjustToMinimumContentsLengthWithIcon)
        self.plugin.addItem(L("Solo pedales de huwe.mus1c", "huwe.mus1c pedals only"), "")
        for n, ruta in self.plugins.items():
            self.plugin.addItem(n, ruta)
        self.plugin.currentIndexChanged.connect(self.cambiar_plugin)
        self.editor = QPushButton(L("Abrir ventana del ampli", "Open amp window"))
        self.editor.clicked.connect(lambda: self.enviar(cmd="editor"))
        self.editor.setEnabled(False)
        fa.addWidget(self.plugin, 1)
        fa.addWidget(self.editor)
        a.addLayout(fa)
        faltan = [(n, url) for n, url in AMPLIS if n not in self.plugins]
        if faltan:
            fl = QHBoxLayout()
            for n, url in faltan:
                b = QPushButton(L(f"Conseguir {n} (gratis)", f"Get {n} (free)"))
                b.clicked.connect(lambda _=False, u=url: QDesktopServices.openUrl(QUrl(u)))
                fl.addWidget(b)
            fl.addStretch()
            a.addLayout(fl)
        fila.addWidget(ampli, 3)

        tonos = QFrame()
        tonos.setObjectName("tarjeta")
        tc = QVBoxLayout(tonos)
        tc.setContentsMargins(18, 14, 18, 14)
        tc.addWidget(self.etiqueta(L("Tonos", "Tones")))
        ft = QHBoxLayout()
        self.tono = QComboBox()
        self.tono.setSizeAdjustPolicy(QComboBox.AdjustToMinimumContentsLengthWithIcon)
        self.tono.activated.connect(self.cargar_tono)
        guardar = QPushButton("💾  " + L("Guardar", "Save"))
        guardar.clicked.connect(self.guardar_tono)
        self.borrar = QPushButton("🗑")
        self.borrar.setToolTip(L("Borrar este tono", "Delete this tone"))
        self.borrar.clicked.connect(self.borrar_tono)
        ft.addWidget(self.tono, 1)
        ft.addWidget(guardar)
        ft.addWidget(self.borrar)
        tc.addLayout(ft)
        fila.addWidget(tonos, 2)
        caja.addLayout(fila)

        # ── pedales ──
        caja.addWidget(self.etiqueta(L("Pedales (en orden de la señal)", "Pedals (in signal order)")))
        rejilla = QGridLayout()
        rejilla.setSpacing(12)
        self.pedales = {}
        for i, (pid, nombres, ruedas) in enumerate(PEDALES):
            p = Pedal(pid, nombres, ruedas)
            p.cambiado.connect(self.mandar_config)
            self.pedales[pid] = p
            rejilla.addWidget(p, i // 3, i % 3)
        caja.addLayout(rejilla)

        # ── grabar ──
        fg = QHBoxLayout()
        self.grabar = QPushButton("●  " + L("Grabar", "Record"))
        self.grabar.setObjectName("grabar")
        self.grabar.setCheckable(True)
        self.grabar.setEnabled(False)
        self.grabar.clicked.connect(self.alternar_grabacion)
        self.grabado = QLabel("")
        self.grabado.setObjectName("estado")
        self.ver_grabacion = QPushButton("📂  " + L("Abrir carpeta", "Show in folder"))
        self.ver_grabacion.hide()
        self.ver_grabacion.clicked.connect(lambda: abrir_en_carpeta(self.ultima_grabacion))
        fg.addWidget(self.grabar)
        fg.addWidget(self.grabado, 1)
        fg.addWidget(self.ver_grabacion)
        caja.addLayout(fg)
        caja.addStretch()

        self.llenar_tonos()
        self.poner_pedales(FABRICA[0]["pedales"])

    @staticmethod
    def etiqueta(txt):
        lab = QLabel(txt.upper())
        lab.setObjectName("seccion")
        return lab

    # ── proceso del motor ──
    def arrancar_motor(self):
        if self.proc is not None:
            return
        self.proc = QProcess(self)
        self.proc.setProcessChannelMode(QProcess.SeparateChannels)
        self.proc.readyReadStandardOutput.connect(self.leer)
        self.proc.finished.connect(self.motor_muerto)
        self.buffer_linea = b""
        self.proc.setWorkingDirectory(str(AQUI))
        if getattr(sys, "frozen", False):  # instalada: el mismo .exe hace de motor
            self.proc.start(sys.executable, ["--amp-motor"])
        else:
            exe = sys.executable.replace("pythonw.exe", "python.exe")
            self.proc.start(exe, ["-u", str(AQUI / "amp_motor.py")])
        self.estado.setText(L("Preparando el motor de audio…", "Starting the audio engine…"))

    def motor_muerto(self, *_):
        self.proc = None
        self.marcar_apagado()
        self.estado.setText(L("El motor de audio se ha cerrado. Pulsa Encender para reiniciarlo.",
                              "The audio engine stopped. Press Turn on to restart it."))

    def enviar(self, **m):
        if self.proc is not None:
            self.proc.write((json.dumps(m) + "\n").encode())

    def leer(self):
        self.buffer_linea += bytes(self.proc.readAllStandardOutput())
        *lineas, self.buffer_linea = self.buffer_linea.split(b"\n")
        for linea in lineas:
            try:
                self.mensaje(json.loads(linea))
            except ValueError:
                pass

    def mensaje(self, m):
        if "nivel" in m:
            self.med_in.poner(m["nivel"][0])
            self.med_out.poner(m["nivel"][1])
            return
        ok = m.get("ok")
        if ok in ("listo", "dispositivos"):
            self.llenar(self.entrada, m["entradas"], "entrada", ("guitar", "inst", "usb", "line", "línea"))
            self.llenar(self.salida, m["salidas"], "salida", ("usb", "altavoces", "speakers", "headphones"))
            if ok == "listo":
                self.estado.setText(L("Listo. Elige entrada y salida y pulsa Encender.",
                                      "Ready. Pick your input and output and press Turn on."))
                self.cambiar_plugin(enviar_estado=True)
                self.mandar_config()
                if getattr(self, "encender_al_estar", False):
                    self.encender_al_estar = False
                    self.encender()
        elif ok == "start":
            self.encendido = True
            self.boton.setChecked(True)
            self.boton.setText("⏻  " + L("Apagar", "Turn off"))
            self.grabar.setEnabled(True)
            self.estado.setText(L(f"🔊 Sonando · retraso ≈ {m['latencia_ms']:.0f} ms · {m['sample_rate']} Hz",
                                  f"🔊 Live · latency ≈ {m['latencia_ms']:.0f} ms · {m['sample_rate']} Hz"))
        elif ok == "parar":
            self.marcar_apagado()
        elif ok == "plugin":
            self.editor.setEnabled(bool(m.get("nombre")))
        elif ok == "estado" and self.pendiente_guardar:
            nombre = self.pendiente_guardar
            self.pendiente_guardar = None
            TONOS.mkdir(parents=True, exist_ok=True)
            datos = {"nombre": nombre, "pedales": self.valores(), "plugin": Path(m["ruta"]).stem
                     if m.get("ruta") else None, "plugin_estado": m.get("datos") or None}
            seguro = re.sub(r'[<>:"/\\|?*]', "_", nombre)
            (TONOS / f"{seguro}.json").write_text(json.dumps(datos, ensure_ascii=False, indent=1), "utf-8")
            self.llenar_tonos(seleccionar=nombre)
        elif ok == "grabado":
            self.ultima_grabacion = m["ruta"]
            self.grabado.setText("✓ " + Path(m["ruta"]).name)
            self.ver_grabacion.show()
        elif "error" in m:
            if m.get("cmd") == "arrancar":
                self.marcar_apagado()
                self.estado.setText(L("No se ha podido abrir la tarjeta de sonido: ",
                                      "Couldn't open the audio device: ") + m["error"]
                                    + L(" — prueba el modo Compatible u otro buffer.",
                                        " — try Compatible mode or another buffer size."))
            else:
                self.estado.setText("⚠ " + m["error"])

    def llenar(self, combo, lista, clave, pistas):
        guardado = idioma.leer_config().get(f"amp_{clave}_{self.modo.currentData()}")
        combo.blockSignals(True)
        combo.clear()
        for idx, nombre in lista:
            combo.addItem(nombre, idx)
        i = combo.findText(guardado) if guardado else -1
        if i < 0:  # por orden de preferencia, saltando los dispositivos virtuales
            reales = [(k, n.lower()) for k, (_, n) in enumerate(lista)
                      if not any(v in n.lower() for v in ("steam", "vdvad", "virtual", "mezcla", "stereo mix"))]
            i = next((k for p in pistas for k, n in reales if p in n), reales[0][0] if reales else 0)
        combo.setCurrentIndex(i)
        combo.blockSignals(False)

    def pedir_dispositivos(self):
        if self.encendido:
            self.apagar()
        self.enviar(cmd="dispositivos", modo=self.modo.currentData())

    # ── encender / apagar ──
    def alternar(self):
        if self.encendido:
            self.apagar()
        else:
            self.encender()

    def encender(self):
        if self.proc is None:
            self.encender_al_estar = True
            self.arrancar_motor()
            self.boton.setChecked(False)
            return
        if self.entrada.currentData() is None or self.salida.currentData() is None:
            self.boton.setChecked(False)
            return
        modo = self.modo.currentData()
        idioma.guardar_config(**{f"amp_entrada_{modo}": self.entrada.currentText(),
                                 f"amp_salida_{modo}": self.salida.currentText()})
        self.boton.setChecked(False)
        self.estado.setText(L("Encendiendo…", "Turning on…"))
        self.enviar(cmd="arrancar", entrada=self.entrada.currentData(), salida=self.salida.currentData(),
                    buffer=self.buffer.currentData(), modo=modo)

    def apagar(self):
        self.enviar(cmd="parar")
        self.marcar_apagado()

    def marcar_apagado(self):
        self.encendido = False
        self.boton.setChecked(False)
        self.boton.setText("⏻  " + L("Encender", "Turn on"))
        self.grabar.setChecked(False)
        self.grabar.setEnabled(False)
        self.med_in.poner(-90)
        self.med_out.poner(-90)

    def alternar_grabacion(self, on):
        if on:
            GRABACIONES.mkdir(parents=True, exist_ok=True)
            ruta = nombre_libre(GRABACIONES / time.strftime(L("Toma %Y-%m-%d %H.%M.wav", "Take %Y-%m-%d %H.%M.wav")))
            self.enviar(cmd="grabar", ruta=str(ruta))
            self.grabado.setText(L("Grabando… (pulsa otra vez para parar)", "Recording… (press again to stop)"))
            self.ver_grabacion.hide()
        else:
            self.enviar(cmd="grabar", ruta=None)

    # ── pedales, plugin y tonos ──
    def valores(self):
        return {pid: p.valores() for pid, p in self.pedales.items()}

    def poner_pedales(self, valores):
        base = por_defecto()
        for pid, p in self.pedales.items():
            p.poner({**base[pid], **valores.get(pid, {})})
        self.mandar_config()

    def mandar_config(self):
        self.enviar(cmd="config", pedales=self.valores())

    def cambiar_plugin(self, *_, enviar_estado=False, datos=None):
        ruta = self.plugin.currentData() or None
        if ruta and not enviar_estado and datos is None:
            # Los amplis traen su propia pantalla: apagamos la de huwe.mus1c para no ponerla dos veces.
            self.pedales["cab"].poner({**self.pedales["cab"].valores(), "on": False})
            self.mandar_config()
        self.editor.setEnabled(False)
        self.enviar(cmd="plugin", ruta=ruta, datos=datos)

    def llenar_tonos(self, seleccionar=None):
        self.tonos_usuario = {}
        if TONOS.exists():
            for f in sorted(TONOS.glob("*.json")):
                try:
                    d = json.loads(f.read_text("utf-8"))
                    self.tonos_usuario[d["nombre"]] = (f, d)
                except Exception:
                    pass
        self.tono.blockSignals(True)
        self.tono.clear()
        for t in FABRICA:
            self.tono.addItem("★ " + L(*t["nombre"]), ("fabrica", t))
        for n, (f, d) in self.tonos_usuario.items():
            self.tono.addItem(n, ("usuario", d))
        if seleccionar:
            self.tono.setCurrentIndex(max(0, self.tono.findText(seleccionar)))
        self.tono.blockSignals(False)
        self.borrar.setEnabled(self.tono.currentData() is not None and self.tono.currentData()[0] == "usuario")

    def cargar_tono(self, *_):
        tipo, t = self.tono.currentData()
        self.borrar.setEnabled(tipo == "usuario")
        self.poner_pedales(t["pedales"])
        nombre_plugin = t.get("plugin")
        i = self.plugin.findText(nombre_plugin) if nombre_plugin else 0
        if nombre_plugin and i < 0:
            self.estado.setText(L(f"Este tono usa {nombre_plugin}, que no está instalado.",
                                  f"This tone uses {nombre_plugin}, which isn't installed."))
            i = 0
        self.plugin.blockSignals(True)
        self.plugin.setCurrentIndex(i)
        self.plugin.blockSignals(False)
        self.cambiar_plugin(datos=t.get("plugin_estado") if i else None)

    def guardar_tono(self):
        nombre, ok = QInputDialog.getText(self, L("Guardar tono", "Save tone"),
                                          L("Nombre del tono:", "Tone name:"))
        if ok and nombre.strip():
            self.pendiente_guardar = nombre.strip()
            if self.proc is None:
                self.mensaje({"ok": "estado", "ruta": None, "datos": None})
            else:
                self.enviar(cmd="estado")

    def borrar_tono(self):
        tipo, d = self.tono.currentData()
        if tipo != "usuario":
            return
        if QMessageBox.question(self, NOMBRE, L(f"¿Borrar el tono «{d['nombre']}»?",
                                                f"Delete the tone “{d['nombre']}”?")) == QMessageBox.Yes:
            self.tonos_usuario[d["nombre"]][0].unlink(missing_ok=True)
            self.llenar_tonos()

    def mostrado(self):
        self.arrancar_motor()

    def cerrar(self):
        if self.proc is not None:
            self.enviar(cmd="salir")
            self.proc.waitForFinished(1500)
            if self.proc is not None:
                self.proc.kill()


# ───────────────────────────── ventana ─────────────────────────────

class Ventana(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(NOMBRE)
        self.setWindowIcon(QIcon(icono()))
        self.resize(1180, 820)
        self.setMinimumSize(980, 640)
        raiz = QWidget()
        raiz.setObjectName("raiz")
        fila = QHBoxLayout(raiz)
        fila.setContentsMargins(0, 0, 0, 0)
        fila.setSpacing(0)

        lateral = QFrame()
        lateral.setObjectName("lateral")
        lateral.setFixedWidth(240)
        lc = QVBoxLayout(lateral)
        lc.setContentsMargins(18, 24, 18, 18)
        logo = QLabel()
        logo.setPixmap(icono().scaled(44, 44, Qt.KeepAspectRatio, Qt.SmoothTransformation))
        marca = QLabel(NOMBRE)
        marca.setObjectName("marca")
        marca2 = QLabel(L("estudio de audio libre", "free audio studio"))
        marca2.setObjectName("marca2")
        cab = QHBoxLayout()
        cab.addWidget(logo)
        textos = QVBoxLayout()
        textos.setSpacing(0)
        textos.addWidget(marca)
        textos.addWidget(marca2)
        cab.addLayout(textos)
        cab.addStretch()
        lc.addLayout(cab)
        lc.addSpacing(26)

        self.lista = QListWidget()
        self.paginas = QStackedWidget()
        for clase in (Amplificador, Masterizar, Limpiar, Tablatura):
            pagina = clase()
            self.paginas.addWidget(pagina)
            QListWidgetItem(f"{clase.icono}   {clase.titulo}", self.lista)
        self.lista.currentRowChanged.connect(self.cambiar)
        lc.addWidget(self.lista, 1)

        self.idioma = QComboBox()
        self.idioma.addItem("🌐  English", "en")
        self.idioma.addItem("🌐  Español", "es")
        self.idioma.setCurrentIndex(1 if idioma.ACTUAL == "es" else 0)
        self.idioma.currentIndexChanged.connect(self.cambiar_idioma)
        lc.addWidget(self.idioma)
        lc.addSpacing(8)
        self.pie = QLabel(self.texto_pie())
        self.pie.setObjectName("pie")
        self.pie.setWordWrap(True)
        lc.addWidget(self.pie)

        fila.addWidget(lateral)
        fila.addWidget(self.paginas, 1)
        self.setCentralWidget(raiz)
        self.lista.setCurrentRow(0)
        QTimer.singleShot(300, self.mirar_gpu)

    def texto_pie(self, gpu=""):
        return (gpu + "\n" if gpu else "") + f"v{VERSION} · " + L("gratis · sin internet · GPLv3",
                                                                  "free · offline · GPLv3")

    def cambiar(self, i):
        for k in range(self.paginas.count()):
            comp = getattr(self.paginas.widget(k), "comp", None)
            if comp:
                comp.parar()
        self.paginas.setCurrentIndex(i)
        mostrado = getattr(self.paginas.widget(i), "mostrado", None)
        if mostrado:
            mostrado()

    def cambiar_idioma(self):
        idioma.guardar_config(idioma=self.idioma.currentData())
        if self.ocupado():
            QMessageBox.information(self, NOMBRE, L("El idioma cambiará al volver a abrir la app.",
                                                    "The language will change next time you open the app."))
            return
        args = [] if getattr(sys, "frozen", False) else [str(Path(__file__).resolve())]
        QProcess.startDetached(sys.executable, args)
        self.close()

    def mirar_gpu(self):
        def t(_):
            import torch
            return torch.cuda.get_device_name(0) if torch.cuda.is_available() else None
        self._gpu = Hilo(t)
        self._gpu.hecho.connect(lambda g: self.pie.setText(self.texto_pie(
            "⚡ " + g.replace("NVIDIA GeForce ", "") if g else L("Usando el procesador (sin GPU)",
                                                                 "Running on CPU (no GPU)"))))
        self._gpu.start()

    def ocupado(self):
        return any(getattr(self.paginas.widget(k), "hilo", None) for k in range(self.paginas.count()))

    def closeEvent(self, e):
        if self.ocupado() and QMessageBox.question(
                self, NOMBRE, L("Hay algo procesándose. ¿Cerrar igualmente?",
                                "Something is still processing. Close anyway?")) != QMessageBox.Yes:
            e.ignore()
            return
        for k in range(self.paginas.count()):
            cerrar = getattr(self.paginas.widget(k), "cerrar", None)
            if cerrar:
                cerrar()
        e.accept()
        QApplication.processEvents()
        os._exit(0)  # cierra aunque quede un hilo de IA trabajando


def main():
    if "--amp-motor" in sys.argv:  # versión instalada: este mismo .exe hace de motor del Amplificador
        for nombre, fd, modo in (("stdin", 0, "r"), ("stdout", 1, "w"), ("stderr", 2, "w")):
            if getattr(sys, nombre) is None:
                try:
                    setattr(sys, nombre, os.fdopen(fd, modo, encoding="utf-8", buffering=1))
                except OSError:
                    setattr(sys, nombre, open(os.devnull, modo))
        import amp_motor
        amp_motor.main()
        return
    if "--autoprueba" in sys.argv:  # comprueba los motores sin ventana: --autoprueba carpeta_con_riff.wav…
        carpeta = Path(sys.argv[sys.argv.index("--autoprueba") + 1])
        informe = {}
        for nombre, f in [
            ("master", lambda: motores.masterizar(carpeta / "h_riff.wav", carpeta / "h_ref.wav",
                                                  carpeta / "h_master.wav", aviso=lambda m: None)),
            ("clean", lambda: motores.limpiar(carpeta / "h_ruido.wav", carpeta / "h_limpio.wav",
                                              aviso=lambda m: None)),
            ("tab", lambda: motores.audio_a_tab(carpeta / "h_riff.wav", carpeta, aviso=lambda m: None)[2]),
        ]:
            t = time.time()
            try:
                informe[nombre] = {"ok": str(f()), "s": round(time.time() - t, 1)}
            except Exception:
                informe[nombre] = {"error": traceback.format_exc()}
        (carpeta / "h_informe.json").write_text(json.dumps(informe, indent=1), "utf-8")
        return
    if sys.platform == "win32":
        import ctypes
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("huwe.mus1c")
    app = QApplication(sys.argv)
    app.setApplicationName(NOMBRE)
    app.setStyleSheet(ESTILO)
    app.setFont(QFont("Segoe UI", 10))
    v = Ventana()
    v.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
