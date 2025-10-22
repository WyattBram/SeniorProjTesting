import json
import urllib.request
import time
import base64

# Dracula: "I have more percs than there are stars in the leo cluster"

def send_json(url: str = "http://visionmodel:8001/", data: dict | None = None) -> str:
    body = json.dumps(data or {}).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=body,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req) as response:
        return response.read().decode("utf-8")


def send_image(url: str = "http://visionmodel:8001/", image_path: str = "") -> str:
    """Send an image file to the server"""
    try:
        # Read and encode image as base64
        with open(image_path, "rb") as f:
            image_data = base64.b64encode(f.read()).decode('utf-8')
        
        # Send as JSON
        data = {
            "image_data": image_data,
            "filename": image_path
        }
        return send_json(url, data)
    except Exception as e:
        return json.dumps({"error": str(e)})

if __name__ == "__main__":
    print("Sending image...")
    result = send_image(image_path="abc.jpg")
    print("Result:", result)




