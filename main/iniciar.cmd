@echo off
setlocal
cd /d "%~dp0"
if not exist ".venv312\Scripts\python.exe" goto portable
".venv312\Scripts\python.exe" -c "import sys; assert sys.version_info.major == 3 and sys.version_info.minor == 12; import numpy, scipy, PySide6, pyaudiowpatch, serial" >nul 2>&1
if errorlevel 1 goto portable
".venv312\Scripts\python.exe" run.py %*
goto end
:portable
if not exist ".runtime\python312\python.exe" goto missing
".runtime\python312\python.exe" -c "import sys; assert sys.version_info.major == 3 and sys.version_info.minor == 12; import numpy, scipy, PySide6, pyaudiowpatch, serial" >nul 2>&1
if errorlevel 1 goto missing
".runtime\python312\python.exe" run.py %*
goto end
:missing
echo Nenhum ambiente Python 3.12 com as dependencias foi encontrado. Execute instalar.cmd.
pause
exit /b 1
:end
if errorlevel 1 pause
