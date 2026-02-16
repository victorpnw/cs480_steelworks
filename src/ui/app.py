"""
Streamlit UI Layer - Presentation

This module implements the user interface using Streamlit, a Python web app framework.
It handles all presentation logic for displaying recurring defects analysis.

Architecture:
  - Streamlit pages handle rendering and user interactions
  - Services provide business logic via dependency injection
  - Repositories provide data access via services
  - UI is stateless (all state comes from user input and database)

Streamlit Features Used:
  - st.write(), st.dataframe(): Display data
  - st.selectbox(), st.date_input(): User input
  - st.filter(): Client-side filtering
  - st.markdown(): Formatted text
  - st.columns(), st.expander(): Layout components
  - st.session_state: UI state management

Time Complexity of UI operations:
  - Rendering: O(k) where k is number of rows/elements
  - Filtering: O(k) client-side
  - Sorting: O(k log k)
  
Space Complexity: O(k) for storing data in memory for display

Acceptance Criteria Implementation:
  AC5: Table with all required fields
  AC6: Visual highlights and filter for Recurring status
  AC7: Drill-down detail view with weekly breakdown
  AC8: Incomplete data messaging
  AC9: Default sorting (Recurring first, by weeks desc, by lots desc)
"""

import streamlit as st
from datetime import date, timedelta
from typing import List, Optional
import pandas as pd

from src.models import RecurringDefectResult, DefectDetailResult
from src.services import RecurringDefectClassificationService
from src.repositories import InspectionRecordRepository, DefectRepository
from src.models.db import get_session


def init_session_state():
    """
    Initialize Streamlit session state with default values.
    
    Session state persists across page reruns, allowing us to maintain UI state
    across user interactions.
    
    Time Complexity: O(1)
    Space Complexity: O(1)
    """
    if "start_date" not in st.session_state:
        # Default: last 12 weeks
        st.session_state.start_date = date.today() - timedelta(weeks=12)
    
    if "end_date" not in st.session_state:
        st.session_state.end_date = date.today()
    
    if "selected_status_filter" not in st.session_state:
        st.session_state.selected_status_filter = "All"
    
    if "selected_defect" not in st.session_state:
        st.session_state.selected_defect = None


def render_header():
    """
    Render the application header and title.
    
    Time Complexity: O(1)
    Space Complexity: O(1)
    """
    st.set_page_config(
        page_title="SteelWorks - Recurring Defects",
        page_icon="🏭",
        layout="wide",
    )
    st.title("🏭 SteelWorks - Recurring Defects Analysis")
    st.markdown(
        """
        **Quality Engineering Tool**
        
        Identify and analyze defects that appear across multiple lots over time.
        """
    )


def render_filters() -> tuple[date, date, str]:
    """
    Render the date range and status filter controls.
    
    Returns the user's selected date range and status filter.
    
    Returns:
        Tuple of (start_date, end_date, status_filter_selection)
    
    Time Complexity: O(1)
    Space Complexity: O(1)
    
    Acceptance Criteria Implementation:
        AC6: Status filter enables viewing only Recurring defects
    """
    col1, col2, col3 = st.columns(3)
    
    with col1:
        start = st.date_input(
            "Start Date",
            value=st.session_state.start_date,
            key="start_date_input",
        )
    
    with col2:
        end = st.date_input(
            "End Date",
            value=st.session_state.end_date,
            key="end_date_input",
        )
    
    with col3:
        status_filter = st.selectbox(
            "Filter by Status",
            ["All", "Recurring", "Not recurring", "Insufficient data"],
            index=0,
            key="status_filter_select",
        )
    
    return start, end, status_filter


