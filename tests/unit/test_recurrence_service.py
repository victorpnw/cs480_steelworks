import pytest
from datetime import date
from typing import List, Optional

from recurring_defects.models import InspectionRecord, DefectListRow
from recurring_defects.service import RecurrenceService


class DummyRepo:
    """In-memory repository used in unit tests.

    Initialize with an optional list of `InspectionRecord` objects. The
    methods filter by date range and/or defect code to simulate a real
    repository.
    """

    def __init__(self, records: Optional[List[InspectionRecord]] = None):
        self._records: List[InspectionRecord] = records or []

    def add(self, record: InspectionRecord) -> None:
        self._records.append(record)

    def get_inspection_records(self, start_date: date, end_date: date) -> List[InspectionRecord]:
        """Return records with inspection_date between start_date and end_date (inclusive)."""
        return [
            r for r in self._records
            if start_date <= r.inspection_date <= end_date
        ]

    def get_records_for_defect(self, defect_code: str, start_date: date, end_date: date) -> List[InspectionRecord]:
        """Return records matching the defect_code in the given date range.

        Note: `defect_code` mapping to `defect_id` is not managed here; tests
        should create `InspectionRecord` instances with matching `defect_id`
        values and know which id corresponds to the defect_code under test.
        """
        # In tests we typically create records referencing defect ids directly.
        # For convenience, support passing defect_code like 'DEF-001' by parsing
        # the numeric suffix if present (e.g., DEF-001 -> 1).
        parsed_id: Optional[int] = None
        if defect_code and defect_code.upper().startswith("DEF-"):
            try:
                parsed_id = int(defect_code.split("-")[-1])
            except ValueError:
                parsed_id = None

        def matches(r: InspectionRecord) -> bool:
            in_range = start_date <= r.inspection_date <= end_date
            if parsed_id is not None:
                return in_range and r.defect_id == parsed_id
            return in_range

        return [r for r in self._records if matches(r)]


def test_evaluate_recurring_classification():
    """AC1: When defect appears in more than one calendar week -> Recurring."""
    # Arrange: use DummyRepo and add two non-zero records for the same defect
    repo = DummyRepo()
    repo.add(InspectionRecord(id=1, inspection_id="i1", lot_id=10, defect_id=1, inspection_date=date(2026, 1, 4), qty_defects=5, is_data_complete=True))
    repo.add(InspectionRecord(id=2, inspection_id="i2", lot_id=11, defect_id=1, inspection_date=date(2026, 1, 12), qty_defects=3, is_data_complete=True))

    service = RecurrenceService(repository=repo)

    # Act
    result = service.evaluate_defects(start_date=date(2026, 1, 1), end_date=date(2026, 1, 31))

    # Assert: expected shape and an entry for defect_id 1 marked Recurring
    assert isinstance(result, list)
    assert any(isinstance(r, DefectListRow) and getattr(r, "defect_id", None) == 1 and r.status == "Recurring" for r in result)


def test_single_lot_not_recurring():
    """AC2: Same lot-only occurrences should not be Recurring."""
    pytest.skip("stub - implement with repository mock and assertions")


def test_zero_defects_ignored():
    """AC3: Records with qty_defects == 0 must be ignored in counts."""
    pytest.skip("stub - implement with repository mock and assertions")


def test_insufficient_data_marked():
    """AC4 / AC8: When data is incomplete, service should indicate insufficient data."""
    pytest.skip("stub - implement with repository mock and assertions")


def test_list_view_fields_present():
    """AC5: List rows contain required fields for the UI."""
    pytest.skip("stub - assert DefectListRow fields and types")


def test_drilldown_detail_view_structure():
    """AC7: Detail view contains week breakdown and underlying records."""
    pytest.skip("stub - implement with repository mock and assertions")
