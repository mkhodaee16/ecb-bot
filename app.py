from flask import Flask, render_template, request, jsonify, redirect, url_for, flash
from flask_socketio import SocketIO
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
import os
import logging
from datetime import datetime
from dotenv import load_dotenv
import MetaTrader5 as mt5
import threading
import time
from services.telegram_service import TelegramService
from functools import wraps
from models import MT5Account, RestrictedSymbol, TradeLog, WebhookLog, Position, Webhook, Log
import urllib.parse
from sqlalchemy_utils import database_exists, create_database
import pymysql
from sqlalchemy import create_engine
from init_db import init_database
init_database()

# Load environment variables and configure logging
load_dotenv()
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
def get_database_uri():
    host = os.getenv('MYSQL_HOST')
    port = os.getenv('MYSQL_PORT')
    user = os.getenv('MYSQL_USER')
    password = os.getenv('MYSQL_PASSWORD')
    database = os.getenv('MYSQL_DATABASE')
    
    return f"mysql+pymysql://{user}:{password}@{host}:{port}/{database}"

def init_database():
    try:
        uri = get_database_uri()
        retries = 3
        while retries > 0:
            try:
                engine = create_engine(uri)
                engine.connect()
                if not database_exists(uri):
                    create_database(uri)
                    logger.info(f"Created database {os.getenv('MYSQL_DATABASE')}")
                return uri
            except Exception as e:
                retries -= 1
                if retries == 0:
                    raise
                logger.warning(f"Connection attempt failed, retrying... ({retries} attempts left)")
                time.sleep(2)
    except Exception as e:
        logger.error(f"Database initialization error: {e}")
        return None

# Update .env configuration
def update_env():
    env_path = os.path.join(os.path.dirname(__file__), '.env')
    with open(env_path, 'r') as file:
        lines = file.readlines()
    
    with open(env_path, 'w') as file:
        for line in lines:
            if 'MYSQL_HOST' in line:
                line = f'MYSQL_HOST=remote.runflare.com:31737\n'
            file.write(line)

# Initialize Flask app
app = Flask(__name__)

# Configure database
db_uri = init_database()
if not db_uri:
    raise RuntimeError("Failed to initialize database")

app.config['SQLALCHEMY_DATABASE_URI'] = db_uri
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY')

# Initialize SQLAlchemy
db = SQLAlchemy(app)

# Create all tables
with app.app_context():
    try:
        db.create_all()
        logger.info("Database tables created successfully") 
    except Exception as e:
        logger.error(f"Failed to create tables: {e}")
        raise

# Initialize extensions
socketio = SocketIO(app, async_mode='gevent')
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

# Setup logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)
handler = logging.FileHandler('app.log')
logger.addHandler(handler)

# Initialize services
telegram_service = TelegramService()


def init_admin_user():
    try:
        admin = User.query.filter_by(username=os.getenv('ADMIN_USER')).first()
        if not admin:
            admin = User(username=os.getenv('ADMIN_USER'))
            admin.set_password(os.getenv('ADMIN_PASS'))
            db.session.add(admin)
            db.session.commit()
            logger.info("Admin user created successfully")
    except Exception as e:
        logger.error(f"Error creating admin user: {str(e)}")


def safe_init_db():
    try:
        db_path = 'instance/trading_bot.db'
        if os.path.exists(db_path):
            try:
                os.remove(db_path)
                logger.info("Removed existing database")
            except PermissionError:
                logger.error(
                    "Cannot remove database - file is locked. Please close all other instances of the application.")
                return False

        with app.app_context():
            db.create_all()
            logger.info("Created new database successfully")
        return True
    except Exception as e:
        logger.error(f"Database initialization error: {str(e)}")
        return False

def check_auth(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if os.getenv('FLASK_ENV') == 'development':
            return f(*args, **kwargs)
        if not current_user.is_authenticated:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function



class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(200), nullable=False)  

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))

# Custom logging handler to store logs in database


class DatabaseLoggingHandler(logging.Handler):
    def emit(self, record):
        log = Log(
            timestamp=datetime.fromtimestamp(record.created),
            level=record.levelname,
            message=record.getMessage()
        )
        with app.app_context():
            db.session.add(log)
            db.session.commit()


