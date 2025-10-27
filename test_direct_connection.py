#!/usr/bin/env python3
"""
Test script to verify the direct connection between frontend and backend.
This script tests the video analysis endpoint.
"""

import requests
import json
import os
import time

def test_server_health():
    """Test if the server is running and responsive"""
    try:
        response = requests.get("http://localhost:8001/health", timeout=5)
        if response.status_code == 200:
            print("✓ Server is running and healthy")
            return True
        else:
            print(f"✗ Server returned status {response.status_code}")
            return False
    except requests.exceptions.ConnectionError:
        print("✗ Server is not running or not accessible")
        print("  Make sure to run: ./start_server.sh")
        return False
    except Exception as e:
        print(f"✗ Error connecting to server: {e}")
        return False

def test_video_analysis():
    """Test video analysis with a sample video"""
    try:
        # Check if we have a test video
        test_video_path = "image_container/input/myvideo.mp4"
        if not os.path.exists(test_video_path):
            print(f"✗ Test video not found: {test_video_path}")
            print("  Please ensure you have a test video file")
            return False
        
        print(f"Testing video analysis with: {test_video_path}")
        
        # Prepare the multipart form data
        with open(test_video_path, 'rb') as video_file:
            files = {
                'video': ('test_video.mp4', video_file, 'video/mp4')
            }
            data = {
                'title': 'Test Analysis',
                'step_seconds': '1'
            }
            
            print("Sending video to analysis server...")
            response = requests.post(
                "http://localhost:8001/analyze-video",
                files=files,
                data=data,
                timeout=60  # Allow more time for processing
            )
        
        if response.status_code == 200:
            result = response.json()
            print("✓ Video analysis completed successfully!")
            print(f"  Title: {result.get('title', 'N/A')}")
            print(f"  Frames processed: {result.get('frames_processed', 'N/A')}")
            print(f"  Total garbage objects: {result.get('total_garbage_count', 'N/A')}")
            print(f"  Average per frame: {result.get('average_garbage_count', 'N/A'):.2f}")
            return True
        else:
            print(f"✗ Analysis failed with status {response.status_code}")
            print(f"  Response: {response.text}")
            return False
            
    except Exception as e:
        print(f"✗ Error testing video analysis: {e}")
        return False

def main():
    print("🧪 Testing Direct Frontend-Backend Connection")
    print("=" * 50)
    
    # Test 1: Check if server is running
    print("\n1. Testing server health...")
    if not test_server_health():
        print("\n❌ Connection test failed: Server not accessible")
        return
    
    # Test 2: Test video analysis
    print("\n2. Testing video analysis...")
    if not test_video_analysis():
        print("\n❌ Connection test failed: Video analysis failed")
        return
    
    print("\n✅ Direct connection test completed successfully!")
    print("   Your frontend can now connect directly to the backend.")
    print("   You can now test the full pipeline in your browser at:")
    print("   http://localhost:3000/videoFromStreams")

if __name__ == "__main__":
    main()
