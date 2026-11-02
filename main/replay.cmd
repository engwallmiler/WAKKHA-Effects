@echo off
setlocal
cd /d "%~dp0"
set "BEATLIGHT_REPLAY_PY=%~dp0.runtime\python312\python.exe"
if not exist "%BEATLIGHT_REPLAY_PY%" (
  echo Python local nao encontrado. Execute instalar.cmd primeiro.
  exit /b 2
)
if "%~1"=="" (
  "%BEATLIGHT_REPLAY_PY%" -X utf8 -m beatlight.replay --help
  exit /b 0
)
"%BEATLIGHT_REPLAY_PY%" -X utf8 -m beatlight.replay %*
exit /b %errorlevel%
