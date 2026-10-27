@echo off
setlocal EnableExtensions
pushd "%~dp0"
if errorlevel 1 exit /b 1

echo QlikGPT: creating or reusing the three Qlik applications...
call "%~dp0create-apps.cmd"
if errorlevel 1 (
    echo ERROR: App creation step failed.
    popd
    endlocal & exit /b 1
)

echo QlikGPT: deploying scripts and running the QVD pipeline...
call "%~dp0deploy-all.cmd"
if errorlevel 1 (
    echo ERROR: Pipeline deployment failed.
    popd
    endlocal & exit /b 1
)

echo.
echo QlikGPT pipeline completed.
popd
endlocal & exit /b 0
