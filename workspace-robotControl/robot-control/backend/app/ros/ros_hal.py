"""ROS HAL base classes to keep ROS specifics out of core."""
from __future__ import annotations

import logging
import os
import threading
import time
from abc import ABC, abstractmethod

from app.ros.robot_interface import RobotInterface
from app.ros.ros2_manager import ROS2Publisher, get_publisher


logger = logging.getLogger("backend.ros.ros_hal")


class RosRobotBase(RobotInterface, ABC):
    """Base class for ROS-backed robots.

    Provides shared publishing and optional subscriptions.
    """

    def __init__(self, topic: str, msg_type, default_key: str = "cmd_vel") -> None:
        self._default_key = default_key
        self._publishers: dict[str, ROS2Publisher] = {}
        self._subscriptions: dict[str, object] = {}
        self.register_publisher(default_key, topic, msg_type)

    def register_publisher(self, key: str, topic: str, msg_type) -> None:
        self._publishers[key] = get_publisher(topic, msg_type)

    def register_subscription(self, key: str, topic: str, msg_type, callback, qos: int = 10) -> None:
        publisher = self._publishers[self._default_key]
        self._subscriptions[key] = publisher.create_subscription(topic, msg_type, callback, qos)

    def shutdown(self) -> None:
        # Cleanly stop ROS2 background threads/executors.
        for pub in list(self._publishers.values()):
            try:
                pub.shutdown()
            except Exception:
                pass

    def _publisher(self, key: str | None = None) -> ROS2Publisher:
        return self._publishers[key or self._default_key]

    def _refresh_timestamp(self, msg, key: str | None = None) -> None:
        if not hasattr(msg, "header"):
            return

        # Some robots/nodes expect TwistStamped headers to be left at 0 (stamp unset)
        # while others expect current time. Make this configurable.
        stamp_mode = (os.getenv("CMD_VEL_STAMP_MODE", "preserve") or "preserve").strip().lower()
        # preserve: do nothing if a stamp exists
        # now: set stamp to current node time
        # zero: force stamp = 0
        if stamp_mode == "now":
            msg.header.stamp = self._publisher(key).now()
        elif stamp_mode == "zero":
            try:
                msg.header.stamp.sec = 0
                msg.header.stamp.nanosec = 0
            except Exception:
                # Fallback: if stamp is not mutable, overwrite with a zero time msg
                from builtin_interfaces.msg import Time  # type: ignore
                msg.header.stamp = Time(sec=0, nanosec=0)

        # Optionally set a frame_id (some stacks prefer e.g. base_link)
        frame_id = os.getenv("CMD_VEL_FRAME_ID")
        if frame_id is not None and hasattr(msg.header, "frame_id"):
            msg.header.frame_id = str(frame_id)

    def _publish(self, msg, key: str | None = None) -> None:
        self._refresh_timestamp(msg, key)
        self._publisher(key).publish(msg)

        if (os.getenv("CMD_VEL_DEBUG", "0").strip().lower() in {"1", "true", "yes", "on"}) and (key is None or key == self._default_key):
            try:
                topic = getattr(self._publisher(key), "_topic", "<topic>")
                if hasattr(msg, "twist"):
                    lin_x = float(getattr(msg.twist.linear, "x", 0.0))
                    ang_z = float(getattr(msg.twist.angular, "z", 0.0))
                else:
                    lin_x = float(getattr(msg.linear, "x", 0.0))
                    ang_z = float(getattr(msg.angular, "z", 0.0))
                logger.info("Published cmd_vel to %s: linear.x=%.3f angular.z=%.3f", topic, lin_x, ang_z)
            except Exception:
                pass

    def _publish_for(
        self,
        msg,
        duration_s: float,
        cancel_event: threading.Event | None = None,
        key: str | None = None,
    ) -> None:
        """Publish a message for the given duration, then stop."""
        end = time.time() + max(0.0, float(duration_s))
        if duration_s <= 0:
            self._publish(msg, key)
            self.stop()
            return

        while time.time() < end:
            if cancel_event is not None and cancel_event.is_set():
                break
            self._publish(msg, key)
            time.sleep(0.05)

        self.stop()

    @abstractmethod
    def stop(self) -> None:
        """Stop the robot (publish zero velocity)."""
        raise NotImplementedError
