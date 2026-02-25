"""
defect_repository.py — Data Access Layer for defect records.

This module is the *only* place that touches the database for defect-related
queries.  The service layer calls these functions; the UI layer never calls
them directly.

Key concepts:
    Repository pattern:  A class whose sole job is to run database queries and
                         return results.  It hides SQL details from the rest of
                         the application.
    Session:             A SQLAlchemy session that you pass in so the
                         repository can execute queries.
"""

from sqlalchemy.orm import Session

from src.models import Defect


class DefectRepository:
    """Provides database queries for defect records.

    Usage::

        repo = DefectRepository(session)
        defects = repo.get_all_defects()

    Args:
        session: An active SQLAlchemy ``Session`` obtained from
                 ``database.get_session()``.
    """

    def __init__(self, session: Session):
        self._session = session

    def get_all_defects(self) -> list[Defect]:
        """Return all defect records.

        Returns:
            A list of ``Defect`` domain objects.
        """
        # TODO: implement — query defects table and return all rows.
        return []

    def get_defect_by_code(self, defect_code: str) -> Defect | None:
        """Return a single defect by its business key.

        Args:
            defect_code: The defect's unique business key (e.g., 'DEF-001').

        Returns:
            A ``Defect`` domain object, or ``None`` if not found.
        """
        # TODO: implement — query defects table filtered by defect_code.
        return None
