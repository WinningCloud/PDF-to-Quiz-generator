from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import os
from quiz_platform.api.init_admin_route import router as init_admin_router


from api import auth_routes, admin_routes, student_routes
from db.database import engine
from db.models import Base


# Create DB tables automatically
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="PDF Quiz Platform API",
    description="AI-powered PDF to Quiz Generation Platform",
    version="1.0.0"
)

# CORS Origins
origins = [
    "http://localhost:5173",
    "http://localhost:5174",
    "http://127.0.0.1:5173",
    "http://127.0.0.1:5174",
    os.getenv("FRONTEND_URL")  # Production frontend URL from Render
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=[o for o in origins if o],  # remove None values
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Static file directory for uploaded PDFs
os.makedirs("data/uploads", exist_ok=True)
app.mount("/uploads", StaticFiles(directory="data/uploads"), name="uploads")

# Routers
app.include_router(auth_routes.router, prefix="/api/auth", tags=["Authentication"])
app.include_router(admin_routes.router, prefix="/api/admin", tags=["Admin"])
app.include_router(student_routes.router, prefix="/api/student", tags=["Student"])
app.include_router(init_admin_router, prefix="/setup", tags=["Setup"])


@app.get("/")
async def root():
    return {"message": "PDF Quiz Platform API", "status": "running"}

@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "pdf-quiz-platform"}
