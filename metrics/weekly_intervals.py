import streamlit as st
import pandas as pd

from .utils import get_weekly_metrics, display_weekly_data

def display_weekly_streams(streams_df):
    """
    Weekly Stream Counts with current week handling.
    """
    if streams_df.empty:
        st.write("No data for Weekly Streams")
        return
    
    weekly_data = get_weekly_metrics(streams_df, 'created_at')
    display_weekly_data(weekly_data, "Stream Count", '#1f77b4')

def display_weekly_active_users(streams_df):
    """
    Weekly Active Users with current week handling.
    """
    if streams_df.empty:
        st.write("No data for Weekly Active Users")
        return
    
    weekly_data = get_weekly_metrics(
        streams_df, 
        'created_at',
        'user_id',
        'unique_count'
    )
    display_weekly_data(weekly_data, "Active Users", '#ff7f0e')