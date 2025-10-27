# Video Analysis API

This project implements a complete video analysis system with a REST API that processes video frames through a YOLO model for garbage detection.

## Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Frontend      │    │  Backend API    │    │  Model Server   │
│                 │    │                 │    │                 │
│ - Uploads video │───▶│ - Receives      │───▶│ - Receives      │
│ - Sends userId  │    │   video + userId│    │   images        │
│ - Gets results  │◀───│ - Processes     │◀───│ - Runs YOLO     │
│                 │    │   via containers│    │   prediction    │
└─────────────────┘    └─────────────────┘    └─────────────────┘
                              │
                              ▼
                       ┌─────────────────┐
                       │ Image Container │
                       │                 │
                       │ - Extracts      │
                       │   frames        │
                       │ - Sends to      │
                       │   model         │
                       └─────────────────┘
```

## Components

### Backend API Server (`api_server.py`)
- **Purpose**: REST API endpoint for video analysis
- **Key Features**:
  - FastAPI-based HTTP server
  - Video upload handling (multipart/form-data)
  - Docker container orchestration
  - JSON response formatting
- **Endpoints**:
  - `POST /api/analyze-video`: Main video analysis endpoint
  - `GET /health`: Health check endpoint

### Image Container (`image_container/`)
- **Purpose**: Extracts frames from video files and sends them to the model
- **Key Files**:
  - `image_client.py`: Main client that processes videos and sends frames
  - `dockerfile`: Container configuration
- **Features**:
  - Video frame extraction using FFmpeg
  - Base64 encoding of images
  - HTTP communication with model container
  - Configurable frame extraction intervals

### Model Container (`model_container/`)
- **Purpose**: Receives images and runs YOLO predictions
- **Key Files**:
  - `model_server.py`: HTTP server that receives images
  - `main.py`: YOLO prediction logic
  - `FinalModel.pt`: Trained YOLO model
  - `dockerfile`: Container configuration
- **Features**:
  - HTTP server for receiving images
  - YOLO model inference
  - Garbage detection and counting
  - Comprehensive logging and error handling

## Quick Start

### 1. Start All Services

```bash
# Start the complete system (API server + model server)
docker-compose up -d
```

This will:
- Build and run the API server on port 8000
- Build and run the model server on port 8001
- Create a Docker network for inter-container communication
- Set up health checks and auto-restart

### 2. Test the API

#### **Using curl (Command Line)**
```bash
# Test health endpoint
curl -X GET http://localhost:8000/health

# Analyze a video
curl -X POST \
  -F "video_file=@image_container/input/floating-trash-and-ball-drift-on-polluted-river-surface-SBV-352831077-preview.mp4" \
  -F "userId=test_user_123" \
  http://localhost:8000/api/analyze-video
```

#### **Using JavaScript/Frontend**
```javascript
const formData = new FormData();
formData.append('video_file', videoFile);
formData.append('userId', 'user123');

const response = await fetch('http://localhost:8000/api/analyze-video', {
  method: 'POST',
  body: formData
});

const result = await response.json();
console.log(result);
```

### 3. Legacy Processing (Direct Container Usage)

For direct container usage without the API:

```bash
# Process video with default settings (1-second intervals)
./process_video.sh

# Process video with custom settings
./process_video.sh 2 5  # 2-second intervals, max 5 frames
```

### 4. Monitor and Debug

#### **View Logs**
```bash
# Check API server logs
docker-compose logs api-server

# Check model server logs
docker-compose logs visionmodel

# Follow logs in real-time
docker-compose logs -f api-server
docker-compose logs -f visionmodel
```

#### **System Status**
```bash
# See all running containers
docker-compose ps

# See all containers (including stopped ones)
docker ps -a

# Check Docker network
docker network ls
docker network inspect seniorprojtesting_my-network
```

#### **Clean Up**
```bash
# Stop all services
docker-compose down

# Stop and restart specific services
docker-compose restart api-server
docker-compose restart visionmodel

# Remove all containers and networks
docker-compose down --volumes --remove-orphans
```

## API Documentation

### Backend API Server (`http://localhost:8000`)

#### **POST /api/analyze-video**
Analyzes a video for garbage detection.

**Request:**
- **Method**: POST
- **Content-Type**: multipart/form-data
- **Parameters**:
  - `video_file`: Video file (required)
  - `userId`: User identifier (required)

**Response:**
```json
{
  "success": true,
  "userId": "test_user_123",
  "results": {
    "ok": true,
    "video": "test_user_123_video.mp4",
    "frames_sent": 16,
    "responses": [
      {
        "frame": "frame_00001.jpg",
        "response": {
          "garbage_count": 0,
          "filename": "frame_00001.jpg",
          "message": "Image processed successfully"
        }
      },
      {
        "frame": "frame_00002.jpg",
        "response": {
          "garbage_count": 1,
          "filename": "frame_00002.jpg",
          "message": "Image processed successfully"
        }
      }
    ]
  }
}
```

#### **GET /health**
Health check endpoint.

**Response:**
```json
{
  "status": "healthy",
  "service": "video-analysis-api"
}
```

### Expected Output

When you call the API, you should see output like this:

