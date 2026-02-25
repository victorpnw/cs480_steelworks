"""
Test Suite for Recurring Defects Classification

This module contains comprehensive unit tests covering all Acceptance Criteria (AC1-AC9).

Test Strategy:
  - Use pytest for test framework
  - Mock repositories to isolate business logic
  - Test each AC with multiple scenarios
  - Test boundary conditions and edge cases

Test Organization:
  - Fixtures: Reusable test data
  - Test Classes: Grouped by AC or feature
  - Each test is independent and can run in any order

Time Complexity of Tests:
  - Test setup (fixtures): O(1)
  - Each test: O(k) where k is mocked data size (small)
  - Total suite runtime: < 5 seconds

AC to Test Mapping:
  - AC1 (Multi-week recurring): test_ac1_*
  - AC2 (Single-lot defects): test_ac2_*
  - AC3 (Zero defects excluded): test_ac3_*
  - AC4 (Insufficient data): test_ac4_*
  - AC5 (List view fields): test_ac5_*
  - AC6 (Visual highlight/filter): test_ac6_*
  - AC7 (Drill-down view): test_ac7_*
  - AC8 (Incomplete messaging): test_ac8_*
  - AC9 (Sorting): test_ac9_*
"""

import pytest
from datetime import date, timedelta
from unittest.mock import Mock, MagicMock, patch
from typing import List

from src.models import (
    InspectionRecord,
    RecurringDefectResult,
    DefectDetailResult,
)
from src.services import RecurringDefectClassificationService
from src.repositories import InspectionRecordRepository, DefectRepository


# ==================== FIXTURES ====================


@pytest.fixture
def mock_inspection_repo():
    """Create a mock inspection repository for testing"""
    return Mock(spec=InspectionRecordRepository)


@pytest.fixture
def mock_defect_repo():
    """Create a mock defect repository for testing"""
    return Mock(spec=DefectRepository)


@pytest.fixture
def service(mock_inspection_repo, mock_defect_repo):
    """Create a service instance with mocked dependencies"""
    return RecurringDefectClassificationService(mock_inspection_repo, mock_defect_repo)


@pytest.fixture
def sample_base_date():
    """Create a base date for consistent testing (Monday, 2026-01-05)"""
    return date(2026, 1, 5)  # Monday of week 2


# ==================== AC1: Multi-Week Recurring Defects ====================


class TestAC1_MultiWeekRecurring:
    """
    AC1: Definition of 'recurring'
    
    Given inspection records from multiple lots,
    When the same defect code appears in inspection records in more than one calendar week,
    Then the defect should be classified as a recurring issue.
    """
    
    def test_ac1_defect_in_two_weeks_is_recurring(
        self, service, mock_inspection_repo, sample_base_date
    ):
        """
        Test Case: Defect appears in week 1 and week 2 → Recurring
        
        Expected: status = "Recurring"
        """
        # Arrange: Create records spanning 2 weeks
        week1_monday = sample_base_date
        week2_monday = sample_base_date + timedelta(days=7)
        
        records = [
            InspectionRecord(1, "INV-1", 1, 1, week1_monday, qty_defects=1),
            InspectionRecord(2, "INV-2", 2, 1, week2_monday, qty_defects=1),
        ]
        
        mock_inspection_repo.get_all_defect_codes.return_value = ["DEFECT_A"]
        mock_inspection_repo.get_non_zero_records_for_defect.return_value = records
        mock_inspection_repo.get_incomplete_data_ranges.return_value = []
        
        # Act
        results = service.classify_defects(
            sample_base_date,
            sample_base_date + timedelta(days=14)
        )
        
        # Assert
        assert len(results) == 1
        assert results[0].defect_code == "DEFECT_A"
        assert results[0].status == "Recurring"
        assert results[0].weeks_with_occurrences == 2
    
    def test_ac1_defect_in_three_weeks_is_recurring(
        self, service, mock_inspection_repo, sample_base_date
    ):
        """
        Test Case: Defect appears in weeks 1, 3, and 5 (non-consecutive) → Recurring
        
        Expected: status = "Recurring", weeks_with_occurrences = 3
        """
        # Arrange
        records = [
            InspectionRecord(1, "INV-1", 1, 1, sample_base_date, qty_defects=2),
            InspectionRecord(2, "INV-2", 2, 1, sample_base_date + timedelta(days=14), qty_defects=1),
            InspectionRecord(3, "INV-3", 3, 1, sample_base_date + timedelta(days=28), qty_defects=3),
        ]
        
        mock_inspection_repo.get_all_defect_codes.return_value = ["DEFECT_B"]
        mock_inspection_repo.get_non_zero_records_for_defect.return_value = records
        mock_inspection_repo.get_incomplete_data_ranges.return_value = []
        
        # Act
        results = service.classify_defects(
            sample_base_date,
            sample_base_date + timedelta(days=35)
        )
        
        # Assert
        assert results[0].status == "Recurring"
        assert results[0].weeks_with_occurrences == 3
        assert results[0].total_qty_defects == 6


