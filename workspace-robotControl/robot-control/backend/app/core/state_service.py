"""Reactive state service for UI updates."""
from __future__ import annotations

import logging
import threading
import time
from typing import Any

from rx.subject import BehaviorSubject

logger = logging.getLogger("backend.core.state_service")


class StateService:
    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._subject = BehaviorSubject(self._base_payload({}))

    def _base_payload(self, data: dict[str, Any]) -> dict[str, Any]:
        return {
            "type": "state",
            "timestamp": time.time(),
            "data": data,
        }

    def publish(self, data: dict[str, Any]) -> None:
        with self._lock:
            self._subject.on_next(self._base_payload(data))

    def publish_queue_status(self, status: dict[str, Any]) -> None:
        self.publish({"queue": status})

    def publish_robot_status(self, status: dict[str, Any]) -> None:
        self.publish({"robot": status})

    def publish_command_event(self, event: dict[str, Any]) -> None:
        self.publish({"command_event": event})

    def snapshot(self) -> dict[str, Any]:
        return self._subject.value

    def subject(self) -> BehaviorSubject:
        return self._subject


state_service = StateService()