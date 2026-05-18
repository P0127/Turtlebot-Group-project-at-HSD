"""Command queue manager.

Purpose:
- Accept commands quickly via REST without blocking the request.
- Execute commands sequentially in a dedicated worker thread.
- Provide status information (busy/idle, current job, queue length, last error).
- Support emergency stop: cancel current command and clear the queue.

This module must not import ROS or robot backends directly.
It stays in the core layer and is controlled by the controller.
"""


import logging
import queue
import threading
import time
import uuid
from dataclasses import dataclass, asdict
from collections.abc import Callable

from rx.subject import Subject

logger = logging.getLogger("backend.core.command_queue")


@dataclass(frozen=True)
class QueuedCommand:
    """A command waiting in the queue (or currently executing)."""
    command_id: str
    command_text: str
    timestamp: float

@dataclass
class QueueStatus:
    state: str = "idle"  # "idle" | "busy" | "stopped"
    queue_length: int = 0

    current_command_id: str | None = None
    current_command: str | None = None
    current_timestamp: float | None = None

    processed_count: int = 0
    last_error: str | None = None


class CommandQueueManager:
    """Producer/consumer queue manager with a single worker thread.

        Requires two callables:
            - execute_fn(command_text, cancel_event): executes one command
            - stop_fn(): immediate stop for the robot (used for emergency stop)

        The queue manager handles:
            - ordering (FIFO)
            - threading
            - status tracking
            - cancellation requests (via cancel_event)
        """
    def __init__(
        self,
        execute_fn: Callable[[str, threading.Event], None],
        stop_fn: Callable[[], None],
        max_queue_size: int = 40,
        on_status: Callable[[dict], None] | None = None,
        on_event: Callable[[dict], None] | None = None,
    ) -> None:
        self._execute_fn = execute_fn
        self._stop_fn = stop_fn
        self._on_status = on_status
        self._on_event = on_event
        self._event_subject: Subject = Subject()

        self._queue: queue.Queue[QueuedCommand] = queue.Queue(maxsize=max_queue_size)
        self._status = QueueStatus()
        self._status_lock = threading.RLock()

        self._worker_thread : threading.Thread | None = None
        self._shutdown_event = threading.Event()
        self._cancel_current_event = threading.Event()

    """Lifecycle methods (start/shutdown)."""

    def start(self) -> None:
        """Start the background thread if not already running."""
        with self._status_lock:
            if self._worker_thread is not None and self._worker_thread.is_alive():
                return  # Already running
            
            # Ensure shutdown event is cleared.
            self._shutdown_event.clear()

            # Start the worker thread.
            self._worker_thread = threading.Thread(
                target=self._worker_loop, 
                name="CommandQueueWorker", 
                daemon=True)
            self._worker_thread.start()

    def shutdown(self, timeout_s: float = 2.0) -> None:
        """Stop the worker thread (used at application shutdown).
        Also cancels any running command and clears the queue.
        """
        # First, stop robot motion and cancel current command.
        self.emergency_stop(clear_queue=True)

        # Signal the worker loop to exit.
        self._shutdown_event.set()

        # Wait for the thread to finish.
        if self._worker_thread:
            self._worker_thread.join(timeout=timeout_s)

        # Update status to reflect that processing has stopped.
        with self._status_lock:
            self._status.state = "stopped"

    """Public API methods (enqueue, emergency_stop, get_status)."""

    def enqueue(self, command_text: str) -> str:
        """Add a new command to the queue.
        Returns the unique command ID.
        """
        logger.debug("enqueue called: %s", command_text)
        cmd_id = str(uuid.uuid4())
        queued_cmd = QueuedCommand(
            command_id=cmd_id,
            command_text=command_text,
            timestamp=time.time()
        )
        # Put into queue (may block if full).
        self._queue.put_nowait(queued_cmd)
        

        # Update status.
        with self._status_lock:
            self._status.queue_length = self._queue.qsize()
            if self._status.state == "stopped":
                self._status.state = "idle"
            status_snapshot = asdict(self._status)

        self._emit_status(status_snapshot)

        self._emit_event({
            "type": "queued",
            "command_id": queued_cmd.command_id,
            "command": queued_cmd.command_text,
            "timestamp": queued_cmd.timestamp,
        })

        return queued_cmd.command_id
    
    def emergency_stop(self, clear_queue: bool = True) -> None:
        """Cancel the current command and optionally clear the queue.
        also calls the stop_fn to halt the robot immediately.
        """
        logger.debug("emergency_stop called clear_queue=%s", clear_queue)
        # Cancel current command.
        self._cancel_current_event.set()

        # Clear pending commands if requested.
        if clear_queue:
            self._drain_queue()

        # Stop robot immediately.
        try:
            self._stop_fn()
        except Exception as e:
            with self._status_lock:
                self._status.last_error = f"stop_fn failed: {e}"

        # Update status.
        with self._status_lock:
            self._status.queue_length = self._queue.qsize()
            if self._status.current_command_id is None and self._status.state != "stopped":
                self._status.state = "idle"
            status_snapshot = asdict(self._status)

        self._emit_status(status_snapshot)
    

    def get_status(self) -> dict:
        """Return current status as a dictionary."""
        with self._status_lock:
            self._status.queue_length = self._queue.qsize()
            status_snapshot = asdict(self._status)

        return status_snapshot

    def event_subject(self) -> Subject:
        return self._event_subject

    def _emit_status(self, status: dict) -> None:
        if self._on_status is None:
            return
        try:
            self._on_status(status)
        except Exception:
            pass

    def _emit_event(self, event: dict) -> None:
        try:
            self._event_subject.on_next(event)
        except Exception:
            pass
        if self._on_event is None:
            return
        try:
            self._on_event(event)
        except Exception:
            pass
        
    """Internal methods."""
    def _drain_queue(self) -> None:
        """Remove all pending commands from the queue."""
        while not self._queue.empty():
            try:
                self._queue.get_nowait()
                self._queue.task_done()
            except queue.Empty:
                break
    
    def _worker_loop(self) -> None:
        """Background worker thread loop.
        - Waits for commands in the queue.
        - Executes them sequentially (FIFO).
        - Updates status information.
        - Respects shutdown and cancellation events.
        """
        while not self._shutdown_event.is_set():
            try:
                # Wait for the next command.
                queued_cmd = self._queue.get(timeout=0.5)
                
            except queue.Empty:
                with self._status_lock:
                    if self._status.current_command_id is None and self._status.state != "stopped":
                        self._status.state = "idle"
                        self._status.queue_length = self._queue.qsize()
                        status_snapshot = asdict(self._status)
                self._emit_status(status_snapshot)
                continue  

            # Update status to busy.
            with self._status_lock:
                self._status.state = "busy"
                self._status.current_command_id = queued_cmd.command_id
                self._status.current_command = queued_cmd.command_text
                self._status.current_timestamp = time.time()
                self._status.queue_length = self._queue.qsize()
                status_snapshot = asdict(self._status)

            self._emit_status(status_snapshot)

            # Fresh cancel event for this command.
            self._cancel_current_event.clear()

            start_ts = time.time()
            self._emit_event({
                "type": "started",
                "command_id": queued_cmd.command_id,
                "command": queued_cmd.command_text,
                "timestamp_start": start_ts,
            })

            # Execute the command.
            result = "ok"
            try:
                logger.debug("Executing command %s", queued_cmd.command_text)
                self._execute_fn(queued_cmd.command_text, self._cancel_current_event)
                if self._cancel_current_event.is_set():
                    result = "cancelled"
    
                with self._status_lock:
                    self._status.processed_count += 1
                    self._status.last_error = None
                    status_snapshot = asdict(self._status)
                self._emit_status(status_snapshot)
            except Exception as e:
                result = "error"
                with self._status_lock:
                    self._status.last_error = f"execute_fn failed: {e}"
                    status_snapshot = asdict(self._status)
                self._emit_status(status_snapshot)

            finally:
                self._queue.task_done()
               

            # Clear current command info.
            with self._status_lock:
                self._status.current_command_id = None
                self._status.current_command = None
                self._status.current_timestamp = None
                self._status.queue_length = self._queue.qsize()

                if self._queue.qsize() == 0 and not self._shutdown_event.is_set():
                    self._status.state = "idle"
                status_snapshot = asdict(self._status)

            self._emit_status(status_snapshot)

            end_ts = time.time()
            self._emit_event({
                "type": "finished",
                "command_id": queued_cmd.command_id,
                "command": queued_cmd.command_text,
                "timestamp_start": start_ts,
                "timestamp_end": end_ts,
                "duration_s": round(end_ts - start_ts, 4),
                "result": result,
            })