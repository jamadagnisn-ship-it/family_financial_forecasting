"""
Financial Planning Dashboard - Core Classes
Comprehensive retirement and college planning system
"""

from dataclasses import dataclass
from typing import List, Dict, Tuple
import pandas as pd
import numpy as np
from datetime import datetime


@dataclass
class Account:
    """Represents an individual investment or retirement account"""
    owner: str
    account_type: str  # e.g., "401K", "Vanguard", "529"
    is_pretax: bool
    current_balance: float
    annual_contribution: float
    growth_rate: float = 0.07  # Default 7% real return
    contribution_start_age: int = None  # Owner's current age
    contribution_end_age: int = None  # When contributions stop
    withdrawal_start_age: int = None  # When withdrawals begin
    
    def __post_init__(self):
        """Initialize derived attributes"""
        self.balance_history = [self.current_balance]
        self.contribution_history = [0]  # First year is current state
        self.withdrawal_history = [0]
    
    def grow(self, years: int = 1, growth_rate_override: float = None) -> None:
        """Apply growth for specified number of years"""
        rate = growth_rate_override if growth_rate_override is not None else self.growth_rate
        for _ in range(years):
            self.current_balance *= (1 + rate)
            self.balance_history.append(self.current_balance)
    
    def contribute(self, amount: float) -> None:
        """Add contribution to account"""
        self.current_balance += amount
        self.contribution_history.append(amount)
    
    def withdraw(self, amount: float) -> float:
        """
        Withdraw from account. Returns actual amount withdrawn.
        Cannot withdraw more than available balance.
        """
        actual_withdrawal = min(amount, self.current_balance)
        self.current_balance -= actual_withdrawal
        self.withdrawal_history.append(actual_withdrawal)
        return actual_withdrawal
    
    def project_balance(self, years: int, contributions: List[float] = None) -> List[float]:
        """
        Project account balance over specified years
        Returns list of balances for each year
        """
        balances = [self.current_balance]
        current = self.current_balance
        
        for year in range(years):
            # Apply growth
            current *= (1 + self.growth_rate)
            # Add contribution if specified
            if contributions and year < len(contributions):
                current += contributions[year]
            balances.append(current)
        
        return balances
    
    def get_balance(self) -> float:
        """Return current balance"""
        return self.current_balance
    
    def reset_to_initial(self, initial_balance: float) -> None:
        """Reset account to initial state for new scenario"""
        self.current_balance = initial_balance
        self.balance_history = [initial_balance]
        self.contribution_history = [0]
        self.withdrawal_history = [0]


@dataclass
class Person:
    """Represents a family member"""
    name: str
    current_age: int
    birth_year: int = None
    
    def __post_init__(self):
        if self.birth_year is None:
            self.birth_year = datetime.now().year - self.current_age
    
    def age_in_year(self, year: int) -> int:
        """Calculate person's age in a given year"""
        return year - self.birth_year


