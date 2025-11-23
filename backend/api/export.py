"""Project export/import API endpoints."""
import json
import zipfile
import tempfile
import subprocess
from pathlib import Path
from datetime import datetime
from io import BytesIO
from fastapi import APIRouter, HTTPException, UploadFile, File
from fastapi.responses import JSONResponse, StreamingResponse

from models.schemas import ProjectExport

router = APIRouter()

DATA_DIR = Path(__file__).parent.parent.parent / "data"


def get_session_dir(session_id: str) -> Path:
    return DATA_DIR / session_id


def compress_audio_to_mp3(wav_path: Path, mp3_path: Path, bitrate: str = "128k"):
    """Compress WAV to MP3 using ffmpeg."""
    try:
        subprocess.run([
            "ffmpeg", "-y", "-i", str(wav_path),
            "-codec:a", "libmp3lame", "-b:a", bitrate,
            str(mp3_path)
        ], check=True, capture_output=True)
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        return False


def convert_mp3_to_wav(mp3_path: Path, wav_path: Path):
    """Convert MP3 back to WAV using ffmpeg."""
    try:
        subprocess.run([
            "ffmpeg", "-y", "-i", str(mp3_path),
            "-codec:a", "pcm_s16le", "-ar", "44100",
            str(wav_path)
        ], check=True, capture_output=True)
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        return False


@router.get("/sessions/{session_id}/export")
async def export_project(session_id: str):
    """
    Export complete project as a zip file containing:
    - project.json: metadata, sections, and alignments
    - vocals.mp3: compressed vocals audio (if available)
    """
    session_dir = get_session_dir(session_id)
    if not session_dir.exists():
        raise HTTPException(status_code=404, detail="Session not found")

    # Load metadata
    metadata_path = session_dir / "metadata.json"
    if not metadata_path.exists():
        raise HTTPException(status_code=404, detail="Metadata not found")

    with open(metadata_path) as f:
        metadata = json.load(f)

    # Load sections
    sections_path = session_dir / "sections.json"
    sections = []
    if sections_path.exists():
        with open(sections_path) as f:
            sections = json.load(f)

    # Load alignments
    alignments_path = session_dir / "alignments.json"
    alignments = []
    if alignments_path.exists():
        with open(alignments_path) as f:
            alignments = json.load(f)

    # Create project data
    project_data = {
        "version": "2.0",
        "exported_at": datetime.utcnow().isoformat(),
        "metadata": metadata,
        "sections": sections,
        "alignments": alignments,
        "has_vocals_audio": False
    }

    # Create zip file in memory
    zip_buffer = BytesIO()
    with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zf:
        # Check for vocals and compress to MP3
        vocals_path = session_dir / "vocals.wav"
        if vocals_path.exists():
            with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as tmp:
                tmp_mp3 = Path(tmp.name)

            if compress_audio_to_mp3(vocals_path, tmp_mp3):
                zf.write(tmp_mp3, "vocals.mp3")
                project_data["has_vocals_audio"] = True
                tmp_mp3.unlink()
            else:
                # Fallback: include wav if ffmpeg not available
                zf.write(vocals_path, "vocals.wav")
                project_data["has_vocals_audio"] = True

        # Add project JSON
        zf.writestr("project.json", json.dumps(project_data, indent=2))

    zip_buffer.seek(0)

    filename = f"{metadata.get('original_filename', session_id).rsplit('.', 1)[0]}_project.zip"

    return StreamingResponse(
        zip_buffer,
        media_type="application/zip",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"'
        }
    )


@router.post("/sessions/{session_id}/import")
async def import_project(session_id: str, file: UploadFile = File(...)):
    """
    Import project data from a previously exported file.

    Accepts either:
    - .zip file (new format with vocals audio)
    - .json file (legacy format without audio)
    """
    session_dir = get_session_dir(session_id)
    if not session_dir.exists():
        raise HTTPException(status_code=404, detail="Session not found")

    content = await file.read()
    filename = file.filename or ""

    # Determine file type and parse accordingly
    if filename.endswith(".zip") or content[:4] == b'PK\x03\x04':
        # ZIP file format
        try:
            with zipfile.ZipFile(BytesIO(content), 'r') as zf:
                # Extract project.json
                if "project.json" not in zf.namelist():
                    raise HTTPException(status_code=400, detail="Invalid project zip: missing project.json")

                project_json = zf.read("project.json")
                import_data = json.loads(project_json)

                # Extract vocals audio if present
                if "vocals.mp3" in zf.namelist():
                    with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as tmp:
                        tmp.write(zf.read("vocals.mp3"))
                        tmp_mp3 = Path(tmp.name)

                    vocals_wav = session_dir / "vocals.wav"
                    if convert_mp3_to_wav(tmp_mp3, vocals_wav):
                        import_data["_has_vocals"] = True
                    tmp_mp3.unlink()

                elif "vocals.wav" in zf.namelist():
                    vocals_wav = session_dir / "vocals.wav"
                    with open(vocals_wav, "wb") as f:
                        f.write(zf.read("vocals.wav"))
                    import_data["_has_vocals"] = True

        except zipfile.BadZipFile:
            raise HTTPException(status_code=400, detail="Invalid zip file")
    else:
        # Legacy JSON format
        try:
            import_data = json.loads(content)
        except json.JSONDecodeError:
            raise HTTPException(status_code=400, detail="Invalid JSON file")

    # Validate structure
    if "sections" not in import_data:
        raise HTTPException(status_code=400, detail="Missing 'sections' in import data")

    # Import sections
    sections = import_data.get("sections", [])
    with open(session_dir / "sections.json", "w") as f:
        json.dump(sections, f, indent=2)

    # Import alignments
    alignments = import_data.get("alignments", [])
    with open(session_dir / "alignments.json", "w") as f:
        json.dump(alignments, f, indent=2)

    # Update metadata
    metadata_path = session_dir / "metadata.json"
    if metadata_path.exists():
        with open(metadata_path) as f:
            metadata = json.load(f)

        metadata["has_sections"] = len(sections) > 0
        metadata["imported_from"] = import_data.get("metadata", {}).get("original_filename", "unknown")

        # Mark vocals as available if imported
        if import_data.get("_has_vocals"):
            metadata["has_vocals"] = True

        with open(metadata_path, "w") as f:
            json.dump(metadata, f, indent=2)

    return {
        "message": "Project imported successfully",
        "sections_count": len(sections),
        "alignments_count": len(alignments),
        "has_vocals": import_data.get("_has_vocals", False)
    }


@router.get("/sessions/{session_id}/export/sections")
async def export_sections_only(session_id: str):
    """Export just the sections data."""
    session_dir = get_session_dir(session_id)
    sections_path = session_dir / "sections.json"

    if not sections_path.exists():
        raise HTTPException(status_code=404, detail="No sections found")

    with open(sections_path) as f:
        sections = json.load(f)

    return JSONResponse(
        content={"sections": sections},
        headers={
            "Content-Disposition": f'attachment; filename="{session_id}_sections.json"'
        }
    )


@router.get("/sessions/{session_id}/export/alignments")
async def export_alignments_only(session_id: str):
    """Export just the alignments data."""
    session_dir = get_session_dir(session_id)
    alignments_path = session_dir / "alignments.json"

    if not alignments_path.exists():
        raise HTTPException(status_code=404, detail="No alignments found")

    with open(alignments_path) as f:
        alignments = json.load(f)

    return JSONResponse(
        content={"alignments": alignments},
        headers={
            "Content-Disposition": f'attachment; filename="{session_id}_alignments.json"'
        }
    )
