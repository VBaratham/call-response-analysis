"""Pydantic models for API request/response schemas."""
from pydantic import BaseModel, Field
from typing import Optional
from enum import Enum


class SectionLabel(str, Enum):
    CALL = "call"
    RESPONSE = "response"


class Section(BaseModel):
    """A single section (call or response) in the audio."""
    id: str
    start: float = Field(..., ge=0, description="Start time in seconds")
    end: float = Field(..., gt=0, description="End time in seconds")
    label: SectionLabel
    is_reference: bool = Field(default=False, description="Whether this is a reference section for fingerprinting")
    confidence: Optional[float] = Field(default=None, ge=0, le=1, description="Fingerprinting confidence score")

    @property
    def duration(self) -> float:
        return self.end - self.start

    class Config:
        json_schema_extra = {
            "example": {
                "id": "section_0",
                "start": 10.5,
                "end": 15.2,
                "label": "call",
                "is_reference": False,
                "confidence": 0.85
            }
        }


class SectionCreate(BaseModel):
    """Schema for creating a new section."""
    start: float = Field(..., ge=0)
    end: float = Field(..., gt=0)
    label: SectionLabel
    is_reference: bool = False


class SectionUpdate(BaseModel):
    """Schema for updating a section (all fields optional)."""
    start: Optional[float] = Field(default=None, ge=0)
    end: Optional[float] = Field(default=None, gt=0)
    label: Optional[SectionLabel] = None
    is_reference: Optional[bool] = None


class PitchPoint(BaseModel):
    """A single point in a pitch contour."""
    time: float
    f0_hz: Optional[float] = None
    semitones: Optional[float] = None
    voiced: bool = False


class PairAlignment(BaseModel):
    """Alignment data for a call/response pair."""
    pair_id: int
    call_section_id: str
    response_section_id: str
    optimal_offset: float = Field(default=0.0, description="Optimal time offset in seconds")
    custom_offset: Optional[float] = Field(default=None, description="User-defined offset override")
    correlation: Optional[float] = None
    correlation_unaligned: Optional[float] = None
    cosine_similarity: Optional[float] = None


class ProjectMetadata(BaseModel):
    """Metadata about the current project/session."""
    session_id: str
    original_filename: str
    duration: float
    sample_rate: int
    processing_status: str = "pending"
    has_vocals: bool = False
    has_sections: bool = False
    has_pitch: bool = False


class ProcessingStatus(BaseModel):
    """Status of background processing tasks."""
    stage: str = Field(..., description="Current processing stage")
    progress: float = Field(default=0.0, ge=0, le=1, description="Progress 0-1")
    message: str = ""
    error: Optional[str] = None


class ProjectExport(BaseModel):
    """Complete project data for export/import."""
    metadata: ProjectMetadata
    sections: list[Section]
    alignments: list[PairAlignment]
    version: str = "1.0"


class UploadResponse(BaseModel):
    """Response after file upload."""
    session_id: str
    filename: str
    duration: float
    message: str


class AudioInfo(BaseModel):
    """Basic audio file information."""
    duration: float
    sample_rate: int
    channels: int
    waveform_url: str
