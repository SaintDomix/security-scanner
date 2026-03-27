from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import os
from dotenv import load_dotenv

load_dotenv()

from app.models.database import engine
from app.models.models import Base
from app.routers import auth, users, scans

Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="SecureScanner API",
    description="Security scanning platform — SAST, Secrets, DAST",
    version="2.0.0",
    redirect_slashes=False,
)

FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:5173")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[FRONTEND_URL, "http://localhost:3000", "http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(users.router)
app.include_router(scans.router)

os.makedirs("reports", exist_ok=True)
app.mount("/reports", StaticFiles(directory="reports"), name="reports")


@app.get("/")
def root():
    return {"message": "SecureScanner API v2", "docs": "/docs"}


@app.get("/health")
def health():
    return {"status": "ok"}