# ==================== AC2: Single-Lot / Single-Week Defects ====================


class TestAC2_SingleWeekNotRecurring:
    """
    AC2: Single lot defects
    
    Given multiple inspection records for the same lot,
    When the same defect code appears only within that single lot and 
         does not appear in other lots,
    Then the defect should not be classified as recurring.
    
    Note: This is technically about "single lot", but the classification metric is
    "appears in only one calendar week". We test both interpretations.
    """
    
    def test_ac2_defect_only_in_one_week_not_recurring(
        self, service, mock_inspection_repo, sample_base_date
    ):
        """
        Test Case: Defect appears only in one calendar week → Not recurring
        
        Note: Multiple lots in same week is fine; it's the week count that matters.
        
        Expected: status = "Not recurring"
        """
        # Arrange: Records from 2 lots, but same week
        records = [
            InspectionRecord(1, "INV-1", 1, 1, sample_base_date, qty_defects=1),
            InspectionRecord(2, "INV-2", 2, 1, sample_base_date + timedelta(days=2), qty_defects=1),
        ]
        
        mock_inspection_repo.get_all_defect_codes.return_value = ["DEFECT_C"]
        mock_inspection_repo.get_non_zero_records_for_defect.return_value = records
        mock_inspection_repo.get_incomplete_data_ranges.return_value = []
        
        # Act
        results = service.classify_defects(
            sample_base_date,
            sample_base_date + timedelta(days=6)  # Single week
        )
        
        # Assert
        assert len(results) == 1
        assert results[0].status == "Not recurring"
        assert results[0].weeks_with_occurrences == 1
        assert results[0].lots_affected == 2  # Multiple lots is OK
    
    def test_ac2_multiple_records_same_lot_same_week_not_recurring(
        self, service, mock_inspection_repo, sample_base_date
    ):
        """
        Test Case: Multiple inspections of same defect in same lot, same week → Not recurring
        
        Expected: status = "Not recurring", qty summed
        """
        # Arrange: Same lot, different days of the week
        records = [
            InspectionRecord(1, "INV-1", 1, 1, sample_base_date, qty_defects=2),
            InspectionRecord(2, "INV-2", 1, 1, sample_base_date + timedelta(days=3), qty_defects=3),
        ]
        
        mock_inspection_repo.get_all_defect_codes.return_value = ["DEFECT_D"]
        mock_inspection_repo.get_non_zero_records_for_defect.return_value = records
        mock_inspection_repo.get_incomplete_data_ranges.return_value = []
        
        # Act
        results = service.classify_defects(
            sample_base_date,
            sample_base_date + timedelta(days=6)
        )
        
        # Assert
        assert results[0].status == "Not recurring"
        assert results[0].weeks_with_occurrences == 1
        assert results[0].lots_affected == 1
        assert results[0].total_qty_defects == 5


# ==================== AC3: Zero Defects Excluded ====================


