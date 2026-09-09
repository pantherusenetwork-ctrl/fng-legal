@echo off
REM Commun aux 3 lanceurs : trouve l'exe (ou python run.py) SANS dependre
REM du repertoire courant ni d'un dossier frere RackForgePrime-PC.
REM A appeler depuis LANCER-*.bat (setlocal deja actif).

cd /d "%~dp0"
set "RFP_KIT=%~dp0"
if "%RFP_KIT:~-1%"=="\" set "RFP_KIT=%RFP_KIT:~0,-1%"

set "RFP_EXE="
set "RFP_PY="
set "RFP_RUN="

if exist "%RFP_KIT%\RackForgePrime.exe" set "RFP_EXE=%RFP_KIT%\RackForgePrime.exe"
if not defined RFP_EXE if exist "%RFP_KIT%\RackForgePrime\RackForgePrime.exe" (
  set "RFP_EXE=%RFP_KIT%\RackForgePrime\RackForgePrime.exe"
  set "RFP_KIT=%RFP_KIT%\RackForgePrime"
)

REM Ancien deploiement 3 dossiers (Web/Phone a cote de -PC) : repli, pas le nominal.
if not defined RFP_EXE if exist "%RFP_KIT%\..\RackForgePrime-PC\RackForgePrime.exe" (
  set "RFP_KIT=%RFP_KIT%\..\RackForgePrime-PC"
  set "RFP_EXE=%RFP_KIT%\RackForgePrime.exe"
)

REM Lanceurs ranges dans portable\ du depot : on remonte a run.py.
if not defined RFP_EXE if exist "%RFP_KIT%\..\run.py" (
  set "RFP_KIT=%RFP_KIT%\.."
  set "RFP_RUN=%RFP_KIT%\run.py"
)
if not defined RFP_EXE if exist "%RFP_KIT%\run.py" set "RFP_RUN=%RFP_KIT%\run.py"

if defined RFP_RUN (
  if exist "%RFP_KIT%\.venv\Scripts\python.exe" (
    set "RFP_PY=%RFP_KIT%\.venv\Scripts\python.exe"
  ) else (
    set "RFP_PY=python"
  )
)

if not defined RFP_EXE if not defined RFP_RUN (
  echo.
  echo [ERREUR] RackForgePrime.exe introuvable a cote de ce lanceur.
  echo.
  echo Copiez le dossier COMPLET du kit portable :
  echo   RackForgePrime.exe  +  _internal\  +  LANCER-*.bat  +  RackForgePrime-Workspace\
  echo.
  echo Ne copiez PAS un seul sous-dossier (RackForgePrime-Web ou -Phone tout seul).
  echo Voir LISEZMOI.txt a la racine du kit.
  echo.
  pause
  exit /b 1
)

set "RACKFORGE_KIT_DIR=%RFP_KIT%"
set "RACKFORGE_WORKSPACE=%RFP_KIT%\RackForgePrime-Workspace"
set "RACKFORGE_EDITION=%RFP_EDITION%"

echo.
echo RackForgePrime — edition %RFP_EDITION%
echo Kit : %RFP_KIT%
echo Espace de travail : %RACKFORGE_WORKSPACE%
echo Fermez cette fenetre pour arreter le serveur.
echo.
