@echo off
chcp 65001 >nul
REM DailyPaper scheduled run
REM Task Scheduler runs this daily

set "SCRIPT_DIR=%~dp0"
set "PROJECT_ROOT=%SCRIPT_DIR%.."
cd /d "%PROJECT_ROOT%"
python "%SCRIPT_DIR%run-yesterday-scheduled.py"
exit /b %ERRORLEVEL%
