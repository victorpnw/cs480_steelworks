"""
Service Layer - Business Logic

This module implements the core business logic for the recurring defect classification
system. It bridges the data access layer (repositories) and presentation layer (UI).

Key Responsibilities:
1. Classify defects as Recurring / Not Recurring / Insufficient Data (AC1-AC4)
2. Generate results for the list view (AC5)
3. Prepare drill-down data for detail views (AC7-AC8)

Architecture Pattern:
  - Services depend on repositories (dependency injection)
  - Services are independent of presentation layer (Streamlit, REST, etc.)
  - All business logic is here, making it easy to reuse across UIs

Classification Algorithm (AC1-AC4):
  
  A defect is "RECURRING" if:
    1. It appears in inspection records from more than one calendar week (AC1)
    2. At least one record with qty_defects > 0 exists in each week (AC3)
    3. All data is complete for the evaluation period (AC4)
  
  A defect is "NOT RECURRING" if:
    1. It appears in only one calendar week (AC2)
    2. All data is complete
  
  A defect is "INSUFFICIENT DATA" if:
    - Gaps exist in the data that prevent confident classification (AC4)

Time Complexity:
  - Classify single defect: O(k log k) where k = records for that defect
    * k to fetch records
    * log k grouping by week
  - Classify all defects: O(n log n) where n = total records
    * n to fetch all records
    * log n grouping operations
"""

from datetime import date, timedelta
from typing import List, Dict, Tuple, Optional
from src.models import (
    InspectionRecord,
    RecurringDefectResult,
    DefectDetailResult,
)
from src.repositories import InspectionRecordRepository, DefectRepository


