from dotenv import load_dotenv
from models import db, AppSettings
from flask import Flask
import os

app = Flask(__name__)

# Database configuration
app.config['SQLALCHEMY_DATABASE_URI'] = (
    f"mysql+pymysql://root:awjjJF3HbxM7CbnBu7Ek@"
    f"tradingdb-iqi-service:3306/tradingdjjm_db"
)
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db.init_app(app)

def migrate_env_to_db():
    load_dotenv()
    
    settings = {
        'MT5': {
            'MT5_LOGIN': os.getenv('MT5_LOGIN'),
            'MT5_PASSWORD': os.getenv('MT5_PASSWORD'),
            'MT5_SERVER': os.getenv('MT5_SERVER')
        },
        'SECURITY': {
            'tradekey': os.getenv('tradekey'),
            'SECRET_KEY': os.getenv('SECRET_KEY')
        },
        'ADMIN': {
            'ADMIN_USER': os.getenv('ADMIN_USER'),
            'ADMIN_PASS': os.getenv('ADMIN_PASS')
        },
        'TELEGRAM': {
            'TELEGRAM_BOT_TOKEN': os.getenv('TELEGRAM_BOT_TOKEN'),
            'TELEGRAM_GROUP_ID': os.getenv('TELEGRAM_GROUP_ID')
        }
    }
    
    with app.app_context():
        db.create_all()
        for category, items in settings.items():
            for key, value in items.items():
                if value:  # Only add if value exists
                    setting = AppSettings(
                        key=key,
                        value=value,
                        category=category
                    )
                    db.session.add(setting)
        db.session.commit()

if __name__ == "__main__":
    migrate_env_to_db()