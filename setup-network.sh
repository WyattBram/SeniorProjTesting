#!/bin/bash

# Might be needed idk will see later

# Check if my-network exists, create if it doesn't
if ! docker network ls | grep -q "my-network"; then
    echo "Creating my-network..."
    docker network create my-network
else
    echo "my-network already exists"
fi

# Check if visionmodel container exists and connect it to the network
if docker ps | grep -q "visionmodel"; then
    echo "Connecting visionmodel to my-network..."
    docker network connect my-network visionmodel 2>/dev/null || echo "visionmodel already connected to my-network"
else
    echo "visionmodel container not running"
fi

echo "Network setup complete!"

