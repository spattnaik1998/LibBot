# Chatbot Setup Guide

This guide explains how to set up and run the multi-agent chatbot system with LangGraph and OpenAI GPT-4o.

## Prerequisites

1. **SQL Server Database** with Books database containing:
   - `users` table with `available_credits` column
   - `book_names` table with `Qty` column
   
2. **OpenAI API Key** for GPT-4o model access

3. **Python 3.8+** and **Node.js 16+**

## Backend Setup

### 1. Install Python Dependencies

```bash
cd backend
pip install -r requirements.txt
```

### 2. Environment Configuration

Create a `.env` file in the backend directory:

```env
# OpenAI API Configuration
OPENAI_API_KEY=your_openai_api_key_here

# JWT Secret (change in production)
SECRET_KEY=your-jwt-secret-key-here

# Database Configuration (optional - defaults are in config.py)
SERVER_NAME=localhost
DATABASE_NAME=Books
```

### 3. Database Schema Update

Make sure your database has the required schema updates:

```sql
-- Add available_credits column to users table if not exists
IF NOT EXISTS (SELECT * FROM INFORMATION_SCHEMA.COLUMNS 
               WHERE TABLE_NAME = 'users' AND COLUMN_NAME = 'available_credits')
BEGIN
    ALTER TABLE users ADD available_credits INT DEFAULT 100 NOT NULL
END

-- Add Qty column to book_names table if not exists  
IF NOT EXISTS (SELECT * FROM INFORMATION_SCHEMA.COLUMNS 
               WHERE TABLE_NAME = 'book_names' AND COLUMN_NAME = 'Qty')
BEGIN
    ALTER TABLE book_names ADD Qty INT DEFAULT 1 NOT NULL
END
```

### 4. Start Backend Server

```bash
cd backend
python main.py
```

The backend will run on `http://localhost:8000`

## Frontend Setup

### 1. Install Dependencies

```bash
cd frontend
npm install
```

### 2. Start Frontend Server

```bash
npm start
```

The frontend will run on `http://localhost:3000`

## Chatbot Features

### Master Agent Commands

The chatbot accepts exactly three commands:

1. **`query`** - Search for books in the catalog
2. **`buy`** - Purchase books (costs 20 credits per book)
3. **`buy credits`** - Add more credits to your account

### Agent Workflows

#### Query Agent
- User types: `query`
- Bot asks: "What book are you looking for?"
- User provides book title (partial matches supported)
- Bot returns matching books with availability

#### Buy Agent
- User types: `buy`
- Bot asks: "Please tell me the book title and quantity"
- User provides: "Book Title, 2 copies"
- Bot processes purchase, deducts credits and inventory

#### Credit Agent
- User types: `buy credits`
- Bot asks: "How many credits would you like to add?"
- User provides: "50" or "50 credits"
- Bot adds credits to user account

## API Endpoints

### Chatbot Endpoints

- `POST /chatbot/chat` - Send message to chatbot
- `GET /chatbot/welcome` - Get welcome message

### Authentication Required
All chatbot endpoints require Bearer token authentication.

## Database Transactions

The chatbot performs atomic transactions:

- **Buy Transaction**: Deducts book quantity AND user credits (rollback on failure)
- **Credit Transaction**: Adds credits to user account

## Error Handling

The system handles:
- Invalid commands (politely redirects to valid options)
- Insufficient credits or inventory
- Book not found scenarios
- Database connection failures
- Token authentication errors

## Architecture

```
User Input → Master Agent → Route to Subordinate Agent → Database Transaction → Response
```

- **LangGraph**: Manages workflow between agents
- **OpenAI GPT-4o**: Provides conversational intelligence
- **SQL Server**: Handles all data persistence
- **FastAPI**: Serves chatbot endpoints
- **React**: Provides chat UI interface

## Troubleshooting

### Common Issues

1. **"OPENAI_API_KEY not found"**
   - Add your OpenAI API key to `.env` file
   
2. **Database connection errors**
   - Verify SQL Server is running
   - Check connection string in config.py
   
3. **Token authentication fails**
   - Ensure user is logged in
   - Check JWT secret key matches

4. **Chatbot gives unexpected responses**
   - Verify exactly one of: query, buy, buy credits
   - Check for typos in commands

### Debug Mode

Set environment variable for detailed logging:
```bash
export LANGCHAIN_VERBOSE=true
```

## Production Considerations

1. **Security**
   - Change JWT secret key
   - Use environment variables for all secrets
   - Add rate limiting to chatbot endpoints

2. **Performance**
   - Consider caching frequently accessed book data
   - Add connection pooling for database
   - Monitor OpenAI API usage and costs

3. **Scaling**
   - Use Redis for conversation state management
   - Consider async processing for database operations
   - Add monitoring and logging

## Testing

Test the complete workflow:
1. Register new user (gets 100 credits)
2. Login and access dashboard
3. Use chatbot with each command type
4. Verify database updates correctly
5. Test error scenarios (insufficient credits, etc.)