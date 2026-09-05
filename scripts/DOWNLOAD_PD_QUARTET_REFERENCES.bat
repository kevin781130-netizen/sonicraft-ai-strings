@echo off
cd /d "%~dp0.."
python training\scripts\fetch_wikimedia_pd_quartets.py
pause
