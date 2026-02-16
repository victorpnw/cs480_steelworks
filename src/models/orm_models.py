"""
SQLAlchemy ORM Models for Database Persistence

This module defines SQLAlchemy declarative models that map to the PostgreSQL database schema.
These are database-specific ORM models that handle persistence and relationships.

Separation from Domain Models:
  - `src/models/__init__.py` contains domain models (business logic layer)
  - This module contains ORM models (data access layer)
  - Services will translate between them as needed

Database Schema:
  - defects: Master table of defect types
  - lots: Master table of lot batches
  - inspection_records: Transactional table linking lots to defects with inspection data
"""

from sqlalchemy import Column, Integer, String, Date, Boolean, ForeignKey, TIMESTAMP, CheckConstraint
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from datetime import datetime, date

Base = declarative_base()


class DefectORM(Base):
    """
    SQLAlchemy ORM model for the 'defects' table.
    
    Stores the master list of defect types that can be found during inspections.
    
    Attributes:
        id (int): Primary key (surrogate key)
        defect_code (str): Business key - unique defect classification code (e.g., "CRACK_001")
        created_at (datetime): Timestamp when record was inserted
        
    Relationships:
        inspection_records: One-to-many relationship with InspectionRecordORM
    
    Database Constraints:
        - UNIQUE constraint on defect_code (business key uniqueness)
    """
    __tablename__ = "defects"
    
    id = Column(Integer, primary_key=True)
    defect_code = Column(String(50), nullable=False, unique=True)
    created_at = Column(TIMESTAMP, nullable=False, default=datetime.utcnow)
    
    # Relationship
    inspection_records = relationship("InspectionRecordORM", back_populates="defect",
                                      cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<DefectORM(id={self.id}, defect_code={self.defect_code})>"


class LotORM(Base):
    """
    SQLAlchemy ORM model for the 'lots' table.
    
    Stores the master list of manufacturing lots/batches.
    
    Attributes:
        id (int): Primary key (surrogate key)
        lot_id (str): Business key - unique lot identifier (e.g., "LOT-2026-001")
        created_at (datetime): Timestamp when record was inserted
    
    Relationships:
        inspection_records: One-to-many relationship with InspectionRecordORM
    
    Database Constraints:
        - UNIQUE constraint on lot_id (business key uniqueness)
    """
    __tablename__ = "lots"
    
    id = Column(Integer, primary_key=True)
    lot_id = Column(String(100), nullable=False, unique=True)
    created_at = Column(TIMESTAMP, nullable=False, default=datetime.utcnow)
    
    # Relationship
    inspection_records = relationship("InspectionRecordORM", back_populates="lot",
                                      cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<LotORM(id={self.id}, lot_id={self.lot_id})>"


class InspectionRecordORM(Base):
    """
    SQLAlchemy ORM model for the 'inspection_records' table.
    
    Transactional table storing the results of inspecting a lot for specific defects.
    Each record represents one inspection event on one date for one lot-defect combination.
    
    Attributes:
        id (int): Primary key (surrogate key)
        inspection_id (str): Business key - unique inspection identifier (UNIQUE constraint)
        lot_id (int): Foreign key referencing lots(id)
        defect_id (int): Foreign key referencing defects(id)
        inspection_date (date): Calendar date of the inspection
        qty_defects (int): Count of defects found (0 = no defects, >= 0 always)
        is_data_complete (bool): Flag indicating data completeness
            - True: Record exists or data gap is confirmed
            - False: Possible gap in data, cannot confirm completeness
    
    Relationships:
        lot: Many-to-one relationship with LotORM
        defect: Many-to-one relationship with DefectORM
    
    Database Constraints:
        - FOREIGN KEY constraints with CASCADE DELETE on lot_id and defect_id
        - CHECK constraint: qty_defects >= 0 (non-negative constraint)
        - UNIQUE constraint on inspection_id
        - Indexes on:
            * inspection_date (for range queries)
            * (defect_id, inspection_date) composite (for AC1-AC4 queries)
    
    Key Business Logic:
        - Records with qty_defects = 0 must NOT be counted as defect occurrences (AC3)
        - is_data_complete flag is used to determine "Insufficient data" status (AC4)
    
    Typical Queries (O(n) with proper indexes):
        - Find all records for a defect: filter by defect_id
        - Find records in a date range: filter by inspection_date
        - Count distinct weeks for a defect: group by DATE_TRUNC('week', inspection_date)
    """
    __tablename__ = "inspection_records"
    
    id = Column(Integer, primary_key=True)
    inspection_id = Column(String(100), nullable=False, unique=True)
    lot_id = Column(Integer, ForeignKey("lots.id", ondelete="CASCADE"), nullable=False)
    defect_id = Column(Integer, ForeignKey("defects.id", ondelete="CASCADE"), nullable=False)
    inspection_date = Column(Date, nullable=False)
    qty_defects = Column(Integer, nullable=False)
    is_data_complete = Column(Boolean, default=True)
    
    # Add CHECK constraint for qty_defects >= 0
    __table_args__ = (
        CheckConstraint("qty_defects >= 0", name="check_qty_defects_non_negative"),
    )
    
    # Relationships
    lot = relationship("LotORM", back_populates="inspection_records")
    defect = relationship("DefectORM", back_populates="inspection_records")
    
    def __repr__(self):
        return (f"<InspectionRecordORM(id={self.id}, inspection_id={self.inspection_id}, "
                f"lot_id={self.lot_id}, defect_id={self.defect_id}, "
                f"inspection_date={self.inspection_date}, qty_defects={self.qty_defects})>")
