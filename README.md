# 🏭 SteelWorks - Recurring Defects Analysis Tool

Quality engineering tool for identifying and analyzing defects that appear across multiple manufacturing lots over time.

## Table of Contents

- [Project Description](#project-description)
- [Architecture](#architecture)
- [Tech Stack](#tech-stack)
- [Setup & Installation](#setup--installation)
- [How to Run / Build](#how-to-run--build)
- [Usage Examples](#usage-examples)
- [Running Tests](#running-tests)
- [Configuration](#configuration)
- [Key Design Decisions](#key-design-decisions)
- [What to Change for Production](#what-to-change-for-production)

---

## Project Description

### Problem Statement

As a quality engineer, you need to distinguish between:
- **Recurring Issues**: Defects that appear across multiple lots over time (systemic problems)
- **One-off Incidents**: Defects that happen only once in a specific lot (isolated problems)

This distinction is critical because recurring issues indicate systemic quality problems requiring process improvements, while one-off incidents are typically isolated events.

### Solution Overview

The SteelWorks Recurring Defects Analysis Tool provides:

1. **Smart Classification**: Automatically identifies if a defect type appears across multiple calendar weeks
2. **Visual Dashboard**: Interactive list view showing all defects with key metrics
3. **Drill-Down Analysis**: Detailed breakdown by week showing which lots were affected
4. **Data Quality Indicators**: Flags periods with incomplete data that affect classification reliability

### Key Features

✅ **Classification Logic** (AC1-AC4)
- Multi-week defect detection for recurring classification
- Single-lot defect handling
- Automatic filtering of zero-defect inspection records
- Incomplete data detection and flagging

✅ **List View** (AC5-AC6, AC9)
- Table with all relevant metrics (defect code, status, weeks, lots, dates, quantities)
- Visual highlighting for recurring defects
- Filter by status (Recurring / Not Recurring / Insufficient Data)
- Intelligent default sorting (Recurring first, by weeks desc, by lots desc)

✅ **Drill-Down Analysis** (AC7-AC8)
- Weekly time breakdown showing which lots were affected
- Complete transparency via underlying inspection records
- Clear indication of data gaps that affect classification

---

## Architecture

### Layered Architecture (4-Tier)

```
┌─────────────────────────────────────────────┐
│      UI Layer (Streamlit)                   │
│  - Presentation, user interaction           │
└─────────────────┬───────────────────────────┘
                  │
┌─────────────────▼───────────────────────────┐
│      Service Layer (Business Logic)         │
│  - Classification algorithm (AC1-AC4)       │
│  - Data aggregation and transformation      │
└─────────────────┬───────────────────────────┘
                  │
┌─────────────────▼───────────────────────────┐
│   Repository Layer (Data Access)            │
│  - Query encapsulation and reusability      │
│  - ORM model management                     │
└─────────────────┬───────────────────────────┘
                  │
┌─────────────────▼───────────────────────────┐
│   Database Layer (PostgreSQL)               │
│  - Data persistence                         │
│  - Schema: defects, lots, inspection_records│
└─────────────────────────────────────────────┘
```

### Key Design Patterns

- **Repository Pattern**: Data access abstraction
- **Service Pattern**: Business logic encapsulation  
- **Dependency Injection**: Loose coupling between layers
- **Domain Models**: Clear separation between ORM and domain models

### Directory Structure

```
src/
├── models/           # Domain models + ORM models + DB connection
│   ├── __init__.py   # Domain entities (Defect, Lot, InspectionRecord)
│   ├── orm_models.py # SQLAlchemy ORM models
│   └── db.py         # Database connection & session management
│
├── repositories/     # Data access layer
│   └── __init__.py   # Repository classes (queries)
│
├── services/         # Business logic layer
│   └── __init__.py   # Classification algorithm
│
└── ui/              # Presentation layer
    └── app.py       # Streamlit application

tests/
└── test_recurring_defects.py  # Comprehensive test suite (21 tests)

config/              # Configuration files

db/                  # Database schema and seed data
├── schema.sql
├── seed.sql
└── sample_queries.sql

docs/                # Architecture and design documentation
```

---

## Tech Stack

| Component | Technology | Version |
|-----------|----------|---------|
| Language | Python | 3.9+ |
| Package Manager | Poetry | Latest |
| Web Framework | Streamlit | 1.28+ |
| ORM | SQLAlchemy | 2.0+ |
| Database | PostgreSQL | 12+ |
| Testing | pytest | 7.4+ |
| Database Driver | psycopg2 | 2.9+ |

### Why This Stack?

- **Python**: Excellent AI support, large community, great for data analysis
- **Poetry**: Reproducible dependency management and virtual environments
- **Streamlit**: Fast development of data applications, no frontend coding needed
- **SQLAlchemy**: Type-safe queries, database abstraction, easy testing
- **PostgreSQL**: Reliable, performant, mature, widely used in industry
- **pytest**: Simple yet powerful testing, excellent fixtures support

---

## Setup & Installation

### Prerequisites

- Python 3.9 or higher
- PostgreSQL 12 or higher (running locally or remotely)
- Git (optional, for version control)

### Step 1: Clone/Download the Project

```bash
# If using git:
git clone <repository-url>
cd cs480_steelworks

# Or just download and extract the ZIP file
```

### Step 2: Set Up Python Environment with Poetry

```bash
# Install Poetry (if not already installed)
# See https://python-poetry.org/docs/#installation
curl -sSL https://install.python-poetry.org | python3 -

# Install dependencies
cd cs480_steelworks
poetry install
```

### Step 3: Configure Database Connection

1. **Create PostgreSQL Database**:
```bash
# Create database
psql -U postgres -c "CREATE DATABASE steelworks;"
   ```

```bash
cp .env.example .env

# Then edit .env:
DATABASE_URL=postgresql://your_username:your_password@localhost:5432/steelworks
DB_POOL_SIZE=5
DB_MAX_OVERFLOW=10
```

### Step 4: Initialize Database Schema

```bash
# Create all tables (safe to run multiple times)
poetry run python main.py --init-db
```

Expected output:
```
Initializing database schema...
✓ Database initialized successfully!
✓ All tables created.
```

### Step 5: Load Sample Data (Optional)

```bash
# Run the seed script to populate test data
poetry run python -m data.load_sample_data
```

---

## How to Run / Build

### Running the Application

```bash
# Start the Streamlit app
cd cs480_steelworks
poetry run streamlit run src/ui/app.py

# Or using the main.py entry point:
poetry run python main.py
```

The app will open in your browser at: **http://localhost:8501**

### Building/Packaging

For production deployment:

```bash
# Create a wheel distribution
poetry build

# Or create a standalone package
poetry export -f requirements.txt --output requirements.txt
```

---

## Usage Examples

### Example 1: Analyzing Last 12 Weeks

1. **Open the app** at http://localhost:8501
2. **Set date range**:
   - Start Date: 12 weeks ago
   - End Date: Today
3. **View recurring defects**: Table shows all defects sorted by status
4. **Filter**: Select "Recurring" from the status filter to see only systemic issues

### Example 2: Investigating a Specific Defect

1. **In the main table**, find the defect code you want to analyze (e.g., "CRACK_001")
2. **Click the defect code** in the "Drill-down Analysis" dropdown
3. **Review the detail view**:
   - See which weeks it appeared in
   - See which lots were affected in each week
   - Review the complete inspection records
4. **Check for data gaps**: Look for the "⚠️ Incomplete Data Detected" warning

### Example 3: Comparing Defect Patterns

1. **Use the default sort** to see Recurring defects at the top
2. **Compare "# Weeks" column**: Defects spanning more weeks are more chronic
3. **Compare "# Lots" column**: Defects affecting more lots are more widespread
4. **Drill down on top defects** to understand the pattern

---

## Running Tests

### Run All Tests

```bash
# Run full test suite with coverage
poetry run pytest tests/ -v --cov=src --cov-report=html

# View coverage report
open htmlcov/index.html  # macOS/Linux
start htmlcov\index.html  # Windows
```

### Run Specific Test Suite

```bash
# Run only Acceptance Criteria tests
poetry run pytest tests/test_recurring_defects.py -v

# Run only AC1 tests (Multi-week recurring)
poetry run pytest tests/test_recurring_defects.py::TestAC1_MultiWeekRecurring -v

# Run only AC7 tests (Drill-down detail view)
poetry run pytest tests/test_recurring_defects.py::TestAC7_DrillDownDetailView -v
```

### Test Coverage by Acceptance Criteria

| AC | Test Class | Tests | Coverage |
|-----|-----------|-------|----------|
| AC1 | TestAC1_MultiWeekRecurring | 2 | ✓ |
| AC2 | TestAC2_SingleWeekNotRecurring | 2 | ✓ |
| AC3 | TestAC3_ZeroDefectsExcluded | 2 | ✓ |
| AC4 | TestAC4_InsufficientData | 2 | ✓ |
| AC5 | TestAC5_ListViewFields | 2 | ✓ |
| AC6 | TestAC6_VisualHighlightAndFilter | 1 | ✓ |
| AC7 | TestAC7_DrillDownDetailView | 2 | ✓ |
| AC8 | TestAC8_InsufficientDataMessaging | 2 | ✓ |
| AC9 | TestAC9_DefaultSortingAndPrioritization | 3 | ✓ |
| Edge Cases | TestEdgeCasesAndIntegration | 3 | ✓ |

**Total: 21 test cases covering all 9 Acceptance Criteria**

Each test case includes:
- Clear test name describing the scenario
- Arrange/Act/Assert structure
- Docstring with expected behavior
- Assertions validating AC requirements

### Debugging Tests

```bash
# Run with verbose output and print statements
poetry run pytest tests/test_recurring_defects.py -v -s

# Run a single test with detailed output
poetry run pytest tests/test_recurring_defects.py::TestAC1_MultiWeekRecurring::test_ac1_defect_in_two_weeks_is_recurring -vv

# Run with pytest debugger on failure
poetry run pytest tests/test_recurring_defects.py --pdb
```

---

## Configuration

### Environment Variables

Create a `.env` file in the project root with the following settings:

```env
# Required: Database Connection
DATABASE_URL=postgresql://user:password@host:port/steelworks

# Optional: Connection Pool (defaults shown)
DB_POOL_SIZE=5              # Connections to keep ready
DB_MAX_OVERFLOW=10          # Extra connections for surge
DB_POOL_TIMEOUT=30          # Timeout in seconds

# Optional: Debugging
DB_ECHO_SQL=False           # Set True to log all SQL
APP_DEBUG=True
LOG_LEVEL=INFO
```

### Database Connection Troubleshooting

If you get a connection error:

```
Error: could not connect to server: No such file or directory
```

Check:
1. PostgreSQL is running: `psql -U postgres -c "SELECT 1"`
2. Database exists: `psql -l | grep steelworks`
3. .env file has correct DATABASE_URL
4. Port 5432 is open (default PostgreSQL port)

---

## Key Design Decisions

### 1. Layered Architecture

**Decision**: Use 4-tier layered architecture (UI → Service → Repository → DB)

**Benefits**:
- Clear separation of concerns
- Easy to test each layer independently
- Easy to swap implementations (e.g., PostgreSQL → MySQL)
- Follows industry best practices

### 2. Repository Pattern for Data Access

**Decision**: All database queries go through repository classes

**Benefits**:
- Query logic is centralized and reusable
- Easy to mock for testing
- Database-agnostic business logic
- Easy to add query optimizations

### 3. Service Layer for Business Logic

**Decision**: All classification logic (AC1-AC4) in service layer

**Benefits**:
- Classification algorithm is independent of database or UI
- Can be reused across different interfaces
- Easy to unit test without a database
- Clear business rule documentation

### 4. Separate Domain and ORM Models

**Decision**: `models/__init__.py` has domain models, `models/orm_models.py` has ORM

**Benefits**:
- Domain models reflect business concepts
- ORM models are database-specific
- Easy to migrate database later
- Better encapsulation

### 5. PostgreSQL for Persistence

**Decision**: Use PostgreSQL for reliable, performant data storage

**Benefits**:
- ACID compliance ensures data integrity
- Excellent performance for analytical queries
- Wide industry adoption
- Good support in Python ecosystem

### 6. Streamlit for UI

**Decision**: Use Streamlit for rapid web UI development

**Benefits**:
- Fast prototyping (write Python, get web app)
- No HTML/CSS/JavaScript required
- Built-in components (tables, charts, buttons)
- Automatic caching and state management

---

## What to Change for Production

When deploying to production, update:

### 1. Database Configuration (.env)

```env
# Change from local to production database
DATABASE_URL=postgresql://prod_user:prod_password@db.example.com:5432/steelworks_prod

# Adjust pool settings for production load
DB_POOL_SIZE=20
DB_MAX_OVERFLOW=40
```

### 2. Application Settings

```env
# Set to False for production
APP_DEBUG=False
DB_ECHO_SQL=False
LOG_LEVEL=WARNING
```

### 3. Author/Organization Info (pyproject.toml)

Update authors section:
```toml
authors = ["Your Name <your.email@example.com>"]
```

Also update `src/__init__.py`:
```python
__author__ = "Your Organization Name"
```

### 4. Streamlit Configuration

Create `~/.streamlit/config.toml` or `streamlit/config.toml`:
```toml
[theme]
primaryColor = "#0066cc"
backgroundColor = "#FFFFFF"
secondaryBackgroundColor = "#F0F2F6"

[server]
headless = true
port = 8501
```

---

## Additional Resources

- **SQLAlchemy Docs**: https://docs.sqlalchemy.org/
- **Streamlit Docs**: https://docs.streamlit.io/
- **PostgreSQL Docs**: https://www.postgresql.org/docs/
- **pytest Docs**: https://docs.pytest.org/
- **Poetry Docs**: https://python-poetry.org/docs/

---

## License

[Specify your license here - e.g., MIT, Apache 2.0, etc.]

## Authors

- **Original Developer**: SteelWorks Quality Engineering Team
- **Course**: CS 480 (Software Engineering)
- **Year**: 2026

---

**Last Updated**: February 2026
