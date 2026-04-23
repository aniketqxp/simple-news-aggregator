import uvicorn
import os
from dotenv import load_dotenv

# Load environment variables from .env if present
load_dotenv()

from src.main import app

if __name__ == "__main__":
    # Get port from environment or default to 8000
    port = int(os.getenv("PORT", 8000))
    host = os.getenv("HOST", "127.0.0.1")
    
    uvicorn.run(
        "src.main:app",
        host=host,
        port=port,
        reload=True
    )
