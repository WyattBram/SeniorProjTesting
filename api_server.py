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
import firebase_admin
from firebase_admin import credentials, firestore
from datetime import datetime

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize Firebase
try:
    cred_path = Path("/app/RiverGuardAccountKey.json")
    if cred_path.exists():
        cred = credentials.Certificate(str(cred_path))
        firebase_admin.initialize_app(cred, {
            "projectId": "trashapi-6eced",
            "storageBucket": "trashapi-6eced.appspot.com"
        })
        db = firestore.client()
        logger.info("Firebase initialized successfully")
    else:
        logger.warning(f"Firebase credentials not found at {cred_path}. Firebase features disabled.")
        db = None
except Exception as e:
    logger.error(f"Failed to initialize Firebase: {e}")
    db = None

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

def save_results_to_firestore(user_id: str, video_filename: str, results: dict):
    """
    Save analysis results to Firestore database.
    Returns True if successful, False otherwise.
    """
    if db is None:
        logger.warning("Firebase not available, skipping database save")
        return False
    
    try:
        # Calculate summary statistics
        total_garbage = 0
        frames_processed = 0
        garbage_count_per_frame = []
        
        if results.get("ok") and "responses" in results:
            for frame_response in results["responses"]:
                frame_data = frame_response.get("response", {})
                garbage_count = frame_data.get("garbage_count", 0)
                total_garbage += garbage_count
                frames_processed += 1
                garbage_count_per_frame.append(garbage_count)
        
        # Create document data with only required fields
        doc_data = {
            "userId": user_id,
            "videoFilename": video_filename,
            "uploadDate": datetime.now(),
            "totalGarbageCount": total_garbage,
            "framesProcessed": frames_processed,
            "garbageCountPerFrame": garbage_count_per_frame
        }
        
        # Save to Firestore using userId as document ID
        doc_ref = db.collection("videos").document(user_id).set(doc_data)
        logger.info(f"Saved analysis results to Firestore for userId: {user_id} (used as doc ID)")
        return True
        
    except Exception as e:
        logger.error(f"Failed to save to Firestore: {e}")
        return False

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
        
        # Save video to temporary file in a location accessible to Docker
        temp_video_path = Path("/tmp") / f"{userId}_{video_file.filename}"
        with open(temp_video_path, "wb") as f:
            f.write(content)
        
        try:
            # Create a simple filename for the container mount
            container_filename = f"{userId}_{video_file.filename}".replace("_", "-")
            
            # Use docker cp to copy the file into the container instead of mounting
            # This avoids Docker volume mount issues completely
            container_name = f"imageclient_{userId}"
            
            # Start a temporary container
            subprocess.run([
                "docker", "run", "-d",
                "--name", container_name,
                "--network", "seniorprojtesting_my-network",
                "-e", f"USER_ID={userId}",
                "-e", "WORKER_URL=http://visionmodel:8001/",
                "seniorprojtesting-imageclient",
                "sleep", "300"  # Keep container alive for 5 minutes
            ], capture_output=True, text=True, cwd=os.getcwd())
            
            # Copy the video file into the container
            subprocess.run([
                "docker", "cp", str(temp_video_path.absolute()), f"{container_name}:/tmp/video.mp4"
            ], capture_output=True, text=True, cwd=os.getcwd())
            
            # Run the processing command
            result = subprocess.run([
                "docker", "exec", container_name,
                "python", "-c", 
                f"import os; os.environ['INPUT_PATH']='/tmp/video.mp4'; exec(open('/app/image_client.py').read())"
            ], capture_output=True, text=True, cwd=os.getcwd())
            
            # Clean up the temporary container
            subprocess.run(["docker", "rm", "-f", container_name], capture_output=True, text=True)
            
            logger.info(f"Container return code: {result.returncode}")
            logger.info(f"Container stdout: {result.stdout}")
            logger.info(f"Container stderr: {result.stderr}")
            
            # Don't fail on non-zero return code - check if we got valid JSON output
            if not result.stdout.strip():
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
                
                # Save results to Firestore (non-blocking)
                try:
                    save_results_to_firestore(userId, video_file.filename, json_output)
                except Exception as e:
                    logger.error(f"Failed to save results to Firestore: {e}")
                    # Don't fail the request if Firestore save fails
                
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
