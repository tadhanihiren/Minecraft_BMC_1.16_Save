@echo off
echo ============================================
echo  Pulling Minecraft save from GitHub
echo  (local save is backed up first as ZIP)
echo ============================================
echo.

set SAVE_DIR=%~dp0golida
set REPO_URL=https://github.com/tadhanihiren/Minecraft_BMC_1.16_Save.git

rem ---- 1. Back up current local save as ZIP ----
if exist "%SAVE_DIR%\*.dat" (
    for /f "tokens=2 delims==" %%a in ('wmic os get localdatetime /value ^| find "="') do set DT=%%a
    set ZIPNAME=golida_backup_%DT:~0,14%.zip
    set ZIPNAME=%ZIPNAME: =%
    echo Backing up current save to: %ZIPNAME%
    powershell -NoProfile -Command "Compress-Archive -Path '%SAVE_DIR%\*' -DestinationPath '%~dp0%ZIPNAME%' -Force"
    echo Backup done: %~dp0%ZIPNAME%
) else (
    echo No existing save to back up. Skipping backup.
)

rem ---- 2. Delete old save ----
if exist "%SAVE_DIR%" (
    echo Removing old save...
    rmdir /s /q "%SAVE_DIR%"
)

rem ---- 3. Fresh clone (overwrite) ----
echo Cloning fresh copy from GitHub...
git clone %REPO_URL% "%SAVE_DIR%"

if %errorlevel% neq 0 (
    echo.
    echo Error: Failed to clone! Your backup ZIP is still there.
    pause
    exit /b 1
)

echo.
echo ============================================
echo  Done!
echo  - New save downloaded to %SAVE_DIR%
echo  - Old save backed up as ZIP in this folder
echo ============================================
pause
