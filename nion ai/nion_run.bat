@echo off
title Zora AI Assistant
echo ==============================================
echo        Starting Zora AI System...
echo ==============================================
echo.

:: Start the main MJ agent in console mode with your Headphone Mic
echo Starting Zora Agent (Console Mode)...
echo.
python agent.py console --input-device 10 --output-device 14

echo.
echo Zora has stopped.
pause
