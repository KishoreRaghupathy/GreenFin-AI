import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import sys
import os # Import the os module for file operations

# --- Configuration for ESG Scoring and Reporting ---
# Define the weight and direction (positive/negative impact) for each factor.
ESG_SCORING_WEIGHTS = {
    'ESG_Score_0_100': 0.50, # Strong emphasis on overall ESG performance
    'Emissions_Intensity_tCO2e_per_M_Rev': 0.30, # Strong emphasis on environmental impact
    'Governance_Risk_1_5': 0.20, # Emphasis on governance structure
}

# Define the directory where reports will be saved
REPORT_DIR = r'D:\DS\DS25\GreenFin\GreenFin-AI\reports'

# --- Utility Functions ---

def ensure_report_dir():
    """Ensures the report directory exists."""
    if not os.path.exists(REPORT_DIR):
        os.makedirs(REPORT_DIR)
        print(f"Created report directory: {REPORT_DIR}")

def save_report_content(filename, content):
    """Saves text content to a file in the report directory."""
    try:
        filepath = os.path.join(REPORT_DIR, filename)
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)
        print(f"Text report saved to: {filepath}")
    except Exception as e:
        print(f"Error saving report file {filename}: {e}")


# --- Data Preparation and Scoring ---

def load_data(filepath):
    """Loads the ESG loan data."""
    try:
        # Load the data
        df = pd.read_csv(filepath)
        
        # Ensure all required columns for analysis are present
        required_cols = list(ESG_SCORING_WEIGHTS.keys()) + ['Outstanding_Amount_Mn', 'Sector', 'Borrower_Name', 'Loan_ID']
        if not all(col in df.columns for col in required_cols):
            missing = [col for col in required_cols if col not in df.columns]
            print(f"Error: Missing required columns for analysis: {missing}. Found columns: {df.columns.tolist()}")
            sys.exit(1)

        # Handle missing ESG/Emissions data by filling with a median or neutral value
        for col in ESG_SCORING_WEIGHTS.keys():
            df[col].fillna(df[col].median(), inplace=True)
            
        # Drop rows where critical financial data is missing
        df.dropna(subset=['Outstanding_Amount_Mn', 'Sector'], inplace=True)
        
        print(f"Data loaded successfully from {filepath}. Total records analyzed: {len(df)}")
        return df
    
    except FileNotFoundError:
        print(f"Error: The file '{filepath}' was not found.")
        sys.exit(1)
    except Exception as e:
        print(f"An unexpected error occurred during data loading: {e}")
        sys.exit(1)

def calculate_green_finance_score(df):
    """
    Calculates a single Green Finance Score (0-100) for each loan by normalizing and weighting ESG metrics.
    A higher score indicates better green alignment/lower risk.
    """
    df_scores = df.copy()

    # 1. Normalize ESG_Score (Higher is better, score 0-100)
    df_scores['Normalized_ESG'] = df_scores['ESG_Score_0_100'] / 100.0

    # 2. Normalize Governance Risk (Lower is better, score 1-5)
    # Inverse scaling: A score of 1 (Min Risk) -> 1.0 (Good). A score of 5 (Max Risk) -> 0.0 (Bad).
    df_scores['Normalized_Gov'] = (5 - df_scores['Governance_Risk_1_5']) / 4.0

    # 3. Normalize Emissions Intensity (Lower is better) - Rank-based approach
    
    # Clip extreme outliers to prevent distortion during ranking
    emission_limit = df_scores['Emissions_Intensity_tCO2e_per_M_Rev'].quantile(0.95)
    df_scores['Emissions_Capped'] = df_scores['Emissions_Intensity_tCO2e_per_M_Rev'].clip(upper=emission_limit)

    # Rank the capped emissions, then normalize to 0-1 and invert (1 - score)
    df_scores['Normalized_Emission'] = 1 - df_scores['Emissions_Capped'].rank(pct=True)

    # 4. Apply Weights to calculate the Final Score (0 to 1)
    df_scores['Green_Finance_Score'] = (
        df_scores['Normalized_ESG'] * ESG_SCORING_WEIGHTS['ESG_Score_0_100'] +
        df_scores['Normalized_Gov'] * ESG_SCORING_WEIGHTS['Governance_Risk_1_5'] +
        df_scores['Normalized_Emission'] * ESG_SCORING_WEIGHTS['Emissions_Intensity_tCO2e_per_M_Rev']
    )
    
    # Scale to 0-100 for readability
    df_scores['Green_Finance_Score'] *= 100
    
    # Sort by the final score (highest score = best alignment)
    df_scores.sort_values(by='Green_Finance_Score', ascending=False, inplace=True)

    return df_scores

