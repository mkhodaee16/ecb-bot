@echo off
echo Resetting services...

:: Kill all ngrok processes
taskkill /F /IM ngrok.exe 2>nul

:: Clear ngrok sessions
del /F /Q "%TEMP%\ngrok*" 2>nul
del /F /Q "%USERPROFILE%\.ngrok2\ngrok.yml" 2>nul

:: Clear telegram cache
del /F /Q "telegram_cache.txt" 2>nul

:: Wait for processes to close
timeout /t 3 /nobreak

:: Configure ngrok
ngrok config add-authtoken 2repyZpBG4BN6WVJj0jqW0VvHjM_H5DYxaWyYUA7aHytkm5K

:: Start services again
call start.bat

echo Reset complete!