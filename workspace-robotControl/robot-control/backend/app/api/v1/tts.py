"""Offline TTS exposed as API."""

import subprocess

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.core.tts_service import say as tts_say


router = APIRouter()


class TTSRequest(BaseModel):
    text: str
    lang: str = "de-DE"


@router.post("/say")
def say(body: TTSRequest):
    try:
        tts_say(body.text, body.lang)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=500, detail=f"TTS dependency missing: {exc}")
    except subprocess.CalledProcessError as exc:
        raise HTTPException(status_code=500, detail=f"TTS command failed: {exc}")
    return {"status": "ok"}


if __name__ == "__main__":
    tts_say("Hallo, das ist ein Test mit Pico TTS auf deinem Computer.", "de-DE")

