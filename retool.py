import streamlit as st
from supabase import create_client
import pandas as pd
import numpy as np
from dotenv import load_dotenv
from datetime import datetime, timezone
# Import metric components
from metrics.avg_streams_per_user import display_avg_streams_per_user
from metrics.highlight_feedback import display_highlight_like_ratio, display_highlight_share_ratio
from metrics.new_user_signups import display_new_user_signups
from metrics.weekly_intervals import display_weekly_streams, display_weekly_active_users

# Load environment variables
load_dotenv()


def display_summary_metrics(streams: pd.DataFrame, users: pd.DataFrame) -> None:
    """
    Display the summary metrics section with improved layout and calculations
    """
    st.header('Summary Metrics', divider='blue')
    
    # Create three rows of metrics for better spacing
    row1_cols = st.columns([1, 1, 1])  # Top row for most important metrics
    row2_cols = st.columns([1, 1, 1])  # Second row for other metrics
    
    # 1. MRR (Most important)
    with row1_cols[0]:
        st.metric(
            "Monthly Recurring Revenue",
            "$103",
            help="Current monthly recurring revenue"
        )

    # 2. Current Paid Users
    with row1_cols[1]:
        st.metric(
            "Current Paid Users",
            "3",
            help="Number of paid users in the current month"
        )

    # 3. Highlight Agreement Rate
    with row1_cols[2]:
        st.metric(
            "Highlight Agreement Rate",
            "8.6%",
            help="Percentage of highlights that match human agreement"
        )

    # 4. Average Streams per Week per User
    with row2_cols[0]:
        if not streams.empty:
            today = pd.Timestamp.now(tz='UTC')
            last_week_start = today - pd.Timedelta(days=today.weekday() + 7)
            last_week_end = last_week_start + pd.Timedelta(days=7)
            
            last_week_data = streams[
                (streams['created_at'] >= last_week_start) & 
                (streams['created_at'] < last_week_end)
            ]
            
            if not last_week_data.empty:
                user_streams = last_week_data.groupby('user_id').size()
                avg_streams = user_streams.mean()
                
                st.metric(
                    "Last Week's Average Streams/User",
                    f"{avg_streams:.1f}",
                    help="Average number of streams per user for the last complete week"
                )
            else:
                st.metric("Last Week's Average Streams/User", "0.0")
        else:
            st.metric("Last Week's Average Streams/User", "No data")

    # 5. Monthly Active Users (MAU)
    with row2_cols[1]:
        if not streams.empty:
            current_date = pd.Timestamp.now(tz='UTC')
            thirty_days_ago = current_date - pd.Timedelta(days=30)
            active_users = len(streams[streams['created_at'] >= thirty_days_ago]['user_id'].unique())
            
            st.metric(
                "Monthly Active Users",
                f"{active_users:,}",
                help="Unique users who streamed in the last 30 days"
            )
        else:
            st.metric("Monthly Active Users", "No data")

    # 6. Premium Users (kept as requested)
    with row2_cols[2]:
        if not users.empty:
            premium_users = users[users['is_paying'] == True].shape[0]
            total_users = len(users)
            premium_percentage = (premium_users / total_users * 100) if total_users > 0 else 0
            
            st.metric(
                "Premium Users",
                f"{premium_users:,}",
                f"{premium_percentage:.1f}% of total",
                help="Number of users with premium subscriptions"
            )
        else:
            st.metric("Premium Users", "No data")

def create_analytics_dashboard():
    """
    Create and display the main analytics dashboard with all metrics and visualizations
    """
    try:
        # Initialize Supabase client
        supabase_url = st.secrets["env"]["SUPABASE_URL"]
        supabase_key = st.secrets["env"]["SUPABASE_KEY"]
        supabase = create_client(supabase_url, supabase_key)

        # List of developer user IDs to exclude
        developer_ids = st.secrets["env"]["DEVELOPER_IDS"].split(',')

        # Set page config
        st.set_page_config(
            page_title="Platform Analytics",
            page_icon="📊",
            layout="wide",
            initial_sidebar_state="expanded"
        )

        # Fetch data from all tables
        with st.spinner('Fetching data...'):
            streams = pd.DataFrame(supabase.from_('Streams').select('*').execute().data)
            highlights = pd.DataFrame(supabase.from_('Highlights').select('*').execute().data)
            users = pd.DataFrame(supabase.from_('Users').select('*').execute().data)

            # Filter out developer data
            streams = streams[~streams['user_id'].isin(developer_ids)]
            highlights = highlights[~highlights['user_id'].isin(developer_ids)]
            users = users[~users['user_id'].isin(developer_ids)]

        # Convert timestamps to datetime with UTC
        if not streams.empty:
            streams['created_at'] = pd.to_datetime(streams['created_at'], utc=True)
        if not users.empty:
            users['created_at'] = pd.to_datetime(users['created_at'], utc=True)

        # Main dashboard title with styling
        st.title('📊 Platform Analytics Dashboard')
        st.caption('Data excludes developer activity')

        # Add data freshness indicator
        last_update = pd.Timestamp.now(tz='UTC')
        st.sidebar.info(f"Data last updated: {last_update.strftime('%Y-%m-%d %H:%M:%S')} UTC")

        # Display summary metrics
        display_summary_metrics(streams, users)

        # Create tabs for different metric categories
        tabs = st.tabs(["User Activity", "Growth", "Highlight Feedback"])

        with tabs[0]:
            st.header("User Activity Metrics")
            
            st.subheader("Weekly Metrics")
            display_avg_streams_per_user(streams)
            display_weekly_streams(streams)
            display_weekly_active_users(streams)

        with tabs[1]:
            st.header("Growth Metrics")
            # Display growth metrics
            display_new_user_signups(users)
            
            # Display highlights metrics if available
            if not highlights.empty:
                st.subheader("Highlights Activity")
                # Add your highlights metrics here


        with tabs[2]:
            st.header("Highlight Feedback Metrics")
            display_highlight_like_ratio(highlights)
            display_highlight_share_ratio(highlights)

        # Add footer with data disclaimer
        st.markdown("---")
        st.caption("Note: All metrics are calculated based on UTC timezone")

    except Exception as e:
        st.error(f"An error occurred: {str(e)}")
        st.error("Please check your database connection and try again.")
        # Log the full error for debugging
        st.exception(e)

if __name__ == "__main__":
    create_analytics_dashboard()