# Logger setup
logger = logging.getLogger()
logger.setLevel(logging.INFO)
logger.addHandler(DatabaseLoggingHandler())


def get_order_type(type_str):
    order_types = {
        "buy limit": mt5.ORDER_TYPE_BUY_LIMIT,
        "sell limit": mt5.ORDER_TYPE_SELL_LIMIT,
        "buy stop": mt5.ORDER_TYPE_BUY_STOP,
        "sell stop": mt5.ORDER_TYPE_SELL_STOP
    }
    return order_types.get(type_str.lower())


def init_mt5():
    if not mt5.initialize():
        logger.error("MT5 initialization failed")
        return False

    if not mt5.login(
        login=int(os.getenv('MT5_LOGIN')),
        password=os.getenv('MT5_PASSWORD'),
        server=os.getenv('MT5_SERVER')
    ):
        logger.error("MT5 login failed")
        return False

    return True


@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('home'))
        
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        app.logger.info(f"Login attempt for user: {username}")
        
        user = User.query.filter_by(username=username).first()
        
        if user and user.check_password(password):
            app.logger.info(f"Login successful for {username}")
            login_user(user)
            return redirect(url_for('home'))
        
        app.logger.error(f"Login failed for {username}")
        flash('Invalid username or password')
    
    return render_template('login.html')


@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

@app.route('/webhook', methods=['POST'])
def webhook():
    try:
        webhook_data = request.get_json()
        logger.info(f"Received webhook data: {webhook_data}")

        # Format validation and standardization
        formatted_data = {
            "password": webhook_data.get("tradekey"),
            "action": webhook_data.get("action"),
            "symbol": webhook_data.get("symbol"),
            "volume": float(webhook_data.get("volume")),
            "order_type": webhook_data.get("order_type"),
            "price": float(webhook_data.get("price")),
            "stop_loss": float(webhook_data.get("stop_loss")),
            "take_profit": float(webhook_data.get("take_profit"))
        }

        # Validate password
        if formatted_data["password"] != os.getenv("tradekey"):
            return jsonify({"error": "Invalid password"}), 403

        # Handle position request
        return handle_position_request(formatted_data)

    except ValueError as e:
        return jsonify({"error": f"Invalid number format: {str(e)}"}), 400
    except Exception as e:
        logger.error(f"Webhook error: {str(e)}")
        return jsonify({"error": str(e)}), 500

def handle_position_request(data):
    try:
        # Delete existing pending orders for this symbol
        delete_pending_orders(data['symbol'])
        
        # Create new position
        position = Position(
            symbol=data['symbol'],
            type=data['order_type'],
            volume=data['volume'],
            price_open=data['price'],
            sl=data['stop_loss'],
            tp=data['take_profit'],
            status='Pending'
        )
        db.session.add(position)
        db.session.commit()

        # Open positions for all active accounts
        accounts = MT5Account.query.filter_by(is_active=True).all()
        for account in accounts:
            if not is_symbol_restricted(account.id, data['symbol']):
                open_position_for_account(account, position)
                
        return jsonify({'status': 'success'})
    except Exception as e:
        logger.error(f"Error handling position: {str(e)}")
        return jsonify({'status': 'error', 'message': str(e)})

def delete_pending_orders(symbol):
    try:
        # Find and delete existing pending orders
        pending_positions = Position.query.filter_by(
            symbol=symbol, 
            status='Pending'
        ).all()
        
        for position in pending_positions:
            # Close MT5 orders
            accounts = MT5Account.query.filter_by(is_active=True).all()
            for account in accounts:
                close_mt5_position(account, position)
            
            # Update database
            position.status = 'Cancelled'
            position.closed_at = datetime.utcnow()
            
        db.session.commit()
    except Exception as e:
        logger.error(f"Error deleting pending orders: {str(e)}")
        raise

