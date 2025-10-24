# Data Pipeline Setup

This project implements a data pipeline that processes video frames through a YOLO model for garbage detection.

## Architecture

```
┌─────────────────┐    ┌─────────────────┐
│  Image Container │    │  Model Container │
│                 │    │                 │
│ - Extracts      │───▶│ - Receives      │
│   frames from    │    │   images        │
│   video         │    │ - Runs YOLO     │
│ - Sends to      │    │   prediction    │
│   model         │    │ - Returns count │
└─────────────────┘    └─────────────────┘
```

## Components

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

### 1. Build and Run Containers

```bash
# Make the script executable
chmod +x create_container.sh

# Build and run both containers
./create_container.sh
```

This will:
- Create a Docker network called `my-network`
- Build and run the model container on port 8001
- Build and run the image container with input volume mounted

### 2. Test the Complete Pipeline

The image container is designed as a one-time job that processes your video and exits. Here's how to test it:

#### **Basic Video Processing Test**
```bash
# Process the video in image_container/input/myvideo.mp4
docker run --network my-network --name imageclient-test -v $(pwd)/image_container/input:/app/input imageclient
```

#### **Test with Different Parameters**
```bash
# Process video with 2-second intervals instead of 1-second
docker run --network my-network -e STEP=2 -v $(pwd)/image_container/input:/app/input imageclient

# Process only first 5 frames
docker run --network my-network -e MAX_FRAMES=5 -v $(pwd)/image_container/input:/app/input imageclient

# Process with custom video path
docker run --network my-network -e INPUT_PATH=/app/input/myvideo.mp4 -v $(pwd)/image_container/input:/app/input imageclient
```

#### **Test Model Server Directly**
```bash
# Check if model server is running
docker ps | grep visionmodel

# Test with a single image using curl
curl -X POST http://localhost:8001/ \
  -H "Content-Type: application/json" \
  -d '{"image_data":"'$(base64 -i image_container/ab.jpg)'", "filename":"test.jpg"}'
```

### 3. Monitor and Debug

#### **View Logs**
```bash
# Check model server logs
docker logs visionmodel

# Check image container logs (after running it)
docker logs imageclient-test
```

#### **System Status**
```bash
# See all running containers
docker ps

# See all containers (including stopped ones)
docker ps -a

# Check Docker network
docker network ls
docker network inspect my-network
```

#### **Clean Up**
```bash
# Remove test containers
docker rm imageclient-test

# Stop and restart model server if needed
docker restart visionmodel

# Stop all containers
docker stop $(docker ps -q)
```

### 4. Expected Output

When you run the pipeline, you should see output like this:

```
Extracting frames every 1s from '/app/input/myvideo.mp4' and sending to http://visionmodel:8001/
Sending frame 1/10 -> frame_00001.jpg
Sending frame 2/10 -> frame_00002.jpg
...
{
  "ok": true,
  "video": "myvideo.mp4",
  "step_seconds": 1.0,
  "frames_sent": 10,
  "responses": [
    {
      "frame": "frame_00001.jpg",
      "response": {
        "garbage_count": 5,
        "filename": "frame_00001.jpg",
        "message": "Image processed successfully"
      }
    },
    ...
  ]
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

## API Endpoints

### Model Server (`http://localhost:8001/`)

**POST /** - Process an image
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

## Logging

Both containers include comprehensive logging:

- **Image Container**: Logs frame extraction, encoding, and network communication
- **Model Container**: Logs image reception, prediction results, and errors

View logs:
```bash
# View model container logs
docker logs visionmodel

# View image container logs
docker logs imageclient
```

## Troubleshooting

### Common Issues

1. **Model server not accessible**
   - Check if containers are running: `docker ps`
   - Verify network: `docker network ls`
   - Check logs: `docker logs visionmodel`
   - Ensure port 8001 is exposed: `docker ps | grep 8001`

2. **Image processing fails**
   - Ensure input video exists in `image_container/input/`
   - Check file permissions
   - Verify FFmpeg is working: `docker exec imageclient ffmpeg -version`
   - Check video path in container: `docker run --rm -v $(pwd)/image_container/input:/app/input imageclient ls -la /app/input/`

3. **Network connectivity issues**
   - Ensure both containers are on the same network
   - Check container names match the URLs in the code
   - Test connectivity: `docker exec imageclient ping visionmodel`

4. **Container name conflicts**
   - Remove existing containers: `docker rm imageclient-test`
   - Use different names: `docker run --name my-test-container ...`

### Debug Commands

```bash
# Check container status
docker ps -a

# Check network
docker network inspect my-network

# View container logs
docker logs visionmodel
docker logs imageclient

# Test network connectivity
docker exec imageclient ping visionmodel

# Test model server directly
curl -X GET http://localhost:8001/

# Check if video file exists in container
docker run --rm -v $(pwd)/image_container/input:/app/input imageclient ls -la /app/input/

# Run container interactively for debugging
docker run -it --network my-network -v $(pwd)/image_container/input:/app/input imageclient /bin/bash
```

### Quick Fixes

```bash
# Restart everything
docker stop $(docker ps -q) && docker rm $(docker ps -aq)
./create_container.sh

# Rebuild containers
docker build -t visionmodel model_container/
docker build -t imageclient image_container/

# Check system resources
docker system df
docker system prune  # Clean up unused resources
```

## Development

### Adding New Features

1. **Image Container**: Modify `image_client.py` for new processing logic
2. **Model Container**: Update `model_server.py` for new API endpoints
3. **Testing**: Use `test_pipeline.py` to verify changes

### Custom Model

To use a different YOLO model:
1. Replace `FinalModel.pt` with your model file
2. Update the model loading code in `main.py` if needed
3. Rebuild the model container

## File Structure

```
SeniorProjTesting/
├── image_container/
│   ├── dockerfile
│   ├── image_client.py
│   ├── input/
│   │   └── myvideo.mp4
│   └── *.jpg (test images)
├── model_container/
│   ├── dockerfile
│   ├── main.py
│   ├── model_server.py
│   └── FinalModel.pt
├── create_container.sh
├── setup-network.sh
├── test_pipeline.py
└── README.md
```
