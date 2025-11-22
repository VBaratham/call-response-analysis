"""File upload API endpoints."""
import uuid
import shutil
from pathlib import Path
from fastapi import APIRouter, UploadFile, File, HTTPException
import librosa

from models.schemas import UploadResponse, AudioInfo

router = APIRouter()

DATA_DIR = Path(__file__).parent.parent.parent / "data"


def get_session_dir(session_id: str) -> Path:
    """Get the directory for a session."""
    return DATA_DIR / session_id


@router.post("/upload", response_model=UploadResponse)
async def upload_audio(file: UploadFile = File(...)):
    """
    Upload an audio file to start a new analysis session.

    Accepts common audio formats: wav, mp3, flac, ogg, m4a
    """
    # Validate file extension
    allowed_extensions = {".wav", ".mp3", ".flac", ".ogg", ".m4a", ".aiff"}
    file_ext = Path(file.filename).suffix.lower()
    if file_ext not in allowed_extensions:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file format. Allowed: {', '.join(allowed_extensions)}"
        )

    # Create session
    session_id = str(uuid.uuid4())[:8]
    session_dir = get_session_dir(session_id)
    session_dir.mkdir(parents=True, exist_ok=True)

    # Save uploaded file
    original_path = session_dir / f"original{file_ext}"
    try:
        with open(original_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
    except Exception as e:
        shutil.rmtree(session_dir, ignore_errors=True)
        raise HTTPException(status_code=500, detail=f"Failed to save file: {str(e)}")

    # Get audio info using librosa (supports more formats including m4a)
    try:
        # Load just enough to get duration and sample rate
        y, sr = librosa.load(str(original_path), sr=None, mono=False, duration=1.0)
        # Get full duration without loading entire file
        duration = librosa.get_duration(path=str(original_path))
        channels = 1 if len(y.shape) == 1 else y.shape[0]
    except Exception as e:
        shutil.rmtree(session_dir, ignore_errors=True)
        raise HTTPException(status_code=400, detail=f"Could not read audio file: {str(e)}")

    # Save metadata
    import json
    metadata = {
        "session_id": session_id,
        "original_filename": file.filename,
        "duration": duration,
        "sample_rate": sr,
        "channels": channels,
        "processing_status": "uploaded"
    }
    with open(session_dir / "metadata.json", "w") as f:
        json.dump(metadata, f, indent=2)

    return UploadResponse(
        session_id=session_id,
        filename=file.filename,
        duration=duration,
        message="File uploaded successfully. Ready for processing."
    )


@router.get("/sessions/{session_id}/audio-info", response_model=AudioInfo)
async def get_audio_info(session_id: str):
    """Get information about the uploaded audio file."""
    session_dir = get_session_dir(session_id)
    metadata_path = session_dir / "metadata.json"

    if not metadata_path.exists():
        raise HTTPException(status_code=404, detail="Session not found")

    import json
    with open(metadata_path) as f:
        metadata = json.load(f)

    # Determine which audio file to serve (prefer vocals if available)
    vocals_path = session_dir / "vocals.wav"
    if vocals_path.exists():
        waveform_url = f"/audio/{session_id}/vocals.wav"
    else:
        # Find original file
        original_files = list(session_dir.glob("original.*"))
        if not original_files:
            raise HTTPException(status_code=404, detail="Audio file not found")
        waveform_url = f"/audio/{session_id}/{original_files[0].name}"

    return AudioInfo(
        duration=metadata["duration"],
        sample_rate=metadata["sample_rate"],
        channels=metadata.get("channels", 2),
        waveform_url=waveform_url
    )


@router.delete("/sessions/{session_id}")
async def delete_session(session_id: str):
    """Delete a session and all its data."""
    session_dir = get_session_dir(session_id)
    if not session_dir.exists():
        raise HTTPException(status_code=404, detail="Session not found")

    shutil.rmtree(session_dir)
    return {"message": "Session deleted successfully"}


@router.get("/sessions")
async def list_sessions():
    """List all available sessions."""
    sessions = []
    for session_dir in DATA_DIR.iterdir():
        if session_dir.is_dir():
            metadata_path = session_dir / "metadata.json"
            if metadata_path.exists():
                import json
                with open(metadata_path) as f:
                    metadata = json.load(f)
                sessions.append(metadata)
    return {"sessions": sessions}


SAMPLES_DIR = Path(__file__).parent.parent.parent / "samples"


@router.get("/sample/om-namah-shivaya")
async def use_sample_file():
    """
    Create a session using the Om Namah Shivaya sample file.
    The sample file should be placed at samples/om_namah_shivaya.m4a
    """
    import json

    # Look for sample file
    sample_patterns = ["om_namah_shivaya.*", "om-namah-shivaya.*", "OmNamahShivaya.*"]
    sample_file = None

    for pattern in sample_patterns:
        matches = list(SAMPLES_DIR.glob(pattern)) if SAMPLES_DIR.exists() else []
        if matches:
            sample_file = matches[0]
            break

    if not sample_file or not sample_file.exists():
        raise HTTPException(
            status_code=404,
            detail=f"Sample file not found. Place an audio file named 'om_namah_shivaya.m4a' in {SAMPLES_DIR}"
        )

    # Create session
    session_id = str(uuid.uuid4())[:8]
    session_dir = get_session_dir(session_id)
    session_dir.mkdir(parents=True, exist_ok=True)

    # Copy sample file
    file_ext = sample_file.suffix.lower()
    original_path = session_dir / f"original{file_ext}"
    shutil.copy(sample_file, original_path)

    # Get audio info
    try:
        y, sr = librosa.load(str(original_path), sr=None, mono=False, duration=1.0)
        duration = librosa.get_duration(path=str(original_path))
        channels = 1 if len(y.shape) == 1 else y.shape[0]
    except Exception as e:
        shutil.rmtree(session_dir, ignore_errors=True)
        raise HTTPException(status_code=400, detail=f"Could not read sample file: {str(e)}")

    # Save metadata
    metadata = {
        "session_id": session_id,
        "original_filename": sample_file.name,
        "duration": duration,
        "sample_rate": sr,
        "channels": channels,
        "processing_status": "uploaded"
    }
    with open(session_dir / "metadata.json", "w") as f:
        json.dump(metadata, f, indent=2)

    return {
        "session_id": session_id,
        "filename": sample_file.name,
        "duration": duration,
        "message": "Sample file loaded. Ready for processing."
    }