def open_position_for_account(account, position):
    if not mt5.initialize():
        raise Exception(f"MT5 initialization failed for account {account.login}")
        
    if not mt5.login(account.login, account.password, account.server):
        raise Exception(f"MT5 login failed for account {account.login}")
    
    try:
        adjusted_volume = position.volume * account.volume_coefficient
        
        request = {
            "action": mt5.TRADE_ACTION_DEAL,
            "symbol": position.symbol,
            "volume": adjusted_volume,
            "type": get_order_type(position.type),
            "price": position.price_open,
            "sl": position.sl,
            "tp": position.tp,
            "deviation": 20,
            "magic": 234000,
            "comment": f"python script {position.id}",
            "type_time": mt5.ORDER_TIME_GTC,
            "type_filling": mt5.ORDER_FILLING_IOC,
        }
        
        result = mt5.order_send(request)
        if result.retcode != mt5.TRADE_RETCODE_DONE:
            raise Exception(f"Order failed: {result.comment}")
            
        # Log trade
        log_trade(account.id, position, result)
        
    finally:
        mt5.shutdown()

def update_trailing_stop():
    open_positions = Position.query.filter_by(status='Open').all()
    
    for position in open_positions:
        current_price = get_current_price(position.symbol)
        
        if position.type.startswith('Buy'):
            new_sl = calculate_trailing_stop(
                current_price, 
                position.price_open, 
                position.sl, 
                'buy'
            )
        else:
            new_sl = calculate_trailing_stop(
                current_price, 
                position.price_open, 
                position.sl, 
                'sell'
            )
            
        if new_sl != position.sl:
            update_position_sl(position, new_sl)

def calculate_trailing_stop(current_price, open_price, current_sl, direction):
    trail_points = 100  # Configurable trailing stop distance
    
    if direction == 'buy':
        potential_sl = current_price - trail_points
        return max(potential_sl, current_sl)
    else:
        potential_sl = current_price + trail_points
        return min(potential_sl, current_sl)

def update_position_sl(position, new_sl):
    try:
        position.sl = new_sl
        db.session.commit()
        
        # Update SL in MT5
        accounts = MT5Account.query.filter_by(is_active=True).all()
        for account in accounts:
            if not is_symbol_restricted(account.id, position.symbol):
                update_mt5_position_sl(account, position)
    except Exception as e:
        logger.error(f"Error updating SL: {str(e)}")
        raise

def update_mt5_position_sl(account, position):
    if not mt5.initialize():
        raise Exception(f"MT5 initialization failed for account {account.login}")
        
    if not mt5.login(account.login, account.password, account.server):
        raise Exception(f"MT5 login failed for account {account.login}")
    
    try:
        request = {
            "action": mt5.TRADE_ACTION_MODIFY,
            "symbol": position.symbol,
            "sl": position.sl,
            "tp": position.tp,
            "position": position.ticket
        }
        
        result = mt5.order_send(request)
        if result.retcode != mt5.TRADE_RETCODE_DONE:
            raise Exception(f"Failed to update SL: {result.comment}")
    finally:
        mt5.shutdown()

def is_symbol_restricted(account_id, symbol):
    restricted_symbols = RestrictedSymbol.query.filter_by(account_id=account_id).all()
    return any(restricted.symbol == symbol for restricted in restricted_symbols)

