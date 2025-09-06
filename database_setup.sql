-- Database setup for User Authentication System
-- Run this script in your SQL Server Management Studio or similar tool

USE Books;
GO

-- Create Users table
IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='users' AND xtype='U')
BEGIN
    CREATE TABLE users (
        user_id INT IDENTITY(1,1) PRIMARY KEY,
        first_name NVARCHAR(50) NOT NULL,
        last_name NVARCHAR(50) NOT NULL,
        email NVARCHAR(100) NOT NULL UNIQUE,
        gender NVARCHAR(10) CHECK (gender IN ('Male', 'Female', 'Other')),
        age INT CHECK (age >= 13 AND age <= 120),
        available_credits INT DEFAULT 100 NOT NULL,
        created_at DATETIME2 DEFAULT GETDATE(),
        updated_at DATETIME2 DEFAULT GETDATE()
    );
    
    PRINT 'Users table created successfully';
END
ELSE
BEGIN
    PRINT 'Users table already exists';
END
GO

-- Create Authentication table
IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='authentication' AND xtype='U')
BEGIN
    CREATE TABLE authentication (
        auth_id INT IDENTITY(1,1) PRIMARY KEY,
        user_id INT NOT NULL,
        username NVARCHAR(50) NOT NULL UNIQUE,
        password_hash NVARCHAR(255) NOT NULL,
        created_at DATETIME2 DEFAULT GETDATE(),
        last_login DATETIME2 NULL,
        is_active BIT DEFAULT 1,
        FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
    );
    
    PRINT 'Authentication table created successfully';
END
ELSE
BEGIN
    PRINT 'Authentication table already exists';
END
GO

-- Create indexes for better performance
IF NOT EXISTS (SELECT * FROM sys.indexes WHERE name = 'IX_users_email')
BEGIN
    CREATE INDEX IX_users_email ON users(email);
    PRINT 'Index on users.email created';
END

IF NOT EXISTS (SELECT * FROM sys.indexes WHERE name = 'IX_authentication_username')
BEGIN
    CREATE INDEX IX_authentication_username ON authentication(username);
    PRINT 'Index on authentication.username created';
END
GO

-- Create book_names table for the book inventory
IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='book_names' AND xtype='U')
BEGIN
    CREATE TABLE book_names (
        book_id INT IDENTITY(1,1) PRIMARY KEY,
        title NVARCHAR(500) NOT NULL,
        author NVARCHAR(200) NOT NULL,
        Qty INT DEFAULT 20 NOT NULL CHECK (Qty >= 0),
        created_at DATETIME2 DEFAULT GETDATE(),
        updated_at DATETIME2 DEFAULT GETDATE()
    );
    
    PRINT 'book_names table created successfully';
END
ELSE
BEGIN
    PRINT 'book_names table already exists';
END
GO

-- Create indexes for better performance on book_names table
IF NOT EXISTS (SELECT * FROM sys.indexes WHERE name = 'IX_book_names_title')
BEGIN
    CREATE INDEX IX_book_names_title ON book_names(title);
    PRINT 'Index on book_names.title created';
END

IF NOT EXISTS (SELECT * FROM sys.indexes WHERE name = 'IX_book_names_author')
BEGIN
    CREATE INDEX IX_book_names_author ON book_names(author);
    PRINT 'Index on book_names.author created';
END
GO

PRINT 'Database setup completed successfully!';