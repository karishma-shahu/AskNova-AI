
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError
from urllib.parse import urlparse
import json
import os


# Load API key from .env
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ENV_FILE = os.path.join(BASE_DIR, ".env")



def load_api_key():
    # Read the latest key from .env first
    try:
        with open(ENV_FILE, "r", encoding="utf-8-sig") as file:
            for line in file:
                line = line.strip()

                if not line or line.startswith("#") or "=" not in line:
                    continue

                key, value = line.split("=", 1)

                if key.strip() == "GEMINI_API_KEY":
                    value = value.strip().strip('"').strip("'")
                    if value:
                        return value

    except OSError:
        pass

    # Use system environment only if .env has no key
    return os.environ.get("GEMINI_API_KEY", "").strip()

GEMINI_API_KEY = load_api_key()

API_URL = "https://generativelanguage.googleapis.com/v1beta/interactions"
MODEL = "gemini-3.5-flash-lite"


class AskNovaHandler(BaseHTTPRequestHandler):

    # CORS headers
    def add_cors_headers(self):
        origin = self.headers.get("Origin", "")
        parsed_origin = urlparse(origin)

        if (
            parsed_origin.scheme == "http"
            and parsed_origin.hostname in ("localhost", "127.0.0.1")
        ):
            self.send_header("Access-Control-Allow-Origin", origin)
            self.send_header("Vary", "Origin")

        self.send_header(
            "Access-Control-Allow-Methods", "GET, POST, OPTIONS"
        )
        self.send_header(
            "Access-Control-Allow-Headers", "Content-Type"
        )
        self.send_header("Access-Control-Max-Age", "600")

    # Send JSON response
    def send_json(self, data, status=200):
        response = json.dumps(data).encode("utf-8")

        self.send_response(status)
        self.send_header(
            "Content-Type", "application/json; charset=utf-8"
        )
        self.send_header("Content-Length", str(len(response)))

        self.add_cors_headers()

        self.end_headers()
        self.wfile.write(response)

    # Browser preflight
    def do_OPTIONS(self):
        self.send_response(204)
        self.add_cors_headers()
        self.end_headers()

    # Health check
    def do_GET(self):
        path = self.path.split("?")[0]

        if path == "/":
            self.send_json({
                "message": "Welcome to AskNova AI Backend"
            })

        elif path == "/health":
            self.send_json({
                "status": "ok"
            })

        else:
            self.send_json({
                "error": "Not found"
            }, 404)

    # Gemini chat
    def do_POST(self):

        if self.path.split("?")[0] != "/chat":
            self.send_json({"error": "Not found"}, 404)
            return

        try:
            length = int(self.headers.get("Content-Length", 0))
            data = json.loads(self.rfile.read(length))

            message = data.get("message", "")

            if not isinstance(message, str):
                message = ""

            message = message.strip()

            if not message:
                self.send_json({
                    "error": "Message is required"
                }, 400)
                return

            if not GEMINI_API_KEY:
                self.send_json({
                    "error": "API key not found in backend/.env"
                }, 500)
                return

            # Prepare Gemini request
            payload = json.dumps({
                "model": MODEL,
                "input": message
            }).encode("utf-8")

            request = Request(
    API_URL,
    data=payload,
    headers={
        "Content-Type": "application/json",
        "x-goog-api-key": GEMINI_API_KEY,
        "Api-Revision": "2026-05-20"
    },
    method="POST"
)
            # Send request to Gemini
            with urlopen(request, timeout=60) as response:
                result = json.loads(
                    response.read().decode("utf-8")
                )

            # Extract Gemini answer safely
            reply_parts = []

            if isinstance(result, dict):
                for step in result.get("steps", []):
                    if not isinstance(step, dict):
                        continue

                    if step.get("type") == "model_output":
                        for part in step.get("content", []):
                            if (
                                isinstance(part, dict)
                                and part.get("type") == "text"
                            ):
                                reply_parts.append(
                                    part.get("text", "")
                                )

            reply = "\n".join(reply_parts).strip()

            if not reply:
                self.send_json({
                    "error": "Gemini returned an empty response."
                }, 502)
                return

            self.send_json({
                "reply": reply
            })

        # Handle Gemini API errors
        except HTTPError as error:

            raw_error = error.read().decode(
                "utf-8", errors="replace"
            )

            try:
                error_data = json.loads(raw_error)
            except json.JSONDecodeError:
                error_data = raw_error

            # Handle dictionary response
            if isinstance(error_data, dict):

                api_error = error_data.get("error", error_data)

                if isinstance(api_error, dict):
                    detail = api_error.get(
                        "message",
                        json.dumps(api_error, ensure_ascii=False)
                    )
                else:
                    detail = str(api_error)

            # Handle list response
            elif isinstance(error_data, list):
                detail = json.dumps(
                    error_data, ensure_ascii=False
                )

            else:
                detail = str(error_data)

            print(
                f"Gemini API error ({error.code}): {detail}"
            )

            self.send_json({
                "error": f"Gemini API error ({error.code}): {detail}"
            }, 502)

        # Internet connection error
        except URLError as error:

            print("Connection error:", repr(error))

            self.send_json({
                "error": "Google Gemini connection failed. Check internet."
            }, 502)

        # JSON error
        except json.JSONDecodeError as error:

            print("JSON error:", repr(error))

            self.send_json({
                "error": "Invalid JSON request or response."
            }, 400)

        # Other backend errors
        except Exception as error:

            print("Unexpected server error:", repr(error))

            self.send_json({
                "error": "Backend error. Check the backend terminal."
            }, 500)


# Start backend
print("Gemini API key loaded:", bool(GEMINI_API_KEY))

server = HTTPServer(
    ("127.0.0.1", 8000),
    AskNovaHandler
)

print("AskNova AI Backend running at http://127.0.0.1:8000")

server.serve_forever()
