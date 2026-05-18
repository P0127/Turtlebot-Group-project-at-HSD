from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

import logging
import os
import sys
import threading
import time
from typing import Optional

# Allow running this module as a script: `python stt.py`
# by ensuring the backend root (folder containing `app/`) is on sys.path.
if __package__ is None or __package__ == "":
    current_dir = os.path.dirname(__file__)
    backend_root = os.path.abspath(os.path.join(current_dir, "..", "..", ".."))
    if backend_root not in sys.path:
        sys.path.insert(0, backend_root)

from app.api.v1.intent_parser import parse_intent
from app.api.v1.function_calling import function_calling

router = APIRouter()
logger = logging.getLogger("backend.api.stt")


class STTTextRequest(BaseModel):
    text: str


class STTLiveStartRequest(BaseModel):
    device: Optional[str] = None
    sample_rate: Optional[int] = None


_live_lock = threading.RLock()
_live_stop_event = threading.Event()
_live_thread: threading.Thread | None = None
_live_state: dict[str, object] = {
    "running": False,
    "device": None,
    "sample_rate": None,
    "started_at": None,
    "last_error": None,
    "phase": "idle",
    "last_event_seq": 0,
    "last_event_text": None,
    "last_heard_text": None,
    "last_command_text": None,
    "last_reply": None,
}


def _set_live_event(text: str, phase: str | None = None) -> None:
    with _live_lock:
        try:
            _live_state["last_event_seq"] = int(_live_state.get("last_event_seq", 0)) + 1
        except Exception:
            _live_state["last_event_seq"] = 1
        _live_state["last_event_text"] = text
        if phase is not None:
            _live_state["phase"] = phase


def _reply_for_intent(intent: str) -> str:
    parts = (intent or "").strip().split()
    action = parts[0] if parts else ""
    if action == "stop":
        return "Verstanden. Ich stoppe."
    if action == "forward":
        return "Verstanden. Ich fahre vorwärts."
    if action == "backward":
        return "Verstanden. Ich fahre rückwärts."
    if action == "left":
        return "Verstanden. Ich drehe nach links."
    if action == "right":
        return "Verstanden. Ich drehe nach rechts."
    if action == "dock":
        return "Verstanden. Ich docke an."
    if action == "undock":
        return "Verstanden. Ich docke ab."
    if action in {"nav", "goto", "pose", "navigate"}:
        return "Verstanden. Ich navigiere zum Ziel."
    return f"Verstanden. Ich führe '{action}' aus."


@router.post("/parse")
def parse_stt_text(body: STTTextRequest):
    intent = parse_intent(body.text)
    if not intent:
        raise HTTPException(status_code=400, detail="No intent derived from text")
    return {"status": "ok", "intent": intent}


@router.post("/execute")
def execute_stt_text(body: STTTextRequest):
    # Local imports to avoid side effects when running this module as a CLI tool.
    from app.core.controller import controller
    from app.core.tts_service import say_async

    # Always try rule-based parsing first (important for deterministic intents
    # like battery queries), then optionally LLM function calling.
    rule_intent = parse_intent(body.text)

    # Handle battery query early and deterministically.
    if rule_intent == "get_battery_status":
        intent = rule_intent
    else:
        intent_mode = os.getenv("INTENT_MODE", "parse")
        if intent_mode == "parse":
            intent = rule_intent
        else:
            try:
                intent = function_calling(body.text)
            except Exception as exc:
                logger.warning("function_calling failed, fallback to parse_intent: %s", exc)
                intent = None

            if not intent:
                intent = rule_intent
    
    if not intent:
        raise HTTPException(status_code=400, detail="No intent derived from text")

    if intent == "take_photo":
        try:
            _ = controller.take_photo()
            reply = "Foto aufgenommen."
            say_async(reply)
            return {
                "status": "ok",
                "intent": intent,
                "reply": reply,
                "command_id": None,
            }
        except Exception:
            reply = "Foto konnte nicht aufgenommen werden."
            say_async(reply)
            return {
                "status": "ok",
                "intent": intent,
                "reply": reply,
                "command_id": None,
            }

    if intent == "get_battery_status":
        battery = controller.get_battery()
        raw_pct = battery.get("percentage") if isinstance(battery, dict) else None

        percent_value = None
        if raw_pct is not None:
            try:
                p = float(raw_pct)
                if 0.0 <= p <= 1.0:
                    p *= 100.0
                percent_value = max(0.0, min(100.0, p))
            except Exception:
                percent_value = None

        if percent_value is None:
            reply = "Der Batteriestatus konnte gerade nicht ermittelt werden."
        else:
            reply = f"Der aktuelle Batteriestatus beträgt {percent_value:.0f} Prozent."

        say_async(reply)
        return {
            "status": "ok",
            "intent": intent,
            "battery": percent_value,
            "reply": reply,
            "command_id": None,
        }

    command_id = controller.enqueue_command(intent)
    reply = _reply_for_intent(intent)
    say_async(reply)
    return {"status": "accepted", "intent": intent, "command_id": command_id, "reply": reply}