class CollegeCalculator:
    """Calculate 529 needs and contribution sufficiency"""
    
    def __init__(self, 
                 base_cost_per_year: float = 90000,
                 coverage_target: float = 0.80,
                 inflation_rate: float = 0.03,
                 base_year: int = None):
        self.base_cost_per_year = base_cost_per_year
        self.coverage_target = coverage_target
        self.inflation_rate = inflation_rate
        self.base_year = base_year if base_year is not None else datetime.now().year
    
    def calculate_college_need(self, start_year: int) -> float:
        """
        Calculate total 4-year college cost needed at start year
        Accounts for inflation from base year to college start
        """
        years_to_college = start_year - self.base_year
        inflated_annual_cost = self.base_cost_per_year * (1 + self.inflation_rate) ** years_to_college
        
        # Four years of college, with continuing inflation
        total_need = sum([
            inflated_annual_cost * (1 + self.inflation_rate) ** i 
            for i in range(4)
        ])
        
        return total_need * self.coverage_target
    
    def project_529_value(self, current_balance: float, 
                          annual_contribution: float, 
                          years_until_college: int,
                          growth_rate: float = 0.07) -> float:
        """Project 529 value at college start"""
        balance = current_balance
        for year in range(years_until_college):
            balance = balance * (1 + growth_rate) + annual_contribution
        return balance
    
    def years_to_stop_contributing(self, current_balance: float,
                                   annual_contribution: float,
                                   college_start_year: int,
                                   growth_rate: float = 0.07,
                                   target_amount: float = None) -> Tuple[int, str]:
        """
        Determine when to stop 529 contributions
        Returns (years_to_contribute, status_message)
        
        Args:
            current_balance: Current 529 balance
            annual_contribution: Annual contribution amount
            college_start_year: Year when college starts
            growth_rate: Expected nominal growth rate
            target_amount: Optional target amount to reach (if None, calculates default)
        """
        years_until_college = college_start_year - self.base_year
        
        # Use provided target or calculate default
        if target_amount is None:
            target_amount = self.calculate_college_need(college_start_year)
        
        # Check if already sufficient with no more contributions
        projected_no_contrib = current_balance * (1 + growth_rate) ** years_until_college
        if projected_no_contrib >= target_amount:
            return (0, f"Already sufficient! Current trajectory: ${projected_no_contrib:,.0f}, Need: ${target_amount:,.0f}")
        
        # Binary search for optimal contribution years
        for years_contrib in range(years_until_college + 1):
            projected = self.project_529_value(
                current_balance, 
                annual_contribution, 
                years_contrib, 
                growth_rate
            )
            # Then grow without contributions for remaining years
            remaining_years = years_until_college - years_contrib
            final_value = projected * (1 + growth_rate) ** remaining_years
            
            if final_value >= target_amount:
                return (years_contrib, f"Contribute {years_contrib} more years to reach ${target_amount:,.0f}")
        
        # If never sufficient
        max_value = self.project_529_value(
            current_balance, 
            annual_contribution, 
            years_until_college, 
            growth_rate
        )
        shortfall = target_amount - max_value
        return (years_until_college, 
                f"May fall short by ${shortfall:,.0f}. Consider increasing contributions.")


