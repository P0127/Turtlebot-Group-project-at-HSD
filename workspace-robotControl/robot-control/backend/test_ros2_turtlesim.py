"""Smoke test for ROS2 turtlesim publishing.

Usage (requires ROS2 environment where `import rclpy` works and turtlesim_node running):

1) In a ROS2 shell:
   ros2 run turtlesim turtlesim_node

2) In the same ROS2 shell (or one that can import rclpy):
   python test_ros2_turtlesim.py

This test publishes a short forward motion and then stops.
"""

from app.ros.ros2_manager import TwistCommand, get_turtlesim_publisher


def main() -> None:
    pub = get_turtlesim_publisher()
    pub.publish_for(TwistCommand(linear_x=1.0, angular_z=0.0, duration_s=1.0))
    pub.stop()
    print("ROS2 turtlesim publish smoke-test done")


if __name__ == "__main__":
    main()
