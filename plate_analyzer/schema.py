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


class Airport(BaseModel):
    pass


class Failure(BaseModel):
    exception_message: str
    zip_file: str
    file_name: str
    approach: ApproachName


class SkipReason(str, Enum):
    VISUAL_APPROACH = "VISUAL"
    COPTER_ONLY = "COPTER"
    MILITARY_CHART = "MILITARY"


class SkippedApproach(BaseModel):
    skip_reason: SkipReason
    approaches: List[ApproachName]


class AnalysisResult(BaseModel):
    airports: Dict[str, Airport]
    failures: List[Failure]
    skipped_approaches: List[SkippedApproach]
