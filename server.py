from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from main import predict


class SimpleHandler(BaseHTTPRequestHandler):
    def do_POST(self):
        content_length_header = self.headers.get("Content-Length")
        length = int(content_length_header or 0)
        raw_body = self.rfile.read(length) if length > 0 else b""

        # Try to parse JSON if content-type indicates JSON; otherwise echo raw
        content_type = self.headers.get("Content-Type", "").lower()
        if "application/json" in content_type:
            try:
                import json

                payload = json.loads(raw_body.decode("utf-8") or "null")
                response_bytes = json.dumps({"received": payload}).encode("utf-8")

                print(f"Will create a container with stream: {payload['Stream']}")
                self.send_response(200)
                self.send_header("Content-Type", "application/json; charset=utf-8")

                try:
                    if payload["Stream"] == "abc":
                        amt = predict("abc.jpg")
                        response_bytes = json.dumps({"garbage_count": amt}).encode("utf-8")
                    else:
                        amt = predict("ab.jpg")
                        response_bytes = json.dumps({"garbage_count": amt}).encode("utf-8")
                except Exception as e:
                    print(f"Prediction failed: {e}")
                    response_bytes = json.dumps({"error": str(e)}).encode("utf-8")

                self.send_header("Content-Length", str(len(response_bytes)))
                self.end_headers()
                self.wfile.write(response_bytes)
                return
            except Exception:
                # Malformed JSON
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
        return  # Silence default logging for simplicity


def run(host: str = "127.0.0.1", port: int = 8001) -> None:
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