def render_list_view(results: List[RecurringDefectResult], status_filter: str):
    """
    Render the main list/table view of recurring defects.
    
    This implements AC5, AC6, and AC9.
    
    Time Complexity:
        O(k) where k is number of results
        - Filtering: O(k)
        - Rendering: O(k)
    Space Complexity: O(k) for dataframe
    
    Args:
        results: Classification results from the service
        status_filter: User's selected status filter
    
    Acceptance Criteria:
        AC5: Display all required fields (defect_code, status, weeks, lots, dates, qty)
        AC6: Visual highlight for "Recurring" status + filtering capability
        AC9: Default sorting by status (Recurring first), weeks desc, lots desc
    """
    st.subheader("📊 Recurring Defects List")
    st.markdown("---")
    
    # Filter results by status (AC6)
    filtered_results = results
    if status_filter != "All":
        filtered_results = [r for r in results if r.status == status_filter]
    
    if not filtered_results:
        st.info(f"No defects found with status: {status_filter}")
        return
    
    # Prepare data for table (AC5: all required fields)
    table_data = []
    for result in filtered_results:
        table_data.append({
            "Defect Code": result.defect_code,
            "Status": result.status,
            "# Weeks": result.weeks_with_occurrences,
            "# Lots": result.lots_affected,
            "First Seen": result.first_seen_date,
            "Last Seen": result.last_seen_date,
            "Total Qty Defects": result.total_qty_defects,
        })
    
    df = pd.DataFrame(table_data)
    
    # AC6: Visual styling - highlight Recurring defects
    def highlight_row(row):
        """Apply styling to rows based on status"""
        if row["Status"] == "Recurring":
            return ["background-color: #ffffcc"] * len(row)  # Light yellow
        elif row["Status"] == "Insufficient data":
            return ["background-color: #ffe6e6"] * len(row)  # Light red
        return [""] * len(row)
    
    styled_df = df.style.apply(highlight_row, axis=1)
    
    st.dataframe(styled_df, use_container_width=True)
    
    # Show summary stats
    col1, col2, col3 = st.columns(3)
    with col1:
        recurring_count = len([r for r in filtered_results if r.status == "Recurring"])
        st.metric("Recurring Defects", recurring_count)
    
    with col2:
        not_recurring_count = len([r for r in filtered_results if r.status == "Not recurring"])
        st.metric("Not Recurring", not_recurring_count)
    
    with col3:
        insufficient_count = len([r for r in filtered_results if r.status == "Insufficient data"])
        st.metric("Insufficient Data", insufficient_count)
    
    # Allow drill-down selection (AC7)
    st.subheader("📋 Drill-down Analysis")
    selected_code = st.selectbox(
        "Select a defect to view details:",
        [r.defect_code for r in filtered_results],
        index=None,
        placeholder="Choose a defect...",
    )
    
    if selected_code:
        st.session_state.selected_defect = selected_code
        render_detail_view(selected_code)


