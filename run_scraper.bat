@echo off
REM Run Python scraper with parameters
call C:\scraper_amazon\.venv\Scripts\activate
python C:\scraper_amazon\main.py %1 %2
