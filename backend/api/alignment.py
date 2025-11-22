"""Pitch alignment API endpoints."""
import json
from pathlib import Path
from typing import List, Optional
from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import FileResponse
import numpy as np

from models.schemas import PairAlignment, PitchPoint

router = APIRouter()

DATA_DIR = Path(__file__).parent.parent.parent / "data"


def get_session_dir(session_id: str) -> Path:
    return DATA_DIR / session_id


def load_sections(session_id: str) -> List[dict]:
    sections_path = get_session_dir(session_id) / "sections.json"
    if not sections_path.exists():
        return []
    with open(sections_path) as f:
        return json.load(f)


def get_pairs(sections: List[dict]) -> List[dict]:
    """Get call/response pairs from sections."""
    calls = [s for s in sections if s["label"] == "call"]
    responses = [s for s in sections if s["label"] == "response"]

    pairs = []
    for i, call in enumerate(calls):
        if i < len(responses):
            pairs.append({
                "pair_id": i,
                "call": call,
                "response": responses[i]
            })
    return pairs


@router.get("/sessions/{session_id}/pairs")
async def get_section_pairs(session_id: str):
    """Get all call/response pairs."""
    session_dir = get_session_dir(session_id)
    if not session_dir.exists():
        raise HTTPException(status_code=404, detail="Session not found")

    sections = load_sections(session_id)
    pairs = get_pairs(sections)

    return {"pairs": pairs, "count": len(pairs)}


def load_full_pitch(session_id: str) -> dict:
    """Load the full track pitch data."""
    pitch_path = get_session_dir(session_id) / "pitch_full.json"
    if not pitch_path.exists():
        return None
    with open(pitch_path) as f:
        return json.load(f)


def slice_pitch(full_pitch: dict, start_time: float, end_time: float) -> List[dict]:
    """Extract pitch data for a time range, with relative times."""
    pitch_data = full_pitch.get('pitch', [])
    sliced = []
    for p in pitch_data:
        if start_time <= p['time'] <= end_time:
            # Create a copy with relative time
            point = dict(p)
            point['relative_time'] = p['time'] - start_time
            sliced.append(point)
    return sliced


@router.get("/sessions/{session_id}/pairs/{pair_id}/pitch")
async def get_pair_pitch(session_id: str, pair_id: int):
    """Get pitch contours for a call/response pair by slicing from full track data."""
    session_dir = get_session_dir(session_id)
    if not session_dir.exists():
        raise HTTPException(status_code=404, detail="Session not found")

    # Load full pitch data
    full_pitch = load_full_pitch(session_id)
    if not full_pitch:
        raise HTTPException(status_code=404, detail="Pitch data not found. Run processing first.")

    # Get sections to find the pair
    sections = load_sections(session_id)
    pairs = get_pairs(sections)

    if pair_id >= len(pairs):
        raise HTTPException(status_code=404, detail=f"Pair {pair_id} not found. Only {len(pairs)} pairs exist.")

    pair = pairs[pair_id]
    call = pair['call']
    response = pair['response']

    # Slice pitch data for call and response
    call_pitch = slice_pitch(full_pitch, call['start'], call['end'])
    response_pitch = slice_pitch(full_pitch, response['start'], response['end'])

    return {
        "pair_id": pair_id,
        "call": call_pitch,
        "response": response_pitch
    }


@router.get("/sessions/{session_id}/alignments")
async def get_alignments(session_id: str):
    """Get all alignment data for a session."""
    session_dir = get_session_dir(session_id)
    if not session_dir.exists():
        raise HTTPException(status_code=404, detail="Session not found")

    alignments_path = session_dir / "alignments.json"
    if not alignments_path.exists():
        # Return empty alignments
        return {"alignments": [], "has_full_pitch": False}

    with open(alignments_path) as f:
        alignments = json.load(f)

    # Check if full pitch data exists
    has_full_pitch = (session_dir / "pitch_full.json").exists()

    return {"alignments": alignments, "has_full_pitch": has_full_pitch}


@router.put("/sessions/{session_id}/alignments/{pair_id}")
async def update_alignment(session_id: str, pair_id: int, custom_offset: Optional[float] = None):
    """Update alignment offset for a pair."""
    session_dir = get_session_dir(session_id)
    if not session_dir.exists():
        raise HTTPException(status_code=404, detail="Session not found")

    alignments_path = session_dir / "alignments.json"
    if alignments_path.exists():
        with open(alignments_path) as f:
            alignments = json.load(f)
    else:
        alignments = []

    # Find or create alignment entry
    alignment_idx = next((i for i, a in enumerate(alignments) if a["pair_id"] == pair_id), None)

    if alignment_idx is not None:
        alignments[alignment_idx]["custom_offset"] = custom_offset
    else:
        alignments.append({
            "pair_id": pair_id,
            "custom_offset": custom_offset,
            "optimal_offset": 0.0
        })

    with open(alignments_path, "w") as f:
        json.dump(alignments, f, indent=2)

    return {"message": "Alignment updated", "pair_id": pair_id, "custom_offset": custom_offset}


