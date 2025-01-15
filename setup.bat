@echo off
echo Setting up ECB Bot...

:: Check Python installation
python --version 2>nul || (
    echo Python is not installed! Please install Python first.
    exit /b 1
)

:: Create virtual environment
python -m venv .venv

:: Activate virtual environment
call .venv\Scripts\activate

:: Install requirements
pip install -r requirements.txt

:: Create .env if not exists
if not exist .env (
    echo Creating .env file...
    (
    echo MT5_LOGIN=your_login
    echo MT5_PASSWORD=your_password
    echo MT5_SERVER=your_server
    echo tradekey=your_trade_key
    echo SECRET_KEY=your_secret_key
    echo FLASK_ENV=development
    echo ADMIN_USER=admin
    echo ADMIN_PASS=admin
    echo TELEGRAM_BOT_TOKEN=your_token
    echo TELEGRAM_GROUP_ID=your_group_id
    ) > .env
)

:: Create database and admin user
python create_admin.py

echo Setup complete! Run 'start.bat' to launch the application.
pause