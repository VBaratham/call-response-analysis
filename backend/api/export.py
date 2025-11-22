"""Project export/import API endpoints."""
import json
from pathlib import Path
from datetime import datetime
from fastapi import APIRouter, HTTPException, UploadFile, File
from fastapi.responses import JSONResponse

from models.schemas import ProjectExport

router = APIRouter()

DATA_DIR = Path(__file__).parent.parent.parent / "data"


def get_session_dir(session_id: str) -> Path:
    return DATA_DIR / session_id


@router.get("/sessions/{session_id}/export")
async def export_project(session_id: str):
    """
    Export complete project data as JSON.

    Includes metadata, sections, and alignments.
    Can be used to resume work later.
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

    export_data = {
        "version": "1.0",
        "exported_at": datetime.utcnow().isoformat(),
        "metadata": metadata,
        "sections": sections,
        "alignments": alignments
    }

    return JSONResponse(
        content=export_data,
        headers={
            "Content-Disposition": f'attachment; filename="{session_id}_project.json"'
        }
    )


@router.post("/sessions/{session_id}/import")
async def import_project(session_id: str, file: UploadFile = File(...)):
    """
    Import project data from a previously exported JSON file.

    This will overwrite existing sections and alignments.
    """
    session_dir = get_session_dir(session_id)
    if not session_dir.exists():
        raise HTTPException(status_code=404, detail="Session not found")

    try:
        content = await file.read()
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

    # Update metadata to reflect import
    metadata_path = session_dir / "metadata.json"
    if metadata_path.exists():
        with open(metadata_path) as f:
            metadata = json.load(f)
        metadata["has_sections"] = len(sections) > 0
        metadata["imported_from"] = import_data.get("metadata", {}).get("original_filename", "unknown")
        with open(metadata_path, "w") as f:
            json.dump(metadata, f, indent=2)

    return {
        "message": "Project imported successfully",
        "sections_count": len(sections),
        "alignments_count": len(alignments)
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
