import uvicorn

from .logging_config import setup_logging

setup_logging()

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, log_config=None)
