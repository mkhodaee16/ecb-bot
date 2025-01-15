@echo off
echo Starting services...

:: Check for .env file
if not exist .env (
    echo Creating .env file...
    echo ADMIN_USER=admin>.env
    echo ADMIN_PASS=admin>>.env
    echo TELEGRAM_BOT_TOKEN=your_token>>.env
    echo TELEGRAM_CHAT_ID=your_chat_id>>.env
)

:: Activate virtual environment
call .venv\Scripts\activate

:: Create admin user first
python create_admin.py
if errorlevel 1 (
    echo Failed to create admin user
    exit /b 1
)

:: Verify Telegram credentials
python -c "from services.telegram_service import TelegramService; TelegramService().test_connection()"
if errorlevel 1 (
    echo Warning: Telegram service not configured correctly
    timeout /t 3
)

:: Start ngrok
start cmd /k "ngrok start flask-app --config ngrok.yml"

:: Wait for ngrok to initialize
timeout /t 5

:: Start Flask app
start cmd /k "python app.py"

echo Services started!