def summarize_portfolio(df_scored):
    """Analyzes and summarizes the portfolio's exposure across different risk tiers,
    returning both the DataFrame summary and the Markdown formatted text."""
    
    # Define Risk Tiers based on the Green Finance Score (0-100)
    def assign_tier(score):
        if score >= 80:
            return 'A: Leader (Low Risk)'
        elif score >= 60:
            return 'B: Aligned (Moderate Risk)'
        elif score >= 40:
            return 'C: Watchlist (High Risk)'
        else:
            return 'D: Divestment (Very High Risk)'
            
    df_scored['Risk_Tier'] = df_scored['Green_Finance_Score'].apply(assign_tier)
    
    # Calculate key summary metrics
    total_exposure = df_scored['Outstanding_Amount_Mn'].sum()
    
    # Group and aggregate data
    summary = df_scored.groupby('Risk_Tier').agg(
        Total_Exposure=('Outstanding_Amount_Mn', 'sum'),
        Count=('Loan_ID', 'count'),
        Avg_Score=('Green_Finance_Score', 'mean')
    ).reset_index()

    summary['Exposure_Percentage'] = (summary['Total_Exposure'] / total_exposure) * 100
    
    # Define fixed order for tiers in the output table
    tier_order = ['A: Leader (Low Risk)', 'B: Aligned (Moderate Risk)', 'C: Watchlist (High Risk)', 'D: Divestment (Very High Risk)']
    summary['Risk_Tier'] = pd.Categorical(summary['Risk_Tier'], categories=tier_order, ordered=True)
    summary.sort_values('Risk_Tier', inplace=True)
    
    # Generate the Markdown output for printing and saving
    markdown_output = "\n" + "="*80 + "\n"
    markdown_output += "           *** GREEN FINANCE PORTFOLIO RISK SUMMARY ***\n"
    markdown_output += f"Total Portfolio Exposure: {total_exposure:,.2f} Million\n"
    markdown_output += "="*80 + "\n"
    markdown_output += summary.to_markdown(index=False, floatfmt=".2f")
    markdown_output += "\n" + "="*80 + "\n"
    
    print(markdown_output) # Keep printing to console
    
    return summary, markdown_output

def plot_exposure_by_risk_tier(summary_df, save_filepath):
    """Creates a visualization of the total loan exposure across the defined risk tiers and saves it."""
    
    # Ensure tiers are plotted in the correct (score-based) order
    summary_df = summary_df.sort_values(by='Avg_Score', ascending=True) 

    plt.figure(figsize=(10, 7))
    # Define colors from Red (Worst/D) to Green (Best/A)
    tier_colors = {
        'D: Divestment (Very High Risk)': '#d9534f',
        'C: Watchlist (High Risk)': '#f0ad4e',
        'B: Aligned (Moderate Risk)': '#5bc0de',
        'A: Leader (Low Risk)': '#5cb85c'
    }
    
    # Sort the tiers for plotting to ensure consistent color mapping
    plot_tiers = summary_df['Risk_Tier'].tolist()
    plot_colors = [tier_colors.get(tier, '#cccccc') for tier in plot_tiers]

    bars = plt.bar(
        plot_tiers, 
        summary_df['Total_Exposure'], 
        color=plot_colors 
    )
    
    plt.title('Portfolio Exposure (Outstanding Amount) by ESG Risk Tier', fontsize=16, pad=20)
    plt.ylabel('Outstanding Amount (Mn $)', fontsize=12)
    plt.xlabel('ESG Risk Tier', fontsize=12)
    
    # Ensure labels are readable
    plt.xticks(rotation=45, ha='right')
    plt.grid(axis='y', linestyle='--', alpha=0.7)
    
    # Add labels for exposure percentage
    for bar in bars:
        height = bar.get_height()
        # Find the corresponding percentage using the height (exposure amount)
        percentage = summary_df[summary_df['Total_Exposure'] == height]['Exposure_Percentage'].iloc[0]
        
        plt.text(
            bar.get_x() + bar.get_width() / 2., 
            height + (height * 0.01), # Position slightly above the bar
            f'{percentage:.1f}%',
            ha='center', va='bottom', fontsize=10
        )
        
    plt.tight_layout()
    plt.savefig(save_filepath) # Save the figure to the specified path
    plt.close() # Close the plot to free memory
    print(f"Plot saved successfully to: {save_filepath}")


