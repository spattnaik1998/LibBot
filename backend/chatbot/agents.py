"""Individual agent implementations for the chatbot system"""
import re
from typing import Dict, Any, List
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage
from .state import ChatbotState, AgentState, ConversationStep
from .database_tools import chatbot_db

class BaseChatbotAgent:
    """Base class for all chatbot agents"""
    
    def __init__(self, openai_api_key: str):
        self.llm = ChatOpenAI(
            model="gpt-4o",
            api_key=openai_api_key,
            temperature=0.3
        )
    
    def call_llm(self, system_prompt: str, user_message: str) -> str:
        """Call the LLM with system and user messages"""
        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=user_message)
        ]
        response = self.llm.invoke(messages)
        return response.content

class MasterAgent(BaseChatbotAgent):
    """Intelligent master agent that understands natural language and orchestrates the conversation"""
    
    def __init__(self, openai_api_key: str):
        super().__init__(openai_api_key)
        self.capabilities = {
            "search": "Search for books by title, author, or genre",
            "buy": "Purchase single or multiple books", 
            "credits": "Add more credits to your account"
        }
    
    def process(self, state: ChatbotState) -> ChatbotState:
        """Intelligently process user input and route to appropriate agent"""
        user_message = state.user_message.strip()
        
        # Use LLM to understand user intent and extract information
        intent_analysis = self._analyze_user_intent(user_message)
        
        # Check if this is an informational/help request that master agent should handle
        if intent_analysis.get("action") == "provide_information":
            # Master agent provides the information directly
            state.agent_response = intent_analysis["response"]
            # Stay with master agent for follow-up questions
            
        elif intent_analysis["intent"] == "search":
            # Direct search intent - route to QueryAgent
            state.current_agent = AgentState.QUERY
            state.conversation_step = ConversationStep.WAITING_FOR_BOOK_SEARCH
            
            if intent_analysis.get("search_query"):
                # User already provided search terms, forward to QueryAgent
                state.user_message = intent_analysis["search_query"]
                state.agent_response = f"I'll search for '{intent_analysis['search_query']}' in our catalog..."
            else:
                # Ask for search terms
                state.agent_response = intent_analysis["response"]
                
        elif intent_analysis["intent"] == "buy":
            # Purchase intent - route to BuyAgent
            state.current_agent = AgentState.BUY  
            state.conversation_step = ConversationStep.WAITING_FOR_BUY_DETAILS
            
            if intent_analysis.get("has_book_details"):
                # User provided book details, forward to BuyAgent
                state.user_message = intent_analysis["book_request"]
                state.agent_response = "Let me process your purchase..."
            else:
                # Ask for book details
                state.agent_response = intent_analysis["response"]
                
        elif intent_analysis["intent"] == "credits":
            # Credit purchase intent - route to CreditAgent
            state.current_agent = AgentState.CREDIT
            state.conversation_step = ConversationStep.WAITING_FOR_CREDIT_AMOUNT
            
            if intent_analysis.get("credit_amount"):
                # User provided amount, forward to CreditAgent
                state.user_message = str(intent_analysis["credit_amount"])
                state.agent_response = f"I'll add {intent_analysis['credit_amount']} credits to your account..."
            else:
                # Ask for amount
                state.agent_response = intent_analysis["response"]
                
        elif intent_analysis["intent"] in ["help", "greeting", "informational"]:
            # Master agent handles these directly with intelligent responses
            state.agent_response = intent_analysis["response"]
            # Stay with master agent for conversation continuity
            
        else:
            # Unclear intent - ask for clarification with helpful context
            state.agent_response = intent_analysis.get("response", 
                "I'd be happy to help you! I can search for books, help you make purchases, add credits to your account, or answer questions about how the system works. What would you like to do?")
        
        state.reset_context()
        return state
    
    def _analyze_user_intent(self, user_message: str) -> Dict[str, Any]:
        """Use LLM to intelligently analyze user intent and extract relevant information"""
        
        system_prompt = """You are an intelligent bookstore assistant with comprehensive knowledge of the system. Analyze the user's message and provide helpful responses.

## YOUR CAPABILITIES:
1. **SEARCH** - Find books by title, author, genre, or description (supports partial matches)
2. **PURCHASE** - Buy single or multiple books (20 credits each) with various formats:
   - Single: "Harry Potter, 2 copies" or "Book Title, quantity 3"
   - Multiple: "Book 1, 2 copies; Book 2, 1 copy" (semicolon separated)
   - Colon format: "Harry Potter: 2, Lord of the Rings: 1"
   - Simple format: "Book A: 3, Book B: 1, Book C: 2"
3. **CREDITS** - Add credits to user accounts
4. **HELP & GUIDANCE** - Answer questions about how the system works

## SYSTEM KNOWLEDGE:
- Books cost 20 credits each
- Multiple book purchases are atomic (all succeed or all fail)
- Partial book title matching is supported
- Users start with 100 credits when they register
- System supports natural language - no rigid commands needed

Respond with a JSON object:
{
    "intent": "search|buy|credits|help|greeting|informational|unclear",
    "action": "route_to_agent|provide_information|ask_clarification",
    "confidence": 0.8,
    "response": "Your complete, helpful response to the user",
    "search_query": "extracted search terms (if search intent)",
    "book_request": "extracted book purchase details (if buy intent)", 
    "has_book_details": true/false,
    "credit_amount": number (if credits intent and amount specified)
}

## EXAMPLES:

User: "I want to find books by Stephen King"
{"intent": "search", "action": "route_to_agent", "confidence": 0.9, "search_query": "Stephen King", "response": "I'll search for books by Stephen King in our catalog..."}

User: "Can you help me buy Harry Potter?"
{"intent": "buy", "action": "route_to_agent", "confidence": 0.8, "book_request": "Harry Potter", "has_book_details": true, "response": "I'll help you purchase Harry Potter. How many copies would you like?"}

User: "How can I buy multiple books?"
{"intent": "help", "action": "provide_information", "confidence": 1.0, "response": "You can purchase multiple books using these formats:\n\n• 'Book 1, 2 copies; Book 2, 1 copy'\n• 'Harry Potter: 2, Lord of the Rings: 1'\n• 'Book A: 3, Book B: 1'\n\nAll books are purchased together (20 credits each). What books would you like?"}

User: "What formats do you support for buying books?"
{"intent": "help", "action": "provide_information", "confidence": 1.0, "response": "Supported formats:\n\n**Single:** 'Harry Potter, 2 copies' or 'Book Title, quantity 3'\n**Multiple:** 'Book 1, 2 copies; Book 2, 1 copy' or 'Harry Potter: 2, Gatsby: 1'\n\nWhat would you like to purchase?"}

User: "How much do books cost?"
{"intent": "help", "action": "provide_information", "confidence": 1.0, "response": "Each book costs 20 credits. Examples: 1 book = 20 credits, 3 books = 60 credits.\n\nWould you like to browse books or add credits?"}

User: "I need 50 more credits"
{"intent": "credits", "action": "route_to_agent", "confidence": 0.9, "credit_amount": 50, "response": "I'll add 50 credits to your account..."}

User: "How does the system work?"
{"intent": "help", "action": "provide_information", "confidence": 1.0, "response": "I can help you search for books, make purchases, and manage credits. Just tell me what you need naturally - no special commands required.\n\nWhat would you like to do?"}

User: "What are the different ways I can buy books?"
{"intent": "help", "action": "provide_information", "confidence": 1.0, "response": "You can buy books using:\n\n• Single: 'Harry Potter, 2 copies'\n• Multiple: 'Book 1, 2 copies; Book 2, 1 copy'\n• Natural language: 'I want Harry Potter and two copies of Gatsby'\n\nWhat books would you like?"}

User: "Can you explain how credits work?"
{"intent": "help", "action": "provide_information", "confidence": 1.0, "response": "Credits are simple: each book costs 20 credits. New users get 100 credits (5 books). You can add more credits anytime by asking.\n\nWould you like to browse books or add credits?"}

Always provide complete, helpful information when users ask about system capabilities. Be proactive and educational."""

        try:
            response = self.call_llm(system_prompt, user_message)
            # Parse JSON response
            import json
            # Clean the response to extract JSON
            if "```json" in response:
                response = response.split("```json")[1].split("```")[0].strip()
            elif "```" in response:
                response = response.split("```")[1].strip()
            
            intent_data = json.loads(response)
            return intent_data
            
        except (json.JSONDecodeError, Exception) as e:
            # Fallback if LLM response isn't valid JSON
            return {
                "intent": "unclear",
                "confidence": 0.5,
                "response": f"I'd be happy to help you! I can search for books, help you make purchases, or add credits to your account. Could you tell me more about what you'd like to do?"
            }

