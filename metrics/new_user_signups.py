import streamlit as st
import pandas as pd

def display_new_user_signups(users_df):
    """
    Displays New User Signups per completed week (excluding current week).
    """
    if users_df.empty:
        st.write("No user data for Signups")
        return
    
    if not pd.api.types.is_datetime64_any_dtype(users_df['created_at']):
        users_df['created_at'] = pd.to_datetime(users_df['created_at'], utc=True)
    
    # Monday-based weeks
    users_df['week_start'] = users_df['created_at'] - pd.to_timedelta(users_df['created_at'].dt.weekday, unit='D')
    
    today = pd.Timestamp.now(tz='UTC')
    current_week_start = today - pd.to_timedelta(today.weekday(), unit='D')
    completed_weeks = users_df[users_df['week_start'] < current_week_start]

    if completed_weeks.empty:
        st.write("No fully completed weeks available for signups.")
        return

    weekly_signups = completed_weeks.groupby('week_start').size().reset_index(name='new_users')

    st.write("Data for Weekly Signups (Completed Weeks Only):")
    st.dataframe(weekly_signups)  
    st.write("New User Signups (Weekly, excluding current week):")
    st.line_chart(data=weekly_signups, x='week_start', y='new_users')
