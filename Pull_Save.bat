@echo off
echo Pulling Minecraft save from GitHub...
echo.

set REPO_URL=https://github.com/tadhanihiren/Minecraft_BMC_1.16_Save.git
set SAVE_DIR=F:\Saves\golida

if exist "%SAVE_DIR%" (
    echo Save folder already exists. Backing up...
    ren "%SAVE_DIR%" "golida_backup_%date:~-4%%date:~4,2%%date:~7,2%"
)

echo Cloning repository...
git clone %REPO_URL% "%TEMP%\Minecraft_BMC_Save"

if %errorlevel% neq 0 (
    echo Error: Failed to clone repository!
    pause
    exit /b 1
)

echo Copying to saves...
mkdir "%SAVE_DIR%"
xcopy /E /I /Y "%TEMP%\Minecraft_BMC_Save" "%SAVE_DIR%"

echo Cleaning up...
rmdir /s /q "%TEMP%\Minecraft_BMC_Save"

echo.
echo Done! Save is ready.
pause
