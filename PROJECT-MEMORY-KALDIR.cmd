@echo off
setlocal
chcp 65001 >nul
title Project Memory Kaldirma
cd /d "%~dp0"

echo.
echo Project Memory kaldiriliyor...
echo.

powershell.exe -NoLogo -NoProfile -ExecutionPolicy Bypass -File "%~dp0uninstall.ps1" -RemoveGlobalRules
set "UNINSTALL_RESULT=%ERRORLEVEL%"

echo.
if "%UNINSTALL_RESULT%"=="0" (
    echo KALDIRMA BASARILI.
) else (
    echo KALDIRMA BASARISIZ. Hata kodu: %UNINSTALL_RESULT%
)

if not defined PROJECT_MEMORY_NO_PAUSE pause
exit /b %UNINSTALL_RESULT%