def render_detail_view(
    defect_code: str,
    start_date: date = None,
    end_date: date = None,
):
    """
    Render the drill-down detail view for a specific defect.
    
    Implements AC7 (weekly breakdown and underlying records) and
    AC8 (incomplete data messaging).
    
    Time Complexity:
        O(k log k) where k = records for the defect
        - Fetching and grouping: O(k log k)
        - Rendering: O(k)
    Space Complexity: O(k)
    
    Args:
        defect_code: The defect to analyze
        start_date: Date range start (uses session state if None)
        end_date: Date range end (uses session state if None)
    
    Acceptance Criteria:
        AC7: Time breakdown by week, lots per week, underlying records
        AC8: Incomplete period messaging with date ranges
    """
    if start_date is None:
        start_date = st.session_state.start_date
    if end_date is None:
        end_date = st.session_state.end_date
    
    # Get detail data
    session = get_session()
    try:
        inspection_repo = InspectionRecordRepository(session)
        defect_repo = DefectRepository(session)
        service = RecurringDefectClassificationService(inspection_repo, defect_repo)
        
        detail = service.get_defect_detail(defect_code, start_date, end_date)
    finally:
        session.close()
    
    if detail is None:
        st.warning(f"No data found for defect: {defect_code}")
        return
    
    # Show defect header
    st.markdown(f"### 🔍 {defect_code}")
    st.markdown(f"**Status:** {detail.status}")
    
    # AC8: Show incomplete periods if any
    if detail.incomplete_periods:
        st.warning(
            "⚠️ **Incomplete Data Detected**\n\n"
            "The following periods have incomplete inspection data, which may affect "
            "classification accuracy:"
        )
        for period_start, period_end in detail.incomplete_periods:
            st.write(f"  • {period_start} to {period_end}")
    
    # AC7: Weekly breakdown
    st.markdown("#### Weekly Breakdown")
    
    # Sort weeks by week number
    sorted_weeks = sorted(
        detail.weekly_breakdown.items(),
        key=lambda x: x[1]["week_number"],
    )
    
    for week_key, week_data in sorted_weeks:
        with st.expander(
            f"Week {week_data['week_number']:2d} "
            f"({week_data['week_start']} to {week_data['week_end']})",
            expanded=False,
        ):
            col1, col2 = st.columns(2)
            with col1:
                st.metric(
                    "Total Qty Defects",
                    week_data["total_qty_defects"],
                )
            with col2:
                st.metric(
                    "Lots Affected",
                    len(week_data["lots"]),
                )
            
            st.write("**Lots:** " + ", ".join(str(l) for l in week_data["lots"]))
            
            # Show records for this week
            st.write("**Inspection Records:**")
            record_data = []
            for record in week_data["records"]:
                record_data.append({
                    "Inspection ID": record.inspection_id,
                    "Lot ID": record.lot_id,
                    "Date": record.inspection_date,
                    "Qty Defects": record.qty_defects,
                    "Data Complete": "✓" if record.is_data_complete else "✗",
                })
            
            if record_data:
                st.dataframe(
                    pd.DataFrame(record_data),
                    use_container_width=True,
                    hide_index=True,
                )
    
    # AC7: Show all underlying records
    st.markdown("#### All Underlying Records")
    all_records = []
    for record in detail.underlying_records:
        all_records.append({
            "Inspection ID": record.inspection_id,
            "Lot ID": record.lot_id,
            "Inspection Date": record.inspection_date,
            "Qty Defects": record.qty_defects,
            "Data Complete": "✓" if record.is_data_complete else "✗",
        })
    
    if all_records:
        st.dataframe(
            pd.DataFrame(all_records),
            use_container_width=True,
            hide_index=True,
        )


def main():
    """
    Main application entry point.
    
    Orchestrates the UI layout and ties together all components.
    
    Time Complexity: O(n log n) where n = total records in date range
        - Initialization: O(1)
        - Data fetching: O(n log n)
        - Rendering: O(n)
    Space Complexity: O(n)
    """
    # Initialize and render
    init_session_state()
    render_header()
    
    # Get user inputs
    col1, col2, col3 = st.columns(3)
    with col1:
        start_date = st.date_input(
            "Start Date",
            value=st.session_state.start_date,
            key="start_date_picker",
        )
    with col2:
        end_date = st.date_input(
            "End Date",
            value=st.session_state.end_date,
            key="end_date_picker",
        )
    with col3:
        status_filter = st.selectbox(
            "Filter by Status",
            ["All", "Recurring", "Not recurring", "Insufficient data"],
            key="status_filter_select_main",
        )
    
    # Validate dates
    if start_date > end_date:
        st.error("Start Date must be before End Date")
        return
    
    # Fetch and classify defects
    session = get_session()
    try:
        inspection_repo = InspectionRecordRepository(session)
        defect_repo = DefectRepository(session)
        service = RecurringDefectClassificationService(inspection_repo, defect_repo)
        
        # Load and classify
        with st.spinner("Analyzing defects..."):
            results = service.classify_defects(start_date, end_date)
        
        if not results:
            st.info("No defects found in the selected date range.")
            return
        
        # Display results
        render_list_view(results, status_filter)
        
    finally:
        session.close()


if __name__ == "__main__":
    main()
