#!/bin/bash

echo "Creating container $1"
cd image_container
docker build -t $1 .
docker run -network my-network  --name $1 $1