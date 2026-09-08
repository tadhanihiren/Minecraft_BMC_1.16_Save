@echo off
echo ============================================
echo  Pulling Minecraft save from GitHub
echo ============================================
echo.

set SAVE_DIR=%~dp0golida
set REPO_URL=https://github.com/tadhanihiren/Minecraft_BMC_1.16_Save.git

rem ---- 0. Nothing to do if no local save ----
if not exist "%SAVE_DIR%" goto freshclone

rem ---- 1. Check if local differs from GitHub (would a merge conflict / overwrite lose anything?) ----
echo Checking for differences with GitHub...
cd /d "%TEMP%"
if exist "%TEMP%\Minecraft_BMC_Check" rmdir /s /q "%TEMP%\Minecraft_BMC_Check"
git clone --quiet %REPO_URL% "%TEMP%\Minecraft_BMC_Check"
if %errorlevel% neq 0 (
    echo Error: could not reach GitHub. Skipping change check.
    goto freshclone
)

set HAS_DIFF=
for /f "delims=" %%i in ('robocopy "%SAVE_DIR%" "%TEMP%\Minecraft_BMC_Check" /L /NJH /NJS /NFL /NDL ^| findstr /i "Newer Older"') do set HAS_DIFF=1
rmdir /s /q "%TEMP%\Minecraft_BMC_Check"

rem ---- 2. Only back up as ZIP if there are differences (i.e. local changes would be lost) ----
if defined HAS_DIFF (
    echo.
    echo Local save has changes that differ from GitHub.
    echo Backing up local save as ZIP before overwriting...
    for /f "tokens=2 delims==" %%a in ('wmic os get localdatetime /value ^| find "="') do set DT=%%a
    set ZIPNAME=golida_backup_%DT:~0,14%.zip
    powershell -NoProfile -Command "Compress-Archive -Path '%SAVE_DIR%\*' -DestinationPath '%~dp0%ZIPNAME%' -Force"
    echo Backup done: %~dp0%ZIPNAME%
    echo.
) else (
    echo No local changes - no backup needed.
)

:freshclone
rem ---- 3. Delete old save and fresh clone (overwrite) ----
if exist "%SAVE_DIR%" rmdir /s /q "%SAVE_DIR%"
echo Downloading save from GitHub...
git clone %REPO_URL% "%SAVE_DIR%"
if %errorlevel% neq 0 (
    echo Error: Failed to download! Backup ZIP (if any) is still in this folder.
    pause
    exit /b 1
)

echo.
echo ============================================
echo  Done! Save downloaded to %SAVE_DIR%
echo ============================================
pause
