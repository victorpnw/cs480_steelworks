from abc import ABC, abstractmethod
from datetime import date
from typing import List

from .models import InspectionRecord


class InspectionRepository(ABC):
    """Abstract repository for fetching inspection records.

    Implementations should handle DB access, queries and mapping to
    `InspectionRecord` dataclasses. All methods are stubs here.
    """

    @abstractmethod
    def get_inspection_records(self, start_date: date, end_date: date) -> List[InspectionRecord]:
        """Return all inspection records in the inclusive date range.

        Note: AC3 requires ignoring records where `qty_defects == 0` in
        classification logic; repository implementations may include that
        filter or leave it to the service layer.
        """
        raise NotImplementedError()

    @abstractmethod
    def get_records_for_defect(self, defect_code: str, start_date: date, end_date: date) -> List[InspectionRecord]:
        """Return inspection records for a specific defect code in range."""
        raise NotImplementedError()
