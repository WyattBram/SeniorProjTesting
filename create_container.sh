#!/bin/bash

# Create network if it doesn't exist
if ! docker network ls | grep -q "my-network"; then
    echo "Creating my-network..."
    docker network create my-network
fi

# Build and run model container
echo "Building model container..."
cd model_container
docker build -t visionmodel .
docker run -d --network my-network --name visionmodel -p 8001:8001 visionmodel

# Build and run image container  
echo "Building image container..."
cd ../image_container
docker build -t imageclient .
docker run -d --network my-network --name imageclient -v $(pwd)/input:/app/input imageclient

echo "Containers created and connected to my-network!"
echo "Model server running on http://localhost:8001"