def price_update_thread(app):
    with app.app_context():
        while True:
            try:
                # Get all active positions
                positions = Position.query.filter(Position.status.in_(['Open', 'Pending'])).all()
                
                price_updates = {}
                for pos in positions:
                    symbol_info = mt5.symbol_info(pos.symbol)
                    if symbol_info is None:
                        continue

                    price = symbol_info.bid if pos.type.lower().includes('buy') else symbol_info.ask
                    change = price - pos.price_open
                    price_updates[pos.symbol] = {
                        'bid': symbol_info.bid,
                        'ask': symbol_info.ask,
                        'change': change
                    }

                    # Update trailing stop
                    update_trailing_stop()

                    # Update position status if needed
                    if pos.status == 'Pending':
                        # Check if pending order should be activated
                        if (pos.type == 'Buy Limit' and price <= pos.price_open) or \
                           (pos.type == 'Sell Limit' and price >= pos.price_open) or \
                           (pos.type == 'Buy Stop' and price >= pos.price_open) or \
                           (pos.type == 'Sell Stop' and price <= pos.price_open):
                            pos.status = 'Open'
                            db.session.commit()
                            # Send telegram notification for status change
                            telegram_service.position_status_changed(pos)
                    elif pos.status == 'Open':
                        # Check for SL/TP
                        if pos.type.startswith('Buy'):
                            if price <= pos.sl:
                                pos.status = 'Closed'
                                pos.price_close = price
                                pos.profit = (price - pos.price_open) * pos.volume * 100000
                                # Send telegram notification for status change
                                telegram_service.position_status_changed(pos)
                            elif price >= pos.tp:
                                pos.status = 'Closed'
                                pos.price_close = price
                                pos.profit = (price - pos.price_open) * pos.volume * 100000
                                # Send telegram notification for status change
                                telegram_service.position_status_changed(pos)
                        else:  # Sell positions
                            if price >= pos.sl:
                                pos.status = 'Closed'
                                pos.price_close = price
                                pos.profit = (pos.price_open - price) * pos.volume * 100000
                                # Send telegram notification for status change
                                telegram_service.position_status_changed(pos)
                            elif price <= pos.tp:
                                pos.status = 'Closed'
                                pos.price_close = price
                                pos.profit = (pos.price_open - price) * pos.volume * 100000
                                # Send telegram notification for status change
                                telegram_service.position_status_changed(pos)

                # Emit price updates via WebSocket
                if price_updates:
                    socketio.emit('price_update', {'prices': price_updates})

                db.session.commit()
                time.sleep(1)

            except Exception as e:
                logger.error(f"Price update error: {str(e)}")
                time.sleep(5)

def log_trade(account_id, position, result):
    log = TradeLog(
        account_id=account_id,
        symbol=position.symbol,
        action='open',
        type=position.type,
        volume=position.volume,
        price=position.price_open,
        sl=position.sl,
        tp=position.tp,
        profit=0  # Initial profit is 0
    )
    db.session.add(log)
    db.session.commit()

def get_current_price(symbol):
    symbol_info = mt5.symbol_info(symbol)
    if symbol_info is None:
        raise Exception(f"Symbol {symbol} not found")
    return symbol_info.bid if symbol_info.bid > 0 else symbol_info.ask

def close_mt5_position(account, position):
    if not mt5.initialize():
        raise Exception(f"MT5 initialization failed for account {account.login}")
        
    if not mt5.login(account.login, account.password, account.server):
        raise Exception(f"MT5 login failed for account {account.login}")
    
    try:
        request = {
            "action": mt5.TRADE_ACTION_DEAL,
            "symbol": position.symbol,
            "volume": position.volume,
            "type": mt5.ORDER_TYPE_SELL if position.type.startswith('Buy') else mt5.ORDER_TYPE_BUY,
            "position": position.ticket,
            "price": mt5.symbol_info_tick(position.symbol).bid
        }
        
        result = mt5.order_send(request)
        if result.retcode != mt5.TRADE_RETCODE_DONE:
            raise Exception(f"Failed to close position: {result.comment}")
    finally:
        mt5.shutdown()
        
    if not mt5.login(account.login, account.password, account.server):
        raise Exception(f"MT5 login failed for account {account.login}")
    
    try:
        request = {
            "action": mt5.TRADE_ACTION_DEAL,
            "symbol": position.symbol,
            "volume": position.volume,
            "type": mt5.ORDER_TYPE_SELL if position.type.startswith('Buy') else mt5.ORDER_TYPE_BUY,
            "position": position.ticket,
            "price": mt5.symbol_info_tick(position.symbol).bid
        }
        
        result = mt5.order_send(request)
        if result.retcode != mt5.TRADE_RETCODE_DONE:
            raise Exception(f"Failed to close position: {result.comment}")
    finally:
        mt5.shutdown()

