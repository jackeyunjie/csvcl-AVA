@echo off
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0hermass_task_runner.ps1" -Action update-m15 -NoContraction
exit /b %ERRORLEVEL%
