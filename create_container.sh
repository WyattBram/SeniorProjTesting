#!/bin/bash

echo "Creating container $1"
docker build -t $1 .
docker run -network my-network  --name $1 $1