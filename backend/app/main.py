from pathlib import Path
from importlib.util import find_spec
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from .config import settings
from .database import init_db
from .api import auth, billing, charts, geo

BASE = Path(__file__).resolve().parents[2]
FRONTEND_DIR = BASE / "frontend"


def create_app() -> FastAPI:
    if settings.is_production:
        if settings.secret_key == "development-only-change-me" or len(settings.secret_key) < 32:
            raise RuntimeError("ASTRA_SECRET_KEY must be a unique random secret of at least 32 characters in production")
        if settings.database_url.startswith("sqlite"):
            raise RuntimeError("Use PostgreSQL or another supported production database; SQLite is development-only")
        if settings.geocoder_provider.lower() == "nominatim":
            raise RuntimeError("The public Nominatim endpoint is not an approved production geocoder. Configure a commercial provider or self-hosted service.")
    @asynccontextmanager
    async def lifespan(app: FastAPI):
        init_db()
        yield

    app = FastAPI(
        title="ASTRA OS API",
        version="0.1.1",
        description="Deterministic astronomical chart calculations with auditable astrology conventions.",
        lifespan=lifespan,
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[settings.frontend_origin],
        allow_credentials=True,
        allow_methods=["GET", "POST", "DELETE"],
        allow_headers=["Authorization", "Content-Type", "Stripe-Signature"],
    )
    app.include_router(auth.router)
    app.include_router(charts.router)
    app.include_router(geo.router)
    app.include_router(billing.router)

    @app.get("/api/health")
    def health():
        return {"status": "ok", "service": "astra-os", "version": "0.1.1"}

    @app.get("/api/ready")
    def readiness():
        ephemeris_path = Path(settings.ephemeris_dir) / settings.ephemeris_file
        checks = {
            "skyfield_installed": find_spec("skyfield") is not None,
            "ephemeris_file_present": ephemeris_path.is_file(),
            "timezonefinder_installed": find_spec("timezonefinder") is not None,
        }
        ready = all(checks.values())
        body = {"status": "ready" if ready else "degraded", "checks": checks}
        return body if ready else JSONResponse(status_code=503, content=body)

    @app.get("/api/meta")
    def meta():
        return {
            "name": "ASTRA OS",
            "version": "0.1.1",
            "systems": ["vedic", "western", "kp", "jaimini"],
            "locales": ["en", "hi", "gu"],
            "ephemeris": settings.ephemeris_file,
            "geocoder_provider": settings.geocoder_provider.lower(),
        }

    if FRONTEND_DIR.exists():
        app.mount("/", StaticFiles(directory=str(FRONTEND_DIR), html=True), name="frontend")
    return app


app = create_app()
