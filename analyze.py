from pydantic import BaseModel
import arinc424

from enum import Enum
from typing import List, Optional


AIRPORT_APPROACH_TYPE = 'PF'


WAYPOINT_TYPES = {
    'A': 'airport_as_waypoint',
    'E': 'essential_waypoint',
    'F': 'off_airway_waypoint',
    'G': 'runway_as_waypoint',
    'H': 'heliport_as_waypoint',
    'N': 'ndb_navaid_as_waypoint',
    'P': 'phantom_waypoint',
    'R': 'non_essential_waypoint',
    'T': 'transition_essential_waypoint',
    'V': 'vhf_navaid_as_waypoint'
}


APPROACH_FIX_TYPES = {
    'A': 'initial_approach_fix',
    'B': 'intermediate_approach_fix',
    'C': 'initial_approach_fix_with_hold',
    'D': 'initial_approach_fix_with_final_course_fix',
    'E': 'final_end_point_fix',
    'F': 'final_approach_fix',
    'H': 'holding_fix',
    'I': 'final_approach_course_fix',
    'M': 'published_missed_approach_point_fix',
}


APPROACH_ROUTE_TYPES = {
    'A': 'Approach Transition',
    'B': 'Localizer/Backcourse Approach',
    'D': 'VOR/DME Approach',
    'F': 'Flight Management System (FMS) Approach',
    'G': 'Instrument Guidance System (IGS) Approach',
    'I': 'Instrument Landing System (ILS) Approach',
    'J': 'GNSS Landing System (GLS) Approach',
    'L': 'Localizer Only (LOC) Approach',
    'M': 'Microwave Landing System (MLS) Approach',
    'N': 'Non-Directional Beacon (NDB) Approach',
    'P': 'Global Position System (GPS) Approach',
    'Q': 'Non-Directional Beacon + DME (NDB+DME) Approach',
    'R': 'Area Navigation (RNAV) Approach',
    'S': 'VOR Approach using VORDME/VORTAC',
    'T': 'TACAN Approach',
    'U': 'Simplified Directional Facility (SDF) Approach',
    'V': 'VOR Approach',
    'W': 'Microwave Landing System (MLS), Type A Approach',
    'X': 'Localizer Directional Aid (LDA) Approach',
    'Y': 'Microwave Landing System (MLS), Type B and C Approach',
    'Z': 'Missed Approach',
}


class VorDmeDefinedPoint(BaseModel):
    # Defined as Outbound Course/OB CRS in arinc424 docs.
    vor_name: str
    radial: float
    is_dme_arc: bool = False
    distance: Optional[float]

    @classmethod
    def from_record(cls, record):
        # VOR/DME defined points.
        try:
            vor_name = get_arinc424_field_value(record, 'Recommended Navaid')
            if vor_name.strip() == '':
                return None
        except KeyError:
            return None
        radial = int(get_arinc424_field_value(record, 'Theta')) / 10.0
        
        # If the path is AF, then it's an "Arc to Fix" aka a DME ARC.
        is_dme_arc = get_arinc424_field_value(record, 'Path and Termination') == 'AF'

        distance = None
        try:
            distance = int(get_arinc424_field_value(record, 'Rho')) / 10.0
        except KeyError:
            pass

        return cls(vor_name=vor_name, radial=radial, is_dme_arc=is_dme_arc, distance=distance)


class Waypoint(BaseModel):
    from_fix_identifier: Optional[str]
    fix_identifier: str

    route_type: str

    course: Optional[float]
    altitude: Optional[int]

    waypoint_type: Optional[str]
    fix_type: Optional[str]

    vor_dme_point: Optional[VorDmeDefinedPoint]

    @classmethod
    def from_record(cls, record):
        fix_identifier = get_arinc424_field_value(record, 'Fix Identifier')

        from_fix_identifier = get_arinc424_field_value(record, 'Transition Identifier')
        if from_fix_identifier.strip() == '':
            from_fix_identifier = None

        route_type = get_arinc424_field_value_raw(record, 'Route Type')
        route_type = APPROACH_ROUTE_TYPES[route_type]

        course = None
        try:
            course_field = get_arinc424_field_value(record, 'Magnetic Course')
            if course_field:
                course = float(course_field)
        except KeyError:
            pass

        altitude = None
        try:
            altitude_field = get_arinc424_field_value_raw(record, 'Altitude').strip()
            if altitude_field:
                altitude = int(altitude_field)
        except KeyError:
            pass
        
        waypoint_type = None
        approach_fix_type = None

        try:
            waypoint_description_code = get_arinc424_field_value_raw(
                record, 'Waypoint Description Code')
            if waypoint_description_code[0] != ' ':
                waypoint_type = WAYPOINT_TYPES[waypoint_description_code[0]]
            if waypoint_description_code[3] != ' ':
                approach_fix_type = APPROACH_FIX_TYPES[waypoint_description_code[3]]
        except KeyError:
            pass

        vor_dme_point = VorDmeDefinedPoint.from_record(record)

        return cls(fix_identifier=fix_identifier,
                   from_fix_identifier=from_fix_identifier,
                   route_type=route_type,
                   course=course,
                   altitude=altitude,
                   waypoint_type=waypoint_type,
                   fix_type=approach_fix_type,
                   vor_dme_point=vor_dme_point)


class Approach(BaseModel):
    identifier: str
    approach_types: List[str] = []

    waypoints: List[Waypoint] = []


class Airport(BaseModel):
    identifier: str
    approaches: dict[str, Approach] = {}

    def get_or_add_approach(self, approach_identifier) -> Approach:
        if approach_identifier not in self.approaches:
            self.approaches[approach_identifier] = Approach(identifier=approach_identifier)

        return self.approaches[approach_identifier]


def get_arinc424_field_value_raw(record, name):
    for field in record.fields:
        if field.name != name:
            continue
        return field.value
    raise KeyError(f"Field {name} not found in {record}")


def get_arinc424_field_value(record, name, strip=True):
    for field in record.fields:
        if field.name != name:
            continue

        value = field.decode(field.value)
        if strip:
            value = value.strip()
        return value

    raise KeyError(f"Field {name} not found in {record}")


def process_airport_approach(record):
    airport_name = get_arinc424_field_value(record, 'Airport Identifier')

    if airport_name != "KAHN":
        return

    global airport
    if airport is None:
        airport = Airport(identifier=airport_name)

    record.decode()
    approach_name = get_arinc424_field_value(record, 'SID/STAR/Approach Identifier')
    approach = airport.get_or_add_approach(approach_name)

    waypoint = Waypoint.from_record(record)
    approach.waypoints.append(waypoint)


def compute_metadata_for_approaches(airport):
    for approach in airport.approaches.values():
        approach_types = set()

        for waypoint in approach.waypoints:
            if waypoint.route_type != 'Approach Transition':
                approach_types.add(waypoint.route_type)

        approach.approach_types = list(approach_types)


airport = None

with open("../../Downloads/FAACIFP18", "r") as f:
    for line in f:
        record = arinc424.Record()

        record.read(line)
        
        if record.code == AIRPORT_APPROACH_TYPE:
            process_airport_approach(record)

    # Go through each airport and its approaches and add metadata per
    # approach.
    compute_metadata_for_approaches(airport)


with open('output.json', 'w') as f:
    f.write(airport.model_dump_json(indent=4))
