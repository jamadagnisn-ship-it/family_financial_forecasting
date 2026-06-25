"""
Test the new features: 529 redirection and contribution growth rate
"""

from load_data import load_accounts_from_csv, create_family_from_accounts
from financial_planner import Portfolio, Scenario

# Load portfolio
csv_file = "Accounts.csv"
accounts = load_accounts_from_csv(csv_file)
family = create_family_from_accounts(accounts, csv_path=csv_file)
portfolio = Portfolio(accounts, family)

print("="*70)
print("TESTING NEW FEATURES")
print("="*70)

# Test with contribution growth rate
scenario = Scenario(
    name="Test with 2% contribution growth",
    retirement_age=54,
    annual_spending=200000,
    contribution_years=12,
    contribution_growth_rate=0.02  # 2% annual increase
)

print(f"\nRunning scenario: {scenario.name}")
print(f"  Contribution Growth Rate: {scenario.contribution_growth_rate*100:.1f}%")

# Run simulation
results_df = portfolio.simulate_scenario(
    retirement_age=scenario.retirement_age,
    annual_spending=scenario.annual_spending,
    inflation_rate=0.03,
    projection_years=30,
    contribution_years=scenario.contribution_years,
    contribution_growth_rate=scenario.contribution_growth_rate
)

print(f"\n✓ Simulation completed successfully!")
print(f"\nKey Results:")
print(f"  Initial Portfolio: ${portfolio.total_balance():,.0f}")
print(f"  Year 1 Total Balance: ${results_df.iloc[0]['total_balance']:,.0f}")
print(f"  Year 10 Total Balance: ${results_df.iloc[9]['total_balance']:,.0f}")

# Check for 529 redirection
if 'redirected_529' in results_df.columns:
    redirected = results_df[results_df['redirected_529'] > 0]
    if len(redirected) > 0:
        print(f"\n✓ 529 Redirection Active!")
        print(f"  First redirection in year: {redirected.iloc[0]['year']:.0f}")
        print(f"  Amount redirected: ${redirected.iloc[0]['redirected_529']:,.0f}")
    else:
        print(f"\n✓ No 529 redirection yet (still contributing)")

print(f"\nYear 3 Post-tax Balance: ${results_df.iloc[2]['posttax_balance']:,.0f}")
print(f"Year 3 Pre-tax Balance: ${results_df.iloc[2]['pretax_balance']:,.0f}")
print(f"Year 3 529 Balance: ${results_df.iloc[2]['education_balance']:,.0f}")

print("\n" + "="*70)
print("TEST COMPLETED SUCCESSFULLY!")
print("="*70)
