"""FastAPI endpoints for the chatbot system"""
from fastapi import APIRouter, HTTPException, Depends, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
from typing import Dict, Any
import os
from auth import verify_token
from chatbot.stateful_workflow import StatefulChatbotWorkflow

# Initialize security
security = HTTPBearer()

# Initialize chatbot workflow
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
if not OPENAI_API_KEY:
    raise ValueError("OPENAI_API_KEY environment variable is required")

chatbot_workflow = StatefulChatbotWorkflow(OPENAI_API_KEY)

# Create router
router = APIRouter(prefix="/chatbot", tags=["chatbot"])

class ChatMessage(BaseModel):
    message: str

class ChatResponse(BaseModel):
    response: str
    success: bool
    current_agent: str
    conversation_step: str
    error: str = None

@router.post("/chat", response_model=ChatResponse)
async def chat_with_bot(
    chat_message: ChatMessage,
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    """Send a message to the chatbot and get response"""
    
    try:
        # Verify token and get user info
        token_data = verify_token(credentials.credentials)
        
        # Get user data from token (we'll need to modify auth.py to include user_id)
        # For now, let's extract from the token payload
        import jose.jwt
        from config import settings
        
        payload = jose.jwt.decode(
            credentials.credentials, 
            settings.SECRET_KEY, 
            algorithms=[settings.ALGORITHM]
        )
        user_id = payload.get("user_id")
        username = token_data.username
        
        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token: missing user_id"
            )
        
        # Process message through chatbot workflow
        result = chatbot_workflow.process_message(
            user_id=user_id,
            username=username,
            message=chat_message.message
        )
        
        if result["success"]:
            return ChatResponse(
                response=result["response"],
                success=True,
                current_agent=result["current_agent"],
                conversation_step=result["conversation_step"]
            )
        else:
            return ChatResponse(
                response=result["response"],
                success=False,
                current_agent="master",
                conversation_step="error",
                error=result.get("error", "Unknown error")
            )
            
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Chatbot service error: {str(e)}"
        )

@router.get("/welcome")
async def get_welcome_message(
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    """Get welcome message for the chatbot"""
    
    try:
        # Verify token
        token_data = verify_token(credentials.credentials)
        
        welcome_message = chatbot_workflow.get_welcome_message(token_data.username)
        
        return {
            "message": welcome_message,
            "success": True
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get welcome message: {str(e)}"
        )