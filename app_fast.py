from fastapi import FastAPI, Form, File, UploadFile, Depends, HTTPException, BackgroundTasks
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from pydantic import BaseModel
# Changed EmailStr to regular string validation
from typing import Optional, List, Dict
import cv2
import numpy as np
import face_recognition
import os
from datetime import datetime, timedelta
from datetime import date
import sqlite3
import json
import pandas as pd
import uvicorn
import shutil
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import asyncio
from concurrent.futures import ThreadPoolExecutor
import threading

# Import database, models, and auth utils
from sqlalchemy.orm import Session
from config import get_db, init_db
from model import User, Student, Teacher, FaceEncoding, Attendance
from auth_utils import hash_password, verify_password, create_access_token, ACCESS_TOKEN_EXPIRE_MINUTES

# Create FastAPI app
app = FastAPI()

# OAuth2 scheme for token authentication
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="login")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Simple session storage (in production, use proper authentication system)
sessions = {}

# Request models
class LoginRequest(BaseModel):
    username: str
    password: str

class NameRequest(BaseModel):
    name1: str
    name2: str

# New request models for registration and authentication
class UserCreate(BaseModel):
    username: str
    email: str  # Changed from EmailStr to str to avoid the dependency
    password: str
    role: str = "student"  # Default role is student

class StudentCreate(BaseModel):
    user: UserCreate
    student_id: str
    first_name: str
    last_name: str
    group_id: Optional[int] = None

class TeacherCreate(BaseModel):
    user: UserCreate
    first_name: str
    last_name: str

class Token(BaseModel):
    access_token: str
    token_type: str

# Initialize database on startup
@app.on_event("startup")
async def startup_db_client():
    try:
        init_db()
    except Exception as e:
        print(f"Error initializing database: {e}")

@app.get('/new')
def new_get():
    return {"message": "Everything is okay!"}

@app.post('/new')
def new_post():
    return {"status": "success", "message": "Request received"}

@app.post('/name')
async def name(name1: str = Form(...), image: UploadFile = File(...), name2: Optional[str] = Form(None)):
    """
    Endpoint to upload a face image for registration with a name
    """
    try:
        # Save the uploaded image
        img_name = name1 + ".png"
        path = 'C:/Users/User/Documents/GitHub/ais_face_recognition/Training images'
        
        # Ensure directory exists
        os.makedirs(path, exist_ok=True)
        
        # Save uploaded file to the training images directory
        file_path = os.path.join(path, img_name)
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(image.file, buffer)
        
        return {"status": "success", "message": f"Image {img_name} saved successfully"}
    except Exception as e:
        return {"status": "error", "message": f"Failed to save image: {str(e)}"}

@app.get('/name')
def name_get():
    return {"status": "error", "message": "All is not well"}

def send_email_threaded(student_name, arrival_time, date_str):
    """Send email in a separate thread so it doesn't block the main application"""
    sender_email = "jafarman2007@gmail.com"
    receiver_email = "mazitovdzafar32@gmail.com"
    password = "rkjt yvtp gbpu qbaz"  # App password
    
    # Create message
    message = MIMEMultipart()
    message["From"] = sender_email
    message["To"] = receiver_email
    message["Subject"] = f"Late Arrival Notification: {student_name}"
    
    # Email content
    body = f"""
    Late Arrival Notification
    
    Student: {student_name}
    Date: {date_str}
    Arrival Time: {arrival_time}
    
    This student has arrived after the 8:20 AM cutoff time.
    """
    message.attach(MIMEText(body, "plain"))
    
    def send_email_task():
        try:
            print(f"Starting to send email for {student_name}...")
            server = smtplib.SMTP("smtp.gmail.com", 587)
            server.starttls()
            server.login(sender_email, password)
            server.sendmail(sender_email, receiver_email, message.as_string())
            server.quit()
            print(f"Email sent successfully for {student_name}")
        except Exception as e:
            print(f"Failed to send email: {str(e)}")
    
    # Start a new thread to send the email immediately
    email_thread = threading.Thread(target=send_email_task)
    email_thread.daemon = True  # Thread will exit when main program exits
    email_thread.start()
    print(f"Email thread started for {student_name}")

