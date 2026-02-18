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
        from datetime import datetime
        from collections import defaultdict
        
        # Get all inspection records in date range
        all_records = self.repository.get_inspection_records(start_date, end_date)
        
        # AC3: Filter out records with qty_defects == 0
        valid_records = [r for r in all_records if r.qty_defects > 0]
        
        # Group records by defect_id
        defects_map: dict = defaultdict(list)
        for record in valid_records:
            defects_map[record.defect_id].append(record)
        
        # Evaluate each defect and build DefectListRow
        result: List[DefectListRow] = []
        
        for defect_id, records in defects_map.items():
            # Generate defect code from defect_id (e.g., 1 -> "DEF-001")
            defect_code = f"DEF-{defect_id:03d}" if defect_id else ""
            
            # Collect lot_ids and inspection dates
            lots_set = set()
            weeks_set = set()
            total_qty = 0
            has_incomplete_data = False
            
            for record in records:
                lots_set.add(record.lot_id)
                # Get ISO calendar week and year to identify unique weeks
                iso_calendar = record.inspection_date.isocalendar()
                weeks_set.add((iso_calendar[0], iso_calendar[1]))  # (year, week)
                total_qty += record.qty_defects
                if not record.is_data_complete:
                    has_incomplete_data = True
            
            # Determine status based on AC1, AC2, AC4
            if has_incomplete_data:
                # AC4: Incomplete data -> Insufficient data
                status = "Insufficient data"
            elif len(weeks_set) > 1:
                # AC1: Appears in more than one week -> Recurring
                status = "Recurring"
            elif len(lots_set) > 1:
                # Multiple lots but same week -> Recurring (spans multiple lots)
                status = "Recurring"
            else:
                # AC2: Single lot -> Not Recurring
                status = "Not recurring"
            
            # Get first and last seen dates
            first_seen = min(r.inspection_date for r in records) if records else None
            last_seen = max(r.inspection_date for r in records) if records else None
            
            row = DefectListRow(
                defect_id=defect_id,
                defect_code=defect_code,
                status=status,
                num_weeks=len(weeks_set),
                num_lots=len(lots_set),
                first_seen=first_seen,
                last_seen=last_seen,
                total_qty=total_qty
            )
            result.append(row)
        
        return result

    def get_defect_detail(self, defect_code: str, start_date: date, end_date: date) -> DefectDetail:
        """Return a drill-down detail view for a single defect code.

        Responsibilities (to implement):
        - Week-by-week breakdown (AC7)
        - Include underlying inspection records
        - Mark missing/insufficient periods per AC8
        """
        raise NotImplementedError()