def get_mt5_order_type(order_type):
    order_types = {
        "buy": mt5.ORDER_TYPE_BUY,
        "sell": mt5.ORDER_TYPE_SELL,
        "buy limit": mt5.ORDER_TYPE_BUY_LIMIT,
        "sell limit": mt5.ORDER_TYPE_SELL_LIMIT,
        "buy stop": mt5.ORDER_TYPE_BUY_STOP,
        "sell stop": mt5.ORDER_TYPE_SELL_STOP
    }
    return order_types.get(order_type.lower(), mt5.ORDER_TYPE_BUY)



@app.route('/')
@check_auth
def home():
    webhooks = Webhook.query.all()
    positions = Position.query.all()
    return render_template('home.html', webhooks=webhooks, positions=positions)



@app.route('/api/position/<int:id>')
def get_position_details(id):
    position = Position.query.get_or_404(id)
    return jsonify({
        'id': position.id,
        'timestamp': position.timestamp,
        'symbol': position.symbol,
        'ticket': position.ticket,
        'type': position.type,
        'volume': position.volume,
        'price_open': position.price_open,
        'sl': position.sl,
        'tp': position.tp,
        'profit': position.profit,
        'status': position.status
    })


@app.route('/api/webhook/<int:id>')
def get_webhook_details(id):
    webhook = Webhook.query.get_or_404(id)
    return jsonify({
        'id': webhook.id,
        'timestamp': webhook.timestamp,
        'action': webhook.action,
        'symbol': webhook.symbol,
        'volume': webhook.volume,
        'order_type': webhook.order_type,
        'price': webhook.price,
        'stop_loss': webhook.stop_loss,
        'take_profit': webhook.take_profit,
        'expiration': webhook.expiration,
        'status': webhook.status,
        'error_message': webhook.error_message
    })


@app.route('/webhook/<int:id>/details')
def webhook_details(id):
    webhook = Webhook.query.get_or_404(id)
    return jsonify({
        'request': {
            'action': webhook.action,
            'symbol': webhook.symbol,
            'volume': webhook.volume,
            'order_type': webhook.order_type,
            'price': webhook.price,
            'stop_loss': webhook.stop_loss,
            'take_profit': webhook.take_profit
        },
        'mt5_response': webhook.error_message or "Success"
    })


@app.route('/api/position/<int:id>/details')
def position_details(id):
    position = Position.query.get_or_404(id)
    return jsonify({
        'id': position.id,
        'timestamp': position.timestamp,
        'symbol': position.symbol,
        'ticket': position.ticket,
        'type': position.type,
        'volume': position.volume,
        'price_open': position.price_open,
        'sl': position.sl,
        'tp': position.tp,
        'profit': position.profit,
        'status': position.status
    })

@app.route('/api/position/<int:ticket>/close', methods=['POST'])
def close_position(ticket):
    try:
        position = Position.query.filter_by(ticket=ticket).first_or_404()

        if not mt5.initialize():
            return jsonify({"error": "MT5 initialization failed"}), 500

        request = {
            "action": mt5.TRADE_ACTION_DEAL,
            "symbol": position.symbol,
            "volume": position.volume,
            "type": mt5.ORDER_TYPE_SELL if position.type.lower().startswith('buy') else mt5.ORDER_TYPE_BUY,
            "position": position.ticket,
            "price": mt5.symbol_info_tick(position.symbol).bid
        }

        result = mt5.order_send(request)

        if result.retcode == mt5.TRADE_RETCODE_DONE:
            position.status = 'Closed'
            position.price_close = request['price']
            db.session.commit()
            return jsonify({"success": True})

        return jsonify({"error": f"MT5 error: {result.comment}"}), 400

    except Exception as e:
        logger.error(f"Close position error: {str(e)}")
        return jsonify({"error": str(e)}), 500


