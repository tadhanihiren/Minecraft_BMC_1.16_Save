@echo off
echo Pulling latest save from GitHub (merges, keeps local changes)...
echo.

set REPO_URL=https://github.com/tadhanihiren/Minecraft_BMC_1.16_Save.git
set SAVE_DIR=%~dp0golida

if exist "%SAVE_DIR%\.git" (
    rem Already a git repo - just pull latest
    cd /d "%SAVE_DIR%"
    rem save any uncommitted local changes
    git stash
    git pull
    git stash pop
    echo.
    echo Done! Save updated.
    pause
    exit /b 0
)

if exist "%SAVE_DIR%" (
    echo Existing golida folder found but it's not a git repo.
    echo Converting it to a git repo before pulling...
    cd /d "%SAVE_DIR%"
    git init
    git remote add origin %REPO_URL%
    git fetch origin
    git checkout -b main origin/main
    echo.
    echo Done! Save merged with GitHub.
    pause
    exit /b 0
)

echo No save folder found. Cloning fresh copy...
git clone %REPO_URL% "%SAVE_DIR%"
echo.
echo Done! Save downloaded.
pause
