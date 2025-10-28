#!/usr/bin/env python3
"""
Backend API Server for Video Analysis
Simple FastAPI server that processes videos using the existing Docker pipeline
"""

from fastapi import FastAPI, File, UploadFile, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import subprocess
import os
import tempfile
import json
import shutil
from pathlib import Path
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Video Analysis API", version="1.0.0")

# Enable CORS for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure this for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configuration
MAX_FILE_SIZE = 100 * 1024 * 1024  # 100MB
ALLOWED_EXTENSIONS = {".mp4", ".avi", ".mov", ".mkv"}
TEMP_DIR = Path("temp_uploads")
TEMP_DIR.mkdir(exist_ok=True)

@app.post("/api/analyze-video")
async def analyze_video(
    video_file: UploadFile = File(...),
    userId: str = Form(...)
):
    """
    Analyze uploaded video for garbage detection
    """
    try:
        # Validate userId
        if not userId or len(userId.strip()) == 0:
            raise HTTPException(status_code=400, detail="userId is required")
        
        # Validate file
        if not video_file.filename:
            raise HTTPException(status_code=400, detail="No file uploaded")
        
        file_extension = Path(video_file.filename).suffix.lower()
        if file_extension not in ALLOWED_EXTENSIONS:
            raise HTTPException(
                status_code=400, 
                detail=f"Unsupported file type. Allowed: {', '.join(ALLOWED_EXTENSIONS)}"
            )
        
        # Read file content
        content = await video_file.read()
        if len(content) > MAX_FILE_SIZE:
            raise HTTPException(
                status_code=400, 
                detail=f"File too large. Max size: {MAX_FILE_SIZE // (1024*1024)}MB"
            )
        
        logger.info(f"Processing video for userId: {userId}, size: {len(content)} bytes")
        
        # Save video to temporary file
        temp_video_path = TEMP_DIR / f"{userId}_{video_file.filename}"
        with open(temp_video_path, "wb") as f:
            f.write(content)
        
        try:
            # Copy video to input directory for container
            # Both containers now use /app/input as the mount point
            input_video_path = Path("/app/input") / f"{userId}_{video_file.filename}"
            shutil.copy2(temp_video_path, input_video_path)
            
            # Set the correct path for the container (relative to /app/input)
            container_video_path = f"/app/input/{userId}_{video_file.filename}"
            
            # Set environment variables and run container
            env = os.environ.copy()
            env["INPUT_PATH"] = container_video_path
            env["USER_ID"] = userId
            
            logger.info(f"Running Docker container for userId: {userId}")
            
            # Use docker-compose to run the image processing container
            # This automatically handles networking and volume mounts
            result = subprocess.run([
                "docker-compose", "run", "--rm",
                "-e", f"INPUT_PATH={container_video_path}",
                "-e", f"USER_ID={userId}",
                "imageclient"
            ], capture_output=True, text=True, cwd=os.getcwd())
            
            if result.returncode != 0:
                logger.error(f"Docker container failed: {result.stderr}")
                raise HTTPException(
                    status_code=500, 
                    detail=f"Video processing failed: {result.stderr}"
                )
            
            # Parse the JSON output from container
            try:
                # The container outputs JSON mixed with log messages
                # Find the JSON object in the output
                stdout = result.stdout.strip()
                
                # Find the start of JSON (first '{')
                json_start = stdout.find('{')
                if json_start == -1:
                    raise ValueError("No JSON object found in output")
                
                # Extract JSON part
                json_str = stdout[json_start:]
                
                # Parse JSON
                json_output = json.loads(json_str)
                
                logger.info(f"Successfully processed video for userId: {userId}")
                
                return {
                    "success": True,
                    "userId": userId,
                    "results": json_output
                }
                
            except (json.JSONDecodeError, ValueError) as e:
                logger.error(f"Failed to parse container output: {e}")
                logger.error(f"Container stdout: {result.stdout}")
                raise HTTPException(
                    status_code=500, 
                    detail="Failed to parse processing results"
                )
        
        finally:
            # Cleanup temporary files
            if temp_video_path.exists():
                temp_video_path.unlink()
            if input_video_path.exists():
                input_video_path.unlink()
            logger.info(f"Cleaned up temporary files for userId: {userId}")
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error processing video for userId {userId}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "service": "video-analysis-api"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
