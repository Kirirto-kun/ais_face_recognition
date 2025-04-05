from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from routes.auth.auth_routes import router as auth_router
from routes.admin.admin_routes import router as admin_router
from routes.student.student_routes import router as student_router
from schema.database import engine, Base
import uvicorn

# Create database tables
Base.metadata.create_all(bind=engine)

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

# Include routers
app.include_router(auth_router, prefix="/auth", tags=["Authentication"])
app.include_router(admin_router, prefix="/admin", tags=["Admin"])
app.include_router(student_router, prefix="/student", tags=["Student"])

@app.get("/")
async def root():
    return {"message": "Welcome to the Face Recognition Attendance System API"}

@app.get("/health")
async def health_check():
    return {"status": "healthy"}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)