@app.post("/")
def recognize_post(db: Session = Depends(get_db)):
    path = 'Training images'
    images = []
    classNames = []
    myList = os.listdir(path)
    
    for cl in myList:
        curImg = cv2.imread(f'{path}/{cl}')
        images.append(curImg)
        classNames.append(os.path.splitext(cl)[0])
    def update_images():
        images = []
        classNames = []
        myList = os.listdir(path)
        for cl in myList:
            curImg = cv2.imread(f'{path}/{cl}')
            images.append(curImg)
            classNames.append(os.path.splitext(cl)[0])
        return images, classNames
    
    def findEncodings(images):
        encodeList = []
        for img in images:
            img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
            encode = face_recognition.face_encodings(img)[0]
            if not len(encode):
                continue
            encodeList.append(encode)
        return encodeList

    def markData(name, db_session):
        now = datetime.now()
        dtString = now.strftime('%H:%M')
        today_date = str(date.today())
        
        # Create new attendance record directly using SQLite
        # instead of using potentially mismatched SQLAlchemy model
        conn = sqlite3.connect('information.db')
        cur = conn.cursor()
        
        # Check if the record already exists
        cur.execute("SELECT * FROM Attendance WHERE NAME=? AND Date=?", (name, today_date))
        existing_record = cur.fetchone()
        
        # Insert only if record doesn't exist
        if not existing_record:
            cur.execute("INSERT INTO Attendance (NAME, Time, Date) VALUES (?, ?, ?)", 
                      (name, dtString, today_date))
            conn.commit()
            
        # Get the data for return
        cur.execute("SELECT NAME, Time, Date FROM Attendance WHERE NAME=? AND Date=?", 
                   (name, today_date))
        record = cur.fetchone()
        conn.close()
        
        return {"name": record[0], "time": record[1], "date": record[2]}

    def send_late_email(student_name, arrival_time, date_str):
        """Send email notification for late arrival in a non-blocking way"""
        sender_email = "jafarman2007@gmail.com"
        receiver_email = "mazitovdzafar32@gmail.com"
        password = "rkjt yvtp gbpu qbaz"  # App password
        
        # Create message
        message = MIMEMultipart()
        message["From"] = sender_email
        message["To"] = receiver_email
        message["Subject"] = f"Late Arrival Notification: {student_name}"
        
        # Email content
        body = f"""
        Late Arrival Notification
        
        Student: {student_name}
        Date: {date_str}
        Arrival Time: {arrival_time}
        
        This student has arrived after the 8:20 AM cutoff time.
        """
        message.attach(MIMEText(body, "plain"))
        
        # Using a separate function to send email
        try:
            # This function runs in a separate thread/process, so it won't block the camera
            server = smtplib.SMTP("smtp.gmail.com", 587)
            server.starttls()
            server.login(sender_email, password)
            server.sendmail(sender_email, receiver_email, message.as_string())
            server.quit()
            print(f"Late notification email sent for {student_name}")
        except Exception as e:
            print(f"Failed to send email: {str(e)}")

    def markAttendance(name):
        # Use SQLite database instead of CSV file
        now = datetime.now()
        dtString = now.strftime('%H:%M')
        today_date = str(date.today())
        
        # Connect to the database
        conn = sqlite3.connect('information.db')
        cur = conn.cursor()
        
        # Check if any record exists for this person today
        cur.execute("SELECT Time FROM Attendance WHERE NAME=? AND Date=? ORDER BY Time DESC", (name, today_date))
        existing_record = cur.fetchone()
        
        should_insert = True
        
        # If a record exists, check the time difference
        if existing_record:
            last_time = existing_record[0]
            
            # Parse the time from the last record (format: HH:MM)
            last_time_parts = last_time.split(':')
            last_datetime = datetime(
                now.year, now.month, now.day, 
                int(last_time_parts[0]), int(last_time_parts[1])
            )
            
            # Calculate time difference in minutes
            time_diff = (now - last_datetime).total_seconds() / 60
            
            # Only insert if more than 1 minute has passed
            should_insert = time_diff > 1
        
        # Insert only if no record exists or if time difference > 1 minute
        if should_insert:
            cur.execute("INSERT INTO Attendance (NAME, Time, Date) VALUES (?, ?, ?)", 
                      (name, dtString, today_date))
            conn.commit()
            
            # Check if it's this person's first entry today and if they're late
            if not existing_record:
                # Create a cutoff time for 8:20 AM
                cutoff_hour, cutoff_minute = 8, 20
                
                # Check if current time is after 8:20 AM
                if (now.hour > cutoff_hour or 
                    (now.hour == cutoff_hour and now.minute > cutoff_minute)):
                    # Send email in a separate thread that starts immediately
                    send_email_threaded(name, dtString, today_date)
        
        conn.close()

    encodeListKnown = findEncodings(images)
    
    # In a real API, implement this as a background task or separate service
    cap = cv2.VideoCapture(0)
    recognized_people = []
    while True:
        
        success, img = cap.read()
        imgS = cv2.resize(img, (0, 0), None, 0.25, 0.25)
        imgS = cv2.cvtColor(imgS, cv2.COLOR_BGR2RGB)

        facesCurFrame = face_recognition.face_locations(imgS)
        encodesCurFrame = face_recognition.face_encodings(imgS, facesCurFrame)

        for encodeFace, faceLoc in zip(encodesCurFrame, facesCurFrame):
            matches = face_recognition.compare_faces(encodeListKnown, encodeFace)
            faceDis = face_recognition.face_distance(encodeListKnown, encodeFace)
            matchIndex = np.argmin(faceDis)

            if faceDis[matchIndex] < 0.50:
                name = classNames[matchIndex].upper()
                markAttendance(name)
                attendance_data = markData(name, db)
                recognized_people.append(attendance_data)
            else:
                name = 'Unknown'

            y1, x2, y2, x1 = faceLoc
            y1, x2, y2, x1 = y1 * 4, x2 * 4, y2 * 4, x1 * 4
            cv2.rectangle(img, (x1, y1), (x2, y2), (0, 255, 0), 2)
            cv2.rectangle(img, (x1, y2 - 35), (x2, y2), (0, 255, 0), cv2.FILLED)
            cv2.putText(img, name, (x1 + 6, y2 - 6), cv2.FONT_HERSHEY_COMPLEX, 1, (255, 255, 255), 2)
            
        cv2.imshow('Punch your Attendance', img)
        c = cv2.waitKey(1)
        if c == 27:
            break
            
    cap.release()
    cv2.destroyAllWindows()

    return {"status": "success", "recognized_people": recognized_people}

