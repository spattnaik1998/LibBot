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

### Intelligent Natural Language Processing

The chatbot now uses **GPT-4o powered natural language understanding** - no rigid commands required! Just talk naturally:

#### 🎯 **Smart Intent Detection**
- Understands conversational requests
- Extracts relevant information automatically
- Routes to appropriate specialized agents
- Handles greetings, help requests, and clarifications

#### 📚 **Search Examples**
- *"I want to find books by Stephen King"*
- *"Show me fantasy novels"*  
- *"Do you have Harry Potter?"*
- *"Search for mystery books"*

#### 💰 **Purchase Examples**
- *"I want to buy Harry Potter"*
- *"Can you help me purchase The Great Gatsby, 2 copies?"*
- *"Buy Gatsby 2 and Pride and Prejudice 1"*
- *"I need to buy multiple books: Book A: 3, Book B: 1"*

#### 💳 **Credit Examples** 
- *"I need 50 more credits"*
- *"Add credits to my account"*
- *"Can I buy 100 credits?"*

### Agent Workflows

#### Master Agent (ENHANCED!)
- **Intelligence**: Uses GPT-4o for intent analysis and information extraction
- **Knowledge Base**: Comprehensive understanding of system capabilities
- **Q&A Capabilities**: Answers questions about features directly (no routing needed)
- **Smart Routing**: Automatically directs operational requests to specialized agents
- **Dynamic Responses**: Generates contextual, helpful responses in real-time
- **Examples Handled Directly**:
  - *"How can I buy multiple books?"* → Detailed format explanations
  - *"How much do books cost?"* → Credit system breakdown
  - *"What can you do?"* → Comprehensive capability overview
  - *"Explain how credits work"* → Full credit system explanation

#### Query Agent
- Receives natural search queries from Master Agent
- Supports partial matches, author searches, genre searches  
- Returns matching books with availability information

#### Buy Agent (Enhanced)
- Handles both single and multiple book purchases
- **Single book:** Extracted from natural language requests
- **Multiple books:** Supports various formats automatically parsed
- **Atomic transactions:** All-or-nothing purchase processing

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

- **Single Book Purchase**: Deducts book quantity AND user credits (rollback on failure)
- **Multiple Book Purchase**: Processes all books atomically - either all succeed or all fail with complete rollback
- **Credit Transaction**: Adds credits to user account

### Conversational AI Features

The chatbot provides a **natural, intelligent conversation experience**:

1. **Contextual Understanding**:
   - Remembers conversation context
   - Asks clarifying questions when needed
   - Provides helpful suggestions and examples

2. **Flexible Input Processing**:
   - No rigid command syntax required
   - Understands typos and variations
   - Handles incomplete information gracefully

3. **Smart Information Extraction**:
   - Automatically extracts book titles, quantities, and authors
   - Detects purchase intent vs. search intent vs. help requests
   - Processes multiple requests in single messages

4. **Proactive Assistance**:
   - Offers helpful suggestions
   - Explains available options
   - Guides users through complex transactions

### Enhanced Buy Features

The buy system now supports:

1. **Multiple Book Formats:**
   - **Semicolon separated:** `"Book 1, 2 copies; Book 2, 1 copy"`
   - **Colon format:** `"Harry Potter: 2, Lord of the Rings: 1"`  
   - **Simple format:** `"Book A: 3, Book B: 1, Book C: 2"`
   - **Single book:** `"Harry Potter, 2 copies"` or `"Book Title, quantity 3"`

2. **Atomic Multi-Book Transactions:**
   - Validates ALL books exist and have sufficient quantity before purchase
   - Checks user has enough credits for total cost
   - Either completes entire transaction or rolls back completely

3. **Smart Input Parsing:**
   - Supports various quantity formats (copies, books, numbers)
   - Handles different separators (semicolons, commas, colons)
   - Defaults to quantity 1 if not specified

## Error Handling

The system handles:
- **Unclear requests** (asks clarifying questions naturally)
- **Insufficient credits or inventory** (provides helpful suggestions)
- **Book not found scenarios** (offers alternatives and search tips)
- **Database connection failures** (graceful error recovery)
- **Token authentication errors** (clear re-authentication guidance)
- **LLM parsing errors** (fallback to helpful default responses)

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