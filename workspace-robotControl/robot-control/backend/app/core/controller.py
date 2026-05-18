"""Controller (no ROS imports here)."""
import logging
import threading
import time

from app.core.commands import parse_command
from app.core.config import get_robot_backend
from app.core.command_queue import CommandQueueManager
from app.core.state_service import state_service

logger = logging.getLogger("backend.core.controller")


class RobotController:
    
    def __init__(self):
        logger.debug("Initializing RobotController")
        self.robot = get_robot_backend()
        self._state_stop_event = threading.Event()
        self._state_thread: threading.Thread | None = None
        self._queue = CommandQueueManager(
            execute_fn=self._execute_one_command,
            stop_fn=self._stop_robot_immediately,
            max_queue_size=40,
            on_status=state_service.publish_queue_status,
            on_event=state_service.publish_command_event,
        )

        self._queue.start()
        self._start_state_publisher()

    """Public methods for controlling the robot and its command queue."""

    def enqueue_command(self, command_text: str):
        """Enqueue a command and return its job ID.
        This is non-blocking; the REST API can return immediately."""
        logger.debug("enqueue_command called: %s", command_text)
        return self._queue.enqueue(command_text)

    def emergency_stop(self) -> None:
        """Cancel the current command and clear the queue."""
        logger.debug("emergency_stop called")
        self._queue.emergency_stop(clear_queue=True) 


    def status(self) -> dict:
        """Get current status of the command queue."""
        return {
            "robot_backend": type(self.robot).__name__,
            **self._queue.get_status(),
        }
    
    def shutdown(self) -> None:
        """Called on app shutdown to stop the worker thread and robot."""
        logger.debug("shutdown called")
        self._state_stop_event.set()
        if self._state_thread:
            self._state_thread.join(timeout=1.0)
        self._queue.shutdown(timeout_s=2.0)

        # If the backend is ROS2-based, stop background spin threads cleanly.
        shutdown_robot = getattr(self.robot, "shutdown", None)
        if callable(shutdown_robot):
            try:
                shutdown_robot()
            except Exception as exc:
                logger.warning("robot.shutdown failed: %s", exc)
    
    def health(self) -> dict:
        """Quick health info for debugging."""
        logger.debug("health called")
        battery_pct = None
        try:
            battery = self.get_battery()
            raw_pct = battery.get("percentage") if isinstance(battery, dict) else None
            if raw_pct is not None:
                pct = float(raw_pct)
                # Some ROS drivers report battery in [0,1], others already in [0,100].
                if 0.0 <= pct <= 1.0:
                    pct *= 100.0
                battery_pct = round(max(0.0, min(100.0, pct)), 2)
        except Exception:
            battery_pct = None

        return {
            "robot_backend": type(self.robot).__name__,
            "battery": battery_pct,
        }
    
    def take_photo(self) -> str:
        logger.debug("take_photo called")
        get_photo = getattr(self.robot, "get_last_image_base64", None)
        if callable(get_photo):
            try:
                return get_photo()
            except Exception as exc:
                logger.warning("take_photo failed, returning placeholder: %s", exc)

        photo = "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+ip1sAAAAASUVORK5CYII="  # Placeholder image data
        return photo

    def get_map(self) -> dict:
        get_map = getattr(self.robot, "get_last_map", None)
        if not callable(get_map):
            return {"available": False, "reason": "Map not supported by this backend"}

        msg = get_map()
        if msg is None:
            return {"available": False, "reason": "No map received yet"}

        info = getattr(msg, "info", None)
        origin = getattr(info, "origin", None) if info is not None else None
        position = getattr(origin, "position", None) if origin is not None else None

        return {
            "available": True,
            "width": getattr(info, "width", None),
            "height": getattr(info, "height", None),
            "resolution": getattr(info, "resolution", None),
            "origin": {
                "x": getattr(position, "x", None),
                "y": getattr(position, "y", None),
                "z": getattr(position, "z", None),
            },
            "data_length": len(getattr(msg, "data", []) or []),
        }

    def get_nav_status(self) -> dict:
        get_nav_status = getattr(self.robot, "get_last_nav_status", None)
        if not callable(get_nav_status):
            return {"available": False, "reason": "Navigation status not supported by this backend"}

        msg = get_nav_status()
        if msg is None:
            return {"available": False, "reason": "No navigation status received yet"}

        status_list = getattr(msg, "status_list", []) or []
        simplified = []
        for status in status_list:
            simplified.append({
                "status": getattr(status, "status", None),
            })

        return {
            "available": True,
            "count": len(simplified),
            "statuses": simplified,
        }

    def get_battery(self) -> dict:
        get_battery = getattr(self.robot, "get_last_battery", None)
        if not callable(get_battery):
            return {"available": False, "reason": "Battery not supported by this backend"}

        msg = get_battery()
        if msg is None:
            return {"available": False, "reason": "No battery data received yet"}

        return {
            "available": True,
            "percentage": getattr(msg, "percentage", None),
            "voltage": getattr(msg, "voltage", None),
            "current": getattr(msg, "current", None),
            "temperature": getattr(msg, "temperature", None),
        }

    def get_camera_info(self) -> dict:
        get_image = getattr(self.robot, "get_last_image", None)
        if not callable(get_image):
            return {"available": False, "reason": "Camera not supported by this backend"}

        msg = get_image()
        if msg is None:
            return {"available": False, "reason": "No image received yet"}

        return {
            "available": True,
            "height": getattr(msg, "height", None),
            "width": getattr(msg, "width", None),
            "encoding": getattr(msg, "encoding", None),
        }

    def get_dock_status(self) -> dict:
        get_docking_status = getattr(self.robot, "get_docking_status", None)
        if not callable(get_docking_status):
            return {"available": False, "reason": "Docking not supported by this backend"}

        try:
            return get_docking_status()
        except Exception as exc:
            return {"available": False, "reason": str(exc)}
    
    """Internal methods for executing commands and stopping the robot."""

    def _execute_one_command(self, command_text: str, cancel_event: threading.Event) -> None:
        """Execute a single command.
        This runs in the worker thread."""
        logger.debug("_execute_one_command called: %s", command_text)
        # If a stop has been requested before we start, do nothing.
        if cancel_event.is_set():
            return  
        
        try:
            cmd = parse_command(command_text)

            # Check again before executing.
            if cancel_event.is_set():
                return

            self.robot.execute_command(cmd, cancel_event)
        except Exception as e:
            logger.error("Error executing command '%s': %s", command_text, str(e), exc_info=True)
    

    def _stop_robot_immediately(self) -> None:
        """Stop the robot immediately.
        For true cancellation of current command, the ROS publisher must cooperate."""
        logger.debug("_stop_robot_immediately called")
        self.robot.stop()

    def _start_state_publisher(self) -> None:
        if self._state_thread and self._state_thread.is_alive():
            return

        logger.debug("Starting state publisher thread")

        def _loop() -> None:
            last_seen: dict[str, int] = {}
            while not self._state_stop_event.is_set():
                payload: dict[str, object] = {}
                changed = False

                items = {
                    "battery": getattr(self.robot, "get_last_battery", None),
                    "camera": getattr(self.robot, "get_last_image", None),
                    "map": getattr(self.robot, "get_last_map", None),
                    "nav_status": getattr(self.robot, "get_last_nav_status", None),
                }

                for key, getter in items.items():
                    if not callable(getter):
                        continue
                    try:
                        msg = getter()
                    except Exception:
                        continue
                    if msg is None:
                        continue

                    msg_id = id(msg)
                    if last_seen.get(key) == msg_id:
                        continue
                    last_seen[key] = msg_id

                    if key == "battery":
                        payload[key] = self.get_battery()
                    elif key == "camera":
                        payload[key] = self.get_camera_info()
                    elif key == "map":
                        payload[key] = self.get_map()
                    elif key == "nav_status":
                        payload[key] = self.get_nav_status()

                    changed = True

                if changed:
                    state_service.publish_robot_status(payload)

                time.sleep(0.2)

        self._state_thread = threading.Thread(target=_loop, name="StatePublisher", daemon=True)
        self._state_thread.start()
    



# Global instance
controller = RobotController()
