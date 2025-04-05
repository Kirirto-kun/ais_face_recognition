from sqlalchemy import Column, Integer, String, ForeignKey, DateTime, Boolean, LargeBinary, Date, Time, func
from sqlalchemy.orm import relationship
from datetime import datetime
from base import Base

class User(Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True)
    email = Column(String, unique=True, index=True)
    hashed_password = Column(String)
    role = Column(String, default="student")  # admin, teacher, student
    created_at = Column(DateTime, default=datetime.utcnow)
    is_active = Column(Boolean, default=True)
    
    # Relationships
    student = relationship("Student", back_populates="user", uselist=False)
    teacher = relationship("Teacher", back_populates="user", uselist=False)

class Student(Base):
    __tablename__ = "students"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    student_id = Column(String, unique=True, index=True)  # School/college ID
    first_name = Column(String)
    last_name = Column(String)
    group_id = Column(Integer, ForeignKey("groups.id"))
    
    # Relationships
    user = relationship("User", back_populates="student")
    group = relationship("Group", back_populates="students")
    attendances = relationship("Attendance", back_populates="student")
    face_encoding = relationship("FaceEncoding", back_populates="student", uselist=False)

class Teacher(Base):
    __tablename__ = "teachers"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    first_name = Column(String)
    last_name = Column(String)
    
    # Relationships
    user = relationship("User", back_populates="teacher")
    courses = relationship("Course", back_populates="teacher")

class Group(Base):
    __tablename__ = "groups"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True)
    year = Column(Integer)
    
    # Relationships
    students = relationship("Student", back_populates="group")
    courses = relationship("Course", back_populates="group")

class Course(Base):
    __tablename__ = "courses"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String)
    group_id = Column(Integer, ForeignKey("groups.id"))
    teacher_id = Column(Integer, ForeignKey("teachers.id"))
    
    # Relationships
    group = relationship("Group", back_populates="courses")
    teacher = relationship("Teacher", back_populates="courses")
    sessions = relationship("Session", back_populates="course")

class Session(Base):
    __tablename__ = "sessions"
    
    id = Column(Integer, primary_key=True, index=True)
    course_id = Column(Integer, ForeignKey("courses.id"))
    date = Column(Date)
    start_time = Column(Time)
    end_time = Column(Time)
    
    # Relationships
    course = relationship("Course", back_populates="sessions")
    attendances = relationship("Attendance", back_populates="session")

class Attendance(Base):
    __tablename__ = "attendance"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    time = Column(String, nullable=False)
    date = Column(String, nullable=False)
    created_at = Column(DateTime, default=func.now())
    
    # Optional relationships to support both uses
    student_id = Column(Integer, ForeignKey("students.id"), nullable=True)
    session_id = Column(Integer, ForeignKey("sessions.id"), nullable=True)
    present = Column(Boolean, default=True)
    
    # Relationships
    student = relationship("Student", back_populates="attendances")
    session = relationship("Session", back_populates="attendances")
    
    def __repr__(self):
        return f"<Attendance(name='{self.name}', date='{self.date}', time='{self.time}')>"

class FaceEncoding(Base):
    __tablename__ = "face_encodings"
    
    id = Column(Integer, primary_key=True, index=True)
    student_id = Column(Integer, ForeignKey("students.id"), unique=True)
    encoding_data = Column(LargeBinary)  # Stores the 128-dimension face encoding as binary
    image_path = Column(String)  # Path to the face image file
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    student = relationship("Student", back_populates="face_encoding")
