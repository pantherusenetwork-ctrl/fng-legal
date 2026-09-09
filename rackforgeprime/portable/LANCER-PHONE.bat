@echo off
setlocal EnableExtensions
title RackForgePrime — Phone
set "RFP_EDITION=phone"
call "%~dp0_commun.cmd"
if errorlevel 1 exit /b 1

echo Edition Phone : le serveur ecoute sur toutes les interfaces (0.0.0.0).
echo Adresses IPv4 de ce poste (a ouvrir sur le telephone, meme Wi-Fi) :
ipconfig | findstr /i "IPv4"
echo.
echo Une boite de dialogue et DERNIERE-ADRESSE.txt affichent aussi l'URL.
echo.

if defined RFP_EXE (
  "%RFP_EXE%" --edition phone
) else (
  set "PYTHONIOENCODING=utf-8"
  "%RFP_PY%" "%RFP_RUN%" --edition phone
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
