from dataclasses import dataclass
from typing import Optional, List, Dict, Any
from datetime import datetime

@dataclass(frozen=True)
class TimetableEntry:
    """Domain Entity representing a single schedule slot in the ERP."""
    id: Optional[int]
    day: str
    time: str
    subject: str
    teacher: Optional[str] = None
    room: Optional[str] = None
    slot_type: str = "Theory"
    division: Optional[str] = None
    department: Optional[str] = None
    year: Optional[str] = None
    semester: Optional[str] = None
    created_at: Optional[datetime] = None

@dataclass
class ConflictReport:
    """Struct for conflict detection results."""
    has_conflict: bool
    type: Optional[str] = None  # 'FACULTY' or 'ROOM'
    message: Optional[str] = None
    conflicting_entry_id: Optional[int] = None
