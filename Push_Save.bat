@echo off
echo Pushing Minecraft save to GitHub...
echo.

set REPO_URL=https://github.com/tadhanihiren/Minecraft_BMC_1.16_Save.git
set SAVE_DIR=%~dp0golida

if not exist "%SAVE_DIR%" (
    echo Error: Save folder not found at %SAVE_DIR%
    pause
    exit /b 1
)

set TEMP_REPO=%TEMP%\Minecraft_BMC_Push

if exist "%TEMP_REPO%" rmdir /s /q "%TEMP_REPO%"

echo Cloning repository...
git clone %REPO_URL% "%TEMP_REPO%"

echo Copying save files...
xcopy /E /I /Y "%SAVE_DIR%" "%TEMP_REPO%"

echo Adding and committing...
cd /d "%TEMP_REPO%"
git add -A
git commit -m "Update save %date% %time:~0,5%"

echo Pushing to GitHub...
git push

echo Cleaning up...
rmdir /s /q "%TEMP_REPO%"

echo.
echo Done! Save uploaded to GitHub.
pause