@app.route('/api/position/<int:ticket>/update', methods=['POST'])
def update_position(ticket):
    try:
        data = request.get_json()
        position = Position.query.filter_by(ticket=ticket).first_or_404()

        if not mt5.initialize():
            return jsonify({"error": "MT5 initialization failed"}), 500

        request = {
            "action": mt5.TRADE_ACTION_MODIFY,
            "symbol": position.symbol,
            "position": position.ticket,
            "price": float(data.get("price", position.price_open)),
            "sl": float(data.get("stop_loss", position.sl or 0)),
            "tp": float(data.get("take_profit", position.tp or 0))
        }

        result = mt5.order_send(request)

        if result.retcode == mt5.TRADE_RETCODE_DONE:
            # Update position in database
            position.sl = request["sl"]
            position.tp = request["tp"]
            if position.status == "Pending":
                position.price_open = request["price"]
            db.session.commit()

            return jsonify({
                "success": True,
                "message": "Position updated successfully"
            })
        else:
            return jsonify({
                "success": False,
                "error": f"MT5 error: {result.comment}"
            }), 400

    except Exception as e:
        logger.error(f"Update position error: {str(e)}")
        return jsonify({"error": str(e)}), 500


@app.route('/api/position/<int:ticket>/cancel', methods=['POST'])
def cancel_position(ticket):
    try:
        position = Position.query.filter_by(ticket=ticket).first_or_404()

        if position.status != 'Pending':
            return jsonify({"error": "Only pending orders can be cancelled"}), 400

        if not mt5.initialize():
            return jsonify({"error": "MT5 initialization failed"}), 500

        cancel_request = {
            "action": mt5.TRADE_ACTION_REMOVE,
            "order": position.ticket
        }

        result = mt5.order_send(cancel_request)
        if result.retcode == mt5.TRADE_RETCODE_DONE:
            position.status = 'Cancelled'
            db.session.commit()
            return jsonify({"success": True})

        return jsonify({"error": f"MT5 error: {result.comment}"}), 400

    except Exception as e:
        logger.error(f"Cancel position error: {str(e)}")
        return jsonify({"error": str(e)}), 500


@app.route('/api/positions')
def get_positions():
    positions = Position.query.order_by(Position.timestamp.desc()).all()
    return jsonify([{
        'timestamp': p.timestamp,
        'symbol': p.symbol,
        'type': p.type,
        'price_open': p.price_open,
        'price_close': p.price_close,
        'sl': p.sl,
        'tp': p.tp,
        'profit': p.profit,
        'status': p.status
    } for p in positions])


@app.route('/positions')
@login_required
def positions():
    positions = Position.query.all()
    return render_template('positions.html', positions=positions)



@app.route('/logs')
@login_required
def logs():
    logs = Log.query.all()
    return render_template('logs.html', logs=logs)


@app.route('/webhooks')
@login_required
def webhooks():
    webhooks = Webhook.query.all()
    return render_template('webhooks.html', webhooks=webhooks)


@app.route('/admin/accounts', methods=['GET'])
@login_required
def accounts():
    accounts = MT5Account.query.all()
    return render_template('accounts.html', accounts=accounts)

@app.route('/admin/accounts/add', methods=['GET', 'POST'])
@login_required
def add_account():
    if request.method == 'POST':
        account = MT5Account(
            name=request.form['name'],
            login=request.form['login'],
            password=request.form['password'],
            server=request.form['server'],
            volume_coefficient=float(request.form['volume_coefficient'])
        )
        db.session.add(account)
        db.session.commit()
        flash('Account added successfully!', 'success')
        return redirect(url_for('accounts'))
    return render_template('add_account.html')

@app.route('/admin/accounts/<int:id>/symbols', methods=['GET', 'POST'])
@login_required
def manage_symbols(id):
    account = MT5Account.query.get_or_404(id)
    if request.method == 'POST':
        # Clear existing restrictions
        RestrictedSymbol.query.filter_by(account_id=id).delete()
        # Add new restrictions
        symbols = request.form.getlist('symbols')
        for symbol in symbols:
            restriction = RestrictedSymbol(account_id=id, symbol=symbol)
            db.session.add(restriction)
        db.session.commit()
        flash('Symbol restrictions updated!', 'success')
        return redirect(url_for('accounts'))
    return render_template('manage_symbols.html', account=account)

@app.route('/admin/logs')
@login_required
def view_logs():
    trade_logs = TradeLog.query.order_by(TradeLog.created_at.desc()).limit(100)
    webhook_logs = WebhookLog.query.order_by(WebhookLog.created_at.desc()).limit(100)
    return render_template('logs.html', trade_logs=trade_logs, webhook_logs=webhook_logs)

