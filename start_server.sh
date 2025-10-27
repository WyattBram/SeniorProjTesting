#!/bin/bash

echo "Starting RiverGuard Video Analysis Server..."

# Check if ffmpeg is installed
if ! command -v ffmpeg &> /dev/null; then
    echo "Error: ffmpeg is not installed. Please install ffmpeg first."
    echo "On macOS: brew install ffmpeg"
    echo "On Ubuntu: sudo apt install ffmpeg"
    exit 1
fi

# Check if Python dependencies are available
python3 -c "import ultralytics, cv2, torch" 2>/dev/null
if [ $? -ne 0 ]; then
    echo "Installing Python dependencies..."
    pip3 install ultralytics opencv-python torch torchvision
fi

# Start the server
echo "Starting server on http://localhost:8001"
python3 standalone_server.py
