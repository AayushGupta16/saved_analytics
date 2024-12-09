import streamlit as st
import pandas as pd

from .utils import get_weekly_metrics, display_weekly_data

def display_new_user_signups(users_df):
    """
    New user signups with current week handling.
    """
    if users_df.empty:
        st.write("No user data for Signups")
        return
    
    weekly_data = get_weekly_metrics(users_df, 'created_at')
    display_weekly_data(weekly_data, "New Users", 'green')