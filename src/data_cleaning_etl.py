import pandas as pd
import os


RAW_DATA_PATH = r'D:\DS\DS25\GreenFin\GreenFin-AI\data\raw'
CLEANED_DATA_PATH = r'D:\DS\DS25\GreenFin\GreenFin-AI\data\cleaned'
CLEANED_FILE = os.path.join(CLEANED_DATA_PATH, 'portfolio_clean.csv')

# 1 Ensure the output directory exists
os.makedirs(CLEANED_DATA_PATH, exist_ok=True)
os.makedirs('src', exist_ok=True)

def execute_etl():
    """
    Performs the core ETL (cleaning, merging, imputation) to create the
    portfolio_clean dataset for modeling. This simulates the Redshift/Glue job.
    """
    print("--- Starting GreenFin AI Data Cleaning and ETL (Phase 1.4) ---")
    
    try:
        # 1. Loading Raw Data
        loan_df = pd.read_csv(os.path.join(RAW_DATA_PATH, 'loan_portfolio.csv'))
        financials_df = pd.read_csv(os.path.join(RAW_DATA_PATH, 'company_financials.csv'))
        esg_df = pd.read_csv(os.path.join(RAW_DATA_PATH, 'esg_scores.csv'))
        factors_df = pd.read_csv(os.path.join(RAW_DATA_PATH, 'emission_factors.csv'))
        
        print("1. Raw data loaded successfully.")
        
        # 2. Mergeing the  Data Sources (Simulating complex joins in Redshift)
        
        # Merge 1: Loan Portfolio and Financials (on Borrower Name)
        portfolio_clean = pd.merge(loan_df, financials_df, on='Borrower_Name', how='left')
        
        # Merge 2: Add ESG Scores
        portfolio_clean = pd.merge(portfolio_clean, esg_df, on='Borrower_Name', how='left')

        # Merge 3: Add Sector Emission Factors (Crucial for baseline PCAF calculation)
        portfolio_clean = pd.merge(portfolio_clean, factors_df, on='Sector', how='left')

        print("2. All data sources merged into a single portfolio dataframe.Take a Look at the Data")

        # 3. Data Cleaning and Transformation
        
        # Imputation: Replace missing Reported_GHG_Emissions_tCO2e with a flag value (0)
        # We will use the model to predict these later, but for initial clean, NaN must be handled.
        # Create a flag before imputation
        portfolio_clean['Reported_Missing_Flag'] = portfolio_clean['Reported_GHG_Emissions_tCO2e'].isnull().astype(int)
        
        # Impute NaNs in the emissions column with 0 for now (to avoid breaking models)
        portfolio_clean['Reported_GHG_Emissions_tCO2e'] = portfolio_clean['Reported_GHG_Emissions_tCO2e'].fillna(0)
        
        # Handle potential NaNs from missing ESG/Financials (shouldn't happen with synthetic data, but good practice)
        for col in ['Outstanding_Amount_Mn', 'Revenue_Mn', 'Enterprise_Value_Mn', 'ESG_Score_0_100']:
             # Use median imputation for continuous variables
            portfolio_clean[col] = portfolio_clean[col].fillna(portfolio_clean[col].median())
        
        # Feature Engineering (Basic Ratios - useful for credit risk and emissions proxies)
        portfolio_clean['Debt_to_EV_Ratio'] = portfolio_clean['Outstanding_Amount_Mn'] / portfolio_clean['Enterprise_Value_Mn']
        portfolio_clean['Emissions_per_Revenue'] = portfolio_clean['Reported_GHG_Emissions_tCO2e'] / portfolio_clean['Revenue_Mn']
        
        print("3. Data cleaning, imputation, and initial feature engineering completed.")

        # 4. Final Output (Simulating writing to the Redshift Cleaned DW)
        portfolio_clean = portfolio_clean.sort_values(by='Borrower_Name').reset_index(drop=True)
        
        # Select final columns to match the planned Redshift schema structure
        final_columns = [
            'Loan_ID', 'Borrower_Name', 'Sector', 'Outstanding_Amount_Mn', 
            'Revenue_Mn', 'Enterprise_Value_Mn', 'Reported_GHG_Emissions_tCO2e',
            'Reported_Missing_Flag', 'ESG_Score_0_100', 'Governance_Risk_1_5',
            'Emissions_Intensity_tCO2e_per_M_Rev', 'Debt_to_EV_Ratio'
        ]
        
        # Save the cleaned portfolio to a new CSV file
        portfolio_clean[final_columns].to_csv(CLEANED_FILE, index=False)
        
        print(f"4. Cleaned portfolio saved to: {CLEANED_FILE}")
        print(f"Final Cleaned Records: {len(portfolio_clean)}.")

    except FileNotFoundError:
        print(f"ERROR: Raw data files not found in {RAW_DATA_PATH}. Please run 'data_generation.py' first.")
        return
    except Exception as e:
        print(f"An unexpected error occurred during ETL: {e}")
        return

if __name__ == '__main__':
    execute_etl()
    print("\n--- Stage 1 (Data Engineering) ETL Complete. ---")
    print("The 'portfolio_clean.csv' is now ready for Stage 2: Modeling and Analytics.")