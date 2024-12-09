import streamlit as st
import pandas as pd
from .utils import get_weekly_metrics, display_weekly_data

def display_avg_streams_per_user(streams_df):
    """
    Average streams per user with current week handling.
    """
    if streams_df.empty:
        st.write("No data for Average Streams per User")
        return
    
    weekly_data = get_weekly_metrics(
        streams_df,
        'created_at',
        'user_id',
        'mean'
    )
    display_weekly_data(weekly_data, "Average Streams per User", 'orange')
