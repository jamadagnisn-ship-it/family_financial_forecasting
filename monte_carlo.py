"""
Monte Carlo Simulator - Parametric approach for retirement and education planning
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Tuple
from copy import deepcopy
from datetime import datetime


class MonteCarloSimulator:
    """
    Parametric Monte Carlo simulator using normal distribution
    Models year-to-year return volatility for realistic scenario analysis
    """
    
    def __init__(self, 
                 mean_return: float = 0.10,
                 std_dev: float = 0.18,
                 random_seed: int = None):
        """
        Initialize Monte Carlo simulator
        
        Parameters:
        - mean_return: Expected annual nominal return (e.g., 0.10 for 10%)
        - std_dev: Standard deviation of returns (e.g., 0.18 for stocks)
        - random_seed: For reproducibility
        """
        self.mean_return = mean_return
        self.std_dev = std_dev
        
        if random_seed:
            np.random.seed(random_seed)
    
    def generate_return_sequence(self, years: int) -> np.ndarray:
        """Generate a random sequence of annual returns"""
        return np.random.normal(self.mean_return, self.std_dev, years)
    
    def run_retirement_simulation(self,
                                  portfolio,
                                  scenario,
                                  num_simulations: int = 1000,
                                  owner_age: int = None,
                                  college_info: dict = None) -> Dict:
        """
        Run Monte Carlo simulation for retirement scenario
        
        Args:
            portfolio: Portfolio object with accounts
            scenario: Scenario object with retirement parameters
            num_simulations: Number of Monte Carlo simulations to run
            owner_age: Current age of primary owner (required)
            college_info: Dict mapping child name to (start_year, annual_cost)
        
        Returns dict with:
        - success_rate: Probability portfolio survives
        - percentiles: 10th, 25th, 50th, 75th, 90th percentile outcomes
        - final_balance_distribution: Array of final balances
        - min_balance_distribution: Array of minimum balances reached
        - failure_years: List of years when failures occurred
        """
        if owner_age is None:
            raise ValueError("owner_age must be provided for Monte Carlo simulation")
        
        if college_info is None:
            college_info = {}
        
        print(f"\nRunning {num_simulations} Monte Carlo simulations...")
        
        results = {
            'final_balances': [],
            'min_balances': [],
            'failure_years': [],
            'age_70_balances': [],
            'age_80_balances': [],
            'paths': []  # Store some sample paths for visualization
        }
        
        for sim in range(num_simulations):
            if sim % 100 == 0:
                print(f"  Simulation {sim}/{num_simulations}...", end='\r')
            
            # Run single simulation with random returns
            outcome = self._run_single_retirement_path(portfolio, scenario, owner_age, college_info)
            
            results['final_balances'].append(outcome['final_balance'])
            results['min_balances'].append(outcome['min_balance'])
            results['age_70_balances'].append(outcome.get('age_70_balance', 0))
            results['age_80_balances'].append(outcome.get('age_80_balance', 0))
            
            if outcome['failure_year']:
                results['failure_years'].append(outcome['failure_year'])
            
            # Store first 100 paths for visualization
            if sim < 100:
                results['paths'].append(outcome['path'])
        
        print(f"  Completed {num_simulations} simulations!      ")
        
        # Calculate statistics
        final_balances = np.array(results['final_balances'])
        min_balances = np.array(results['min_balances'])
        
        success_count = sum(1 for b in final_balances if b > 500000)
        success_rate = success_count / num_simulations
        
        return {
            'success_rate': success_rate,
            'success_count': success_count,
            'total_simulations': num_simulations,
            'final_balance_percentiles': {
                '10th': np.percentile(final_balances, 10),
                '25th': np.percentile(final_balances, 25),
                '50th': np.percentile(final_balances, 50),
                '75th': np.percentile(final_balances, 75),
                '90th': np.percentile(final_balances, 90)
            },
            'min_balance_percentiles': {
                '10th': np.percentile(min_balances, 10),
                '50th': np.percentile(min_balances, 50),
                '90th': np.percentile(min_balances, 90)
            },
            'age_70_percentiles': {
                '10th': np.percentile([b for b in results['age_70_balances'] if b > 0], 10) if results['age_70_balances'] else 0,
                '50th': np.percentile([b for b in results['age_70_balances'] if b > 0], 50) if results['age_70_balances'] else 0,
                '90th': np.percentile([b for b in results['age_70_balances'] if b > 0], 90) if results['age_70_balances'] else 0
            },
            'age_80_percentiles': {
                '10th': np.percentile([b for b in results['age_80_balances'] if b > 0], 10) if results['age_80_balances'] else 0,
                '50th': np.percentile([b for b in results['age_80_balances'] if b > 0], 50) if results['age_80_balances'] else 0,
                '90th': np.percentile([b for b in results['age_80_balances'] if b > 0], 90) if results['age_80_balances'] else 0
            },
            'failure_years': results['failure_years'],
            'most_common_failure': self._most_common(results['failure_years']) if results['failure_years'] else None,
            'sample_paths': results['paths'][:20]  # Return 20 sample paths
        }
    
    def _run_single_retirement_path(self, portfolio_template, scenario, owner_age, college_info) -> Dict:
        """Run a single retirement simulation with stochastic returns"""
        from financial_planner import Portfolio, Account, CollegeCalculator
        
        # Create deep copy of portfolio for this simulation
        accounts_copy = []
        for acc in portfolio_template.accounts:
            acc_copy = Account(
                owner=acc.owner,
                account_type=acc.account_type,
                is_pretax=acc.is_pretax,
                current_balance=acc.current_balance,
                annual_contribution=acc.annual_contribution,
                growth_rate=acc.growth_rate
            )
            accounts_copy.append(acc_copy)
        
        portfolio = Portfolio(accounts_copy, portfolio_template.family)
        
        # Generate random return sequence
        projection_years = 50
        return_sequence = self.generate_return_sequence(projection_years)
        
        # Setup college and 529 logic
        current_year = datetime.now().year
        contribution_years = scenario.contribution_years or (scenario.retirement_age - owner_age)
        contribution_growth_rate = getattr(scenario, 'contribution_growth_rate', 0.0)
        inflation_rate = scenario.inflation_rate
        
        # Calculate when to stop 529 contributions (use simple heuristic)
        calc = CollegeCalculator()
        stop_529_contrib = {}
        for acc in portfolio.accounts:
            if acc.account_type == "529" and acc.owner in college_info:
                college_start = college_info[acc.owner][0]
                nominal_growth = self.mean_return  # Already nominal in Monte Carlo
                years_to_stop, _ = calc.years_to_stop_contributing(
                    acc.current_balance,
                    acc.annual_contribution,
                    college_start,
                    nominal_growth
                )
                stop_529_contrib[acc.owner] = years_to_stop
        
        min_balance = float('inf')
        age_70_balance = None
        age_80_balance = None
        failure_year = None
        path = []
        
        for year in range(projection_years):
            year_num = current_year + year
            current_age = owner_age + year
            
            # Handle college withdrawals from 529s
            for acc in portfolio.accounts:
                if acc.account_type == "529" and acc.owner in college_info:
                    college_start, annual_cost_2026 = college_info[acc.owner]
                    college_end = college_start + 4
                    
                    if college_start <= year_num < college_end:
                        years_since_start = year_num - college_start
                        # Calculate inflation from base year to college year
                        years_to_college = college_start - current_year
                        inflated_cost = annual_cost_2026 * (1 + inflation_rate) ** (years_to_college + years_since_start)
                        acc.withdraw(inflated_cost)
            
            # Contribution phase
            if year < contribution_years:
                redirected_to_posttax = 0
                
                for acc in portfolio.accounts:
                    contribution_amount = acc.annual_contribution * (1 + contribution_growth_rate) ** year
                    
                    if acc.account_type == "529":
                        # Check if should still contribute
                        if acc.owner in stop_529_contrib and year < stop_529_contrib[acc.owner]:
                            acc.contribute(contribution_amount)
                        else:
                            # Redirect to post-tax
                            redirected_to_posttax += contribution_amount
                    else:
                        # Regular retirement accounts
                        acc.contribute(contribution_amount)
                    
                    # Apply stochastic return
                    acc.grow(1, growth_rate_override=return_sequence[year])
                
                # Distribute redirected 529 funds to post-tax accounts
                if redirected_to_posttax > 0:
                    posttax_accounts = [acc for acc in portfolio.accounts 
                                       if not acc.is_pretax and acc.account_type != "529"]
                    if posttax_accounts:
                        total_posttax_balance = sum(acc.get_balance() for acc in posttax_accounts)
                        for acc in posttax_accounts:
                            if total_posttax_balance > 0:
                                proportion = acc.get_balance() / total_posttax_balance
                            else:
                                proportion = 1.0 / len(posttax_accounts)
                            acc.contribute(redirected_to_posttax * proportion)
            
            # Withdrawal phase  
            elif year >= contribution_years:
                adjusted_spending = scenario.annual_spending * (1 + inflation_rate) ** (year - contribution_years)
                withdrawals, shortfall = portfolio.withdraw_tax_smart(adjusted_spending, current_age)
                
                # Apply stochastic return
                for acc in portfolio.accounts:
                    if acc.get_balance() > 0:
                        acc.grow(1, growth_rate_override=return_sequence[year])
            
            # Track metrics
            total_balance = portfolio.total_balance()
            path.append({'year': year_num, 'age': current_age, 'balance': total_balance})
            
            if total_balance < min_balance:
                min_balance = total_balance
            
            if current_age == 70:
                age_70_balance = total_balance
            if current_age == 80:
                age_80_balance = total_balance
            
            # Check for failure
            if total_balance < 500000 and failure_year is None and year >= contribution_years:
                failure_year = year_num
        
        return {
            'final_balance': portfolio.total_balance(),
            'min_balance': min_balance,
            'age_70_balance': age_70_balance,
            'age_80_balance': age_80_balance,
            'failure_year': failure_year,
            'path': path
        }
    
    def run_529_simulation(self,
                          current_balance: float,
                          annual_contribution: float,
                          years_until_college: int,
                          target_amount: float,
                          num_simulations: int = 1000) -> Dict:
        """
        Run Monte Carlo for 529 college savings
        
        Returns probability of meeting target and percentile outcomes
        """
        results = []
        
        for sim in range(num_simulations):
            # Generate returns for contribution phase
            contribution_returns = self.generate_return_sequence(years_until_college)
            
            balance = current_balance
            for year_return in contribution_returns:
                balance = balance * (1 + year_return) + annual_contribution
            
            results.append(balance)
        
        results = np.array(results)
        success_count = sum(1 for b in results if b >= target_amount)
        
        return {
            'success_rate': success_count / num_simulations,
            'success_count': success_count,
            'total_simulations': num_simulations,
            'target_amount': target_amount,
            'percentiles': {
                '10th': np.percentile(results, 10),
                '25th': np.percentile(results, 25),
                '50th': np.percentile(results, 50),
                '75th': np.percentile(results, 75),
                '90th': np.percentile(results, 90)
            },
            'mean': np.mean(results),
            'shortfall_risk': {
                '10th_percentile_shortfall': max(0, target_amount - np.percentile(results, 10)),
                'median_shortfall': max(0, target_amount - np.percentile(results, 50))
            }
        }
    
    @staticmethod
    def _most_common(lst: List) -> int:
        """Find most common element in list"""
        if not lst:
            return None
        from collections import Counter
        return Counter(lst).most_common(1)[0][0]


if __name__ == "__main__":
    # Quick test
    print("Monte Carlo Simulator Module Loaded")
    
    simulator = MonteCarloSimulator(mean_return=0.10, std_dev=0.18)
    
    # Test return generation
    returns = simulator.generate_return_sequence(10)
    print(f"\nSample 10-year return sequence:")
    for i, r in enumerate(returns):
        print(f"  Year {i+1}: {r*100:+.1f}%")
    
    print(f"\nMean: {returns.mean()*100:.1f}%")
    print(f"Std Dev: {returns.std()*100:.1f}%")
