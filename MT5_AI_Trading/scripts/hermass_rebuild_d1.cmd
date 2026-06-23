@echo off
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0hermass_task_runner.ps1" -Action rebuild-d1 -ConfirmFullRebuild
exit /b %ERRORLEVEL%