class TestAC3_ZeroDefectsExcluded:
    """
    AC3: Zero Defects
    
    Given an inspection record with Qty Defects equal to 0,
    When evaluating whether a defect is recurring,
    Then that record should not be counted as an occurrence of the defect.
    """
    
    def test_ac3_zero_defects_record_ignored(
        self, service, mock_inspection_repo, sample_base_date
    ):
        """
        Test Case: Week 1 has qty_defects=0, Week 2 has qty_defects=1 → Not recurring
        
        The Week 1 record should be ignored, leaving only Week 2.
        
        Expected: status = "Not recurring", weeks_with_occurrences = 1
        """
        # Arrange: Mock returns only NON-ZERO records (as per AC3)
        # This is the key: the repository's get_non_zero_records_for_defect
        # already filters out zero-defect records
        records = [
            InspectionRecord(2, "INV-2", 1, 1, sample_base_date + timedelta(days=7), qty_defects=1),
        ]
        
        mock_inspection_repo.get_all_defect_codes.return_value = ["DEFECT_E"]
        mock_inspection_repo.get_non_zero_records_for_defect.return_value = records
        mock_inspection_repo.get_incomplete_data_ranges.return_value = []
        
        # Act
        results = service.classify_defects(
            sample_base_date,
            sample_base_date + timedelta(days=14)
        )
        
        # Assert
        assert results[0].status == "Not recurring"
        assert results[0].weeks_with_occurrences == 1
    
    def test_ac3_all_zero_defects_no_results(
        self, service, mock_inspection_repo, sample_base_date
    ):
        """
        Test Case: All records for a defect have qty_defects=0 → No result returned
        
        Expected: defect filtered out entirely (empty results)
        """
        # Arrange
        mock_inspection_repo.get_all_defect_codes.return_value = ["DEFECT_F"]
        mock_inspection_repo.get_non_zero_records_for_defect.return_value = []
        mock_inspection_repo.get_incomplete_data_ranges.return_value = []
        
        # Act
        results = service.classify_defects(
            sample_base_date,
            sample_base_date + timedelta(days=14)
        )
        
        # Assert
        assert len(results) == 0


# ==================== AC4: Incomplete Data ====================


class TestAC4_InsufficientData:
    """
    AC4: Incomplete Data
    
    Given incomplete inspection data for certain time periods,
    When it is not possible to determine whether a defect appears across multiple weeks,
    Then the system should indicate insufficient data rather than classify the defect.
    """
    
    def test_ac4_incomplete_data_status(
        self, service, mock_inspection_repo, sample_base_date
    ):
        """
        Test Case: Defect has records in 2 weeks, but data is incomplete → Insufficient data status
        
        Expected: status = "Insufficient data" (not "Recurring")
        """
        # Arrange
        records = [
            InspectionRecord(1, "INV-1", 1, 1, sample_base_date, qty_defects=1),
            InspectionRecord(2, "INV-2", 2, 1, sample_base_date + timedelta(days=7), qty_defects=1),
        ]
        
        # Mock incomplete periods that overlap with defect date range
        incomplete_periods = [
            (sample_base_date + timedelta(days=3), sample_base_date + timedelta(days=5))
        ]
        
        mock_inspection_repo.get_all_defect_codes.return_value = ["DEFECT_G"]
        mock_inspection_repo.get_non_zero_records_for_defect.return_value = records
        mock_inspection_repo.get_incomplete_data_ranges.return_value = incomplete_periods
        
        # Act
        results = service.classify_defects(
            sample_base_date,
            sample_base_date + timedelta(days=14)
        )
        
        # Assert
        assert results[0].status == "Insufficient data"
        assert len(results[0].incomplete_periods) > 0
    
    def test_ac4_no_incomplete_data_normal_classification(
        self, service, mock_inspection_repo, sample_base_date
    ):
        """
        Test Case: Defect in 2 weeks, no incomplete data → Normal classification
        
        Expected: status = "Recurring"
        """
        # Arrange
        records = [
            InspectionRecord(1, "INV-1", 1, 1, sample_base_date, qty_defects=1),
            InspectionRecord(2, "INV-2", 2, 1, sample_base_date + timedelta(days=7), qty_defects=1),
        ]
        
        mock_inspection_repo.get_all_defect_codes.return_value = ["DEFECT_H"]
        mock_inspection_repo.get_non_zero_records_for_defect.return_value = records
        mock_inspection_repo.get_incomplete_data_ranges.return_value = []
        
        # Act
        results = service.classify_defects(
            sample_base_date,
            sample_base_date + timedelta(days=14)
        )
        
        # Assert
        assert results[0].status == "Recurring"


# ==================== AC5: List View Fields ====================


