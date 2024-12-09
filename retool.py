import streamlit as st
from supabase import create_client
import pandas as pd
import numpy as np
from dotenv import load_dotenv
from datetime import datetime, timezone

# Import metric components
from metrics.avg_streams_per_user import display_avg_streams_per_user
from metrics.monthly_total_streams import display_monthly_total_streams
from metrics.monthly_active_users import display_monthly_active_users
from metrics.monthly_retention import display_monthly_retention
from metrics.new_user_signups import display_new_user_signups
from metrics.weekly_intervals import display_weekly_streams, display_weekly_active_users

# Load environment variables
load_dotenv()


def display_summary_metrics(streams: pd.DataFrame, users: pd.DataFrame) -> None:
    """
    Display the summary metrics section with improved layout and calculations
    """
    st.header('Summary Metrics', divider='blue')
    
    # Create two rows of metrics for better spacing
    row1_cols = st.columns([1, 1])
    row2_cols = st.columns([1, 1])
    
    # 1. Average Streams per Week per User
    with row1_cols[0]:
        if not streams.empty:
            # Calculate using complete weeks only
            start_date = pd.Timestamp('2024-09-29', tz='UTC')
            df = streams.copy()
            df['week_number'] = ((df['created_at'] - start_date) // pd.Timedelta(weeks=1)) + 1
            df['week_start'] = start_date + (df['week_number'] - 1) * pd.Timedelta(weeks=1)
            
            # Get complete weeks only (exclude current week)
            today = pd.Timestamp.now(tz='UTC')
            complete_weeks_data = df[df['week_start'] < today - pd.Timedelta(days=today.weekday())]
            
            if not complete_weeks_data.empty:
                weekly_streams = complete_weeks_data.groupby(['week_start', 'user_id']).size().reset_index(name='streams')
                avg_streams = weekly_streams.groupby('week_start')['streams'].mean().mean()
                
                st.metric(
                    "Average Weekly Streams/User",
                    f"{avg_streams:.1f}",
                    help="Average number of streams per user per week (excluding current week)"
                )
            else:
                st.metric("Average Weekly Streams/User", "0.0")
        else:
            st.metric("Average Weekly Streams/User", "No data")

    # 2. Monthly Active Users (MAU)
    with row1_cols[1]:
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

    # 3. Total Users
    with row2_cols[0]:
        if not users.empty:
            total_users = len(users)
            # Calculate user growth
            last_month = pd.Timestamp.now(tz='UTC') - pd.Timedelta(days=30)
            prev_total = len(users[users['created_at'] < last_month])
            growth = ((total_users - prev_total) / prev_total * 100) if prev_total > 0 else 0
            
            st.metric(
                "Total Users",
                f"{total_users:,}",
                f"{growth:+.1f}% in 30 days",
                help="Total number of registered users"
            )
        else:
            st.metric("Total Users", "No data")

    # 4. Premium Users
    with row2_cols[1]:
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

        st.caption("📊 Dotted lines and star markers (⭐) indicate projected data for the current period")


        # Create tabs for different metric categories
        tabs = st.tabs(["User Activity", "Retention", "Growth"])

        with tabs[0]:
            st.header("User Activity Metrics")
            
            st.subheader("Monthly Metrics")
            display_monthly_total_streams(streams)
            
            st.subheader("Weekly Metrics")
            display_avg_streams_per_user(streams)
            display_weekly_streams(streams)
            display_weekly_active_users(streams)

        with tabs[1]:
            st.header("Retention Metrics")
            # Display retention metrics
            display_monthly_retention(streams)

        with tabs[2]:
            st.header("Growth Metrics")
            # Display growth metrics
            display_new_user_signups(users)
            
            # Display highlights metrics if available
            if not highlights.empty:
                st.subheader("Highlights Activity")
                # Add your highlights metrics here

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