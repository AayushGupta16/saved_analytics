import streamlit as st
import pandas as pd

def display_avg_streams_per_user(streams_df):
    """
    Displays a simple average streams per user per completed week (excluding current week).
    """
    if streams_df.empty:
        st.write("No data for Average Streams per User")
        return

    # Ensure datetime
    if not pd.api.types.is_datetime64_any_dtype(streams_df['created_at']):
        streams_df['created_at'] = pd.to_datetime(streams_df['created_at'], utc=True)

    # Calculate Monday-based week_start
    # Monday is weekday()=0, so subtract .weekday() days to get the Monday of that week
    streams_df['week_start'] = streams_df['created_at'] - pd.to_timedelta(streams_df['created_at'].dt.weekday, unit='D')

    # Exclude current (incomplete) week
    # Current week start = Monday of the current week
    today = pd.Timestamp.now(tz='UTC')
    current_week_start = today - pd.to_timedelta(today.weekday(), unit='D')
    completed_weeks = streams_df[streams_df['week_start'] < current_week_start]

    if completed_weeks.empty:
        st.write("No fully completed weeks available.")
        return

    weekly_streams = completed_weeks.groupby(['week_start', 'user_id']).size().reset_index(name='streams')
    avg_per_week = weekly_streams.groupby('week_start')['streams'].mean().reset_index(name='avg_streams')

    st.write("Data for Avg Streams per User (Completed Weeks Only):")
    st.dataframe(avg_per_week)  
    st.write("Average Streams per User (Weekly, excluding current week):")
    st.line_chart(data=avg_per_week, x='week_start', y='avg_streams')