class TestAC5_ListViewFields:
    """
    AC5: List/table view with required fields
    
    Given the user opens the "Recurring Defects" view for a selected date range,
    When the system finishes evaluating defects using AC1–AC4,
    Then the system should display a list/table where each row includes:
      - Defect Code
      - Status (Recurring / Not recurring / Insufficient data)
      - # of calendar weeks with occurrences
      - # of lots affected
      - First seen date, Last seen date
      - Total Qty Defects
    """
    
    def test_ac5_all_required_fields_present(
        self, service, mock_inspection_repo, sample_base_date
    ):
        """
        Test Case: Result contains all required fields
        
        Expected: RecurringDefectResult has all AC5 fields
        """
        # Arrange
        records = [
            InspectionRecord(1, "INV-1", 1, 1, sample_base_date, qty_defects=5),
            InspectionRecord(2, "INV-2", 2, 1, sample_base_date + timedelta(days=7), qty_defects=3),
        ]
        
        mock_inspection_repo.get_all_defect_codes.return_value = ["DEFECT_I"]
        mock_inspection_repo.get_non_zero_records_for_defect.return_value = records
        mock_inspection_repo.get_incomplete_data_ranges.return_value = []
        
        # Act
        results = service.classify_defects(
            sample_base_date,
            sample_base_date + timedelta(days=14)
        )
        
        # Assert: Check all AC5 fields
        result = results[0]
        assert result.defect_code == "DEFECT_I"
        assert result.status in ["Recurring", "Not recurring", "Insufficient data"]
        assert result.weeks_with_occurrences == 2
        assert result.lots_affected == 2
        assert result.first_seen_date == sample_base_date
        assert result.last_seen_date == sample_base_date + timedelta(days=7)
        assert result.total_qty_defects == 8
    
    def test_ac5_total_qty_defects_sum_only_nonzero(
        self, service, mock_inspection_repo, sample_base_date
    ):
        """
        Test Case: Total Qty Defects sums only non-zero records
        
        Expected: total_qty_defects = sum of all qty_defects in non-zero records
        """
        # Arrange
        records = [
            InspectionRecord(1, "INV-1", 1, 1, sample_base_date, qty_defects=10),
            InspectionRecord(2, "INV-2", 1, 1, sample_base_date + timedelta(days=1), qty_defects=5),
            InspectionRecord(3, "INV-3", 2, 1, sample_base_date + timedelta(days=7), qty_defects=3),
        ]
        
        mock_inspection_repo.get_all_defect_codes.return_value = ["DEFECT_J"]
        mock_inspection_repo.get_non_zero_records_for_defect.return_value = records
        mock_inspection_repo.get_incomplete_data_ranges.return_value = []
        
        # Act
        results = service.classify_defects(
            sample_base_date,
            sample_base_date + timedelta(days=14)
        )
        
        # Assert
        assert results[0].total_qty_defects == 18  # 10 + 5 + 3


# ==================== AC6: Visual Highlight and Filter ====================


class TestAC6_VisualHighlightAndFilter:
    """
    AC6: Visual highlight and filter for recurring defects
    
    Given the list is displayed,
    When a defect code has Status = Recurring,
    Then it should be visually distinguishable (e.g., a "Recurring" badge/icon),
    And the user should be able to filter the list to show only Recurring defects.
    
    Note: Visual highlighting is UI-layer concern (Streamlit). Here we test
    that the status field is correctly set and sortable.
    """
    
    def test_ac6_status_correctly_set_for_filtering(
        self, service, mock_inspection_repo, sample_base_date
    ):
        """
        Test Case: Results have correct status for filtering
        
        Expected: Can filter by status field
        """
        # Arrange: Mix of recurring and non-recurring
        recurring_records = [
            InspectionRecord(1, "INV-1", 1, 1, sample_base_date, qty_defects=1),
            InspectionRecord(2, "INV-2", 2, 1, sample_base_date + timedelta(days=7), qty_defects=1),
        ]
        not_recurring_records = [
            InspectionRecord(3, "INV-3", 1, 2, sample_base_date, qty_defects=1),
        ]
        
        def mock_get_nonzero(code, start, end):
            if code == "RECURRING_DEFECT":
                return recurring_records
            elif code == "NOT_RECURRING":
                return not_recurring_records
            return []
        
        mock_inspection_repo.get_all_defect_codes.return_value = ["RECURRING_DEFECT", "NOT_RECURRING"]
        mock_inspection_repo.get_non_zero_records_for_defect.side_effect = mock_get_nonzero
        mock_inspection_repo.get_incomplete_data_ranges.return_value = []
        
        # Act
        results = service.classify_defects(
            sample_base_date,
            sample_base_date + timedelta(days=14)
        )
        
        # Assert
        recurring_results = [r for r in results if r.status == "Recurring"]
        not_recurring_results = [r for r in results if r.status == "Not recurring"]
        
        assert len(recurring_results) == 1
        assert len(not_recurring_results) == 1
        assert recurring_results[0].defect_code == "RECURRING_DEFECT"
        assert not_recurring_results[0].defect_code == "NOT_RECURRING"


