# PyInstaller: empaqueta huwe.mus1c en una carpeta (dist\huwe.mus1c) que luego mete Inno Setup.
# Uso (desde la carpeta del proyecto):  .venv-build\Scripts\pyinstaller instalador\huwe.mus1c.spec --noconfirm
from PyInstaller.utils.hooks import collect_data_files, collect_dynamic_libs, collect_submodules

RAIZ = SPECPATH + "\\.."

datas = [
    (RAIZ + "\\modelos", "modelos"),
    (RAIZ + "\\icono.ico", "."),
]
datas += collect_data_files("librosa")  # incluye los .pyi que usa lazy_loader
datas += collect_data_files("basic_pitch", includes=["saved_models/icassp_2022/nmp.onnx"])
datas += collect_data_files("imageio_ffmpeg", include_py_files=False)
datas += collect_data_files("df")
binaries = collect_dynamic_libs("pedalboard") + collect_dynamic_libs("sounddevice")

# df no se deja importar al analizar (usa una API vieja de torchaudio que motores.py sustituye): a mano.
DF = ["checkpoint", "config", "deepfilternet", "deepfilternet2", "deepfilternet3", "enhance", "io", "logger",
      "model", "modules", "multiframe", "utils", "version"]
hiddenimports = (["df." + m for m in DF] + collect_submodules("matchering") + ["amp_motor", "pedales",
                 "idioma", "motores", "libdf", "onnxruntime", "sklearn.utils._typedefs"])

a = Analysis(
    [RAIZ + "\\huwe.mus1c.pyw"],
    pathex=[RAIZ],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    excludes=["tensorflow", "keras", "tensorboard", "matplotlib", "IPython", "tkinter",
              "PySide6.QtWebEngineCore", "PySide6.QtWebEngineWidgets", "PySide6.Qt3DCore", "PySide6.QtQuick"],
    noarchive=False,
)
pyz = PYZ(a.pure)
exe = EXE(
    pyz, a.scripts, [],
    exclude_binaries=True,
    name="huwe.mus1c",
    icon=RAIZ + "\\icono.ico",
    console=False,
    version=None,
)
coll = COLLECT(exe, a.binaries, a.datas, name="huwe.mus1c")
