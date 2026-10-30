# Building the Windows installer

1. Create a lightweight CPU environment (no TensorFlow):
   ```bash
   uv venv --python 3.11 .venv-build
   uv pip install --python .venv-build/Scripts/python.exe "torch==2.11.*" "torchaudio==2.11.*" --index-url https://download.pytorch.org/whl/cpu
   uv pip install --python .venv-build/Scripts/python.exe --no-deps basic-pitch
   uv pip install --python .venv-build/Scripts/python.exe -r requirements-build.txt
   ```
2. Put the official **TONE3000** plugin (from <https://www.tone3000.com/plugin>) in `instalador/terceros/TONE3000.vst3/`.
3. Package the app:
   ```bash
   .venv-build/Scripts/pyinstaller instalador/huwe.mus1c.spec --noconfirm --distpath instalador/dist --workpath instalador/build
   ```
4. Self-test the packaged app. Put `h_riff.wav`, `h_ref.wav` and `h_ruido.wav` in a folder, then run:
   ```bash
   instalador/dist/huwe.mus1c/huwe.mus1c.exe --autoprueba <folder>
   ```
   It writes the results to `<folder>/h_informe.json`.
5. Compile the installer with [Inno Setup 6](https://jrsoftware.org/isinfo.php):
   ```bash
   ISCC instalador/huwe.mus1c.iss
   ```
   The installer is written to `instalador/salida/`.
