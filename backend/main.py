from fastapi import FastAPI, HTTPException, status, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from datetime import timedelta
from typing import Optional

from config import settings
from database import db
from models import UserRegistration, UserLogin, UserResponse, Token
from auth import verify_password, get_password_hash, create_access_token, verify_token

app = FastAPI(
    title="Book Project Authentication API",
    description="User registration and authentication system",
    version="1.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Security scheme
security = HTTPBearer()

@app.get("/")
async def root():
    """Health check endpoint"""
    return {"message": "Book Project Authentication API is running"}

@app.post("/register", response_model=dict)
async def register_user(user: UserRegistration):
    """Register a new user"""
    
    # Check if username already exists
    check_username_query = """
        SELECT username FROM authentication WHERE username = ?
    """
    existing_username = db.execute_query(check_username_query, (user.username,))
    if existing_username:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username already exists"
        )
    
    # Check if email already exists
    check_email_query = """
        SELECT email FROM users WHERE email = ?
    """
    existing_email = db.execute_query(check_email_query, (user.email,))
    if existing_email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )
    
    # Hash password
    hashed_password = get_password_hash(user.password)
    
    # Insert user into users table
    insert_user_query = """
        INSERT INTO users (first_name, last_name, email, gender, age)
        OUTPUT INSERTED.user_id
        VALUES (?, ?, ?, ?, ?)
    """
    user_result = db.execute_query(
        insert_user_query,
        (user.first_name, user.last_name, user.email, user.gender, user.age)
    )
    
    if not user_result:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create user"
        )
    
    user_id = user_result[0]["user_id"]
    
    # Insert authentication record
    insert_auth_query = """
        INSERT INTO authentication (user_id, username, password_hash)
        VALUES (?, ?, ?)
    """
    auth_success = db.execute_non_query(
        insert_auth_query,
        (user_id, user.username, hashed_password)
    )
    
    if not auth_success:
        # If auth insertion fails, we should ideally rollback the user insertion
        # For now, we'll just raise an error
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create authentication record"
        )
    
    return {
        "message": "User registered successfully",
        "user_id": user_id,
        "username": user.username
    }

@app.post("/login", response_model=Token)
async def login_user(user: UserLogin):
    """Authenticate user and return access token"""
    
    # Get user authentication data
    auth_query = """
        SELECT a.user_id, a.username, a.password_hash, a.is_active,
               u.first_name, u.last_name, u.email, u.gender, u.age, u.created_at
        FROM authentication a
        INNER JOIN users u ON a.user_id = u.user_id
        WHERE a.username = ?
    """
    
    auth_result = db.execute_query(auth_query, (user.username,))
    
    if not auth_result:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password"
        )
    
    user_data = auth_result[0]
    
    # Check if account is active
    if not user_data["is_active"]:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Account is deactivated"
        )
    
    # Verify password
    if not verify_password(user.password, user_data["password_hash"]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password"
        )
    
    # Update last login
    update_login_query = """
        UPDATE authentication SET last_login = GETDATE() WHERE username = ?
    """
    db.execute_non_query(update_login_query, (user.username,))
    
    # Create access token
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user_data["username"], "user_id": user_data["user_id"]},
        expires_delta=access_token_expires
    )
    
    return {
        "access_token": access_token,
        "token_type": "bearer"
    }

@app.get("/profile", response_model=UserResponse)
async def get_user_profile(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """Get user profile information"""
    
    # Verify token
    token_data = verify_token(credentials.credentials)
    
    # Get user data
    profile_query = """
        SELECT u.user_id, u.first_name, u.last_name, u.email, u.gender, u.age, u.created_at,
               a.username
        FROM users u
        INNER JOIN authentication a ON u.user_id = a.user_id
        WHERE a.username = ? AND a.is_active = 1
    """
    
    user_result = db.execute_query(profile_query, (token_data.username,))
    
    if not user_result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    user_data = user_result[0]
    return UserResponse(**user_data)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)