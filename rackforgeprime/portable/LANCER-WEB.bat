@echo off
setlocal EnableExtensions
title RackForgePrime — Web
set "RFP_EDITION=web"
call "%~dp0_commun.cmd"
if errorlevel 1 exit /b 1

echo Edition Web : le navigateur s'ouvre sur http://127.0.0.1:8137
echo Si la fenetre ne s'ouvre pas, double-cliquez DERNIERE-ADRESSE.txt
echo.

if defined RFP_EXE (
  "%RFP_EXE%" --edition web
) else (
  set "PYTHONIOENCODING=utf-8"
  "%RFP_PY%" "%RFP_RUN%" --edition web
)
if errorlevel 1 (
  echo.
  echo Le serveur s'est arrete avec une erreur. Lisez :
  echo   %RFP_KIT%\rackforge-demarrage.log
  echo   %RACKFORGE_WORKSPACE%\rackforge.log
  echo   %RFP_KIT%\LISEZMOI.txt  (section Depannage)
  pause
)
endlocal