class Portfolio:
    """Aggregates all accounts and runs retirement scenarios"""
    
    def __init__(self, accounts: List[Account], family: List[Person]):
        self.accounts = accounts
        self.family = family
        self.initial_balances = {i: acc.current_balance for i, acc in enumerate(accounts)}
    
    def total_balance(self) -> float:
        """Return total portfolio value"""
        return sum(acc.get_balance() for acc in self.accounts)
    
    def pretax_balance(self) -> float:
        """Return total pre-tax account balance"""
        return sum(acc.get_balance() for acc in self.accounts if acc.is_pretax)
    
    def posttax_balance(self) -> float:
        """Return total post-tax account balance"""
        return sum(acc.get_balance() for acc in self.accounts 
                  if not acc.is_pretax and acc.account_type != "529")
    
    def education_balance(self) -> float:
        """Return total 529 account balance"""
        return sum(acc.get_balance() for acc in self.accounts if acc.account_type == "529")
    
    def reset_accounts(self) -> None:
        """Reset all accounts to initial state"""
        for i, acc in enumerate(self.accounts):
            acc.reset_to_initial(self.initial_balances[i])
    
    def withdraw_tax_smart(self, amount_needed: float, owner_age: int) -> Dict[str, float]:
        """
        Withdraw from accounts in tax-efficient order
        Order: Post-tax brokerage → Roth (future) → Pre-tax (if age >= 59.5)
        Returns dict of withdrawal sources and amounts
        """
        withdrawals = {}
        remaining = amount_needed
        
        # First: Post-tax accounts (no penalty, already taxed)
        for acc in self.accounts:
            if remaining <= 0:
                break
            if not acc.is_pretax and acc.account_type != "529" and acc.get_balance() > 0:
                withdrawn = acc.withdraw(remaining)
                withdrawals[f"{acc.owner}_{acc.account_type}"] = withdrawn
                remaining -= withdrawn
        
        # Second: Pre-tax accounts (only if age >= 59.5 to avoid penalty)
        if remaining > 0 and owner_age >= 59.5:
            for acc in self.accounts:
                if remaining <= 0:
                    break
                if acc.is_pretax and acc.get_balance() > 0:
                    withdrawn = acc.withdraw(remaining)
                    withdrawals[f"{acc.owner}_{acc.account_type}"] = withdrawn
                    remaining -= withdrawn
        
        return withdrawals, remaining
    
    def get_stock_percentage(self,
                            strategy: str,
                            account_type: str,
                            age: int) -> float:
        """
        Calculate stock allocation percentage (0-100) for visualization.
        
        Args:
            strategy: "Fixed", "Aggressive", "Moderate", or "Conservative"
            account_type: "529" or any other (retirement accounts)
            age: Current age (owner for retirement accounts, beneficiary for 529s)
        
        Returns:
            Stock percentage (0-100)
        """
        if strategy == "Fixed":
            # Fixed strategy doesn't use age-based allocation
            return None
        
        # Calculate stock percentage based on strategy and account type
        if account_type == "529":
            # For 529 accounts, use child's age with steeper glide path
            # Cap age at 18 to keep allocation flat during college years (18-22)
            effective_age = min(age, 18)
            
            if strategy == "Aggressive":
                stock_pct = max(20, 95 - (effective_age * 4.2))
            elif strategy == "Moderate":
                stock_pct = max(18, 85 - (effective_age * 3.7))
            else:  # Conservative
                stock_pct = max(17, 75 - (effective_age * 3.2))
        else:
            # For retirement accounts, use traditional age-based formulas
            if strategy == "Aggressive":
                stock_pct = max(20, 120 - age)
            elif strategy == "Moderate":
                stock_pct = max(10, 110 - age)
            else:  # Conservative
                stock_pct = max(10, 100 - age)
        
        return stock_pct
    
    def _calculate_age_based_allocation(self, 
                                        strategy: str, 
                                        account_type: str, 
                                        age: int,
                                        stock_return: float = 0.07,
                                        bond_return: float = 0.025) -> float:
        """
        Calculate age-appropriate stock allocation percentage and resulting growth rate.
        
        Args:
            strategy: "Fixed", "Aggressive", "Moderate", or "Conservative"
            account_type: "529" or any other (retirement accounts)
            age: Current age (owner for retirement accounts, beneficiary for 529s)
            stock_return: Expected real return for stocks (default 7%)
            bond_return: Expected real return for bonds (default 2.5%)
        
        Returns:
            Expected real growth rate for this account at this age
        """
        if strategy == "Fixed":
            # Use the fixed stock return (for backward compatibility)
            return stock_return
        
        # Get stock percentage using the helper method
        stock_pct = self.get_stock_percentage(strategy, account_type, age)
        
        # Convert to decimal
        stock_allocation = stock_pct / 100.0
        
        # Calculate blended return using separate stock and bond returns
        blended_return = (stock_allocation * stock_return) + ((1 - stock_allocation) * bond_return)
        
        return blended_return
    
    def simulate_scenario(self, 
                         retirement_age: int,
                         annual_spending: float,
                         inflation_rate: float = 0.03,
                         projection_years: int = 50,
                         contribution_years: int = None,
                         college_info: dict = None,
                         contribution_growth_rate: float = 0.0,
                         mortgage_info: dict = None,
                         owner_current_age: int = 42,
                         redirect_to_pretax: bool = False,
                         retirement_ages: dict = None,
                         adults_info: dict = None,
                         partial_retirement_coverage: float = 1.0,
                         allocation_strategy: str = "Fixed",
                         stock_return: float = 0.07,
                         bond_return: float = 0.025) -> pd.DataFrame:
        """
        Simulate a retirement scenario at the portfolio level with support for staggered retirement.
        Returns DataFrame with year-by-year account balances.
        
        Args:
            retirement_age: Age when FIRST person retires (when portfolio withdrawals begin)
            annual_spending: Annual spending in retirement (in today's/real dollars)
            inflation_rate: Expected annual inflation rate
            projection_years: Number of years to project forward
            contribution_years: Years until first person retires (None = auto-calculate from retirement_age)
            college_info: Dict mapping child name to (start_year, annual_cost_2026_dollars)
            contribution_growth_rate: Annual increase in contributions (e.g., 0.02 for 2% raises)
            mortgage_info: Dict with keys 'monthly_emi' and 'years_remaining' for mortgage tracking
            owner_current_age: Current age of the primary account owner
            redirect_to_pretax: If True, redirect 529/mortgage funds to pre-tax; if False, to post-tax
            retirement_ages: Dict mapping each owner name to their individual retirement age (for staggered retirement)
            adults_info: Dict mapping adult name to current age
            partial_retirement_coverage: Fraction of spending from portfolio when first person retires (0.0-1.0)
                                        Remaining covered by still-working spouse. Full coverage when last person retires.
            allocation_strategy: "Fixed", "Aggressive", "Moderate", or "Conservative" for age-based allocation
            stock_return: Expected real return for stocks (used in glide path strategies)
            bond_return: Expected real return for bonds (used in glide path strategies)
        
        Returns:
            DataFrame with year-by-year projections including balances, contributions, withdrawals
        
        Note on Staggered Retirement:
            - retirement_age / contribution_years: Define when portfolio withdrawals START (first person retires)
            - retirement_ages dict: Maps each owner to THEIR individual retirement age
            - Individual contributions: Each owner stops contributing when THEY reach their retirement age
            - Spending coverage: Partial at first retirement, full when last person retires
        """
        # Reset to initial state
        self.reset_accounts()
        
        # If contribution_years not specified, contribute until retirement
        # Get current year dynamically instead of hardcoding
        current_year = datetime.now().year
        
        # Handle case where owner_current_age is None
        if owner_current_age is None:
            # Try to infer from adults_info
            if adults_info and len(adults_info) > 0:
                owner_current_age = list(adults_info.values())[0]
            else:
                raise ValueError("owner_current_age must be provided or adults_info must contain at least one adult. "
                               "Please ensure your account data is properly loaded and validated.")
        
        owner_age = owner_current_age
        
        # contribution_years defines when we transition from "accumulation" to "retirement" phase globally
        # This is when the FIRST person retires and portfolio withdrawals begin
        # However, individual owners continue contributing until THEIR retirement age (see per-owner logic below)
        if contribution_years is None:
            contribution_years = retirement_age - owner_age
        
        # Default college info to empty dict if not provided
        if college_info is None:
            college_info = {}
        
        # Calculate 529 contribution stop years using actual calculator
        from financial_planner import CollegeCalculator
        calc = CollegeCalculator()
        stop_529_contrib = {}
        redirected_529_amounts = {}
        
        for acc in self.accounts:
            if acc.account_type == "529" and acc.owner in college_info:
                college_start, annual_cost = college_info[acc.owner]
                # Calculate total 4-year target from annual cost
                target_amount = annual_cost * 4
                nominal_growth = acc.growth_rate + inflation_rate
                years_to_stop, _ = calc.years_to_stop_contributing(
                    acc.current_balance,
                    acc.annual_contribution,
                    college_start,
                    nominal_growth,
                    target_amount=target_amount
                )
                stop_529_contrib[acc.owner] = years_to_stop
                redirected_529_amounts[acc.owner] = acc.annual_contribution
        
        # Handle mortgage tracking
        mortgage_payoff_year = None
        annual_mortgage_payment = 0
        if mortgage_info and mortgage_info.get('monthly_emi', 0) > 0:
            monthly_emi = mortgage_info['monthly_emi']
            years_remaining = mortgage_info['years_remaining']
            annual_mortgage_payment = monthly_emi * 12
            mortgage_payoff_year = years_remaining  # Year index when paid off
        
        results = []
        
        # Calculate nominal growth rate for consistency with nominal spending
        nominal_growth_rate = None  # Will be set per account type
        
        for year in range(projection_years):
            year_num = current_year + year
            year_data = {
                'year': year_num,
                'owner_age': owner_age + year,
                'total_balance': self.total_balance(),
                'pretax_balance': self.pretax_balance(),
                'posttax_balance': self.posttax_balance(),
                'education_balance': self.education_balance(),
            }
            
            # Handle college withdrawals for 529 accounts
            total_college_withdrawals = 0
            for acc in self.accounts:
                if acc.account_type == "529" and acc.owner in college_info:
                    college_start, annual_cost_2026 = college_info[acc.owner]
                    college_end = college_start + 4
                    
                    # Check if in college years
                    if college_start <= year_num < college_end:
                        years_since_start = year_num - college_start
                        # Inflate college cost from base year to college year
                        years_to_college = college_start - current_year
                        inflated_cost = annual_cost_2026 * (1 + inflation_rate) ** (years_to_college + years_since_start)
                        
                        # Withdraw for this year
                        withdrawal = acc.withdraw(inflated_cost)
                        total_college_withdrawals += withdrawal
            
            year_data['college_withdrawals'] = total_college_withdrawals
            
            # Contributions phase (before retirement)
            if year < contribution_years:
                # Track redirected 529 funds
                redirected_to_posttax = 0
                
                # Track mortgage payments and potential redirection
                mortgage_payment_this_year = 0
                redirected_mortgage = 0
                
                if mortgage_payoff_year is not None:
                    if year < mortgage_payoff_year:
                        # Still paying mortgage
                        mortgage_payment_this_year = annual_mortgage_payment
                    else:
                        # Mortgage paid off - redirect to savings!
                        redirected_mortgage = annual_mortgage_payment
                
                for acc in self.accounts:
                    # Calculate contribution with growth rate applied
                    contribution_amount = acc.annual_contribution * (1 + contribution_growth_rate) ** year
                    
                    # Calculate age-based growth rate for this account
                    if acc.account_type == "529":
                        # For 529, use child's age (beneficiary)
                        # Child's age = their current age (stored in college_info indirectly) + years
                        if acc.owner in college_info:
                            college_start_year, _ = college_info[acc.owner]
                            # If college starts at 18, calculate child's current age
                            years_until_college = college_start_year - current_year
                            child_current_age = 18 - years_until_college
                            child_age_this_year = child_current_age + year
                        else:
                            # Fallback: assume child is 0 years old
                            child_age_this_year = year
                        
                        age_based_real_return = self._calculate_age_based_allocation(
                            allocation_strategy, 
                            "529", 
                            child_age_this_year,
                            stock_return,
                            bond_return
                        )
                    else:
                        # For retirement accounts, use owner's age
                        if adults_info and acc.owner in adults_info:
                            owner_age_this_year = adults_info[acc.owner] + year
                        else:
                            # Fallback to primary owner age
                            owner_age_this_year = owner_age + year
                        
                        age_based_real_return = self._calculate_age_based_allocation(
                            allocation_strategy,
                            acc.account_type,
                            owner_age_this_year,
                            stock_return,
                            bond_return
                        )
                    
                    # Use nominal growth rate (real + inflation) for this account
                    # This keeps balances consistent with nominal spending
                    nominal_rate = age_based_real_return + inflation_rate
                    
                    # Check if this account owner has retired (for staggered retirement)
                    # Each owner stops contributing when THEY reach their individual retirement age
                    owner_retired = False
                    if retirement_ages and adults_info and acc.owner in adults_info:
                        # Calculate owner's current age at this year
                        owner_current_age_this_year = adults_info[acc.owner] + year
                        # Check if they've reached their retirement age
                        if acc.owner in retirement_ages:
                            owner_retired = owner_current_age_this_year >= retirement_ages[acc.owner]
                    
                    if acc.account_type == "529":
                        # Check if should still contribute to 529
                        if acc.owner in stop_529_contrib and year < stop_529_contrib[acc.owner]:
                            acc.contribute(contribution_amount)
                        else:
                            # Redirect 529 contribution to post-tax accounts
                            redirected_to_posttax += contribution_amount
                        acc.grow(1, growth_rate_override=nominal_rate)
                    else:
                        # Regular retirement accounts - only contribute if owner hasn't retired
                        if not owner_retired:
                            acc.contribute(contribution_amount)
                        acc.grow(1, growth_rate_override=nominal_rate)
                
                # Add redirected mortgage payment to post-tax redirection pool
                redirected_to_posttax += redirected_mortgage
                
                # Distribute redirected 529 funds + mortgage based on user preference
                if redirected_to_posttax > 0:
                    if redirect_to_pretax:
                        # Redirect to pre-tax accounts (401k/IRA)
                        target_accounts = [acc for acc in self.accounts if acc.is_pretax]
                    else:
                        # Redirect to post-tax accounts (brokerage)
                        target_accounts = [acc for acc in self.accounts 
                                          if not acc.is_pretax and acc.account_type != "529"]
                    
                    if target_accounts:
                        # Split proportionally by current balance
                        total_target_balance = sum(acc.get_balance() for acc in target_accounts)
                        for acc in target_accounts:
                            if total_target_balance > 0:
                                proportion = acc.get_balance() / total_target_balance
                            else:
                                proportion = 1.0 / len(target_accounts)
                            acc.contribute(redirected_to_posttax * proportion)
                
                year_data['redirected_529'] = redirected_to_posttax - redirected_mortgage
                year_data['mortgage_payment'] = mortgage_payment_this_year
                year_data['redirected_mortgage'] = redirected_mortgage
            
            # Withdrawal phase (after first person retires)
            # NOTE: Individual owners may still be contributing to their accounts if they haven't retired yet
            # This phase begins when year >= contribution_years (first retirement), but spending coverage
            # transitions from partial to full as remaining adults retire (see staggered retirement logic)
            elif year >= contribution_years:
                # Calculate inflation-adjusted spending
                base_adjusted_spending = annual_spending * (1 + inflation_rate) ** (year - contribution_years)
                
                # Handle partial retirement coverage (staggered retirement)
                # Check if all adults have retired
                all_retired = True
                if retirement_ages and adults_info:
                    for adult_name, adult_age in adults_info.items():
                        adult_age_this_year = adult_age + year
                        if adult_name in retirement_ages:
                            if adult_age_this_year < retirement_ages[adult_name]:
                                all_retired = False
                                break
                
                # Apply partial coverage if not all retired yet
                if all_retired:
                    adjusted_spending = base_adjusted_spending
                    coverage_percentage = 1.0
                else:
                    adjusted_spending = base_adjusted_spending * partial_retirement_coverage
                    coverage_percentage = partial_retirement_coverage
                
                # Withdraw to meet spending needs
                withdrawals, shortfall = self.withdraw_tax_smart(adjusted_spending, owner_age + year)
                
                year_data['spending'] = adjusted_spending
                year_data['nominal_spending'] = base_adjusted_spending  # Full spending amount
                year_data['coverage_percentage'] = coverage_percentage
                year_data['shortfall'] = shortfall
                year_data['withdrawals'] = withdrawals
                
                # Grow remaining balances using nominal growth rate (including 529s if not withdrawn)
                for acc in self.accounts:
                    if acc.get_balance() > 0:
                        nominal_rate = acc.growth_rate + inflation_rate
                        acc.grow(1, growth_rate_override=nominal_rate)
            
            # Store individual account balances
            for i, acc in enumerate(self.accounts):
                year_data[f'acc_{i}_{acc.owner}_{acc.account_type}'] = acc.get_balance()
            
            results.append(year_data)
        
        return pd.DataFrame(results)
    
    def check_scenario_success(self, scenario_df: pd.DataFrame, min_balance: float = 0) -> Dict:
        """
        Check if retirement scenario is successful
        Success = portfolio never depletes (goes to zero or negative)
        
        Args:
            scenario_df: DataFrame with projection results
            min_balance: Minimum acceptable balance (default 0 = no depletion)
        """
        final_balance = scenario_df['total_balance'].iloc[-1]
        min_portfolio_balance = scenario_df['total_balance'].min()
        years_until_depletion = None
        
        # Check if portfolio depletes below minimum threshold
        depletion_year = scenario_df[scenario_df['total_balance'] <= min_balance]
        if not depletion_year.empty:
            years_until_depletion = depletion_year.iloc[0]['year']
        
        # Success = portfolio stays above minimum threshold throughout projection
        success = min_portfolio_balance > min_balance
        
        return {
            'success': success,
            'final_balance': final_balance,
            'min_balance': min_portfolio_balance,
            'years_until_depletion': years_until_depletion
        }
    
    def generate_allocation_history(self,
                                   allocation_strategy: str,
                                   projection_years: int,
                                   owner_current_age: int,
                                   college_info: dict = None,
                                   adults_info: dict = None) -> pd.DataFrame:
        """
        Generate allocation percentage history over projection period.
        
        Args:
            allocation_strategy: "Fixed", "Aggressive", "Moderate", or "Conservative"
            projection_years: Number of years to project
            owner_current_age: Current age of primary owner
            college_info: Dict mapping child name to (start_year, annual_cost)
            adults_info: Dict mapping adult name to current age
        
        Returns:
            DataFrame with allocation percentages by account type over time
        """
        if allocation_strategy == "Fixed":
            # Fixed strategy doesn't have allocation history
            return None
        
        current_year = datetime.now().year
        results = []
        
        for year in range(projection_years):
            year_data = {
                'year': current_year + year,
                'owner_age': owner_current_age + year
            }
            
            # Calculate allocation for retirement accounts (non-529)
            retirement_accounts = [acc for acc in self.accounts if acc.account_type != "529"]
            if retirement_accounts:
                # Use first adult's age for primary retirement allocation
                if adults_info:
                    first_adult = list(adults_info.keys())[0]
                    owner_age_this_year = adults_info[first_adult] + year
                else:
                    owner_age_this_year = owner_current_age + year
                
                stock_pct = self.get_stock_percentage(
                    allocation_strategy,
                    "retirement",  # Generic non-529
                    owner_age_this_year
                )
                year_data['retirement_stocks'] = stock_pct
                year_data['retirement_bonds'] = 100 - stock_pct
            
            # Calculate allocation for 529 accounts
            for acc in self.accounts:
                if acc.account_type == "529" and acc.owner in college_info:
                    college_start_year, _ = college_info[acc.owner]
                    years_until_college = college_start_year - current_year
                    child_current_age = 18 - years_until_college
                    child_age_this_year = child_current_age + year
                    
                    stock_pct = self.get_stock_percentage(
                        allocation_strategy,
                        "529",
                        child_age_this_year
                    )
                    year_data[f'{acc.owner}_stocks'] = stock_pct
                    year_data[f'{acc.owner}_bonds'] = 100 - stock_pct
            
            results.append(year_data)
        
        return pd.DataFrame(results)


