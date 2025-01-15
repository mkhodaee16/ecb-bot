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
from services.tunnel_service import TunnelService
from functools import wraps

# Load environment variables
load_dotenv()

# Flask app setup (MUST BE AT TOP)
app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'default_secret_key')
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///trading_bot.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Initialize extensions
db = SQLAlchemy(app)
socketio = SocketIO(app)
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
    admin_user = User.query.filter_by(username=os.getenv('ADMIN_USER')).first()
    if not admin_user:
        admin_user = User(username=os.getenv('ADMIN_USER'))
        admin_user.set_password(os.getenv('ADMIN_PASS'))
        db.session.add(admin_user)
        db.session.commit()
        app.logger.info("Admin user created")
    try:
        # Check if admin exists
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


# Database Models


class Log(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    level = db.Column(db.String(20))
    message = db.Column(db.String(500))


class Webhook(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    action = db.Column(db.String(50))
    symbol = db.Column(db.String(20))
    volume = db.Column(db.Float)
    order_type = db.Column(db.String(20))  # Modified to handle pending orders
    price = db.Column(db.Float)  # Added for pending orders
    stop_loss = db.Column(db.Float)
    take_profit = db.Column(db.Float)
    expiration = db.Column(db.DateTime)  # Added for pending orders
    status = db.Column(db.String(20))
    error_message = db.Column(db.String(200))


class Position(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    symbol = db.Column(db.String(20))  # Fixed typo from 'symbo'
    ticket = db.Column(db.Integer)
    type = db.Column(db.String(20))
    volume = db.Column(db.Float)
    price_open = db.Column(db.Float)
    price_close = db.Column(db.Float, nullable=True)
    sl = db.Column(db.Float, nullable=True)
    tp = db.Column(db.Float, nullable=True)
    profit = db.Column(db.Float, nullable=True)
    status = db.Column(db.String(20), default='Pending')


class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(120), nullable=False)

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

        # Initialize MT5
        if not mt5.initialize():
            return jsonify({"error": "MT5 initialization failed"}), 500

        # Check symbol exists
        symbol_info = mt5.symbol_info(formatted_data["symbol"])
        if symbol_info is None:
            return jsonify({"error": f"Symbol {formatted_data['symbol']} not found"}), 400

        # Cancel existing pending positions with the same symbol
        pending_positions = Position.query.filter_by(symbol=formatted_data["symbol"], status="Pending").all()
        for pos in pending_positions:
            cancel_request = {
                "action": mt5.TRADE_ACTION_REMOVE,
                "order": pos.ticket
            }
            result = mt5.order_send(cancel_request)
            if result.retcode == mt5.TRADE_RETCODE_DONE:
                pos.status = 'Cancelled'
                db.session.commit()

        # Create MT5 request
        mt5_request = {
            "action": mt5.TRADE_ACTION_PENDING,
            "symbol": formatted_data["symbol"],
            "volume": formatted_data["volume"],
            "type": get_order_type(formatted_data["order_type"]),
            "price": formatted_data["price"],
            "sl": formatted_data["stop_loss"],
            "tp": formatted_data["take_profit"]
        }

        # Log request details
        logger.info(f"MT5 request: {mt5_request}")

        result = mt5.order_send(mt5_request)
        logger.info(f"MT5 response: {result}")

        if result.retcode == mt5.TRADE_RETCODE_DONE:
            position = Position(
                symbol=formatted_data["symbol"],
                ticket=result.order,
                type=formatted_data["order_type"],
                volume=formatted_data["volume"],
                price_open=formatted_data["price"],
                sl=formatted_data["stop_loss"],
                tp=formatted_data["take_profit"],
                status="Pending"
            )
            db.session.add(position)
            db.session.commit()

            # Save webhook data
            webhook = Webhook(
                action=formatted_data["action"],
                symbol=formatted_data["symbol"],
                volume=formatted_data["volume"],
                order_type=formatted_data["order_type"],
                price=formatted_data["price"],
                stop_loss=formatted_data["stop_loss"],
                take_profit=formatted_data["take_profit"],
                status="Pending",
                error_message=result.comment
            )
            db.session.add(webhook)
            db.session.commit()

            # Send telegram notification
            telegram_service.position_opened(position)

            # Emit WebSocket update
            socketio.emit('webhook_received', {'webhook_id': result.order})

            return jsonify({
                "success": True,
                "order": result.order,
                "message": "Order placed successfully"
            })
        else:
            return jsonify({
                "error": f"MT5 error: {result.comment}",
                "retcode": result.retcode
            }), 400

    except ValueError as e:
        return jsonify({"error": f"Invalid number format: {str(e)}"}), 400
    except Exception as e:
        logger.error(f"Webhook error: {str(e)}")
        return jsonify({"error": str(e)}), 500


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

    # Start tunnel service
    tunnel_service = TunnelService(port=5000)
    tunnel_url = tunnel_service.start_ngrok()  # or tunnel_service.start_localtunnel()
    if tunnel_url:
        logger.info(f"Webhook URL: {tunnel_url}/webhook")
    
    # Start price update thread
    thread = threading.Thread(
        target=price_update_thread,
        args=(app,),
        daemon=True
    )
    thread.start()

    socketio.run(app, host='0.0.0.0', port=5000)
