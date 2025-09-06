"""Stateful chatbot workflow with proper session management"""
import os
import re
from typing import Dict, Any
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage
from .database_tools import chatbot_db
from .session_manager import session_manager, ConversationState

class StatefulChatbotWorkflow:
    """Stateful chatbot workflow with session management"""
    
    def __init__(self, openai_api_key: str):
        self.openai_api_key = openai_api_key
        self.llm = ChatOpenAI(
            model="gpt-4o",
            api_key=openai_api_key,
            temperature=0.3
        )
    
    def call_llm(self, system_prompt: str, user_message: str) -> str:
        """Call the LLM with system and user messages"""
        try:
            messages = [
                SystemMessage(content=system_prompt),
                HumanMessage(content=user_message)
            ]
            response = self.llm.invoke(messages)
            return response.content
        except Exception as e:
            return f"I encountered an error: {str(e)}. Please try again."
    
    def process_message(self, user_id: int, username: str, message: str) -> Dict[str, Any]:
        """Process a user message with session state management"""
        
        try:
            # Get or create session
            session = session_manager.get_session(user_id, username)
            
            # Add user message to session
            session.add_message("user", message)
            
            # Process based on current state and message
            if session.state == ConversationState.INITIAL:
                response = self._handle_initial_state(session, message)
            elif session.state == ConversationState.WAITING_FOR_SEARCH:
                response = self._handle_search_input(session, message)
            elif session.state == ConversationState.WAITING_FOR_BUY_DETAILS:
                response = self._handle_buy_input(session, message)
            elif session.state == ConversationState.WAITING_FOR_CREDITS:
                response = self._handle_credits_input(session, message)
            else:
                response = self._handle_invalid_state(session, message)
            
            # Add response to session history
            if response["success"] and response["response"]:
                session.add_message("assistant", response["response"])
            
            return response
            
        except Exception as e:
            return {
                "success": False,
                "error": f"Chatbot error: {str(e)}",
                "response": "I'm sorry, I encountered an error. Please try again.",
                "current_agent": "master",
                "conversation_step": "error",
                "conversation_history": [],
                "transaction_result": None
            }
    
    def _handle_initial_state(self, session, message: str) -> Dict[str, Any]:
        """Handle messages when in initial state"""
        user_message = message.lower().strip()
        
        if user_message == "query":
            session.set_state(ConversationState.WAITING_FOR_SEARCH)
            return {
                "success": True,
                "response": "Great! I'll help you search for a book. What book are you looking for?",
                "current_agent": "query",
                "conversation_step": "waiting_for_search",
                "conversation_history": session.conversation_history,
                "transaction_result": None
            }
            
        elif user_message == "buy":
            session.set_state(ConversationState.WAITING_FOR_BUY_DETAILS)
            return {
                "success": True,
                "response": "Perfect! I'll help you buy a book. Please tell me the book title and quantity you want to purchase (e.g., 'The Great Gatsby, 2 copies').",
                "current_agent": "buy",
                "conversation_step": "waiting_for_buy_details",
                "conversation_history": session.conversation_history,
                "transaction_result": None
            }
            
        elif user_message == "buy credits":
            session.set_state(ConversationState.WAITING_FOR_CREDITS)
            return {
                "success": True,
                "response": "I'll help you buy more credits. How many credits would you like to add to your account?",
                "current_agent": "credit",
                "conversation_step": "waiting_for_credits",
                "conversation_history": session.conversation_history,
                "transaction_result": None
            }
            
        else:
            # Try natural language understanding for direct commands
            return self._try_natural_language(session, message)
    
    def _handle_search_input(self, session, search_term: str) -> Dict[str, Any]:
        """Handle book search input from Query Agent"""
        try:
            # Clean the search term
            search_term = search_term.strip()
            
            if not search_term:
                return {
                    "success": True,
                    "response": "Please tell me what book you're looking for.",
                    "current_agent": "query",
                    "conversation_step": "waiting_for_search",
                    "conversation_history": session.conversation_history,
                    "transaction_result": None
                }
            
            # Use AI to intelligently parse the search request
            search_params = self._parse_search_intent(search_term)
            
            # Perform search based on AI-parsed parameters
            if search_params["search_type"] == "author":
                books = chatbot_db.get_books_by_author(search_params["search_value"])
                search_description = f"books by author '{search_params['search_value']}'"
            elif search_params["search_type"] == "title":
                books = chatbot_db.get_books_by_partial_title(search_params["search_value"])
                search_description = f"books with title '{search_params['search_value']}'"
            else:
                # General search - both title and author
                books = chatbot_db.get_books_by_partial_title(search_term)
                search_description = f"books matching '{search_term}'"
            
            if not books:
                response_text = f"I couldn't find any {search_description}. Please try a different search term or check the spelling.\n\nYou can:\n• Try different keywords\n• Check for typos\n• Use author names or book titles\n• Try partial matches\n\nOr type a new command: **query**, **buy**, **return**, or **buy credits**"
            elif len(books) == 1:
                book = books[0]
                response_text = f"📖 **Found Book:**\n\n**{book['title']}** by {book.get('author', 'Unknown Author')}\n• Quantity available: **{book['Qty']} copies**\n• Price: **20 credits per copy**\n\nWould you like to:\n• Search for another book (just type the title)\n• **buy** this book\n• Try another command: **return** or **buy credits**"
            else:
                # Multiple matches - show up to 10
                book_list = []
                for i, book in enumerate(books[:10], 1):
                    author = book.get('author', 'Unknown Author')
                    book_list.append(f"{i}. **{book['title']}** by {author} ({book['Qty']} available)")
                
                book_list_text = "\n".join(book_list)
                response_text = f"📚 **Found {len(books)} books matching '{search_term}':**\n\n{book_list_text}"
                
                if len(books) > 10:
                    response_text += f"\n\n... and {len(books) - 10} more results. Try a more specific search term."
                    
                response_text += "\n\nYou can:\n• Search more specifically (type a more specific title)\n• **buy** a specific book\n• Try another command: **return** or **buy credits**"
            
            # Reset to initial state after providing results
            session.set_state(ConversationState.INITIAL)
            
            return {
                "success": True,
                "response": response_text,
                "current_agent": "master",
                "conversation_step": "completed",
                "conversation_history": session.conversation_history,
                "transaction_result": {"books_found": len(books), "search_term": search_term}
            }
            
        except Exception as e:
            session.set_state(ConversationState.INITIAL)
            return {
                "success": False,
                "response": f"Sorry, I had trouble searching for books: {str(e)}",
                "current_agent": "master",
                "conversation_step": "error",
                "conversation_history": session.conversation_history,
                "transaction_result": None
            }
    
    def _handle_buy_input(self, session, message: str) -> Dict[str, Any]:
        """Handle buy request input from Buy Agent"""
        try:
            book_title, quantity = self._parse_buy_request(message)
            
            if not book_title or quantity <= 0:
                return {
                    "success": True,
                    "response": "I need both the book title and quantity. Please format like:\n• 'The Great Gatsby, 2 copies'\n• 'Pride and Prejudice, 1 copy'\n• 'Book Title, quantity 3'",
                    "current_agent": "buy",
                    "conversation_step": "waiting_for_buy_details",
                    "conversation_history": session.conversation_history,
                    "transaction_result": None
                }
            
            # Execute the purchase transaction
            result = chatbot_db.buy_book_transaction(session.user_id, book_title, quantity)
            
            if result["success"]:
                response_text = f"""✅ **Purchase Successful!**

📖 **Book:** {result['book_title']}
📦 **Quantity purchased:** {result['quantity_purchased']} copies
💰 **Credits spent:** {result['credits_spent']} credits
💳 **Remaining credits:** {result['remaining_credits']} credits
📚 **Books still available:** {result['remaining_book_qty']} copies

Thank you for your purchase! 

What would you like to do next?
• **query** - Search for more books
• **buy** - Purchase another book  
• **buy credits** - Add more credits"""
            else:
                response_text = f"""❌ **Purchase Failed**

{result['error']}

What would you like to do?
• **query** - Search for books
• **buy credits** - Add more credits  
• Try another command"""
            
            # Reset to initial state
            session.set_state(ConversationState.INITIAL)
            
            return {
                "success": True,
                "response": response_text,
                "current_agent": "master",
                "conversation_step": "completed",
                "conversation_history": session.conversation_history,
                "transaction_result": result
            }
            
        except Exception as e:
            session.set_state(ConversationState.INITIAL)
            return {
                "success": False,
                "response": f"Sorry, I had trouble processing your purchase: {str(e)}",
                "current_agent": "master",
                "conversation_step": "error",
                "conversation_history": session.conversation_history,
                "transaction_result": None
            }
    
    def _handle_credits_input(self, session, message: str) -> Dict[str, Any]:
        """Handle credits purchase input from Credit Agent"""
        try:
            # Extract number of credits to add
            match = re.search(r'\d+', message)
            if not match:
                return {
                    "success": True,
                    "response": "Please specify how many credits you want to buy:\n• Type a number like '50' or '100'\n• Or '50 credits'",
                    "current_agent": "credit",
                    "conversation_step": "waiting_for_credits",
                    "conversation_history": session.conversation_history,
                    "transaction_result": None
                }
            
            credits_to_add = int(match.group())
            if credits_to_add <= 0:
                raise ValueError("Invalid amount")
            
            # Execute credit addition
            result = chatbot_db.add_credits_transaction(session.user_id, credits_to_add)
            
            if result["success"]:
                response_text = f"""✅ **Credit Purchase Successful!**

💰 **Credits added:** {result['credits_added']} credits
💳 **New total balance:** {result['new_credits_total']} credits

Your account has been updated!

What would you like to do next?
• **query** - Search for books  
• **buy** - Purchase books (20 credits each)
• **return** - Return books
• **buy credits** - Add more credits"""
            else:
                response_text = f"""❌ **Credit Purchase Failed**

{result['error']}

Please try again or contact support."""
            
            # Reset to initial state
            session.set_state(ConversationState.INITIAL)
            
            return {
                "success": True,
                "response": response_text,
                "current_agent": "master",
                "conversation_step": "completed",
                "conversation_history": session.conversation_history,
                "transaction_result": result
            }
            
        except Exception as e:
            session.set_state(ConversationState.INITIAL)
            return {
                "success": False,
                "response": f"Sorry, I had trouble processing your credit purchase: {str(e)}",
                "current_agent": "master",
                "conversation_step": "error",
                "conversation_history": session.conversation_history,
                "transaction_result": None
            }
    
    
    def _try_natural_language(self, session, message: str) -> Dict[str, Any]:
        """Try to understand natural language input and route appropriately"""
        lower_msg = message.lower()
        
        # Check for direct book search (no buy/credit keywords)
        if not any(keyword in lower_msg for keyword in ["buy", "purchase", "credit"]):
            # Treat as book search
            session.set_state(ConversationState.WAITING_FOR_SEARCH)
            return self._handle_search_input(session, message)
        
        # Check for buy-like requests
        elif any(keyword in lower_msg for keyword in ["buy", "purchase"]) and any(keyword in lower_msg for keyword in ["copy", "copies", "book"]):
            session.set_state(ConversationState.WAITING_FOR_BUY_DETAILS)
            return self._handle_buy_input(session, message)
        
        # Check for credit requests
        elif any(keyword in lower_msg for keyword in ["credit", "credits"]) and re.search(r'\d+', message):
            session.set_state(ConversationState.WAITING_FOR_CREDITS)
            return self._handle_credits_input(session, message)
        
        else:
            return self._handle_invalid_command(session, message)
    
    def _handle_invalid_command(self, session, message: str) -> Dict[str, Any]:
        """Handle invalid commands with helpful guidance"""
        
        response_text = f"""I can help you with these three commands:

🔍 **query** - Search for books in our catalog
💰 **buy** - Purchase books (20 credits per book)  
💳 **buy credits** - Add more credits to your account

You can also:
• Type a book title directly to search
• Say "buy Book Title, 2 copies" to purchase

Please choose one of these options!"""
        
        return {
            "success": True,
            "response": response_text,
            "current_agent": "master",
            "conversation_step": "initial",
            "conversation_history": session.conversation_history,
            "transaction_result": None
        }
    
    def _handle_invalid_state(self, session, message: str) -> Dict[str, Any]:
        """Handle invalid conversation state"""
        session.set_state(ConversationState.INITIAL)
        return self._handle_invalid_command(session, message)
    
    def _parse_buy_request(self, user_input: str) -> tuple[str, int]:
        """Parse book title and quantity from user input"""
        quantity_patterns = [
            r'(\d+)\s*(?:copies|copy|books|book)',
            r'quantity\s*:?\s*(\d+)',
            r',\s*(\d+)(?:\s*(?:copies|copy|books|book))?',
        ]
        
        quantity = 0
        for pattern in quantity_patterns:
            match = re.search(pattern, user_input, re.IGNORECASE)
            if match:
                quantity = int(match.group(1))
                user_input = re.sub(pattern, '', user_input, flags=re.IGNORECASE)
                break
        
        book_title = user_input.strip(' ,').strip()
        return book_title, quantity
    
    def _parse_search_intent(self, search_query: str) -> Dict[str, str]:
        """Use AI to intelligently parse search intent and extract parameters"""
        try:
            system_prompt = """You are a search query parser for a bookstore. Analyze the user's search query and determine:

1. What type of search this is: "author", "title", or "general"
2. Extract the main search value (author name, book title, or search term)

Rules:
- If asking for books BY someone, it's an "author" search
- If asking for a specific book title, it's a "title" search  
- If unclear or general, it's a "general" search

Return ONLY a JSON object with this exact format:
{
    "search_type": "author|title|general",
    "search_value": "extracted name or title"
}

Examples:
- "books by Stephen King" → {"search_type": "author", "search_value": "Stephen King"}
- "Give me Salman Rushdie books" → {"search_type": "author", "search_value": "Salman Rushdie"}
- "I want Harry Potter" → {"search_type": "title", "search_value": "Harry Potter"}
- "Find me some fantasy books" → {"search_type": "general", "search_value": "fantasy"}
- "What Agatha Christie novels do you have?" → {"search_type": "author", "search_value": "Agatha Christie"}"""

            user_message = f"Parse this search query: '{search_query}'"
            
            response = self.call_llm(system_prompt, user_message)
            
            # Try to parse the JSON response
            import json
            try:
                parsed = json.loads(response.strip())
                if "search_type" in parsed and "search_value" in parsed:
                    return parsed
            except json.JSONDecodeError:
                pass
            
            # Fallback if AI response isn't valid JSON
            return {"search_type": "general", "search_value": search_query}
            
        except Exception as e:
            print(f"Error parsing search intent: {e}")
            # Fallback to general search
            return {"search_type": "general", "search_value": search_query}
    
    def get_welcome_message(self, username: str) -> str:
        """Get welcome message for new users"""
        return f"""Welcome to the Book Store, {username}.

I can help you search for books, make purchases, and manage your account. Just tell me what you need in natural language.

What can I help you with today?"""