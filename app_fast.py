from fastapi import FastAPI, Form, File, UploadFile, Depends, HTTPException
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, List, Dict
import cv2
import numpy as np
import face_recognition
import os
from datetime import datetime
from datetime import date
import sqlite3
import json
import pandas as pd
import uvicorn
import shutil

# Create FastAPI app
app = FastAPI()

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
        path = 'C:/Users/User/Desktop/face/face-recognition-attendance-management-system-with-PowerBI-dashboard-main/Training images'
        
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

@app.post("/")
def recognize_post():
    path = 'Training images'
    images = []
    classNames = []
    myList = os.listdir(path)
    
    for cl in myList:
        curImg = cv2.imread(f'{path}/{cl}')
        images.append(curImg)
        classNames.append(os.path.splitext(cl)[0])

    def findEncodings(images):
        encodeList = []
        for img in images:
            img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
            encode = face_recognition.face_encodings(img)[0]
            if not len(encode):
                continue
            encodeList.append(encode)
        return encodeList

    def markData(name):
        now = datetime.now()
        dtString = now.strftime('%H:%M')
        today = date.today()
        conn = sqlite3.connect('information.db')
        conn.execute('''CREATE TABLE IF NOT EXISTS Attendance
                        (NAME TEXT  NOT NULL,
                         Time  TEXT NOT NULL ,Date TEXT NOT NULL)''')

        conn.execute("INSERT or Ignore into Attendance (NAME,Time,Date) values (?,?,?)", (name, dtString, today,))
        conn.commit()
        cursor = conn.execute("SELECT NAME,Time,Date from Attendance")
        conn.close()
        return {"name": name, "time": dtString, "date": str(today)}

    def markAttendance(name):
        with open('attendance.csv', 'r+', errors='ignore') as f:
            myDataList = f.readlines()
            nameList = []
            for line in myDataList:
                entry = line.split(',')
                nameList.append(entry[0])
            if name not in nameList:
                now = datetime.now()
                dtString = now.strftime('%H:%M')
                f.writelines(f'\n{name},{dtString}')

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
                attendance_data = markData(name)
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

@app.post('/login')
def login(request: LoginRequest):
    username = request.username
    password = request.password
    
    df = pd.read_csv('cred.csv')
    if len(df.loc[df['username'] == username]['password'].values) > 0:
        if df.loc[df['username'] == username]['password'].values[0] == password:
            sessions[username] = True
            return {"status": "success", "username": username}
        else:
            return {"status": "failed", "message": "Invalid password"}
    else:
        return {"status": "failed", "message": "User not found"}

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
    cursor = cur.execute("SELECT DISTINCT NAME,Time, Date from Attendance where Date=?", (today,))
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

@app.get('/data')
def data_get():
    return {"message": "Use POST to retrieve today's attendance data"}

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