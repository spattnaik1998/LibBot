import os
from dotenv import load_dotenv

load_dotenv()

class Settings:
    # Database settings
    SERVER_NAME = "localhost"
    DATABASE_NAME = "Books"
    
    # JWT settings
    SECRET_KEY = os.getenv("SECRET_KEY", "your-secret-key-change-this-in-production")
    ALGORITHM = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES = 30
    
    # CORS settings
    ALLOWED_ORIGINS = [
        "http://localhost:3000",  # React development server
        "http://127.0.0.1:3000",
    ]

settings = Settings()