"""
Streamlit Dashboard - Interactive Financial Planning
"""

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
import numpy as np
from datetime import datetime
from load_data import load_accounts_from_csv, create_family_from_accounts
from financial_planner import Portfolio, Scenario, CollegeCalculator, Account, Person
from monte_carlo import MonteCarloSimulator
from analytics import initialize_analytics, track_event

# Get current year dynamically
CURRENT_YEAR = datetime.now().year

# Initialize analytics tracking
initialize_analytics()
track_event('page_view')

# Page configuration
st.set_page_config(
    page_title="Financial Planner Dashboard",
    page_icon="💰",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS
st.markdown("""
    <style>
    .big-font {
        font-size:20px !important;
        font-weight: bold;
    }
    .success-box {
        padding: 20px;
        border-radius: 5px;
        background-color: #d4edda;
        border: 1px solid #c3e6cb;
        color: #155724;
    }
    .warning-box {
        padding: 20px;
        border-radius: 5px;
        background-color: #fff3cd;
        border: 1px solid #ffeaa7;
        color: #856404;
    }
    .danger-box {
        padding: 20px;
        border-radius: 5px;
        background-color: #f8d7da;
        border: 1px solid #f5c6cb;
        color: #721c24;
    }
    </style>
    """, unsafe_allow_html=True)


@st.cache_data
def load_initial_data():
    """Load initial account data"""
    accounts = load_accounts_from_csv("Accounts_Template.csv")
    family = create_family_from_accounts(accounts, csv_path="Accounts_Template.csv")
    return accounts, family


def load_data_from_uploaded_file(uploaded_file, growth_rate=0.07):
    """Load accounts from uploaded CSV file"""
    import io
    
    # Read CSV with proper encoding handling
    content = uploaded_file.getvalue().decode("utf-8-sig")  # utf-8-sig handles BOM
    df = pd.read_csv(io.StringIO(content))
    
    # Clean column names: strip whitespace and normalize
    df.columns = df.columns.str.strip()
    
    # Validate required columns
    required_columns = ['Owner', 'Age', 'Type', 'Pre-tax', 'Balance', 'Annual Contribution']
    missing_columns = [col for col in required_columns if col not in df.columns]
    if missing_columns:
        raise ValueError(f"Missing required columns: {missing_columns}. Found columns: {list(df.columns)}")
    
    accounts = []
    owners_info = {}  # Track unique owners with their ages
    children_info = {}  # Track children (529 accounts)
    
    for idx, row in df.iterrows():
        try:
            # Convert "Yes"/"No" to boolean
            is_pretax = str(row['Pre-tax']).strip().lower() in ['yes', 'true', '1']
            
            owner_name = str(row['Owner']).strip()
            owner_age = int(row['Age'])
            account_type = str(row['Type']).strip()
            
            # Track owner information
            if owner_name not in owners_info:
                owners_info[owner_name] = owner_age
            
            # Track children (529 accounts)
            if account_type == "529":
                children_info[owner_name] = owner_age
            
            account = Account(
                owner=owner_name,
                account_type=account_type,
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
    
    # Create family from parsed data
    family = [Person(name, age) for name, age in owners_info.items()]
    
    return accounts, family, children_info


def create_portfolio_with_custom_contributions(base_accounts, child_contributions):
    """Create portfolio with custom 529 contributions
    
    Args:
        base_accounts: List of Account objects
        child_contributions: Dict mapping child name to annual contribution amount
    """
    accounts = []
    for acc in base_accounts:
        new_acc = Account(
            owner=acc.owner,
            account_type=acc.account_type,
            is_pretax=acc.is_pretax,
            current_balance=acc.current_balance,
            annual_contribution=acc.annual_contribution,
            growth_rate=acc.growth_rate
        )
        
        # Override 529 contributions
        if acc.account_type == "529" and acc.owner in child_contributions:
            new_acc.annual_contribution = child_contributions[acc.owner]
        
        accounts.append(new_acc)
    
    return accounts


def validate_account_data(accounts_df):
    """
    Validate account data for consistency and sanity.
    
    Returns: (is_valid: bool, error_messages: List[str])
    """
    errors = []
    
    # Check 1: All ages should be greater than 0
    invalid_ages = accounts_df[accounts_df['Age'] <= 0]
    if not invalid_ages.empty:
        for _, row in invalid_ages.iterrows():
            errors.append(f"❌ Invalid age for {row['Owner']} ({row['Type']}): Age must be > 0, found {row['Age']}")
    
    # Check 2: Same owner should have same age across all accounts
    owner_ages = {}
    for _, row in accounts_df.iterrows():
        owner = str(row['Owner']).strip()
        age = int(row['Age'])
        account_type = str(row['Type']).strip()
        
        if owner in owner_ages:
            if owner_ages[owner] != age:
                errors.append(f"❌ Age mismatch for {owner}: Found {owner_ages[owner]} in one account and {age} in {account_type}")
        else:
            owner_ages[owner] = age
    
    # Check 3: Balance should be non-negative
    invalid_balances = accounts_df[accounts_df['Balance'] < 0]
    if not invalid_balances.empty:
        for _, row in invalid_balances.iterrows():
            errors.append(f"❌ Invalid balance for {row['Owner']} ({row['Type']}): Balance cannot be negative, found ${row['Balance']:,.2f}")
    
    # Check 4: Annual contribution should be non-negative
    invalid_contributions = accounts_df[accounts_df['Annual Contribution'] < 0]
    if not invalid_contributions.empty:
        for _, row in invalid_contributions.iterrows():
            errors.append(f"❌ Invalid contribution for {row['Owner']} ({row['Type']}): Contribution cannot be negative, found ${row['Annual Contribution']:,.2f}")
    
    # Check 5: Owner name should not be empty
    empty_owners = accounts_df[accounts_df['Owner'].isna() | (accounts_df['Owner'].astype(str).str.strip() == '')]
    if not empty_owners.empty:
        errors.append(f"❌ Found {len(empty_owners)} account(s) with empty owner name")
    
    # Check 6: Account type should not be empty
    empty_types = accounts_df[accounts_df['Type'].isna() | (accounts_df['Type'].astype(str).str.strip() == '')]
    if not empty_types.empty:
        errors.append(f"❌ Found {len(empty_types)} account(s) with empty account type")
    
    # Check 7: For 529 accounts, ages should be reasonable for children (typically < 25)
    children_529 = accounts_df[accounts_df['Type'] == '529']
    old_children = children_529[children_529['Age'] > 22]
    if not old_children.empty:
        for _, row in old_children.iterrows():
            errors.append(f"⚠️ Warning: 529 account for {row['Owner']} has age {row['Age']}. Typically 529 beneficiaries are < 22 years old.")
    
    # Check 8: Very young ages for non-529 accounts (likely data entry error)
    adults = accounts_df[accounts_df['Type'] != '529']
    young_adults = adults[adults['Age'] < 18]
    if not young_adults.empty:
        for _, row in young_adults.iterrows():
            errors.append(f"⚠️ Warning: Non-529 account for {row['Owner']} has age {row['Age']}. This seems unusual for retirement accounts.")
    
    # Check 9: Pre-tax column should be valid
    try:
        for _, row in accounts_df.iterrows():
            pretax_val = str(row['Pre-tax']).strip().lower()
            if pretax_val not in ['yes', 'no', 'true', 'false', '1', '0']:
                errors.append(f"⚠️ Warning: Unclear Pre-tax value for {row['Owner']} ({row['Type']}): '{row['Pre-tax']}'. Use 'Yes' or 'No'.")
    except:
        pass  # Skip if there's any parsing issue
    
    # Check 10: Very high balances might be data entry errors
    high_balances = accounts_df[accounts_df['Balance'] > 10000000]
    if not high_balances.empty:
        for _, row in high_balances.iterrows():
            errors.append(f"⚠️ Warning: Very high balance for {row['Owner']} ({row['Type']}): ${row['Balance']:,.0f}. Please verify this is correct.")
    
    # Check 11: Very high contributions might be data entry errors
    high_contributions = accounts_df[accounts_df['Annual Contribution'] > 100000]
    if not high_contributions.empty:
        for _, row in high_contributions.iterrows():
            errors.append(f"⚠️ Warning: Very high annual contribution for {row['Owner']} ({row['Type']}): ${row['Annual Contribution']:,.0f}. Please verify this is correct.")
    
    # Check 12: Check for potential duplicate accounts (same owner + same type)
    owner_type_counts = accounts_df.groupby(['Owner', 'Type']).size()
    duplicates = owner_type_counts[owner_type_counts > 1]
    if not duplicates.empty:
        for (owner, acc_type), count in duplicates.items():
            errors.append(f"⚠️ Warning: {owner} has {count} accounts of type '{acc_type}'. This might be intentional or a duplicate entry.")
    
    is_valid = len([e for e in errors if e.startswith('❌')]) == 0
    
    return is_valid, errors


def plot_portfolio_projection(results_df, scenario_name, children_info=None, primary_owner_age=None):
    """Create interactive Plotly chart for portfolio projection
    
    Args:
        results_df: DataFrame with projection results
        scenario_name: Name of the scenario
        children_info: Dict mapping child name to current age
        primary_owner_age: Current age of primary account owner
    """
    
    fig = make_subplots(
        rows=2, cols=1,
        subplot_titles=('Total Portfolio Value Over Time', 'Account Type Breakdown'),
        vertical_spacing=0.12,
        row_heights=[0.5, 0.5]
    )
    
    # Top chart: Total portfolio
    fig.add_trace(
        go.Scatter(
            x=results_df['owner_age'],
            y=results_df['total_balance'],
            fill='tozeroy',
            name='Total Portfolio',
            line=dict(color='#1f77b4', width=3),
            hovertemplate='Age: %{x}<br>Balance: $%{y:,.0f}<extra></extra>'
        ),
        row=1, col=1
    )
    
    # Bottom chart: Account breakdown
    fig.add_trace(
        go.Scatter(
            x=results_df['owner_age'],
            y=results_df['posttax_balance'],
            name='Post-Tax (Vanguard)',
            line=dict(color='#2ca02c', width=2),
            stackgroup='one',
            hovertemplate='Post-Tax: $%{y:,.0f}<extra></extra>'
        ),
        row=2, col=1
    )
    
    fig.add_trace(
        go.Scatter(
            x=results_df['owner_age'],
            y=results_df['pretax_balance'],
            name='Pre-Tax (401k)',
            line=dict(color='#ff7f0e', width=2),
            stackgroup='one',
            hovertemplate='Pre-Tax: $%{y:,.0f}<extra></extra>'
        ),
        row=2, col=1
    )
    
    fig.add_trace(
        go.Scatter(
            x=results_df['owner_age'],
            y=results_df['education_balance'],
            name='529 Education',
            line=dict(color='#9467bd', width=2),
            stackgroup='one',
            hovertemplate='529: $%{y:,.0f}<extra></extra>'
        ),
        row=2, col=1
    )
    
    # Add vertical lines for college start years (dynamic based on children info)
    if children_info and primary_owner_age:
        ages = results_df['owner_age'].values
        
        for child_name, child_age in children_info.items():
            # Calculate when child turns 18 (college start)
            years_until_college = 18 - child_age
            # Calculate owner's age when child starts college
            owner_age_at_college = primary_owner_age + years_until_college
            
            if owner_age_at_college in ages:
                fig.add_vline(x=owner_age_at_college, line_dash="dash", line_color="purple", 
                             annotation_text=f"{child_name} → College", 
                             annotation_position="top",
                             row=1, col=1)
                fig.add_vline(x=owner_age_at_college, line_dash="dash", line_color="purple",
                             row=2, col=1)
    
    # Add mortgage payoff marker if applicable
    if 'redirected_mortgage' in results_df.columns:
        # Find the first year where redirected_mortgage > 0 (mortgage is paid off)
        payoff_data = results_df[results_df['redirected_mortgage'] > 0]
        if len(payoff_data) > 0:
            payoff_age = payoff_data.iloc[0]['owner_age']
            fig.add_vline(x=payoff_age, line_dash="dot", line_color="green",
                         annotation_text="🏠 Mortgage Paid Off",
                         annotation_position="top",
                         row=1, col=1)
            fig.add_vline(x=payoff_age, line_dash="dot", line_color="green",
                         row=2, col=1)
    
    # Update layout
    fig.update_xaxes(title_text="Your Age", row=2, col=1)
    fig.update_xaxes(title_text="Your Age", row=1, col=1)
    fig.update_yaxes(title_text="Balance ($)", row=1, col=1)
    fig.update_yaxes(title_text="Balance ($)", row=2, col=1)
    
    fig.update_layout(
        height=800,
        hovermode='x unified',
        showlegend=True,
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1
        )
    )
    
    return fig


def plot_allocation_glide_path(allocation_df, children_info=None, primary_owner_age=None):
    '''Create interactive chart showing asset allocation percentages over time
    
    Args:
        allocation_df: DataFrame with allocation percentages over time
        children_info: Dict mapping child name to current age
        primary_owner_age: Current age of primary account owner
    '''
    if allocation_df is None or allocation_df.empty:
        return None
    
    fig = go.Figure()
    
    # Plot retirement account stocks/bonds
    if 'retirement_stocks' in allocation_df.columns:
        fig.add_trace(
            go.Scatter(
                x=allocation_df['owner_age'],
                y=allocation_df['retirement_stocks'],
                name='Retirement Accounts - Stocks',
                line=dict(color='#2E86AB', width=3),
                fill='tonexty',
                hovertemplate='Age: %{x}<br>Stocks: %{y:.1f}%<extra></extra>'
            )
        )
        
        fig.add_trace(
            go.Scatter(
                x=allocation_df['owner_age'],
                y=allocation_df['retirement_bonds'],
                name='Retirement Accounts - Bonds',
                line=dict(color='#A23B72', width=3),
                fill='tozeroy',
                hovertemplate='Age: %{x}<br>Bonds: %{y:.1f}%<extra></extra>'
            )
        )
    
    # Plot 529 account allocations
    if children_info:
        colors_529_stocks = ['#06A77D', '#F18F01']
        colors_529_bonds = ['#C73E1D', '#6A4C93']
        
        color_idx = 0
        for child_name in children_info.keys():
            stock_col = f'{child_name}_stocks'
            bond_col = f'{child_name}_bonds'
            
            if stock_col in allocation_df.columns:
                fig.add_trace(
                    go.Scatter(
                        x=allocation_df['owner_age'],
                        y=allocation_df[stock_col],
                        name=f'{child_name} 529 - Stocks',
                        line=dict(color=colors_529_stocks[color_idx % len(colors_529_stocks)], 
                                 width=2, dash='dot'),
                        hovertemplate=f'{child_name} Stocks: %{{y:.1f}}%<extra></extra>'
                    )
                )
                
                fig.add_trace(
                    go.Scatter(
                        x=allocation_df['owner_age'],
                        y=allocation_df[bond_col],
                        name=f'{child_name} 529 - Bonds',
                        line=dict(color=colors_529_bonds[color_idx % len(colors_529_bonds)], 
                                 width=2, dash='dot'),
                        hovertemplate=f'{child_name} Bonds: %{{y:.1f}}%<extra></extra>'
                    )
                )
                
                color_idx += 1
    
    # Add reference lines
    fig.add_hline(y=60, line_dash="dash", line_color="gray", opacity=0.5,
                 annotation_text="60% Balanced", annotation_position="right")
    fig.add_hline(y=40, line_dash="dash", line_color="gray", opacity=0.5,
                 annotation_text="40%", annotation_position="right")
    
    # Update layout
    fig.update_layout(
        title="Asset Allocation Glide Path Over Time",
        xaxis_title="Your Age",
        yaxis_title="Allocation Percentage (%)",
        height=500,
        hovermode='x unified',
        showlegend=True,
        legend=dict(
            orientation="v",
            yanchor="top",
            y=1,
            xanchor="left",
            x=1.02
        ),
        yaxis=dict(range=[0, 100])
    )
    
    return fig


def analyze_529_status(accounts, college_calculator, inflation_rate, children_info, child_targets,
                       enable_monte_carlo=False, num_simulations=0, growth_rate=0.07, volatility=0.18):
    """Analyze 529 accounts and return status
    
    Args:
        accounts: List of Account objects
        college_calculator: CollegeCalculator instance
        inflation_rate: Annual inflation rate
        children_info: Dict mapping child name to current age
        child_targets: Dict mapping child name to target amount
        enable_monte_carlo: Whether to run Monte Carlo simulation
        num_simulations: Number of Monte Carlo simulations
        growth_rate: Expected real return rate
        volatility: Market volatility (standard deviation)
    """
    status_data = []
    
    for acc in accounts:
        if acc.account_type == "529":
            child_age = children_info.get(acc.owner, 10)
            years_until_college = 18 - child_age
            college_start = CURRENT_YEAR + years_until_college
            
            # Use user-specified target or calculate default
            target = child_targets.get(acc.owner, college_calculator.calculate_college_need(college_start))
            
            # Use NOMINAL growth rate for 529 projections since college costs are in nominal dollars
            nominal_growth_rate = acc.growth_rate + inflation_rate
            
            years_until = years_until_college
            years_contrib, message = college_calculator.years_to_stop_contributing(
                acc.current_balance,
                acc.annual_contribution,
                college_start,
                nominal_growth_rate,
                target_amount=target
            )
            
            projected_value = college_calculator.project_529_value(
                acc.current_balance,
                acc.annual_contribution,
                years_contrib,
                nominal_growth_rate
            )
            remaining_years = years_until - years_contrib
            final_value = projected_value * (1 + nominal_growth_rate) ** remaining_years
            
            coverage_pct = (final_value / target) * 100
            
            # Run Monte Carlo if enabled
            mc_results = None
            if enable_monte_carlo and num_simulations > 0:
                simulator = MonteCarloSimulator(
                    mean_return=nominal_growth_rate,
                    std_dev=volatility
                )
                mc_results = simulator.run_529_simulation(
                    current_balance=acc.current_balance,
                    annual_contribution=acc.annual_contribution,
                    years_until_college=years_until,
                    target_amount=target,
                    num_simulations=num_simulations
                )
            
            status_data.append({
                'child': acc.owner,
                'current_balance': acc.current_balance,
                'annual_contribution': acc.annual_contribution,
                'college_start': college_start,
                'target': target,
                'projected_value': final_value,
                'coverage_pct': coverage_pct,
                'years_contrib': years_contrib,
                'message': message,
                'status': 'success' if coverage_pct >= 100 else ('warning' if coverage_pct >= 90 else 'danger'),
                'monte_carlo': mc_results
            })
    
    return status_data


# Main Dashboard
def main():
    st.title("💰 Family Financial Planning Dashboard")
    
    # Add quick start guide
    with st.expander("📖 Quick Start Guide - First Time Users"):
        st.markdown("""
        **Welcome to the Financial Planner!** Follow these steps to get started:
        
        1. **Download the Template** (in the sidebar) → Fill in your account information
        2. **Upload Your CSV** → Load your personalized data
        3. **Configure 529 Targets** → Set college savings goals for each child
        4. **Adjust Scenarios** → Retirement age, spending, growth rates
        5. **Run Scenario** → Click the big button to see your projections!
        
        **Template Columns:**
        - `Owner`: Your name or child's name
        - `Age`: Current age
        - `Type`: "401K", "Vanguard", "529"
        - `Pre-tax`: "Yes" or "No"
        - `Balance`: Current account balance
        - `Annual Contribution`: Yearly contribution amount
        
        **Important:** For 401K accounts, include employer contributions (e.g., employer match) in the Annual Contribution column.
        
        See `README_TEMPLATE.md` for detailed instructions.
        """)
    
    # Add motivation and disclaimer section
    with st.expander("ℹ️ About This Tool - Motivation, Features & Important Disclaimers"):
        st.markdown("""
        ### Motivation for Developing This Tool
        
        A lack of easy-to-use online tools that can handle more complex multi-year and retirement scenarios for a full family 
        including multiple accounts (both pre and post-tax), 529 accounts and cashflows freed up after a mortgage is paid off. 
        My goal was to have a framework that allows:

        **What This Tool Does:**
        1. Plugging in current balances across multiple accounts, and continued contributions. 
        2. Setting 529 contribution targets for multiple children and modeling their growth, providing a target for stopping contributions when the corpus becomes sufficient. 
        3. Automatic handling of when to stop 529 contributions and diverting those funds to pre- or post-tax investment accounts. 
        4. Modeling the automatic diversion of mortgage payments into pre- or post-tax investment accounts after a house is paid off. 
        5. A simple withdrawal strategy after retirement (first from post-tax and then from pre-tax accounts). 
        6. Allow for simple modeling of staggered retirement of people (spouse retires at different ages).
        7. Monte Carlo simulations to understand probability ranges and market risk.
        8. **Age-based asset allocation glide paths** with blended stock/bond portfolios that automatically adjust risk exposure based on age and strategy (Aggressive/Moderate/Conservative), with separate return and volatility assumptions for stocks and bonds.

        ---
        
        ### Things NOT Handled
        ⚠️ This tool does not include:
        1. Detailed tax treatments and optimizations (state taxes, marginal brackets, RMDs after age 73)
        2. Roth conversions and backdoor Roth strategies
        3. Modeling complex investments such as ESOPs, RSUs, annuities, real estate investments
        4. Expensive one-off costs (weddings, home remodels, buying a second house, a retirement Porsche, large healthcare shocks)
        5. Positive shocks - inheritances, proceeds from sale of a business, etc.
        6. Social security benefits and pensions (you can manually adjust annual spending to account for these)
        7. Healthcare costs and long-term care insurance
        8. Estate planning and beneficiary considerations

        ---
        
        ### Key Assumptions & Caveats
        
        ⚠️ **Growth Rates:** Default 7% real return assumes diversified equity portfolio. Historical returns don't guarantee future performance.
        
        ⚠️ **Inflation:** Default 3% may not match actual future inflation. Sensitivity test with higher rates (4-5%).
        
        ⚠️ **Spending:** Assumes constant real spending. Reality varies (healthcare increases with age, travel in early retirement).
        
        ⚠️ **Sequence of Returns Risk:** Market downturns in early retirement can derail plans even with good average returns. Monte Carlo helps visualize this risk.
        
        ⚠️ **Market Volatility:** Even a "95% success rate" means 1 in 20 chance of portfolio depletion. Run conservative scenarios.
        
        ⚠️ **Contributions:** Assumes steady contributions. Job changes, emergencies, business fluctuations can disrupt plans.

        ---
        
        ### Best Practices
        
        1. **Understand your spending:** Have a sense of current annual spending and what it would look like when you are retired 
           (mortgage payments drop off, some kids' expenses drop off, etc.). Add a 20-25% buffer to account for taxes.
        
        2. **Run multiple scenarios:** Vary retirement ages, spending levels, growth rates (test 5%, 6%, 7%, 8% returns).
        
        3. **Be conservative:** Better to over-save than under-save. Plan for the 10th percentile outcome, not the median.
        
        4. **Update regularly:** Revisit projections as life changes! Update annually or after major life events.
        
        5. **Use Monte Carlo:** Pay attention to probability distributions, not just the median outcome.
        
        6. **Sanity check:** Do outputs align with common sense and industry benchmarks (4% withdrawal rule, etc.)?

        ---
        
        ### Privacy & Data Security
        
        🔒 **All calculations run locally in your browser.** Your financial data never leaves your computer. 
        No sign-ups, no tracking, no data collection.

        ---
        
        ### ⚠️ DISCLAIMER - Not Financial Advice
        
        **This is a hobby project for educational and planning purposes only. Use with caution!**
        
        **This tool is NOT:**
        - A substitute for professional financial advice
        - Tax advice (consult a CPA)
        - Investment advice (consult a fiduciary advisor)  
        - Legal advice (consult an attorney for estate planning)

        **Consider consulting a Certified Financial Planner (CFP) for:**
        - Complex tax situations
        - Significant wealth ($1M+ portfolios)
        - Risk tolerance assessment
        - Detailed retirement income strategies
        - Estate planning needs

        **Use this tool as pre-work** to ask more informed questions when talking with certified financial planners and advisors.
        """)
    
    st.markdown("---")
    
    # File Upload Section
    st.sidebar.header("📁 Account Data")
    
    uploaded_file = st.sidebar.file_uploader(
        "Upload Your Accounts CSV",
        type=['csv'],
        help="Upload your account information using the template format"
    )
    
    # Download template button
    with open("Accounts_Template.csv", "r") as f:
        template_csv = f.read()
    
    st.sidebar.download_button(
        label="📥 Download Template CSV",
        data=template_csv,
        file_name="Accounts_Template.csv",
        mime="text/csv",
        help="Download a template with sample data to fill in"
    )
    
    st.sidebar.success("🔒 **Privacy:** All data stays local in your browser. Nothing is uploaded to any server.")
    
    st.sidebar.markdown("---")
    
    # Load data based on: 1) session state (if updated), 2) uploaded file, or 3) default
    # Check if we have updated data in session state first
    if 'updated_accounts' in st.session_state and 'updated_family' in st.session_state and 'updated_children' in st.session_state:
        base_accounts = st.session_state['updated_accounts']
        family = st.session_state['updated_family']
        children_info = st.session_state['updated_children']
        st.sidebar.info("ℹ️ Using edited account data. Upload a new file to reset.")
    elif uploaded_file is not None:
        try:
            # Clear any previously edited data when a new file is uploaded
            if 'updated_accounts' in st.session_state:
                del st.session_state['updated_accounts']
                del st.session_state['updated_family']
                del st.session_state['updated_children']
            
            base_accounts, family, children_info = load_data_from_uploaded_file(uploaded_file)
            track_event('file_upload', {'num_accounts': len(base_accounts)})
            st.sidebar.success(f"✓ Loaded {len(base_accounts)} accounts from uploaded file")
            st.sidebar.info("💡 **Reminder:** For 401K accounts, include employer contributions in the Annual Contribution column.")
            
            # Validate uploaded data
            validation_df_data = []
            for acc in base_accounts:
                owner_age = None
                for person in family:
                    if person.name == acc.owner:
                        owner_age = person.current_age
                        break
                if owner_age is None:
                    owner_age = 0  # Will trigger validation error
                
                validation_df_data.append({
                    'Owner': acc.owner,
                    'Age': owner_age,
                    'Type': acc.account_type,
                    'Pre-tax': 'Yes' if acc.is_pretax else 'No',
                    'Balance': acc.current_balance,
                    'Annual Contribution': acc.annual_contribution
                })
            
            validation_df = pd.DataFrame(validation_df_data)
            is_valid, errors = validate_account_data(validation_df)
            
            if not is_valid:
                st.sidebar.error("⚠️ Validation issues found in uploaded file:")
                for error in errors:
                    if error.startswith('❌'):
                        st.sidebar.error(error)
                st.sidebar.info("💡 Please review and fix the data in the table below.")
            
        except ValueError as e:
            st.sidebar.error(f"❌ Error loading file: {str(e)}")
            st.sidebar.info("💡 Please check your CSV format matches the template.")
            # Fall back to default
            base_accounts, family = load_initial_data()
            children_info = {}
            for acc in base_accounts:
                if acc.account_type == "529":
                    for person in family:
                        if person.name == acc.owner:
                            children_info[acc.owner] = person.current_age
                            break
        except Exception as e:
            st.sidebar.error(f"❌ Unexpected error: {str(e)}")
            st.sidebar.info("💡 Using default data instead.")
            # Fall back to default
            base_accounts, family = load_initial_data()
            children_info = {}
            for acc in base_accounts:
                if acc.account_type == "529":
                    for person in family:
                        if person.name == acc.owner:
                            children_info[acc.owner] = person.current_age
                            break
    else:
        base_accounts, family = load_initial_data()
        # Extract children info from default data  
        children_info = {}
        for acc in base_accounts:
            if acc.account_type == "529":
                # Extract age from accounts
                for person in family:
                    if person.name == acc.owner:
                        children_info[acc.owner] = person.current_age
                        break
        st.sidebar.info("ℹ️ Using default Accounts_Template.csv. Upload your own file to customize.")
    
    # Display and allow editing of account data
    st.header("📋 Your Account Data")
    
    st.info("**💡 Pro Tip:** This table is fully editable! You can modify values, add new rows, or delete rows directly here without uploading a CSV file. Click 'Update Accounts' when done to apply your changes.")
    
    # Create dataframe from base_accounts for display/editing
    account_data = []
    for acc in base_accounts:
        # Find owner age
        owner_age = None
        for person in family:
            if person.name == acc.owner:
                owner_age = person.current_age
                break
        
        account_data.append({
            'Owner': acc.owner,
            'Age': owner_age if owner_age else 0,
            'Type': acc.account_type,
            'Pre-tax': 'Yes' if acc.is_pretax else 'No',
            'Balance': acc.current_balance,
            'Annual Contribution': acc.annual_contribution
        })
    
    df_accounts = pd.DataFrame(account_data)
    
    # Display editable dataframe
    edited_df = st.data_editor(
        df_accounts,
        num_rows="dynamic",  # Allow adding/deleting rows
        use_container_width=True,
        column_config={
            "Owner": st.column_config.TextColumn("Owner", help="Account owner's name"),
            "Age": st.column_config.NumberColumn("Age", min_value=0, max_value=100, help="Current age"),
            "Type": st.column_config.TextColumn("Type", help="401K, Vanguard, 529, etc."),
            "Pre-tax": st.column_config.SelectboxColumn("Pre-tax", options=["Yes", "No"], help="Is this a pre-tax account?"),
            "Balance": st.column_config.NumberColumn("Balance", format="$%.0f", help="Current account balance"),
            "Annual Contribution": st.column_config.NumberColumn("Annual Contribution", format="$%.0f", help="Annual contribution amount")
        },
        hide_index=True,
        key="account_editor"
    )
    
    # Validate account data
    is_valid, validation_errors = validate_account_data(edited_df)
    
    # Display validation results
    if not is_valid:
        st.error("**⚠️ Data Validation Errors Found:**")
        for error in validation_errors:
            if error.startswith('❌'):
                st.error(error)
    
    # Display warnings (non-blocking)
    warnings = [e for e in validation_errors if e.startswith('⚠️')]
    if warnings:
        with st.expander("⚠️ Validation Warnings (Click to view)"):
            for warning in warnings:
                st.warning(warning)
    
    # Show validation success if all checks pass
    if is_valid and not warnings:
        st.success("✅ All data validation checks passed!")
    elif is_valid and warnings:
        st.success(f"✅ Data validation passed with {len(warnings)} warning(s)")
    
    # Add update button
    col1, col2, col3 = st.columns([1, 1, 2])
    with col1:
        if st.button("🔄 Update Accounts", type="primary", help="Apply changes from the table above", disabled=not is_valid):
            # Reload accounts from edited dataframe
            try:
                base_accounts = []
                family_dict = {}
                children_info = {}
                
                for _, row in edited_df.iterrows():
                    # Parse data
                    owner_name = str(row['Owner']).strip()
                    owner_age = int(row['Age'])
                    account_type = str(row['Type']).strip()
                    is_pretax = str(row['Pre-tax']).strip().lower() in ['yes', 'true', '1']
                    balance = float(row['Balance'])
                    annual_contrib = float(row['Annual Contribution'])
                    
                    # Track owner information
                    if owner_name not in family_dict:
                        family_dict[owner_name] = owner_age
                    
                    # Track children (529 accounts)
                    if account_type == "529":
                        children_info[owner_name] = owner_age
                    
                    # Create account
                    account = Account(
                        owner=owner_name,
                        account_type=account_type,
                        is_pretax=is_pretax,
                        current_balance=balance,
                        annual_contribution=annual_contrib,
                        growth_rate=0.07  # Will be updated by growth_rate slider
                    )
                    base_accounts.append(account)
                
                # Recreate family
                family = [Person(name, age) for name, age in family_dict.items()]
                
                # Save to session state so changes persist across reruns
                st.session_state['updated_accounts'] = base_accounts
                st.session_state['updated_family'] = family
                st.session_state['updated_children'] = children_info
                
                track_event('accounts_update', {'num_accounts': len(base_accounts)})
                st.success("✅ Accounts updated successfully!")
                # Rerun to refresh all calculations
                try:
                    st.rerun()
                except AttributeError:
                    st.experimental_rerun()  # For older Streamlit versions
                
            except Exception as e:
                st.error(f"❌ Error updating accounts: {str(e)}")
    
    with col2:
        # Add reset button if there are edited accounts in session
        if 'updated_accounts' in st.session_state:
            if st.button("🔄 Reset to Original", help="Clear edited data and reload from file/default"):
                del st.session_state['updated_accounts']
                del st.session_state['updated_family']
                del st.session_state['updated_children']
                try:
                    st.rerun()
                except AttributeError:
                    st.experimental_rerun()
    
    with col3:
        st.info(f"**{len(edited_df)} accounts** loaded")
    
    st.markdown("---")
    
    # Identify all adults (non-529 account owners) with their ages
    adults_info = {}  # {name: age}
    for acc in base_accounts:
        if acc.account_type != "529":
            for person in family:
                if person.name == acc.owner and person.name not in adults_info:
                    adults_info[person.name] = person.current_age
                    break
    
    # Identify primary owner (first non-529 account owner) for backward compatibility
    primary_owner = None
    primary_owner_age = None
    if adults_info:
        primary_owner = list(adults_info.keys())[0]
        primary_owner_age = adults_info[primary_owner]
    else:
        st.error("⛔ No adult account owners found. Please ensure your data includes at least one non-529 account.")
        st.stop()
    
    # Sidebar - Scenario Configuration
    st.sidebar.header("🎯 Scenario Configuration")
    
    st.sidebar.subheader("Retirement Planning")
    
    # Create retirement age sliders for each adult
    retirement_ages = {}
    for adult_name, adult_age in sorted(adults_info.items()):
        retirement_ages[adult_name] = st.sidebar.slider(
            f"{adult_name}'s Retirement Age",
            min_value=max(adult_age, 45),
            max_value=70,
            value=min(54, max(adult_age, 45) + 12),  # Default: current age + 12 years or 54
            step=1,
            help=f"Age at which {adult_name} plans to retire",
            key=f"retire_{adult_name}"
        )
    
    # Determine first and last retirement ages
    if retirement_ages:
        first_retirement_age = min(retirement_ages.values())
        last_retirement_age = max(retirement_ages.values())
        retirement_age = first_retirement_age  # For backward compatibility
    else:
        # Fallback if no adults found
        retirement_age = st.sidebar.slider(
            "Retirement Age",
            min_value=45,
            max_value=65,
            value=54,
            step=1,
            help="Age at which you plan to retire"
        )
        first_retirement_age = retirement_age
        last_retirement_age = retirement_age
    
    # Spending coverage during staggered retirement
    if len(retirement_ages) > 1 and first_retirement_age != last_retirement_age:
        st.sidebar.markdown("**⚖️ Staggered Retirement**")
        partial_retirement_coverage = st.sidebar.slider(
            "% of Spending from Investments (after 1st retires)",
            min_value=0,
            max_value=100,
            value=50,
            step=5,
            help="What % of annual spending comes from portfolio vs. working spouse's income until both retire"
        ) / 100
        
        first_retiree = min(retirement_ages, key=retirement_ages.get)
        last_retiree = max(retirement_ages, key=retirement_ages.get)
        
        st.sidebar.info(f"""
            📅 **Timeline:**
            - {first_retiree} retires at {retirement_ages[first_retiree]}
            - Portfolio covers {partial_retirement_coverage*100:.0f}% of spending
            - {last_retiree} retires at {retirement_ages[last_retiree]}
            - Portfolio covers 100% of spending
        """)
    else:
        partial_retirement_coverage = 1.0  # Both retire together, 100% from portfolio
    
    annual_spending = st.sidebar.number_input(
        f"Annual Spending ({CURRENT_YEAR} dollars)",
        min_value=100000,
        max_value=400000,
        value=200000,
        step=10000,
        help="How much you need per year in retirement"
    )
    
    st.sidebar.subheader("Investment Assumptions")
    
    allocation_strategy = st.sidebar.selectbox(
        "Asset Allocation Strategy",
        options=["Fixed", "Aggressive", "Moderate", "Conservative"],
        index=0,
        help="""Fixed: Use slider value for all accounts at all ages.
        Age-based strategies automatically adjust stock/bond mix:
        • Retirement accounts: Use 120/110/100 - age formulas
        • 529 accounts: More aggressive when child is young, conservative near college"""
    )
    
    # Different return inputs based on allocation strategy
    if allocation_strategy == "Fixed":
        growth_rate = st.sidebar.slider(
            "Annual Growth Rate (%)",
            min_value=3.0,
            max_value=12.0,
            value=7.0,
            step=0.5,
            help="Expected real return on investments (applies to all accounts)"
        ) / 100
        stock_return = growth_rate  # For display in glide path info
        bond_return = growth_rate  # Not used in Fixed strategy
    else:
        st.sidebar.markdown("**Expected Real Returns:**")
        stock_return = st.sidebar.slider(
            "Stock Return (%)",
            min_value=4.0,
            max_value=12.0,
            value=7.0,
            step=0.5,
            help="Historical real stock returns ~7-10%. Real = after inflation."
        ) / 100
        
        bond_return = st.sidebar.slider(
            "Bond Return (%)",
            min_value=1.0,
            max_value=6.0,
            value=2.5,
            step=0.25,
            help="Historical real bond returns ~2-3%. Real = after inflation."
        ) / 100
        
        # Use stock return as the base growth rate for age-based calculations
        growth_rate = stock_return
        
        # Show blended return for current age
        if adults_info:
            first_adult = list(adults_info.keys())[0]
            current_owner_age = adults_info[first_adult]
            # Create temporary portfolio to calculate stock percentage
            temp_portfolio = Portfolio(base_accounts, family)
            sample_stock_pct = temp_portfolio.get_stock_percentage(allocation_strategy, "retirement", current_owner_age)
            if sample_stock_pct is not None:
                blended = (sample_stock_pct/100) * stock_return + (1 - sample_stock_pct/100) * bond_return
                st.sidebar.info(f"""
                    📊 **Your Current Portfolio (Age {current_owner_age}):**
                    - {sample_stock_pct:.0f}% Stocks / {100-sample_stock_pct:.0f}% Bonds
                    - Blended return: {blended*100:.2f}% real
                """)
    
    inflation_rate = st.sidebar.slider(
        "Inflation Rate (%)",
        min_value=1.0,
        max_value=5.0,
        value=3.0,
        step=0.25,
        help="Expected annual inflation"
    ) / 100
    
    st.sidebar.subheader("529 College Contributions")
    
    # Display 529 accounts and allow contribution adjustments
    child_529_contribs = {}
    child_529_targets = {}
    
    for acc in base_accounts:
        if acc.account_type == "529":
            child_529_contribs[acc.owner] = st.sidebar.number_input(
                f"{acc.owner} - Annual 529 Contribution",
                min_value=0,
                max_value=50000,
                value=int(acc.annual_contribution),
                step=1000,
                key=f"contrib_{acc.owner}"
            )
    
    st.sidebar.markdown("**🎓 College Cost Targets (Per Child)**")
    st.sidebar.info(f"""
        **Typical 4-Year College Costs ({CURRENT_YEAR} dollars):**
        - 🏫 In-State Public: ~$100K total
        - 🌎 Out-of-State Public: ~$200K total  
        - 🎓 Private University: ~$360K total
        
        Enter your target coverage amount (e.g., 80% of expected cost).
        The tool will adjust for inflation to college start year.
    """)
    
    for acc in base_accounts:
        if acc.account_type == "529":
            # Calculate college start year (assume age 18)
            child_age = children_info.get(acc.owner, 10)
            years_until_college = 18 - child_age
            college_start_year = CURRENT_YEAR + years_until_college
            
            child_529_targets[acc.owner] = st.sidebar.number_input(
                f"{acc.owner} - Target Amount ($)",
                min_value=0,
                max_value=500000,
                value=72000,  # Default: 80% of $90K/year * 4 years = $288K, but let's use a more conservative default
                step=10000,
                help=f"Target coverage for {acc.owner} (starts college ~{college_start_year})",
                key=f"target_{acc.owner}"
            )
    
    st.sidebar.subheader("🏠 House Mortgage")
    enable_mortgage = st.sidebar.checkbox(
        "Include Mortgage in Plan",
        value=False,
        help="Model mortgage payments and redirect to savings after payoff"
    )
    
    if enable_mortgage:
        monthly_emi = st.sidebar.number_input(
            "Monthly EMI (Principal + Interest)",
            min_value=0,
            max_value=10000,
            value=3000,
            step=100,
            help="Monthly payment excluding property tax and insurance"
        )
        
        mortgage_term_remaining = st.sidebar.number_input(
            "Term Remaining (years)",
            min_value=0,
            max_value=30,
            value=15,
            step=1,
            help="Number of years until mortgage is paid off"
        )
    else:
        monthly_emi = 0
        mortgage_term_remaining = 0
    
    st.sidebar.subheader("💰 Fund Redirection Strategy")
    st.sidebar.markdown("**Where to redirect freed-up funds?**")
    st.sidebar.info("""
        When 529 targets are met or mortgage is paid off, 
        those funds can be redirected to grow your retirement savings.
    """)
    
    redirect_to_pretax = st.sidebar.radio(
        "Redirect to:",
        options=["Post-Tax Accounts", "Pre-Tax Accounts (401k/IRA)"],
        index=0,
        help="Choose whether redirected 529 and mortgage payments go to taxable brokerage or tax-deferred retirement accounts"
    )
    
    # Convert to boolean for processing
    redirect_to_pretax = (redirect_to_pretax == "Pre-Tax Accounts (401k/IRA)")
    
    st.sidebar.subheader("Advanced Settings")
    
    contribution_growth_rate = st.sidebar.slider(
        "Annual Contribution Growth Rate (%)",
        min_value=0.0,
        max_value=5.0,
        value=2.0,
        step=0.25,
        help="Annual increase in contributions due to salary raises, 401k limit increases, etc."
    ) / 100
    
    contribution_years = st.sidebar.number_input(
        "Years Until First Retirement",
        min_value=0,
        max_value=30,
        value=max(0, first_retirement_age - primary_owner_age) if primary_owner_age else 12,
        help="Years until first person retires (when portfolio withdrawals begin). Individual owners continue contributing until their own retirement age."
    )
    
    projection_years = st.sidebar.slider(
        "Projection Timeline (years)",
        min_value=20,
        max_value=60,
        value=50,
        step=5
    )
    
    st.sidebar.subheader("Monte Carlo Analysis")
    
    enable_monte_carlo = st.sidebar.checkbox(
        "Enable Monte Carlo Simulation",
        value=False,
        help="Run thousands of scenarios with varying returns to show probability of success"
    )
    
    if enable_monte_carlo:
        st.sidebar.info("💡 After adjusting Monte Carlo settings, click 'Run Retirement Scenario' to see updated results.")
        
        num_simulations = st.sidebar.select_slider(
            "Number of Simulations",
            options=[100, 500, 1000, 2000, 5000],
            value=1000,
            help="More simulations = more accurate but slower"
        )
        
        st.sidebar.markdown("**Market Volatility (Std Dev):**")
        stock_volatility = st.sidebar.slider(
            "Stock Volatility (%)",
            min_value=10.0,
            max_value=30.0,
            value=18.0,
            step=1.0,
            help="Historical stock market volatility ~18%"
        ) / 100
        
        bond_volatility = st.sidebar.slider(
            "Bond Volatility (%)",
            min_value=2.0,
            max_value=10.0,
            value=5.0,
            step=0.5,
            help="Historical bond volatility ~5%"
        ) / 100
        
        # Calculate blended volatility for current allocation
        if allocation_strategy != "Fixed" and adults_info:
            first_adult = list(adults_info.keys())[0]
            current_owner_age = adults_info[first_adult]
            # Create temporary portfolio to calculate stock percentage
            temp_portfolio = Portfolio(base_accounts, family)
            sample_stock_pct = temp_portfolio.get_stock_percentage(allocation_strategy, "retirement", current_owner_age)
            if sample_stock_pct is not None:
                # Blended volatility (simplified, not accounting for correlation)
                blended_vol = (sample_stock_pct/100) * stock_volatility + (1 - sample_stock_pct/100) * bond_volatility
                st.sidebar.info(f"""
                    📊 **Current Blended Volatility:**
                    {blended_vol*100:.1f}% (based on {sample_stock_pct:.0f}/{100-sample_stock_pct:.0f} mix)
                """)
                volatility = blended_vol
            else:
                volatility = stock_volatility
        else:
            # Fixed strategy - use stock volatility
            volatility = stock_volatility
    else:
        num_simulations = 0
        volatility = 0.18
        stock_volatility = 0.18  # Default values for display purposes
        bond_volatility = 0.05
    
    # Create portfolio with custom parameters
    custom_accounts = create_portfolio_with_custom_contributions(
        base_accounts, child_529_contribs
    )
    
    # Update growth rates for all accounts
    for acc in custom_accounts:
        acc.growth_rate = growth_rate
    
    portfolio = Portfolio(custom_accounts, family)
    
    # Display current portfolio status
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Total Portfolio", f"${portfolio.total_balance():,.0f}")
    with col2:
        st.metric("Post-Tax Accounts", f"${portfolio.posttax_balance():,.0f}")
    with col3:
        st.metric("Pre-Tax (401k)", f"${portfolio.pretax_balance():,.0f}")
    with col4:
        st.metric("529 Education", f"${portfolio.education_balance():,.0f}")
    
    st.markdown("---")
    
    # 529 Analysis Section
    st.header("🎓 529 College Savings Analysis")
    
    redirect_type = "pre-tax retirement accounts (401k/IRA)" if redirect_to_pretax else "post-tax brokerage accounts"
    
    # Explanatory info box
    st.info(f"""
        **📊 Methodology Note:**  
        - **College costs** are projected in **nominal (future) dollars** with {inflation_rate*100:.1f}% annual inflation
        - **529 growth rates** used are **nominal** ({(growth_rate + inflation_rate)*100:.1f}% = {growth_rate*100:.1f}% real return + {inflation_rate*100:.1f}% inflation)
        - **Target amounts** are based on your specified goals (set in sidebar)
        - College start years calculated assuming children attend at age 18
        
        **💰 Contribution Redirection:**  
        Once 529 contributions stop (when target is reached), those funds are automatically redirected to **{redirect_type}** 
        to continue building retirement savings. This optimizes overall portfolio growth.
        
        This ensures apples-to-apples comparison between inflated college costs and investment growth.
    """)
    
    college_calc = CollegeCalculator()
    status_data = analyze_529_status(
        custom_accounts, college_calc, inflation_rate, children_info, child_529_targets,
        enable_monte_carlo=enable_monte_carlo,
        num_simulations=num_simulations if enable_monte_carlo else 0,
        growth_rate=growth_rate,
        volatility=volatility
    )
    
    col1, col2 = st.columns(2)
    
    for i, status in enumerate(status_data):
        with col1 if i % 2 == 0 else col2:
            if status['status'] == 'success':
                box_class = 'success-box'
                icon = '✅'
            elif status['status'] == 'warning':
                box_class = 'warning-box'
                icon = '⚠️'
            else:
                box_class = 'danger-box'
                icon = '❌'
            
            st.markdown(f"""
                <div class='{box_class}'>
                    <h3>{icon} {status['child']}'s 529</h3>
                    <p><strong>Current Balance:</strong> ${status['current_balance']:,.0f}</p>
                    <p><strong>Annual Contribution:</strong> ${status['annual_contribution']:,.0f}</p>
                    <p><strong>College Target:</strong> ${status['target']:,.0f}</p>
                    <p><strong>Projected Value (deterministic):</strong> ${status['projected_value']:,.0f}</p>
                    <p><strong>Coverage:</strong> {status['coverage_pct']:.1f}%</p>
                    <p><strong>Recommendation:</strong> {status['message']}</p>
                </div>
            """, unsafe_allow_html=True)
            
            # Show Monte Carlo results if available
            if status['monte_carlo'] is not None:
                mc = status['monte_carlo']
                st.write(f"**🎲 Monte Carlo Analysis ({mc['total_simulations']:,} simulations):**")
                st.write(f"- **Success Rate:** {mc['success_rate']*100:.1f}% ({mc['success_count']:,} of {mc['total_simulations']:,} scenarios meet target)")
                st.write(f"- **Median Outcome:** ${mc['percentiles']['50th']:,.0f}")
                st.write(f"- **10th Percentile (worst):** ${mc['percentiles']['10th']:,.0f}")
                st.write(f"- **90th Percentile (best):** ${mc['percentiles']['90th']:,.0f}")
                
                if mc['success_rate'] < 0.80:
                    st.warning(f"⚠️ Only {mc['success_rate']*100:.0f}% probability of reaching target. Consider increasing contributions.")
                elif mc['success_rate'] >= 0.95:
                    st.success(f"✅ {mc['success_rate']*100:.0f}% probability of success - very strong position!")
    
    st.markdown("---")
    
    # Mortgage Information Section
    if enable_mortgage and monthly_emi > 0:
        st.header("🏠 House Mortgage Plan")
        
        annual_mortgage = monthly_emi * 12
        payoff_year = CURRENT_YEAR + mortgage_term_remaining
        total_paid = annual_mortgage * mortgage_term_remaining
        
        redirect_type = "pre-tax retirement accounts (401k/IRA)" if redirect_to_pretax else "post-tax brokerage accounts"
        
        st.info(f"""
            **📊 Mortgage Details:**  
            - **Monthly EMI:** ${monthly_emi:,.0f} (Principal + Interest)
            - **Annual Payment:** ${annual_mortgage:,.0f}
            - **Remaining Term:** {mortgage_term_remaining} years
            - **Payoff Year:** {payoff_year}
            - **Total Remaining Payments:** ${total_paid:,.0f}
            
            **💰 Post-Payoff Savings Boost:**  
            After the mortgage is paid off in {payoff_year}, the ${annual_mortgage:,.0f}/year will be automatically 
            redirected to your **{redirect_type}**, accelerating retirement savings growth!
        """)
        
        st.markdown("---")
    
    # Final validation before running scenario
    # Create a dataframe from current base_accounts to validate
    validation_df_data = []
    for acc in base_accounts:
        # Find owner age from family
        owner_age = None
        for person in family:
            if person.name == acc.owner:
                owner_age = person.current_age
                break
        if owner_age is None:
            raise ValueError(f"Cannot find age for account owner '{acc.owner}'. Please ensure all account owners are properly defined.")
        
        validation_df_data.append({
            'Owner': acc.owner,
            'Age': owner_age,
            'Type': acc.account_type,
            'Pre-tax': 'Yes' if acc.is_pretax else 'No',
            'Balance': acc.current_balance,
            'Annual Contribution': acc.annual_contribution
        })
    
    validation_df = pd.DataFrame(validation_df_data)
    final_validation_ok, final_errors = validate_account_data(validation_df)
    
    # Build dynamic college_info from children data (needed for both simulation and display)
    college_info = {}
    for child_name, child_age in children_info.items():
        years_until_college = 18 - child_age
        college_start_year = CURRENT_YEAR + years_until_college
        # Get user-specified target or use default
        target_amount = child_529_targets.get(child_name, 72000)
        college_info[child_name] = (college_start_year, target_amount / 4)  # Divide by 4 for annual cost
    
    # Run Scenario Button (disabled if validation fails)
    if not final_validation_ok:
        st.error("⛔ **Cannot run scenario:** Please fix the data validation errors shown above in the account table.")
    
    if st.button("🚀 Run Retirement Scenario", type="primary", disabled=not final_validation_ok):
        track_event('scenario_run', {
            'allocation_strategy': allocation_strategy,
            'retirement_age': first_retirement_age,
            'staggered': len(retirement_ages) > 1 and first_retirement_age != last_retirement_age,
            'mortgage_enabled': enable_mortgage
        })
        with st.spinner("Running projection..."):
            # Create scenario name based on retirement configuration
            if len(retirement_ages) > 1 and first_retirement_age != last_retirement_age:
                scenario_name = f"Retire at {first_retirement_age}-{last_retirement_age} (staggered)"
            else:
                scenario_name = f"Retire at {first_retirement_age}"
            
            # Create scenario
            scenario = Scenario(
                name=scenario_name,
                retirement_age=first_retirement_age,
                annual_spending=annual_spending,
                growth_rate=growth_rate,
                inflation_rate=inflation_rate,
                contribution_years=contribution_years,
                contribution_growth_rate=contribution_growth_rate
            )
            
            # Run deterministic simulation
            mortgage_info = None
            if enable_mortgage and monthly_emi > 0:
                mortgage_info = {
                    'monthly_emi': monthly_emi,
                    'years_remaining': mortgage_term_remaining
                }
            
            # college_info already built earlier, no need to rebuild here
            
            results_df = portfolio.simulate_scenario(
                retirement_age=retirement_age,
                annual_spending=annual_spending,
                inflation_rate=inflation_rate,
                projection_years=projection_years,
                contribution_years=contribution_years,
                contribution_growth_rate=contribution_growth_rate,
                mortgage_info=mortgage_info,
                college_info=college_info,
                owner_current_age=primary_owner_age,
                redirect_to_pretax=redirect_to_pretax,
                retirement_ages=retirement_ages,
                adults_info=adults_info,
                partial_retirement_coverage=partial_retirement_coverage,
                allocation_strategy=allocation_strategy,
                stock_return=growth_rate,
                bond_return=bond_return if allocation_strategy != "Fixed" else growth_rate
            )
            
            success_metrics = portfolio.check_scenario_success(results_df)
            
            # Run Monte Carlo if enabled
            mc_results = None
            if enable_monte_carlo:
                track_event('monte_carlo_run', {'num_simulations': num_simulations})
                # IMPORTANT: Reset portfolio to initial state before Monte Carlo
                # The deterministic simulation above modified the portfolio
                portfolio.reset_accounts()
                
                simulator = MonteCarloSimulator(
                    mean_return=growth_rate + inflation_rate,  # Nominal return
                    std_dev=volatility
                )
                mc_results = simulator.run_retirement_simulation(
                    portfolio=portfolio,
                    scenario=scenario,
                    num_simulations=num_simulations,
                    owner_age=primary_owner_age,
                    college_info=college_info
                )
            
            # Store in session state
            st.session_state['results_df'] = results_df
            st.session_state['success_metrics'] = success_metrics
            st.session_state['scenario'] = scenario
            st.session_state['mc_results'] = mc_results
    
    # Display results if available
    if 'results_df' in st.session_state:
        results_df = st.session_state['results_df']
        success_metrics = st.session_state['success_metrics']
        scenario = st.session_state['scenario']
        mc_results = st.session_state.get('mc_results', None)
        
        st.markdown("---")
        st.header("📊 Scenario Results")
        
        # Success indicator
        if success_metrics['success']:
            st.success(f"✅ SUCCESS! This retirement plan is viable.")
        else:
            st.error(f"❌ WARNING: Portfolio may be depleted before end of projection.")
        
        # Key metrics
        col1, col2, col3, col4 = st.columns(4)
        
        retirement_yr_idx = max(0, first_retirement_age - primary_owner_age) if primary_owner_age else 0
        balance_at_retirement = results_df.iloc[retirement_yr_idx]['total_balance'] if retirement_yr_idx < len(results_df) else results_df.iloc[0]['total_balance']
        
        # Display label based on whether retirements are staggered
        if len(retirement_ages) > 1 and first_retirement_age != last_retirement_age:
            retirement_label = f"Balance at First Retirement (age {first_retirement_age})"
        else:
            retirement_label = f"Balance at Retirement (age {first_retirement_age})"
        
        with col1:
            st.metric(
                retirement_label,
                f"${balance_at_retirement:,.0f}",
                delta=f"${balance_at_retirement - portfolio.total_balance():,.0f}"
            )
        
        with col2:
            age_70_data = results_df[results_df['owner_age'] == 70]
            if len(age_70_data) > 0:
                balance_70 = age_70_data.iloc[0]['total_balance']
                st.metric("Balance at Age 70", f"${balance_70:,.0f}")
            else:
                st.metric("Balance at Age 70", "N/A")
        
        with col3:
            st.metric(
                "Final Balance",
                f"${success_metrics['final_balance']:,.0f}"
            )
        
        with col4:
            st.metric(
                "Minimum Balance",
                f"${success_metrics['min_balance']:,.0f}"
            )
        
        # Monte Carlo Results Section
        if mc_results is not None:
            st.markdown("---")
            st.subheader(f"🎲 Monte Carlo Analysis ({mc_results['total_simulations']:,} Simulations)")
            
            # Success rate indicator
            success_rate = mc_results['success_rate']
            if success_rate >= 0.95:
                st.success(f"**✅ {success_rate*100:.1f}% Success Rate** - Excellent probability of success!")
            elif success_rate >= 0.85:
                st.info(f"**✓ {success_rate*100:.1f}% Success Rate** - Good probability of success")
            elif success_rate >= 0.75:
                st.warning(f"**⚠️ {success_rate*100:.1f}% Success Rate** - Moderate risk of portfolio depletion")
            else:
                st.error(f"**❌ {success_rate*100:.1f}% Success Rate** - High risk of failure")
            
            # Percentile outcomes
            st.write("**Portfolio Value Percentiles:**")
            
            # Create a clean table for Monte Carlo results
            mc_summary = pd.DataFrame({
                'Milestone': ['At Retirement (deterministic)', 'Age 70', 'Age 80', 'Final Balance'],
                '10th Percentile (Worst Case)': [
                    f"${balance_at_retirement:,.0f}",
                    f"${mc_results['age_70_percentiles']['10th']:,.0f}",
                    f"${mc_results['age_80_percentiles']['10th']:,.0f}",
                    f"${mc_results['final_balance_percentiles']['10th']:,.0f}"
                ],
                '50th Percentile (Median)': [
                    f"${balance_at_retirement:,.0f}",
                    f"${mc_results['age_70_percentiles']['50th']:,.0f}",
                    f"${mc_results['age_80_percentiles']['50th']:,.0f}",
                    f"${mc_results['final_balance_percentiles']['50th']:,.0f}"
                ],
                '90th Percentile (Best Case)': [
                    f"${balance_at_retirement:,.0f}",
                    f"${mc_results['age_70_percentiles']['90th']:,.0f}",
                    f"${mc_results['age_80_percentiles']['90th']:,.0f}",
                    f"${mc_results['final_balance_percentiles']['90th']:,.0f}"
                ]
            })
            
            # Center the table with 75% width
            col1, col2, col3 = st.columns([0.125, 0.75, 0.125])
            with col2:
                st.dataframe(mc_summary, use_container_width=True, hide_index=True)
            
            st.info(f"""
                **💡 Understanding Large Numbers:**  
                These are **nominal (future) dollars** with {projection_years} years of compounding at {(growth_rate + inflation_rate)*100:.1f}% nominal return.
                Even modest portfolios grow dramatically over decades. At 10% annual growth, money doubles every 7 years!
                
                **In today's ({CURRENT_YEAR}) dollars:**  
                - Age 70 median: ${mc_results['age_70_percentiles']['50th'] / (1.03 ** (70-42)):,.0f} (equivalent purchasing power)
                - Final median: ${mc_results['final_balance_percentiles']['50th'] / (1.03 ** projection_years):,.0f} (equivalent purchasing power)
            """)
            
            st.write(f"**Key Insights:**")
            st.write(f"- **Worst case (10th percentile):** ${mc_results['final_balance_percentiles']['10th']:,.0f} final balance")
            st.write(f"- **Median outcome (50th percentile):** ${mc_results['final_balance_percentiles']['50th']:,.0f} final balance")
            st.write(f"- **Best case (90th percentile):** ${mc_results['final_balance_percentiles']['90th']:,.0f} final balance")
            
            if mc_results['failure_years']:
                st.write(f"- **Failures occurred:** {len(mc_results['failure_years'])} out of {mc_results['total_simulations']} simulations")
                st.write(f"- **Most common failure year:** {mc_results['most_common_failure']}")
            else:
                st.write(f"- **No failures** in any of the {mc_results['total_simulations']:,} simulations!")
        
        # Portfolio projection chart
        st.subheader("Portfolio Value Over Time")
        fig = plot_portfolio_projection(results_df, scenario.name, children_info, primary_owner_age)
        # Center the chart with 75% width
        col1, col2, col3 = st.columns([0.125, 0.75, 0.125])
        with col2:
            st.plotly_chart(fig, use_container_width=True)
        
        # Asset Allocation Glide Path Chart
        if allocation_strategy != "Fixed":
            st.subheader("Asset Allocation Strategy Over Time")
            
            # Generate allocation history
            allocation_df = portfolio.generate_allocation_history(
                allocation_strategy=allocation_strategy,
                projection_years=projection_years,
                owner_current_age=primary_owner_age,
                college_info=college_info,
                adults_info=adults_info
            )
            
            if allocation_df is not None:
                allocation_fig = plot_allocation_glide_path(allocation_df, children_info, primary_owner_age)
                if allocation_fig:
                    # Center the chart with 75% width
                    col1, col2, col3 = st.columns([0.125, 0.75, 0.125])
                    with col2:
                        st.plotly_chart(allocation_fig, use_container_width=True)
                    
                    # Add explanation
                    info_text = f"""
                        **📊 Understanding Your Glide Path ({allocation_strategy} Strategy):**
                        
                        Your portfolio automatically adjusts the stock/bond mix as you age:
                        - **Younger years:** Higher stock allocation for growth potential
                        - **Approaching retirement:** Gradually shift to bonds for stability
                        - **During retirement:** Allocation locks at your retirement age
                        
                        **Strategy Details:**
                        - **Retirement Accounts:** {"120 - age" if allocation_strategy == "Aggressive" else "110 - age" if allocation_strategy == "Moderate" else "100 - age"} formula for stock %
                        - **529 Accounts:** More aggressive glide path based on years until college
                        - **College Years:** Allocation freezes when child reaches 18
                        
                        **Return Assumptions:**
                        - **Stocks:** {stock_return*100:.1f}% real return
                        - **Bonds:** {bond_return*100:.1f}% real return
                        - **Blended:** Weighted average based on your age-based allocation
                    """
                    
                    # Add volatility info only if Monte Carlo is enabled
                    if enable_monte_carlo:
                        info_text += f"""
                        
                        **Volatility Assumptions (for Monte Carlo):**
                        - **Stocks:** {stock_volatility*100:.0f}% standard deviation
                        - **Bonds:** {bond_volatility*100:.0f}% standard deviation
                        - **Blended:** {volatility*100:.1f}% (varies with your age-based mix)
                        """
                    
                    info_text += """
                        
                        **Why this matters:**
                        - Higher stocks = higher expected returns + higher volatility
                        - Higher bonds = lower returns + more stability
                        - The glide path balances growth needs with risk tolerance by age
                    """
                    
                    st.info(info_text)
        
        # Detailed yearly breakdown
        st.subheader("Detailed Year-by-Year Projection")
        
        # Build withdrawal strategy message
        withdrawal_info = f"""
            **💡 Withdrawal Strategy (Waterfall Approach):**  
            - **Before age 59.5:** All withdrawals come from **post-tax accounts** (Vanguard) to avoid early withdrawal penalties
            - **After age 59.5:** Continue draining post-tax accounts first, then switch to **pre-tax accounts** (401k) once depleted
        """
        
        # Add staggered retirement info if applicable
        if len(retirement_ages) > 1 and first_retirement_age != last_retirement_age:
            first_retiree = min(retirement_ages, key=retirement_ages.get)
            last_retiree = max(retirement_ages, key=retirement_ages.get)
            withdrawal_info += f"""
            
            **⚖️ Staggered Retirement:**
            - **{first_retiree} retires at {retirement_ages[first_retiree]}:** Portfolio covers {partial_retirement_coverage*100:.0f}% of spending
            - **{last_retiree} retires at {retirement_ages[last_retiree]}:** Portfolio covers 100% of spending
            - Working spouse's income covers the remaining {(1-partial_retirement_coverage)*100:.0f}% during transition period
            """
        
        withdrawal_info += f"""
            
            **What you'll see in the table below:**
            - Post-tax balance decreases as withdrawals are taken for living expenses
            - Pre-tax accounts continue growing untouched until post-tax is depleted (or age 59.5, whichever comes later)
            - This tax-smart strategy minimizes penalties and maximizes tax-deferred growth
            
            **📈 Dollar Basis:**  
            - All balances and spending shown in **nominal (future) dollars**
            - Investment returns use {(growth_rate + inflation_rate)*100:.1f}% nominal rate ({growth_rate*100:.1f}% real + {inflation_rate*100:.1f}% inflation)
            - This keeps projections consistent: inflated spending vs. inflated account values
            
            📄 See `Withdrawal_Strategy_v1.0.txt` for complete details.
        """
        
        st.info(withdrawal_info)
        
        # Filter to show key years
        display_columns = ['year', 'owner_age', 'total_balance', 
                          'posttax_balance', 'pretax_balance', 
                          'education_balance']
        
        # Add optional columns if they exist
        if 'mortgage_payment' in results_df.columns:
            display_columns.append('mortgage_payment')
        if 'redirected_mortgage' in results_df.columns:
            display_columns.append('redirected_mortgage')
        if 'spending' in results_df.columns:
            display_columns.append('spending')
        
        display_df = results_df[display_columns].copy()
        
        # Format for display
        for col in ['total_balance', 'posttax_balance', 'pretax_balance', 'education_balance',
                   'mortgage_payment', 'redirected_mortgage', 'spending']:
            if col in display_df.columns:
                display_df[col] = display_df[col].apply(lambda x: f"${x:,.0f}" if pd.notna(x) and x > 0 else "-")
        
        display_df['year'] = display_df['year'].astype(int)
        display_df['owner_age'] = display_df['owner_age'].astype(int)
        
        # Show first 30 years
        # Center the table with 75% width
        col1, col2, col3 = st.columns([0.125, 0.75, 0.125])
        with col2:
            st.dataframe(display_df.head(30), use_container_width=True, height=400)
        
        # Download button
        csv = results_df.to_csv(index=False)
        st.download_button(
            label="📥 Download Full Projection (CSV)",
            data=csv,
            file_name=f"projection_{scenario.name.replace(' ', '_')}.csv",
            mime="text/csv"
        )
    
    # Footer
    st.markdown("---")
    st.markdown("""
        <div style='text-align: center; color: #666; padding: 20px;'>
            <p>Financial Planning Dashboard v1.0 | Built with Streamlit</p>
            <p><em>Disclaimer: This tool is for planning purposes only. Consult a financial advisor for personalized advice.</em></p>
        </div>
    """, unsafe_allow_html=True)


if __name__ == "__main__":
    main()
