"""FastAPI example application for ChewyAttachment"""

import os
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

from chewy_attachment.fastapi_app import dependencies, router

BASE_DIR = Path(__file__).resolve().parent
DATABASE_URL = f"sqlite:///{BASE_DIR}/attachments.db"
STORAGE_ROOT = BASE_DIR / "media" / "attachments"

# Optional: Set custom table name via environment variable
# os.environ["CHEWY_ATTACHMENT_TABLE_NAME"] = "my_custom_attachments"

dependencies.configure(DATABASE_URL, STORAGE_ROOT)

app = FastAPI(
    title="ChewyAttachment Example",
    description="Example FastAPI application using ChewyAttachment",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def add_demo_user(request: Request, call_next):
    """
    Demo middleware that sets a fake user ID.

    In production, replace this with your actual authentication middleware.
    """
    request.state.user_id = "demo-user-123"
    response = await call_next(request)
    return response


app.include_router(router, prefix="/api/attachments")


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": "ChewyAttachment FastAPI Example",
        "docs": "/docs",
        "api_prefix": "/api/attachments",
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