class RecurringDefectClassificationService:
    """
    Service for identifying and classifying recurring defects.
    
    This is the core business logic that implements Acceptance Criteria AC1-AC9.
    
    Attributes:
        inspection_repo: Repository for accessing inspection records
        defect_repo: Repository for accessing defect master data
    
    Key Methods:
        - classify_defects(): Classify all defects in a date range (AC1-AC4, AC5-AC6, AC9)
        - get_defect_detail(): Get detailed breakdown for a specific defect (AC7-AC8)
    """
    
    def __init__(
        self, inspection_repo: InspectionRecordRepository, defect_repo: DefectRepository
    ):
        """
        Initialize the service with repository instances.
        
        Args:
            inspection_repo: Repository for inspection record queries
            defect_repo: Repository for defect master data queries
        """
        self.inspection_repo = inspection_repo
        self.defect_repo = defect_repo
    
    def classify_defects(
        self, start_date: date, end_date: date
    ) -> List[RecurringDefectResult]:
        """
        Classify all defects within a date range into Recurring/Not Recurring/Insufficient Data.
        
        This method implements the core classification logic (AC1-AC4) and prepares
        results for the list view (AC5-AC6, AC9).
        
        Algorithm Overview:
        1. Get all unique defect codes in the date range
        2. For each defect:
           a. Fetch all non-zero inspection records (AC3)
           b. Group by calendar week
           c. Count weeks, lots, dates, and sum quantities
           d. Check for incomplete data (AC4)
           e. Classify based on week count (AC1-AC2)
        3. Sort results by status and week count (AC9)
        
        Time Complexity:
          O(n log n) where n = total inspection records in date range
          - O(d) to fetch all d unique defects: O(d)
          - For each defect k records: average O(n/d) per defect
          - Grouping by week: O(k log k) per defect
          - Total: O(d * k log k) = O(n log n)
        
        Space Complexity:
          O(n) for storing all defect results and intermediate data
        
        Args:
            start_date (date): Inclusive start of evaluation period
            end_date (date): Inclusive end of evaluation period
        
        Returns:
            List[RecurringDefectResult]: Results sorted by AC9 priority:
                1. Recurring defects first
                2. Within status, sort by weeks_with_occurrences descending
                3. Then by lots_affected descending
        
        Raises:
            ValueError: If start_date > end_date
        
        Acceptance Criteria Mapping:
            AC1: Multi-week defects → "Recurring" status
            AC2: Single-week defects → "Not recurring" status
            AC3: Qty_defects = 0 records filtered out before processing
            AC4: Incomplete data detection → "Insufficient data" status
            AC5: All returned fields match requirements
            AC6: Status field enables filtering
            AC9: Sorting as specified
        """
        if start_date > end_date:
            raise ValueError("start_date must be <= end_date")
        
        # Get all unique defect codes
        defect_codes = self.inspection_repo.get_all_defect_codes()
        
        results: List[RecurringDefectResult] = []
        
        # Classify each defect
        for defect_code in defect_codes:
            # Fetch all non-zero records for this defect in the date range
            records = self.inspection_repo.get_non_zero_records_for_defect(
                defect_code, start_date, end_date
            )
            
            # Skip defects with no occurrences in the period
            if not records:
                continue
            
            # Group records by calendar week
            weeks_dict: Dict[int, List[Tuple[date, int, int]]] = {}  # week_num -> [(date, qty, lot_id)]
            for record in records:
                year, week_num, _ = record.inspection_date.isocalendar()
                if week_num not in weeks_dict:
                    weeks_dict[week_num] = []
                weeks_dict[week_num].append(
                    (record.inspection_date, record.qty_defects, record.lot_id)
                )
            
            # Calculate metrics
            weeks_with_occurrences = len(weeks_dict)
            
            # Get distinct lots affected (AC5)
            lot_ids_set = set()
            for record in records:
                lot_ids_set.add(record.lot_id)
            lots_affected = len(lot_ids_set)
            
            # Get date range (AC5)
            all_dates = [r.inspection_date for r in records]
            first_seen_date = min(all_dates)
            last_seen_date = max(all_dates)
            
            # Sum quantities (AC5)
            total_qty_defects = sum(r.qty_defects for r in records)
            
            # Classify as Recurring or Not Recurring (AC1-AC2)
            if weeks_with_occurrences > 1:
                # AC1: More than one week → Recurring
                status = "Recurring"
            else:
                # AC2: Single week → Not recurring
                status = "Not recurring"
            
            # Check for incomplete data (AC4)
            incomplete_periods = self.inspection_repo.get_incomplete_data_ranges(
                start_date, end_date
            )
            
            # If incomplete periods exist and affect our defect's week range,
            # mark as "Insufficient data" (AC4)
            if incomplete_periods:
                # Check if any incomplete period overlaps with our defect's date range
                defect_date_range = (first_seen_date, last_seen_date)
                if self._date_ranges_overlap(defect_date_range, incomplete_periods):
                    status = "Insufficient data"
            
            # Create result
            result = RecurringDefectResult(
                defect_code=defect_code,
                status=status,
                weeks_with_occurrences=weeks_with_occurrences,
                lots_affected=lots_affected,
                first_seen_date=first_seen_date,
                last_seen_date=last_seen_date,
                total_qty_defects=total_qty_defects,
                incomplete_periods=incomplete_periods,
            )
            results.append(result)
        
        # Sort by AC9: Recurring first, then by weeks desc, then lots desc
        def sort_key(r: RecurringDefectResult):
            status_priority = {
                "Recurring": 0,  # Highest priority (lower number sorts first)
                "Insufficient data": 1,
                "Not recurring": 2,  # Lowest priority
            }
            # Return tuple: (status_priority, -weeks, -lots, defect_code)
            # Negative values reverse the sort order (descending)
            return (
                status_priority.get(r.status, 3),
                -r.weeks_with_occurrences,
                -r.lots_affected,
                r.defect_code,  # Alphabetical for tie-breaking
            )
        
        results.sort(key=sort_key)
        return results
    
    def get_defect_detail(
        self, defect_code: str, start_date: date, end_date: date
    ) -> Optional[DefectDetailResult]:
        """
        Get detailed information for a specific defect, including weekly breakdown.
        
        This method implements the drill-down view requirements (AC7-AC8).
        
        The result includes:
        1. Defect code and status (from classification)
        2. Weekly breakdown showing:
           - Week start/end dates
           - Lots affected in that week
           - Total qty_defects in that week
           - Underlying inspection records for that week
        3. Complete list of underlying records
        4. Any incomplete periods
        
        Time Complexity:
          O(k log k) where k = records for the defect in the date range
          - O(k) to fetch records
          - O(k log k) to group by week
        Space Complexity:
          O(k) for storing records and groups
        
        Args:
            defect_code (str): The defect to analyze
            start_date (date): Date range start
            end_date (date): Date range end
        
        Returns:
            DefectDetailResult: Weekly and record-level breakdown, or None if defect not found
        
        Acceptance Criteria Mapping:
            AC7: Weekly breakdown with lots and quantities
            AC8: Incomplete periods indicated in result
        """
        # Get non-zero records for the defect
        records = self.inspection_repo.get_non_zero_records_for_defect(
            defect_code, start_date, end_date
        )
        
        if not records:
            return None
        
        # First, classify the defect to get its status
        classification = self.classify_defects(start_date, end_date)
        defect_result = next(
            (r for r in classification if r.defect_code == defect_code), None
        )
        status = defect_result.status if defect_result else "Unknown"
        
        # Group records by week
        weekly_breakdown: Dict[str, Dict] = {}  # week_key -> breakdown data
        
        for record in records:
            year, week_num, _ = record.inspection_date.isocalendar()
            week_key = f"week_{week_num:02d}"  # e.g., "week_03"
            
            if week_key not in weekly_breakdown:
                # Calculate week bounds
                week_start = self.inspection_repo._get_week_start_date(
                    record.inspection_date
                )
                week_end = self.inspection_repo._get_week_end_date(
                    record.inspection_date
                )
                
                weekly_breakdown[week_key] = {
                    "week_start": week_start,
                    "week_end": week_end,
                    "week_number": week_num,
                    "lots": set(),
                    "total_qty_defects": 0,
                    "records": [],
                }
            
            # Add record to the week
            lot_orm = None  # Will be looked up in the repository
            weekly_breakdown[week_key]["lots"].add(record.lot_id)
            weekly_breakdown[week_key]["total_qty_defects"] += record.qty_defects
            weekly_breakdown[week_key]["records"].append(record)
        
        # Convert sets to sorted lists
        for week_data in weekly_breakdown.values():
            week_data["lots"] = sorted(list(week_data["lots"]))
        
        # Get incomplete periods
        incomplete_periods = self.inspection_repo.get_incomplete_data_ranges(
            start_date, end_date
        )
        
        # Create result
        result = DefectDetailResult(
            defect_code=defect_code,
            status=status,
            weekly_breakdown=weekly_breakdown,
            underlying_records=records,
            incomplete_periods=incomplete_periods,
        )
        
        return result
    
    # ==================== Helper Methods ====================
    
    @staticmethod
    def _date_ranges_overlap(
        range1: Tuple[date, date], ranges2: List[Tuple[date, date]]
    ) -> bool:
        """
        Check if a single date range overlaps with any of multiple ranges.
        
        Time Complexity: O(n) where n is number of ranges in ranges2
        Space Complexity: O(1)
        
        Args:
            range1: Tuple of (start_date, end_date)
            ranges2: List of (start_date, end_date) tuples
        
        Returns:
            bool: True if any overlap exists
        """
        start1, end1 = range1
        for start2, end2 in ranges2:
            # Ranges overlap if: start1 <= end2 AND end1 >= start2
            if start1 <= end2 and end1 >= start2:
                return True
        return False
    
    @staticmethod
    def _get_week_number(d: date) -> int:
        """
        Get the ISO week number for a date.
        
        Time Complexity: O(1)
        
        Args:
            d (date): Any date
        
        Returns:
            int: ISO week number (1-53)
        """
        _, week_num, _ = d.isocalendar()
        return week_num
