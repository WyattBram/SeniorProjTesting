# Video Analysis API

This project implements a complete video analysis system with a REST API that processes video frames through a YOLO model for garbage detection. Results are automatically saved to Firebase Firestore for persistent storage and retrieval.

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
                            │        ┌─────────────────┐
                            │        │   Firebase      │
                            └───────▶│   Firestore     │
                                     │                 │
                                     │ - Stores results│
                                     │ - Persists data │
                                     └─────────────────┘
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
- **Purpose**: REST API endpoint for video analysis with Firebase integration
- **Key Features**:
  - FastAPI-based HTTP server
  - Video upload handling (multipart/form-data)
  - Docker container orchestration using `docker cp` for file transfer
  - Automatic Firebase Firestore integration for result persistence
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

### Prerequisites

- Docker and Docker Compose installed
- Firebase service account key (`RiverGuardAccountKey.json`) in the project root
- Python 3.13+ (for local development)

### 1. Start All Services

```bash
# Navigate to the project directory
cd SeniorProjTesting

# Start the complete system (API server + model server)
docker-compose up -d
```

This will:
- Build and run the API server on port 8000 with Firebase integration
- Build and run the model server on port 8001
- Create a Docker network for inter-container communication
- Set up health checks and auto-restart
- Initialize Firebase Admin SDK for database operations

### 2. Test the API

#### **Using curl (Command Line)**
```bash
# Test health endpoint
curl -X GET http://localhost:8000/health

# Analyze a video (replace with your video path)
curl -X POST \
  -F "video_file=@/path/to/your/video.mp4" \
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

### 3. Monitor and Debug

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
    "video": "video.mp4",
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

#### **GET /health**
Health check endpoint.

**Response:**
```json
{
  "status": "healthy",
  "service": "video-analysis-api"
}
```

## How It Works

### Video Processing Pipeline

1. **Video Upload**: Client uploads video file via POST request with userId
2. **File Handling**: API server saves video to temporary location
3. **Container Execution**: API server creates temporary imageclient container
4. **File Transfer**: Video file is copied into container using `docker cp`
5. **Frame Extraction**: FFmpeg extracts frames at 1-second intervals
6. **ML Processing**: Each frame is sent to the model server for garbage detection
7. **Results Aggregation**: All frame results are collected and returned
8. **Firebase Storage**: Results are automatically saved to Firestore database
9. **Cleanup**: Temporary containers and files are removed

### Key Technical Details

- **File Transfer Method**: Uses `docker cp` instead of volume mounts to avoid Docker mounting issues
- **Container Management**: Creates temporary containers for each video processing request
- **Network Communication**: All containers communicate via Docker network `seniorprojtesting_my-network`
- **Frame Extraction**: FFmpeg extracts frames at configurable intervals (default: 1 second)
- **Firebase Integration**: Automatic result persistence to Firestore after successful analysis
- **Document Structure**: Each video analysis creates a document with userId as the document ID
- **Error Handling**: Comprehensive error handling and logging throughout the pipeline

## Configuration

### Environment Variables

The image container supports these environment variables:

- `INPUT_PATH`: Path to input video (set by API server)
- `USER_ID`: User identifier (set by API server)
- `WORKER_URL`: Model server URL (default: `http://visionmodel:8001/`)

### Firebase Configuration

Firebase integration requires:

- `RiverGuardAccountKey.json`: Firebase service account key (must be in project root)
- Firestore collection: `videos` (automatically created)
- Document structure:
  ```json
  {
    "userId": "user_id_string",
    "videoFilename": "original_filename.mp4",
    "uploadDate": "timestamp",
    "totalGarbageCount": 19,
    "framesProcessed": 16,
    "garbageCountPerFrame": [0, 0, 0, 1, 2, ...]
  }
  ```

### Docker Compose Services

- **api-server**: FastAPI server with Docker client capabilities and Firebase integration
- **visionmodel**: YOLO model server for garbage detection

## Troubleshooting

### Common Issues

1. **"Video file not found" Error**
   - **Solution**: This was resolved by switching from Docker volume mounts to `docker cp` file transfer
   - **Root Cause**: Docker was creating directories instead of mounting files
   - **Fix**: The current implementation uses `docker cp` to copy files into containers