# ==================== AC7: Drill-down Detail View ====================


class TestAC7_DrillDownDetailView:
    """
    AC7: Drill-down detail view by defect code
    
    Given the list is displayed,
    When the user selects a defect code,
    Then the system should show a detail view that includes:
      - A time breakdown by calendar week
      - For each week: lots involved and total Qty Defects that week
      - The underlying inspection records used for the calculation
    """
    
    def test_ac7_detail_includes_weekly_breakdown(
        self, service, mock_inspection_repo, mock_defect_repo, sample_base_date
    ):
        """
        Test Case: Detail view includes weekly breakdown with lots and quantities
        
        Expected: weekly_breakdown dict with week data
        """
        # Arrange
        records = [
            InspectionRecord(1, "INV-1", 1, 1, sample_base_date, qty_defects=5),
            InspectionRecord(2, "INV-2", 2, 1, sample_base_date + timedelta(days=2), qty_defects=3),
            InspectionRecord(3, "INV-3", 1, 1, sample_base_date + timedelta(days=7), qty_defects=2),
        ]
        
        mock_inspection_repo.get_non_zero_records_for_defect.return_value = records
        mock_inspection_repo.get_all_defect_codes.return_value = ["DEFECT_K"]
        mock_inspection_repo.get_incomplete_data_ranges.return_value = []
        
        # Mock _get_week_start_date and _get_week_end_date
        def mock_week_start(d):
            return d - __import__('datetime').timedelta(days=d.weekday())
        
        def mock_week_end(d):
            return d + __import__('datetime').timedelta(days=6 - d.weekday())
        
        mock_inspection_repo._get_week_start_date = mock_week_start
        mock_inspection_repo._get_week_end_date = mock_week_end
        
        # Act
        detail = service.get_defect_detail(
            "DEFECT_K",
            sample_base_date,
            sample_base_date + timedelta(days=14)
        )
        
        # Assert
        assert detail is not None
        assert detail.defect_code == "DEFECT_K"
        assert len(detail.weekly_breakdown) >= 1
        
        # Check that weekly breakdown has required structure
        for week_key, week_data in detail.weekly_breakdown.items():
            assert "week_start" in week_data
            assert "week_end" in week_data
            assert "lots" in week_data
            assert "total_qty_defects" in week_data
            assert "records" in week_data
    
    def test_ac7_underlying_records_included(
        self, service, mock_inspection_repo, sample_base_date
    ):
        """
        Test Case: Detail view includes all underlying records
        
        Expected: underlying_records list contains all inspection records
        """
        # Arrange
        records = [
            InspectionRecord(1, "INV-1", 1, 1, sample_base_date, qty_defects=1),
            InspectionRecord(2, "INV-2", 2, 1, sample_base_date + timedelta(days=7), qty_defects=1),
        ]
        
        mock_inspection_repo.get_non_zero_records_for_defect.return_value = records
        mock_inspection_repo.get_all_defect_codes.return_value = ["DEFECT_L"]
        mock_inspection_repo.get_incomplete_data_ranges.return_value = []
        mock_inspection_repo._get_week_start_date = lambda d: d
        mock_inspection_repo._get_week_end_date = lambda d: d
        
        # Act
        detail = service.get_defect_detail(
            "DEFECT_L",
            sample_base_date,
            sample_base_date + timedelta(days=14)
        )
        
        # Assert
        assert detail is not None
        assert len(detail.underlying_records) == 2


# ==================== AC8: Insufficient Data Messaging ====================


