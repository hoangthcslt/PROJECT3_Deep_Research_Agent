"""
FastAPI application entrypoint.
Sets up CORS, REST routes, WebSocket endpoint, and startup/shutdown lifecycle.
"""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.api.routes.research import router as research_router
from app.api.routes.export import router as export_router
from app.api.websocket import router as ws_router
from app.services.qdrant_service import qdrant_service
from app.services.neo4j_service import neo4j_service

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown lifecycle events."""
    # ── Startup ──
    logger.info("🚀 Starting Deep Research Agent backend...")
    await qdrant_service.initialize()
    await neo4j_service.initialize()
    logger.info("✅ All services initialized successfully.")

    yield

    # ── Shutdown ──
    logger.info("🛑 Shutting down services...")
    await neo4j_service.close()
    logger.info("✅ Shutdown complete.")


app = FastAPI(
    title="Deep Research Agent API",
    description="AI-powered research assistant — Plan → Search → Read → Synthesize → Reflect",
    version="0.1.0",
    lifespan=lifespan,
)

# ── CORS Middleware ──
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Register Routers ──
app.include_router(research_router, prefix="/api/v1/research", tags=["Research"])
app.include_router(export_router, prefix="/api/v1/research", tags=["Export"])
app.include_router(ws_router, tags=["WebSocket"])


@app.get("/health", tags=["Health"])
async def health_check():
    """Health check endpoint for Docker / load balancer."""
    return {"status": "healthy", "service": "deep-research-agent"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host=settings.app_host,
        port=settings.app_port,
        reload=settings.is_development,
    )
