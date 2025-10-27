"""
Standalone video analysis server that handles video uploads and processes them.
This server combines image extraction and model analysis functionality.
"""

import os
import tempfile
import subprocess
import glob
import json
import base64
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import urllib.parse

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Try to import the model prediction function
try:
    # Add the model container directory to the path
    import sys
    sys.path.append(os.path.join(os.path.dirname(__file__), 'model_container'))
    from main import predict
    MODEL_AVAILABLE = True
    logger.info("Model loaded successfully")
except ImportError as e:
    logger.warning(f"Model not available - running in simulation mode: {e}")
    MODEL_AVAILABLE = False
    
    def predict(image_path: str) -> int:
        """Simulate model prediction for testing"""
        import random
        return random.randint(0, 5)


def extract_frames(video_path: str, step_seconds: float = 1.0, out_dir: Optional[str] = None) -> List[str]:
    """
    Use ffmpeg to extract frames approximately every `step_seconds` seconds.
    """
    if not os.path.exists(video_path):
        raise FileNotFoundError(f"Video file not found: {video_path}")
    if step_seconds <= 0:
        raise ValueError("Step must be greater than 0 seconds.")

    temp_dir = out_dir or tempfile.mkdtemp(prefix="frames_")
    os.makedirs(temp_dir, exist_ok=True)
    out_pattern = os.path.join(temp_dir, "frame_%05d.jpg")

    cmd = [
        "ffmpeg",
        "-hide_banner",
        "-loglevel", "error",
        "-y",
        "-i", video_path,
        "-vf", f"fps=1/{step_seconds}",
        "-q:v", "2",
        out_pattern,
    ]

    logger.info(f"Extracting frames from {video_path} every {step_seconds}s")
    subprocess.run(cmd, check=True)

    frames = sorted(glob.glob(os.path.join(temp_dir, "frame_*.jpg")))
    if not frames:
        raise RuntimeError(f"No frames extracted. Possibly video too short or invalid step {step_seconds}s.")
    
    logger.info(f"Extracted {len(frames)} frames")
    return frames


def process_video_frames(frames: List[str]) -> Dict[str, Any]:
    """
    Process each frame through the model and return results.
    """
    frame_results = []
    total_garbage_count = 0
    
    for idx, frame_path in enumerate(frames, start=1):
        frame_name = os.path.basename(frame_path)
        logger.info(f"Processing frame {idx}/{len(frames)}: {frame_name}")
        
        try:
            garbage_count = predict(frame_path)
            frame_results.append({
                "frame": frame_name,
                "garbage_count": garbage_count
            })
            total_garbage_count += garbage_count
            logger.info(f"Frame {frame_name}: {garbage_count} objects detected")
        except Exception as e:
            logger.error(f"Error processing frame {frame_name}: {e}")
            frame_results.append({
                "frame": frame_name,
                "garbage_count": 0,
                "error": str(e)
            })
    
    return {
        "frame_results": frame_results,
        "total_garbage_count": total_garbage_count,
        "frames_processed": len(frames)
    }


class VideoAnalysisHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        """Handle GET requests - return server info"""
        if self.path == '/':
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            response = {
                "status": "running",
                "service": "video-analysis-server",
                "model_available": MODEL_AVAILABLE
            }
            self.wfile.write(json.dumps(response).encode('utf-8'))
        elif self.path == '/health':
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(json.dumps({"status": "healthy"}).encode('utf-8'))
        else:
            self.send_response(404)
            self.end_headers()
    
    def do_OPTIONS(self):
        """Handle CORS preflight requests"""
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()
    
    def do_POST(self):
        """Handle POST requests for video analysis"""
        if self.path == '/analyze-video':
            self.handle_video_analysis()
        else:
            self.send_response(404)
            self.end_headers()
    
    def handle_video_analysis(self):
        """Handle video upload and analysis"""
        try:
            # Parse multipart form data
            content_type = self.headers.get('Content-Type', '')
            if not content_type.startswith('multipart/form-data'):
                self.send_error(400, "Content-Type must be multipart/form-data")
                return
            
            # Read the request body
            content_length = int(self.headers.get('Content-Length', 0))
            if content_length == 0:
                self.send_error(400, "No content received")
                return
            
            body = self.rfile.read(content_length)
            
            # Parse multipart data (simplified parser)
            boundary = content_type.split('boundary=')[1]
            parts = body.split(f'--{boundary}'.encode())
            
            video_data = None
            title = ""
            step_seconds = 1.0
            
            for part in parts:
                if b'name="video"' in part:
                    # Extract video file
                    header_end = part.find(b'\r\n\r\n')
                    if header_end != -1:
                        video_data = part[header_end + 4:]
                        # Remove trailing boundary markers
                        if video_data.endswith(b'\r\n'):
                            video_data = video_data[:-2]
                elif b'name="title"' in part:
                    # Extract title
                    header_end = part.find(b'\r\n\r\n')
                    if header_end != -1:
                        title_bytes = part[header_end + 4:]
                        if title_bytes.endswith(b'\r\n'):
                            title_bytes = title_bytes[:-2]
                        title = title_bytes.decode('utf-8')
                elif b'name="step_seconds"' in part:
                    # Extract step_seconds
                    header_end = part.find(b'\r\n\r\n')
                    if header_end != -1:
                        step_bytes = part[header_end + 4:]
                        if step_bytes.endswith(b'\r\n'):
                            step_bytes = step_bytes[:-2]
                        try:
                            step_seconds = float(step_bytes.decode('utf-8'))
                        except ValueError:
                            step_seconds = 1.0
            
            if not video_data:
                self.send_error(400, "No video file provided")
                return
            
            if not title.strip():
                self.send_error(400, "No title provided")
                return
            
            logger.info(f"Processing video analysis: {title}")
            
            # Save video to temporary file
            with tempfile.NamedTemporaryFile(delete=False, suffix='.mp4') as temp_video:
                temp_video.write(video_data)
                temp_video_path = temp_video.name
            
            try:
                # Extract frames
                frames = extract_frames(temp_video_path, step_seconds)
                
                # Process frames through model
                analysis_result = process_video_frames(frames)
                
                # Compile final results
                result = {
                    "title": title,
                    "video": os.path.basename(temp_video_path),
                    "step_seconds": step_seconds,
                    "frames_processed": analysis_result["frames_processed"],
                    "total_garbage_count": analysis_result["total_garbage_count"],
                    "average_garbage_count": analysis_result["total_garbage_count"] / analysis_result["frames_processed"] if analysis_result["frames_processed"] > 0 else 0,
                    "frame_results": analysis_result["frame_results"]
                }
                
                # Send response
                self.send_response(200)
                self.send_header('Content-Type', 'application/json')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.end_headers()
                self.wfile.write(json.dumps(result, indent=2).encode('utf-8'))
                
                logger.info(f"Analysis completed: {analysis_result['total_garbage_count']} total objects in {analysis_result['frames_processed']} frames")
                
            finally:
                # Clean up temporary files
                try:
                    os.unlink(temp_video_path)
                    # Clean up frame files
                    for frame in frames:
                        if os.path.exists(frame):
                            os.unlink(frame)
                    # Remove frame directory
                    frame_dir = os.path.dirname(frames[0]) if frames else None
                    if frame_dir and os.path.exists(frame_dir):
                        os.rmdir(frame_dir)
                except Exception as e:
                    logger.warning(f"Error cleaning up temporary files: {e}")
                    
        except Exception as e:
            logger.error(f"Error processing video analysis: {e}")
            self.send_error(500, f"Internal server error: {str(e)}")
    
    def log_message(self, format, *args):
        """Suppress default logging"""
        pass


def run_server(host: str = "0.0.0.0", port: int = 8001):
    """Run the video analysis server"""
    server = ThreadingHTTPServer((host, port), VideoAnalysisHandler)
    logger.info(f"Video analysis server starting on http://{host}:{port}")
    logger.info(f"Model available: {MODEL_AVAILABLE}")
    
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        logger.info("Server stopped by user")
    finally:
        server.server_close()
        logger.info("Server stopped")


if __name__ == "__main__":
    run_server()
