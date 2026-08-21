@echo off
setlocal
chcp 65001 >nul
title Project Memory Guncelleme
cd /d "%~dp0"

echo.
echo Project Memory guncelleniyor...
echo Mevcut surum once zaman damgali bir klasore yedeklenecek.
echo.

powershell.exe -NoLogo -NoProfile -ExecutionPolicy Bypass -File "%~dp0install.ps1" -InstallGlobalRules -Force
set "INSTALL_RESULT=%ERRORLEVEL%"

echo.
if "%INSTALL_RESULT%"=="0" (
    echo GUNCELLEME BASARILI.
    echo Codex'i yeniden baslatin veya yeni bir gorev acin.
) else (
    echo GUNCELLEME BASARISIZ. Hata kodu: %INSTALL_RESULT%
)

if not defined PROJECT_MEMORY_NO_PAUSE pause
exit /b %INSTALL_RESULT%
