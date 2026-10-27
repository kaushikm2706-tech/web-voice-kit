"""Agent endpoints for the payment-promise demo: /agent/turn and /agent/confirm.
They wrap examples/voice-agent/extract.py. No audio, no transcripts stored or logged. (UNOFFICIAL, not affiliated with Gnani AI.)"""
import datetime as dt
import importlib.util
from pathlib import Path
from typing import Any, Optional

from fastapi import APIRouter
from pydantic import BaseModel, Field

_path = Path(__file__).resolve().parent.parent / "examples" / "voice-agent" / "extract.py"
_spec = importlib.util.spec_from_file_location("voice_agent_extract", _path)
ex = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(ex)

router = APIRouter(prefix="/agent")


class TurnRequest(BaseModel):
    text: str = Field(min_length=1, max_length=400)
    amount: Optional[int] = Field(default=None, ge=0, le=10**9)
    day: Optional[dict[str, Any]] = None
    today: Optional[dt.date] = None          # the caller's local date, sent by the page


class ConfirmRequest(BaseModel):
    text: str = Field(min_length=1, max_length=400)


@router.post("/turn")
def turn(req: TurnRequest):
    r = ex.turn(req.text, req.today or dt.date.today(), req.amount, req.day)
    return {"amount": r["amount"], "day": r["day"], "date": r["date"].isoformat() if r["date"] else None,
            "prompt": r["confirm_prompt"], "needsClarification": r["needs_clarification"], "summary": r["summary"]}


@router.post("/confirm")
def confirm(req: ConfirmRequest):
    return ex.confirm_intent(req.text)
