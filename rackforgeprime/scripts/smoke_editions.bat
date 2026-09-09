@echo off
REM Smoke Windows des 3 editions. Prefere l'exe du kit s'il est deja assemble,
REM sinon python run.py (meme contrat que scripts\smoke_editions.py).
setlocal EnableExtensions
cd /d "%~dp0\.."
set "PYTHONIOENCODING=utf-8"
if exist ".venv\Scripts\python.exe" (
  ".venv\Scripts\python.exe" "scripts\smoke_editions.py" %*
) else (
  python "scripts\smoke_editions.py" %*
)
endlocal
exit /b %ERRORLEVEL%
