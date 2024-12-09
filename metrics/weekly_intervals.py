import streamlit as st
import pandas as pd

def display_weekly_streams(streams_df):
    """
    Weekly Stream Counts for completed weeks (excluding current week).
    """
    if streams_df.empty:
        st.write("No data for Weekly Streams")
        return
    
    if not pd.api.types.is_datetime64_any_dtype(streams_df['created_at']):
        streams_df['created_at'] = pd.to_datetime(streams_df['created_at'], utc=True)
    
    streams_df['week_start'] = streams_df['created_at'] - pd.to_timedelta(streams_df['created_at'].dt.weekday, unit='D')

    today = pd.Timestamp.now(tz='UTC')
    current_week_start = today - pd.to_timedelta(today.weekday(), unit='D')
    completed_weeks = streams_df[streams_df['week_start'] < current_week_start]

    if completed_weeks.empty:
        st.write("No fully completed weeks available for streams.")
        return

    weekly_counts = completed_weeks.groupby('week_start').size().reset_index(name='streams')

    st.write("Data for Weekly Streams (Completed Weeks Only):")
    st.dataframe(weekly_counts)  
    st.write("Weekly Stream Count (excluding current week):")
    st.line_chart(data=weekly_counts, x='week_start', y='streams')

def display_weekly_active_users(streams_df):
    """
    Weekly Active Users for completed weeks (excluding current week).
    """
    if streams_df.empty:
        st.write("No data for Weekly Active Users")
        return
    
    if not pd.api.types.is_datetime64_any_dtype(streams_df['created_at']):
        streams_df['created_at'] = pd.to_datetime(streams_df['created_at'], utc=True)
    
    streams_df['week_start'] = streams_df['created_at'] - pd.to_timedelta(streams_df['created_at'].dt.weekday, unit='D')

    today = pd.Timestamp.now(tz='UTC')
    current_week_start = today - pd.to_timedelta(today.weekday(), unit='D')
    completed_weeks = streams_df[streams_df['week_start'] < current_week_start]

    if completed_weeks.empty:
        st.write("No fully completed weeks available for active users.")
        return

    weekly_active = completed_weeks.groupby(['week_start'])['user_id'].nunique().reset_index(name='active_users')

    st.write("Data for Weekly Active Users (Completed Weeks Only):")
    st.dataframe(weekly_active)  
    st.write("Weekly Active Users (excluding current week):")
    st.line_chart(data=weekly_active, x='week_start', y='active_users')
