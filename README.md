# ⚖️ ECB Trading Bot

![ECB Bot](static/favicon/favicon-32x32.png)

---

## 📈 Introducing the ECB Trading Bot
The ECB Trading Bot is a powerful automated trading system that integrates **MetaTrader5 (MT5)** with **TradingView signals**. It allows seamless execution of trading strategies by receiving signals from TradingView and executing them directly in MT5.

---

## 🌐 Features

- ⚔️ **Receive TradingView Signals**: Automatically import signals from your TradingView alerts.
- 💻 **Automated MT5 Trading**: Execute trades with precision directly on your MetaTrader5 account.
- 🌐 **Web-Based Admin Panel**: Manage settings and monitor trades from an intuitive interface.
- 📢 **Telegram Notifications**: Stay informed with real-time alerts.
- ⏳ **Live Monitoring**: Keep track of your trades as they happen.
- 🌍 **Take Profit & Stop Loss Settings**: Adjust risk parameters easily.
- 🔎 **Detailed Reporting**: Access comprehensive trade reports.

---

## ⚡️ Prerequisites

- 🔦 Python 3.9+
- 🏦 MetaTrader 5
- 🔐 Telegram Account
- 📊 TradingView Account

---

## 🚀 Installation and Setup

### 1. ✔️ Install Dependencies
```bash
# Clone the repository
git clone https://github.com/your-username/ecb-bot.git
cd ecb-bot
setup.bat
```

### 2. ⚖️ Configure the Bot
Edit the `.env` file with your credentials:
```
MT5_LOGIN=your_login
MT5_PASSWORD=your_password
MT5_SERVER=your_server
TELEGRAM_BOT_TOKEN=your_token
TELEGRAM_GROUP_ID=your_group_id
```

### 3. ⏳ Start the Bot
```bash
start.bat
```

---

## 🔧 How to Use

### 🔁 Setting Up Webhook in TradingView
1. Go to the **Alerts** section in TradingView.
2. Create a new alert.
3. In the **Webhook URL** field, use the following URL:

```
https://noted-raptor-evident.ngrok-free.app/webhook
```

4. Set the **Message** format as follows:
```json
{
    "action": "OPEN",
    "symbol": "{{ticker}}",
    "type": "{{strategy.order.action}}",
    "price": {{close}},
    "volume": {{strategy.order.contracts}}
}
```

---

### 📝 Admin Panel
- **URL**: [http://localhost:5000](http://localhost:5000)
- **Default Username**: `admin`
- **Default Password**: `admin`

---

## ⚔️ Security Features

- 🔒 Two-Factor Authentication (2FA)
- 🔐 Encryption of Sensitive Data
- 🛡️ IP Whitelisting
- ⚖️ Secure Token for Webhook Authentication

---

## 🌐 Development

### Local Development:
```bash
set FLASK_ENV=development
python app.py
```

### Running Tests:
```bash
pytest tests/
```

---

## 🛠️ Troubleshooting

- **Reset Services**:
  ```bash
  reset.bat
  ```

- **Logs**:
  Check the logs in the `logs/` folder.

- **MT5 Connection Test**:
  ```bash
  python test_mt5_connection.py
  ```

---

## 🌎 Contributions
We welcome pull requests! Before submitting, please:

1. Run all tests.
2. Format your code.
3. Update documentation.

---

## ⚖️ License

This project is licensed under the **MIT License**.

---

## 💬 Contact
- 🔍 Telegram: [@khodaei_mahdi](https://t.me/khodaei_mahdi)
- ✉️ Email: mikhodaee@gmail.com

---

