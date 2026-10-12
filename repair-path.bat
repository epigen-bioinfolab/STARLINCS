@echo off
title STARLINCS PATH Repair
echo.
echo  ==================================================================
echo                    User PATH Repair Tool
echo  ==================================================================
echo.
echo  This fixes common corruption left by 'setx PATH ...':
echo    - stray '=' entries
echo    - trailing/embedded stray quote characters
echo    - duplicate entries
echo.
echo  Your PATH will NOT be shortened or have entries removed,
echo  other than the junk described above.
echo.
set "PS_TMP=%TEMP%\starlincs_path_repair.ps1"
echo $old = [Environment]::GetEnvironmentVariable('Path','User') > "%PS_TMP%"
echo if ($null -eq $old) { $old = '' } >> "%PS_TMP%"
echo Write-Host "Before:" >> "%PS_TMP%"
echo Write-Host $old >> "%PS_TMP%"
echo Write-Host "" >> "%PS_TMP%"
echo $old = $old.Trim([char]34) >> "%PS_TMP%"
echo $parts = $old -split ';' ^| ForEach-Object { $_.Trim().Trim([char]34) } >> "%PS_TMP%"
echo $parts = $parts ^| Where-Object { $_ -and ($_ -ne '=') } >> "%PS_TMP%"
echo $seen = @{} >> "%PS_TMP%"
echo $clean = @() >> "%PS_TMP%"
echo foreach ($p in $parts) { >> "%PS_TMP%"
echo     $key = $p.TrimEnd('\').ToLowerInvariant() >> "%PS_TMP%"
echo     if (-not $seen.ContainsKey($key)) { >> "%PS_TMP%"
echo         $seen[$key] = $true >> "%PS_TMP%"
echo         $clean += $p >> "%PS_TMP%"
echo     } >> "%PS_TMP%"
echo } >> "%PS_TMP%"
echo $new = ($clean -join ';') >> "%PS_TMP%"
echo [Environment]::SetEnvironmentVariable('Path', $new, 'User') >> "%PS_TMP%"
echo Write-Host "After:" >> "%PS_TMP%"
echo Write-Host $new >> "%PS_TMP%"
powershell -NoProfile -ExecutionPolicy Bypass -File "%PS_TMP%"
del "%PS_TMP%"
echo.
echo  ==================================================================
echo   Done. Close and reopen any terminal windows for the fix to apply.
echo  ==================================================================
echo.
pause