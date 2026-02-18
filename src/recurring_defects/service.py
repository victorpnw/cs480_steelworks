from datetime import date
from typing import List

from .models import DefectListRow, DefectDetail
from .repository import InspectionRepository


class RecurrenceService:
    """Service to evaluate defects for recurrence and provide views.

    Methods are stubs: implement business logic later following ACs.
    """

    def __init__(self, repository: InspectionRepository):
        self.repository = repository

    def evaluate_defects(self, start_date: date, end_date: date) -> List[DefectListRow]:
        """Evaluate all defects in the date range and return list rows.

        Responsibilities (to implement):
        - Apply AC3: exclude records with qty_defects == 0
        - Apply AC1-AC4 classification rules
        - Return a list of `DefectListRow` objects suitable for list/table view
        """
        raise NotImplementedError()

    def get_defect_detail(self, defect_code: str, start_date: date, end_date: date) -> DefectDetail:
        """Return a drill-down detail view for a single defect code.

        Responsibilities (to implement):
        - Week-by-week breakdown (AC7)
        - Include underlying inspection records
        - Mark missing/insufficient periods per AC8
        """
        raise NotImplementedError()
