# Robot Control System

Backend + Web-UI zur Steuerung von ROS2-Robotern (TurtleBot/Create3 oder Turtlesim).

## Voraussetzungen

- ROS2 installiert und gesourct (z.B. `source /opt/ros/jazzy/setup.bash`)
- Python venv vorhanden: `/home/ros/ros/projects/takecontrol/.venv`
- Node.js (für Quasar UI)
- Für STT: `arecord` + Vosk Modell (Standard: `takecontrol/LM/vosk-model-de-0.21`)
- Für TTS: mindestens eins von: `pico2wave` + `paplay/aplay` **oder** `spd-say` **oder** `espeak/espeak-ng`

## Quickstart (Backend + UI)

Terminal A (Backend):

```bash
source /home/ros/ros/projects/takecontrol/.venv/bin/activate
python /home/ros/ros/projects/takecontrol/robot-control/backend/app/main.py
```

Terminal B (UI):

```bash
cd /home/ros/ros/projects/takecontrol/web-ui/quasar-project
npm install
npm run dev
```

Backend: http://127.0.0.1:8000/docs

## Backend starten (empfohlen)

### Real TurtleBot/Create3 (Linux)

Das Script lädt ROS2 + Workspace + venv:

```bash
/home/ros/ros/projects/takecontrol/robot-control/backend/run_backend.sh
```

### Turtlesim (Linux)

```bash
ros2 run turtlesim turtlesim_node

source /home/ros/ros/projects/takecontrol/.venv/bin/activate
export ROBOT_BACKEND=sim
python /home/ros/ros/projects/takecontrol/robot-control/backend/app/main.py
```

### Wichtig: Port 8000 schon belegt

Wenn du `address already in use` bekommst, läuft schon ein Backend. Prüfen:

```bash
ss -ltnp | grep ':8000'
```

## UI (Quasar)

```bash
cd /home/ros/ros/projects/takecontrol/web-ui/quasar-project
npm install
npm run dev
```

Die UI spricht standardmäßig das Backend unter `http://127.0.0.1:8000` an.

## STT → API → Bot (Vosk)

Ziel: Vosk erkennt Sprache → Script schickt **rohen Text** an `POST /api/v1/stt/execute` → Backend erkennt Intent + fährt + spricht Bestätigung.

### 1) Backend muss laufen

```bash
curl -s http://127.0.0.1:8000/api/v1/control/health
```

### 2) STT Live-Stream starten

```bash
source /home/ros/ros/projects/takecontrol/.venv/bin/activate
cd /home/ros/ros/projects/takecontrol/robot-control/backend/app/api/v1

# optional, falls Backend nicht lokal ist
export BACKEND_BASE_URL='http://127.0.0.1:8000'

# optional: Vosk Modellpfad
export STT_MODEL_PATH='/home/ros/ros/projects/takecontrol/LM/vosk-model-de-0.21'

python stt.py
```

### Audio "Gerät belegt" (PipeWire/WirePlumber)

Wenn `arecord` mit `Ressource ist belegt` abbricht: nutze **kein** `hw:*`, sondern ein PipeWire-freundliches Device:

```bash
export STT_DEVICE='default:CARD=ArrayUAC10'
python stt.py
```

Verfügbare Geräte anzeigen:

```bash
arecord -L
arecord -l
```

### STT ohne Mikro testen (HTTP)

```bash
curl -sS -X POST http://127.0.0.1:8000/api/v1/stt/execute \
  -H 'Content-Type: application/json' \
  -d '{"text":"fahre vorwärts"}'
```

## TTS (HTTP)

```bash
curl -sS -X POST http://127.0.0.1:8000/api/v1/tts/say \
  -H 'Content-Type: application/json' \
  -d '{"text":"Hallo, Testausgabe.","lang":"de-DE"}'
```

TTS-Settings (optional):

```bash
# auto | pico2wave | spd-say | espeak
export TTS_ENGINE=auto

# falls du einen Player erzwingen willst (z.B. "paplay" oder "aplay")
export TTS_PLAYER='paplay'

# abschalten
export TTS_ENABLED=0
```

## Steuer-API (Kurz)

- `POST /api/v1/control/command` Body: `{"command":"forward 1.0 0.5"}`
- `POST /api/v1/control/stop`
- `GET /api/v1/control/photo`
- `GET /api/v1/control/dock_status`

Swagger UI: http://127.0.0.1:8000/docs

## Docking / Undocking

Der Backend-Default ist **Create3 Actions** `/dock` und `/undock` (ohne Nav2/AMCL).

Status prüfen:

```bash
curl -s http://127.0.0.1:8000/api/v1/control/dock_status
```

## Kamera / Foto

Die Foto-Funktion nutzt ROS2 Image Topics (Standard):

- `/camera/image_raw`
- `/oakd/rgb/preview/image_raw`

Topics überschreiben:

```bash
export CAMERA_TOPIC=/dein/camera/topic
export OAKD_CAMERA_TOPIC=/dein/oakd/topic
```

Foto-Format (optional):

```bash
export PHOTO_FORMAT=jpeg   # oder png
export PHOTO_MAX_WIDTH=640
export PHOTO_JPEG_QUALITY=75
```