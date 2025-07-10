from fastapi import FastAPI, HTTPException, Depends, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.middleware.cors import CORSMiddleware
from pymongo import MongoClient
from pydantic import BaseModel, EmailStr, Field, ConfigDict
from passlib.context import CryptContext
from jose import JWTError, jwt
from datetime import datetime, timedelta
from typing import Optional, Any
import os
from dotenv import load_dotenv
from bson import ObjectId

# Load environment variables
load_dotenv()

# FastAPI app
app = FastAPI(title="Health App API", version="1.0.0")

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Specify your app's domain in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Security
SECRET_KEY = os.getenv("SECRET_KEY", "your-secret-key-here-change-in-production")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
security = HTTPBearer()

# MongoDB connection
MONGODB_URL = "mongodb+srv://bmi-user:1234@bmi-cluster.mongodb.net/bmi_db?retryWrites=true&w=majority"
client = MongoClient(MONGODB_URL)
db = client.bmi_db
users_collection = db.users

# Pydantic models
class UserRegister(BaseModel):
    username: str
    email: EmailStr
    password: str

class UserLogin(BaseModel):
    username: str
    password: str

class UserResponse(BaseModel):
    id: str = Field(..., alias="_id")
    username: str
    email: EmailStr
    created_at: datetime

    # Pydantic V2 ConfigDict
    model_config = ConfigDict(
        populate_by_name=True,
        arbitrary_types_allowed=True, # Required for ObjectId
        json_encoders={ObjectId: str}
    )

class Token(BaseModel):
    access_token: str
    token_type: str

class AuthResponse(BaseModel):
    success: bool
    message: str
    user: Optional[UserResponse] = None
    token: Optional[str] = None

# Utility functions
def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password):
    return pwd_context.hash(password)

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta if expires_delta else timedelta(minutes=15))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

def get_user_by_username(username: str):
    return users_collection.find_one({"username": username})

def get_user_by_email(email: str):
    return users_collection.find_one({"email": email})

def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    try:
        payload = jwt.decode(credentials.credentials, SECRET_KEY, algorithms=[ALGORITHM])
        username = payload.get("sub")
        if not username:
            raise HTTPException(status_code=401, detail="Invalid credentials")
        user = get_user_by_username(username)
        if not user:
            raise HTTPException(status_code=401, detail="Invalid credentials")
        return user
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid credentials")

# API Routes
@app.get("/")
async def root():
    return {"message": "Health App API is running", "status": "healthy"}

@app.post("/api/auth/register", response_model=AuthResponse)
async def register(user_data: UserRegister):
    if get_user_by_username(user_data.username):
        return AuthResponse(success=False, message="Username already exists")
    if get_user_by_email(user_data.email):
        return AuthResponse(success=False, message="Email already registered")
    hashed_password = get_password_hash(user_data.password)
    user_doc = {
        "username": user_data.username,
        "email": user_data.email,
        "password": hashed_password,
        "created_at": datetime.utcnow()
    }
    result = users_collection.insert_one(user_doc)
    if result.inserted_id:
        access_token = create_access_token(data={"sub": user_data.username}, expires_delta=timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
        created_user = users_collection.find_one({"_id": result.inserted_id})
        user_response = UserResponse(id=str(created_user["_id"]), username=created_user["username"], email=created_user["email"], created_at=created_user["created_at"])
        return AuthResponse(success=True, message="User created successfully", user=user_response, token=access_token)
    return AuthResponse(success=False, message="Failed to create user")

@app.post("/api/auth/login", response_model=AuthResponse)
async def login(user_data: UserLogin):
    user = get_user_by_username(user_data.username)
    if not user or not verify_password(user_data.password, user["password"]):
        return AuthResponse(success=False, message="Invalid username or password")
    access_token = create_access_token(data={"sub": user["username"]}, expires_delta=timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    user_response = UserResponse(id=str(user["_id"]), username=user["username"], email=user["email"], created_at=user["created_at"])
    return AuthResponse(success=True, message="Login successful", user=user_response, token=access_token)

@app.get("/api/auth/me", response_model=UserResponse)
async def get_current_user_info(current_user: dict = Depends(get_current_user)):
    return UserResponse(id=str(current_user["_id"]), username=current_user["username"], email=current_user["email"], created_at=current_user["created_at"])

@app.get("/api/users")
async def get_all_users(current_user: dict = Depends(get_current_user)):
    users = list(users_collection.find({}, {"password": 0}))
    for user in users:
        user["id"] = str(user["_id"])
        del user["_id"]
    return {"users": users}

@app.get("/api/health")
async def health_check():
    try:
        client.admin.command('ping')
        return {"status": "healthy", "database": "connected", "timestamp": datetime.utcnow()}
    except Exception as e:
        return {"status": "unhealthy", "database": "disconnected", "error": str(e), "timestamp": datetime.utcnow()}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=10000)
