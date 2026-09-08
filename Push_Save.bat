@echo off
echo Pushing save changes to GitHub...
echo.

set REPO_URL=https://github.com/tadhanihiren/Minecraft_BMC_1.16_Save.git
set SAVE_DIR=%~dp0golida

if not exist "%SAVE_DIR%" (
    echo Error: Save folder not found at %SAVE_DIR%
    pause
    exit /b 1
)

if not exist "%SAVE_DIR%\.git" (
    echo Converting save folder into a git repo...
    cd /d "%SAVE_DIR%"
    git init
    git remote add origin %REPO_URL%
    git fetch origin
    git checkout -b main origin/main 2>nul
)

cd /d "%SAVE_DIR%"

echo Adding changes...
git add -A

echo Checking what changed...
git status

set CHANGED=
for /f %%i in ('git status --porcelain') do set CHANGED=1
if not defined CHANGED (
    echo No changes to push.
    pause
    exit /b 0
)

echo Committing changes...
git commit -m "Update save %date% %time:~0,5%"

echo Pushing to GitHub...
git pull --rebase
git push

echo.
echo Done! Changes uploaded to GitHub.
pause
