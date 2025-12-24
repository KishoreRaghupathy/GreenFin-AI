import pandas as pd
import numpy as np
import scipy.optimize as sco
import matplotlib.pyplot as plt
import os

# Configuration
DATA_PATH = os.path.join(os.path.dirname(__file__), '../data/cleaned/portfolio_clean.csv')
RISK_FREE_RATE = 0.03
TRADING_DAYS = 252

def load_data(filepath):
    """Loads the cleaned portfolio data."""
    if not os.path.exists(filepath):
        # Create dummy data if file doesn't exist for testing
        print(f"File not found at {filepath}. Creating dummy data.")
        data = {
            'Loan_ID': [f'L{i}' for i in range(100)],
            'Borrower_Name': [f'Borrower {i}' for i in range(100)],
            'ESG_Score_0_100': np.random.randint(20, 100, 100),
            'Outstanding_Amount_Mn': np.random.uniform(10, 500, 100),
            'Sector': np.random.choice(['Energy', 'Tech', 'Real Estate', 'Manufacturing'], 100)
        }
        df = pd.DataFrame(data)
        return df
    return pd.read_csv(filepath)

def assign_tier(esg_score):
    """Assigns GFS Tier based on ESG Score."""
    if esg_score >= 80:
        return 'A'
    elif esg_score >= 60:
        return 'B'
    elif esg_score >= 40:
        return 'C'
    else:
        return 'D'

def simulate_historical_returns(df, days=TRADING_DAYS*2):
    """
    Simulates historical returns for the assets.
    Assumption: Higher ESG Score -> Lower Volatility, Slightly lower but more stable returns.
    Lower ESG Score -> Higher Volatility, Higher Risk Premium (but subject to shocks).
    """
    np.random.seed(42)
    n_assets = len(df)
    
    # Base params
    means = np.random.normal(0.08, 0.05, n_assets) / TRADING_DAYS
    # Adjust volatility based on ESG score (Inverse relationship)
    # Score 100 -> low vol, Score 0 -> high vol
    vol_scale = (1 - df['ESG_Score_0_100'] / 150.0) # 0.33 to 1.0 multiplier
    vols = np.random.uniform(0.15, 0.40, n_assets) * vol_scale / np.sqrt(TRADING_DAYS)
    
    returns = np.random.normal(loc=means, scale=vols, size=(days, n_assets))
    return pd.DataFrame(returns, columns=df['Loan_ID'])

def portfolio_performance(weights, mean_returns, cov_matrix):
    """Calculates portfolio return and volatility."""
    returns = np.sum(mean_returns * weights) * TRADING_DAYS
    std = np.sqrt(np.dot(weights.T, np.dot(cov_matrix, weights))) * np.sqrt(TRADING_DAYS)
    return returns, std

def neg_sharpe_ratio(weights, mean_returns, cov_matrix, risk_free_rate):
    """Negative Sharpe Ratio for minimization."""
    p_ret, p_std = portfolio_performance(weights, mean_returns, cov_matrix)
    return -(p_ret - risk_free_rate) / p_std

def get_max_sharpe_ratio_weights(mean_returns, cov_matrix):
    """Optimizes weights to maximize Sharpe Ratio."""
    num_assets = len(mean_returns)
    args = (mean_returns, cov_matrix, RISK_FREE_RATE)
    constraints = ({'type': 'eq', 'fun': lambda x: np.sum(x) - 1})
    bound = (0.0, 1.0)
    bounds = tuple(bound for asset in range(num_assets))
    
    initial_weights = num_assets * [1. / num_assets,]
    
    result = sco.minimize(neg_sharpe_ratio, initial_weights, args=args,
                        method='SLSQP', bounds=bounds, constraints=constraints)
    
    return result

def run_optimization():
    print("--- GreenFin Quantitative Engine ---")
    df = load_data(DATA_PATH)
    
    # 1. Categorization
    df['Tier'] = df['ESG_Score_0_100'].apply(assign_tier)
    print("Portfolio Categorization Summary:")
    print(df['Tier'].value_counts().sort_index())
    
    # 2. Simulate Market Data (since we don't have raw price history)
    print("\nSimulating historical asset returns based on ESG profiles...")
    returns_df = simulate_historical_returns(df)
    mean_returns = returns_df.mean()
    cov_matrix = returns_df.cov()
    
    # 3. Optimization: Scenario A (Legacy Portfolio - All Assets)
    print("\nOptimizing Legacy Portfolio (All Assets)...")
    result_legacy = get_max_sharpe_ratio_weights(mean_returns, cov_matrix)
    weights_legacy = result_legacy.x
    ret_legacy, vol_legacy = portfolio_performance(weights_legacy, mean_returns, cov_matrix)
    sharpe_legacy = (ret_legacy - RISK_FREE_RATE) / vol_legacy
    print(f"Legacy Sharpe Ratio: {sharpe_legacy:.4f}")
    print(f"Legacy Volatility: {vol_legacy:.4f}")
    
    # 4. Optimization: Scenario B (Decoupled Portfolio - Ex-Tier D)
    print("\nOptimizing Decoupled Portfolio (Ex-Tier D)...")
    # Filter out Tier D columns
    non_d_ids = df[df['Tier'] != 'D']['Loan_ID']
    returns_df_decoupled = returns_df[non_d_ids]
    
    mean_returns_dec = returns_df_decoupled.mean()
    cov_matrix_dec = returns_df_decoupled.cov()
    
    result_dec = get_max_sharpe_ratio_weights(mean_returns_dec, cov_matrix_dec)
    weights_dec = result_dec.x
    ret_dec, vol_dec = portfolio_performance(weights_dec, mean_returns_dec, cov_matrix_dec)
    sharpe_dec = (ret_dec - RISK_FREE_RATE) / vol_dec
    print(f"Decoupled Sharpe Ratio: {sharpe_dec:.4f}")
    print(f"Decoupled Volatility: {vol_dec:.4f}")
    
    # 5. Output
    print("\n--- Strategic Conclusion ---")
    if sharpe_dec > sharpe_legacy:
        print("PASS: Decoupling Tier D assets improves risk-adjusted returns.")
        improvement = (sharpe_dec - sharpe_legacy) / sharpe_legacy * 100
        print(f"Sharpe Ratio Improvement: +{improvement:.2f}%")
    else:
        print("FAIL: Decoupling did not optimally improve Sharpe Ratio. Review covariance assumptions.")

if __name__ == "__main__":
    run_optimization()
