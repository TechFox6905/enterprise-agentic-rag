# ============================================================
# CRITICAL: logfire MUST be configured before ALL other imports
# so that spans from all modules are captured from the start.
# ============================================================
import logfire

from app.config import settings

# Logfire v2 EU tokens start with "pylf_v2_eu_" and must send spans to the
# EU endpoint. If no base URL is configured, infer it from the token prefix
# so the same .env works locally and inside Docker without manual overrides.
_logfire_base_url = settings.LOGFIRE_BASE_URL
if not _logfire_base_url and settings.LOGFIRE_TOKEN:
    if settings.LOGFIRE_TOKEN.startswith("pylf_v2_eu_"):
        _logfire_base_url = "https://logfire-eu.pydantic.dev"

logfire.configure(
    token=settings.LOGFIRE_TOKEN,
    advanced=logfire.AdvancedOptions(base_url=_logfire_base_url) if _logfire_base_url else None,
)

# Now safe to import app modules - logfire is already active
from contextlib import asynccontextmanager
from fastapi import Depends, FastAPI, Response
from prometheus_fastapi_instrumentator import Instrumentator

from app.agents.graph import build_graph
from app.guardrails import initialize_rails
from app.api.auth import verify_api_key
from app.api.rate_limit import _init_rate_limiter
from app.api.routers.health import router as health_router
from app.services.health.connection_checker import check_all_connections, log_connection_summary


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Initialize all application resources during startup and
    release them cleanly during shutdown.
    """

    initialize_rails()

    # Build the production LangGraph instance.
    app.state.rag_agent = build_graph()

    # Configure Redis/in-memory rate limiter.
    app.state.rate_limiter_enabled = _init_rate_limiter()

    # Verify external services.
    connection_results = check_all_connections()
    all_healthy = log_connection_summary(connection_results)

    if settings.STRICT_STARTUP and not all_healthy:
        failed = [
            name
            for name, result in connection_results.items()
            if not result.healthy
        ]
        raise RuntimeError(
            f"STRICT_STARTUP enabled; failing services: {', '.join(failed)}"
        )

    if not settings.API_KEY:
        logfire.warning(
            "🔓 RAG_API_KEY is not set — /query is open to anyone. Set it in production."
        )

    logfire.info("🚀 Application startup completed.")

    yield

    logfire.info("🛑 Application shutdown completed.")


# Initialize FastAPI
app = FastAPI(title="Enterprise Agentic RAG API", lifespan=lifespan)
app.include_router(health_router)

# Expose Prometheus metrics at /metrics with default request instrumentation.
Instrumentator().instrument(app).expose(app, endpoint="/metrics", include_in_schema=False)


@app.get("/")
def home():
    return {"message": "Enterprise LangGraph RAG API is live."}


@app.get("/graph")
def get_graph_image(_api_key: str = Depends(verify_api_key)):
    """
    Returns the Mermaid image of the agent's workflow.
    """
    try:
        png_bytes = app.state.rag_agent.get_graph().draw_mermaid_png()
        return Response(content=png_bytes, media_type="image/png")
    except Exception as e:
        return {"error": f"Could not generate graph image: {e}"}
