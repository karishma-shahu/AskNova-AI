
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError
from urllib.parse import urlparse
import json
import os


# Project paths
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ENV_FILE = os.path.join(BASE_DIR, ".env")


# Load Gemini API key
def load_api_key():

    # First read local .env file
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

    # Render environment variable
    return os.environ.get("GEMINI_API_KEY", "").strip()


GEMINI_API_KEY = load_api_key()

# Gemini API settings
API_URL = "https://generativelanguage.googleapis.com/v1beta/interactions"
MODEL = "gemini-3.5-flash-lite"

# Render frontend URL (add in Render environment settings)
FRONTEND_ORIGIN = os.environ.get(
    "FRONTEND_ORIGIN", ""
).strip().rstrip("/")


class AskNovaHandler(BaseHTTPRequestHandler):

    # CORS configuration
    def add_cors_headers(self):

        origin = self.headers.get("Origin", "")
        parsed_origin = urlparse(origin)

        # Allow local development
        is_local = (
            parsed_origin.scheme == "http"
            and parsed_origin.hostname in ("localhost", "127.0.0.1")
        )

        # Allow deployed frontend
        is_deployed = (
            bool(FRONTEND_ORIGIN)
            and origin == FRONTEND_ORIGIN
        )

        if is_local or is_deployed:
            self.send_header(
                "Access-Control-Allow-Origin", origin
            )
            self.send_header("Vary", "Origin")

        self.send_header(
            "Access-Control-Allow-Methods", "GET, POST, OPTIONS"
        )
        self.send_header(
            "Access-Control-Allow-Headers", "Content-Type"
        )
        self.send_header("Access-Control-Max-Age", "600")

    # JSON response
    def send_json(self, data, status=200):

        response = json.dumps(data).encode("utf-8")

        self.send_response(status)

        self.send_header(
            "Content-Type", "application/json; charset=utf-8"
        )
        self.send_header(
            "Content-Length", str(len(response))
        )

        self.add_cors_headers()

        self.end_headers()
        self.wfile.write(response)

    # Handle browser preflight
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

    # Chat endpoint
    def do_POST(self):

        if self.path.split("?")[0] != "/chat":

            self.send_json({
                "error": "Not found"
            }, 404)

            return

        try:

            length = int(
                self.headers.get("Content-Length", 0)
            )

            data = json.loads(
                self.rfile.read(length)
            )

            if not isinstance(data, dict):

                self.send_json({
                    "error": "Invalid request format"
                }, 400)

                return

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
                    "error": "Gemini API key not configured"
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

            # Call Gemini API
            with urlopen(request, timeout=60) as response:

                result = json.loads(
                    response.read().decode("utf-8")
                )

            # Extract AI response
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
                    "error": "Gemini returned an empty response"
                }, 502)

                return

            self.send_json({
                "reply": reply
            })

        # Gemini API error
        except HTTPError as error:

            raw_error = error.read().decode(
                "utf-8", errors="replace"
            )

            try:
                error_data = json.loads(raw_error)

            except json.JSONDecodeError:
                error_data = raw_error

            if isinstance(error_data, dict):

                api_error = error_data.get(
                    "error", error_data
                )

                if isinstance(api_error, dict):

                    detail = api_error.get(
                        "message",
                        json.dumps(api_error)
                    )

                else:
                    detail = str(api_error)

            elif isinstance(error_data, list):

                detail = json.dumps(
                    error_data,
                    ensure_ascii=False
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
                "error": "Unable to connect to Google Gemini"
            }, 502)

        # JSON error
        except json.JSONDecodeError as error:

            print("JSON error:", repr(error))

            self.send_json({
                "error": "Invalid JSON request or response"
            }, 400)

        # Other backend errors
        except Exception as error:

            print("Unexpected server error:", repr(error))

            self.send_json({
                "error": "Unexpected backend error"
            }, 500)


# Render port configuration
PORT = int(os.environ.get("PORT", "8000"))

# Start backend server
print(
    "Gemini API key loaded:",
    bool(GEMINI_API_KEY)
)

server = HTTPServer(
    ("0.0.0.0", PORT),
    AskNovaHandler
)

print(
    f"AskNova AI Backend running on port {PORT}"
)

server.serve_forever()
