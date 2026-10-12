@echo off
setlocal EnableDelayedExpansion
title STARLINCS Uninstaller

set "SCRIPT_DIR=%~dp0"
set "VENV_DIR=%SCRIPT_DIR%.venv"
for /f "usebackq delims=" %%D in (`powershell -NoProfile -Command "[Environment]::GetFolderPath('Desktop')"`) do set "DESKTOP=%%D"
set "SHORTCUT=%DESKTOP%\STARLINCS.lnk"

echo.
echo  ==================================================================
echo                    STARLINCS  -  Uninstaller
echo  ==================================================================
echo.

echo  This will remove:
echo    - Virtual environment (.venv)
echo    - LAUNCH_STARLINCS.vbs launcher
echo    - Global 'starlincs' command
echo    - Legacy STARLINCS install artifacts (if any)
echo    - This folder from your user PATH (if it was added)
echo.
set /p CONFIRM="Continue? (y/n): "
if /i not "%CONFIRM%"=="y" (
    echo  Cancelled.
    pause
    exit /b 0
)

:: ── 1. Remove virtual environment ───────────────────────────────────────────
echo.
echo [1/6] Removing virtual environment...
if exist "%VENV_DIR%" (
    rmdir /s /q "%VENV_DIR%"
    echo  [OK] Removed .venv
) else (
    echo  [SKIP] .venv not found
)

:: ── 2. Remove launcher script ────────────────────────────────────────────────
echo.
echo [2/6] Removing launcher script...
if exist "%SCRIPT_DIR%LAUNCH_STARLINCS.vbs" (
    del "%SCRIPT_DIR%LAUNCH_STARLINCS.vbs"
    echo  [OK] Removed LAUNCH_STARLINCS.vbs
) else (
    echo  [SKIP] LAUNCH_STARLINCS.vbs not found
)



:: ── 3. Remove global launcher and pointer ────────────────────────────────────
echo.
echo [3/6] Removing global 'starlincs' command...

set "WINAPPS=%LOCALAPPDATA%\Microsoft\WindowsApps"
set "POINTER_DIR=%LOCALAPPDATA%\STARLINCS"

if exist "%WINAPPS%\starlincs.bat" (
    del "%WINAPPS%\starlincs.bat"
    echo  [OK] Removed global launcher
) else (
    echo  [SKIP] Global launcher not found
)

if exist "%POINTER_DIR%" (
    rmdir /s /q "%POINTER_DIR%"
    echo  [OK] Removed install path pointer
) else (
    echo  [SKIP] Install path pointer not found
)

:: ── 4. Remove legacy install artifacts ───────────────────────────────────────
echo.
echo [4/6] Removing legacy install artifacts...
if exist "%LOCALAPPDATA%\Programs\starlincs" (
    rmdir /s /q "%LOCALAPPDATA%\Programs\starlincs" >nul 2>&1
    echo  [OK] Removed legacy folder: %LOCALAPPDATA%\Programs\starlincs
) else (
    echo  [SKIP] No legacy folder found
)


:: ── 5. Clean up user PATH ─────────────────────────────────────────────────────
echo.
echo [6/6] Checking user PATH for leftover entries...

set "PS_TMP=%TEMP%\starlincs_path_cleanup.ps1"
echo $dir = '%SCRIPT_DIR%' > "%PS_TMP%"
echo if ($dir.EndsWith('\')) { $dir = $dir.Substring(0, $dir.Length-1) } >> "%PS_TMP%"
echo $legacy = '%LOCALAPPDATA%\Programs\starlincs' >> "%PS_TMP%"
echo $old = [Environment]::GetEnvironmentVariable('Path','User') >> "%PS_TMP%"
echo if ($null -eq $old) { $old = '' } >> "%PS_TMP%"
echo $old = $old.Trim().Trim([char]34) >> "%PS_TMP%"
echo $parts = $old -split ';' ^| ForEach-Object { $_.Trim().Trim([char]34) } >> "%PS_TMP%"
echo $parts = $parts ^| Where-Object { $_ -and ($_ -ne '=') -and ($_.TrimEnd('\') -ine $dir) -and ($_.TrimEnd('\') -ine $legacy) } >> "%PS_TMP%"
echo $new = ($parts -join ';') >> "%PS_TMP%"
echo if ($new -ne $old) { [Environment]::SetEnvironmentVariable('Path', $new, 'User') } >> "%PS_TMP%"

powershell -NoProfile -ExecutionPolicy Bypass -File "%PS_TMP%" >nul 2>&1
del "%PS_TMP%"
echo  [OK] PATH cleaned (restart terminals for it to take effect)

:: ── Done ─────────────────────────────────────────────────────────────────────
echo.
echo  ==================================================================
echo   Uninstall complete.
echo  ==================================================================
echo.
echo  To fully remove STARLINCS, you can now delete this entire folder:
echo    %SCRIPT_DIR%
echo.
pause