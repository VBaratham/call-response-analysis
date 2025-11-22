"""Sections CRUD API endpoints."""
import json
import uuid
from pathlib import Path
from typing import List
from fastapi import APIRouter, HTTPException

from models.schemas import Section, SectionCreate, SectionUpdate, SectionLabel

router = APIRouter()

DATA_DIR = Path(__file__).parent.parent.parent / "data"


def get_session_dir(session_id: str) -> Path:
    return DATA_DIR / session_id


def load_sections(session_id: str) -> List[dict]:
    """Load sections from file."""
    sections_path = get_session_dir(session_id) / "sections.json"
    if not sections_path.exists():
        return []
    with open(sections_path) as f:
        return json.load(f)


def save_sections(session_id: str, sections: List[dict]):
    """Save sections to file."""
    sections_path = get_session_dir(session_id) / "sections.json"
    with open(sections_path, "w") as f:
        json.dump(sections, f, indent=2)


@router.get("/sessions/{session_id}/sections", response_model=List[Section])
async def get_sections(session_id: str):
    """Get all sections for a session."""
    session_dir = get_session_dir(session_id)
    if not session_dir.exists():
        raise HTTPException(status_code=404, detail="Session not found")

    sections = load_sections(session_id)
    return sections


@router.post("/sessions/{session_id}/sections", response_model=Section)
async def create_section(session_id: str, section: SectionCreate):
    """Create a new section."""
    session_dir = get_session_dir(session_id)
    if not session_dir.exists():
        raise HTTPException(status_code=404, detail="Session not found")

    sections = load_sections(session_id)

    # Validate times
    if section.end <= section.start:
        raise HTTPException(status_code=400, detail="End time must be after start time")

    # Generate ID
    new_section = {
        "id": f"section_{uuid.uuid4().hex[:8]}",
        "start": section.start,
        "end": section.end,
        "label": section.label.value,
        "is_reference": section.is_reference,
        "confidence": None
    }

    sections.append(new_section)
    sections.sort(key=lambda s: s["start"])
    save_sections(session_id, sections)

    return new_section


@router.put("/sessions/{session_id}/sections/{section_id}", response_model=Section)
async def update_section(session_id: str, section_id: str, update: SectionUpdate):
    """Update a section."""
    session_dir = get_session_dir(session_id)
    if not session_dir.exists():
        raise HTTPException(status_code=404, detail="Session not found")

    sections = load_sections(session_id)
    section_idx = next((i for i, s in enumerate(sections) if s["id"] == section_id), None)

    if section_idx is None:
        raise HTTPException(status_code=404, detail="Section not found")

    section = sections[section_idx]

    # Apply updates
    if update.start is not None:
        section["start"] = update.start
    if update.end is not None:
        section["end"] = update.end
    if update.label is not None:
        section["label"] = update.label.value
    if update.is_reference is not None:
        section["is_reference"] = update.is_reference

    # Validate
    if section["end"] <= section["start"]:
        raise HTTPException(status_code=400, detail="End time must be after start time")

    sections[section_idx] = section
    sections.sort(key=lambda s: s["start"])
    save_sections(session_id, sections)

    return section


@router.delete("/sessions/{session_id}/sections/{section_id}")
async def delete_section(session_id: str, section_id: str):
    """Delete a section."""
    session_dir = get_session_dir(session_id)
    if not session_dir.exists():
        raise HTTPException(status_code=404, detail="Session not found")

    sections = load_sections(session_id)
    original_len = len(sections)
    sections = [s for s in sections if s["id"] != section_id]

    if len(sections) == original_len:
        raise HTTPException(status_code=404, detail="Section not found")

    save_sections(session_id, sections)
    return {"message": "Section deleted"}


