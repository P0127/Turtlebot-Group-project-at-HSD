"""
TurtleBot Backend
"""
import base64
import io
import os
import threading
import time
from typing import Any

from geometry_msgs.msg import Twist
import numpy as np
from PIL import Image

from app.core.models.command import (
    Command,
    DockCommand,
    ForwardCommand,
    NavigateToPoseCommand,
    StopCommand,
    TurnLeftCommand,
    TurnRightCommand,
    UndockCommand,
)
from app.ros.ros_hal import RosRobotBase


class TurtleBotRobot(RosRobotBase):

    CMD_VEL_TOPIC = "/cmd_vel"
    ODOM_TOPIC = "/odom"
    BATTERY_TOPIC = "/battery_state"
    CAMERA_TOPIC = "/camera/image_raw"
    OAKD_CAMERA_TOPIC = "/oakd/rgb/preview/image_raw"
    MAP_TOPIC = "/map"
    NAV_STATUS_TOPIC = "/navigate_to_pose/_action/status"

    NAV2_ACTIVE_TIMEOUT_S = 2.0  # Reduced from 15.0 to fail faster if Nav2 is not available
    NAV2_TASK_TIMEOUT_S = 180.0
    DOCK_TASK_TIMEOUT_S = 20.0  # Keep queue responsive if docking stack isn't ready

    def __init__(self) -> None:
        cmd_vel_topic = os.getenv("CMD_VEL_TOPIC", self.CMD_VEL_TOPIC)
        cmd_vel_type = (os.getenv("CMD_VEL_MSG_TYPE", "TwistStamped") or "TwistStamped").strip()

        # Some TurtleBot/Create3 stacks consume Twist (unstamped) on a separate topic.
        # To avoid "published but robot doesn't move" situations, we can optionally
        # publish the same velocities to an additional Twist topic.
        self._publish_unstamped = self._env_bool("CMD_VEL_PUBLISH_UNSTAMPED", True)
        self._cmd_vel_unstamped_topic = (os.getenv("CMD_VEL_UNSTAMPED_TOPIC", "/cmd_vel_unstamped") or "/cmd_vel_unstamped").strip()

        # Important: ROS2 requires publisher/subscriber message types to match exactly.
        # TurtleBot4 uses TwistStamped on /cmd_vel with BEST_EFFORT QoS.
        msg_type: Any
        if cmd_vel_type.lower() in {"twiststamped", "stamped"}:
            from geometry_msgs.msg import TwistStamped  # type: ignore
            msg_type = TwistStamped
            self._cmd_vel_kind = "TwistStamped"
        else:
            msg_type = Twist
            self._cmd_vel_kind = "Twist"

        super().__init__(cmd_vel_topic, msg_type)

        if self._publish_unstamped:
            try:
                from geometry_msgs.msg import Twist as TwistMsg  # type: ignore
                self.register_publisher("cmd_vel_unstamped", self._cmd_vel_unstamped_topic, TwistMsg)
            except Exception:
                # If geometry_msgs is unavailable, RosRobotBase will already be unusable.
                self._publish_unstamped = False

        self._last_odom = None
        self._last_battery = None
        self._last_image = None
        self._last_image_b64: str | None = None
        self._last_image_b64_time: float = 0.0
        self._last_image_id: int | None = None
        self._image_cache_lock = threading.RLock()
        self._last_map = None
        self._last_nav_status = None

        try:
            from nav_msgs.msg import Odometry
            self.register_subscription("odom", self.ODOM_TOPIC, Odometry, self._on_odom)
        except Exception:
            pass

        try:
            from sensor_msgs.msg import BatteryState
            self.register_subscription("battery", self.BATTERY_TOPIC, BatteryState, self._on_battery)
        except Exception:
            pass

        camera_topic = os.getenv("CAMERA_TOPIC", self.CAMERA_TOPIC)
        oakd_topic = os.getenv("OAKD_CAMERA_TOPIC", self.OAKD_CAMERA_TOPIC)
        try:
            from sensor_msgs.msg import Image
            self.register_subscription("camera", camera_topic, Image, self._on_image)
            if oakd_topic and oakd_topic != camera_topic:
                self.register_subscription("camera_oakd", oakd_topic, Image, self._on_image)
        except Exception:
            pass

        try:
            from nav_msgs.msg import OccupancyGrid
            self.register_subscription("map", self.MAP_TOPIC, OccupancyGrid, self._on_map)
        except Exception:
            pass

        try:
            from action_msgs.msg import GoalStatusArray
            self.register_subscription("nav_status", self.NAV_STATUS_TOPIC, GoalStatusArray, self._on_nav_status)
        except Exception:
            pass

        self._navigator = None
        self._navigator_lock = threading.RLock()

        self._dock_client = None
        self._undock_client = None

    def _get_navigator(self):
        with self._navigator_lock:
            if self._navigator is not None:
                return self._navigator
            try:
                from turtlebot4_navigation.turtlebot4_navigator import TurtleBot4Navigator
            except Exception as exc:
                raise RuntimeError(
                    "Nav2 navigator not available. Install turtlebot4_navigation and Nav2." 
                    f" Original error: {exc}"
                )
            self._navigator = TurtleBot4Navigator()
            return self._navigator

    def _env_float(self, name: str, default: float) -> float:
        try:
            return float(os.getenv(name, str(default)))
        except Exception:
            return default

    def _env_bool(self, name: str, default: bool = False) -> bool:
        raw = os.getenv(name)
        if raw is None:
            return default
        return raw.strip().lower() in {"1", "true", "yes", "on"}

    def _wait_for_nav2_active(
        self,
        navigator,
        cancel_event: threading.Event | None,
        timeout_s: float,
    ) -> None:
        if cancel_event is not None and cancel_event.is_set():
            raise RuntimeError("Cancelled")

        # Best effort: use a timeout parameter if the navigator supports it.
        for kw in ("timeout_sec", "timeout_s", "timeout"):
            try:
                navigator.waitUntilNav2Active(**{kw: timeout_s})
                return
            except TypeError:
                pass

        # Fallback: run the blocking call in a helper thread and enforce timeout.
        done = threading.Event()
        err: list[Exception] = []

        def _run() -> None:
            try:
                navigator.waitUntilNav2Active()
            except Exception as exc:
                err.append(exc)
            finally:
                done.set()

        t = threading.Thread(target=_run, name="nav2-wait", daemon=True)
        t.start()

        start = time.time()
        while not done.is_set():
            if cancel_event is not None and cancel_event.is_set():
                raise RuntimeError("Cancelled")
            if time.time() - start > timeout_s:
                raise TimeoutError("Nav2 not active (timeout)")
            time.sleep(0.1)

        if err:
            raise RuntimeError(f"Nav2 activation failed: {err[0]}")

    def _wait_task_complete(
        self,
        navigator,
        cancel_event: threading.Event | None,
        timeout_s: float,
    ) -> None:
        start = time.time()
        while not navigator.isTaskComplete():
            if cancel_event is not None and cancel_event.is_set():
                try:
                    navigator.cancelTask()
                except Exception:
                    pass
                return
            if time.time() - start > timeout_s:
                try:
                    navigator.cancelTask()
                except Exception:
                    pass
                raise TimeoutError("Nav2 task did not complete (timeout)")
            time.sleep(0.1)

    def _on_odom(self, msg) -> None:
        self._last_odom = msg

    def _on_battery(self, msg) -> None:
        self._last_battery = msg

    def _on_image(self, msg) -> None:
        self._last_image = msg

    def _on_map(self, msg) -> None:
        self._last_map = msg

    def _on_nav_status(self, msg) -> None:
        self._last_nav_status = msg

    def get_last_odom(self):
        return self._last_odom

    def get_last_battery(self):
        return self._last_battery

    def get_last_image(self):
        return self._last_image

    def get_last_image_base64(self) -> str:
        msg = self._last_image
        if msg is None:
            raise RuntimeError("No image received yet")

        # Cache: avoid repeatedly encoding the same ROS Image message instance.
        # Do NOT time-cache across different frames; users expect a fresh frame
        # after pressing the photo button.
        with self._image_cache_lock:
            if self._last_image_b64 is not None and self._last_image_id == id(msg):
                return self._last_image_b64

        height = int(getattr(msg, "height", 0) or 0)
        width = int(getattr(msg, "width", 0) or 0)
        encoding = (getattr(msg, "encoding", "") or "").lower()
        data = getattr(msg, "data", b"") or b""

        if height <= 0 or width <= 0 or not data:
            raise RuntimeError("Invalid image data")

        if encoding in {"rgb8", "bgr8"}:
            arr = np.frombuffer(data, dtype=np.uint8).reshape((height, width, 3))
            if encoding == "bgr8":
                arr = arr[:, :, ::-1]
            img = Image.fromarray(arr, mode="RGB")
        elif encoding in {"rgba8", "bgra8"}:
            arr = np.frombuffer(data, dtype=np.uint8).reshape((height, width, 4))
            if encoding == "bgra8":
                arr = arr[:, :, [2, 1, 0, 3]]
            img = Image.fromarray(arr, mode="RGBA").convert("RGB")
        elif encoding in {"mono8", "8uc1"}:
            arr = np.frombuffer(data, dtype=np.uint8).reshape((height, width))
            img = Image.fromarray(arr, mode="L")
        else:
            raise RuntimeError(f"Unsupported image encoding: {encoding}")

        # Reduce payload/CPU to keep the API responsive.
        try:
            max_w = int(os.getenv("PHOTO_MAX_WIDTH", "640") or "640")
        except Exception:
            max_w = 640
        try:
            jpeg_q = int(os.getenv("PHOTO_JPEG_QUALITY", "75") or "75")
        except Exception:
            jpeg_q = 75

        if max_w > 0 and img.width > max_w:
            scale = max_w / float(img.width)
            new_h = max(1, int(img.height * scale))
            img = img.resize((max_w, new_h))

        fmt = (os.getenv("PHOTO_FORMAT", "jpeg") or "jpeg").strip().lower()
        buf = io.BytesIO()
        if fmt in {"jpg", "jpeg"}:
            img.save(buf, format="JPEG", quality=jpeg_q, optimize=True)
            mime = "image/jpeg"
        else:
            img.save(buf, format="PNG")
            mime = "image/png"
        b64 = base64.b64encode(buf.getvalue()).decode("ascii")
        result = f"data:{mime};base64,{b64}"
        with self._image_cache_lock:
            self._last_image_b64 = result
            self._last_image_b64_time = time.time()
            self._last_image_id = id(msg)
        return result

    def get_last_map(self):
        return self._last_map

    def get_last_nav_status(self):
        return self._last_nav_status

    def get_docking_status(self) -> dict:
        # Prefer Create3 dock/undock actions (do not require Nav2/AMCL).
        mode = (os.getenv("DOCK_MODE", "create3") or "create3").strip().lower()
        if mode in {"create3", "action"}:
            try:
                self._ensure_dock_clients()
                ok = bool(self._dock_client.wait_for_server(timeout_sec=0.5)) and bool(
                    self._undock_client.wait_for_server(timeout_sec=0.5)
                )
                if ok:
                    return {"available": True, "mode": "create3_action"}
                return {"available": False, "mode": "create3_action", "reason": "Dock/Undock action server not available"}
            except Exception as exc:
                return {"available": False, "mode": "create3_action", "reason": str(exc)}

        # Fallback: Nav2 navigator-based docking (requires Nav2/AMCL).
        try:
            navigator = self._get_navigator()
        except Exception as exc:
            return {"available": False, "mode": "nav2", "reason": str(exc)}

        active_timeout = self._env_float("NAV2_ACTIVE_TIMEOUT_S", self.NAV2_ACTIVE_TIMEOUT_S)
        quick_timeout = min(2.0, float(active_timeout))

        try:
            self._wait_for_nav2_active(navigator, None, quick_timeout)
        except Exception as exc:
            return {"available": False, "mode": "nav2", "reason": f"Nav2 not active: {exc}"}

        return {"available": True, "mode": "nav2"}

    def _ensure_dock_clients(self) -> None:
        if self._dock_client is not None and self._undock_client is not None:
            return

        from rclpy.action import ActionClient  # type: ignore
        from irobot_create_msgs.action import Dock, Undock  # type: ignore

        node = self._publisher().get_node()
        dock_name = (os.getenv("CREATE3_DOCK_ACTION", "/dock") or "/dock").strip()
        undock_name = (os.getenv("CREATE3_UNDOCK_ACTION", "/undock") or "/undock").strip()

        self._dock_client = ActionClient(node, Dock, dock_name)
        self._undock_client = ActionClient(node, Undock, undock_name)

    def _wait_future(self, future, cancel_event: threading.Event | None, timeout_s: float):
        start = time.time()
        while not future.done():
            if cancel_event is not None and cancel_event.is_set():
                raise RuntimeError("Cancelled")
            if timeout_s and (time.time() - start) > timeout_s:
                raise TimeoutError("Timeout waiting for ROS2 action")
            time.sleep(0.05)
        return future.result()

    def _create3_dock_action(self, kind: str, cancel_event: threading.Event | None = None) -> None:
        self._ensure_dock_clients()

        timeout_s = self._env_float("DOCK_ACTION_TIMEOUT_S", 60.0)
        server_timeout_s = self._env_float("DOCK_SERVER_TIMEOUT_S", 2.0)

        if kind == "dock":
            client = self._dock_client
            from irobot_create_msgs.action import Dock  # type: ignore
            goal = Dock.Goal()
        else:
            client = self._undock_client
            from irobot_create_msgs.action import Undock  # type: ignore
            goal = Undock.Goal()

        if not client.wait_for_server(timeout_sec=float(server_timeout_s)):
            raise RuntimeError(f"{kind} action server not available")

        send_fut = client.send_goal_async(goal)
        goal_handle = self._wait_future(send_fut, cancel_event, timeout_s=timeout_s)
        if not getattr(goal_handle, "accepted", False):
            raise RuntimeError(f"{kind} goal rejected")

        result_fut = goal_handle.get_result_async()
        self._wait_future(result_fut, cancel_event, timeout_s=timeout_s)

    def execute_command(self, cmd: Command, cancel_event: threading.Event | None = None):
        if isinstance(cmd, StopCommand):
            self.stop()
            return

        # For movement commands (forward, turn), publish directly without waiting for Nav2.
        # Publish to the primary cmd_vel topic (Twist or TwistStamped) and optionally
        # mirror to /cmd_vel_unstamped as Twist.
        duration_s = 0.0

        if isinstance(cmd, ForwardCommand):
            linear_x = float(cmd.velocity)
            angular_z = 0.0
            duration_s = cmd.duration_s
        elif isinstance(cmd, TurnLeftCommand):
            linear_x = 0.0
            angular_z = float(cmd.angular_velocity)
            duration_s = cmd.duration_s
        elif isinstance(cmd, TurnRightCommand):
            linear_x = 0.0
            angular_z = -float(cmd.angular_velocity)
            duration_s = cmd.duration_s
        elif isinstance(cmd, NavigateToPoseCommand):
            self._navigate_to_pose(cmd, cancel_event)
            return
        elif isinstance(cmd, DockCommand):
            self._dock(cancel_event)
            return
        elif isinstance(cmd, UndockCommand):
            self._undock(cancel_event)
            return
        else:
            raise ValueError(f"Unsupported command: {type(cmd).__name__}")

        # Publish the movement command
        self._publish_cmd_vel_for(linear_x=linear_x, angular_z=angular_z, duration_s=duration_s, cancel_event=cancel_event)

    def stop(self):
        msg = self._new_cmd_vel_msg()
        self._set_cmd_vel(msg, linear_x=0.0, angular_z=0.0)
        self._publish(msg)

        if self._publish_unstamped and "cmd_vel_unstamped" in getattr(self, "_publishers", {}):
            try:
                from geometry_msgs.msg import Twist as TwistMsg  # type: ignore
                t = TwistMsg()
                t.linear.x = 0.0
                t.angular.z = 0.0
                self._publish(t, key="cmd_vel_unstamped")
            except Exception:
                pass

    def _publish_cmd_vel_for(
        self,
        linear_x: float,
        angular_z: float,
        duration_s: float,
        cancel_event: threading.Event | None = None,
    ) -> None:
        msg = self._new_cmd_vel_msg()
        self._set_cmd_vel(msg, linear_x=linear_x, angular_z=angular_z)

        unstamped = None
        if self._publish_unstamped and "cmd_vel_unstamped" in getattr(self, "_publishers", {}):
            try:
                from geometry_msgs.msg import Twist as TwistMsg  # type: ignore
                unstamped = TwistMsg()
                unstamped.linear.x = float(linear_x)
                unstamped.angular.z = float(angular_z)
            except Exception:
                unstamped = None

        end = time.time() + max(0.0, float(duration_s))
        if duration_s <= 0:
            self._publish(msg)
            if unstamped is not None:
                self._publish(unstamped, key="cmd_vel_unstamped")
            self.stop()
            return

        while time.time() < end:
            if cancel_event is not None and cancel_event.is_set():
                break
            self._publish(msg)
            if unstamped is not None:
                self._publish(unstamped, key="cmd_vel_unstamped")
            time.sleep(0.05)

        self.stop()

    def _new_cmd_vel_msg(self):
        if getattr(self, "_cmd_vel_kind", "Twist") == "TwistStamped":
            from geometry_msgs.msg import TwistStamped  # type: ignore
            return TwistStamped()
        return Twist()

    def _set_cmd_vel(self, msg, linear_x: float, angular_z: float) -> None:
        # Supports Twist and TwistStamped.
        if hasattr(msg, "twist"):
            msg.twist.linear.x = float(linear_x)
            msg.twist.angular.z = float(angular_z)
        else:
            msg.linear.x = float(linear_x)
            msg.angular.z = float(angular_z)

    def _navigate_to_pose(self, cmd: NavigateToPoseCommand, cancel_event: threading.Event | None = None) -> None:
        navigator = self._get_navigator()
        active_timeout = self._env_float("NAV2_ACTIVE_TIMEOUT_S", self.NAV2_ACTIVE_TIMEOUT_S)
        task_timeout = self._env_float("NAV2_TASK_TIMEOUT_S", self.NAV2_TASK_TIMEOUT_S)
        self._wait_for_nav2_active(navigator, cancel_event, active_timeout)
        goal_pose = navigator.getPoseStamped([cmd.x, cmd.y], cmd.yaw_deg)
        navigator.startToPose(goal_pose)
        self._wait_task_complete(navigator, cancel_event, task_timeout)

    def _dock(self, cancel_event: threading.Event | None = None) -> None:
        # Prefer simple Create3 docking action (no Nav2 needed).
        mode = (os.getenv("DOCK_MODE", "create3") or "create3").strip().lower()
        if mode in {"create3", "action"}:
            try:
                self._create3_dock_action("dock", cancel_event)
                return
            except Exception as exc:
                import logging
                logging.getLogger("backend.core.turtlebot").warning(
                    "Create3 dock action failed, falling back: %s", str(exc)
                )

        try:
            navigator = self._get_navigator()
            active_timeout = self._env_float("NAV2_ACTIVE_TIMEOUT_S", self.NAV2_ACTIVE_TIMEOUT_S)
            task_timeout = self._env_float("DOCK_TASK_TIMEOUT_S", self.DOCK_TASK_TIMEOUT_S)

            # Dock/undock in TurtleBot4Navigator typically depends on Nav2/AMCL.
            # If Nav2 isn't active, don't block the command queue for minutes.
            require_nav2 = self._env_bool("DOCK_REQUIRE_NAV2", False)
            try:
                self._wait_for_nav2_active(navigator, cancel_event, min(2.0, float(active_timeout)))
            except Exception as exc:
                if require_nav2:
                    raise
                import logging
                logging.getLogger("backend.core.turtlebot").warning(
                    "Dock skipped because Nav2 is not active: %s", str(exc)
                )
                return

            navigator.dock()
            self._wait_task_complete(navigator, cancel_event, task_timeout)
        except Exception as e:
            import logging
            logger = logging.getLogger("backend.core.turtlebot")
            logger.warning("Dock command failed (Nav2 may not be available): %s", str(e))
            # Don't raise - just log and continue

    def _undock(self, cancel_event: threading.Event | None = None) -> None:
        mode = (os.getenv("DOCK_MODE", "create3") or "create3").strip().lower()
        if mode in {"create3", "action"}:
            try:
                self._create3_dock_action("undock", cancel_event)
                return
            except Exception as exc:
                import logging
                logging.getLogger("backend.core.turtlebot").warning(
                    "Create3 undock action failed, falling back: %s", str(exc)
                )

        try:
            navigator = self._get_navigator()
            active_timeout = self._env_float("NAV2_ACTIVE_TIMEOUT_S", self.NAV2_ACTIVE_TIMEOUT_S)
            task_timeout = self._env_float("DOCK_TASK_TIMEOUT_S", self.DOCK_TASK_TIMEOUT_S)

            require_nav2 = self._env_bool("DOCK_REQUIRE_NAV2", False)
            try:
                self._wait_for_nav2_active(navigator, cancel_event, min(2.0, float(active_timeout)))
            except Exception as exc:
                if require_nav2:
                    raise
                import logging
                logging.getLogger("backend.core.turtlebot").warning(
                    "Undock skipped because Nav2 is not active: %s", str(exc)
                )
                return

            navigator.undock()
            self._wait_task_complete(navigator, cancel_event, task_timeout)
        except Exception as e:
            import logging
            logger = logging.getLogger("backend.core.turtlebot")
            logger.warning("Undock command failed (Nav2 may not be available): %s", str(e))
            # Don't raise - just log and continue