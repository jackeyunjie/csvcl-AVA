@echo off
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0hermass_task_runner.ps1" -Action update-h1 -NoContraction
exit /b %ERRORLEVEL%
