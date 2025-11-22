"""Main FastAPI application entry point."""
import os
from pathlib import Path
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from api import upload, processing, sections, alignment, export

# Application setup
app = FastAPI(
    title="Call/Response Analysis API",
    description="API for analyzing call and response patterns in audio",
    version="1.0.0"
)

# CORS configuration for development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Data directory for uploads and processing
DATA_DIR = Path(__file__).parent.parent / "data"
DATA_DIR.mkdir(exist_ok=True)

# Frontend directory (for production)
FRONTEND_DIR = Path(__file__).parent.parent / "frontend" / "dist"

# Mount static files for serving audio
app.mount("/audio", StaticFiles(directory=str(DATA_DIR)), name="audio")

# Include API routers
app.include_router(upload.router, prefix="/api", tags=["Upload"])
app.include_router(processing.router, prefix="/api", tags=["Processing"])
app.include_router(sections.router, prefix="/api", tags=["Sections"])
app.include_router(alignment.router, prefix="/api", tags=["Alignment"])
app.include_router(export.router, prefix="/api", tags=["Export"])

# Serve frontend static files in production
if FRONTEND_DIR.exists():
    app.mount("/assets", StaticFiles(directory=str(FRONTEND_DIR / "assets")), name="assets")

    @app.get("/")
    async def serve_frontend():
        """Serve the frontend index.html."""
        return FileResponse(FRONTEND_DIR / "index.html")

    @app.get("/{path:path}")
    async def serve_frontend_routes(path: str, request: Request):
        """Serve frontend for client-side routing, except API routes."""
        # Don't interfere with API routes
        if path.startswith("api/") or path.startswith("audio/"):
            return {"error": "Not found"}

        # Check if it's a static file
        file_path = FRONTEND_DIR / path
        if file_path.exists() and file_path.is_file():
            return FileResponse(file_path)

        # Return index.html for client-side routing
        return FileResponse(FRONTEND_DIR / "index.html")
else:
    @app.get("/")
    async def root():
        """Health check endpoint (dev mode - frontend served separately)."""
        return {"status": "ok", "message": "Call/Response Analysis API", "mode": "development"}


@app.get("/api/health")
async def health_check():
    """Detailed health check."""
    return {
        "status": "healthy",
        "data_dir": str(DATA_DIR),
        "data_dir_exists": DATA_DIR.exists()
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