```json
{
  "success": true,
  "userId": "test_user_123",
  "results": {
    "ok": true,
    "video": "test_user_123_floating-trash-video.mp4",
    "frames_sent": 16,
    "responses": [
      {
        "frame": "frame_00001.jpg",
        "response": {
          "garbage_count": 0,
          "filename": "frame_00001.jpg",
          "message": "Image processed successfully"
        }
      },
      {
        "frame": "frame_00005.jpg",
        "response": {
          "garbage_count": 1,
          "filename": "frame_00005.jpg",
          "message": "Image processed successfully"
        }
      },
      {
        "frame": "frame_00009.jpg",
        "response": {
          "garbage_count": 2,
          "filename": "frame_00009.jpg",
          "message": "Image processed successfully"
        }
      }
    ]
  }
}
```

## Configuration

### Environment Variables

The image container supports these environment variables:

- `INPUT_PATH`: Path to input video (default: `../input/myvideo.mp4`)
- `STEP`: Frame extraction interval in seconds (default: `1`)
- `WORKER_URL`: Model server URL (default: `http://visionmodel:8001/`)
- `MAX_FRAMES`: Maximum number of frames to process (optional)

### Example Usage

```bash
# Process video with 2-second intervals
docker run --network my-network \
  -e STEP=2 \
  -e INPUT_PATH=/app/input/myvideo.mp4 \
  imageclient
```

## Legacy API Endpoints

### Model Server (`http://localhost:8001/`)

**POST /** - Process an image (used internally by the system)
- **Request**: JSON with `image_data` (base64) and `filename`
- **Response**: JSON with `garbage_count`, `filename`, and `message`

Example request:
```json
{
  "image_data": "base64_encoded_image_data",
  "filename": "frame_001.jpg"
}
```

Example response:
```json
{
  "garbage_count": 3,
  "filename": "frame_001.jpg",
  "message": "Image processed successfully"
}
```

**Note**: This endpoint is used internally by the image container. For external use, use the Backend API Server at `http://localhost:8000/api/analyze-video`.

## Logging

All services include comprehensive logging:

- **API Server**: Logs video uploads, processing requests, and responses
- **Image Container**: Logs frame extraction, encoding, and network communication
- **Model Container**: Logs image reception, prediction results, and errors

View logs:
```bash
# View API server logs
docker logs api-server

# View model container logs
docker logs visionmodel

# View image container logs (when running)
docker logs imageclient
```

## Troubleshooting

### Common Issues

1. **API server not accessible**
   - Check if containers are running: `docker ps`
   - Verify API server is running: `curl http://localhost:8000/health`
   - Check logs: `docker logs api-server`
   - Ensure port 8000 is exposed: `docker ps | grep 8000`

2. **Model server not accessible**
   - Check if containers are running: `docker ps`
   - Verify network: `docker network ls`
   - Check logs: `docker logs visionmodel`
   - Ensure port 8001 is exposed: `docker ps | grep 8001`

3. **Video processing fails**
   - Ensure input video exists and is accessible
   - Check file permissions
   - Verify FFmpeg is working: `docker exec imageclient ffmpeg -version`
   - Check video path in container: `docker run --rm -v $(pwd)/image_container/input:/app/input imageclient ls -la /app/input/`

4. **Network connectivity issues**
   - Ensure all containers are on the same network
   - Check container names match the URLs in the code
   - Test connectivity: `docker exec imageclient ping visionmodel`

5. **Container name conflicts**
   - Remove existing containers: `docker rm api-server visionmodel`
   - Use different names or restart: `docker-compose down && docker-compose up -d`

### Debug Commands

```bash
# Check container status
docker ps -a

# Check network
docker network inspect seniorprojtesting_my-network

# View container logs
docker logs api-server
docker logs visionmodel
docker logs imageclient

# Test API endpoints
curl -X GET http://localhost:8000/health
curl -X POST -F "video_file=@test.mp4" -F "userId=test" http://localhost:8000/api/analyze-video

# Test network connectivity
docker exec imageclient ping visionmodel

# Check if video file exists in container
docker run --rm -v $(pwd)/image_container/input:/app/input imageclient ls -la /app/input/

# Run container interactively for debugging
docker run -it --network seniorprojtesting_my-network -v $(pwd)/image_container/input:/app/input imageclient /bin/bash
```

### Quick Fixes

```bash
# Restart everything
docker-compose down && docker-compose up -d

# Rebuild containers
docker-compose build
docker-compose up -d

# Check system resources
docker system df
docker system prune  # Clean up unused resources
```

## Development

### Adding New Features

1. **API Server**: Modify `api_server.py` for new endpoints or processing logic
2. **Image Container**: Modify `image_client.py` for new processing logic
3. **Model Container**: Update `model_server.py` for new API endpoints
4. **Testing**: Use the API endpoints to verify changes

### Custom Model

To use a different YOLO model:
1. Replace `FinalModel.pt` with your model file
2. Update the model loading code in `main.py` if needed
3. Rebuild the model container: `docker-compose build visionmodel`

## File Structure

```
SeniorProjTesting/
├── api_server.py              # Backend API server
├── requirements.txt           # Python dependencies for API server
├── Dockerfile                 # API server container configuration
├── docker-compose.yml         # Multi-container orchestration
├── process_video.sh           # Legacy video processing script
├── test_model_direct.py       # Direct model testing script
├── test_pipeline.py           # Pipeline testing script
├── image_container/
│   ├── dockerfile
│   ├── image_client.py
│   ├── input/
│   │   ├── myvideo.mp4
│   │   └── floating-trash-and-ball-drift-on-polluted-river-surface-SBV-352831077-preview.mp4
│   └── *.jpg (test images)
├── model_container/
│   ├── dockerfile
│   ├── main.py
│   ├── model_server.py
│   └── FinalModel.pt
└── README.md
```
