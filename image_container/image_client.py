from __future__ import annotations

import json
import urllib.request
import base64
import os
import subprocess
import tempfile
import glob
from typing import List, Optional, Dict, Any

# Dracula: "I have more percs than there are stars in the leo cluster"

def send_json(url: str = "http://visionmodel:8001/", data: dict | None = None) -> str:
    body = json.dumps(data or {}).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=body,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req) as response:
        return response.read().decode("utf-8")


def send_image(url: str = "http://visionmodel:8001/", image_path: str = "") -> str:
    """Send an image file to the model"""
    try:
        with open(image_path, "rb") as f:
            image_data = base64.b64encode(f.read()).decode('utf-8')

        data = {
            "image_data": image_data,
            "filename": os.path.basename(image_path)
        }
        return send_json(url, data)
    except Exception as e:
        return json.dumps({"error": str(e)})


# ---------------------------------------------------
# NEW: Dynamic video slicing + per-frame model sending
# ---------------------------------------------------

def extract_frames(video_path: str, step_seconds: float, out_dir: Optional[str] = None) -> List[str]:
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

    subprocess.run(cmd, check=True)

    frames = sorted(glob.glob(os.path.join(temp_dir, "frame_*.jpg")))
    if not frames:
        raise RuntimeError(f"No frames extracted. Possibly video too short or invalid step {step_seconds}s.")
    return frames


def splice_and_send_video(
    video_path: str,
    step: str,
    target_url: str = "http://visionmodel:8001/",
    max_frames: Optional[int] = None
) -> Dict[str, Any]:
    """
    Dynamically extract frames every `step` seconds and send each frame
    to the backend model endpoint via send_image().
    Returns a structured dict summarizing the entire run.
    """
    # Parse step value
    try:
        step_seconds = float(step)
        if step_seconds <= 0:
            raise ValueError
    except Exception:
        return {"ok": False, "error": f"Invalid step value '{step}'. Must be a positive number."}

    # Extract frames from the video
    try:
        frames = extract_frames(video_path, step_seconds)
    except Exception as e:
        return {"ok": False, "error": f"Frame extraction failed: {e}"}

    if max_frames and len(frames) > max_frames:
        frames = frames[:max_frames]

    responses: list[dict[str, Any]] = []

    # Send each frame via send_image()
    for idx, frame_path in enumerate(frames, start=1):
        frame_name = os.path.basename(frame_path)
        print(f"Sending frame {idx}/{len(frames)} -> {frame_name}")

        raw_response = send_image(target_url, frame_path)

        # Attempt to parse backend JSON response
        try:
            parsed = json.loads(raw_response)
        except Exception:
            parsed = {"error": f"Non-JSON response from backend", "raw": raw_response}

        responses.append({
            "frame": frame_name,
            "response": parsed
        })

    return {
        "ok": True,
        "video": os.path.basename(video_path),
        "step_seconds": step_seconds,
        "frames_sent": len(frames),
        "responses": responses
    }

# ---------------------------------------------------
# Example entrypoint for Docker
# ---------------------------------------------------
if __name__ == "__main__":
    VIDEO_PATH = os.getenv("INPUT_PATH", "../input/myvideo.mp4")
    STEP = os.getenv("STEP", "1")  # ← this can be any float as a string
    TARGET = os.getenv("WORKER_URL", "http://visionmodel:8001/")
    MAX = os.getenv("MAX_FRAMES")

    max_frames = int(MAX) if (MAX and MAX.isdigit()) else None

    print(f"Extracting frames every {STEP}s from '{VIDEO_PATH}' and sending to {TARGET}")
    result = splice_and_send_video(VIDEO_PATH, STEP, TARGET, max_frames)
    
    print(json.dumps(result, indent=2))