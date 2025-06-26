from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List
from datetime import datetime

app = FastAPI()

# Pydantic model for request body
class BMIRequest(BaseModel):
    name: str
    height: float
    weight: float

# Pydantic model for response
class BMIRecord(BaseModel):
    id: int
    name: str
    height: float
    weight: float
    bmi: float
    timestamp: str

# In-memory storage (replace with database in production)
bmi_records: List[BMIRecord] = []
record_id_counter = 1

@app.get("/")
def read_root():
    return {"Hello": "World"}

# CORS setup
origins = ["*"]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# POST endpoint to store BMI record
@app.post("/save_bmi")
def save_bmi(bmi_data: BMIRequest):
    global record_id_counter
    
    # Validation
    if bmi_data.height <= 0 or bmi_data.weight <= 0:
        return {"error": "Height and weight must be positive numbers."}
    
    if not bmi_data.name.strip():
        return {"error": "Name cannot be empty."}
    
    # Calculate BMI
    bmi = bmi_data.weight / (bmi_data.height * bmi_data.height)
        # Create record
    new_record = BMIRecord(
        id=record_id_counter,
        name=bmi_data.name.strip(),
        height=bmi_data.height,
        weight=bmi_data.weight,
        bmi=round(bmi, 2),
        timestamp=datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    )
    
    # Store record
    bmi_records.append(new_record)
    record_id_counter += 1
    
    return {
        "success": True,
        "message": "BMI record saved successfully!",
        "record": new_record
    }

# GET endpoint to retrieve all BMI records
@app.get("/get_all_bmi_records")
def get_all_bmi_records():
    return {"records": bmi_records}

# GET endpoint to retrieve records by name
@app.get("/get_bmi_records/{name}")
def get_bmi_records_by_name(name: str):
    user_records = [record for record in bmi_records if record.name.lower() == name.lower()]
    return {"records": user_records}