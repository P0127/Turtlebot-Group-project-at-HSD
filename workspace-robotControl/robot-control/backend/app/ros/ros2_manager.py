"""ROS2 manager for publishing Twist commands.

This keeps ROS2-specific imports and lifecycle contained in the ros layer.

Notes (Windows): ROS2 Python packages (rclpy, geometry_msgs) typically come
from the ROS2 installation, not conda. If they are unavailable, this module
will raise a clear error when used.
"""

from __future__ import annotations

import os
import threading
from typing import Optional


_rclpy_lock = threading.RLock()
_rclpy_init_done = False
_active_publishers = 0


class ROS2NotAvailableError(RuntimeError):
    pass


class ROS2Publisher:
    """Base class for ROS2 publishers"""

    def __init__(self, topic: str, msg_type) -> None:
        self._topic = topic
        self._msg_type = msg_type
        self._lock = threading.RLock()
        self._spin_thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()

        # Deferred imports so the rest of the backend runs without ROS2.
        try:
            import rclpy  # type: ignore
            from rclpy.node import Node  # type: ignore
            from rclpy.qos import QoSProfile, ReliabilityPolicy, DurabilityPolicy  # type: ignore
            from rclpy.executors import SingleThreadedExecutor  # type: ignore
        except Exception as exc:  # pragma: no cover
            raise ROS2NotAvailableError(
                "ROS2 Python packages not available. "
                "Ensure ROS2 is installed and its environment is sourced so 'import rclpy' works. "
                f"Original error: {exc}"
            )

        self._rclpy = rclpy

        global _rclpy_init_done, _active_publishers
        with _rclpy_lock:
            if not _rclpy_init_done:
                if not self._rclpy.ok():
                    self._rclpy.init(args=None)
                _rclpy_init_done = True
            _active_publishers += 1

        topic_name = self._topic.replace("/", "_").strip("_")
        self._node: Node = Node(f"backend_publisher_{topic_name}")
        self._executor = SingleThreadedExecutor()
        self._executor.add_node(self._node)

        # QoS can be tuned via env to match the robot's subscriber.
        reliability_env = (os.getenv("CMD_VEL_RELIABILITY", "best_effort") or "best_effort").lower()
        durability_env = (os.getenv("CMD_VEL_DURABILITY", "volatile") or "volatile").lower()
        depth_env = int(os.getenv("CMD_VEL_DEPTH", "10") or "10")
   
        robot_backend = os.getenv("ROBOT_BACKEND", "sim").lower()
        if robot_backend == "sim":
            reliability_env = "reliable"

        rel_map = {
            "best_effort": ReliabilityPolicy.BEST_EFFORT,
            "reliable": ReliabilityPolicy.RELIABLE,
        }
        dur_map = {
            "volatile": DurabilityPolicy.VOLATILE,
            "transient_local": DurabilityPolicy.TRANSIENT_LOCAL,
        }

        qos_profile = QoSProfile(
            reliability=rel_map.get(reliability_env, ReliabilityPolicy.BEST_EFFORT),
            durability=dur_map.get(durability_env, DurabilityPolicy.VOLATILE),
            depth=depth_env,
        )

        self._pub = self._node.create_publisher(self._msg_type, self._topic, qos_profile)

        self._ensure_spinning()

    def _ensure_spinning(self) -> None:
        with self._lock:
            if self._spin_thread and self._spin_thread.is_alive():
                return

            self._stop_event.clear()

            def _spin() -> None:
                while not self._stop_event.is_set() and self._rclpy.ok():
                    self._executor.spin_once(timeout_sec=0.1)

            self._spin_thread = threading.Thread(target=_spin, name="ros2-spin", daemon=True)
            self._spin_thread.start()

    def shutdown(self) -> None:
        global _active_publishers
        with self._lock:
            self._stop_event.set()

            # Stop spin thread first to avoid races with executor/node teardown.
            t = self._spin_thread
            if t is not None and t.is_alive():
                t.join(timeout=2.0)

            try:
                try:
                    # rclpy executors support shutdown() in most distros.
                    self._executor.shutdown()
                except Exception:
                    pass

                try:
                    self._executor.remove_node(self._node)
                except Exception:
                    pass

                try:
                    self._node.destroy_node()
                except Exception:
                    pass
            finally:
                with _rclpy_lock:
                    _active_publishers = max(0, int(_active_publishers) - 1)
                    # Only shut down rclpy when the last publisher is gone.
                    if _active_publishers == 0 and self._rclpy.ok():
                        try:
                            self._rclpy.shutdown()
                        except Exception:
                            pass

    def get_node(self):
        return self._node

    def now(self):
        return self._node.get_clock().now().to_msg()

    def publish(self, msg) -> None:
        self._pub.publish(msg)

    def create_subscription(self, topic: str, msg_type, callback, qos: int = 10):
        # Many robot sensor topics (camera/odom/laser) are published as BEST_EFFORT.
        # If we subscribe with RELIABLE (rclpy default when passing an int depth),
        # endpoints may not match and messages stop arriving.
        try:
            from rclpy.qos import QoSProfile, ReliabilityPolicy, DurabilityPolicy  # type: ignore
        except Exception:
            return self._node.create_subscription(msg_type, topic, callback, qos)

        # If caller passed a QoSProfile already, forward it.
        if not isinstance(qos, int):
            return self._node.create_subscription(msg_type, topic, callback, qos)

        reliability_env = (os.getenv("ROS_SUB_RELIABILITY", "best_effort") or "best_effort").lower()
        durability_env = (os.getenv("ROS_SUB_DURABILITY", "volatile") or "volatile").lower()

        rel_map = {
            "best_effort": ReliabilityPolicy.BEST_EFFORT,
            "reliable": ReliabilityPolicy.RELIABLE,
        }
        dur_map = {
            "volatile": DurabilityPolicy.VOLATILE,
            "transient_local": DurabilityPolicy.TRANSIENT_LOCAL,
        }

        profile = QoSProfile(
            depth=int(qos),
            reliability=rel_map.get(reliability_env, ReliabilityPolicy.BEST_EFFORT),
            durability=dur_map.get(durability_env, DurabilityPolicy.VOLATILE),
        )
        return self._node.create_subscription(msg_type, topic, callback, profile)


_publishers: dict[tuple[str, object], ROS2Publisher] = {}


def get_publisher(topic_name: str, msg_type) -> ROS2Publisher:
    key = (topic_name, msg_type)
    if key not in _publishers:
        print(f"Creating new ROS2Publisher for topic: {topic_name} with msg_type: {msg_type}")
        _publishers[key] = ROS2Publisher(topic=topic_name, msg_type=msg_type)
    return _publishers[key]