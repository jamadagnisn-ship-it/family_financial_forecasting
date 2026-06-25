"""
Projection Engine - Run retirement scenarios and generate projections
"""

import pandas as pd
import matplotlib.pyplot as plt
from load_data import load_accounts_from_csv, create_family_from_accounts, print_portfolio_summary
from financial_planner import Portfolio, Scenario


def run_retirement_scenario(portfolio: Portfolio, 
                            scenario: Scenario,
                            verbose: bool = True) -> pd.DataFrame:
    """Run a complete retirement scenario and return results"""
    
    if verbose:
        print(f"\n{'='*70}")
        print(f"SCENARIO: {scenario.name}")
        print(f"{'='*70}")
        print(f"Retirement Age: {scenario.retirement_age}")
        print(f"Annual Spending (2026 dollars): ${scenario.annual_spending:,.0f}")
        print(f"Growth Rate: {scenario.growth_rate*100:.1f}%")
        print(f"Inflation Rate: {scenario.inflation_rate*100:.1f}%")
        if hasattr(scenario, 'contribution_growth_rate') and scenario.contribution_growth_rate > 0:
            print(f"Contribution Growth Rate: {scenario.contribution_growth_rate*100:.1f}%")
    
    # Run simulation
    results_df = portfolio.simulate_scenario(
        retirement_age=scenario.retirement_age,
        annual_spending=scenario.annual_spending,
        inflation_rate=scenario.inflation_rate,
        projection_years=50,
        contribution_years=scenario.contribution_years,
        contribution_growth_rate=getattr(scenario, 'contribution_growth_rate', 0.0)
    )
    
    # Check success
    success_metrics = portfolio.check_scenario_success(results_df)
    
    if verbose:
        print(f"\nRESULTS:")
        print(f"  Success: {'✓ YES' if success_metrics['success'] else '✗ NO'}")
        print(f"  Final Balance (year 2076): ${success_metrics['final_balance']:,.0f}")
        print(f"  Minimum Balance: ${success_metrics['min_balance']:,.0f}")
        
        if success_metrics['years_until_depletion']:
            print(f"  ⚠ Portfolio depletes in: {success_metrics['years_until_depletion']}")
        
        # Show key milestones
        retirement_year = 2026 + (scenario.retirement_age - 42)
        age_60 = results_df[results_df['owner_age'] == 60].iloc[0] if len(results_df[results_df['owner_age'] == 60]) > 0 else None
        age_70 = results_df[results_df['owner_age'] == 70].iloc[0] if len(results_df[results_df['owner_age'] == 70]) > 0 else None
        age_80 = results_df[results_df['owner_age'] == 80].iloc[0] if len(results_df[results_df['owner_age'] == 80]) > 0 else None
        
        print(f"\nKEY MILESTONES:")
        print(f"  At retirement ({retirement_year}): ${results_df.iloc[scenario.retirement_age - 42]['total_balance']:,.0f}")
        
        if age_60 is not None:
            print(f"  At age 60 ({int(age_60['year'])}): ${age_60['total_balance']:,.0f}")
        if age_70 is not None:
            print(f"  At age 70 ({int(age_70['year'])}): ${age_70['total_balance']:,.0f}")
        if age_80 is not None:
            print(f"  At age 80 ({int(age_80['year'])}): ${age_80['total_balance']:,.0f}")
    
    return results_df, success_metrics


def compare_scenarios(portfolio: Portfolio, scenarios: list) -> pd.DataFrame:
    """Compare multiple retirement scenarios"""
    
    comparison_data = []
    
    for scenario in scenarios:
        # Reset portfolio for each scenario
        portfolio.reset_accounts()
        
        # Run scenario
        results_df, success_metrics = run_retirement_scenario(
            portfolio, scenario, verbose=False
        )
        
        # Extract key metrics
        retirement_year_idx = scenario.retirement_age - 42
        comparison_data.append({
            'Scenario': scenario.name,
            'Retirement Age': scenario.retirement_age,
            'Annual Spending': scenario.annual_spending,
            'Success': '✓' if success_metrics['success'] else '✗',
            'Balance at Retirement': results_df.iloc[retirement_year_idx]['total_balance'],
            'Balance at 70': results_df[results_df['owner_age'] == 70].iloc[0]['total_balance'] if len(results_df[results_df['owner_age'] == 70]) > 0 else 0,
            'Final Balance': success_metrics['final_balance'],
            'Min Balance': success_metrics['min_balance'],
            'Years Until Depletion': success_metrics['years_until_depletion'] if success_metrics['years_until_depletion'] else 'N/A'
        })
    
    comparison_df = pd.DataFrame(comparison_data)
    
    # Print comparison table
    print(f"\n{'='*100}")
    print("SCENARIO COMPARISON")
    print(f"{'='*100}")
    print(comparison_df.to_string(index=False))
    print(f"{'='*100}")
    
    return comparison_df


