import pandas as pd
from pathlib import Path
from src.utils.db_utils import get_connection

RAW_PATH = Path(__file__).resolve().parents[2] / "data" / "raw"

def load_csv(filename):
    """Load CSV file into pandas DataFrame."""
    path = RAW_PATH / filename
    df = pd.read_csv(path)
    print(f"📥 Loaded {filename} with {len(df)} rows")
    return df

def ingest_to_db():
    conn = get_connection()

    files = {
        "financials": "company_financials.csv",
        "esg_scores": "esg_scores.csv",
        "loan_portfolio": "loan_portfolio.csv",
        "emission_factors": "emission_factors.csv",
    }

    for table, filename in files.items():
        df = load_csv(filename)
        df.to_sql(table, conn, if_exists="replace", index=False)
        print(f"✅ {table} data inserted into database.")

    conn.close()
    print("🎯 All raw data ingested successfully.")

if __name__ == "__main__":
    ingest_to_db()
