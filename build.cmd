@echo off
setlocal EnableExtensions
cd /d "%~dp0"

if not exist "dist" mkdir "dist"

REM Combine ETL1 -> ETL2 -> PRESENTATION into the app load script.
copy /b "scripts\etl1.qvs"+"scripts\etl2.qvs"+"scripts\presentation.qvs" "dist\load.qvs" >nul
if errorlevel 1 (
    echo ERROR: Could not generate dist\load.qvs
    exit /b 1
)
echo OK: Created dist\load.qvs from 3 QVS files.

if /I not "%~1"=="deploy" (
    echo To deploy: set QLIK_APP_ID=your-app-id
    echo            build.cmd deploy
    exit /b 0
)

if "%QLIK_APP_ID%"=="" (
    echo ERROR: Set QLIK_APP_ID in this CMD session first.
    exit /b 1
)

set "QLIK_BIN=qlik.exe"
if exist "%~dp0qlik.exe" set "QLIK_BIN=%~dp0qlik.exe"

echo Deploying ONLY app %QLIK_APP_ID% ...
"%QLIK_BIN%" app build --app "%QLIK_APP_ID%" --script "dist\load.qvs"
if errorlevel 1 (
    echo ERROR: Qlik build/reload failed. Check CLI output.
    exit /b 1
)

echo Verifying the loaded order count ...
"%QLIK_BIN%" app eval "Count(OrderID)" --app "%QLIK_APP_ID%"
if errorlevel 1 (
    echo ERROR: App verification failed.
    exit /b 1
)
echo Done.
