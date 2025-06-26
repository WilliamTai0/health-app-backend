from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List

app = FastAPI()
# add user array data

class BMIRequest(BaseModel):
    name: str
    height: float
    weight: float

class BMIRecord(BaseModel):
    id: int
    name: str
    height: float
    weight: float
    bmi: float

bmi_records: List[BMIRecord] = []
record_id_counter = 1

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.post("/save_bmi")
def save_bmi(bmi_data: BMIRequest):
    global record_id_counter
    
    if bmi_data.height <= 0 or bmi_data.weight <= 0:
        return {"error": "Height and weight must be positive numbers."}
    
    if not bmi_data.name.strip():
        return {"error": "Name cannot be empty."}
    
    bmi = bmi_data.weight / (bmi_data.height * bmi_data.height)
    new_record = BMIRecord(
        id=record_id_counter,
        name=bmi_data.name.strip(),
        height=bmi_data.height,
        weight=bmi_data.weight,
        bmi=round(bmi, 2)
    )
    
    bmi_records.append(new_record)
    record_id_counter += 1
    
    return {"record": new_record}
