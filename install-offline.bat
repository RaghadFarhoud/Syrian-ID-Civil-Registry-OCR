@echo off
rem ============================================================
rem  Offline setup - run ONCE after unpacking the project.
rem  No internet required. Then just use start.bat forever.
rem ============================================================
cd /d "%~dp0"
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0install-offline.ps1"