2. **API server not accessible**
   - Check if containers are running: `docker ps`
   - Verify API server is running: `curl http://localhost:8000/health`
   - Check logs: `docker logs api-server`
   - Ensure port 8000 is exposed: `docker ps | grep 8000`

3. **Model server not accessible**
   - Check if containers are running: `docker ps`
   - Verify network: `docker network ls`
   - Check logs: `docker logs visionmodel`
   - Ensure port 8001 is exposed: `docker ps | grep 8001`

4. **Video processing fails**
   - Ensure input video exists and is accessible
   - Check file permissions
   - Verify FFmpeg is working: `docker exec imageclient ffmpeg -version`
   - Check container logs for specific error messages

5. **Network connectivity issues**
   - Ensure all containers are on the same network
   - Check container names match the URLs in the code
   - Test connectivity: `docker exec imageclient ping visionmodel`

6. **Firebase initialization errors**
   - Verify `RiverGuardAccountKey.json` exists in project root
   - Check Firebase credentials are valid
   - Ensure Firebase Admin SDK is installed: `pip list | grep firebase`
   - View logs: `docker-compose logs api-server | grep -i firebase`

### Debug Commands

```bash
# Check container status
docker ps -a

# Check network
docker network inspect seniorprojtesting_my-network

# View container logs
docker logs api-server
docker logs visionmodel

# Test API endpoints
curl -X GET http://localhost:8000/health
curl -X POST -F "video_file=@test.mp4" -F "userId=test" http://localhost:8000/api/analyze-video

# Test network connectivity
docker exec imageclient ping visionmodel

# Run container interactively for debugging
docker run -it --network seniorprojtesting_my-network imageclient /bin/bash
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
├── api_server.py              # Backend API server with Firebase integration
├── requirements.txt           # Python dependencies for API server (includes firebase-admin)
├── Dockerfile                 # API server container configuration
├── docker-compose.yml         # Multi-container orchestration
├── RiverGuardAccountKey.json  # Firebase service account key
├── image_container/
│   ├── dockerfile
│   ├── image_client.py
│   └── input/                 # Directory for test videos
├── model_container/
│   ├── dockerfile
│   ├── main.py
│   ├── model_server.py
│   └── FinalModel.pt
└── README.md
```

## Recent Updates

### Latest Features (Current Version)

- **✅ Firebase Integration**: Automatic result persistence to Firestore after video analysis
- **✅ Document-based Storage**: Results stored with userId as document ID for easy retrieval
- **✅ Clean Data Structure**: Only essential fields stored (userId, videoFilename, uploadDate, totalGarbageCount, framesProcessed, garbageCountPerFrame)
- **✅ Non-blocking Saves**: Firebase operations don't block API response to frontend

### Fixed Issues (Latest Version)

- **✅ Resolved "Video file not found" error**: Switched from Docker volume mounts to `docker cp` file transfer
- **✅ Fixed container orchestration**: API server now properly manages temporary containers
- **✅ Improved error handling**: Better logging and error reporting throughout the pipeline
- **✅ Streamlined architecture**: Simplified container management and file handling
- **✅ Added docker-compose support**: Proper Docker Compose integration for easy deployment

### Technical Improvements

- **Firebase Integration**: Seamless result persistence with comprehensive error handling
- **File Transfer**: Uses `docker cp` to copy video files into containers, avoiding volume mount issues
- **Container Management**: Creates temporary containers for each request and cleans them up automatically
- **Network Communication**: All containers communicate via Docker network for reliable connectivity
- **Error Handling**: Comprehensive error handling with detailed logging for debugging

## Performance Notes

- **Processing Time**: ~3-5 seconds for a 15-second video (16 frames)
- **Memory Usage**: Containers are created and destroyed per request to minimize resource usage
- **Scalability**: Each video processing request runs in isolation
- **File Size Limits**: Configured to handle videos up to 100MB (adjustable in `api_server.py`)

## Support

For issues or questions:
1. Check the troubleshooting section above
2. Review container logs for specific error messages
3. Ensure all services are running: `docker-compose ps`
4. Test the health endpoint: `curl http://localhost:8000/health`