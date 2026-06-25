# Financial Planner - Account Template Guide

## How to Use the Template

1. **Download the Template**
   - In the dashboard sidebar, click "📥 Download Template CSV"
   - Save `Accounts_Template.csv` to your computer

2. **Fill Out Your Information**
   - Open the template in Excel, Google Sheets, or any text editor
   - Replace the sample data with your actual account information
   - Keep the same comma-separated format

3. **Column Descriptions**

   | Column | Description | Example |
   |--------|-------------|---------|
   | **Owner** | Account owner's name or child's name | "John Doe" or "Child 1" |
   | **Age** | Current age of the owner | 45, 8, etc. |
   | **Type** | Account type | "401K", "Vanguard", "529" |
   | **Pre-tax** | Is this a pre-tax account? | "Yes" or "No" |
   | **Balance** | Current account balance | 100000 |
   | **Annual Contribution** | How much you contribute per year | 20000 |

4. **Account Types**
   - **401K**: Pre-tax retirement account
   - **Vanguard**: Post-tax brokerage account (taxable)
   - **529**: Education savings account (for children)

5. **Important Notes**
   - **Children (529 accounts)**: The app will calculate college start year by assuming they attend at age 18
   - **Multiple accounts per person**: You can have multiple rows for the same owner (e.g., Jack Doe with both Vanguard and 401K)
   - **Comma-separated**: Make sure columns are separated by commas (standard CSV format)
   - **529 targets**: You'll set college savings targets in the app after uploading

6. **Upload Your File**
   - In the dashboard sidebar, click "Upload Your Accounts CSV"
   - Select your filled-out CSV file
   - The app will load your accounts and display a confirmation

## Example Template Structure

```
Owner,Age,Type,Pre-tax,Balance,Annual Contribution
Jack Doe,45,Vanguard,No,100000,25000
Jack Doe,45,401K,Yes,100000,20000
Jane Doe,43,Vanguard,No,100000,20000
Jane Doe,43,401K,Yes,100000,18000
Child 1,8,529,No,100000,5000
Child 2,5,529,No,100000,5000
```

## Setting 529 Targets

After uploading your file, you'll see input fields for each child's 529 target:

**Typical 4-Year College Costs (2026 dollars):**
- 🏫 In-State Public: ~$100K total
- 🌎 Out-of-State Public: ~$200K total  
- 🎓 Private University: ~$360K total

Enter your target coverage amount (e.g., 80% of expected cost = $288K for private).
The tool will automatically adjust for inflation to your child's college start year.

## Need Help?

If you have questions or issues:
1. Check that your CSV is comma-separated (standard CSV format)
2. Verify all required columns are present
3. Make sure "Pre-tax" column only contains "Yes" or "No"
4. Ensure all numeric values are numbers without commas or currency symbols

## Privacy Note

All calculations are performed locally in your browser. Your financial data is never uploaded to any server.
