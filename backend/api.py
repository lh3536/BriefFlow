"""Thin HTTP boundary for the existing Router; no business logic duplication."""
import logging

from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict, Field, field_validator

from backend.router.service import run_brief_flow

LOGGER = logging.getLogger(__name__)
app = FastAPI(title="BriefFlow", version="0.1.0")


class BriefRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    user_text: str = Field(strict=True, min_length=1, max_length=2000)

    @field_validator("user_text")
    @classmethod
    def nonblank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("Please enter your requirements.")
        return value.strip()


@app.get("/api/health")
def health() -> dict:
    return {"status": "ok"}


@app.post("/api/brief")
def generate_brief(request: BriefRequest):
    try:
        return JSONResponse(content=run_brief_flow(request.user_text))
    except Exception:
        LOGGER.exception("Brief pipeline failed")
        raise HTTPException(status_code=500, detail="Unable to generate brief. Please try again.") from None
