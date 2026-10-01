@echo off
rem ============================================================
rem  One-click launcher - no manual setup needed
rem ============================================================
cd /d "%~dp0"
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0run.ps1"