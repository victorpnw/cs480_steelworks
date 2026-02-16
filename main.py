"""
Main Entry Point - Run SteelWorks Recurring Defects App

This script initializes the database and starts the Streamlit application.

Usage:
    # First time setup (creates database and tables):
    python main.py --init-db
    
    # Run the app normally:
    streamlit run main.py
    
    # Or:
    python main.py

Environment Setup:
    1. Create .env file with DATABASE_URL and other settings
    2. Create PostgreSQL database matching DATABASE_URL
    3. Run with --init-db flag to create schema

Time Complexity: O(n) where n is number of tables (typically < 10)
Space Complexity: O(1) - schema creation is metadata operation
"""

import sys
import argparse
from src.models.db import init_db, close_all_sessions


def init_database():
    """
    Initialize the database schema.
    
    Creates all tables defined in ORM models. Safe to run multiple times
    (CREATE TABLE IF NOT EXISTS is used).
    
    Time Complexity: O(t) where t is number of tables
    Space Complexity: O(1)
    """
    try:
        print("Initializing database schema...")
        init_db()
        print("✓ Database initialized successfully!")
        print("✓ All tables created.")
    except Exception as e:
        print(f"✗ Database initialization failed: {e}")
        raise


def run_app():
    """
    Run the Streamlit application.
    
    This function would normally be called by Streamlit's command runner.
    For compatibility, we also support running it directly with Python.
    """
    try:
        # Import and run the app
        from src.ui.app import main
        main()
    except Exception as e:
        print(f"Error running application: {e}")
        raise
    finally:
        close_all_sessions()


def main():
    """Main entry point with argument parsing"""
    parser = argparse.ArgumentParser(
        description="SteelWorks Recurring Defects Analysis Tool"
    )
    parser.add_argument(
        "--init-db",
        action="store_true",
        help="Initialize the database schema (create tables)"
    )
    
    args = parser.parse_args()
    
    if args.init_db:
        init_database()
        print("\nNext steps:")
        print("1. Load CSV data into the database")
        print("2. Run: streamlit run main.py")
    else:
        # Run the Streamlit app
        run_app()


if __name__ == "__main__":
    main()