class Scenario:
    """Bundle of assumptions for a retirement scenario"""
    
    def __init__(self,
                 name: str,
                 retirement_age: int,
                 annual_spending: float,
                 growth_rate: float = 0.07,
                 inflation_rate: float = 0.03,
                 contribution_years: int = None,
                 contribution_growth_rate: float = 0.0):
        self.name = name
        self.retirement_age = retirement_age
        self.annual_spending = annual_spending
        self.growth_rate = growth_rate
        self.inflation_rate = inflation_rate
        self.contribution_years = contribution_years
        self.contribution_growth_rate = contribution_growth_rate
    
    def __repr__(self):
        return f"Scenario(name='{self.name}', retire_at={self.retirement_age}, spending=${self.annual_spending:,})"


if __name__ == "__main__":
    # Example usage
    print("Financial Planner Classes Loaded Successfully!")
    
    # Create sample account
    sample_account = Account(
        owner="Sumanth",
        account_type="401K",
        is_pretax=True,
        current_balance=640000,
        annual_contribution=56000,
        growth_rate=0.07
    )
    
    print(f"\nSample Account: {sample_account.owner}'s {sample_account.account_type}")
    print(f"Current Balance: ${sample_account.get_balance():,.0f}")
    
    # Project 10 years
    balances = sample_account.project_balance(10, [56000] * 10)
    print(f"Projected Balance (10 years): ${balances[-1]:,.0f}")