# keep the CLI streaming demo for local testing without affecting FastAPI startup.
def _run_live_stream(device: str = "hw:3", sample_rate: int = 16000, stop_event: threading.Event | None = None) -> None:
    import json
    import subprocess
    import time
    import vosk
    import requests

    model_path = os.getenv("STT_MODEL_PATH", "/home/ros/ros/projects/takecontrol/LM/vosk-model-de-0.21")
    model = vosk.Model(model_path)
    recognizer = vosk.KaldiRecognizer(model, sample_rate)

    base = (os.getenv("BACKEND_BASE_URL", "http://127.0.0.1:8000") or "http://127.0.0.1:8000").rstrip("/")
    endpoint = os.getenv("STT_HTTP_ENDPOINT", f"{base}/api/v1/stt/execute") or f"{base}/api/v1/stt/execute"

    # WAKE WORD CONFIG
    # Wake word: "Hallo Kröte"
    wake_word = (os.getenv("WAKE_WORD", "Hallo Kröte") or "Hallo Kröte").strip().lower()
    awake_timeout_s = float(os.getenv("WAKE_TIMEOUT_S", "8") or "8")
    awake = False
    awake_until = 0.0
    last_partial = ""

    # PipeWire/WirePlumber often keeps the *hw* device open.
    # Using ALSA 'default' (which routes through PipeWire) avoids "device busy".
    env_device = (os.getenv("STT_DEVICE") or "").strip()
    alsa_card = (os.getenv("STT_ALSA_CARD", "ArrayUAC10") or "ArrayUAC10").strip()
    candidates: list[str]
    if env_device:
        candidates = [env_device]
    else:
        candidates = [
            f"default:CARD={alsa_card}",
            f"sysdefault:CARD={alsa_card}",
            f"dsnoop:CARD={alsa_card},DEV=0",
            "default",
            # last resort: raw hardware (can be busy)
            f"plughw:CARD={alsa_card},DEV=0",
            f"hw:CARD={alsa_card},DEV=0",
        ]

    proc = None
    chosen = None
    last_err = ""
    for dev in candidates:
        print(f"Trying capture device: {dev}")
        p = subprocess.Popen(
            [
                "arecord",
                "-D",
                dev,
                "-r",
                str(sample_rate),
                "-c",
                "1",
                "-f",
                "S16_LE",
                "-t",
                "wav",
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            bufsize=0,
        )

        # Give arecord a moment; if it fails immediately, try next device.
        time.sleep(0.25)
        if p.poll() is not None:
            try:
                err = (p.stderr.read().decode("utf-8", errors="replace") if p.stderr else "").strip()
            except Exception:
                err = ""
            last_err = err or f"arecord exited with code {p.returncode}"
            print(f"Device failed: {dev} -> {last_err}")
            continue

        proc = p
        chosen = dev
        break

    if proc is None or chosen is None:
        raise RuntimeError(
            "Could not open any audio capture device. "
            "Set STT_DEVICE to a working value from `arecord -L`. "
            f"Last error: {last_err}"
        )

    print(f"Live-Stream ({chosen}, {sample_rate}Hz Mono) -> POST {endpoint}")
    with _live_lock:
        _live_state["device"] = chosen
        _live_state["phase"] = "listening"
    _set_live_event("Sprachsteuerung aktiv. Ich höre zu.", phase="listening")

    try:
        while True:
            if stop_event is not None and stop_event.is_set():
                break

            data = proc.stdout.read(16000)
            if len(data) == 0:
                break

            # Timeout: fall back to sleep state
            if awake and time.time() > awake_until:
                awake = False

            # changed - or insertet and text.lower()
            if recognizer.AcceptWaveform(data):
                result = json.loads(recognizer.Result())
                text = (result.get("text", "") or "").strip()
                text_l = text.lower()
                if text:
                    with _live_lock:
                        _live_state["last_heard_text"] = text

                if text:
                    print(f"\nText: '{text}'")

                # If not awake, only listen for wake word in final text.
                if not awake:
                    if wake_word and wake_word in text_l:
                        awake = True
                        awake_until = time.time() + awake_timeout_s
                        print("Wake word detected. Listening for command...")
                        _set_live_event("Wake Word erkannt. Ich führe den nächsten Befehl aus.", phase="awake")
                    continue

                # Awake: send recognized text to backend (but ignore pure wake-word-only utterances).
                if wake_word and text_l == wake_word:
                    continue

                if text:
                    try:
                        # Send raw recognized text to the backend; backend derives intent + executes.
                        with _live_lock:
                            _live_state["phase"] = "executing"
                            _live_state["last_command_text"] = text
                        res = requests.post(endpoint, json={"text": text}, timeout=5)
                        print(f"Backend: {res.status_code} {res.text}")
                        try:
                            payload = res.json()
                        except Exception:
                            payload = {}
                        reply = payload.get("reply") if isinstance(payload, dict) else None
                        if reply:
                            with _live_lock:
                                _live_state["last_reply"] = reply
                        if res.ok:
                            _set_live_event(
                                f"Befehl erkannt: '{text}'. {reply or 'Wird ausgeführt.'}",
                                phase="listening",
                            )
                        else:
                            _set_live_event(
                                f"Befehl konnte nicht ausgeführt werden: '{text}'",
                                phase="listening",
                            )
                    except Exception as exc:
                        print(f"HTTP failed: {exc}")
                        _set_live_event(f"Backend-Fehler bei Sprachbefehl: {exc}", phase="listening")
            else:
                partial = json.loads(recognizer.PartialResult())
                ptxt = (partial.get("partial", "") or "").strip()
                if ptxt and ptxt != last_partial:
                    last_partial = ptxt

                # Show partials (same as before)
                print(f"\rTeil: {ptxt}", end="", flush=True)

                # Wake-word detection on partials for lower latency.
                ptxt_l = ptxt.lower()
                if not awake and wake_word and wake_word in ptxt_l:
                    awake = True
                    awake_until = time.time() + awake_timeout_s
                    print("\nWake word detected (partial). Listening for command...")
                    _set_live_event("Wake Word erkannt. Ich führe den nächsten Befehl aus.", phase="awake")

                    # reset to reduce chance of sending the wake word as the command.
                    # Vosk has a recognizer reset in the API; python binding may expose it as Reset(). 
                    try:
                        recognizer.Reset()
                    except Exception:
                        pass

    except KeyboardInterrupt:
        print("\nBeendet!")
    finally:
        try:
            proc.terminate()
        except Exception:
            pass
        with _live_lock:
            if _live_state.get("running"):
                _live_state["phase"] = "stopped"


if __name__ == "__main__":
    _run_live_stream()


def _live_status_payload() -> dict:
    with _live_lock:
        running = bool(_live_thread is not None and _live_thread.is_alive())
        _live_state["running"] = running
        return dict(_live_state)


@router.get("/live/status")
def live_status():
    return {"status": "ok", **_live_status_payload()}


@router.post("/live/start")
def live_start(body: STTLiveStartRequest | None = None):
    global _live_thread
    req = body or STTLiveStartRequest()

    with _live_lock:
        if _live_thread is not None and _live_thread.is_alive():
            return {"status": "already_running", **_live_status_payload()}

        device = (req.device or os.getenv("STT_DEVICE") or "").strip() or None
        sample_rate = int(req.sample_rate or int(os.getenv("STT_SAMPLE_RATE", "16000") or "16000"))

        _live_stop_event.clear()
        _live_state["running"] = True
        _live_state["device"] = device or "auto"
        _live_state["sample_rate"] = sample_rate
        _live_state["started_at"] = time.time()
        _live_state["last_error"] = None
        _live_state["phase"] = "starting"

        def _runner() -> None:
            try:
                _run_live_stream(device=device or "hw:3", sample_rate=sample_rate, stop_event=_live_stop_event)
            except Exception as exc:
                with _live_lock:
                    _live_state["last_error"] = str(exc)
                    _live_state["phase"] = "error"
                _set_live_event(f"Sprachsteuerung Fehler: {exc}", phase="error")
            finally:
                with _live_lock:
                    _live_state["running"] = False
                    if _live_state.get("phase") != "error":
                        _live_state["phase"] = "stopped"

        _live_thread = threading.Thread(target=_runner, name="stt-live", daemon=True)
        _live_thread.start()

    return {"status": "started", **_live_status_payload()}


@router.post("/live/stop")
def live_stop():
    global _live_thread
    with _live_lock:
        if _live_thread is None or not _live_thread.is_alive():
            _live_state["running"] = False
            return {"status": "not_running", **_live_status_payload()}

        _live_stop_event.set()
        t = _live_thread

    t.join(timeout=3.0)

    with _live_lock:
        _live_state["running"] = bool(_live_thread is not None and _live_thread.is_alive())
        if not _live_state["running"]:
            _live_thread = None
            _live_state["phase"] = "stopped"

    _set_live_event("Sprachsteuerung gestoppt.", phase="stopped")

    return {"status": "stopping", **_live_status_payload()}