#!/bin/bash
# Run backend with proper ROS2 environment setup

set -e

# Source ROS2 environment
source /opt/ros/jazzy/setup.bash

# Source the workspace if it exists
if [ -f "/home/ros/ros/install/setup.bash" ]; then
    source /home/ros/ros/install/setup.bash
fi

# Activate Python virtual environment
source /home/ros/ros/projects/takecontrol/.venv/bin/activate

# Change to backend directory
cd "$(dirname "$0")"

# Set robot backend to real TurtleBot
export ROBOT_BACKEND=real

# Run the backend
python app/main.py
