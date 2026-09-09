@echo off
setlocal EnableExtensions
title RackForgePrime — PC
set "RFP_EDITION=pc"
call "%~dp0_commun.cmd"
if errorlevel 1 exit /b 1

if defined RFP_EXE (
  "%RFP_EXE%" --edition pc
) else (
  set "PYTHONIOENCODING=utf-8"
  "%RFP_PY%" "%RFP_RUN%" --edition pc
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
