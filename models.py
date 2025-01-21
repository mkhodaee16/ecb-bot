from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from datetime import datetime

db = SQLAlchemy()

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(120), nullable=False)

class MT5Account(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    login = db.Column(db.String(50), unique=True, nullable=False)
    password = db.Column(db.String(100), nullable=False)
    server = db.Column(db.String(100), nullable=False)
    name = db.Column(db.String(100))
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class RestrictedSymbol(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    account_id = db.Column(db.Integer, db.ForeignKey('mt5_account.id'), nullable=False)
    symbol = db.Column(db.String(20), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class TradeLog(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    account_id = db.Column(db.Integer, db.ForeignKey('mt5_account.id'), nullable=False)
    symbol = db.Column(db.String(20))
    action = db.Column(db.String(20))
    type = db.Column(db.String(20))
    volume = db.Column(db.Float)
    price = db.Column(db.Float)
    sl = db.Column(db.Float)
    tp = db.Column(db.Float)
    profit = db.Column(db.Float)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class WebhookLog(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    payload = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class Position(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    account_id = db.Column(db.Integer, db.ForeignKey('mt5_account.id'), nullable=False)
    ticket = db.Column(db.Integer, unique=True)
    symbol = db.Column(db.String(20))
    type = db.Column(db.String(20))
    volume = db.Column(db.Float)
    price_open = db.Column(db.Float)
    price_close = db.Column(db.Float, nullable=True)
    sl = db.Column(db.Float)
    tp = db.Column(db.Float)
    profit = db.Column(db.Float, nullable=True)
    status = db.Column(db.String(20), default='Pending')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    closed_at = db.Column(db.DateTime, nullable=True)

class AppSettings(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    key = db.Column(db.String(100), unique=True, nullable=False)
    value = db.Column(db.String(500))
    category = db.Column(db.String(50))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)