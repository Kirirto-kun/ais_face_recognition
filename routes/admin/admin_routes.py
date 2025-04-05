from fastapi import APIRouter, Form, File, UploadFile, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import func
from datetime import date
import shutil
import os
from schema.models import Attendance, AttendanceRecord
from schema.database import get_db
from auth_utils import get_current_user

router = APIRouter()

@router.post('/name')
async def register_face(
    name1: str = Form(...), 
    image: UploadFile = File(...), 
    name2: str = Form(None),
    username: str = Depends(get_current_user)
):
    """
    Endpoint to upload a face image for registration with a name
    """
    try:
        # Save the uploaded image
        img_name = name1 + ".png"
        path = 'Training images'
        
        # Ensure directory exists
        os.makedirs(path, exist_ok=True)
        
        # Save uploaded file to the training images directory
        file_path = os.path.join(path, img_name)
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(image.file, buffer)
        
        return {"status": "success", "message": f"Image {img_name} saved successfully"}
    except Exception as e:
        return {"status": "error", "message": f"Failed to save image: {str(e)}"}

@router.get('/data')
async def get_todays_attendance(
    db: Session = Depends(get_db),
    username: str = Depends(get_current_user)
):
    today = date.today()
    
    # Query attendance records for today
    attendance_records = db.query(Attendance).filter(Attendance.date == today).all()
    
    result = [
        AttendanceRecord(
            name=record.name,
            time=record.time.strftime('%H:%M'),
            date=str(record.date)
        )
        for record in attendance_records
    ]
    
    return {"status": "success", "attendance_data": result}

@router.get('/whole')
async def get_all_attendance(
    db: Session = Depends(get_db),
    username: str = Depends(get_current_user)
):
    # Query all attendance records
    attendance_records = db.query(Attendance).all()
    
    result = [
        AttendanceRecord(
            name=record.name,
            time=record.time.strftime('%H:%M'),
            date=str(record.date)
        )
        for record in attendance_records
    ]
    
    return {"status": "success", "attendance_data": result}

@router.get('/stats')
async def get_attendance_stats(
    db: Session = Depends(get_db),
    username: str = Depends(get_current_user)
):
    # Example of complex query with aggregation
    stats = db.query(
        Attendance.date,
        func.count(Attendance.id).label("total_attendance"),
        func.count(func.distinct(Attendance.name)).label("unique_students")
    ).group_by(Attendance.date).all()
    
    return {
        "status": "success",
        "stats": [
            {
                "date": str(stat.date),
                "total_attendance": stat.total_attendance,
                "unique_students": stat.unique_students
            }
            for stat in stats
        ]
    } 