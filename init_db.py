import mysql.connector
import os
from dotenv import load_dotenv
from flask import Flask
from sqlalchemy import create_engine, text
from sqlalchemy_utils import database_exists, create_database
from flask_sqlalchemy import SQLAlchemy

load_dotenv()

def get_database_uri():
    return f"mysql+mysqlconnector://{os.getenv('MYSQL_USER')}:{os.getenv('MYSQL_PASSWORD')}@{os.getenv('MYSQL_HOST')}:{os.getenv('MYSQL_PORT')}/{os.getenv('MYSQL_DATABASE')}"

def init_database():
    try:
        uri = get_database_uri()
        if not database_exists(uri):
            create_database(uri)
            print(f"Created database {os.getenv('MYSQL_DATABASE')}")
        
        engine = create_engine(uri)
        with engine.connect() as conn:
            with open('schema.sql', 'r') as f:
                queries = f.read().split(';')
                for query in queries:
                    if query.strip():
                        conn.execute(text(query))
                conn.commit()
        
        return uri
    except Exception as e:
        print(f"Database initialization error: {e}")
        return None

# Initialize Flask app
app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = get_database_uri()
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY')
# Initialize extensions
db = SQLAlchemy()
# Initialize extensions
db.init_app(app)

with app.app_context():
    db.create_all()

if __name__ == '__main__':
    init_database()