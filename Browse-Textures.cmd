@echo off
if not exist "%~dp0work\texture-catalog107\index.html" (
  echo Missing verified catalog. Rebuild with work/catalog-textures107.py and work/build-texture-browser107.py using Python with Pillow.
  exit /b 1
)
start "" "%~dp0work\texture-catalog107\index.html"
