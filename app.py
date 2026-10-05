"""Local entry point: API and built React frontend share one origin."""
from backend.api import app

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)
