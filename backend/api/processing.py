"""Audio processing API endpoints."""
import json
import sys
import io
import threading
import asyncio
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
from fastapi import APIRouter, HTTPException, BackgroundTasks
from typing import List

from models.schemas import ProcessingStatus, ProjectMetadata

router = APIRouter()

DATA_DIR = Path(__file__).parent.parent.parent / "data"

# Store for capturing logs per session
_log_buffers = {}
_log_locks = {}


def get_session_dir(session_id: str) -> Path:
    return DATA_DIR / session_id


def get_log_buffer(session_id: str) -> List[str]:
    """Get or create log buffer for a session."""
    if session_id not in _log_buffers:
        _log_buffers[session_id] = []
        _log_locks[session_id] = threading.Lock()
    return _log_buffers[session_id]


def append_log(session_id: str, message: str):
    """Append a log message for a session."""
    if session_id not in _log_locks:
        _log_locks[session_id] = threading.Lock()
    if session_id not in _log_buffers:
        _log_buffers[session_id] = []

    with _log_locks[session_id]:
        # Keep last 200 lines
        _log_buffers[session_id].append(message)
        if len(_log_buffers[session_id]) > 200:
            _log_buffers[session_id] = _log_buffers[session_id][-200:]

    # Also save to file for persistence
    log_path = get_session_dir(session_id) / "processing.log"
    try:
        with open(log_path, "a") as f:
            f.write(message + "\n")
    except:
        pass


class LogCapture:
    """Context manager to capture print statements."""
    def __init__(self, session_id: str):
        self.session_id = session_id
        self.original_stdout = None
        self.original_stderr = None

    def __enter__(self):
        self.original_stdout = sys.stdout
        self.original_stderr = sys.stderr
        sys.stdout = LogWriter(self.session_id, self.original_stdout)
        sys.stderr = LogWriter(self.session_id, self.original_stderr)
        return self

    def __exit__(self, *args):
        sys.stdout = self.original_stdout
        sys.stderr = self.original_stderr


class LogWriter:
    """Custom writer that captures output and forwards to original stream."""
    def __init__(self, session_id: str, original_stream):
        self.session_id = session_id
        self.original_stream = original_stream
        self.buffer = ""

    def write(self, text):
        if self.original_stream:
            self.original_stream.write(text)
            self.original_stream.flush()  # Flush immediately

        # Buffer until we get a newline or carriage return (for progress bars)
        self.buffer += text

        # Handle both \n and \r (tqdm uses \r for progress bars)
        while "\n" in self.buffer or "\r" in self.buffer:
            # Find the first line terminator
            n_pos = self.buffer.find("\n")
            r_pos = self.buffer.find("\r")

            if n_pos == -1:
                split_pos = r_pos
            elif r_pos == -1:
                split_pos = n_pos
            else:
                split_pos = min(n_pos, r_pos)

            line = self.buffer[:split_pos]
            self.buffer = self.buffer[split_pos + 1:]

            if line.strip():
                append_log(self.session_id, line)

    def flush(self):
        if self.original_stream:
            self.original_stream.flush()
        # Also flush any remaining buffer content
        if self.buffer.strip():
            append_log(self.session_id, self.buffer)
            self.buffer = ""


def update_status(session_id: str, stage: str, progress: float, message: str, error: str = None):
    """Update processing status for a session."""
    session_dir = get_session_dir(session_id)
    status = {
        "stage": stage,
        "progress": progress,
        "message": message,
        "error": error
    }
    with open(session_dir / "status.json", "w") as f:
        json.dump(status, f)

    # Also log status updates
    append_log(session_id, f"[{stage}] {message}")


# Thread pool for running processing
_executor = ThreadPoolExecutor(max_workers=2)


def _run_vocal_separation(session_id: str, session_dir: Path):
    """Run only vocal separation in a thread."""
    from services.audio_processor import AudioProcessorService

    try:
        with LogCapture(session_id):
            # Load metadata
            with open(session_dir / "metadata.json") as f:
                metadata = json.load(f)

            # Find original file
            original_files = list(session_dir.glob("original.*"))
            if not original_files:
                raise Exception("Original audio file not found")
            original_path = original_files[0]

            # Stage 1: Vocal separation
            update_status(session_id, "vocal_separation", 0.0, "Starting vocal separation...")
            audio_service = AudioProcessorService()
            vocals_path = audio_service.separate_vocals(str(original_path), str(session_dir))
            update_status(session_id, "vocal_separation", 1.0, "Vocal separation complete")

            # Update metadata
            metadata["has_vocals"] = True
            metadata["processing_status"] = "vocals_ready"
            with open(session_dir / "metadata.json", "w") as f:
                json.dump(metadata, f, indent=2)

            update_status(session_id, "vocals_ready", 1.0, "Vocals ready! Select reference sections.")

        return {"status": "vocals_ready"}

    except Exception as e:
        append_log(session_id, f"ERROR: {str(e)}")
        update_status(session_id, "error", 0.0, str(e), error=str(e))
        return {"status": "error", "error": str(e)}


