$ErrorActionPreference = "Stop"
$env:TEMP = "D:\tmp"
$env:TMP = "D:\tmp"
$env:PIP_CACHE_DIR = "D:\pip-cache"
$python = "D:\GIMM\.venv\Scripts\python.exe"
& $python -m pip install pyinstaller
& $python -m PyInstaller --noconfirm --windowed --name GITM --onedir `
  --distpath "D:\GIMM\dist" --workpath "D:\GIMM\build" `
  --icon "D:\GIMM\assets\icons\app.png" `
  --add-data "assets;assets" --add-data "config.yaml;." --add-data "sprites;sprites" `
  --exclude-module PySide6.QtWebEngine --exclude-module PySide6.QtWebEngineCore `
  --exclude-module PySide6.QtWebEngineWidgets --exclude-module PySide6.QtPdf `
  --exclude-module PySide6.QtPdfWidgets --exclude-module PySide6.Qt3DCore `
  main.py
Copy-Item -Force "D:\GIMM\config.yaml" "D:\GIMM\dist\GITM\config.yaml"
if (Test-Path "D:\GIMM\sprites") { Copy-Item -Recurse -Force "D:\GIMM\sprites" "D:\GIMM\dist\GITM\sprites" }
Write-Output "Built D:\GIMM\dist\GITM\GITM.exe"
