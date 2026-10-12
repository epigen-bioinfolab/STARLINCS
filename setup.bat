@echo off
setlocal EnableDelayedExpansion
title STARLINCS Installer

set "SCRIPT_DIR=%~dp0"
set "VENV_DIR=%SCRIPT_DIR%.venv"
set "LOG_FILE=%SCRIPT_DIR%installation-log.log"

echo. > "%LOG_FILE%"

echo.
echo  ==================================================================
echo                    STARLINCS  -  Windows Installer
echo     Signature-driven Transcriptome Alignment for Repurposing
echo  ==================================================================
echo.

:: ── 1. Check Python ──────────────────────────────────────────────────────────
echo [1/8] Checking Python 3.9+...
python --version >nul 2>&1
if errorlevel 1 (
    echo  [ERROR] Python was not found. >> "%LOG_FILE%"
    echo  [ERROR] Python was not found.
    echo.
    echo  Please install Python 3.9 or newer from:
    echo    https://www.python.org/downloads/
    echo.
    echo  IMPORTANT: During installation, tick "Add Python to PATH"
    echo.
    pause
    exit /b 1
)

for /f "tokens=2 delims= " %%v in ('python --version 2^>^&1') do set PYVER=%%v
for /f "tokens=1,2 delims=." %%a in ("%PYVER%") do (
    set PYMAJ=%%a
    set PYMIN=%%b
)
if %PYMAJ% lss 3 goto :py_too_old
if %PYMAJ% equ 3 if %PYMIN% lss 9 goto :py_too_old
goto :py_ok

:py_too_old
echo  [ERROR] Python %PYVER% is too old. >> "%LOG_FILE%"
echo  [ERROR] Python %PYVER% is too old.
echo.
echo  STARLINCS requires Python 3.9 or newer.
echo  Please download and install it from:
echo    https://www.python.org/downloads/
echo.
echo  IMPORTANT: During installation, tick "Add Python to PATH"
echo.
pause
exit /b 1

:py_ok
echo  [OK] Found Python %PYVER% (Tested on Python 3.14 and older versions)
echo  [OK] Found Python %PYVER% >> "%LOG_FILE%"

:: ── 2. Check tkinter ─────────────────────────────────────────────────────────
echo.
echo [2/8] Checking tkinter (GUI library)...
python -c "import tkinter" >nul 2>&1
if errorlevel 1 (
    echo  [ERROR] tkinter is missing. >> "%LOG_FILE%"
    echo  [ERROR] tkinter is missing.
    echo  Re-install Python from https://www.python.org/downloads/
    echo  and make sure "tcl/tk and IDLE" is ticked during setup.
    pause
    exit /b 1
)
echo  [OK] tkinter is available
echo  [OK] tkinter is available >> "%LOG_FILE%"

:: ── 3. Create virtual environment ───────────────────────────────────────────
echo.
echo [3/8] Setting up Python virtual environment...
if exist "%VENV_DIR%" (
    echo  Removing old virtual environment...
    rmdir /s /q "%VENV_DIR%"
)

python -m venv "%VENV_DIR%"
if errorlevel 1 (
    echo  [ERROR] Failed to create virtual environment. >> "%LOG_FILE%"
    echo  [ERROR] Failed to create virtual environment.
    pause
    exit /b 1
)
echo  [OK] Virtual environment created at %VENV_DIR%
echo  [OK] Virtual environment created at %VENV_DIR% >> "%LOG_FILE%"

set "VENV_PYTHON=%VENV_DIR%\Scripts\python.exe"
set "VENV_PYTHONW=%VENV_DIR%\Scripts\pythonw.exe"
set "VENV_PIP=%VENV_DIR%\Scripts\pip.exe"

:: ── 4. Install Python packages ──────────────────────────────────────────────
echo.
echo [4/8] Installing Python packages (pandas, numpy, gseapy, openpyxl)...
echo  This may take a few minutes.
echo.

"%VENV_PIP%" install --upgrade pip >> "%LOG_FILE%" 2>&1
"%VENV_PIP%" install pandas numpy gseapy openpyxl >> "%LOG_FILE%" 2>&1
if errorlevel 1 (
    echo  [ERROR] Dependency installation failed. See %LOG_FILE%
    echo  Check your internet connection and try again.
    pause
    exit /b 1
)
echo  [OK] Dependencies installed
echo  [OK] Dependencies installed >> "%LOG_FILE%"

