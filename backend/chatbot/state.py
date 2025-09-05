"""State management for the chatbot workflow"""
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, ConfigDict
from enum import Enum

class AgentState(str, Enum):
    MASTER = "master"
    QUERY = "query"
    BUY = "buy"
    RETURN = "return"
    CREDIT = "credit"
    END = "end"

class ConversationStep(str, Enum):
    INITIAL = "initial"
    WAITING_FOR_COMMAND = "waiting_for_command"
    PROCESSING_QUERY = "processing_query"
    WAITING_FOR_BOOK_SEARCH = "waiting_for_book_search"
    WAITING_FOR_BUY_DETAILS = "waiting_for_buy_details"
    WAITING_FOR_RETURN_DETAILS = "waiting_for_return_details"
    WAITING_FOR_CREDIT_AMOUNT = "waiting_for_credit_amount"
    COMPLETED = "completed"

class ChatbotState(BaseModel):
    """State object that gets passed between agents in the workflow"""
    user_id: int
    username: str
    current_agent: AgentState = AgentState.MASTER
    conversation_step: ConversationStep = ConversationStep.INITIAL
    user_message: str = ""
    agent_response: str = ""
    conversation_history: List[Dict[str, str]] = []
    
    # Context data for agents
    selected_book: Optional[Dict[str, Any]] = None
    requested_quantity: Optional[int] = None
    search_results: List[Dict[str, Any]] = []
    
    # Transaction results
    transaction_result: Optional[Dict[str, Any]] = None
    
    # Error handling
    error_message: Optional[str] = None
    
    model_config = ConfigDict(use_enum_values=True)
    
    def add_message(self, role: str, content: str):
        """Add a message to conversation history"""
        self.conversation_history.append({
            "role": role,
            "content": content
        })
    
    def get_last_user_message(self) -> str:
        """Get the last user message from history"""
        for msg in reversed(self.conversation_history):
            if msg["role"] == "user":
                return msg["content"]
        return ""
    
    def reset_context(self):
        """Reset context data for new command"""
        self.selected_book = None
        self.requested_quantity = None
        self.search_results = []
        self.transaction_result = None
        self.error_message = None