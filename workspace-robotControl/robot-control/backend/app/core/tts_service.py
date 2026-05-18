"""TTS service.

Provides a small, dependency-light wrapper around pico2wave + an audio player.
Designed to be safe to call from request handlers (supports async fire-and-forget).
"""

from __future__ import annotations

import logging
import os
import shutil
import subprocess
import tempfile
import threading

logger = logging.getLogger("backend.core.tts")


def _pick_player() -> list[str] | None:
    # Prefer pulseaudio, fall back to ALSA.
    env_player = (os.getenv("TTS_PLAYER") or "").strip()
    if env_player:
        return env_player.split()

    if shutil.which("paplay"):
        return ["paplay"]
    if shutil.which("aplay"):
        return ["aplay"]
    return None


def say(text: str, lang: str | None = None) -> None:
    enabled = (os.getenv("TTS_ENABLED", "1") or "1").strip().lower() in {"1", "true", "yes", "on"}
    if not enabled:
        logger.info("TTS disabled (TTS_ENABLED=0): %s", text)
        return

    text = (text or "").strip()
    if not text:
        return

    lang = (lang or os.getenv("TTS_LANG", "de-DE") or "de-DE").strip()

    engine = (os.getenv("TTS_ENGINE", "auto") or "auto").strip().lower()

    # 1) pico2wave -> wav -> player
    if engine in {"auto", "pico", "pico2wave"}:
        pico = os.getenv("TTS_PICO2WAVE", "pico2wave")
        if shutil.which(pico):
            player = _pick_player()
            if player is None:
                raise FileNotFoundError("No audio player found (paplay/aplay). Set TTS_PLAYER.")

            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
                wav_path = tmp.name

            try:
                subprocess.run([pico, "-l", lang, "-w", wav_path, text], check=True)
                subprocess.run([*player, wav_path], check=True)
                return
            finally:
                try:
                    os.remove(wav_path)
                except Exception:
                    pass
        if engine in {"pico", "pico2wave"}:
            raise FileNotFoundError("pico2wave not found")

    # 2) speech-dispatcher (plays itself)
    if engine in {"auto", "spd", "spd-say"} and shutil.which("spd-say"):
        # spd-say language examples: 'de', 'de-DE'. We'll pass through.
        subprocess.run(["spd-say", "-l", lang, text], check=True)
        return
    if engine in {"spd", "spd-say"}:
        raise FileNotFoundError("spd-say not found")

    # 3) espeak (plays itself)
    espeak = "espeak-ng" if shutil.which("espeak-ng") else ("espeak" if shutil.which("espeak") else None)
    if engine in {"auto", "espeak", "espeak-ng"} and espeak:
        # Map de-DE -> de for espeak
        voice = "de" if lang.lower().startswith("de") else lang
        subprocess.run([espeak, "-v", voice, text], check=True)
        return
    raise FileNotFoundError("No TTS engine available (pico2wave/spd-say/espeak)")


def say_async(text: str, lang: str | None = None) -> None:
    # Fire-and-forget so we don't block API response times.
    def _run() -> None:
        try:
            say(text, lang)
        except Exception as exc:
            logger.warning("TTS failed: %s", exc)

    threading.Thread(target=_run, name="tts-say", daemon=True).start()