:: ── 5. Create launcher script ────────────────────────────────────────────────
echo.
echo [5/8] Creating launcher script...

:: VBS launcher - runs pythonw.exe completely hidden, no console flash at all
set "RUN_VBS=%SCRIPT_DIR%LAUNCH_STARLINCS.vbs"
(
    echo Set objShell = CreateObject^("WScript.Shell"^)
    echo cmd = """%VENV_DIR%\Scripts\pythonw.exe"" ""%SCRIPT_DIR%starlincs\gui.py"""
    echo objShell.Run cmd, 0, False
) > "%RUN_VBS%"
echo  [OK] Created LAUNCH_STARLINCS.vbs ^(GUI, double-click, no console window^)
echo  [OK] Launcher script created >> "%LOG_FILE%"


:: ── 6. Create desktop shortcut ──────────────────────────────────────────────
echo.
echo [6/8] Creating desktop shortcut...
for /f "usebackq delims=" %%D in (`powershell -NoProfile -Command "[Environment]::GetFolderPath('Desktop')"`) do set "DESKTOP=%%D"
set "SHORTCUT=%DESKTOP%\STARLINCS.lnk"
set "ICON_PATH=%SCRIPT_DIR%starlincs\resources\icon.ico"
set "PS_TMP=%TEMP%\starlincs_shortcut.ps1"
echo $ws = New-Object -ComObject WScript.Shell > "%PS_TMP%"
echo $s = $ws.CreateShortcut('%SHORTCUT%') >> "%PS_TMP%"
echo $s.TargetPath = 'wscript.exe' >> "%PS_TMP%"
echo $s.Arguments = [char]34 + '%RUN_VBS%' + [char]34 >> "%PS_TMP%"
echo $s.WorkingDirectory = '%SCRIPT_DIR%' >> "%PS_TMP%"
echo if (Test-Path '%ICON_PATH%') { $s.IconLocation = '%ICON_PATH%' } >> "%PS_TMP%"
echo $s.Description = 'STARLINCS - Drug Repurposing GSEA Tool' >> "%PS_TMP%"
echo $s.Save() >> "%PS_TMP%"
powershell -NoProfile -ExecutionPolicy Bypass -File "%PS_TMP%" >> "%LOG_FILE%" 2>&1
del "%PS_TMP%"
if exist "%SHORTCUT%" (
    echo  [OK] Desktop shortcut created: STARLINCS
) else (
    echo  [WARN] Shortcut creation failed - you can still run via LAUNCH_STARLINCS.vbs
)



:: ── 7. Clean up legacy install artifacts ────────────────────────────────────
echo.
echo [7/8] Cleaning up legacy install artifacts...

if exist "%LOCALAPPDATA%\Programs\starlincs" (
    rmdir /s /q "%LOCALAPPDATA%\Programs\starlincs" >nul 2>&1
    echo  [OK] Removed legacy folder: %LOCALAPPDATA%\Programs\starlincs
    echo  [OK] Removed legacy folder: %LOCALAPPDATA%\Programs\starlincs >> "%LOG_FILE%"
) else (
    echo  [SKIP] No legacy launcher folder found
)

