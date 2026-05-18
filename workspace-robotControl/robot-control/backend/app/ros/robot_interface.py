"""Abstract robot interface.
Each backend must implement these methods.
"""
from abc import ABC, abstractmethod
import threading

from app.core.models.command import Command


class RobotInterface(ABC):
    
    @abstractmethod
    def execute_command(self, cmd: Command, cancel_event: threading.Event | None = None):
        """Execute a high-level command model."""
        raise NotImplementedError
    
    @abstractmethod
    def stop(self):
        """Stop the robot."""
        raise NotImplementedError
