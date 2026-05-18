"""
Application entrypoint
"""
from __future__ import annotations

import os
import sys
import uvicorn

# Ensure `python app/main.py` works by adding project root to sys.path
if __package__ is None or __package__ == "":
    current_dir = os.path.dirname(__file__)
    project_root = os.path.abspath(os.path.join(current_dir, ".."))
    if project_root not in sys.path:
        sys.path.insert(0, project_root)

from app.core.logging_config import setup_logging

# Default env so the app can start ohne manuelles Exportieren.
DEFAULT_ENV = {
    "ROBOT_BACKEND": "real",          # real TurtleBot statt sim
    "CMD_VEL_TOPIC": "/cmd_vel",      # Standard-Cmd-Vel Topic
    "CMD_VEL_MSG_TYPE": "TwistStamped",  # TurtleBot4 nutzt TwistStamped
    "INTENT_MODE": "parse",       # "parse" oder "function_calling"
}
for _k, _v in DEFAULT_ENV.items():
    os.environ.setdefault(_k, _v)

from app.api.app import create_api_app


setup_logging()
app = create_api_app()


def start_server():
    # Reload + ROS2 (rclpy) is fragile; allow opt-in via env.
    reload_enabled = os.getenv("BACKEND_RELOAD", "0").strip() in {"1", "true", "yes", "on"}
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=reload_enabled,
    )

if __name__ == "__main__":
    start_server()
