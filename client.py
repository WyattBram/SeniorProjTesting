import json
import urllib.request

def send_json(url: str = "http://127.0.0.1:8001/", data: dict | None = None) -> str:
    body = json.dumps(data or {}).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=body,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req) as response:
        return response.read().decode("utf-8")


if __name__ == "__main__":
    print(send_json(data={"Stream": "abc"}))
    print(send_json(data={"Stream": "ab"}))


