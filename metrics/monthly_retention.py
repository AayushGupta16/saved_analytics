import streamlit as st
import pandas as pd

def display_monthly_retention(streams_df):
    """
    Just shows monthly unique users for completed months (excluding current month).
    """
    if streams_df.empty:
        st.write("No data for Monthly Retention (simplified)")
        return
    
    if not pd.api.types.is_datetime64_any_dtype(streams_df['created_at']):
        streams_df['created_at'] = pd.to_datetime(streams_df['created_at'], utc=True)
    
    streams_df['year_month'] = streams_df['created_at'].dt.to_period('M')
    if streams_df['year_month'].empty:
        st.write("No monthly data available.")
        return
    
    latest_month = streams_df['year_month'].max()
    completed_months = streams_df[streams_df['year_month'] < latest_month]

    if completed_months.empty:
        st.write("No fully completed months available for retention.")
        return

    monthly_users = completed_months.groupby('year_month')['user_id'].nunique().reset_index()
    monthly_users['year_month'] = monthly_users['year_month'].dt.to_timestamp()

    st.write("Data for Monthly Retention (Completed Months Only):")
    st.dataframe(monthly_users)  
    st.write("Monthly User Counts (excluding current month):")
    st.line_chart(data=monthly_users, x='year_month', y='user_id')
