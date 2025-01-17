import streamlit as st
from supabase import create_client
from data import AnalyticsDataLoader
from graph import display_metrics_dashboard
import pandas as pd

def create_analytics_dashboard():
    """
    Create and display the main analytics dashboard with new architecture
    """
    try:
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

        # Initialize data loader
        data_loader = AnalyticsDataLoader(
            supabase_url=st.secrets["SUPABASE_URL"],
            supabase_key=st.secrets["SUPABASE_KEY"],
            developer_ids=[id.strip() for id in st.secrets["DEVELOPER_IDS"].split(',')]
        )

        # Add data freshness indicator
        last_update = pd.Timestamp.now(tz='UTC')
        st.sidebar.info(f"Data last updated: {last_update.strftime('%Y-%m-%d %H:%M:%S')} UTC")

        # Load all metrics
        with st.spinner('Loading metrics...'):
            data_loader.load_all_metrics()

        # Display dashboard
        display_metrics_dashboard(data_loader)

        # Add footer
        st.markdown("---")
        st.caption("Note: All metrics are calculated based on UTC timezone")

    except Exception as e:
        st.error(f"An error occurred: {str(e)}")
        st.error("Please check your database connection and try again.")
        st.exception(e)

if __name__ == "__main__":
    create_analytics_dashboard()