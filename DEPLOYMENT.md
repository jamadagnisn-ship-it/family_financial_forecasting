# Financial Planner Dashboard - Deployment Guide

## Deploying to Streamlit Community Cloud

### Prerequisites
1. **GitHub Account** - Streamlit Cloud deploys from GitHub repositories
2. **Streamlit Community Cloud Account** - Sign up at [share.streamlit.io](https://share.streamlit.io)

### Step-by-Step Deployment

#### 1. Create a GitHub Repository
```bash
cd "C:\Users\jamadagni.sn\OneDrive - Procter and Gamble\Documents\Savings\FinancialPlanner"
git init
git add .
git commit -m "Initial commit - Financial Planner Dashboard"
```

Create a new repository on GitHub (e.g., `financial-planner-dashboard`) and push:
```bash
git remote add origin https://github.com/YOUR_USERNAME/financial-planner-dashboard.git
git branch -M main
git push -u origin main
```

#### 2. Deploy on Streamlit Cloud
1. Go to [share.streamlit.io](https://share.streamlit.io)
2. Click "New app"
3. Select your GitHub repository
4. Set:
   - **Main file path**: `dashboard.py`
   - **Python version**: 3.9 or higher
5. Click "Deploy!"

Your app will be live at: `https://YOUR_USERNAME-financial-planner-dashboard.streamlit.app`

### Files Required for Deployment

✅ **requirements.txt** - Python dependencies (already created)
✅ **dashboard.py** - Main application file  
✅ **.streamlit/config.toml** - Streamlit configuration (already created)
✅ **.gitignore** - Exclude personal data and cache files (already created)
✅ **Accounts_Template.csv** - Template file for users
✅ **README.md** - This file

### Usage Analytics

The app includes basic session-level analytics tracking:
- Scenarios run
- Monte Carlo simulations
- File uploads
- Feature usage

**Analytics data is session-only** - it doesn't persist across sessions on Streamlit Cloud.

#### For Persistent Analytics
To track usage across all users, integrate with:

**Option 1: Google Analytics 4**
1. Add Google Analytics tracking script to `dashboard.py`
2. Use streamlit-gtag component

**Option 2: Streamlit Analytics Package**
```bash
pip install streamlit-analytics
```

Add to your code:
```python
import streamlit_analytics
with streamlit_analytics.track():
    # Your app code
```

**Option 3: External Database**
- Use Streamlit Secrets for database credentials
- Log events to PostgreSQL, MongoDB, or Firebase

### Privacy Considerations

⚠️ **Important Privacy Notes:**
1. **No Personal Data in Repo** - The `.gitignore` excludes personal CSV files
2. **Client-Side Only** - All calculations run in the user's browser
3. **No Data Storage** - The app doesn't save user financial data
4. **HTTPS by Default** - Streamlit Cloud serves apps over HTTPS

### Resource Limits (Streamlit Community Cloud)
- **Memory**: 1 GB RAM
- **CPU**: Shared
- **Storage**: Ephemeral (resets on restart)
- **Bandwidth**: Fair use policy
- **Always-on**: No (sleeps after inactivity)

### Troubleshooting

**App won't start:**
- Check `requirements.txt` versions
- Verify all imports work
- Check Streamlit Cloud logs

**App is slow:**
- Optimize data processing
- Use `@st.cache_data` for expensive operations
- Reduce Monte Carlo simulation default sizes

**File not found errors:**
- Ensure `Accounts_Template.csv` is in the repo
- Use relative paths, not absolute paths

### Custom Domain (Optional)
Streamlit Cloud apps can use custom domains:
1. Go to app settings
2. Add your custom domain
3. Configure DNS CNAME record

### Updating the App
Simply push to your GitHub repository:
```bash
git add .
git commit -m "Update feature X"
git push
```

Streamlit Cloud will auto-deploy changes within ~60 seconds.

### Support
- [Streamlit Documentation](https://docs.streamlit.io)
- [Streamlit Community Forum](https://discuss.streamlit.io)
- [GitHub Issues](https://github.com/YOUR_USERNAME/financial-planner-dashboard/issues)
