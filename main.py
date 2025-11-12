"""
Web Crawling Agent API - Entry Point
This module imports and exposes the FastAPI app from the app package
"""
from app.main import app

# Expose the app for uvicorn
__all__ = ["app"]

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
