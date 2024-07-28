"""
Output schema for the plate analyzer.
"""

from pydantic import BaseModel

from typing import List, Dict, Optional


class Airport(BaseModel):
    pass


class Failure(BaseModel):
    exception_message: str
    zip_file: str
    file_name: str
    approach_name: str
    airport_name: str


class AnalysisResult(BaseModel):
    airports: Dict[str, Airport]
    failures: List[Failure]
