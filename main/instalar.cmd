@echo off
setlocal
cd /d "%~dp0"
py -3.12 --version >nul 2>nul
if errorlevel 1 (
    echo Python 3.12 nao encontrado. Instale Python 3.12 x64 em https://www.python.org/downloads/windows/
    echo Depois execute novamente este arquivo.
    pause
    exit /b 1
)
if not exist ".venv312\Scripts\python.exe" py -3.12 -m venv .venv312
if errorlevel 1 goto :failed
".venv312\Scripts\python.exe" -m pip install -e ".[dev]"
if errorlevel 1 goto :failed
echo Ambiente preparado. Execute iniciar.cmd para abrir BEATLIGHT DMX.
pause
exit /b 0
:failed
echo Falha na instalacao. Verifique as mensagens acima e a conexao de internet.
pause
exit /b 1
