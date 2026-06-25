# 💰 Family Financial Planning Dashboard

A comprehensive financial planning tool for retirement, college savings (529 plans), and mortgage management with Monte Carlo simulations and age-based asset allocation strategies.

## 🌟 Features

- **Multi-Account Management**: Track 401K, IRA, Vanguard, and 529 accounts
- **Age-Based Asset Allocation**: Automatic glide paths (Aggressive/Moderate/Conservative)
- **529 College Planning**: Optimize contributions and target coverage
- **Mortgage Integration**: Model payoff and automatic fund redirection
- **Staggered Retirement**: Support for spouses retiring at different ages
- **Monte Carlo Simulations**: Risk analysis with 100-5000 scenarios
- **Data Validation**: 12-point validation system for data integrity
- **Interactive Charts**: Plotly visualizations for portfolio projections
- **Privacy-First**: All calculations run locally, no data stored

## 🚀 Quick Start

### Local Development

1. **Clone the repository:**
```bash
git clone https://github.com/YOUR_USERNAME/financial-planner-dashboard.git
cd financial-planner-dashboard
```

2. **Install dependencies:**
```bash
pip install -r requirements.txt
```

3. **Run the app:**
```bash
streamlit run dashboard.py
```

4. **Open in browser:**
Navigate to `http://localhost:8501`

### Using the Dashboard

1. **Download Template** - Get `Accounts_Template.csv` from the sidebar
2. **Fill Your Data** - Enter your account balances and contributions
3. **Upload CSV** - Load your personalized financial data
4. **Configure Scenarios** - Set retirement age, spending, growth rates
5. **Run Projections** - Click "Run Retirement Scenario" button

## 📊 Usage Analytics

The dashboard includes session-based analytics tracking:

- Page views
- Scenarios run
- Monte Carlo simulations executed
- Files uploaded
- Accounts updated
- Features used

**Note**: Analytics are session-only and don't persist on Streamlit Community Cloud.

For production analytics, integrate with:
- **Google Analytics 4** (recommended for public apps)
- **Mixpanel** or **Amplitude** (for detailed user behavior)
- **Custom database** (PostgreSQL, Firebase, etc.)

See `DEPLOYMENT.md` for integration details.

## 🌐 Deploying to Streamlit Cloud

Full deployment instructions in `DEPLOYMENT.md`.

**Quick version:**

1. Push to GitHub
2. Go to [share.streamlit.io](https://share.streamlit.io)
3. Click "New app" → Select your repo
4. Set main file to `dashboard.py`
5. Deploy!

Your app will be live at: `https://YOUR-APP-NAME.streamlit.app`

## 📁 Project Structure

```
financial-planner-dashboard/
├── dashboard.py              # Main Streamlit application
├── financial_planner.py      # Core financial planning logic
├── monte_carlo.py            # Monte Carlo simulation engine
├── load_data.py              # CSV loading and data parsing
├── analytics.py              # Usage tracking module
├── requirements.txt          # Python dependencies
├── Accounts_Template.csv     # Template for user data
├── .streamlit/
│   └── config.toml          # Streamlit configuration
├── .gitignore               # Excluded files
├── README.md                # This file
└── DEPLOYMENT.md            # Detailed deployment guide
```

## 🔒 Privacy & Security

- ✅ **Client-side only** - All calculations in browser
- ✅ **No data storage** - Financial data never saved to servers
- ✅ **HTTPS by default** - Streamlit Cloud uses secure connections
- ✅ **No tracking** - Session analytics only (optional)
- ✅ **Open source** - Review all code

## 📋 Requirements

- Python 3.9+
- streamlit >= 1.28.0
- pandas >= 2.0.0
- numpy >= 1.24.0
- plotly >= 5.14.0

## 🤝 Contributing

Contributions welcome! Please:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit changes (`git commit -m 'Add AmazingFeature'`)
4. Push to branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## ⚠️ Disclaimer

**This tool is for educational and planning purposes only.**

- Not a substitute for professional financial advice
- Not tax, investment, or legal advice
- Historical returns don't guarantee future performance
- Always consult certified professionals (CFP, CPA, attorney)

Use this tool as pre-work for informed discussions with financial advisors.

## 📄 License

MIT License - See LICENSE file for details

## 📧 Contact

- **GitHub Issues**: [Report bugs or request features](https://github.com/YOUR_USERNAME/financial-planner-dashboard/issues)
- **Discussions**: [Ask questions](https://github.com/YOUR_USERNAME/financial-planner-dashboard/discussions)

## 🙏 Acknowledgments

Built with:
- [Streamlit](https://streamlit.io) - Web framework
- [Plotly](https://plotly.com) - Interactive charts
- [Pandas](https://pandas.pydata.org) - Data manipulation
- [NumPy](https://numpy.org) - Numerical computing

---

**Made with ❤️ for better financial planning**