@app.get("/")
def recognize_get():
    return {"message": "Use POST request to start face recognition"}

# Registration routes
@app.post("/register/student", response_model=dict)
async def register_student(student: StudentCreate, db: Session = Depends(get_db)):
    """
    Register a new student user
    """
    # Check if user with the same username or email exists
    db_user = db.query(User).filter(
        (User.username == student.user.username) | (User.email == student.user.email)
    ).first()
    
    if db_user:
        raise HTTPException(status_code=400, detail="Username or email already registered")
    
    # Create new user
    new_user = User(
        username=student.user.username,
        email=student.user.email,
        hashed_password=hash_password(student.user.password),
        role="student"
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    
    # Create student profile
    new_student = Student(
        user_id=new_user.id,
        student_id=student.student_id,
        first_name=student.first_name,
        last_name=student.last_name,
        group_id=student.group_id
    )
    db.add(new_student)
    db.commit()
    
    return {
        "status": "success", 
        "message": "Student registered successfully", 
        "user_id": new_user.id
    }

@app.post("/register/teacher", response_model=dict)
async def register_teacher(teacher: TeacherCreate, db: Session = Depends(get_db)):
    """
    Register a new teacher user
    """
    # Check if user with the same username or email exists
    db_user = db.query(User).filter(
        (User.username == teacher.user.username) | (User.email == teacher.user.email)
    ).first()
    
    if db_user:
        raise HTTPException(status_code=400, detail="Username or email already registered")
    
    # Create new user
    new_user = User(
        username=teacher.user.username,
        email=teacher.user.email,
        hashed_password=hash_password(teacher.user.password),
        role="teacher"
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    
    # Create teacher profile
    new_teacher = Teacher(
        user_id=new_user.id,
        first_name=teacher.first_name,
        last_name=teacher.last_name
    )
    db.add(new_teacher)
    db.commit()
    
    return {
        "status": "success", 
        "message": "Teacher registered successfully", 
        "user_id": new_user.id
    }

# Login routes
@app.post("/token", response_model=Token)
async def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    """
    OAuth2 compatible token login, returns JWT token
    """
    # Find user by username
    user = db.query(User).filter(User.username == form_data.username).first()
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=401,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Generate access token
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.username, "role": user.role, "user_id": user.id},
        expires_delta=access_token_expires
    )
    
    return {"access_token": access_token, "token_type": "bearer"}

# Update existing login route to use database
@app.post('/login')
def login(request: LoginRequest, db: Session = Depends(get_db)):
    username = request.username
    password = request.password
    
    # Check credentials against database
    user = db.query(User).filter(User.username == username).first()
    if user and verify_password(password, user.hashed_password):
        # Generate JWT token
        access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        access_token = create_access_token(
            data={"sub": user.username, "role": user.role, "user_id": user.id},
            expires_delta=access_token_expires
        )
        
        # Store in sessions for backward compatibility
        sessions[username] = True
        
        return {
            "status": "success", 
            "username": username,
            "access_token": access_token,
            "token_type": "bearer",
            "role": user.role
        }
    else:
        return {"status": "failed", "message": "Invalid username or password"}

