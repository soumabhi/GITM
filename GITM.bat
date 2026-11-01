@echo off
cd /d "%~dp0desktop"
start "" "%~dp0desktop\node_modules\electron\dist\electron.exe" "%~dp0desktop"
