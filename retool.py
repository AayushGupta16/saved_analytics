import streamlit as st
from supabase import create_client
import pandas as pd
import numpy as np
from dotenv import load_dotenv
from datetime import datetime, timezone
# Import metric components
from metrics.avg_streams_per_user import display_avg_streams_per_user
from metrics.highlight_feedback import display_highlight_like_ratio, display_highlight_share_ratio, get_weekly_metrics, update_summary_share_rate
from metrics.new_user_signups import display_new_user_signups
from metrics.weekly_intervals import display_weekly_streams, display_weekly_active_users

# Load environment variables
load_dotenv()


def display_summary_metrics(streams: pd.DataFrame, users: pd.DataFrame, highlights: pd.DataFrame) -> None:
    """
    Display the summary metrics section with improved layout and calculations
    """
    st.header('Summary Metrics', divider='blue')
    
    # Create two rows of metrics with 4 columns each
    row1_cols = st.columns(4)  # Top row
    row2_cols = st.columns(4)  # Second row

    # Ensure timestamps are in datetime format
    current_date = pd.Timestamp.now(tz='UTC')
    month_start = current_date.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    prev_month_start = (month_start - pd.Timedelta(days=1)).replace(day=1)
    
    if not highlights.empty:
        highlights = highlights.copy()
        if not pd.api.types.is_datetime64_any_dtype(highlights['created_at']):
            highlights['created_at'] = pd.to_datetime(highlights['created_at'], utc=True)
    
    if not streams.empty:
        streams = streams.copy()
        if not pd.api.types.is_datetime64_any_dtype(streams['created_at']):
            streams['created_at'] = pd.to_datetime(streams['created_at'], utc=True)
    
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

    # 3. Share Rate (New)
    update_summary_share_rate(row1_cols, highlights)

        # 4. Average Streams per Week per User
    with row1_cols[3]:
        if not streams.empty:
            # Use get_weekly_metrics to calculate average streams per user
            weekly_metrics = get_weekly_metrics(
                streams,
                date_column='created_at',
                value_column='user_id',
                agg_function='mean'
            )
            
            if not weekly_metrics.empty:
                # Get the last complete week's data
                last_complete_week = weekly_metrics[~weekly_metrics['is_extrapolated']].iloc[-1]
                
                st.metric(
                    "Avg Streams/User (Week)",
                    f"{last_complete_week['value']:.1f}",
                    help="Average number of streams per user for the last complete week"
                )
            else:
                st.metric("Avg Streams/User (Week)", "0.0")
        else:
            st.metric("Avg Streams/User (Week)", "No data")

    # 5. Like/Dislike Ratio (New)
    with row2_cols[0]:
        if not highlights.empty:
            current_month_data = highlights[highlights['created_at'] >= month_start]
            current_month_data = current_month_data[current_month_data['liked'].notna()]
            
            if not current_month_data.empty:
                likes = (current_month_data['liked'] == True).sum()
                dislikes = (current_month_data['liked'] == False).sum()
                total_rated = likes + dislikes
                
                if total_rated > 0:
                    like_ratio = (likes / total_rated * 100)
                    
                    # Get previous month's data for delta
                    prev_month_data = highlights[
                        (highlights['created_at'] >= prev_month_start) &
                        (highlights['created_at'] < month_start)
                    ]
                    prev_month_data = prev_month_data[prev_month_data['liked'].notna()]
                    
                    prev_ratio = 0
                    if not prev_month_data.empty:
                        prev_likes = (prev_month_data['liked'] == True).sum()
                        prev_dislikes = (prev_month_data['liked'] == False).sum()
                        prev_total = prev_likes + prev_dislikes
                        if prev_total > 0:
                            prev_ratio = (prev_likes / prev_total * 100)
                    
                    delta = like_ratio - prev_ratio if prev_ratio > 0 else None
                    
                    st.metric(
                        "Like Ratio (Month)",
                        f"{like_ratio:.1f}%",
                        f"{delta:+.1f}%" if delta is not None else None,
                        help=f"Percentage of rated highlights marked as liked this month ({likes}/{total_rated} highlights)"
                    )
                else:
                    st.metric(
                        "Like Ratio (Month)",
                        "N/A",
                        help="No rated highlights this month"
                    )
            else:
                st.metric("Like Ratio (Month)", "N/A")
        else:
            st.metric("Like Ratio (Month)", "No data")

    # 6. Highlight Agreement Rate (Preserved)
    with row2_cols[1]:
        st.metric(
            "Highlight Agreement Rate",
            "24.0%",
            help="Percentage of highlights that match human agreement"
        )

    # 7. Monthly Active Users (MAU)
    with row2_cols[2]:
        if not streams.empty:
            thirty_days_ago = current_date - pd.Timedelta(days=30)
            active_users = len(streams[streams['created_at'] >= thirty_days_ago]['user_id'].unique())
            
            st.metric(
                "Monthly Active Users",
                f"{active_users:,}",
                help="Unique users who have converted a in the last 30 days"
            )
        else:
            st.metric("Monthly Active Users", "No data")

    # 8. Premium Users
    with row2_cols[3]:
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
        if not highlights.empty:
            highlights['created_at'] = pd.to_datetime(highlights['created_at'], utc=True)

        # Main dashboard title with styling
        st.title('📊 Platform Analytics Dashboard')
        st.caption('Data excludes developer activity')

        # Add data freshness indicator
        last_update = pd.Timestamp.now(tz='UTC')
        st.sidebar.info(f"Data last updated: {last_update.strftime('%Y-%m-%d %H:%M:%S')} UTC")

        # Display summary metrics
        display_summary_metrics(streams, users, highlights)

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