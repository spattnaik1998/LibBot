"""Session manager for maintaining conversation state"""
from typing import Dict, Any, Optional
from enum import Enum
import time

class ConversationState(str, Enum):
    INITIAL = "initial"
    WAITING_FOR_SEARCH = "waiting_for_search"
    WAITING_FOR_BUY_DETAILS = "waiting_for_buy_details"
    WAITING_FOR_RETURN_DETAILS = "waiting_for_return_details"
    WAITING_FOR_CREDITS = "waiting_for_credits"

class ChatSession:
    def __init__(self, user_id: int, username: str):
        self.user_id = user_id
        self.username = username
        self.state = ConversationState.INITIAL
        self.conversation_history = []
        self.last_activity = time.time()
        
    def update_activity(self):
        self.last_activity = time.time()
        
    def add_message(self, role: str, content: str):
        self.conversation_history.append({
            "role": role,
            "content": content,
            "timestamp": time.time()
        })
        self.update_activity()
        
    def set_state(self, state: ConversationState):
        self.state = state
        self.update_activity()
        
    def is_expired(self, timeout_minutes: int = 30) -> bool:
        return (time.time() - self.last_activity) > (timeout_minutes * 60)

class SessionManager:
    def __init__(self):
        self.sessions: Dict[int, ChatSession] = {}
        
    def get_session(self, user_id: int, username: str) -> ChatSession:
        """Get or create a session for the user"""
        if user_id not in self.sessions:
            self.sessions[user_id] = ChatSession(user_id, username)
        else:
            # Update username in case it changed
            self.sessions[user_id].username = username
            
        session = self.sessions[user_id]
        session.update_activity()
        
        # Clean up expired sessions periodically
        self._cleanup_expired_sessions()
        
        return session
    
    def _cleanup_expired_sessions(self):
        """Remove expired sessions"""
        expired_users = [
            user_id for user_id, session in self.sessions.items() 
            if session.is_expired()
        ]
        for user_id in expired_users:
            del self.sessions[user_id]

# Global session manager instance
session_manager = SessionManager()