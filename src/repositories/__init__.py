"""
Repository Layer - Data Access Objects (DAO)

This module implements the repository pattern for data access. Repositories provide
a clean abstraction over the ORM, encapsulating all database queries and enabling:
  - Easy swapping of persistence mechanisms (moving from PostgreSQL to another DB)
  - Testability through mocking
  - Centralized query logic for reusability across services
  - Query optimization in one place

Architecture:
  - Services call repositories
  - Repositories translate between domain models and ORM models
  - Repositories execute all SQL/ORM queries

Query Performance Notes:
  - All queries leverage database indexes for O(log n) lookups
  - Range queries on inspection_date use database sorting
  - Group operations happen at database level for efficiency

Time Complexity Analysis:
  - Query by ID: O(log n) with index
  - Range query on date: O(k + log n) where k is result set size
  - Group by operations: O(n log n) with database optimization
  
Space Complexity: O(k) where k is the size of returned result set
"""

from datetime import date
from typing import List, Optional, Dict, Set, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import and_, func

from src.models import InspectionRecord, Defect, Lot
from src.models.orm_models import InspectionRecordORM, DefectORM, LotORM


class InspectionRecordRepository:
    """
    Repository for accessing inspection records from the database.
    
    Provides query methods to retrieve inspection records with various filters.
    All methods are designed to support the recurring defect classification logic
    (AC1-AC4).
    
    Key Methods:
        - get_by_defect_id(): Get all records for a specific defect
        - get_by_date_range(): Get records within a date range
        - get_all_defect_codes(): Get all unique defect codes
        - get_weeks_for_defect(): Get distinct weeks a defect appears in
    
    Time Complexity Notes:
        - Leverages database indexes for fast lookups
        - GROUP BY operations batched to database layer
        - All methods return sorted results at database level
    """
    
    def __init__(self, session: Session):
        """
        Initialize the repository with a database session.
        
        Args:
            session (Session): SQLAlchemy session (typically obtained from get_session())
        """
        self.session = session
    
    def get_by_inspection_id(self, inspection_id: str) -> Optional[InspectionRecord]:
        """
        Get a single inspection record by its business key (inspection_id).
        
        Time Complexity: O(log n) - Index on inspection_id
        Space Complexity: O(1)
        
        Args:
            inspection_id (str): The unique inspection identifier
        
        Returns:
            InspectionRecord: Domain model if found, None otherwise
        """
        # Query using the unique index on inspection_id
        orm_record = (
            self.session.query(InspectionRecordORM)
            .filter(InspectionRecordORM.inspection_id == inspection_id)
            .first()
        )
        return self._to_domain_model(orm_record) if orm_record else None
    
    def get_all_for_defect(self, defect_code: str) -> List[InspectionRecord]:
        """
        Get all inspection records for a specific defect code.
        
        This is a critical query used by AC1-AC4 to evaluate whether a defect
        is recurring. All records are sorted by date for easier processing.
        
        Time Complexity: O(log n + k) where k is number of records for the defect
          - Index lookup on defect code: O(log n)
          - Returning k results: O(k)
        Space Complexity: O(k)
        
        Args:
            defect_code (str): The defect classification code
        
        Returns:
            List[InspectionRecord]: All records with this defect code, sorted by date
        """
        # Join with defects table and filter by defect_code
        # Index on (defect_id, inspection_date) optimizes this join
        orm_records = (
            self.session.query(InspectionRecordORM)
            .join(DefectORM, InspectionRecordORM.defect_id == DefectORM.id)
            .filter(DefectORM.defect_code == defect_code)
            .order_by(InspectionRecordORM.inspection_date)
            .all()
        )
        return [self._to_domain_model(orm) for orm in orm_records]
    
    def get_all_for_defect_in_range(
        self, defect_code: str, start_date: date, end_date: date
    ) -> List[InspectionRecord]:
        """
        Get all inspection records for a specific defect within a date range.
        
        Used for date-window filtering when evaluating recurring defect status
        for a specific time period (e.g., "last 12 weeks").
        
        Time Complexity: O(log n + k) where k is the result set size
          - Index on inspection_date speeds up range filtering
          - Index on defect_id speeds up defect filtering
        Space Complexity: O(k)
        
        Args:
            defect_code (str): The defect classification code
            start_date (date): Inclusive start date
            end_date (date): Inclusive end date
        
        Returns:
            List[InspectionRecord]: Records matching both filters, sorted by date
        """
        orm_records = (
            self.session.query(InspectionRecordORM)
            .join(DefectORM, InspectionRecordORM.defect_id == DefectORM.id)
            .filter(
                and_(
                    DefectORM.defect_code == defect_code,
                    InspectionRecordORM.inspection_date >= start_date,
                    InspectionRecordORM.inspection_date <= end_date,
                )
            )
            .order_by(InspectionRecordORM.inspection_date)
            .all()
        )
        return [self._to_domain_model(orm) for orm in orm_records]
    
    def get_all_defect_codes(self) -> List[str]:
        """
        Get a list of all unique defect codes that have inspection records.
        
        Used to iterate through all defects for classification.
        
        Time Complexity: O(n) where n is number of defect records
          - Must scan all distinct defects
        Space Complexity: O(d) where d is number of unique defects
        
        Returns:
            List[str]: Sorted list of all defect codes
        """
        # Query only defect codes that have inspection records (avoid unused defects)
        defect_codes = (
            self.session.query(DefectORM.defect_code)
            .join(InspectionRecordORM, DefectORM.id == InspectionRecordORM.defect_id)
            .distinct()
            .order_by(DefectORM.defect_code)
            .all()
        )
        return [code[0] for code in defect_codes]
    
    def get_all_records_in_range(
        self, start_date: date, end_date: date
    ) -> List[InspectionRecord]:
        """
        Get all inspection records within a date range.
        
        Used to check data completeness (AC4) and get all records for a date window.
        
        Time Complexity: O(log n + k) where k is number of records in date range
        Space Complexity: O(k)
        
        Args:
            start_date (date): Inclusive start date
            end_date (date): Inclusive end date
        
        Returns:
            List[InspectionRecord]: All records in the range, sorted by date
        """
        orm_records = (
            self.session.query(InspectionRecordORM)
            .filter(
                and_(
                    InspectionRecordORM.inspection_date >= start_date,
                    InspectionRecordORM.inspection_date <= end_date,
                )
            )
            .order_by(InspectionRecordORM.inspection_date)
            .all()
        )
        return [self._to_domain_model(orm) for orm in orm_records]
    
    def get_weeks_for_defect(
        self, defect_code: str, start_date: date = None, end_date: date = None
    ) -> List[Tuple[int, date, date]]:
        """
        Get all calendar weeks where a defect appears (with non-zero qty_defects).
        
        CRITICAL for AC1 classification: "same defect code appears in inspection 
        records in more than one calendar week".
        
        This method:
        1. Filters to records with qty_defects > 0 (per AC3)
        2. Groups by calendar week
        3. Returns week information for each occurrence
        
        Time Complexity: O(log n + k log k) where k is records with defect
          - Index lookup: O(log n)
          - GROUP BY at database: O(k log k)
          - Returning results: O(w) where w is number of distinct weeks
        Space Complexity: O(w) where w is number of distinct weeks
        
        Args:
            defect_code (str): The defect classification code
            start_date (date, optional): Filter to records on/after this date
            end_date (date, optional): Filter to records on/before this date
        
        Returns:
            List[Tuple[int, date, date]]: List of (week_number, week_start, week_end)
                where:
                - week_number: ISO week number (1-53)
                - week_start: First day of the week (Monday)
                - week_end: Last day of the week (Sunday)
        
        Example:
            >>> weeks = repo.get_weeks_for_defect("CRACK_001", 
            ...                                   date(2026,1,1), date(2026,12,31))
            >>> weeks
            [(2, date(2026, 1, 5), date(2026, 1, 11)),
             (4, date(2026, 1, 19), date(2026, 1, 25))]
            # Means defect appears in week 2 and week 4
        """
        # Build query
        query = (
            self.session.query(InspectionRecordORM)
            .join(DefectORM, InspectionRecordORM.defect_id == DefectORM.id)
            .filter(
                and_(
                    DefectORM.defect_code == defect_code,
                    InspectionRecordORM.qty_defects > 0,  # AC3: Exclude zero-defect records
                )
            )
        )
        
        # Add date range filter if provided
        if start_date:
            query = query.filter(InspectionRecordORM.inspection_date >= start_date)
        if end_date:
            query = query.filter(InspectionRecordORM.inspection_date <= end_date)
        
        records = query.all()
        
        # Calculate week bounds for each week that has occurrences
        # Using ISO week calculation: Monday=week start, Sunday=week end
        weeks: Dict[int, Tuple[int, date, date]] = {}
        
        for record in records:
            # Python's datetime.isocalendar() returns (year, week, weekday)
            year, week_num, _ = record.inspection_date.isocalendar()
            
            if week_num not in weeks:
                # Calculate week start (Monday) and week end (Sunday)
                week_start = self._get_week_start_date(record.inspection_date)
                week_end = self._get_week_end_date(record.inspection_date)
                weeks[week_num] = (week_num, week_start, week_end)
        
        # Return sorted by week number
        return sorted(list(weeks.values()), key=lambda x: x[0])
    
    def get_non_zero_records_for_defect(
        self, defect_code: str, start_date: date = None, end_date: date = None
    ) -> List[InspectionRecord]:
        """
        Get all inspection records for a defect where qty_defects > 0.
        
        Per AC3, records with qty_defects = 0 should not be counted as occurrences.
        This method filters them out.
        
        Time Complexity: O(log n + k) where k is non-zero records
        Space Complexity: O(k)
        
        Args:
            defect_code (str): The defect classification code
            start_date (date, optional): Inclusive start date
            end_date (date, optional): Inclusive end date
        
        Returns:
            List[InspectionRecord]: Non-zero records, sorted by date
        """
        query = (
            self.session.query(InspectionRecordORM)
            .join(DefectORM, InspectionRecordORM.defect_id == DefectORM.id)
            .filter(
                and_(
                    DefectORM.defect_code == defect_code,
                    InspectionRecordORM.qty_defects > 0,
                )
            )
        )
        
        if start_date:
            query = query.filter(InspectionRecordORM.inspection_date >= start_date)
        if end_date:
            query = query.filter(InspectionRecordORM.inspection_date <= end_date)
        
        orm_records = query.order_by(InspectionRecordORM.inspection_date).all()
        return [self._to_domain_model(orm) for orm in orm_records]
    
    def get_distinct_lots_for_defect(self, defect_code: str) -> List[str]:
        """
        Get all distinct lot IDs where a defect appears (with qty_defects > 0).
        
        Used to count "lots affected" (AC5).
        
        Time Complexity: O(log n + k) where k is records
        Space Complexity: O(l) where l is number of distinct lots
        
        Args:
            defect_code (str): The defect classification code
        
        Returns:
            List[str]: List of distinct lot_ids
        """
        lot_ids = (
            self.session.query(LotORM.lot_id)
            .join(InspectionRecordORM, LotORM.id == InspectionRecordORM.lot_id)
            .join(DefectORM, InspectionRecordORM.defect_id == DefectORM.id)
            .filter(
                and_(
                    DefectORM.defect_code == defect_code,
                    InspectionRecordORM.qty_defects > 0,
                )
            )
            .distinct()
            .order_by(LotORM.lot_id)
            .all()
        )
        return [lot_id[0] for lot_id in lot_ids]
    
    def get_incomplete_data_ranges(
        self, start_date: date, end_date: date
    ) -> List[Tuple[date, date]]:
        """
        Get date ranges within the query window where data appears incomplete.
        
        Per AC4, we need to flag periods where data is incomplete so we can
        trigger "Insufficient data" classification.
        
        This checks the is_data_complete flag to identify periods with gaps.
        
        Time Complexity: O(log n + k) where k is records in range
        Space Complexity: O(g) where g is number of gap periods
        
        Args:
            start_date (date): Query window start
            end_date (date): Query window end
        
        Returns:
            List[Tuple[date, date]]: List of (gap_start, gap_end) date ranges
        """
        # Find records marked as incomplete
        incomplete_records = (
            self.session.query(InspectionRecordORM)
            .filter(
                and_(
                    InspectionRecordORM.is_data_complete == False,
                    InspectionRecordORM.inspection_date >= start_date,
                    InspectionRecordORM.inspection_date <= end_date,
                )
            )
            .order_by(InspectionRecordORM.inspection_date)
            .all()
        )
        
        if not incomplete_records:
            return []
        
        # Merge consecutive incomplete gaps into ranges
        gaps: List[Tuple[date, date]] = []
        current_start = incomplete_records[0].inspection_date
        current_end = incomplete_records[0].inspection_date
        
        for record in incomplete_records[1:]:
            days_diff = (record.inspection_date - current_end).days
            
            # If gap is <= 1 day, consider it continuous
            if days_diff <= 1:
                current_end = record.inspection_date
            else:
                # End the current gap and start a new one
                gaps.append((current_start, current_end))
                current_start = record.inspection_date
                current_end = record.inspection_date
        
        # Add final gap
        gaps.append((current_start, current_end))
        
        return gaps
    
    # ==================== Helper Methods ====================
    
    @staticmethod
    def _to_domain_model(orm_record: InspectionRecordORM) -> InspectionRecord:
        """
        Convert ORM model to domain model.
        
        Time Complexity: O(1)
        Space Complexity: O(1) - converting fixed attributes
        
        Args:
            orm_record: SQLAlchemy ORM record
        
        Returns:
            InspectionRecord: Domain model instance
        """
        if orm_record is None:
            return None
        return InspectionRecord(
            id=orm_record.id,
            inspection_id=orm_record.inspection_id,
            lot_id=orm_record.lot_id,
            defect_id=orm_record.defect_id,
            inspection_date=orm_record.inspection_date,
            qty_defects=orm_record.qty_defects,
            is_data_complete=orm_record.is_data_complete,
        )
    
    @staticmethod
    def _get_week_start_date(d: date) -> date:
        """
        Get the Monday (start) of the ISO week containing date d.
        
        ISO week starts on Monday (weekday 0).
        
        Time Complexity: O(1)
        
        Args:
            d (date): Any date in the week
        
        Returns:
            date: Monday of that week
        """
        # weekday() returns 0=Monday, 6=Sunday
        return d - __import__('datetime').timedelta(days=d.weekday())
    
    @staticmethod
    def _get_week_end_date(d: date) -> date:
        """
        Get the Sunday (end) of the ISO week containing date d.
        
        ISO week ends on Sunday (weekday 6).
        
        Time Complexity: O(1)
        
        Args:
            d (date): Any date in the week
        
        Returns:
            date: Sunday of that week
        """
        # weekday() returns 0=Monday, so add (6 - weekday()) to get to Sunday
        days_to_sunday = 6 - d.weekday()
        return d + __import__('datetime').timedelta(days=days_to_sunday)


