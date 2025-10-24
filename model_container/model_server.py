from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from main import predict
import base64
import tempfile
import os
import json
import logging

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class SimpleHandler(BaseHTTPRequestHandler):
    def do_POST(self):
        content_length_header = self.headers.get("Content-Length")
        length = int(content_length_header or 0)
        raw_body = self.rfile.read(length) if length > 0 else b""


        content_type = self.headers.get("Content-Type", "").lower()
        if "application/json" in content_type:
            try:
                import json

                payload = json.loads(raw_body.decode("utf-8") or "null")
                response_bytes = json.dumps({"received": payload}).encode("utf-8")

                self.send_response(200)
                self.send_header("Content-Type", "application/json; charset=utf-8")

                try:
                    # Check if this is an image upload
                    if "image_data" in payload:
                        filename = payload.get('filename', 'unknown')
                        logger.info(f"Received image: {filename}")
                        
                        # Decode base64 image data
                        try:
                            image_data = base64.b64decode(payload["image_data"])
                            logger.info(f"Successfully decoded image data ({len(image_data)} bytes)")
                        except Exception as e:
                            logger.error(f"Failed to decode base64 image data: {e}")
                            response_bytes = json.dumps({"error": f"Invalid image data: {str(e)}"}).encode("utf-8")
                            self.send_response(400)
                            self.send_header("Content-Type", "application/json; charset=utf-8")
                            self.send_header("Content-Length", str(len(response_bytes)))
                            self.end_headers()
                            self.wfile.write(response_bytes)
                            return
                        
                        # Save to temporary file
                        temp_path = None
                        try:
                            with tempfile.NamedTemporaryFile(delete=False, suffix=".jpg") as temp_file:
                                temp_file.write(image_data)
                                temp_path = temp_file.name
                            logger.info(f"Saved image to temporary file: {temp_path}")
                        except Exception as e:
                            logger.error(f"Failed to save temporary file: {e}")
                            response_bytes = json.dumps({"error": f"Failed to save image: {str(e)}"}).encode("utf-8")
                            self.send_response(500)
                            self.send_header("Content-Type", "application/json; charset=utf-8")
                            self.send_header("Content-Length", str(len(response_bytes)))
                            self.end_headers()
                            self.wfile.write(response_bytes)
                            return
                        
                        # Run prediction on the uploaded image
                        try:
                            logger.info(f"Running prediction on {filename}")
                            amt = predict(temp_path)
                            logger.info(f"Prediction completed: {amt} objects detected")
                            
                            response_bytes = json.dumps({
                                "garbage_count": amt,
                                "filename": filename,
                                "message": "Image processed successfully"
                            }).encode("utf-8")
                        except Exception as e:
                            logger.error(f"Prediction failed for {filename}: {e}")
                            response_bytes = json.dumps({
                                "error": f"Prediction failed: {str(e)}",
                                "filename": filename
                            }).encode("utf-8")
                        finally:
                            # Clean up temporary file
                            if temp_path and os.path.exists(temp_path):
                                try:
                                    os.unlink(temp_path)
                                    logger.info(f"Cleaned up temporary file: {temp_path}")
                                except Exception as e:
                                    logger.warning(f"Failed to clean up temporary file {temp_path}: {e}")
                    else:
                        logger.warning("Received request without image_data")
                        response_bytes = json.dumps({"error": "No image data found in request"}).encode("utf-8")
                        
                except Exception as e:
                    logger.error(f"Unexpected error processing request: {e}")
                    response_bytes = json.dumps({"error": f"Internal server error: {str(e)}"}).encode("utf-8")

                self.send_header("Content-Length", str(len(response_bytes)))
                self.end_headers()
                self.wfile.write(response_bytes)
                return
            except Exception:
                # Bad json
                error_bytes = b'{"error":"invalid json"}'
                self.send_response(400)
                self.send_header("Content-Type", "application/json; charset=utf-8")
                self.send_header("Content-Length", str(len(error_bytes)))
                self.end_headers()
                self.wfile.write(error_bytes)
                return

        # Fallback: echo raw body as text
        self.send_response(200)
        self.send_header("Content-Type", "text/plain; charset=utf-8")
        self.send_header("Content-Length", str(len(raw_body)))
        self.end_headers()
        self.wfile.write(raw_body)

    def log_message(self, format, *args):
        return  


def run(host: str = "0.0.0.0", port: int = 8001) -> None:
    server = ThreadingHTTPServer((host, port), SimpleHandler)
    print(f"Serving on http://{host}:{port}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
        print("Server stopped.")


if __name__ == "__main__":
    run()


