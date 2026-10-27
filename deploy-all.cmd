@echo off
setlocal EnableExtensions
pushd "%~dp0"
if errorlevel 1 exit /b 1

set "QLIK_BIN=qlik.exe"
if exist "%~dp0qlik.exe" set "QLIK_BIN=%~dp0qlik.exe"

if not exist ".local\app-ids.cmd" (
    echo ERROR: App IDs not found. Run create-apps.cmd first.
    goto :failed
)
call ".local\app-ids.cmd"

if not defined QLIK_ETL1_APP_ID goto :missing
if not defined QLIK_ETL2_APP_ID goto :missing
if not defined QLIK_PRESENTATION_APP_ID goto :missing

REM Validate all three target apps before writing any script.
"%QLIK_BIN%" app get "%QLIK_ETL1_APP_ID%" >nul
if errorlevel 1 goto :failed
"%QLIK_BIN%" app get "%QLIK_ETL2_APP_ID%" >nul
if errorlevel 1 goto :failed
"%QLIK_BIN%" app get "%QLIK_PRESENTATION_APP_ID%" >nul
if errorlevel 1 goto :failed

echo.
echo =====================================================
echo QlikGPT - DEPLOY THREE APPS IN QVD DEPENDENCY ORDER
echo =====================================================

echo [1/3] ETL1: update script, reload and STORE RAW QVD
"%QLIK_BIN%" app build --app "%QLIK_ETL1_APP_ID%" --script "scripts\etl1.qvs"
if errorlevel 1 goto :failed

echo [2/3] ETL2: read RAW, transform and STORE clean QVD
"%QLIK_BIN%" app build --app "%QLIK_ETL2_APP_ID%" --script "scripts\etl2.qvs"
if errorlevel 1 goto :failed

echo [3/3] Presentation: read clean QVD, load data model
"%QLIK_BIN%" app build --app "%QLIK_PRESENTATION_APP_ID%" --script "scripts\presentation.qvs"
if errorlevel 1 goto :failed

echo.
echo Checking record count in PRESENTATION ...
"%QLIK_BIN%" app eval "Count(OrderID)" --app "%QLIK_PRESENTATION_APP_ID%"
if errorlevel 1 goto :failed

echo.
echo SUCCESS: All 3 QlikGPT apps built and reloaded.
echo Expected count in Presentation: 5000
echo Actual count is shown above.
popd
endlocal & exit /b 0

:missing
echo ERROR: One or more App IDs are missing from .local\app-ids.cmd.
:failed
echo.
echo STOP: Deployment did not complete. Later layers were not run.
echo Inspect the Qlik CLI error or reload logs above.
popd
endlocal & exit /b 1
