from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from pymongo import MongoClient
from typing import List
from datetime import datetime
import os

app = FastAPI()

# MongoDB setup
MONGO_URI = os.getenv("MONGO_URI", "mongodb+srv://bmi_user:<password>@bmi-cluster.mongodb.net/bmi_db?retryWrites=true&w=majority")
client = MongoClient(MONGO_URI)
db = client["bmi_db"]
collection = db["bmi_records"]

# Pydantic model for request body
class BMIRequest(BaseModel):
    name: str
    height: float
    weight: float

# Pydantic model for response
class BMIRecord(BaseModel):
    id: str  # MongoDB uses _id as string (ObjectId)
    name: str
    height: float
    weight: float
    bmi: float
    timestamp: str

# CORS setup
origins = ["http://localhost:19006", "https://your-frontend-url.onrender.com"]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def read_root():
    return {"Hello": "World"}

# POST endpoint to store BMI record
@app.post("/save_bmi")
def save_bmi(bmi_data: BMIRequest):
    if bmi_data.height <= 0 or bmi_data.weight <= 0:
        raise HTTPException(status_code=400, detail="Height and weight must be positive numbers.")
    if not bmi_data.name.strip():
        raise HTTPException(status_code=400, detail="Name cannot be empty.")

    # Calculate BMI
    bmi = bmi_data.weight / (bmi_data.height * bmi_data.height)
    
    # Create record
    new_record = {
        "name": bmi_data.name.strip(),
        "height": bmi_data.height,
        "weight": bmi_data.weight,
        "bmi": round(bmi, 2),
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }
    
    # Store in MongoDB
    result = collection.insert_one(new_record)
    new_record["id"] = str(result.inserted_id)  # Convert ObjectId to string
    
    return {
        "success": True,
        "message": "BMI record saved successfully!",
        "record": new_record
    }

# GET endpoint to retrieve all BMI records
@app.get("/get_all_bmi_records", response_model=dict)
def get_all_bmi_records():
    records = []
    for record in collection.find():
        record_dict = {
            "id": str(record["_id"]),
            "name": record["name"],
            "height": record["height"],
            "weight": record["weight"],
            "bmi": record["bmi"],
            "timestamp": record["timestamp"]
        }
        records.append(record_dict)
    return {"records": records}

# GET endpoint to retrieve records by name
@app.get("/get_bmi_records/{name}", response_model=dict)
def get_bmi_records_by_name(name: str):
    records = []
    for record in collection.find({"name": {"$regex": f"^{name}$", "$options": "i"}}):
        record_dict = {
            "id": str(record["_id"]),
            "name": record["name"],
            "height": record["height"],
            "weight": record["weight"],
            "bmi": record["bmi"],
            "timestamp": record["timestamp"]
        }
        records.append(record_dict)
    return {"records": records}