def plot_scenario(results_df: pd.DataFrame, scenario_name: str, save_path: str = None):
    """Plot account balances over time"""
    
    fig, axes = plt.subplots(2, 1, figsize=(14, 10))
    
    # Plot 1: Total portfolio value
    ax1 = axes[0]
    ax1.plot(results_df['year'], results_df['total_balance'], 
             linewidth=2.5, color='darkblue', label='Total Portfolio')
    ax1.fill_between(results_df['year'], 0, results_df['total_balance'], 
                     alpha=0.3, color='lightblue')
    ax1.set_xlabel('Year', fontsize=12)
    ax1.set_ylabel('Portfolio Value ($)', fontsize=12)
    ax1.set_title(f'{scenario_name} - Total Portfolio Value', fontsize=14, fontweight='bold')
    ax1.grid(True, alpha=0.3)
    ax1.legend()
    
    # Format y-axis as millions
    ax1.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, p: f'${x/1e6:.1f}M'))
    
    # Plot 2: Account type breakdown
    ax2 = axes[1]
    ax2.plot(results_df['year'], results_df['posttax_balance'], 
             label='Post-Tax Accounts', linewidth=2, color='green')
    ax2.plot(results_df['year'], results_df['pretax_balance'], 
             label='Pre-Tax (401k)', linewidth=2, color='orange')
    ax2.plot(results_df['year'], results_df['education_balance'], 
             label='529 Education', linewidth=2, color='purple')
    
    ax2.set_xlabel('Year', fontsize=12)
    ax2.set_ylabel('Account Balance ($)', fontsize=12)
    ax2.set_title('Account Type Breakdown', fontsize=14, fontweight='bold')
    ax2.grid(True, alpha=0.3)
    ax2.legend()
    ax2.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, p: f'${x/1e6:.1f}M'))
    
    plt.tight_layout()
    
    if save_path:
        plt.savefig(save_path, dpi=300, bbox_inches='tight')
        print(f"\nChart saved to: {save_path}")
    else:
        plt.show()
    
    return fig


def export_detailed_projection(results_df: pd.DataFrame, 
                               scenario_name: str, 
                               output_path: str = None):
    """Export detailed year-by-year projection to CSV"""
    
    # Select key columns for export
    export_columns = ['year', 'owner_age', 'total_balance', 
                     'pretax_balance', 'posttax_balance', 'education_balance']
    
    # Add spending columns if they exist
    if 'spending' in results_df.columns:
        export_columns.extend(['spending', 'shortfall'])
    
    export_df = results_df[export_columns].copy()
    
    # Format for readability
    for col in ['total_balance', 'pretax_balance', 'posttax_balance', 'education_balance']:
        if col in export_df.columns:
            export_df[col] = export_df[col].round(0)
    
    if output_path is None:
        output_path = f"projection_{scenario_name.replace(' ', '_')}.csv"
    
    export_df.to_csv(output_path, index=False)
    print(f"Detailed projection exported to: {output_path}")
    
    return export_df


def show_withdrawal_timeline(results_df: pd.DataFrame, start_year: int = None):
    """Show detailed withdrawal timeline during retirement"""
    
    # Filter to retirement years (when withdrawals occur)
    retirement_df = results_df[results_df.get('spending', 0) > 0].copy()
    
    if len(retirement_df) == 0:
        print("No retirement withdrawals in this scenario yet.")
        return
    
    if start_year:
        retirement_df = retirement_df[retirement_df['year'] >= start_year]
    
    print(f"\n{'='*90}")
    print("RETIREMENT WITHDRAWAL TIMELINE")
    print(f"{'='*90}")
    print(f"{'Year':<6} {'Age':<5} {'Spending':<15} {'Post-Tax':<15} {'Pre-Tax':<15} {'Total':<15}")
    print(f"{'-'*90}")
    
    for _, row in retirement_df.head(20).iterrows():  # Show first 20 years
        print(f"{int(row['year']):<6} {int(row['owner_age']):<5} "
              f"${row.get('spending', 0):>12,.0f}  "
              f"${row['posttax_balance']:>12,.0f}  "
              f"${row['pretax_balance']:>12,.0f}  "
              f"${row['total_balance']:>12,.0f}")


if __name__ == "__main__":
    print("="*70)
    print("FINANCIAL PLANNER - PROJECTION ENGINE")
    print("="*70)
    
    # Load portfolio
    csv_file = "Accounts.csv"
    accounts = load_accounts_from_csv(csv_file)
    family = create_family_from_accounts(accounts, csv_path=csv_file)
    portfolio = Portfolio(accounts, family)
    
    print_portfolio_summary(portfolio)
    
    # Define scenarios to test
    scenarios = [
        Scenario(
            name="Retire at 50",
            retirement_age=50,
            annual_spending=200000,
            contribution_years=8
        ),
        Scenario(
            name="Retire at 52",
            retirement_age=52,
            annual_spending=200000,
            contribution_years=10
        ),
        Scenario(
            name="Retire at 54",
            retirement_age=54,
            annual_spending=200000,
            contribution_years=12
        ),
        Scenario(
            name="Retire at 54 (Conservative)",
            retirement_age=54,
            annual_spending=180000,
            contribution_years=12
        ),
    ]
    
    # Run single detailed scenario
    print("\n" + "="*70)
    print("DETAILED SCENARIO ANALYSIS")
    print("="*70)
    
    portfolio.reset_accounts()
    results_df, success = run_retirement_scenario(portfolio, scenarios[2])  # Retire at 54
    show_withdrawal_timeline(results_df, start_year=2038)
    
    # Compare all scenarios
    print("\n")
    comparison_df = compare_scenarios(portfolio, scenarios)
    
    # Export results
    export_detailed_projection(results_df, scenarios[2].name)
    
    print("\n" + "="*70)
    print("Projection engine complete! Ready for visualization.")
    print("="*70)
