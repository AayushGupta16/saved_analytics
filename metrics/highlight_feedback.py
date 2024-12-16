# File: metrics/highlight_feedback.py

import streamlit as st
import pandas as pd
from .utils import get_weekly_metrics, display_weekly_data

def calculate_share_ratio(highlights_df):
    """
    Calculate the ratio of highlights that are either downloaded or link_copied.
    Returns weekly data with proper handling of current week.
    """
    if highlights_df.empty:
        return pd.DataFrame()
    
    df = highlights_df.copy()
    
    # Convert timestamps to UTC if not already
    if not pd.api.types.is_datetime64_any_dtype(df['created_at']):
        df['created_at'] = pd.to_datetime(df['created_at'], utc=True)
    
    # Calculate if highlight was shared (either downloaded or link copied)
    df['share_ratio'] = ((df['downloaded'] | df['link_copied']).astype(float) * 100)
    
    # Use the common weekly metrics function with mean aggregation
    weekly_data = get_weekly_metrics(
        df,
        date_column='created_at',
        value_column='share_ratio',
        agg_function='mean'
    )
    
    return weekly_data

def update_summary_share_rate(row1_cols, highlights_df):
    """
    Updates the share rate summary metric with consistent calculation.
    """
    with row1_cols[2]:
        if not highlights_df.empty:
            share_ratio_data = calculate_share_ratio(highlights_df)
            
            if not share_ratio_data.empty:
                # Get the latest complete week's data
                complete_weeks = share_ratio_data[~share_ratio_data['is_extrapolated']]
                if not complete_weeks.empty:
                    latest_complete = complete_weeks.iloc[-1]
                    previous_complete = complete_weeks.iloc[-2] if len(complete_weeks) > 1 else None
                    
                    share_ratio = latest_complete['value']
                    delta = None
                    if previous_complete is not None:
                        delta = share_ratio - previous_complete['value']
                    
                    st.metric(
                        "Share Rate (Week)",
                        f"{share_ratio:.1f}%",
                        f"{delta:+.1f}%" if delta is not None else None,
                        help="Percentage of highlights shared in the last complete week"
                    )
                else:
                    st.metric("Share Rate (Week)", "No complete week data")
            else:
                st.metric("Share Rate (Week)", "0.0%")
        else:
            st.metric("Share Rate (Week)", "No data")

def display_highlight_share_ratio(highlights_df):
    """
    Display the weekly share ratio for highlights with current week handling.
    """
    if highlights_df.empty:
        st.write("No data for Highlight Share Ratio")
        return
    
    st.subheader("Share Ratio")
    st.caption("Percentage of highlights that were downloaded or had their link copied")
    
    share_ratio_data = calculate_share_ratio(highlights_df)
    if not share_ratio_data.empty:
        display_weekly_data(share_ratio_data, "Share Ratio (%)", 'brown')
        
        # Get last complete week's data for the summary metric
        complete_weeks = share_ratio_data[~share_ratio_data['is_extrapolated']]
        if not complete_weeks.empty:
            latest_complete = complete_weeks.iloc[-1]
            previous_complete = complete_weeks.iloc[-2] if len(complete_weeks) > 1 else None
            
            delta = None
            if previous_complete is not None:
                delta = latest_complete['value'] - previous_complete['value']
            
            # Display the summary metric
            st.metric(
                "Latest Complete Week Share Rate",
                f"{latest_complete['value']:.1f}%",
                f"{delta:+.1f}%" if delta is not None else None,
                help="Share rate for the last completed week"
            )
    else:
        st.write("No weekly data available for share ratio")