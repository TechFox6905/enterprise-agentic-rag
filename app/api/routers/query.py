import time
import uuid
from typing import Optional

import logfire
from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse

from pydantic import BaseModel

from app.api.auth import verify_api_key
from app.guardrails import guard
from app.logging import set_request_id
from app.api.rate_limit import rate_limit
from app.api.metrics import RAG_REQUEST_DURATION, RAG_REQUESTS_TOTAL, GUARDRAILS_BLOCKS_TOTAL

router = APIRouter(tags=["query"])


class QueryRequest(BaseModel):
    q: str
    thread_id: Optional[str] = "default_user"


@router.post("/query")
@rate_limit()
def query(
    request: Request,
    body: QueryRequest,
    _api_key: str = Depends(verify_api_key),
):
    """
    Runs the LangGraph RAG pipeline synchronously.
    Returns the final answer, thought process, status, and sources.
    """
    q = body.q
    thread_id = body.thread_id
    request_id = str(uuid.uuid4())
    set_request_id(request_id)

    start = time.perf_counter()
    with logfire.span("🔍 /query", request_id=request_id, thread_id=thread_id):
        # Gate: run guardrails synchronously so blocked requests never run the graph.
        rail_fired, rail_response = guard(q)
        if rail_fired:
            GUARDRAILS_BLOCKS_TOTAL.labels(blocked="true").inc()
            RAG_REQUESTS_TOTAL.labels(status="blocked").inc()
            RAG_REQUEST_DURATION.observe(time.perf_counter() - start)
            logfire.info("🛡️ Request blocked by guardrails", request_id=request_id, thread_id=thread_id)
            return {
                "question": q,
                "answer": rail_response,
                "thought_process": ["Intent: Guardrails Fired", "Retrieval: Skipped"],
                "status": "Blocked by guardrails.",
                "sources": [],
            }

        GUARDRAILS_BLOCKS_TOTAL.labels(blocked="false").inc()

        try:
            rag_agent = request.app.state.rag_agent
            initial_state = {
                "messages": [{"role": "user", "content": q}],
                "current_query": q,
                "documents": [],
                "plan": ["Start"],
                "status": "Initializing Graph...",
            }
            config = {"configurable": {"thread_id": thread_id}}
            final_output = rag_agent.invoke(initial_state, config=config)

            RAG_REQUESTS_TOTAL.labels(status="success").inc()
            RAG_REQUEST_DURATION.observe(time.perf_counter() - start)
            logfire.info(
                "✅ RAG pipeline completed",
                request_id=request_id,
                thread_id=thread_id,
            )
            return {
                "question": q,
                "answer": final_output.get("final_answer"),
                "thought_process": final_output.get("plan"),
                "status": final_output.get("status"),
                "sources": final_output.get("documents", []),
            }
        except Exception as e:
            RAG_REQUESTS_TOTAL.labels(status="error").inc()
            RAG_REQUEST_DURATION.observe(time.perf_counter() - start)
            logfire.error(
                f"❌ RAG pipeline failed: {e}",
                request_id=request_id,
                thread_id=thread_id,
            )
            return JSONResponse(
                status_code=500,
                content={
                    "request_id": request_id,
                    "status": "error",
                    "message": "Failed to process request. Please try again later.",
                },
            )
