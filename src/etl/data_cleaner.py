import pandas as pd
from src.utils.db_utils import get_connection

def clean_data():
    conn = get_connection()

    # Load data from DB
    financials = pd.read_sql("SELECT * FROM financials", conn)
    esg = pd.read_sql("SELECT * FROM esg_scores", conn)
    loans = pd.read_sql("SELECT * FROM loan_portfolio", conn)

    # Simple data cleaning example
    financials.dropna(subset=["revenue", "enterprise_value"], inplace=True)
    esg.fillna({"esg_score": esg["esg_score"].mean()}, inplace=True)

    # Merge datasets
    merged = loans.merge(financials, on="company_id", how="left")
    merged = merged.merge(esg, on="company_id", how="left")

    # Save processed data
    merged.to_sql("cleaned_portfolio", conn, if_exists="replace", index=False)
    conn.close()

    print(f"✅ Cleaned data stored as 'cleaned_portfolio' table ({len(merged)} rows).")

if __name__ == "__main__":
    clean_data()
