from __future__ import annotations

from fastapi import FastAPI

from app.api import router


app = FastAPI(title="Macau Shopping Decision API", version="0.1.0")
app.include_router(router)

