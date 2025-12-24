@echo off
echo Starting Clone Hero Score Tracker v2.4.12...
echo.
cd /d "%~dp0"
dist\CloneHeroScoreTracker_v2.4.12.exe 2>&1
echo.
echo.
echo Program exited. Press any key to close this window...
pause > nul
