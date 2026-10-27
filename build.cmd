@echo off
REM Backwards-compatible entry point.
REM QlikGPT now uses three distinct apps and two QVD handoffs.
call "%~dp0run-pipeline.cmd"
exit /b %errorlevel%
