import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime, timedelta, timezone
import numpy as np

def get_fixed_weekly_intervals(df, date_column):
    """
    Assigns each data point to a fixed weekly interval starting from Sept 29, 2024.
    All datetime objects are timezone-aware (UTC).
    """
    if df.empty:
        return pd.DataFrame()
    
    df = df.copy()
    # Ensure datetime is parsed with UTC timezone
    df[date_column] = pd.to_datetime(df[date_column], utc=True)
    
    # Define the start date: Sunday, September 29, 2024, UTC
    start_date = pd.Timestamp('2024-09-29', tz='UTC')
    
    # Calculate the week number for each date
    df['week_number'] = ((df[date_column] - start_date) // pd.Timedelta(weeks=1)) + 1
    df['week_start'] = start_date + (df['week_number'] - 1) * pd.Timedelta(weeks=1)
    
    return df

def get_weekly_signups(users_df, date_column='created_at'):
    """
    Gets weekly signup data with debug logging.
    """
    if users_df.empty:
        print("Input dataframe is empty")
        return pd.DataFrame()
    
    # Add debug logging
    print("\n=== Debug Information ===")
    
    # Ensure datetime is UTC and copy the dataframe
    df = users_df.copy()
    df[date_column] = pd.to_datetime(df[date_column], utc=True)
    
    # Get current time and week boundary
    today = pd.Timestamp.now(tz='UTC')
    print(f"Current time (UTC): {today}")
    
    # Calculate the start of the current week (Sunday)
    days_since_sunday = today.weekday() + 1  # +1 because weekday() considers Monday as 0
    current_week_start = (today - pd.Timedelta(days=days_since_sunday if days_since_sunday < 7 else 0))
    current_week_start = current_week_start.replace(hour=0, minute=0, second=0, microsecond=0)
    print(f"Current week start: {current_week_start}")
    
    # Calculate days elapsed in current week
    days_elapsed = (today - current_week_start).days + 1
    print(f"Days elapsed in current week: {days_elapsed}")
    
    # Define fixed week start date (Sept 29, 2024)
    start_date = pd.Timestamp('2024-09-29', tz='UTC')
    print(f"Fixed start date: {start_date}")
    
    # Calculate week numbers and starts for all data points
    df['week_number'] = ((df[date_column] - start_date) // pd.Timedelta(weeks=1)) + 1
    df['week_start'] = start_date + (df['week_number'] - 1) * pd.Timedelta(weeks=1)
    
    # Print sample of data points
    print("\nSample data points:")
    print(df[[date_column, 'week_start']].head())
    
    # Remove any future data
    df = df[df[date_column] <= today]
    
    # Separate current week and historical data using exact timestamp comparison
    current_week_mask = (df['week_start'] == current_week_start)
    current_week_data = df[current_week_mask]
    historical_data = df[~current_week_mask]
    
    print(f"\nCurrent week data count: {len(current_week_data)}")
    if not current_week_data.empty:
        print("Current week signup dates:")
        print(current_week_data[date_column].tolist())
    
    print(f"Historical data count: {len(historical_data)}")
    
    # Process historical data
    weekly_signups = historical_data.groupby('week_start').size().reset_index(name='new_users')
    weekly_signups['is_extrapolated'] = False
    
    # Handle current week projection if we have data
    if not current_week_data.empty:
        # Get actual signup count for current week
        current_signups = len(current_week_data)
        print(f"\nActual signups in current week: {current_signups}")
        
        # For early week (<=3 days), just show actuals
        if days_elapsed <= 3:
            estimated_signups = current_signups
            print("Early in week - using actual numbers")
        else:
            # Project based on current rate, but never less than actual
            raw_projection = (current_signups / days_elapsed) * 7
            estimated_signups = int(np.ceil(max(raw_projection, current_signups)))
            print(f"Projection calculation: ({current_signups} / {days_elapsed}) * 7 = {raw_projection}")
        
        print(f"Final estimated signups: {estimated_signups}")
        
        # Add current week data
        current_week_row = pd.DataFrame({
            'week_start': [current_week_start],
            'new_users': [estimated_signups],
            'is_extrapolated': [True]
        })
        
        weekly_signups = pd.concat([weekly_signups, current_week_row], ignore_index=True)
    
    print("\nFinal weekly data:")
    print(weekly_signups)
    print("=== End Debug Information ===\n")
    
    return weekly_signups.sort_values('week_start', ascending=False)

def start_of_week(date):
    """
    Returns the start of the week (Sunday) for a given date.
    """
    return date - pd.Timedelta(days=date.weekday() + 1 if date.weekday() != 6 else 0)

def display_new_user_signups(users_df):
    """
    Display weekly new user signups with improved visualization
    """
    st.header('New User Signups (Weekly Intervals)')
    
    if users_df.empty:
        st.write("No data available for New User Signups")
        return
        
    weekly_signups = get_weekly_signups(users_df)
    
    if weekly_signups.empty:
        st.write("No weekly signup data available.")
        return
    
    # Create visualization
    fig = px.line(
        weekly_signups,
        x='week_start',
        y='new_users',
        title='New User Signups (Weekly Intervals)',
        markers=True,
        color_discrete_sequence=['green']
    )
    
    # Update layout
    fig.update_layout(
        hovermode='x unified',
        hoverlabel=dict(
            bgcolor="white",
            font_size=14,
            font_color="black",
            bordercolor="black"
        ),
        title=dict(
            text='New User Signups (Weekly Intervals)',
            x=0.5,
            y=0.95,
            xanchor='center',
            yanchor='top',
            font_size=24
        ),
        xaxis_title="Week Starting",
        yaxis_title="Number of New Users",
        height=600,
        xaxis=dict(tickangle=-45)
    )
    
    # Style the lines differently for actual vs extrapolated data
    for i, row in weekly_signups.iterrows():
        if row['is_extrapolated']:
            fig.add_scatter(
                x=[row['week_start']],
                y=[row['new_users']],
                mode='markers+lines',
                line=dict(dash='dot', color='green'),
                marker=dict(size=10, color='green', symbol='star'),
                name='Projected',
                showlegend=i == len(weekly_signups) - 1,
                hovertemplate="<br>".join([
                    "<b>Week Starting:</b> %{x|%Y-%m-%d}",
                    "<b>New Users:</b> %{y} (Projected)",
                    "<extra></extra>"
                ])
            )
    
    # Update main trace
    fig.update_traces(
        line=dict(width=2),
        marker=dict(size=8),
        hovertemplate="<br>".join([
            "<b>Week Starting:</b> %{x|%Y-%m-%d}",
            "<b>New Users:</b> %{y}",
            "<extra></extra>"
        ]),
        selector=dict(mode='lines+markers')
    )
    
    st.plotly_chart(fig, use_container_width=True)
    
    # Display data table
    st.subheader("Weekly New User Signups Data")
    display_df = weekly_signups.copy()
    display_df['Status'] = display_df['is_extrapolated'].map({True: '📊 Projected', False: '✓ Actual'})
    display_df = display_df.drop('is_extrapolated', axis=1)
    display_df.columns = ['Week Starting', 'New Users', 'Status']
    
    st.dataframe(
        display_df.sort_values('Week Starting', ascending=False),
        hide_index=True
    )

    get_weekly_signups()