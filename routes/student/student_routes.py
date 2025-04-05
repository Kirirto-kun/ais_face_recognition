from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from datetime import datetime, date
import cv2
import numpy as np
import face_recognition
import os
from schema.models import Attendance
from schema.database import get_db
from services.analyze import FaceAnalyzer
from auth_utils import get_current_user

router = APIRouter()
face_analyzer = FaceAnalyzer()

def mark_attendance(name: str, db: Session):
    """Mark attendance in the database"""
    now = datetime.now()
    today = date.today()
    
    # Create new attendance record
    attendance = Attendance(
        name=name,
        time=now.time(),
        date=today
    )
    
    db.add(attendance)
    db.commit()
    
    return {
        "name": name,
        "time": now.strftime('%H:%M'),
        "date": str(today)
    }

@router.post("/")
async def recognize_faces(
    db: Session = Depends(get_db),
    username: str = Depends(get_current_user)
):
    cap = cv2.VideoCapture(0)
    recognized_people = []
    
    while True:
        success, img = cap.read()
        if not success:
            break
            
        # Get face recognition results
        results = face_analyzer.recognize_faces(img)
        
        for name, (x1, y1, x2, y2) in results:
            if name != "Unknown":
                # Mark attendance for recognized person
                attendance_data = mark_attendance(name, db)
                recognized_people.append(attendance_data)
            
            # Draw rectangle and name on the frame
            cv2.rectangle(img, (x1, y1), (x2, y2), (0, 255, 0), 2)
            cv2.rectangle(img, (x1, y2 - 35), (x2, y2), (0, 255, 0), cv2.FILLED)
            cv2.putText(img, name, (x1 + 6, y2 - 6), cv2.FONT_HERSHEY_COMPLEX, 1, (255, 255, 255), 2)
        
        cv2.imshow('Punch your Attendance', img)
        if cv2.waitKey(1) & 0xFF == 27:  # ESC key
            break
    
    cap.release()
    cv2.destroyAllWindows()
    
    return {"status": "success", "recognized_people": recognized_people} 