# User profile endpoint
@app.get("/users/me", response_model=dict)
async def get_user_profile(db: Session = Depends(get_db), token: str = Depends(oauth2_scheme)):
    """
    Get current user profile information
    """
    from auth_utils import verify_access_token
    
    # Verify token and get user information
    payload = verify_access_token(token)
    if not payload:
        raise HTTPException(
            status_code=401,
            detail="Invalid token or token expired",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    username = payload.get("sub")
    user = db.query(User).filter(User.username == username).first()
    
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Get additional profile information based on role
    profile_data = {
        "id": user.id,
        "username": user.username,
        "email": user.email,
        "role": user.role,
    }
    
    if user.role == "student" and user.student:
        profile_data.update({
            "student_id": user.student.student_id,
            "first_name": user.student.first_name,
            "last_name": user.student.last_name,
        })
    elif user.role == "teacher" and user.teacher:
        profile_data.update({
            "first_name": user.teacher.first_name,
            "last_name": user.teacher.last_name,
        })
    
    return profile_data

@app.get('/checklogin')
def checklogin(username: Optional[str] = None):
    if username in sessions:
        return {"logged_in": True, "username": username}
    return {"logged_in": False}

@app.get('/how')
def how():
    return {"message": "API documentation"}

@app.post('/data')
def data():
    today = date.today()
    conn = sqlite3.connect('information.db')
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    # Modified query to get ALL records for today (removed DISTINCT)
    cursor = cur.execute("SELECT NAME, Time, Date from Attendance where Date=?", (today,))
    rows = cur.fetchall()
    print("rows", rows)
    # Define class schedule
    class_schedule = [
        {"class": 1, "start": "08:20", "end": "09:00"},
        {"class": 2, "start": "09:10", "end": "09:50"},
        {"class": 3, "start": "10:00", "end": "10:40"},
        {"class": 4, "start": "10:50", "end": "11:30"},
        {"class": 5, "start": "11:40", "end": "12:20"},
        {"class": 6, "start": "12:30", "end": "13:10"},
        {"class": 7, "start": "13:20", "end": "14:00"},
        {"class": 8, "start": "14:10", "end": "14:50"}
    ]
    
    # Function to determine attendance status
    def check_attendance_status(time_str):
        time_obj = datetime.strptime(time_str, "%H:%M").time()
        
        for lesson in class_schedule:
            class_start = datetime.strptime(lesson["start"], "%H:%M").time()
            class_end = datetime.strptime(lesson["end"], "%H:%M").time()
            
            # Calculate break start/end
            break_start = class_end
            next_class_index = lesson["class"]
            if next_class_index < len(class_schedule):
                break_end = datetime.strptime(class_schedule[next_class_index]["start"], "%H:%M").time()
            else:
                break_end = None
                
            # Check if time falls within this class period
            if class_start <= time_obj <= class_end:
                # Late if more than 5 minutes after start
                late_threshold = (datetime.combine(date.today(), class_start) + timedelta(minutes=5)).time()
                if time_obj <= late_threshold:
                    return {"class": lesson["class"], "status": "on time"}
                else:
                    return {"class": lesson["class"], "status": "late"}
            
            # Check if time falls within break period
            if break_end and break_start <= time_obj <= break_end:
                return {"class": lesson["class"], "status": "break", "next_class": lesson["class"] + 1}
        
        # Before first class
        if time_obj < datetime.strptime(class_schedule[0]["start"], "%H:%M").time():
            return {"class": 1, "status": "before school"}
        # After last class
        elif time_obj > datetime.strptime(class_schedule[-1]["end"], "%H:%M").time():
            return {"class": 8, "status": "after school"}
        
        return {"class": None, "status": "unknown"}
    
    # Group attendance data by name
    attendance_by_name = {}
    for row in rows:
        print(row)
        name = row[0]
        time_str = row[1]
        date_str = row[2]
        
        if name not in attendance_by_name:
            attendance_by_name[name] = {
                "name": name,
                "date": str(date_str),
                "times": [],
                "attendance_info": []
            }
        
        # Add time entry
        attendance_by_name[name]["times"].append(time_str)
        
        # Add attendance status
        attendance_status = check_attendance_status(time_str)
        attendance_by_name[name]["attendance_info"].append({
            "time": time_str,
            "class": attendance_status["class"],
            "status": attendance_status["status"]
        })
    
    conn.close()
    return {"status": "success", "attendance_data": list(attendance_by_name.values())}

@app.get('/whole')
def whole():
    conn = sqlite3.connect('information.db')
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    cursor = cur.execute("SELECT DISTINCT NAME,Time, Date from Attendance")
    rows = cur.fetchall()
    
    result = []
    for row in rows:
        result.append({
            "name": row[0],
            "time": row[1],
            "date": str(row[2])
        })
    
    conn.close()
    return {"status": "success", "attendance_data": result}

@app.get('/dashboard')
def dashboard():
    return {"message": "Dashboard data would be returned as JSON"}