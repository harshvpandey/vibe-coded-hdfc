import uvicorn
import os
import sys
from config import settings

def main():
    print("=" * 60)
    print("      HDFC AI MAILROOM HUB - SERVICE STARTUP ENGINE")
    print("=" * 60)
    print(f"Server Host URL: {settings.API_URL}")
    print(f"Local Workspace: {os.path.abspath(os.getcwd())}")
    print(f"Gemini API Configured: {'YES' if settings.GOOGLE_API_KEY else 'NO'}")
    print("=" * 60)
    print("Starting background service. Open http://localhost:8000 in your browser.")
    print("Press Ctrl+C to terminate the application.")
    print("-" * 60)
    
    # Run FastAPI via Uvicorn
    # reload=True is useful for development, but reload=False is highly recommended
    # when embedding static frontends to prevent double-initialization of LLM threads.
    uvicorn.run(
        "apis.app:app",
        host=settings.API_HOST,
        port=settings.API_PORT,
        reload=False,
        log_level="info"
    )

if __name__ == "__main__":
    main()