:: Sanitize user PATH of any old/corrupted STARLINCS entries (stray "=" or quotes
:: left behind by previous setx-based installs), regardless of install method used.
set "PS_SANITIZE=%TEMP%\starlincs_path_sanitize.ps1"
(
	echo $old = [Environment]::GetEnvironmentVariable('Path','User') > "%PS_SANITIZE%"
	echo if ($null -eq $old) { $old = '' } >> "%PS_SANITIZE%"
	echo $old = $old.Trim([char]34) >> "%PS_SANITIZE%"
	echo $parts = $old -split ';' ^| ForEach-Object { $_.Trim([char]34) } >> "%PS_SANITIZE%"
	echo $parts = $parts ^| Where-Object { $_ -and ($_ -ne '=') } >> "%PS_SANITIZE%"
	echo $cleanDir = '%SCRIPT_DIR%' >> "%PS_SANITIZE%"
	echo if ($cleanDir.EndsWith('\')) { $cleanDir = $cleanDir.Substring(0, $cleanDir.Length-1) } >> "%PS_SANITIZE%"
	echo $legacy = '%LOCALAPPDATA%\Programs\starlincs' >> "%PS_SANITIZE%"
	echo $parts = $parts ^| Where-Object { ($_.TrimEnd('\') -ine $legacy) } >> "%PS_SANITIZE%"
	echo $new = ($parts -join ';') >> "%PS_SANITIZE%"
	echo if ($new -ne $old) { [Environment]::SetEnvironmentVariable('Path', $new, 'User') } >> "%PS_SANITIZE%"
) > "%PS_SANITIZE%"
powershell -NoProfile -ExecutionPolicy Bypass -File "%PS_SANITIZE%" >> "%LOG_FILE%" 2>&1
del "%PS_SANITIZE%"
echo  [OK] User PATH sanitized

:: ── 8. Install global launcher (works from any folder, no PATH edits) ──────
echo.
echo [8/8] Installing global 'starlincs' command...

set "WINAPPS=%LOCALAPPDATA%\Microsoft\WindowsApps"
set "POINTER_DIR=%LOCALAPPDATA%\STARLINCS"
mkdir "%POINTER_DIR%" >nul 2>&1

:: Save the install location (without trailing backslash) so the shim can find it
set "INSTALL_DIR_CLEAN=%SCRIPT_DIR%"
if "%INSTALL_DIR_CLEAN:~-1%"=="\" set "INSTALL_DIR_CLEAN=%INSTALL_DIR_CLEAN:~0,-1%"
(echo %INSTALL_DIR_CLEAN%) > "%POINTER_DIR%\install_path.txt"
echo  [OK] Install path saved to %POINTER_DIR%\install_path.txt

if not exist "%WINAPPS%" (
    echo  [WARN] %WINAPPS% not found - creating it
    mkdir "%WINAPPS%" >nul 2>&1
)

if exist "%WINAPPS%" (
    (
        echo @echo off
        echo setlocal EnableDelayedExpansion
        echo set /p INSTALL_DIR=^<"%POINTER_DIR%\install_path.txt"
        echo if "^!INSTALL_DIR:~-1^!"=="\" set "INSTALL_DIR=^!INSTALL_DIR:~0,-1^!"
        echo if not exist "^!INSTALL_DIR^!\starlincs\cli.py" ^(
        echo     echo STARLINCS: cannot find "^!INSTALL_DIR^!\starlincs\cli.py"
        echo     echo   Move the folder back, or re-run install-windows.bat from the new location.
        echo     exit /b 1
        echo ^)
        echo "^!INSTALL_DIR^!\.venv\Scripts\python.exe" "^!INSTALL_DIR^!\starlincs\cli.py" %%*
    ) > "%WINAPPS%\starlincs.bat"
    echo  [OK] 'starlincs' command installed - works from any folder, any new terminal
    echo  [OK] Global launcher installed at %WINAPPS%\starlincs.bat >> "%LOG_FILE%"
) else (
    echo  [WARN] Could not create %WINAPPS% - falling back to PATH entry
    set "PS_PATH_TMP=%TEMP%\starlincs_path_add.ps1"
    (
        echo $dir = '%SCRIPT_DIR%'
        echo if ^($dir.EndsWith^('\'^)^) { $dir = $dir.Substring^(0, $dir.Length-1^) }
        echo $old = [Environment]::GetEnvironmentVariable^('Path','User'^)
        echo if ^($null -eq $old^) { $old = '' }
        echo $parts = $old -split ';' ^| Where-Object { $_ -and ^($_.Trim^(^) -ne ''^) }
        echo $exists = $parts ^| Where-Object { $_.TrimEnd^('\'^) -ieq $dir }
        echo if ^(-not $exists^) { $parts += $dir }
        echo $new = ^($parts -join ';'^)
        echo [Environment]::SetEnvironmentVariable^('Path','User',$new^)
    ) > "%PS_PATH_TMP%"
    powershell -NoProfile -ExecutionPolicy Bypass -File "%PS_PATH_TMP%" >> "%LOG_FILE%" 2>&1
    del "%PS_PATH_TMP%"
    echo  [OK] Added install folder to user PATH
)

:: ── Done ──────────────────────────────────────────────────────────────────────
echo.
echo  ==================================================================
echo   Installation complete!
echo  ==================================================================
echo.
echo  How to launch STARLINCS:
echo    1. Double-click the "STARLINCS" icon on your Desktop (GUI)
echo    2. Double-click LAUNCH_STARLINCS.vbs in this folder (GUI)
echo    3. Or open a NEW terminal anywhere and run: starlincs --help (CLI)
echo.
echo  Note: 'starlincs' will only work in terminals opened AFTER this
echo  install finished. Close and reopen any open Command Prompt windows.
echo.
echo  Full install log saved to: %LOG_FILE%
echo.
pause
