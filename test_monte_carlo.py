"""
Test Monte Carlo integration with financial planner
"""

from load_data import load_accounts_from_csv, create_family_from_accounts
from financial_planner import Portfolio, Scenario
from monte_carlo import MonteCarloSimulator

print("="*70)
print("TESTING MONTE CARLO INTEGRATION")
print("="*70)

# Load portfolio
csv_file = "Accounts.csv"
accounts = load_accounts_from_csv(csv_file)
family = create_family_from_accounts(accounts, csv_path=csv_file)
portfolio = Portfolio(accounts, family)

print(f"\nPortfolio loaded: ${portfolio.total_balance():,.0f}")

# Create scenario
scenario = Scenario(
    name="Test Monte Carlo - Retire at 54",
    retirement_age=54,
    annual_spending=200000,
    growth_rate=0.07,
    inflation_rate=0.03,
    contribution_years=12,
    contribution_growth_rate=0.02
)

print(f"\nScenario: {scenario.name}")
print(f"  Retirement age: {scenario.retirement_age}")
print(f"  Annual spending: ${scenario.annual_spending:,.0f}")

# Run deterministic simulation first
print(f"\nRunning deterministic simulation...")
results_df = portfolio.simulate_scenario(
    retirement_age=scenario.retirement_age,
    annual_spending=scenario.annual_spending,
    inflation_rate=scenario.inflation_rate,
    projection_years=50,
    contribution_years=scenario.contribution_years,
    contribution_growth_rate=scenario.contribution_growth_rate
)

# Get deterministic age 70 balance
det_age_70 = results_df[results_df['owner_age'] == 70].iloc[0]['total_balance']
det_final = results_df.iloc[-1]['total_balance']

print(f"Deterministic Results:")
print(f"  Age 70 balance: ${det_age_70:,.0f}")
print(f"  Final balance: ${det_final:,.0f}")

# CRITICAL: Reset portfolio before Monte Carlo
print(f"\nResetting portfolio to initial state...")
portfolio.reset_accounts()
print(f"Portfolio after reset: ${portfolio.total_balance():,.0f}")

# Run Monte Carlo with small number for quick test
print(f"\nRunning Monte Carlo simulation (500 simulations)...")
simulator = MonteCarloSimulator(
    mean_return=0.10,  # 7% real + 3% inflation
    std_dev=0.18
)

mc_results = simulator.run_retirement_simulation(
    portfolio=portfolio,
    scenario=scenario,
    num_simulations=500
)

print(f"\n{'='*70}")
print("MONTE CARLO RESULTS")
print(f"{'='*70}")
print(f"Success Rate: {mc_results['success_rate']*100:.1f}%")
print(f"Successful simulations: {mc_results['success_count']} of {mc_results['total_simulations']}")

print(f"\nAge 70 Balance:")
print(f"  Deterministic: ${det_age_70:,.0f}")
print(f"  MC 10th percentile: ${mc_results['age_70_percentiles']['10th']:,.0f}")
print(f"  MC 50th percentile (median): ${mc_results['age_70_percentiles']['50th']:,.0f}")
print(f"  MC 90th percentile: ${mc_results['age_70_percentiles']['90th']:,.0f}")

print(f"\nFinal Balance:")
print(f"  Deterministic: ${det_final:,.0f}")
print(f"  MC 10th percentile: ${mc_results['final_balance_percentiles']['10th']:,.0f}")
print(f"  MC 50th percentile (median): ${mc_results['final_balance_percentiles']['50th']:,.0f}")
print(f"  MC 90th percentile: ${mc_results['final_balance_percentiles']['90th']:,.0f}")

# Check consistency
age_70_diff_pct = abs(mc_results['age_70_percentiles']['50th'] - det_age_70) / det_age_70 * 100
final_diff_pct = abs(mc_results['final_balance_percentiles']['50th'] - det_final) / det_final * 100

print(f"\nConsistency Check:")
print(f"  Age 70: MC median vs deterministic = {age_70_diff_pct:.1f}% difference")
print(f"  Final: MC median vs deterministic = {final_diff_pct:.1f}% difference")

if age_70_diff_pct < 30 and final_diff_pct < 30:
    print(f"  ✓ Results are reasonably consistent! (Median should be close to deterministic)")
else:
    print(f"  ✗ WARNING: Large difference between median and deterministic!")

if mc_results['failure_years']:
    print(f"\nFailures: {len(mc_results['failure_years'])} simulations failed")
    print(f"Most common failure year: {mc_results['most_common_failure']}")
else:
    print(f"\n✓ No failures in any simulation!")

print(f"\n{'='*70}")
print("TEST COMPLETED SUCCESSFULLY!")
print(f"{'='*70}")
