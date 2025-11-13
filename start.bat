@echo off
REM Windows startup script for Crawl4AI with Playwright
REM This ensures the correct asyncio event loop policy is used

echo Starting Web Crawling Agent API...
echo Setting up Windows compatibility for Playwright...

REM Set Python to use WindowsSelectorEventLoop
set PYTHONASYNCIODEBUG=1

REM Start the server
python main.py

pause
