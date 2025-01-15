@echo off
echo Building ECB Bot...

:: Activate virtual environment
call .venv\Scripts\activate

:: Install pyinstaller if not installed
pip install pyinstaller

:: Build executable
pyinstaller --clean --onefile --icon=static/favicon/favicon.ico --add-data "templates;templates" --add-data "static;static" --add-data ".env;." ecb_bot.spec

echo Build complete! Executable is in the dist folder.
pause