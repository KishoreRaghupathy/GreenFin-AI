import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).resolve().parents[2] / "db" / "greenfin.db"

def get_connection():
    """Create or connect to SQLite database."""
    conn = sqlite3.connect(DB_PATH)
    return conn

def create_tables():
    conn = get_connection()
    cursor = conn.cursor()

    cursor.executescript("""
    CREATE TABLE IF NOT EXISTS financials (
        company_id TEXT PRIMARY KEY,
        company_name TEXT,
        sector TEXT,
        revenue REAL,
        enterprise_value REAL
    );

    CREATE TABLE IF NOT EXISTS esg_scores (
        company_id TEXT PRIMARY KEY,
        esg_score REAL,
        sector TEXT
    );

    CREATE TABLE IF NOT EXISTS loan_portfolio (
        loan_id TEXT PRIMARY KEY,
        company_id TEXT,
        asset_class TEXT,
        exposure REAL
    );

    CREATE TABLE IF NOT EXISTS emission_factors (
        sector TEXT PRIMARY KEY,
        emission_intensity REAL
    );

    CREATE TABLE IF NOT EXISTS portfolio_emissions (
        loan_id TEXT PRIMARY KEY,
        company_id TEXT,
        financed_emission REAL,
        stress_scenario REAL
    );
    """)

    conn.commit()
    conn.close()
    print("✅ Tables created successfully.")

if __name__ == "__main__":
    create_tables()
"""Database utility functions for GreenFin application."""