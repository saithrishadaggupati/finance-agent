from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.routers import finance
from app.core.config import get_settings

settings = get_settings()

app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    debug=settings.debug
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(finance.router, prefix="/api/v1", tags=["finance"])


@app.get("/")
def health_check():
    return {
        "status": "running",
        "app": settings.app_name,
        "version": settings.app_version
    }