def log_trade(account_id, trade_data):
    log = TradeLog(
        account_id=account_id,
        symbol=trade_data['symbol'],
        action=trade_data['action'],
        type=trade_data['type'],
        volume=trade_data['volume'],
        price=trade_data['price'],
        sl=trade_data.get('sl'),
        tp=trade_data.get('tp'),
        profit=trade_data.get('profit', 0)
    )
    db.session.add(log)
    db.session.commit()


def check_mt5_positions():
    if not mt5.initialize():
        logger.error("MT5 initialization failed")
        return None

    positions = mt5.positions_get()
    if positions is None:
        return []

    return [
        {
            'ticket': pos.ticket,
            'symbol': pos.symbol,
            'type': 'buy' if pos.type == mt5.POSITION_TYPE_BUY else 'sell',
            'volume': pos.volume,
            'price_open': pos.price_open,
            'sl': pos.sl,
            'tp': pos.tp,
            'profit': pos.profit,
            'current_price': pos.price_current
        } for pos in positions
    ]


def price_update_thread(app):
    with app.app_context():
        while True:
            try:
                # Get all active positions
                positions = Position.query.filter(Position.status.in_(['Open', 'Pending'])).all()
                
                price_updates = {}
                for pos in positions:
                    symbol_info = mt5.symbol_info(pos.symbol)
                    if symbol_info is None:
                        continue

                    price = symbol_info.bid if pos.type.lower().includes('buy') else symbol_info.ask
                    change = price - pos.price_open
                    price_updates[pos.symbol] = {
                        'bid': symbol_info.bid,
                        'ask': symbol_info.ask,
                        'change': change
                    }

                    # Update position status if needed
                    if pos.status == 'Pending':
                        # Check if pending order should be activated
                        if (pos.type == 'Buy Limit' and price <= pos.price_open) or \
                           (pos.type == 'Sell Limit' and price >= pos.price_open) or \
                           (pos.type == 'Buy Stop' and price >= pos.price_open) or \
                           (pos.type == 'Sell Stop' and price <= pos.price_open):
                            pos.status = 'Open'
                            db.session.commit()
                            # Send telegram notification for status change
                            telegram_service.position_status_changed(pos)
                    elif pos.status == 'Open':
                        # Check for SL/TP
                        if pos.type.startswith('Buy'):
                            if price <= pos.sl:
                                pos.status = 'Closed'
                                pos.price_close = price
                                pos.profit = (price - pos.price_open) * pos.volume * 100000
                                # Send telegram notification for status change
                                telegram_service.position_status_changed(pos)
                            elif price >= pos.tp:
                                pos.status = 'Closed'
                                pos.price_close = price
                                pos.profit = (price - pos.price_open) * pos.volume * 100000
                                # Send telegram notification for status change
                                telegram_service.position_status_changed(pos)
                        else:  # Sell positions
                            if price >= pos.sl:
                                pos.status = 'Closed'
                                pos.price_close = price
                                pos.profit = (pos.price_open - price) * pos.volume * 100000
                                # Send telegram notification for status change
                                telegram_service.position_status_changed(pos)
                            elif price <= pos.tp:
                                pos.status = 'Closed'
                                pos.price_close = price
                                pos.profit = (pos.price_open - price) * pos.volume * 100000
                                # Send telegram notification for status change
                                telegram_service.position_status_changed(pos)

                # Emit price updates via WebSocket
                if price_updates:
                    socketio.emit('price_update', {'prices': price_updates})

                db.session.commit()
                time.sleep(1)

            except Exception as e:
                logger.error(f"Price update error: {str(e)}")
                time.sleep(5)


# Update main
if __name__ == "__main__":
    with app.app_context():
        db.create_all()
        init_admin_user()

    # Start price update thread
    thread = threading.Thread(
        target=price_update_thread,
        args=(app,),
        daemon=True
    )
    thread.start()

    socketio.run(app, host='0.0.0.0', port=5001)

with app.app_context():
    db.create_all()
