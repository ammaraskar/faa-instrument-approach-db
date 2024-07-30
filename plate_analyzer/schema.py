"""
Output schema for the plate analyzer.
"""

from pydantic import BaseModel

from enum import Enum
from typing import List, Dict, Optional


class ApproachName(BaseModel):
    """
    Identifies an approach with its airport and name.

    e.g ILS 21L at KPDK airport.
    """

    name: str
    airport: str


class Approach(BaseModel):
    name: str
    plate_file: str

    approach_course: Optional[float]
    # The runway this approach goes to and the degrees the approach
    # is off from the runway, if the approach goes to a runway.
    runway: Optional[str]
    runway_approach_offset_angle: Optional[float]


class Runway(BaseModel):
    name: str
    bearing: float
    threshold_elevation: int


class Airport(BaseModel):
    id: str
    name: str
    latitude: str
    longitude: str
    runways: List[Runway]
    approaches: List[Approach]


# A few info classes related to analysis results and failures.
class Failure(BaseModel):
    """Approaches that failed to analyze, the cause and the
    exact file it was in."""

    exception_message: str
    zip_file: str
    file_name: str
    approach: ApproachName


class SkipReason(str, Enum):
    VISUAL_APPROACH = "VISUAL"
    COPTER_ONLY = "COPTER"
    MILITARY_CHART = "MILITARY"


class SkippedApproach(BaseModel):
    """Approaches that we skipped analyzing and why."""

    skip_reason: SkipReason
    approaches: List[ApproachName]


class AnalysisResult(BaseModel):
    # Which dtpp cycle number was used in the analysis.
    dtpp_cycle_number: str
    airports: Dict[str, Airport]
    failures: List[Failure]
    skipped_approaches: List[SkippedApproach]
