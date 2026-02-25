"""
Domain Models for SteelWorks Quality Engineering Application

This module defines the core domain entities (data model classes) for the application:
- Defect: Represents a type of defect that can occur in manufacturing
- Lot: Represents a batch/lot of manufactured goods
- InspectionRecord: Represents the record of inspection for a lot, including defect details

These models serve as the bridge between the database schema (SQLAlchemy ORM) and business logic.
They encapsulate the structure and validators for domain data.

Relationship Model:
  Lot (1) --> (*) InspectionRecord (*) <-- (1) Defect
  
Time Complexity: O(1) for creating/accessing any model instance (instantiation only)
Space Complexity: O(1) per instance (fixed attributes)
"""

from datetime import date
from dataclasses import dataclass
from typing import Optional, List


@dataclass
class Defect:
    """
    Domain model representing a type of defect that can occur during inspection.
    
    Attributes:
        id (int): Primary key identifier for the defect (surrogate key)
        defect_code (str): Business key - the unique defect classification code
            (e.g., "CRACK_001", "CORROSION", "DENT"). This is the human-readable identifier.
        
    Validation:
        - defect_code must be non-empty and unique across all defects
    
    Usage:
        >>> defect = Defect(id=1, defect_code="CRACK_001")
        >>> print(defect.defect_code)
        CRACK_001
    """
    id: int
    defect_code: str


@dataclass
class Lot:
    """
    Domain model representing a batch/lot of manufactured goods.
    
    Attributes:
        id (int): Primary key identifier for the lot (surrogate key)
        lot_id (str): Business key - the unique lot identifier
            (e.g., "LOT-2026-001", "BATCH-A1"). This is the human-readable identifier.
    
    Validation:
        - lot_id must be non-empty and unique across all lots
    
    Usage:
        >>> lot = Lot(id=1, lot_id="LOT-2026-001")
        >>> print(lot.lot_id)
        LOT-2026-001
    """
    id: int
    lot_id: str


@dataclass
class InspectionRecord:
    """
    Domain model representing an inspection record - the result of inspecting a lot
    for a specific defect on a specific date.
    
    Attributes:
        id (int): Primary key identifier (surrogate key)
        inspection_id (str): Unique business key for the inspection record
            (e.g., "INSP-2026-001-CRACK")
        lot_id (int): Foreign key reference to the Lot
        defect_id (int): Foreign key reference to the Defect
        inspection_date (date): The calendar date when the inspection occurred
        qty_defects (int): The quantity/count of defects found in this inspection
            - 0 means no defects were found (clean inspection)
            - > 0 means defects were found
        is_data_complete (bool): Flag indicating whether data for this period is complete
            - True: Complete data (inspection records exist or are confirmed missing)
            - False: Incomplete data (gaps in records, uncertain whether data exists)
    
    Key Business Rules (from Acceptance Criteria):
        1. Records with qty_defects = 0 should NOT be counted as a defect occurrence (AC3)
        2. This flag is_data_complete is used to detect "Insufficient data" situations (AC4)
    
    Validation:
        - qty_defects >= 0 (must be non-negative)
        - inspection_id must be unique
        - lot_id and defect_id must reference existing records
    
    Time Complexity: O(1) for instance creation
    Space Complexity: O(1) per instance
    
    Usage:
        >>> record = InspectionRecord(
        ...     id=1,
        ...     inspection_id="INSP-2026-001",
        ...     lot_id=1,
        ...     defect_id=2,
        ...     inspection_date=date(2026, 1, 15),
        ...     qty_defects=3,
        ...     is_data_complete=True
        ... )
        >>> record.qty_defects
        3
    """
    id: int
    inspection_id: str
    lot_id: int
    defect_id: int
    inspection_date: date
    qty_defects: int
    is_data_complete: bool = True


@dataclass
class RecurringDefectResult:
    """
    Domain model representing the classification result for a single defect.
    
    This model combines the defect information with the analysis results from the
    recurring defect classification algorithm. It is used to populate the results
    shown in the UI.
    
    Attributes:
        defect_code (str): The defect classification code
        status (str): Classification result - one of:
            - "Recurring": Defect appears in more than one calendar week
            - "Not recurring": Defect appears in only one calendar week
            - "Insufficient data": Cannot determine due to incomplete data
        weeks_with_occurrences (int): Count of distinct calendar weeks with defect occurrences
            (excluding records with qty_defects = 0)
        lots_affected (int): Count of distinct lots where this defect was found
        first_seen_date (date): The earliest inspection_date for this defect
        last_seen_date (date): The latest inspection_date for this defect
        total_qty_defects (int): Sum of all qty_defects for this defect (excluding zero records)
        incomplete_periods (List[tuple]): List of (start_date, end_date) tuples indicating
            periods with incomplete data that affected classification. Empty if no incomplete periods.
    
    Calculation Complexity:
        These values are computed by the RecurringDefectClassificationService.
        Time Complexity: O(n) where n is number of inspection records for the defect
        Space Complexity: O(m) where m is the number of distinct weeks
    
    Usage:
        >>> result = RecurringDefectResult(
        ...     defect_code="CRACK_001",
        ...     status="Recurring",
        ...     weeks_with_occurrences=3,
        ...     lots_affected=2,
        ...     first_seen_date=date(2026, 1, 1),
        ...     last_seen_date=date(2026, 1, 31),
        ...     total_qty_defects=15,
        ...     incomplete_periods=[]
        ... )
    """
    defect_code: str
    status: str  # "Recurring", "Not recurring", "Insufficient data"
    weeks_with_occurrences: int
    lots_affected: int
    first_seen_date: date
    last_seen_date: date
    total_qty_defects: int
    incomplete_periods: List[tuple] = None  # List of (start_date, end_date) tuples
    
    def __post_init__(self):
        """Initialize incomplete_periods as empty list if None"""
        if self.incomplete_periods is None:
            self.incomplete_periods = []


@dataclass
class DefectDetailResult:
    """
    Domain model representing the detailed breakdown for a specific defect.
    
    This model provides the drill-down information needed for AC7 and AC8, showing:
    - The defect code and classification status
    - Weekly breakdown with which lots were affected and defect quantities
    - The underlying inspection records used for the calculation
    
    Attributes:
        defect_code (str): The defect classification code
        status (str): Classification result from RecurringDefectResult
        weekly_breakdown (dict): Keyed by ISO week number (1-53) or formatted week string
            Value: {
                'week_start': date,
                'week_end': date,
                'lots': [lot_ids...],
                'total_qty_defects': int,
                'records': [InspectionRecord...]
            }
        underlying_records (List[InspectionRecord]): All inspection records that contributed
            to this result (filtered by inspection_date range). Used for full transparency.
        incomplete_periods (List[tuple]): List of (start_date, end_date) tuples indicating
            periods with incomplete data
    
    Purpose: Provides complete explainability for drill-down view (AC7-AC8)
    """
    defect_code: str
    status: str
    weekly_breakdown: dict  # Maps week -> {week_start, week_end, lots, total_qty_defects, records}
    underlying_records: List[InspectionRecord]
    incomplete_periods: List[tuple] = None
    
    def __post_init__(self):
        """Initialize incomplete_periods as empty list if None"""
        if self.incomplete_periods is None:
            self.incomplete_periods = []
