# agent/state.py
import operator
from typing import Annotated
from typing_extensions import TypedDict
from dataclasses import dataclass

@dataclass
class RawProfile:
    name: str
    gym: str
    location: str
    specialization: str | None
    contact: str | None
    source_url: str

@dataclass  
class EnrichedLead:
    raw: RawProfile
    instagram_handle: str | None
    google_presence_score: float   # 0–1
    icp_score: float               # 0–1, from RAG
    is_duplicate: bool

class GraphState(TypedDict):
    locations: list[str]
    # Annotated reducer — parallel scrapers append, never overwrite
    raw_profiles: Annotated[list[RawProfile], operator.add]
    enriched_leads: list[EnrichedLead]
    errors: Annotated[list[str], operator.add]   # also parallel-safe
    run_id: str
    checkpoint_id: str | None