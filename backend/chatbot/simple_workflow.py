"""Simplified chatbot workflow without complex LangGraph dependencies"""
import os
from typing import Dict, Any
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage
from .database_tools import chatbot_db
import re

class SimpleChatbotWorkflow:
    """Simplified chatbot workflow"""
    
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
        """Process a user message through the simplified workflow"""
        
        try:
            user_message = message.lower().strip()
            
            # Route to appropriate handler
            if user_message == "query":
                return self.handle_query_start(user_id, username)
            elif user_message == "buy":
                return self.handle_buy_start(user_id, username)
            elif user_message == "return":
                return self.handle_return_start(user_id, username)
            elif user_message == "buy credits":
                return self.handle_credits_start(user_id, username)
            else:
                # Check if this looks like a search query (for Query agent)
                if len(message.strip()) > 0 and not user_message in ["query", "buy", "return", "buy credits"]:
                    # Could be a book search, buy request, return request, or credits request
                    return self.handle_natural_language_input(user_id, username, message)
                else:
                    return self.handle_invalid_command(user_id, username, message)
        
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
    
    def handle_query_start(self, user_id: int, username: str) -> Dict[str, Any]:
        """Handle query command"""
        return {
            "success": True,
            "response": "Great! I'll help you search for a book. What book are you looking for?",
            "current_agent": "query",
            "conversation_step": "waiting_for_book_search",
            "conversation_history": [
                {"role": "user", "content": "query"},
                {"role": "assistant", "content": "Great! I'll help you search for a book. What book are you looking for?"}
            ],
            "transaction_result": None
        }
    
    def handle_buy_start(self, user_id: int, username: str) -> Dict[str, Any]:
        """Handle buy command"""
        return {
            "success": True,
            "response": "Perfect! I'll help you buy a book. Please tell me the book title and quantity you want to purchase (e.g., 'The Great Gatsby, 2 copies').",
            "current_agent": "buy",
            "conversation_step": "waiting_for_buy_details",
            "conversation_history": [
                {"role": "user", "content": "buy"},
                {"role": "assistant", "content": "Perfect! I'll help you buy a book. Please tell me the book title and quantity you want to purchase (e.g., 'The Great Gatsby, 2 copies')."}
            ],
            "transaction_result": None
        }
    
    def handle_return_start(self, user_id: int, username: str) -> Dict[str, Any]:
        """Handle return command"""
        return {
            "success": True,
            "response": "I'll help you return a book. Please tell me the book title and quantity you want to return (e.g., 'Pride and Prejudice, 1 copy').",
            "current_agent": "return",
            "conversation_step": "waiting_for_return_details",
            "conversation_history": [
                {"role": "user", "content": "return"},
                {"role": "assistant", "content": "I'll help you return a book. Please tell me the book title and quantity you want to return (e.g., 'Pride and Prejudice, 1 copy')."}
            ],
            "transaction_result": None
        }
    
    def handle_credits_start(self, user_id: int, username: str) -> Dict[str, Any]:
        """Handle buy credits command"""
        return {
            "success": True,
            "response": "I'll help you buy more credits. How many credits would you like to add to your account?",
            "current_agent": "credit",
            "conversation_step": "waiting_for_credit_amount",
            "conversation_history": [
                {"role": "user", "content": "buy credits"},
                {"role": "assistant", "content": "I'll help you buy more credits. How many credits would you like to add to your account?"}
            ],
            "transaction_result": None
        }
    
    def handle_natural_language_input(self, user_id: int, username: str, message: str) -> Dict[str, Any]:
        """Handle natural language input - try to understand user intent"""
        
        # Try to detect if this is a book search
        if self.looks_like_book_search(message):
            return self.handle_book_search(user_id, username, message)
        
        # Try to detect if this is a buy request
        elif self.looks_like_buy_request(message):
            return self.handle_buy_request(user_id, username, message)
        
        # Try to detect if this is a return request
        elif self.looks_like_return_request(message):
            return self.handle_return_request(user_id, username, message)
        
        # Try to detect if this is a credits request
        elif self.looks_like_credits_request(message):
            return self.handle_credits_request(user_id, username, message)
        
        else:
            return self.handle_invalid_command(user_id, username, message)
    
    def looks_like_book_search(self, message: str) -> bool:
        """Check if message looks like a book search"""
        # If it's just text without buy/return/credit keywords, assume it's a search
        lower_msg = message.lower()
        if any(keyword in lower_msg for keyword in ["buy", "purchase", "return", "refund", "credit"]):
            return False
        return True
    
    def looks_like_buy_request(self, message: str) -> bool:
        """Check if message looks like a buy request"""
        lower_msg = message.lower()
        return any(keyword in lower_msg for keyword in ["buy", "purchase", "copies", "copy"])
    
    def looks_like_return_request(self, message: str) -> bool:
        """Check if message looks like a return request"""
        lower_msg = message.lower()
        return any(keyword in lower_msg for keyword in ["return", "refund"])
    
    def looks_like_credits_request(self, message: str) -> bool:
        """Check if message looks like a credits request"""
        lower_msg = message.lower()
        return any(keyword in lower_msg for keyword in ["credit", "credits", "add credit"])
    
    def handle_book_search(self, user_id: int, username: str, search_term: str) -> Dict[str, Any]:
        """Handle book search request"""
        try:
            books = chatbot_db.get_books_by_partial_title(search_term)
            
            if not books:
                response = f"I couldn't find any books matching '{search_term}'. Please try a different search term or check the spelling."
            elif len(books) == 1:
                book = books[0]
                response = f"Found: **{book['title']}** by {book['author']}\nQuantity available: {book['Qty']} copies"
            else:
                book_list = "\n".join([f"• **{book['title']}** by {book['author']} ({book['Qty']} available)" 
                                     for book in books[:10]])
                response = f"Found {len(books)} books matching '{search_term}':\n\n{book_list}"
                if len(books) > 10:
                    response += f"\n\n... and {len(books) - 10} more results. Try a more specific search term."
            
            return {
                "success": True,
                "response": response,
                "current_agent": "master",
                "conversation_step": "completed",
                "conversation_history": [
                    {"role": "user", "content": search_term},
                    {"role": "assistant", "content": response}
                ],
                "transaction_result": None
            }
            
        except Exception as e:
            return {
                "success": False,
                "response": f"Sorry, I had trouble searching for books: {str(e)}",
                "current_agent": "master",
                "conversation_step": "error",
                "conversation_history": [],
                "transaction_result": None
            }
    
    def handle_buy_request(self, user_id: int, username: str, message: str) -> Dict[str, Any]:
        """Handle buy request"""
        try:
            book_title, quantity = self.parse_buy_request(message)
            
            if not book_title or quantity <= 0:
                return {
                    "success": True,
                    "response": "I need both the book title and quantity. Please format like: 'Book Title, 3 copies' or 'Book Title, quantity 2'",
                    "current_agent": "master",
                    "conversation_step": "completed",
                    "conversation_history": [],
                    "transaction_result": None
                }
            
            result = chatbot_db.buy_book_transaction(user_id, book_title, quantity)
            
            if result["success"]:
                response = f"""✅ **Purchase Successful!**

Book: **{result['book_title']}**
Quantity purchased: {result['quantity_purchased']} copies
Credits spent: {result['credits_spent']} credits
Remaining credits: {result['remaining_credits']} credits
Books still available: {result['remaining_book_qty']} copies

Thank you for your purchase!"""
            else:
                response = f"❌ **Purchase Failed**: {result['error']}"
            
            return {
                "success": True,
                "response": response,
                "current_agent": "master",
                "conversation_step": "completed",
                "conversation_history": [
                    {"role": "user", "content": message},
                    {"role": "assistant", "content": response}
                ],
                "transaction_result": result
            }
            
        except Exception as e:
            return {
                "success": False,
                "response": f"Sorry, I had trouble processing your purchase: {str(e)}",
                "current_agent": "master",
                "conversation_step": "error",
                "conversation_history": [],
                "transaction_result": None
            }
    
    def handle_credits_request(self, user_id: int, username: str, message: str) -> Dict[str, Any]:
        """Handle credits request"""
        try:
            # Extract number of credits to add
            match = re.search(r'\d+', message)
            if not match:
                return {
                    "success": True,
                    "response": "Please specify how many credits you want to buy (e.g., '50 credits' or just '100').",
                    "current_agent": "master",
                    "conversation_step": "completed",
                    "conversation_history": [],
                    "transaction_result": None
                }
            
            credits_to_add = int(match.group())
            if credits_to_add <= 0:
                raise ValueError("Invalid amount")
            
            result = chatbot_db.add_credits_transaction(user_id, credits_to_add)
            
            if result["success"]:
                response = f"""✅ **Credit Purchase Successful!**

Credits added: {result['credits_added']} credits
New total balance: {result['new_credits_total']} credits

Your account has been updated!"""
            else:
                response = f"❌ **Credit Purchase Failed**: {result['error']}"
            
            return {
                "success": True,
                "response": response,
                "current_agent": "master",
                "conversation_step": "completed",
                "conversation_history": [
                    {"role": "user", "content": message},
                    {"role": "assistant", "content": response}
                ],
                "transaction_result": result
            }
            
        except Exception as e:
            return {
                "success": False,
                "response": f"Sorry, I had trouble processing your credit purchase: {str(e)}",
                "current_agent": "master",
                "conversation_step": "error",
                "conversation_history": [],
                "transaction_result": None
            }
    
    def handle_invalid_command(self, user_id: int, username: str, message: str) -> Dict[str, Any]:
        """Handle invalid commands"""
        system_prompt = f"""You are a master chatbot agent for a book store. You only accept these four commands:
        - "query" - to search for books
        - "buy" - to purchase books
        - "return" - to return books  
        - "buy credits" - to purchase more credits
        
        The user said: "{message}"
        
        Politely explain that you only accept the four specific commands listed above. Ask them to choose one of these options."""
        
        try:
            response = self.call_llm(system_prompt, message)
        except:
            response = """I can only help with these four commands:

🔍 **query** - Search for books in our catalog
💰 **buy** - Purchase books (20 credits per book)  
📚 **return** - Return books for refund
💳 **buy credits** - Add more credits to your account

Please type one of these commands to get started!"""
        
        return {
            "success": True,
            "response": response,
            "current_agent": "master",
            "conversation_step": "waiting_for_command",
            "conversation_history": [
                {"role": "user", "content": message},
                {"role": "assistant", "content": response}
            ],
            "transaction_result": None
        }
    
    def parse_buy_request(self, user_input: str) -> tuple[str, int]:
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
    
    def get_welcome_message(self, username: str) -> str:
        """Get welcome message for new users"""
        return f"""👋 **Welcome to the Book Store, {username}!**

I'm your personal book assistant. I can help you with:

🔍 **query** - Search for books in our catalog
💰 **buy** - Purchase books (20 credits per book)
💳 **buy credits** - Add more credits to your account

Please type one of the three commands above to get started!"""