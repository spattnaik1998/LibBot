"""Individual agent implementations for the chatbot system"""
import re
from typing import Dict, Any
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
    """Master agent that routes user commands to appropriate subordinate agents"""
    
    def __init__(self, openai_api_key: str):
        super().__init__(openai_api_key)
        self.valid_commands = ["query", "buy", "buy credits"]
    
    def process(self, state: ChatbotState) -> ChatbotState:
        """Process user input and route to appropriate agent"""
        user_message = state.user_message.lower().strip()
        
        # Check if user input matches valid commands
        if user_message == "query":
            state.current_agent = AgentState.QUERY
            state.conversation_step = ConversationStep.WAITING_FOR_BOOK_SEARCH
            state.agent_response = "Great! I'll help you search for a book. What book are you looking for?"
            
        elif user_message == "buy":
            state.current_agent = AgentState.BUY
            state.conversation_step = ConversationStep.WAITING_FOR_BUY_DETAILS
            state.agent_response = "Perfect! I'll help you buy a book. Please tell me the book title and quantity you want to purchase (e.g., 'The Great Gatsby, 2 copies')."
            
        elif user_message == "buy credits":
            state.current_agent = AgentState.CREDIT
            state.conversation_step = ConversationStep.WAITING_FOR_CREDIT_AMOUNT
            state.agent_response = "I'll help you buy more credits. How many credits would you like to add to your account?"
            
        else:
            # Invalid command - stay with master agent
            system_prompt = f"""You are a master chatbot agent for a book store. You only accept these three commands:
            - "query" - to search for books
            - "buy" - to purchase books
            - "buy credits" - to purchase more credits
            
            The user said: "{user_message}"
            
            Politely explain that you only accept the three specific commands listed above. Ask them to choose one of these options."""
            
            state.agent_response = self.call_llm(system_prompt, user_message)
        
        state.reset_context()
        return state

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
    """Agent that handles book purchases"""
    
    def process(self, state: ChatbotState) -> ChatbotState:
        """Process book purchase request"""
        user_input = state.user_message.strip()
        
        # Parse book title and quantity from user input
        book_title, quantity = self._parse_buy_request(user_input)
        
        if not book_title or quantity <= 0:
            state.agent_response = "I need both the book title and quantity. Please format like: 'Book Title, 3 copies' or 'Book Title, quantity 2'"
            return state
        
        # Execute purchase transaction
        result = chatbot_db.buy_book_transaction(state.user_id, book_title, quantity)
        state.transaction_result = result
        
        if result["success"]:
            state.agent_response = f"""✅ **Purchase Successful!**

Book: **{result['book_title']}**
Quantity purchased: {result['quantity_purchased']} copies
Credits spent: {result['credits_spent']} credits
Remaining credits: {result['remaining_credits']} credits
Books still available: {result['remaining_book_qty']} copies

Thank you for your purchase!"""
        else:
            state.agent_response = f"❌ **Purchase Failed**: {result['error']}"
        
        state.conversation_step = ConversationStep.COMPLETED
        state.current_agent = AgentState.MASTER
        
        return state
    
    def _parse_buy_request(self, user_input: str) -> tuple[str, int]:
        """Parse book title and quantity from user input"""
        # Try to extract quantity using various patterns
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
                # Remove the quantity part from the input to get book title
                user_input = re.sub(pattern, '', user_input, flags=re.IGNORECASE)
                break
        
        # Clean up the book title
        book_title = user_input.strip(' ,').strip()
        
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