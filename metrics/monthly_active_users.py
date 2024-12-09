import streamlit as st
import pandas as pd

def display_monthly_active_users(streams_df):
    """
    Displays Monthly Active Users (MAU) per completed month (excluding current month).
    """
    if streams_df.empty:
        st.write("No data for Monthly Active Users")
        return
    
    if not pd.api.types.is_datetime64_any_dtype(streams_df['created_at']):
        streams_df['created_at'] = pd.to_datetime(streams_df['created_at'], utc=True)
    
    streams_df['year_month'] = streams_df['created_at'].dt.to_period('M')
    # Identify the latest month
    if streams_df['year_month'].empty:
        st.write("No data after converting to monthly periods.")
        return
    
    latest_month = streams_df['year_month'].max()
    completed_months = streams_df[streams_df['year_month'] < latest_month]

    if completed_months.empty:
        st.write("No fully completed months available.")
        return

    mau = completed_months.groupby('year_month')['user_id'].nunique().reset_index()
    mau['year_month'] = mau['year_month'].dt.to_timestamp()

    st.write("Data for MAU (Completed Months Only):")
    st.dataframe(mau)
    st.write("Monthly Active Users (excluding current month):")
    st.line_chart(data=mau, x='year_month', y='user_id')
