from fastapi import APIRouter, HTTPException, Depends, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from App.schema.auth import UserSignup, UserLogin, Token
from App.db import supabase
from passlib.context import CryptContext
from jose import JWTError, jwt
from datetime import datetime, timedelta
from typing import Optional
import os

router = APIRouter()
security = HTTPBearer()

# Password hashing configuration
# Using bcrypt_sha256 to handle passwords longer than 72 bytes
pwd_context = CryptContext(schemes=["bcrypt_sha256"], deprecated="auto")

# JWT configuration
SECRET_KEY = os.getenv("JWT_SECRET_KEY", "your-secret-key-change-this-in-production")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24  # 24 hours

def hash_password(password: str) -> str:
    """Hash a password using bcrypt"""
    return pwd_context.hash(password)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against its hash"""
    return pwd_context.verify(plain_password, hashed_password)

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    """Create a JWT access token"""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """Dependency to get current user from JWT token"""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    try:
        token = credentials.credentials
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email: str = payload.get("sub")
        if email is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception
    
    # Get user from database
    user = supabase.table("signup").select("*").eq("email", email).execute()
    if not user.data:
        raise credentials_exception
    
    return user.data[0]


@router.post("/signup", response_model=Token)
async def signup(user: UserSignup):
    try:
        # Check if user already exists
        existing_user = supabase.table("signup").select("*").eq("email", user.email).execute()
        if existing_user.data:
             raise HTTPException(status_code=400, detail="User with this email already exists")

        # Hash the password
        hashed_password = hash_password(user.password)
        
        # Insert new user with hashed password
        user_data = {
            "username": user.username,
            "email": user.email,
            "password": hashed_password
        }
        response = supabase.table("signup").insert(user_data).execute()
        
        if not response.data:
            raise HTTPException(status_code=500, detail="Failed to create user")
        
        # Create access token
        access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        access_token = create_access_token(
            data={"sub": user.email}, expires_delta=access_token_expires
        )
        
        # Return token and user info (without password)
        user_response = {k: v for k, v in response.data[0].items() if k != "password"}
        
        return {
            "access_token": access_token,
            "token_type": "bearer",
            "user": user_response
        }

    except Exception as e:
        # If it's already an HTTPException, re-raise it
        if isinstance(e, HTTPException):
            raise e
        # Otherwise, wrap it in a 500
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/login", response_model=Token)
async def login(user: UserLogin):
    try:
        # Get user from database
        db_user = supabase.table("signup").select("*").eq("email", user.email).execute()
        
        if not db_user.data:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect email or password"
            )
        
        # Verify password
        if not verify_password(user.password, db_user.data[0]["password"]):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect email or password"
            )
        
        # Create access token
        access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        access_token = create_access_token(
            data={"sub": user.email}, expires_delta=access_token_expires
        )
        
        # Return token and user info (without password)
        user_response = {k: v for k, v in db_user.data[0].items() if k != "password"}
        
        return {
            "access_token": access_token,
            "token_type": "bearer",
            "user": user_response
        }
    
    except Exception as e:
        if isinstance(e, HTTPException):
            raise e
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/me")
async def get_me(current_user: dict = Depends(get_current_user)):
    """Protected route example - get current user info"""
    # Remove password from response
    user_response = {k: v for k, v in current_user.items() if k != "password"}
    return user_response
