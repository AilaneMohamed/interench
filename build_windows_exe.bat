@echo off
setlocal ENABLEDELAYEDEXPANSION
cd /d "%~dp0"

echo ==============================================
echo  Build Windows EXE - Interencheres Public Tracker
echo ==============================================

echo.
where py >nul 2>nul
if %errorlevel%==0 (
  set "PY=py"
) else (
  where python >nul 2>nul
  if %errorlevel%==0 (
    set "PY=python"
  ) else (
    echo Python n'est pas installe ou n'est pas dans le PATH.
    echo Installe Python 3.11+ puis relance ce script.
    pause
    exit /b 1
  )
)

if not exist .venv (
  echo [1/5] Creation de l'environnement virtuel...
  %PY% -m venv .venv
  if errorlevel 1 (
    echo Echec creation environnement virtuel.
    pause
    exit /b 1
  )
)

echo [2/5] Activation environnement virtuel...
call .venv\Scripts\activate.bat
if errorlevel 1 (
  echo Echec activation environnement virtuel.
  pause
  exit /b 1
)

echo [3/5] Installation dependances build...
python -m pip install --upgrade pip
python -m pip install -r requirements-build.txt
if errorlevel 1 (
  echo Echec installation dependances.
  pause
  exit /b 1
)

echo [4/5] Nettoyage anciens builds...
if exist build rmdir /s /q build
if exist dist rmdir /s /q dist

echo [5/5] Generation EXE...
pyinstaller InterencheresPublicTracker.spec --noconfirm
if errorlevel 1 (
  echo Echec pendant PyInstaller.
  pause
  exit /b 1
)

echo.
echo ==============================================
echo  Build termine.
echo  EXE: dist\InterencheresPublicTracker.exe
echo ==============================================
start "" explorer "%cd%\dist"
pause
