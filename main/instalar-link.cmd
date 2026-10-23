@echo off
setlocal
cd /d "%~dp0"
if not exist ".venv312\Scripts\python.exe" goto portable
".venv312\Scripts\python.exe" -c "import sys; assert sys.version_info[:2] == (3,12); import numpy, scipy, PySide6, pyaudiowpatch" >nul 2>&1
if errorlevel 1 goto portable
set "BEATLIGHT_LINK_PY=.venv312\Scripts\python.exe"
goto install
:portable
if not exist ".runtime\python312\python.exe" goto missing
".runtime\python312\python.exe" -c "import sys; assert sys.version_info[:2] == (3,12); import numpy, scipy, PySide6, pyaudiowpatch" >nul 2>&1
if errorlevel 1 goto missing
set "BEATLIGHT_LINK_PY=.runtime\python312\python.exe"
:install
"%BEATLIGHT_LINK_PY%" -m pip install --only-binary=:all: "aalink==0.2.3"
if errorlevel 1 goto failed
"%BEATLIGHT_LINK_PY%" -c "import aalink; print('Ableton Link preparado. Abra iniciar.cmd e acesse Ableton Link.')"
if errorlevel 1 goto failed
pause
exit /b 0
:missing
echo Prepare primeiro o aplicativo com instalar.cmd. E necessario Python 3.12 x64.
pause
exit /b 1
:failed
echo Falha no modulo Link. Verifique internet, arquitetura x64 e Microsoft Visual C++ Redistributable 2015-2022 x64.
pause
exit /b 1
