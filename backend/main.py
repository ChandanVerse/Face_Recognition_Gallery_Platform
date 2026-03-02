"""
FastAPI application with proper CORS configuration
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from contextlib import asynccontextmanager
from pathlib import Path
from backend.config.settings import get_settings

settings = get_settings()

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifecycle events"""
    print("[INFO] Starting FaceFind API")
    # Initialize MongoDB indexes for optimal query performance
    from backend.config.database import initialize_indexes
    initialize_indexes()
    yield
    print("[INFO] Shutting down API")

app = FastAPI(
    title="FaceFind API",
    description="AI-Powered Photo Discovery Platform",
    version="1.0.0",
    lifespan=lifespan
)

# CORS Configuration - CRITICAL FIX
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,  # Uses the list from settings
    allow_credentials=True,
    allow_methods=["*"],  # Allow all methods (GET, POST, PUT, DELETE, OPTIONS, etc.)
    allow_headers=["*"],  # Allow all headers
    expose_headers=["*"],
)

@app.get("/")
def read_root():
    return {"message": "FaceFind API is running"}

@app.get("/health")
def health_check():
    return {"status": "healthy"}

# Import and include routers
from backend.api.routes import auth, galleries, photos

app.include_router(auth.router, prefix="/api/auth", tags=["auth"])
app.include_router(galleries.router, prefix="/api/galleries", tags=["galleries"])
app.include_router(photos.router, prefix="/api", tags=["photos"])

# Mount static files for local storage
storage_path = Path(settings.STORAGE_BASE_PATH)
storage_path.mkdir(parents=True, exist_ok=True)
app.mount("/storage", StaticFiles(directory=str(storage_path)), name="storage")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="localhost",
        port=8000,
        reload=settings.DEBUG
    )