def _run_pitch_estimation(session_id: str, session_dir: Path):
    """Run pitch estimation in background (non-blocking)."""
    from services.pitch_estimator import PitchEstimatorService

    try:
        with LogCapture(session_id):
            vocals_path = session_dir / "vocals.wav"
            if not vocals_path.exists():
                raise Exception("Vocals file not found")

            # Load metadata
            with open(session_dir / "metadata.json") as f:
                metadata = json.load(f)

            print("\n[Background] Starting pitch estimation...")
            pitch_service = PitchEstimatorService()
            pitch_service.extract_full_pitch(str(vocals_path), session_dir)
            print("[Background] Pitch estimation complete")

            # Update metadata
            metadata["has_pitch"] = True
            with open(session_dir / "metadata.json", "w") as f:
                json.dump(metadata, f, indent=2)

        return {"status": "complete"}

    except Exception as e:
        append_log(session_id, f"[Background] Pitch estimation error: {str(e)}")
        return {"status": "error", "error": str(e)}


def _run_segmentation(session_id: str, session_dir: Path, call_references: List, response_references: List):
    """Run fingerprinting/segmentation with reference sections."""
    from services.fingerprinter import FingerprintingService

    try:
        with LogCapture(session_id):
            vocals_path = session_dir / "vocals.wav"
            if not vocals_path.exists():
                raise Exception("Vocals file not found")

            # Load metadata
            with open(session_dir / "metadata.json") as f:
                metadata = json.load(f)

            update_status(session_id, "fingerprinting", 0.0, "Detecting call/response sections...")
            fingerprint_service = FingerprintingService()

            # Convert references to tuples
            call_refs = [(r["start"], r["end"]) for r in call_references] if call_references else None
            response_refs = [(r["start"], r["end"]) for r in response_references] if response_references else None

            sections = fingerprint_service.detect_sections(
                str(vocals_path),
                session_dir,
                call_references=call_refs,
                response_references=response_refs
            )
            update_status(session_id, "fingerprinting", 1.0, f"Detected {len(sections)} sections")

            # Update metadata
            metadata["has_sections"] = True
            metadata["processing_status"] = "sections_ready"
            with open(session_dir / "metadata.json", "w") as f:
                json.dump(metadata, f, indent=2)

            update_status(session_id, "complete", 1.0, "Segmentation complete!")

        return {"status": "complete", "sections_count": len(sections)}

    except Exception as e:
        append_log(session_id, f"ERROR: {str(e)}")
        update_status(session_id, "error", 0.0, str(e), error=str(e))
        return {"status": "error", "error": str(e)}


@router.post("/sessions/{session_id}/process")
async def start_processing(session_id: str):
    """
    Start vocal separation and pitch estimation.

    Vocal separation runs first, then pitch estimation starts in background.
    Returns when vocals are ready so user can select reference sections.
    """
    session_dir = get_session_dir(session_id)
    if not session_dir.exists():
        raise HTTPException(status_code=404, detail="Session not found")

    # Clear previous logs
    if session_id in _log_buffers:
        _log_buffers[session_id] = []
    log_path = session_dir / "processing.log"
    if log_path.exists():
        log_path.unlink()

    # Initialize status
    update_status(session_id, "starting", 0.0, "Starting processing...")

    # Run vocal separation in thread pool
    loop = asyncio.get_event_loop()
    result = await loop.run_in_executor(_executor, _run_vocal_separation, session_id, session_dir)

    if result["status"] == "error":
        raise HTTPException(status_code=500, detail=f"Processing failed: {result.get('error', 'Unknown error')}")

    # Start pitch estimation in background (fire and forget)
    loop.run_in_executor(_executor, _run_pitch_estimation, session_id, session_dir)

    return {
        "status": "vocals_ready",
        "message": "Vocals separated. Pitch estimation running in background. Select reference sections."
    }


@router.post("/sessions/{session_id}/segment")
async def run_segmentation(session_id: str, references: dict = None):
    """
    Run segmentation with user-provided reference sections.

    Args:
        references: {
            "call_references": [{"start": float, "end": float}, ...],
            "response_references": [{"start": float, "end": float}, ...]
        }
        If no references provided, uses automatic pitch-based detection.
    """
    session_dir = get_session_dir(session_id)
    if not session_dir.exists():
        raise HTTPException(status_code=404, detail="Session not found")

    vocals_path = session_dir / "vocals.wav"
    if not vocals_path.exists():
        raise HTTPException(status_code=400, detail="Vocals not yet separated. Run processing first.")

    # Extract references
    call_refs = references.get("call_references", []) if references else []
    response_refs = references.get("response_references", []) if references else []

    # Run segmentation in thread pool
    loop = asyncio.get_event_loop()
    result = await loop.run_in_executor(
        _executor,
        _run_segmentation,
        session_id,
        session_dir,
        call_refs,
        response_refs
    )

    if result["status"] == "error":
        raise HTTPException(status_code=500, detail=f"Segmentation failed: {result.get('error', 'Unknown error')}")

    return {
        "status": "complete",
        "message": "Segmentation complete",
        "sections_count": result.get("sections_count", 0)
    }


