USE [master]
GO

IF NOT EXISTS (SELECT * FROM sys.databases WHERE name = 'tradingdjjm_db')
BEGIN
    CREATE DATABASE [tradingdjjm_db]
END
GO

USE [tradingdjjm_db]
GO

-- User Table
IF NOT EXISTS (SELECT * FROM sys.objects WHERE object_id = OBJECT_ID(N'[dbo].[user]') AND type in (N'U'))
BEGIN
    CREATE TABLE [dbo].[user](
        [id] INT IDENTITY(1,1) PRIMARY KEY,
        [username] VARCHAR(80) NOT NULL UNIQUE,
        [password_hash] VARCHAR(200) NOT NULL
    )
END
GO

-- Insert Admin User
IF NOT EXISTS (SELECT * FROM [dbo].[user] WHERE username = 'adminuser')
BEGIN
    INSERT INTO [dbo].[user] (username, password_hash)
    VALUES ('adminuser', 'hashed_password_here');
END
GO

-- MT5 Accounts Table
IF NOT EXISTS (SELECT * FROM sys.objects WHERE object_id = OBJECT_ID(N'[dbo].[mt5_account]') AND type in (N'U'))
BEGIN
    CREATE TABLE [dbo].[mt5_account](
        [id] INT IDENTITY(1,1) PRIMARY KEY,
        [login] VARCHAR(50) NOT NULL UNIQUE,
        [password] VARCHAR(100) NOT NULL,
        [server] VARCHAR(100) NOT NULL,
        [name] VARCHAR(100) NULL,
        [is_active] BIT DEFAULT 1,
        [created_at] DATETIME DEFAULT GETDATE()
    )
END
GO

-- Restricted Symbols Table
IF NOT EXISTS (SELECT * FROM sys.objects WHERE object_id = OBJECT_ID(N'[dbo].[restricted_symbol]') AND type in (N'U'))
BEGIN
    CREATE TABLE [dbo].[restricted_symbol](
        [id] INT IDENTITY(1,1) PRIMARY KEY,
        [account_id] INT NOT NULL,
        [symbol] VARCHAR(20) NOT NULL,
        [created_at] DATETIME DEFAULT GETDATE(),
        CONSTRAINT [FK_restricted_symbol_mt5_account] FOREIGN KEY ([account_id]) 
        REFERENCES [dbo].[mt5_account] ([id])
    )
END
GO

-- Trade Logs Table
IF NOT EXISTS (SELECT * FROM sys.objects WHERE object_id = OBJECT_ID(N'[dbo].[trade_log]') AND type in (N'U'))
BEGIN
    CREATE TABLE [dbo].[trade_log](
        [id] INT IDENTITY(1,1) PRIMARY KEY,
        [account_id] INT NOT NULL,
        [symbol] VARCHAR(20) NULL,
        [action] VARCHAR(20) NULL,
        [type] VARCHAR(20) NULL,
        [volume] FLOAT NULL,
        [price] FLOAT NULL,
        [sl] FLOAT NULL,
        [tp] FLOAT NULL,
        [profit] FLOAT NULL,
        [created_at] DATETIME DEFAULT GETDATE(),
        CONSTRAINT [FK_trade_log_mt5_account] FOREIGN KEY ([account_id]) 
        REFERENCES [dbo].[mt5_account] ([id])
    )
END
GO

-- Webhook Logs Table
IF NOT EXISTS (SELECT * FROM sys.objects WHERE object_id = OBJECT_ID(N'[dbo].[webhook_log]') AND type in (N'U'))
BEGIN
    CREATE TABLE [dbo].[webhook_log](
        [id] INT IDENTITY(1,1) PRIMARY KEY,
        [payload] NVARCHAR(MAX) NULL,
        [created_at] DATETIME DEFAULT GETDATE()
    )
END
GO
-- Position Table
IF NOT EXISTS (SELECT * FROM sys.objects WHERE object_id = OBJECT_ID(N'[dbo].[position]') AND type in (N'U'))
BEGIN
    CREATE TABLE [dbo].[position](
        [id] INT IDENTITY(1,1) PRIMARY KEY,
        [account_id] INT NOT NULL,
        [ticket] INT UNIQUE,
        [symbol] VARCHAR(20) NOT NULL,
        [type] VARCHAR(20),
        [volume] FLOAT,
        [price_open] FLOAT,
        [price_close] FLOAT,
        [sl] FLOAT,
        [tp] FLOAT,
        [profit] FLOAT,
        [status] VARCHAR(20) DEFAULT 'Pending',
        [created_at] DATETIME DEFAULT GETDATE(),
        [closed_at] DATETIME NULL,
        CONSTRAINT [FK_position_mt5_account] FOREIGN KEY ([account_id]) 
        REFERENCES [dbo].[mt5_account] ([id])
    )
    ALTER TABLE [dbo].[position]
    ALTER COLUMN message TEXT;
END
GO