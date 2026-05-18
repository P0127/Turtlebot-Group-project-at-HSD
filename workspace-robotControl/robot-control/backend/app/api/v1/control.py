"""
Control API
"""
from fastapi import APIRouter, HTTPException, status

from pydantic import BaseModel
from app.core.controller import controller
from app.api.v1.intent_parser import parse_intent


router = APIRouter()


class CommandRequest(BaseModel):
    command: str

class STTRequest(BaseModel):
    original_text: str

class NavigateRequest(BaseModel):
    x: float
    y: float
    yaw_deg: float = 0.0


@router.post("/command")
def execute_command(request: CommandRequest):
    """POST /api/v1/control/command"""
    command_id = controller.enqueue_command(request.command)
    return {"status": "accepted", "command_id": command_id, "command": request.command}


@router.post("/navigate")
def navigate_to_pose(request: NavigateRequest):
    """POST /api/v1/control/navigate"""
    command_text = f"nav {request.x} {request.y} {request.yaw_deg}"
    command_id = controller.enqueue_command(command_text)
    return {"status": "accepted", "command_id": command_id, "command": command_text}

@router.post("/stt")
def handle_stt_command(request: STTRequest):
    """ POST /api/v1/control/stt """
    command = parse_intent(request.original_text)

    if not command:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Command could not be derived from STT text"
            )
    
    if command == "stop":
        controller.emergency_stop()
        return {"status": "stopped", "original_text": request.original_text, "command": command, "command_id": None}
    
    command_id = controller.enqueue_command(command)

    return {"status": "success","original_text": request.original_text,"command_id": command_id,"command": command}



@router.post("/stop")
def emergency_stop():
    """POST /api/v1/control/stop"""
    controller.emergency_stop()
    return {"status": "stopped"}


@router.get("/health")
def health():
    """GET /api/v1/control/health"""
    return {"status": "ok", **controller.health()}


@router.get("/photo")
def take_photo():
    """GET /api/v1/control/photo"""
    picture = controller.take_photo()
    return {
        "status": "success", 
        "photo": picture
    }

@router.get("/status")
def get_status():
    """GET /api/v1/control/status"""
    return controller.status()


@router.get("/map")
def get_map():
    """GET /api/v1/control/map"""
    return controller.get_map()


@router.get("/nav_status")
def get_nav_status():
    """GET /api/v1/control/nav_status"""
    return controller.get_nav_status()


@router.get("/battery")
def get_battery():
    """GET /api/v1/control/battery"""
    return controller.get_battery()


@router.get("/camera")
def get_camera():
    """GET /api/v1/control/camera"""
    return controller.get_camera_info()


@router.get("/dock_status")
def get_dock_status():
    """GET /api/v1/control/dock_status"""
    return controller.get_dock_status()

@router.post("/run_stt")
async def run_speech_to_text():
    try:
        # Runs the script and continues (doesn't wait for it to finish)
        # Use 'python3' if on Linux/Raspberry Pi
        subprocess.Popen(["python", "app/scripts/stt.py"]) 
        return {"status": "success", "message": "STT script started"}
    except Exception as e:
        return {"status": "error", "message": str(e)}