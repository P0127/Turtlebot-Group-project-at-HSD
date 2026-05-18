from typing import Optional
import re
import os

STOP_KEYWORDS = ["stop", "stopp", "halt", "halte an"]

BATTERY_KEYWORDS = [
    "akku",
    "batterie",
    "batteriestand",
    "batterie stand",
    "ladestand",
    "battery",
]

PHOTO_KEYWORDS = [
    "foto",
    "photo",
    "bild",
    "aufnahme",
    "schnappschuss",
]

DOCK_KEYWORDS = ["dock", "andocken", "docke an", "an docken"]
UNDOCK_KEYWORDS = ["undock", "abdocken", "docke ab", "ab docken"]

FORWARD_KEYWORDS = ["vorwärts", "vorwaerts", "geradeaus", "fahr vor", "fahre vor"]
BACKWARD_KEYWORDS = ["rückwärts", "rueckwaerts", "zurück", "zurueck", "backward", "fahr zurück", "fahre zurück"]
LEFT_KEYWORDS = ["links", "nach links", "dreh links", "drehe links"]
RIGHT_KEYWORDS = ["rechts", "nach rechts", "dreh rechts", "drehe rechts"]
NAV_KEYWORDS = ["navigiere", "fahre zu", "geh zu", "go to", "ziel", "koordinate", "koordinaten"]

def extract_number(text: str) -> Optional[float]:
    """
    Extracts a number from STT message (supports float).
    """
    match = re.search(r"\d+(?:[.,]\d+)?", text)
    if match:
        return float(match.group().replace(",", "."))
    return None


def extract_numbers(text: str) -> list[float]:
    vals: list[float] = []
    for m in re.findall(r"-?\d+(?:[.,]\d+)?", text):
        try:
            vals.append(float(m.replace(",", ".")))
        except Exception:
            pass
    return vals


def _contains_any(text: str, keywords: list[str]) -> bool:
    return any(k in text for k in keywords)


def parse_intent(stt_text: str) -> Optional[str]:
    """
    Changes raw STT-Text into correct command
    """
    if not stt_text:
        return None

    normalized = stt_text.lower().strip()

    if _contains_any(normalized, BATTERY_KEYWORDS):
        return "get_battery_status"

    if _contains_any(normalized, PHOTO_KEYWORDS):
        return "take_photo"

    if _contains_any(normalized, DOCK_KEYWORDS):
        return "dock"

    if _contains_any(normalized, UNDOCK_KEYWORDS):
        return "undock"

    if _contains_any(normalized, NAV_KEYWORDS):
        nums = extract_numbers(normalized)
        if len(nums) >= 2:
            x, y = nums[0], nums[1]
            yaw = nums[2] if len(nums) >= 3 else 0.0
            return f"nav {x} {y} {yaw}"
    
    for key in STOP_KEYWORDS:
        if key in normalized:
            return "stop"

    duration = extract_number(normalized)
    if duration == None:
        duration = 1.5  # Default duration, if they user forgets or dont know

    # Default speeds can be tuned to match the UI sliders.
    try:
        default_linear = float(os.getenv("STT_DEFAULT_LINEAR", "0.5") or "0.5")
    except Exception:
        default_linear = 0.5
    try:
        default_angular = float(os.getenv("STT_DEFAULT_ANGULAR", "0.5") or "0.5")
    except Exception:
        default_angular = 0.5

    if _contains_any(normalized, FORWARD_KEYWORDS):
        return f"forward {duration} {default_linear}"

    if _contains_any(normalized, BACKWARD_KEYWORDS):
        return f"backward {duration} {default_linear}"

    if _contains_any(normalized, LEFT_KEYWORDS):
        return f"left {duration} {default_angular}"

    if _contains_any(normalized, RIGHT_KEYWORDS):
        return f"right {duration} {default_angular}"

    return None