class TestAC8_InsufficientDataMessaging:
    """
    AC8: Insufficient data messaging with missing periods
    
    Given the system determines "Insufficient data" per AC4,
    When displaying results,
    Then the system should indicate which time period(s) are incomplete and why 
         the classification was not made.
    """
    
    def test_ac8_incomplete_periods_in_result(
        self, service, mock_inspection_repo, sample_base_date
    ):
        """
        Test Case: Result includes incomplete periods
        
        Expected: incomplete_periods list populated in result
        """
        # Arrange
        records = [
            InspectionRecord(1, "INV-1", 1, 1, sample_base_date, qty_defects=1),
            InspectionRecord(2, "INV-2", 2, 1, sample_base_date + timedelta(days=7), qty_defects=1),
        ]
        
        incomplete_periods = [
            (sample_base_date + timedelta(days=3), sample_base_date + timedelta(days=5))
        ]
        
        mock_inspection_repo.get_all_defect_codes.return_value = ["DEFECT_M"]
        mock_inspection_repo.get_non_zero_records_for_defect.return_value = records
        mock_inspection_repo.get_incomplete_data_ranges.return_value = incomplete_periods
        
        # Act
        results = service.classify_defects(
            sample_base_date,
            sample_base_date + timedelta(days=14)
        )
        
        # Assert
        assert results[0].incomplete_periods == incomplete_periods
        assert len(results[0].incomplete_periods) > 0
    
    def test_ac8_detail_view_shows_incomplete_periods(
        self, service, mock_inspection_repo, sample_base_date
    ):
        """
        Test Case: Detail view includes incomplete periods
        
        Expected: DefectDetailResult.incomplete_periods is populated
        """
        # Arrange
        records = [
            InspectionRecord(1, "INV-1", 1, 1, sample_base_date, qty_defects=1),
        ]
        
        incomplete_periods = [
            (sample_base_date + timedelta(days=1), sample_base_date + timedelta(days=2))
        ]
        
        mock_inspection_repo.get_non_zero_records_for_defect.return_value = records
        mock_inspection_repo.get_all_defect_codes.return_value = ["DEFECT_N"]
        mock_inspection_repo.get_incomplete_data_ranges.return_value = incomplete_periods
        mock_inspection_repo._get_week_start_date = lambda d: d
        mock_inspection_repo._get_week_end_date = lambda d: d
        
        # Act
        detail = service.get_defect_detail(
            "DEFECT_N",
            sample_base_date,
            sample_base_date + timedelta(days=7)
        )
        
        # Assert
        assert detail is not None
        assert detail.incomplete_periods == incomplete_periods


# ==================== AC9: Sorting and Prioritization ====================


