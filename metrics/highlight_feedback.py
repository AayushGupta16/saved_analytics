# File: metrics/highlight_feedback.py

import streamlit as st
import pandas as pd
from .utils import get_weekly_metrics, display_weekly_data

def calculate_like_ratio(highlights_df):
    """
    Calculate the ratio of likes to dislikes for highlights, excluding nulls.
    """
    if highlights_df.empty:
        st.write("Highlights DataFrame is empty")
        return pd.DataFrame()
    
    # Convert timestamps to UTC if not already
    df = highlights_df.copy()
    if not pd.api.types.is_datetime64_any_dtype(df['created_at']):
        df['created_at'] = pd.to_datetime(df['created_at'], utc=True)
    
    # Debug info about the data
    st.write(f"Total highlights: {len(df)}")
    st.write(f"Highlights with non-null 'liked' values: {df['liked'].notna().sum()}")
    st.write(f"Number of likes (True): {(df['liked'] == True).sum()}")
    st.write(f"Number of dislikes (False): {(df['liked'] == False).sum()}")
    
    # Filter for non-null liked values
    df = df[df['liked'].notna()].copy()
    
    if df.empty:
        st.write("No highlights with like/dislike data")
        return pd.DataFrame()
    
    # Create a boolean column for the ratio calculation
    df['like_ratio'] = (df['liked'] == True).astype(float) * 100
    
    # Debug info about weekly data
    st.write("Weekly data before aggregation:")
    debug_weekly = df.groupby(pd.Grouper(key='created_at', freq='W-SAT')).agg({
        'like_ratio': ['count', 'mean']
    }).reset_index()
    st.write(debug_weekly)
    
    # Use the common weekly metrics function
    weekly_data = get_weekly_metrics(
        df,
        date_column='created_at',
        value_column='like_ratio',
        agg_function='mean'
    )
    
    return weekly_data

def calculate_share_ratio(highlights_df):
    """
    Calculate the ratio of highlights that are either downloaded or link_copied.
    """
    if highlights_df.empty:
        return pd.DataFrame()
    
    df = highlights_df.copy()
    
    # Convert timestamps to UTC if not already
    if not pd.api.types.is_datetime64_any_dtype(df['created_at']):
        df['created_at'] = pd.to_datetime(df['created_at'], utc=True)
    
    # Calculate if highlight was shared (either downloaded or link copied)
    df['share_ratio'] = ((df['downloaded'] | df['link_copied']).astype(float) * 100)
    
    # Use the common weekly metrics function
    weekly_data = get_weekly_metrics(
        df,
        date_column='created_at',
        value_column='share_ratio',
        agg_function='mean'
    )
    
    return weekly_data

def display_highlight_like_ratio(highlights_df):
    """
    Display the weekly like/dislike ratio for highlights.
    """
    if highlights_df.empty:
        st.write("No data for Highlight Like/Dislike Ratio")
        return
    
    st.subheader("Like/Dislike Ratio")
    st.caption("Percentage of highlights marked as 'liked' vs 'not liked' (excluding unmarked)")
    
    like_ratio_data = calculate_like_ratio(highlights_df)
    if not like_ratio_data.empty:
        display_weekly_data(like_ratio_data, "Like Ratio (%)", 'purple')
    else:
        st.write("No weekly data available for like/dislike ratio")

def display_highlight_share_ratio(highlights_df):
    """
    Display the weekly share ratio for highlights.
    """
    if highlights_df.empty:
        st.write("No data for Highlight Share Ratio")
        return
    
    st.subheader("Share Ratio")
    st.caption("Percentage of highlights that were downloaded or had their link copied")
    
    share_ratio_data = calculate_share_ratio(highlights_df)
    if not share_ratio_data.empty:
        display_weekly_data(share_ratio_data, "Share Ratio (%)", 'brown')
    else:
        st.write("No weekly data available for share ratio")