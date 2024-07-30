"""
Output schema for the plate analyzer.
"""

from pydantic import BaseModel

from enum import Enum
from typing import List, Dict, Optional


class ApproachType(str, Enum):
    # ILS stuff.
    ILS = "ILS"
    LOCALIZER = "LOC"
    LOCALIZER_DME = "LOC/DME"
    LOCALIZER_NDB = "LOC/NDB"
    LOCALIZER_BACKCOURSE = "LOC Backcourse"
    LOCALIZER_DME_BACKCOURSE = "LOC/DME Backcourse"
    LDA = "LDA"
    LDA_DME = "LDA/DME"
    SDF = "SDF"
    # RNAV/GPS stuff
    RNAV = "RNAV"
    RNAV_GPS = "RNAV (GPS)"
    RNAV_RNP = "RNAV (RNP)"
    GPS = "GPS"
    GBAS = "GBAS"
    TACAN = "TACAN"
    # NAVAids
    NDB = "NDB"
    NDB_DME = "NDB/DME"
    VOR = "VOR"
    VOR_DME = "VOR/DME"

    HIGH_ILS = "High Altitude ILS"
    HIGH_LOC = "High Altitude LOC"
    HIGH_LOC_DME = "High Altitude LOC/DME"
    HIGH_LOC_DME_BACKCOURSE = "High Altitude LOC/DME Backcourse"
    HIGH_RNAV_GPS = "High Altitude RNAV (GPS)"
    HIGH_VOR = "High Altitude VOR"
    HIGH_VOR_DME = "High Altitude VOR/DME"
    HIGH_TACAN = "High Altitude TACAN"

    @staticmethod
    def from_approach_title(title_type: str, is_high_alt: bool = False):
        lookup_table = APPROACH_PLATE_TITLE_TYPES
        if is_high_alt:
            lookup_table = HIGH_ALTITUDE_APPROACH_TITLE_TYPES

        if title_type not in lookup_table:
            raise ValueError(
                f"'{title_type}' {'(High)' if is_high_alt else ''} is not a recognized apporoach type"
            )
        return lookup_table[title_type]


APPROACH_PLATE_TITLE_TYPES = {
    "ILS": ApproachType.ILS,
    "LOC": ApproachType.LOCALIZER,
    "LOC/DME": ApproachType.LOCALIZER_DME,
    "LOC/NDB": ApproachType.LOCALIZER_NDB,
    "LOC BC": ApproachType.LOCALIZER_BACKCOURSE,
    "LOC/DME BC": ApproachType.LOCALIZER_DME_BACKCOURSE,
    "RNAV (GPS)": ApproachType.RNAV_GPS,
    "GPS": ApproachType.GPS,
    "GLS": ApproachType.GBAS,
    "TACAN": ApproachType.TACAN,
    "NDB/DME": ApproachType.NDB_DME,
    "VOR": ApproachType.VOR,
    "VOR/DME": ApproachType.VOR_DME,
    "RNAV (RNP)": ApproachType.RNAV_RNP,
    "NDB": ApproachType.NDB,
    "LDA": ApproachType.LDA,
    "LDA/DME": ApproachType.LDA_DME,
    "SDF": ApproachType.SDF,
}

HIGH_ALTITUDE_APPROACH_TITLE_TYPES = {
    "ILS": ApproachType.HIGH_ILS,
    "LOC": ApproachType.HIGH_LOC,
    "LOC/DME": ApproachType.HIGH_LOC_DME,
    "LOC/DME BC": ApproachType.HIGH_LOC_DME_BACKCOURSE,
    "VOR": ApproachType.HIGH_VOR,
    "VOR/DME": ApproachType.HIGH_VOR_DME,
    "TACAN": ApproachType.HIGH_TACAN,
    "RNAV (GPS)": ApproachType.HIGH_RNAV_GPS,
}


class ApproachComments(BaseModel):
    has_non_standard_takeoff_minimums: bool
    has_non_standard_alternative_requirements: bool
    text_comments: str


class Approach(BaseModel):
    """
    Conceptually this is one-to-one with a single FAA approach plate.
    As such, it may have multiple "approaches" like a localizer approach
    and an ILS approach in one.
    """

    name: str
    plate_file: str
    types: List[ApproachType]

    approach_course: Optional[float]
    # The runway this approach goes to and the degrees the approach
    # is off from the runway, if the approach goes to a runway.
    runway: Optional[str]
    runway_approach_offset_angle: Optional[float]

    comments: ApproachComments
    # Approach instructions.
    missed_instructions: str

    # Features of the approach.
    has_dme_arc: bool
    has_procedure_turn: bool
    has_hold_in_lieu_of_procedure_turn: bool


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


class ApproachName(BaseModel):
    """
    Identifies an approach with its airport and name.

    e.g ILS 21L at KPDK airport.
    """

    name: str
    airport: str


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
