"""
Start the SecureScanner backend.
Reload is disabled so background scan tasks are never interrupted.

Usage:
    python run.py
"""
import uvicorn

if __name__ == "__main__":
    uvicorn.run(
        "app.main:app",
        host="127.0.0.1",
        port=8000,
        reload=False,   # MUST be False — reload kills background scan tasks
    )