class QueryAgent(BaseChatbotAgent):
    """Agent that handles book search queries"""
    
    def process(self, state: ChatbotState) -> ChatbotState:
        """Process book search request"""
        search_term = state.user_message.strip()
        
        # Search for books in database
        books = chatbot_db.get_books_by_partial_title(search_term)
        
        if not books:
            state.agent_response = f"I couldn't find any books matching '{search_term}'. Please try a different search term or check the spelling."
        elif len(books) == 1:
            book = books[0]
            state.agent_response = f"Found: **{book['title']}** by {book['author']}\nQuantity available: {book['Qty']} copies"
            state.selected_book = book
        else:
            # Multiple matches
            book_list = "\n".join([f"• **{book['title']}** by {book['author']} ({book['Qty']} available)" 
                                 for book in books[:10]])  # Limit to 10 results
            state.agent_response = f"Found {len(books)} books matching '{search_term}':\n\n{book_list}"
            if len(books) > 10:
                state.agent_response += f"\n\n... and {len(books) - 10} more results. Try a more specific search term."
        
        state.search_results = books
        state.conversation_step = ConversationStep.COMPLETED
        state.current_agent = AgentState.MASTER
        
        return state

class BuyAgent(BaseChatbotAgent):
    """Agent that handles book purchases - supports single and multiple book purchases"""
    
    def process(self, state: ChatbotState) -> ChatbotState:
        """Process book purchase request"""
        user_input = state.user_message.strip()
        
        # Parse book requests from user input
        book_requests = self._parse_multiple_buy_request(user_input)
        
        if not book_requests:
            state.agent_response = """I need book title(s) and quantities. You can buy:

**Single book:** 
• 'Book Title, 3 copies'
• 'Book Title, quantity 2'

**Multiple books:**
• 'Book 1, 2 copies; Book 2, 1 copy'
• 'Book A: 3, Book B: 1, Book C: 2'
• 'Harry Potter 2, Lord of the Rings 1'

Please try again with the correct format."""
            return state
        
        # Execute purchase transaction(s)
        if len(book_requests) == 1:
            # Single book purchase - use existing method
            book_req = book_requests[0]
            result = chatbot_db.buy_book_transaction(state.user_id, book_req['title'], book_req['quantity'])
            state.transaction_result = result
            
            if result["success"]:
                restock_message = ""
                if result.get("restock_occurred", False):
                    restock_message = f"\n\n📦 **Restocked!** {result['book_title']} was automatically restocked to 20 copies since it went out of stock."
                
                state.agent_response = f"""✅ **Purchase Successful!**

📖 **Book:** {result['book_title']}
📦 **Quantity:** {result['quantity_purchased']} copies
💰 **Credits spent:** {result['credits_spent']} credits
💳 **Remaining credits:** {result['remaining_credits']} credits
📚 **Still available:** {result['remaining_book_qty']} copies{restock_message}

Thank you for your purchase!"""
            else:
                state.agent_response = f"❌ **Purchase Failed**: {result['error']}"
        else:
            # Multiple book purchase - use new method
            result = chatbot_db.buy_multiple_books_transaction(state.user_id, book_requests)
            state.transaction_result = result
            
            if result["success"]:
                books_summary = ""
                for book in result['purchased_books']:
                    restock_note = " (Restocked to 20)" if book.get('restock_occurred', False) else ""
                    books_summary += f"• **{book['title']}** - {book['quantity_purchased']} copies ({book['cost']} credits){restock_note}\n"
                
                restock_message = ""
                if result.get('books_restocked'):
                    restocked_list = ", ".join(result['books_restocked'])
                    restock_message = f"\n\n📦 **Automatic Restocking:** {restocked_list} {'was' if len(result['books_restocked']) == 1 else 'were'} automatically restocked to 20 copies."
                
                state.agent_response = f"""✅ **Multi-Book Purchase Successful!**

📚 **Books purchased:**
{books_summary}
📊 **Transaction summary:**
• Total books: {result['total_books_purchased']} copies
• Total credits spent: {result['total_credits_spent']} credits
• Remaining credits: {result['remaining_credits']} credits{restock_message}

Thank you for your purchase!"""
            else:
                state.agent_response = f"❌ **Purchase Failed**: {result['error']}"
        
        state.conversation_step = ConversationStep.COMPLETED
        state.current_agent = AgentState.MASTER
        
        return state
    
    def _parse_multiple_buy_request(self, user_input: str) -> List[Dict[str, Any]]:
        """Parse multiple book requests from user input
        
        Supports formats like:
        - Single: "Book Title, 3 copies"
        - Multiple: "Book 1, 2 copies; Book 2, 1 copy"  
        - Multiple: "Book A: 3, Book B: 1"
        - Multiple: "Harry Potter 2, Lord of the Rings 1"
        """
        book_requests = []
        
        # First, try to split by semicolon or 'and' for multiple books
        separators = [';', ' and ', ' & ']
        parts = [user_input]
        
        for separator in separators:
            if separator in user_input:
                parts = user_input.split(separator)
                break
        
        # If no separators found, try to detect multiple books by looking for patterns
        if len(parts) == 1:
            # Try to detect "Book: number" patterns
            colon_pattern = r'([^,:]+):\s*(\d+)'
            colon_matches = re.findall(colon_pattern, user_input, re.IGNORECASE)
            
            if len(colon_matches) >= 1:
                # Found colon format books
                for match in colon_matches:
                    title = match[0].strip()
                    try:
                        quantity = int(match[1])
                        if title and quantity > 0:
                            book_requests.append({'title': title, 'quantity': quantity})
                    except ValueError:
                        continue
                
                if book_requests:
                    return book_requests
            
            # Try to detect "Title Number, Title Number" patterns  
            # Look for pattern like "Book1 2, Book2 3" (number patterns)
            # Split by commas first, then parse each part
            comma_parts = user_input.split(',')
            if len(comma_parts) > 1:
                temp_requests = []
                all_parts_have_numbers = True
                
                for part in comma_parts:
                    part = part.strip()
                    # Look for title followed by number at end
                    number_match = re.search(r'^(.+?)\s+(\d+)$', part)
                    if number_match:
                        title = number_match.group(1).strip()
                        quantity = int(number_match.group(2))
                        if title and quantity > 0:
                            temp_requests.append({'title': title, 'quantity': quantity})
                    else:
                        # Check if this part has quantity words like "copies"
                        if re.search(r'\d+\s*(?:copies?|books?)', part, re.IGNORECASE):
                            # This is likely a single book with quantity, not multiple books
                            all_parts_have_numbers = False
                            break
                        # No clear number found, assume quantity 1
                        if part:
                            temp_requests.append({'title': part, 'quantity': 1})
                            all_parts_have_numbers = False
                
                # Only return multiple books if all parts had clear numbers
                if len(temp_requests) > 1 and all_parts_have_numbers:
                    return temp_requests
        
        # Parse each part as a single book request
        for part in parts:
            part = part.strip()
            if not part:
                continue
                
            title, quantity = self._parse_single_buy_request(part)
            if title and quantity > 0:
                book_requests.append({'title': title, 'quantity': quantity})
        
        return book_requests
    
    def _parse_single_buy_request(self, user_input: str) -> tuple[str, int]:
        """Parse single book title and quantity from user input"""
        # Try various patterns to extract quantity
        quantity_patterns = [
            r'(\d+)\s*(?:copies|copy|books|book)',  # "3 copies"
            r'quantity\s*:?\s*(\d+)',              # "quantity: 3"
            r',\s*(\d+)(?:\s*(?:copies|copy|books|book))?',  # ", 3" or ", 3 copies"
            r':\s*(\d+)',                          # ": 3"
            r'\b(\d+)\s*$',                        # ending with number
        ]
        
        quantity = 0
        original_input = user_input
        
        for pattern in quantity_patterns:
            match = re.search(pattern, user_input, re.IGNORECASE)
            if match:
                quantity = int(match.group(1))
                # Remove the quantity part from the input to get book title
                user_input = re.sub(pattern, '', user_input, flags=re.IGNORECASE)
                break
        
        # If no quantity found, default to 1
        if quantity == 0:
            # Check if input ends with a number (like "Harry Potter 2")
            end_number_match = re.search(r'\b(\d+)\s*$', user_input)
            if end_number_match:
                quantity = int(end_number_match.group(1))
                user_input = re.sub(r'\b\d+\s*$', '', user_input)
            else:
                quantity = 1
        
        # Clean up the book title
        book_title = user_input.strip(' ,:').strip()
        
        # If title is empty or too short, return original parsing attempt
        if not book_title or len(book_title) < 2:
            return original_input.strip(), 1
        
        return book_title, quantity


class CreditAgent(BaseChatbotAgent):
    """Agent that handles credit purchases"""
    
    def process(self, state: ChatbotState) -> ChatbotState:
        """Process credit purchase request"""
        user_input = state.user_message.strip()
        
        # Extract number of credits to add
        try:
            credits_to_add = int(re.search(r'\d+', user_input).group())
            if credits_to_add <= 0:
                raise ValueError("Invalid amount")
        except:
            state.agent_response = "Please specify how many credits you want to buy (e.g., '50 credits' or just '100')."
            return state
        
        # Execute credit addition transaction
        result = chatbot_db.add_credits_transaction(state.user_id, credits_to_add)
        state.transaction_result = result
        
        if result["success"]:
            state.agent_response = f"""✅ **Credit Purchase Successful!**

Credits added: {result['credits_added']} credits
New total balance: {result['new_credits_total']} credits

Your account has been updated!"""
        else:
            state.agent_response = f"❌ **Credit Purchase Failed**: {result['error']}"
        
        state.conversation_step = ConversationStep.COMPLETED
        state.current_agent = AgentState.MASTER
        
        return state