"""
Usage Analytics for Financial Planner Dashboard

Simple session-based tracking for understanding how users interact with the app.
For production use, consider integrating with:
- Google Analytics
- Mixpanel  
- Amplitude
- Or your own database backend
"""

import streamlit as st
from datetime import datetime
from typing import Dict, Any


def initialize_analytics():
    """Initialize session state for analytics tracking"""
    if 'analytics' not in st.session_state:
        st.session_state['analytics'] = {
            'session_start': datetime.now(),
            'page_views': 0,
            'scenarios_run': 0,
            'monte_carlo_runs': 0,
            'files_uploaded': 0,
            'accounts_updated': 0,
            'allocation_strategy_used': None,
            'features_used': set()
        }


def track_event(event_name: str, properties: Dict[str, Any] = None):
    """
    Track a user event
    
    Args:
        event_name: Name of the event (e.g., 'scenario_run', 'file_upload')
        properties: Optional dictionary of event properties
    """
    if 'analytics' not in st.session_state:
        initialize_analytics()
    
    analytics = st.session_state['analytics']
    
    # Track specific events
    if event_name == 'page_view':
        analytics['page_views'] += 1
    elif event_name == 'scenario_run':
        analytics['scenarios_run'] += 1
        if properties and 'allocation_strategy' in properties:
            analytics['allocation_strategy_used'] = properties['allocation_strategy']
    elif event_name == 'monte_carlo_run':
        analytics['monte_carlo_runs'] += 1
    elif event_name == 'file_upload':
        analytics['files_uploaded'] += 1
    elif event_name == 'accounts_update':
        analytics['accounts_updated'] += 1
    
    # Track feature usage
    analytics['features_used'].add(event_name)
    
    st.session_state['analytics'] = analytics


def get_session_duration():
    """Get the duration of the current session"""
    if 'analytics' in st.session_state:
        start = st.session_state['analytics']['session_start']
        duration = datetime.now() - start
        return duration.total_seconds()
    return 0


def get_analytics_summary() -> Dict[str, Any]:
    """Get summary of analytics for current session"""
    if 'analytics' not in st.session_state:
        initialize_analytics()
    
    analytics = st.session_state['analytics']
    
    return {
        'session_duration_seconds': get_session_duration(),
        'page_views': analytics['page_views'],
        'scenarios_run': analytics['scenarios_run'],
        'monte_carlo_runs': analytics['monte_carlo_runs'],
        'files_uploaded': analytics['files_uploaded'],
        'accounts_updated': analytics['accounts_updated'],
        'allocation_strategy': analytics.get('allocation_strategy_used'),
        'features_used': list(analytics['features_used'])
    }


def display_analytics_debug():
    """Display analytics debug panel (for development only)"""
    with st.sidebar.expander("📊 Session Analytics (Debug)", expanded=False):
        summary = get_analytics_summary()
        st.json(summary)


# Example integration with external analytics services:
# 
# def send_to_google_analytics(event_name: str, properties: Dict = None):
#     """Send event to Google Analytics via gtag.js"""
#     # Implement GA4 tracking
#     pass
#
# def send_to_mixpanel(event_name: str, properties: Dict = None):
#     """Send event to Mixpanel"""
#     import mixpanel
#     mp = mixpanel.Mixpanel("YOUR_TOKEN")
#     mp.track(st.session_state.get('user_id', 'anonymous'), event_name, properties)
