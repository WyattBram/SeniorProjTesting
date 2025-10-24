#!/usr/bin/env python3
"""
Test script to verify the data pipeline between image and model containers.
This script can be run from the host to test the complete pipeline.
"""

import requests
import base64
import json
import os
import time

def test_model_server():
    """Test if the model server is running and responsive"""
    try:
        # Test basic connectivity
        response = requests.get("http://localhost:8001/", timeout=5)
        print(f"✓ Model server is running (status: {response.status_code})")
        return True
    except requests.exceptions.ConnectionError:
        print("✗ Model server is not running or not accessible")
        return False
    except Exception as e:
        print(f"✗ Error connecting to model server: {e}")
        return False

def test_image_upload():
    """Test sending an image to the model server"""
    try:
        # Use one of the test images
        image_path = "image_container/ab.jpg"
        if not os.path.exists(image_path):
            print(f"✗ Test image not found: {image_path}")
            return False
        
        # Read and encode image
        with open(image_path, "rb") as f:
            image_data = base64.b64encode(f.read()).decode('utf-8')
        
        # Send to model server
        payload = {
            "image_data": image_data,
            "filename": "test_image.jpg"
        }
        
        print("Sending test image to model server...")
        response = requests.post(
            "http://localhost:8001/",
            json=payload,
            headers={"Content-Type": "application/json"},
            timeout=30
        )
        
        if response.status_code == 200:
            result = response.json()
            print(f"✓ Image processed successfully!")
            print(f"  Garbage count: {result.get('garbage_count', 'N/A')}")
            print(f"  Filename: {result.get('filename', 'N/A')}")
            print(f"  Message: {result.get('message', 'N/A')}")
            return True
        else:
            print(f"✗ Model server returned error: {response.status_code}")
            print(f"  Response: {response.text}")
            return False
            
    except Exception as e:
        print(f"✗ Error testing image upload: {e}")
        return False

def main():
    print("🧪 Testing Data Pipeline")
    print("=" * 50)
    
    # Test 1: Check if model server is running
    print("\n1. Testing model server connectivity...")
    if not test_model_server():
        print("\n❌ Pipeline test failed: Model server not accessible")
        print("   Make sure to run: ./create_container.sh")
        return
    
    # Test 2: Test image upload and processing
    print("\n2. Testing image upload and processing...")
    if not test_image_upload():
        print("\n❌ Pipeline test failed: Image processing failed")
        return
    
    print("\n✅ Pipeline test completed successfully!")
    print("   Your data pipeline is working correctly.")

if __name__ == "__main__":
    main()