class DefectRepository:
    """
    Repository for accessing defect master data.
    
    Simple repository for defect lookups.
    """
    
    def __init__(self, session: Session):
        """Initialize with a database session"""
        self.session = session
    
    def get_all(self) -> List[Defect]:
        """
        Get all defects.
        
        Time Complexity: O(n) where n is number of defects
        Space Complexity: O(n)
        """
        defects = (
            self.session.query(DefectORM)
            .order_by(DefectORM.defect_code)
            .all()
        )
        return [self._to_domain_model(d) for d in defects]
    
    def get_by_code(self, defect_code: str) -> Optional[Defect]:
        """
        Get a defect by its code.
        
        Time Complexity: O(log n) with unique index
        Space Complexity: O(1)
        """
        defect = (
            self.session.query(DefectORM)
            .filter(DefectORM.defect_code == defect_code)
            .first()
        )
        return self._to_domain_model(defect) if defect else None
    
    @staticmethod
    def _to_domain_model(orm_defect: DefectORM) -> Defect:
        """Convert ORM to domain model"""
        if orm_defect is None:
            return None
        return Defect(id=orm_defect.id, defect_code=orm_defect.defect_code)


class LotRepository:
    """
    Repository for accessing lot master data.
    
    Simple repository for lot lookups.
    """
    
    def __init__(self, session: Session):
        """Initialize with a database session"""
        self.session = session
    
    def get_all(self) -> List[Lot]:
        """
        Get all lots.
        
        Time Complexity: O(n)
        Space Complexity: O(n)
        """
        lots = (
            self.session.query(LotORM)
            .order_by(LotORM.lot_id)
            .all()
        )
        return [self._to_domain_model(lot) for lot in lots]
    
    def get_by_id(self, lot_id: str) -> Optional[Lot]:
        """
        Get a lot by its ID.
        
        Time Complexity: O(log n)
        Space Complexity: O(1)
        """
        lot = (
            self.session.query(LotORM)
            .filter(LotORM.lot_id == lot_id)
            .first()
        )
        return self._to_domain_model(lot) if lot else None
    
    @staticmethod
    def _to_domain_model(orm_lot: LotORM) -> Lot:
        """Convert ORM to domain model"""
        if orm_lot is None:
            return None
        return Lot(id=orm_lot.id, lot_id=orm_lot.lot_id)
