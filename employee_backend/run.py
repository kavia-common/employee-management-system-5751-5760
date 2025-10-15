"""
Uvicorn launcher for the Employee Backend.

Purpose:
- Ensure the FastAPI application (src.api.main:app) is started with the expected host/port
  for the preview environment (0.0.0.0:3001).
- Keep configuration minimal and environment-driven without hardcoding secrets.

Usage:
  python run.py
  (or) python -m uvicorn src.api.main:app --host 0.0.0.0 --port 3001

Security:
- No secrets are hardcoded here.
- For production deployments, prefer process managers and environment configuration.

"""
from __future__ import annotations

import os

import uvicorn


def main() -> None:
    """
    Entrypoint for launching the FastAPI server with uvicorn.
    """
    # PUBLIC_INTERFACE
    # Allow overriding via env but default to preview expectations
    host = os.getenv("HOST", "0.0.0.0")
    port = int(os.getenv("PORT", "3001"))
    # Use the full application with DB/auth, not the stub
    uvicorn.run("src.api.main:app", host=host, port=port, reload=False)


if __name__ == "__main__":
    main()
