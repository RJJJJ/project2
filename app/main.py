from __future__ import annotations

import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import router


app = FastAPI(title="Macau Shopping Decision API", version="0.1.0")

default_origins = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
]
allowed_origins = [
    origin.strip()
    for origin in os.getenv("ALLOWED_ORIGINS", ",".join(default_origins)).split(",")
    if origin.strip()
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router)
