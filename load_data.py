"""
Data Loader - Load accounts from CSV and create portfolio
"""

import pandas as pd
from datetime import datetime
from financial_planner import Account, Person, Portfolio, CollegeCalculator


def load_accounts_from_csv(csv_path: str, growth_rate: float = 0.07) -> list:
    """Load accounts from CSV file"""
    df = pd.read_csv(csv_path, encoding='utf-8-sig')
    
    # Clean column names: strip whitespace
    df.columns = df.columns.str.strip()
    
    # Validate required columns
    required_columns = ['Owner', 'Age', 'Type', 'Pre-tax', 'Balance', 'Annual Contribution']
    missing_columns = [col for col in required_columns if col not in df.columns]
    if missing_columns:
        raise ValueError(f"Missing required columns: {missing_columns}. Found columns: {list(df.columns)}")
    
    accounts = []
    for idx, row in df.iterrows():
        try:
            # Convert "Yes"/"No" to boolean
            is_pretax = str(row['Pre-tax']).strip().lower() in ['yes', 'true', '1']
            
            account = Account(
                owner=str(row['Owner']).strip(),
                account_type=str(row['Type']).strip(),
                is_pretax=is_pretax,
                current_balance=float(row['Balance']),
                annual_contribution=float(row['Annual Contribution']),
                growth_rate=growth_rate
            )
            accounts.append(account)
        except KeyError as e:
            raise ValueError(f"Error reading row {idx}: Missing column {e}. Available columns: {list(row.index)}")
        except Exception as e:
            raise ValueError(f"Error reading row {idx}: {str(e)}")
    
    return accounts


def create_family_from_accounts(accounts: list, csv_path: str = "Accounts.csv") -> list:
    """Create family members from account data
    
    Args:
        accounts: List of Account objects (not used directly, but kept for compatibility)
        csv_path: Path to CSV file containing account data with Age column
    
    Returns:
        List of Person objects with unique owners and their ages
    
    Note:
        The Account class doesn't store age, so we need to get it from the CSV.
        This function is primarily for standalone scripts that use load_accounts_from_csv.
    """
    owner_ages = {}
    
    try:
        df = pd.read_csv(csv_path, encoding='utf-8-sig')
        df.columns = df.columns.str.strip()
        
        for _, row in df.iterrows():
            owner_name = str(row['Owner']).strip()
            owner_age = int(row['Age'])
            if owner_name not in owner_ages:
                owner_ages[owner_name] = owner_age
        
        return [Person(name, age) for name, age in owner_ages.items()]
    except Exception as e:
        print(f"Warning: Could not extract family from CSV '{csv_path}': {e}")
        print("Returning empty family list.")
        return []


def analyze_529_plans(accounts: list, children_info: dict = None):
    """Analyze 529 accounts and recommend contribution strategies
    
    Args:
        accounts: List of Account objects
        children_info: Dict mapping child name to current age (optional)
    """
    calculator = CollegeCalculator()
    inflation_rate = 0.03  # 3% inflation
    
    print("\n" + "="*70)
    print("529 COLLEGE SAVINGS ANALYSIS")
    print("="*70)
    
    # If children_info not provided, try to extract from CSV for standalone use
    if children_info is None:
        children_info = {}
        try:
            df = pd.read_csv("Accounts.csv", encoding='utf-8-sig')
            df.columns = df.columns.str.strip()
            for _, row in df.iterrows():
                if str(row['Type']).strip() == "529":
                    child_name = str(row['Owner']).strip()
                    child_age = int(row['Age'])
                    children_info[child_name] = child_age
        except Exception as e:
            print(f"Warning: Could not extract 529 info from CSV: {e}")
    
    for acc in accounts:
        if acc.account_type == "529":
            # Get child age from children_info if available
            if acc.owner in children_info:
                child_age = children_info[acc.owner]
                years_until_college = 18 - child_age
                college_start = datetime.now().year + years_until_college
            else:
                print(f"\nSkipping {acc.owner}'s 529: Age information not available")
                continue
            
            # Use NOMINAL growth rate for 529 projections (real + inflation)
            # College costs are in nominal dollars, so 529 projections should be too
            nominal_growth_rate = acc.growth_rate + inflation_rate
            
            years_until = college_start - datetime.now().year
            target = calculator.calculate_college_need(college_start)
            years_contrib, message = calculator.years_to_stop_contributing(
                acc.current_balance,
                acc.annual_contribution,
                college_start,
                nominal_growth_rate
            )
            
            print(f"\n{acc.owner}'s 529:")
            print(f"  Current Age: {child_age}")
            print(f"  Current Balance: ${acc.current_balance:,.0f}")
            print(f"  Annual Contribution: ${acc.annual_contribution:,.0f}")
            print(f"  College Starts: {college_start} ({years_until} years)")
            print(f"  Target Amount (80% coverage): ${target:,.0f}")
            print(f"  Growth Rate Used: {nominal_growth_rate*100:.1f}% nominal ({acc.growth_rate*100:.1f}% real + {inflation_rate*100:.1f}% inflation)")
            print(f"  Recommendation: {message}")


def print_portfolio_summary(portfolio: Portfolio):
    """Print current portfolio summary"""
    print("\n" + "="*70)
    print("PORTFOLIO SUMMARY")
    print("="*70)
    print(f"Total Portfolio Value: ${portfolio.total_balance():,.0f}")
    print(f"  Post-Tax Accounts: ${portfolio.posttax_balance():,.0f}")
    print(f"  Pre-Tax Accounts: ${portfolio.pretax_balance():,.0f}")
    print(f"  529 Education: ${portfolio.education_balance():,.0f}")
    
    print("\nAccount Details:")
    for i, acc in enumerate(portfolio.accounts):
        tax_status = "Pre-tax" if acc.is_pretax else "Post-tax"
        print(f"  {i+1}. {acc.owner:8} | {acc.account_type:10} | {tax_status:9} | "
              f"${acc.current_balance:>10,.0f} | +${acc.annual_contribution:>7,.0f}/year")


if __name__ == "__main__":
    # Load accounts
    csv_file = "Accounts.csv"
    print("Loading accounts from CSV...")
    accounts = load_accounts_from_csv(csv_file)
    
    # Create family from CSV data
    family = create_family_from_accounts(accounts, csv_path=csv_file)
    
    # Create portfolio
    portfolio = Portfolio(accounts, family)
    
    # Print summary
    print_portfolio_summary(portfolio)
    
    # Analyze 529 plans (will extract child info from CSV)
    analyze_529_plans(accounts)
    
    print("\n" + "="*70)
    print("Data loaded successfully! Ready for scenario analysis.")
    print("="*70)