# --- Main Execution Block ---

if __name__ == "__main__":
    # Define the input file path
    FILEPATH = r'D:\DS\DS25\GreenFin\GreenFin-AI\data\cleaned\portfolio_clean.csv'
    
    print("--- Stage 2: ESG Loan Risk and Allocation Analysis ---")
    
    # Ensure the report directory exists
    ensure_report_dir()
    
    # 1. Load Data
    loan_df = load_data(FILEPATH)
    
    # 2. Calculate Green Finance Score
    loan_df_scored = calculate_green_finance_score(loan_df)
    
    # 3. Summarize Portfolio Exposure
    summary_results, summary_markdown = summarize_portfolio(loan_df_scored)
    
    # 4. Plot Exposure and Save
    plot_exposure_by_risk_tier(
        summary_results, 
        os.path.join(REPORT_DIR, 'exposure_by_risk_tier.png')
    )
    
    # 5. Prepare and Output Top/Worst Performing Loans
    
    report_content = summary_markdown
    
    # TOP 5 LOANS
    top_loans = loan_df_scored[loan_df_scored['Risk_Tier'].str.startswith('A')].head(5)
    
    report_content += "\n" + "="*80 + "\n"
    report_content += "TOP 5 LOANS - BEST GREEN FINANCE ALIGNMENT (Score >= 80)\n"
    
    if top_loans.empty:
        top_loans = loan_df_scored.head(5)
        report_content += "(No A-rated loans found, showing top 5 overall):\n"
    
    top_loans_markdown = top_loans[['Borrower_Name', 'Sector', 'Outstanding_Amount_Mn', 'Green_Finance_Score', 'Risk_Tier']].to_markdown(index=False, floatfmt=".2f")
    report_content += top_loans_markdown
    print(report_content.splitlines()[-len(top_loans_markdown.splitlines()):-1][0]) # Print header for top loans
    print(top_loans_markdown) # Print table for top loans


    # BOTTOM 5 LOANS
    bottom_loans = loan_df_scored[loan_df_scored['Risk_Tier'].str.startswith('D')].tail(5) 
    
    report_content += "\n" + "-"*80 + "\n"
    report_content += "BOTTOM 5 LOANS - WORST GREEN FINANCE ALIGNMENT (Candidates for Divestment)\n"

    if bottom_loans.empty:
        bottom_loans = loan_df_scored.tail(5)
        report_content += "(No D-rated loans found, showing bottom 5 overall):\n"
        
    bottom_loans_markdown = bottom_loans[['Borrower_Name', 'Sector', 'Outstanding_Amount_Mn', 'Green_Finance_Score', 'Risk_Tier']].to_markdown(index=False, floatfmt=".2f")
    report_content += bottom_loans_markdown
    print(report_content.splitlines()[-len(bottom_loans_markdown.splitlines()):-1][0]) # Print header for bottom loans
    print(bottom_loans_markdown) # Print table for bottom loans
    
    report_content += "\n" + "="*80 + "\n"

    # 6. Save the final text report
    save_report_content('esg_analysis_report.md', report_content)
    
    print("\n*** ESG Analysis Complete. All results and the visualization are saved in the 'report' directory. ***")