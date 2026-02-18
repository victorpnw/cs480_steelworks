from dataclasses import dataclass
from datetime import date
from typing import List, Optional


@dataclass
class Defect:
    id: int
    defect_code: str
    created_at: Optional[str] = None


@dataclass
class Lot:
    id: int
    lot_id: str
    created_at: Optional[str] = None


@dataclass
class InspectionRecord:
    id: int
    inspection_id: str
    lot_id: int
    defect_id: int
    inspection_date: date
    qty_defects: int
    is_data_complete: bool = True


@dataclass
class DefectListRow:
    defect_id: int
    defect_code: str
    status: str  # 'Recurring' | 'Not recurring' | 'Insufficient data'
    num_weeks: int
    num_lots: int
    first_seen: Optional[date]
    last_seen: Optional[date]
    total_qty: int


@dataclass
class WeekSummary:
    week_start: date
    week_end: date
    lots_in_week: List[str]
    total_qty: int


@dataclass
class DefectDetail:
    defect_code: str
    weeks: List[WeekSummary]
    inspection_records: List[InspectionRecord]