@router.get("/sessions/{session_id}/logs")
async def get_processing_logs(session_id: str, since: int = 0):
    """
    Get processing logs for a session.

    Args:
        session_id: The session ID
        since: Return logs starting from this index (for polling)

    Returns:
        List of log lines and the current count
    """
    session_dir = get_session_dir(session_id)
    if not session_dir.exists():
        raise HTTPException(status_code=404, detail="Session not found")

    logs = get_log_buffer(session_id)

    # Return logs starting from 'since' index
    new_logs = logs[since:] if since < len(logs) else []

    return {
        "logs": new_logs,
        "total": len(logs),
        "since": since
    }


@router.post("/sessions/{session_id}/separate-vocals")
async def separate_vocals_only(session_id: str):
    """Run only vocal separation."""
    session_dir = get_session_dir(session_id)
    if not session_dir.exists():
        raise HTTPException(status_code=404, detail="Session not found")

    from services.audio_processor import AudioProcessorService

    original_files = list(session_dir.glob("original.*"))
    if not original_files:
        raise HTTPException(status_code=404, detail="Original audio file not found")

    update_status(session_id, "vocal_separation", 0.0, "Starting vocal separation...")
    audio_service = AudioProcessorService()
    vocals_path = audio_service.separate_vocals(str(original_files[0]), str(session_dir))
    update_status(session_id, "vocal_separation", 1.0, "Vocal separation complete")

    # Update metadata
    with open(session_dir / "metadata.json") as f:
        metadata = json.load(f)
    metadata["has_vocals"] = True
    with open(session_dir / "metadata.json", "w") as f:
        json.dump(metadata, f, indent=2)

    return {"status": "complete", "vocals_path": vocals_path}


@router.post("/sessions/{session_id}/detect-sections")
async def detect_sections(session_id: str):
    """Run fingerprinting to detect call/response sections."""
    session_dir = get_session_dir(session_id)
    if not session_dir.exists():
        raise HTTPException(status_code=404, detail="Session not found")

    vocals_path = session_dir / "vocals.wav"
    if not vocals_path.exists():
        raise HTTPException(status_code=400, detail="Vocals not yet separated. Run vocal separation first.")

    from services.fingerprinter import FingerprintingService

    update_status(session_id, "fingerprinting", 0.0, "Detecting sections...")
    fingerprint_service = FingerprintingService()
    sections = fingerprint_service.detect_sections(str(vocals_path), session_dir)
    update_status(session_id, "fingerprinting", 1.0, "Section detection complete")

    # Update metadata
    with open(session_dir / "metadata.json") as f:
        metadata = json.load(f)
    metadata["has_sections"] = True
    with open(session_dir / "metadata.json", "w") as f:
        json.dump(metadata, f, indent=2)

    return {"status": "complete", "sections_count": len(sections)}


@router.post("/sessions/{session_id}/estimate-pitch")
async def estimate_pitch(session_id: str):
    """Run pitch estimation on the full vocals track."""
    session_dir = get_session_dir(session_id)
    if not session_dir.exists():
        raise HTTPException(status_code=404, detail="Session not found")

    vocals_path = session_dir / "vocals.wav"

    if not vocals_path.exists():
        raise HTTPException(status_code=400, detail="Vocals not yet separated")

    from services.pitch_estimator import PitchEstimatorService

    update_status(session_id, "pitch_estimation", 0.0, "Estimating pitch...")
    pitch_service = PitchEstimatorService()
    result = pitch_service.extract_full_pitch(str(vocals_path), session_dir)
    update_status(session_id, "pitch_estimation", 1.0, "Pitch estimation complete")

    # Update metadata
    with open(session_dir / "metadata.json") as f:
        metadata = json.load(f)
    metadata["has_pitch"] = True
    with open(session_dir / "metadata.json", "w") as f:
        json.dump(metadata, f, indent=2)

    return {"status": "complete", **result}


@router.get("/sessions/{session_id}/status", response_model=ProcessingStatus)
async def get_processing_status(session_id: str):
    """Get current processing status for a session."""
    session_dir = get_session_dir(session_id)
    status_path = session_dir / "status.json"

    if not status_path.exists():
        return ProcessingStatus(stage="pending", progress=0.0, message="Not started")

    with open(status_path) as f:
        status = json.load(f)

    return ProcessingStatus(**status)


@router.get("/sessions/{session_id}/metadata", response_model=ProjectMetadata)
async def get_metadata(session_id: str):
    """Get session metadata."""
    session_dir = get_session_dir(session_id)
    metadata_path = session_dir / "metadata.json"

    if not metadata_path.exists():
        raise HTTPException(status_code=404, detail="Session not found")

    with open(metadata_path) as f:
        metadata = json.load(f)

    return ProjectMetadata(**metadata)
