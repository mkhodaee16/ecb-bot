-- Database initialization queries
IF NOT EXISTS (SELECT * FROM sys.databases WHERE name = 'TradingDB')
BEGIN
    CREATE DATABASE TradingDB
END
GO

USE TradingDB
GO

CREATE TABLE mt5_account (
    id INT PRIMARY KEY IDENTITY(1,1),
    login VARCHAR(50) UNIQUE NOT NULL,
    password VARCHAR(100) NOT NULL,
    server VARCHAR(100) NOT NULL,
    name VARCHAR(100),
    is_active BIT DEFAULT 1,
    created_at DATETIME DEFAULT GETDATE()
);

CREATE TABLE restricted_symbol (
    id INT PRIMARY KEY IDENTITY(1,1),
    account_id INT FOREIGN KEY REFERENCES mt5_account(id),
    symbol VARCHAR(20) NOT NULL,
    created_at DATETIME DEFAULT GETDATE()
);

CREATE TABLE trade_log (
    id INT PRIMARY KEY IDENTITY(1,1),
    account_id INT FOREIGN KEY REFERENCES mt5_account(id),
    symbol VARCHAR(20),
    action VARCHAR(20),
    type VARCHAR(20),
    volume FLOAT,
    price FLOAT,
    sl FLOAT,
    tp FLOAT,
    profit FLOAT,
    created_at DATETIME DEFAULT GETDATE()
);

CREATE TABLE webhook_log (
    id INT PRIMARY KEY IDENTITY(1,1),
    payload NVARCHAR(MAX),
    created_at DATETIME DEFAULT GETDATE()
);