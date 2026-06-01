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

# Ollama Local Llama configuration
OLLAMA_API_URL = os.getenv("OLLAMA_API_URL", "http://localhost:11434/api/chat")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3")

# Gmail credentials & network servers
GMAIL_EMAIL = os.getenv("GMAIL_EMAIL", "")
GMAIL_APP_PASSWORD = os.getenv("GMAIL_APP_PASSWORD", "")
GMAIL_IMAP_SERVER = "imap.gmail.com"
GMAIL_SMTP_SERVER = "smtp.gmail.com"
GMAIL_SMTP_PORT = 587
GMAIL_IMAP_PORT = 993
AUTO_SEND_THRESHOLD = 0.95
GMAIL_SYNC_FILTER_KEYWORD = "HDFC"
DATABASE_URL = "sqlite:///hdfc_mailroom.db"

# Server settings
API_HOST = "127.0.0.1"
API_PORT = 8000
API_URL = f"http://{API_HOST}:{API_PORT}"

# Logging settings
LOG_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "logs"))
AUDIT_LOG_FILE = os.path.join(LOG_DIR, "audit_execution.log")

# Create logs directory if it doesn't exist
os.makedirs(LOG_DIR, exist_ok=True)
