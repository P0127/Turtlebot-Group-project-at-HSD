"""
Turtlesim Backend
"""
import threading
from geometry_msgs.msg import Twist
from turtlesim.msg import Pose

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


class TurtlesimRobot(RosRobotBase):

    CMD_VEL_TOPIC = "/turtle1/cmd_vel"
    POSE_TOPIC = "/turtle1/pose"

    def __init__(self) -> None:
        super().__init__(self.CMD_VEL_TOPIC, Twist)
        self._last_pose: Pose | None = None
        self.register_subscription("pose", self.POSE_TOPIC, Pose, self._on_pose)

    def _on_pose(self, msg: Pose) -> None:
        self._last_pose = msg

    def get_last_pose(self) -> Pose | None:
        return self._last_pose

    def execute_command(self, cmd: Command, cancel_event: threading.Event | None = None):
        if isinstance(cmd, StopCommand):
            self.stop()
            return

        msg = Twist()
        duration_s = 0.0

        if isinstance(cmd, ForwardCommand):
            msg.linear.x = float(cmd.velocity)
            msg.angular.z = 0.0
            duration_s = cmd.duration_s
        elif isinstance(cmd, TurnLeftCommand):
            msg.linear.x = 0.0
            msg.angular.z = float(cmd.angular_velocity)
            duration_s = cmd.duration_s
        elif isinstance(cmd, TurnRightCommand):
            msg.linear.x = 0.0
            msg.angular.z = -float(cmd.angular_velocity)
            duration_s = cmd.duration_s
        elif isinstance(cmd, NavigateToPoseCommand):
            raise ValueError("Navigation is not supported by turtlesim")
        elif isinstance(cmd, DockCommand):
            # Docking is not physically possible in turtlesim, just log it
            return
        elif isinstance(cmd, UndockCommand):
            # Undocking is not physically possible in turtlesim, just log it
            return
        else:
            raise ValueError(f"Unsupported command: {type(cmd).__name__}")

        self._publish_for(msg, duration_s, cancel_event)

    def stop(self):
        msg = Twist()
        msg.linear.x = 0.0
        msg.angular.z = 0.0
        self._publish(msg)