class TestAC9_DefaultSortingAndPrioritization:
    """
    AC9: Default sorting and prioritization
    
    Given the list is displayed,
    When no explicit sort is chosen,
    Then the default sort should prioritize Recurring defects first, 
         and within those sort by descending # of weeks (then descending # of lots).
    """
    
    def test_ac9_recurring_first_in_sort_order(
        self, service, mock_inspection_repo, sample_base_date
    ):
        """
        Test Case: Recurring defects appear before Not recurring
        
        Expected: results[0].status == "Recurring"
        """
        # Arrange: Create one recurring and one non-recurring
        def mock_get_nonzero(code, start, end):
            if code == "RECURRING":
                return [
                    InspectionRecord(1, "INV-1", 1, 1, sample_base_date, qty_defects=1),
                    InspectionRecord(2, "INV-2", 2, 1, sample_base_date + timedelta(days=7), qty_defects=1),
                ]
            else:  # NOT_RECURRING
                return [
                    InspectionRecord(3, "INV-3", 1, 2, sample_base_date, qty_defects=1),
                ]
        
        mock_inspection_repo.get_all_defect_codes.return_value = ["RECURRING", "NOT_RECURRING"]
        mock_inspection_repo.get_non_zero_records_for_defect.side_effect = mock_get_nonzero
        mock_inspection_repo.get_incomplete_data_ranges.return_value = []
        
        # Act
        results = service.classify_defects(
            sample_base_date,
            sample_base_date + timedelta(days=14)
        )
        
        # Assert
        # First result should be Recurring
        assert results[0].status == "Recurring"
        # Second should be Not recurring
        assert results[1].status == "Not recurring"
    
    def test_ac9_sort_by_weeks_descending_within_status(
        self, service, mock_inspection_repo, sample_base_date
    ):
        """
        Test Case: Within Recurring status, sort by weeks descending
        
        Expected: Defect with 3 weeks appears before defect with 2 weeks
        """
        # Arrange
        def mock_get_nonzero(code, start, end):
            if code == "DEFECT_3WEEKS":
                # Actually 3 weeks
                return [
                    InspectionRecord(1, "I1", 1, 1, sample_base_date, qty_defects=1),
                    InspectionRecord(2, "I2", 2, 1, sample_base_date + timedelta(days=7), qty_defects=1),
                    InspectionRecord(3, "I3", 3, 1, sample_base_date + timedelta(days=14), qty_defects=1),
                ]
            else:  # DEFECT_2WEEKS
                return [
                    InspectionRecord(4, "I4", 1, 2, sample_base_date, qty_defects=1),
                    InspectionRecord(5, "I5", 2, 2, sample_base_date + timedelta(days=7), qty_defects=1),
                ]
        
        mock_inspection_repo.get_all_defect_codes.return_value = ["DEFECT_3WEEKS", "DEFECT_2WEEKS"]
        mock_inspection_repo.get_non_zero_records_for_defect.side_effect = mock_get_nonzero
        mock_inspection_repo.get_incomplete_data_ranges.return_value = []
        
        # Act
        results = service.classify_defects(
            sample_base_date,
            sample_base_date + timedelta(days=21)
        )
        
        # Assert
        assert results[0].defect_code == "DEFECT_3WEEKS"
        assert results[0].weeks_with_occurrences == 3
        assert results[1].defect_code == "DEFECT_2WEEKS"
        assert results[1].weeks_with_occurrences == 2
    
    def test_ac9_sort_by_lots_descending_within_weeks(
        self, service, mock_inspection_repo, sample_base_date
    ):
        """
        Test Case: Within same week count, sort by lots descending
        
        Expected: Defect affecting 3 lots appears before defect affecting 2 lots
        """
        # Arrange
        def mock_get_nonzero(code, start, end):
            if code == "DEFECT_3LOTS":
                return [
                    InspectionRecord(1, "I1", 1, 1, sample_base_date, qty_defects=1),
                    InspectionRecord(2, "I2", 2, 1, sample_base_date, qty_defects=1),
                    InspectionRecord(3, "I3", 3, 1, sample_base_date, qty_defects=1),
                ]
            else:  # DEFECT_2LOTS
                return [
                    InspectionRecord(4, "I4", 1, 2, sample_base_date, qty_defects=1),
                    InspectionRecord(5, "I5", 2, 2, sample_base_date, qty_defects=1),
                ]
        
        mock_inspection_repo.get_all_defect_codes.return_value = ["DEFECT_3LOTS", "DEFECT_2LOTS"]
        mock_inspection_repo.get_non_zero_records_for_defect.side_effect = mock_get_nonzero
        mock_inspection_repo.get_incomplete_data_ranges.return_value = []
        
        # Act
        results = service.classify_defects(
            sample_base_date,
            sample_base_date + timedelta(days=6)
        )
        
        # Assert
        assert results[0].defect_code == "DEFECT_3LOTS"
        assert results[0].lots_affected == 3
        assert results[1].defect_code == "DEFECT_2LOTS"
        assert results[1].lots_affected == 2


# ==================== Edge Cases and Integration ====================


class TestEdgeCasesAndIntegration:
    """Test edge cases and integration scenarios"""
    
    def test_empty_date_range(self, service, mock_inspection_repo):
        """
        Test Case: No records in the selected date range
        
        Expected: Empty results list
        """
        # Arrange
        mock_inspection_repo.get_all_defect_codes.return_value = []
        
        # Act
        results = service.classify_defects(date(2026, 1, 1), date(2026, 1, 7))
        
        # Assert
        assert len(results) == 0
    
    def test_invalid_date_range(self, service):
        """
        Test Case: start_date > end_date
        
        Expected: ValueError raised
        """
        # Act & Assert
        with pytest.raises(ValueError):
            service.classify_defects(date(2026, 1, 10), date(2026, 1, 1))
    
    def test_single_day_range(self, service, mock_inspection_repo):
        """
        Test Case: Single day query window
        
        Expected: Works correctly
        """
        # Arrange
        base_date = date(2026, 1, 5)
        records = [
            InspectionRecord(1, "I1", 1, 1, base_date, qty_defects=1),
        ]
        
        mock_inspection_repo.get_all_defect_codes.return_value = ["DEFECT"]
        mock_inspection_repo.get_non_zero_records_for_defect.return_value = records
        mock_inspection_repo.get_incomplete_data_ranges.return_value = []
        
        # Act
        results = service.classify_defects(base_date, base_date)
        
        # Assert
        assert len(results) == 1
        assert results[0].weeks_with_occurrences == 1


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
