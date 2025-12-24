@echo off
echo Capturing error output from Clone Hero Score Tracker...
echo.
cd /d "%~dp0"
dist\CloneHeroScoreTracker_v2.4.12.exe > error_log.txt 2>&1
echo.
echo Program exited. Error log saved to error_log.txt
echo.
type error_log.txt
echo.
echo.
pause
