import streamlit as st
import pandas as pd
from .monthly_utils import calculate_monthly_retention, create_monthly_plot

def display_monthly_retention(streams_df):
    """
    Displays monthly retention rates with current month handling.
    """
    if streams_df.empty:
        st.write("No data for Monthly Retention")
        return

    # Calculate retention metrics
    retention_data = calculate_monthly_retention(streams_df)
    
    if retention_data.empty:
        st.write("Insufficient data to calculate retention (need at least two months of data).")
        return
    
    # Create visualization
    fig = create_monthly_plot(
        retention_data,
        'Monthly Retention Rate',
        '#FFD700'
    )
    
    st.plotly_chart(fig, use_container_width=True)
    
    # Display data table
    st.subheader("Monthly Retention Data")
    display_df = retention_data.copy()
    display_df['Status'] = display_df['is_extrapolated'].map({True: '📊 In Progress', False: '✓ Complete'})
    display_df = display_df.drop('is_extrapolated', axis=1)
    
    # Format retention rate to 1 decimal place
    display_df['retention_rate'] = display_df['retention_rate'].round(1).astype(str) + '%'
    
    # Rename columns for display
    display_df.columns = [
        'Month', 
        'Retained Users', 
        'Previous Month Users',
        'Retention Rate',
        'Status'
    ]
    
    st.dataframe(
        display_df.sort_values('Month', ascending=False),
        hide_index=True
    )