@router.post("/sessions/{session_id}/sections/{section_id}/toggle-label", response_model=Section)
async def toggle_section_label(session_id: str, section_id: str):
    """Toggle a section's label between call and response."""
    session_dir = get_session_dir(session_id)
    if not session_dir.exists():
        raise HTTPException(status_code=404, detail="Session not found")

    sections = load_sections(session_id)
    section_idx = next((i for i, s in enumerate(sections) if s["id"] == section_id), None)

    if section_idx is None:
        raise HTTPException(status_code=404, detail="Section not found")

    section = sections[section_idx]
    section["label"] = "response" if section["label"] == "call" else "call"
    sections[section_idx] = section
    save_sections(session_id, sections)

    return section


@router.post("/sessions/{session_id}/sections/{section_id}/split", response_model=List[Section])
async def split_section(session_id: str, section_id: str, split_time: float):
    """Split a section at a given time."""
    session_dir = get_session_dir(session_id)
    if not session_dir.exists():
        raise HTTPException(status_code=404, detail="Session not found")

    sections = load_sections(session_id)
    section_idx = next((i for i, s in enumerate(sections) if s["id"] == section_id), None)

    if section_idx is None:
        raise HTTPException(status_code=404, detail="Section not found")

    section = sections[section_idx]

    if split_time <= section["start"] or split_time >= section["end"]:
        raise HTTPException(status_code=400, detail="Split time must be within section bounds")

    # Create two new sections
    first_section = {
        "id": f"section_{uuid.uuid4().hex[:8]}",
        "start": section["start"],
        "end": split_time,
        "label": section["label"],
        "is_reference": False,
        "confidence": None
    }
    second_section = {
        "id": f"section_{uuid.uuid4().hex[:8]}",
        "start": split_time,
        "end": section["end"],
        "label": section["label"],
        "is_reference": False,
        "confidence": None
    }

    # Replace original with two new sections
    sections[section_idx] = first_section
    sections.insert(section_idx + 1, second_section)
    save_sections(session_id, sections)

    return [first_section, second_section]


@router.post("/sessions/{session_id}/sections/merge", response_model=Section)
async def merge_sections(session_id: str, section_ids: List[str]):
    """Merge multiple sections into one."""
    session_dir = get_session_dir(session_id)
    if not session_dir.exists():
        raise HTTPException(status_code=404, detail="Session not found")

    if len(section_ids) < 2:
        raise HTTPException(status_code=400, detail="Need at least 2 sections to merge")

    sections = load_sections(session_id)

    # Find sections to merge
    to_merge = [s for s in sections if s["id"] in section_ids]
    if len(to_merge) != len(section_ids):
        raise HTTPException(status_code=404, detail="One or more sections not found")

    # Sort by start time
    to_merge.sort(key=lambda s: s["start"])

    # Create merged section
    merged = {
        "id": f"section_{uuid.uuid4().hex[:8]}",
        "start": to_merge[0]["start"],
        "end": to_merge[-1]["end"],
        "label": to_merge[0]["label"],  # Use first section's label
        "is_reference": any(s.get("is_reference", False) for s in to_merge),
        "confidence": None
    }

    # Remove old sections, add merged
    sections = [s for s in sections if s["id"] not in section_ids]
    sections.append(merged)
    sections.sort(key=lambda s: s["start"])
    save_sections(session_id, sections)

    return merged


@router.put("/sessions/{session_id}/sections", response_model=List[Section])
async def replace_all_sections(session_id: str, sections: List[SectionCreate]):
    """Replace all sections (for bulk updates like undo/redo)."""
    session_dir = get_session_dir(session_id)
    if not session_dir.exists():
        raise HTTPException(status_code=404, detail="Session not found")

    new_sections = []
    for i, section in enumerate(sections):
        new_sections.append({
            "id": f"section_{uuid.uuid4().hex[:8]}",
            "start": section.start,
            "end": section.end,
            "label": section.label.value,
            "is_reference": section.is_reference,
            "confidence": None
        })

    new_sections.sort(key=lambda s: s["start"])
    save_sections(session_id, new_sections)

    return new_sections