@router.get("/sessions/{session_id}/pairs/{pair_id}/metrics")
async def get_pair_metrics(
    session_id: str,
    pair_id: int,
    offset: float = Query(default=0.0, description="Time offset in seconds")
):
    """Calculate correlation metrics for a pair at a given offset."""
    session_dir = get_session_dir(session_id)
    if not session_dir.exists():
        raise HTTPException(status_code=404, detail="Session not found")

    # Load full pitch data
    full_pitch = load_full_pitch(session_id)
    if not full_pitch:
        raise HTTPException(status_code=404, detail="Pitch data not found. Run processing first.")

    # Get sections to find the pair
    sections = load_sections(session_id)
    pairs = get_pairs(sections)

    if pair_id >= len(pairs):
        raise HTTPException(status_code=404, detail=f"Pair {pair_id} not found")

    pair = pairs[pair_id]
    call = pair['call']
    response = pair['response']

    # Slice pitch data for call and response
    call_pitch = slice_pitch(full_pitch, call['start'], call['end'])
    response_pitch = slice_pitch(full_pitch, response['start'], response['end'])

    # Calculate metrics
    metrics = calculate_metrics(call_pitch, response_pitch, offset)

    return {
        "pair_id": pair_id,
        "offset": offset,
        **metrics
    }


def calculate_metrics(call_pitch: List[dict], response_pitch: List[dict], offset: float) -> dict:
    """Calculate correlation and similarity metrics."""
    # Extract voiced semitone values
    call_times = np.array([p["time"] for p in call_pitch if p.get("semitones") is not None])
    call_semitones = np.array([p["semitones"] for p in call_pitch if p.get("semitones") is not None])

    response_times = np.array([p["time"] for p in response_pitch if p.get("semitones") is not None])
    response_semitones = np.array([p["semitones"] for p in response_pitch if p.get("semitones") is not None])

    if len(call_semitones) < 5 or len(response_semitones) < 5:
        return {
            "correlation": None,
            "correlation_unaligned": None,
            "cosine_similarity": None,
            "error": "Insufficient voiced data"
        }

    # Apply offset to response times
    shifted_response_times = response_times + offset

    # Find overlapping time range
    overlap_start = max(call_times.min(), shifted_response_times.min())
    overlap_end = min(call_times.max(), shifted_response_times.max())

    if overlap_start >= overlap_end:
        return {
            "correlation": None,
            "correlation_unaligned": None,
            "cosine_similarity": None,
            "error": "No overlapping time range"
        }

    # Interpolate to common time grid
    common_times = np.linspace(overlap_start, overlap_end, 100)

    call_interp = np.interp(common_times, call_times, call_semitones)
    response_interp = np.interp(common_times, shifted_response_times, response_semitones)

    # Pearson correlation
    correlation = float(np.corrcoef(call_interp, response_interp)[0, 1])

    # Cosine similarity (on z-scored data)
    call_z = (call_interp - call_interp.mean()) / (call_interp.std() + 1e-10)
    response_z = (response_interp - response_interp.mean()) / (response_interp.std() + 1e-10)
    cosine_sim = float(np.dot(call_z, response_z) / (np.linalg.norm(call_z) * np.linalg.norm(response_z) + 1e-10))

    # Calculate unaligned correlation (offset = 0)
    if offset != 0:
        unaligned_metrics = calculate_metrics(call_pitch, response_pitch, 0.0)
        correlation_unaligned = unaligned_metrics.get("correlation")
    else:
        correlation_unaligned = correlation

    return {
        "correlation": correlation,
        "correlation_unaligned": correlation_unaligned,
        "cosine_similarity": cosine_sim
    }


@router.get("/sessions/{session_id}/pairs/{pair_id}/audio/{source}")
async def get_pair_audio(session_id: str, pair_id: int, source: str):
    """
    Get audio segment for a pair.

    source can be: 'call', 'response', or 'both'
    """
    session_dir = get_session_dir(session_id)
    if not session_dir.exists():
        raise HTTPException(status_code=404, detail="Session not found")

    if source not in ["call", "response", "both"]:
        raise HTTPException(status_code=400, detail="Source must be 'call', 'response', or 'both'")

    # For now, return the vocals file path
    # In production, we'd extract the segment
    vocals_path = session_dir / "vocals.wav"
    if not vocals_path.exists():
        raise HTTPException(status_code=404, detail="Vocals file not found")

    sections = load_sections(session_id)
    pairs = get_pairs(sections)

    if pair_id >= len(pairs):
        raise HTTPException(status_code=404, detail="Pair not found")

    pair = pairs[pair_id]

    # Return info about where to find the audio
    return {
        "vocals_url": f"/audio/{session_id}/vocals.wav",
        "call_start": pair["call"]["start"],
        "call_end": pair["call"]["end"],
        "response_start": pair["response"]["start"],
        "response_end": pair["response"]["end"]
    }
