# TurtleBot Control Project

A system for controlling a TurtleBot, built with a FastAPI backend and a Quasar-based Web UI.

This project was a collective group effort, building upon and expanding a codebase originally established by students in previous years.

## My Contributions

Within the development group, my responsibilities focused on:

- **Web UI Development** — Building and styling the frontend components using the Quasar framework.
- **Full-Stack Integration** — Connecting the Quasar frontend with the Python backend.

---

## Project Structure

```
TurtleBot/
├── workspace-robotControl/
│   └── robot-control/
│       └── backend/          # FastAPI app, ROS2 managers, state services, audio (STT/TTS)
└── workspace-webUI/
    └── web-ui/
        └── quasar-project/   # Frontend web application
```

---

## Prerequisites

- Python 3.10+ (backend)
- Node.js v18+ (frontend)
- ROS2 environment (if running with physical or simulated robot components)

---

## Getting Started

### Backend

```bash
# 1. Navigate to the backend directory
cd workspace-robotControl/robot-control/backend

# 2. Create and activate a virtual environment
python -m venv venv

# On Windows:
venv\Scripts\activate
# On Linux/macOS:
source venv/bin/activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Configure environment variables
cp .env.example .env
# Edit .env and fill in any required local configuration keys

# 5. Start the server
python app/main.py
```

The API will be available at `http://localhost:8000` and interactive docs at `http://localhost:8000/docs`.

---

### Web UI

```bash
# 1. Navigate to the Quasar project directory
cd workspace-webUI/web-ui/quasar-project

# 2. Install dependencies
npm install

# 3. Start the development server
npm run dev
```

The interface will be available at `http://localhost:9000`.
