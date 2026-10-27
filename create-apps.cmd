@echo off
setlocal EnableExtensions
pushd "%~dp0"
if errorlevel 1 exit /b 1

set "QLIK_BIN=qlik.exe"
if exist "%~dp0qlik.exe" set "QLIK_BIN=%~dp0qlik.exe"

"%QLIK_BIN%" version >nul 2>&1
if errorlevel 1 (
    echo ERROR: qlik.exe not found. Put qlik.exe beside this script or on PATH.
    goto :failed
)
"%QLIK_BIN%" user me >nul 2>&1
if errorlevel 1 (
    echo ERROR: Qlik authentication failed. Check your active qlik context.
    goto :failed
)

if not exist ".local" mkdir ".local"
if exist ".local\app-ids.cmd" call ".local\app-ids.cmd"

echo.
echo =====================================================
echo QlikGPT - CREATE 3 SEPARATE QLIK CLOUD APPLICATIONS
echo =====================================================
if defined QLIK_SPACE_ID (
    echo Target: shared space ID %QLIK_SPACE_ID%
) else (
    echo Target: your personal space
)

if not defined QLIK_ETL1_APP_ID call :createApp "QlikGPT - 01 ETL RAW" "QVD RAW extract layer" QLIK_ETL1_APP_ID
if errorlevel 1 goto :failed
if not defined QLIK_ETL2_APP_ID call :createApp "QlikGPT - 02 ETL TRANSFORM" "QVD transform layer" QLIK_ETL2_APP_ID
if errorlevel 1 goto :failed
if not defined QLIK_PRESENTATION_APP_ID call :createApp "QlikGPT - 03 PRESENTATION" "Associative analytics model" QLIK_PRESENTATION_APP_ID
if errorlevel 1 goto :failed

echo.
echo ETL1 App ID:         %QLIK_ETL1_APP_ID%
echo ETL2 App ID:         %QLIK_ETL2_APP_ID%
echo Presentation App ID: %QLIK_PRESENTATION_APP_ID%
echo IDs saved in .local\app-ids.cmd (excluded from Git).
popd
endlocal & exit /b 0

:createApp
echo Creating %~1 ...
if defined QLIK_SPACE_ID (
    "%QLIK_BIN%" app create --attributes-name "%~1" --attributes-description "%~2" --attributes-usage ANALYTICS --attributes-spaceId "%QLIK_SPACE_ID%" --quiet >".local\new-app-id.tmp"
) else (
    "%QLIK_BIN%" app create --attributes-name "%~1" --attributes-description "%~2" --attributes-usage ANALYTICS --quiet >".local\new-app-id.tmp"
)
if errorlevel 1 (
    echo ERROR: App creation failed for %~1.
    exit /b 1
)
set "NEW_ID="
set /p "NEW_ID="<".local\new-app-id.tmp"
del /q ".local\new-app-id.tmp" >nul 2>&1
if not defined NEW_ID (
    echo ERROR: Qlik did not return an app ID.
    exit /b 1
)
"%QLIK_BIN%" app get "%NEW_ID%" >nul
if errorlevel 1 (
    echo ERROR: The app ID returned by Qlik could not be verified: %NEW_ID%
    exit /b 1
)
set "%~3=%NEW_ID%"
>>".local\app-ids.cmd" echo set "%~3=%NEW_ID%"
echo Created: %~1 : %NEW_ID%
exit /b 0

:failed
echo.
echo STOP: QlikGPT application creation not completed.
popd
endlocal & exit /b 1
