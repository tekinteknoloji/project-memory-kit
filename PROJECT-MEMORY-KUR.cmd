@echo off
setlocal
chcp 65001 >nul
title Project Memory Kurulumu
cd /d "%~dp0"

echo.
echo Project Memory kuruluyor...
echo.

powershell.exe -NoLogo -NoProfile -ExecutionPolicy Bypass -File "%~dp0install.ps1" -InstallGlobalRules
set "INSTALL_RESULT=%ERRORLEVEL%"

echo.
if "%INSTALL_RESULT%"=="0" (
    echo KURULUM BASARILI.
    echo Codex'i yeniden baslatin veya yeni bir gorev acin.
) else (
    echo KURULUM BASARISIZ. Hata kodu: %INSTALL_RESULT%
    echo Yukaridaki hata mesajini kontrol edin.
)

if not defined PROJECT_MEMORY_NO_PAUSE pause
exit /b %INSTALL_RESULT%
