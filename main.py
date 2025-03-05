import streamlit as st
from supabase import create_client
from data import AnalyticsDataLoader
from graph import display_metrics_dashboard
import pandas as pd
import os
import socket

def create_analytics_dashboard():
    """
    Create and display the main analytics dashboard with new architecture
    """
    try:
        # Check if we need to redirect to the custom domain
        hostname = socket.gethostname()
        current_url = st.experimental_get_query_params().get('_url', [''])[0]
        target_domain = "analytics.saved.gg"
        
        # If we're not already on the target domain, redirect
        if not current_url.startswith(f"https://{target_domain}") and hostname != "localhost":
            st.markdown(f"""
                <meta http-equiv="refresh" content="0; url=https://{target_domain}">
                <script>window.location.href = "https://{target_domain}";</script>
                <p>Redirecting to <a href="https://{target_domain}">analytics.saved.gg</a>...</p>
            """, unsafe_allow_html=True)
            return
        # Set page config
        st.set_page_config(
            page_title="Platform Analytics",
            page_icon="📊",
            layout="wide",
            initial_sidebar_state="expanded"
        )

        # Main dashboard title
        st.title('📊 Platform Analytics Dashboard')
        st.caption('Data excludes developer activity')

        # Sidebar controls
        st.sidebar.title("Dashboard Controls")
        
        # Get secrets from either environment variables or st.secrets
        # Railway provides environment variables, while local dev uses Streamlit secrets
        def get_secret(key, default=None):
            """Get a secret from either environment variables or Streamlit secrets"""
            # First try environment variables (Railway)
            value = os.environ.get(key)
            if value is not None:
                return value
                
            # Fall back to Streamlit secrets if available
            try:
                return st.secrets[key]
            except (KeyError, FileNotFoundError):
                return default
        
        # Track the state of the developer IDs for changes
        developer_ids_str = get_secret("DEVELOPER_IDS", "")
        current_developer_ids = [id.strip() for id in developer_ids_str.split(',')] if developer_ids_str else []
        
        if 'previous_developer_ids' not in st.session_state:
            st.session_state.previous_developer_ids = current_developer_ids
        
        # Check if developer IDs have changed
        developer_ids_changed = set(current_developer_ids) != set(st.session_state.previous_developer_ids)
        if developer_ids_changed:
            # Update stored developer IDs
            st.session_state.previous_developer_ids = current_developer_ids
            # Force reload if developer IDs changed
            if 'data_loader' in st.session_state:
                st.session_state.data_loader.developer_ids = current_developer_ids
                force_reload = True
                st.sidebar.warning("Developer IDs changed - data will be reloaded")
            else:
                force_reload = False
        else:
            force_reload = False
        
        # Add refresh buttons to sidebar with clear descriptions
        st.sidebar.subheader("Data Refresh Options")
        
        col1, col2 = st.sidebar.columns(2)
        
        # Initialize refresh flags
        force_reload = False
        do_refresh = False
        
        # Button to fetch only new data
        fetch_new = col1.button("🔄 Fetch New Data")
        if fetch_new:
            do_refresh = True
            force_reload = False
            st.sidebar.success("Fetching only new data...")
        
        # Button to completely refresh all data
        full_refresh = col2.button("♻️ Full Refresh")
        if full_refresh:
            do_refresh = True
            force_reload = True
            st.sidebar.success("Completely refreshing all data...")
            # Clear cached data if it exists
            if 'cached_raw_data' in st.session_state:
                del st.session_state.cached_raw_data

        # Initialize data loader
        if 'data_loader' not in st.session_state:
            data_loader = AnalyticsDataLoader(
                supabase_url=get_secret("SUPABASE_URL"),
                supabase_key=get_secret("SUPABASE_KEY"),
                developer_ids=current_developer_ids
            )
            # Load all metrics once
            with st.spinner('Loading metrics...'):
                data_loader.load_all_metrics(force_reload=False)  # Initial load
            print(f"Data loader metrics after loading: Daily: {len(data_loader.daily_metrics)}, Weekly: {len(data_loader.weekly_metrics)}, Monthly: {len(data_loader.monthly_metrics)}")
            st.session_state.data_loader = data_loader
        else:
            data_loader = st.session_state.data_loader
            # Reload metrics if either refresh button was clicked or developer IDs changed
            if do_refresh or developer_ids_changed:
                with st.spinner('Refreshing metrics...'):
                    data_loader.load_all_metrics(force_reload=force_reload)
                
                # Show what happened in the logs
                if force_reload:
                    print("Performed full data refresh")
                else:
                    print("Fetched new data only")
                
                print(f"Data loader metrics after refresh: Daily: {len(data_loader.daily_metrics)}, Weekly: {len(data_loader.weekly_metrics)}, Monthly: {len(data_loader.monthly_metrics)}")

        # Add data freshness indicator
        last_update = pd.Timestamp.now(tz='UTC')
        st.sidebar.info(f"Data last updated: {last_update.strftime('%Y-%m-%d %H:%M:%S')} UTC")

        # Add time period selector at the top level
        period = st.radio(
            "Select Time Period",
            ["Weekly", "Daily", "Monthly"],
            horizontal=True,
        )

        # Display dashboard with selected period
        display_metrics_dashboard(data_loader, period)

        # Add footer
        st.markdown("---")
        st.caption("Note: All metrics are calculated based on UTC timezone")

    except Exception as e:
        st.error(f"An error occurred: {str(e)}")
        st.error("Please check your database connection and try again.")
        st.exception(e)

if __name__ == "__main__":
    create_analytics_dashboard()