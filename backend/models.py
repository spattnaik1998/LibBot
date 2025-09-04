from pydantic import BaseModel, EmailStr, Field
from typing import Optional
from datetime import datetime

class UserRegistration(BaseModel):
    first_name: str = Field(..., min_length=1, max_length=50)
    last_name: str = Field(..., min_length=1, max_length=50)
    email: EmailStr
    gender: str = Field(..., pattern="^(Male|Female|Other)$")
    age: int = Field(..., ge=13, le=120)
    username: str = Field(..., min_length=3, max_length=50)
    password: str = Field(..., min_length=6)

class UserLogin(BaseModel):
    username: str
    password: str

class UserResponse(BaseModel):
    user_id: int
    first_name: str
    last_name: str
    email: str
    gender: str
    age: int
    username: str
    created_at: datetime
    
class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    username: Optional[str] = None