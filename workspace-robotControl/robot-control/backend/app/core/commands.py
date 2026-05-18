"""Command parser."""

from app.core.models.command import (
    DockCommand,
    ForwardCommand,
    NavigateToPoseCommand,
    StopCommand,
    TurnLeftCommand,
    TurnRightCommand,
    UndockCommand,
)


def parse_command(command_text: str):
    """Convert text to a command model.

    "forward 2.0" -> ForwardCommand(duration_s=2.0)
    "stop" -> StopCommand()
    """
    parts = command_text.strip().lower().split()
    
    if not parts:
        raise ValueError("Empty command")
    
    action = parts[0]
    
    if action == "stop":
        return StopCommand()

    if action == "dock":
        return DockCommand()

    if action == "undock":
        return UndockCommand()

    if action in {"nav", "goto", "pose", "navigate"}:
        if len(parts) < 3:
            raise ValueError("Navigation command requires x and y")
        x = float(parts[1])
        y = float(parts[2])
        yaw = float(parts[3]) if len(parts) > 3 else 0.0
        return NavigateToPoseCommand(x=x, y=y, yaw_deg=yaw)
    
    duration = float(parts[1]) if len(parts) > 1 else 1.0
    speed = float(parts[2]) if len(parts) > 2 else None

    if action == "forward":
        if speed is not None:
            return ForwardCommand(velocity=speed, duration_s=duration)
        return ForwardCommand(duration_s=duration)
    if action == "backward":
        # Backward is forward with negative velocity
        if speed is not None:
            return ForwardCommand(velocity=-abs(speed), duration_s=duration)
        return ForwardCommand(velocity=-1.0, duration_s=duration)
    if action == "left":
        if speed is not None:
            return TurnLeftCommand(angular_velocity=abs(speed), duration_s=duration)
        return TurnLeftCommand(duration_s=duration)
    if action == "right":
        if speed is not None:
            return TurnRightCommand(angular_velocity=abs(speed), duration_s=duration)
        return TurnRightCommand(duration_s=duration)

    raise ValueError(f"Unknown Action: {action}")
