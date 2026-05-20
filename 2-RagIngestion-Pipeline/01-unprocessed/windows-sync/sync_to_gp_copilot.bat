@echo off
REM sync_to_gp_copilot.bat - Quick sync from Windows to GP-Copilot
REM Double-click this file to sync LLM-Training folder to WSL

echo.
echo ========================================
echo   Syncing to GP-Copilot RAG System
echo ========================================
echo.

REM Run WSL sync command
wsl bash -c "cd /home/jimmie/linkops-industries/GP-copilot && ./sync_windows_to_wsl.sh"

echo.
echo ========================================
echo   Sync Complete!
echo ========================================
echo.
echo Files are now in WSL at:
echo   ~/linkops-industries/GP-copilot/GP-RAG/unprocessed/windows-sync
echo.
echo To learn from these files, run in WSL:
echo   python GP-RAG/simple_learn.py
echo.
pause