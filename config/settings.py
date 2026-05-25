import os

# Load .env file manually if exists (keeps credentials out of git)
dotenv_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".env"))
if os.path.exists(dotenv_path):
    with open(dotenv_path, "r", encoding="utf-8") as f:
        for line in f:
            if line.strip() and not line.startswith("#") and "=" in line:
                key, val = line.strip().split("=", 1)
                os.environ[key.strip()] = val.strip()

# Google Gemini API Key configuration
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY", "")

# Server settings
API_HOST = "127.0.0.1"
API_PORT = 8000
API_URL = f"http://{API_HOST}:{API_PORT}"

# Logging settings
LOG_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "logs"))
AUDIT_LOG_FILE = os.path.join(LOG_DIR, "audit_execution.log")

# Create logs directory if it doesn't exist
os.makedirs(LOG_DIR, exist_ok=True)
