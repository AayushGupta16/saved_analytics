import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go  # Add this import
from datetime import datetime, timezone
import numpy as np


def get_extrapolated_weekly_data(df: pd.DataFrame, date_column: str, count_column: str = None, 
                                agg_function: str = 'count') -> pd.DataFrame:
    if df.empty:
        return pd.DataFrame()
    
    # Ensure datetime is UTC
    df = df.copy()
    df[date_column] = pd.to_datetime(df[date_column], utc=True)
    
    # Get current time and week boundary
    today = pd.Timestamp.now(tz='UTC')
    
    # Important: Calculate the start of the current week
    # If today is Sunday, use today as the week start
    # Otherwise, go back to the last Sunday
    days_since_sunday = today.weekday() + 1  # +1 because weekday() considers Monday as 0
    current_week_start = (today - pd.Timedelta(days=days_since_sunday if days_since_sunday < 7 else 0))
    current_week_start = current_week_start.replace(hour=0, minute=0, second=0, microsecond=0)
    
    # Calculate days elapsed in current week
    days_elapsed = (today - current_week_start).days + 1
    
    # Define fixed week start date (Sept 29, 2024)
    start_date = pd.Timestamp('2024-09-29', tz='UTC')
    
    # Calculate week numbers and starts for all data points
    df['week_number'] = ((df[date_column] - start_date) // pd.Timedelta(weeks=1)) + 1
    df['week_start'] = start_date + (df['week_number'] - 1) * pd.Timedelta(weeks=1)
    
    # Remove any future data
    df = df[df[date_column] <= today]
    
    # Separate current week and historical data
    # IMPORTANT: Use exact timestamp comparison for week_start
    current_week_mask = (df['week_start'] == current_week_start)
    current_week_data = df[current_week_mask]
    historical_data = df[~current_week_mask]
    
    # First process historical data
    if agg_function == 'unique_count':
        weekly_data = historical_data.groupby('week_start')[count_column].nunique()
    elif agg_function == 'mean':
        grouped = historical_data.groupby(['week_start', count_column]).size()
        weekly_data = grouped.groupby(level=0).mean()
    else:  # count
        weekly_data = historical_data.groupby('week_start').size()
    
    weekly_data = weekly_data.reset_index()
    weekly_data.columns = ['week_start', 'value']
    weekly_data['is_extrapolated'] = False
    
    # Now handle current week projection
    if not current_week_data.empty:
        # Calculate current week value
        if agg_function == 'unique_count':
            current_value = current_week_data[count_column].nunique()
        elif agg_function == 'mean':
            current_value = current_week_data.groupby(count_column).size().mean()
        else:
            current_value = len(current_week_data)
        
        # Extrapolate to full week
        # Ensure we don't divide by zero
        days_elapsed = max(1, days_elapsed)
        extrapolated_value = np.ceil((current_value / days_elapsed) * 7)
        
        # Add current week as extrapolated data
        current_week_row = pd.DataFrame({
            'week_start': [current_week_start],
            'value': [extrapolated_value],
            'is_extrapolated': [True]  # Always mark current week as extrapolated
        })
        
        weekly_data = pd.concat([weekly_data, current_week_row], ignore_index=True)
        
        # Debug logging (you can remove this in production)
        print(f"Current week start: {current_week_start}")
        print(f"Days elapsed: {days_elapsed}")
        print(f"Current value: {current_value}")
        print(f"Extrapolated value: {extrapolated_value}")
    
    return weekly_data.sort_values('week_start', ascending=True)

# The display_weekly_metrics function should work correctly once it receives 
# proper data from get_extrapolated_weekly_data. Here's a verification helper:

def verify_weekly_data(data_df: pd.DataFrame) -> None:
    """Helper function to verify weekly data calculations"""
    today = pd.Timestamp.now(tz='UTC')
    current_week_start = (today - pd.Timedelta(days=today.weekday() + 1 if today.weekday() != 6 else 0))
    current_week_start = current_week_start.replace(hour=0, minute=0, second=0, microsecond=0)
    
    # Print verification info
    print(f"Today: {today}")
    print(f"Current week start: {current_week_start}")
    
    # Verify data
    for _, row in data_df.iterrows():
        week_start = row['week_start']
        is_extrapolated = row['is_extrapolated']
        print(f"\nWeek starting {week_start}:")
        print(f"Value: {row['value']}")
        print(f"Is extrapolated: {is_extrapolated}")
        print(f"Should be extrapolated: {week_start == current_week_start}")


def create_time_series_plot(data: pd.DataFrame, 
                            title: str,
                            y_axis_title: str,
                            color: str = '#1f77b4',
                            show_growth: bool = True) -> go.Figure:
    """
    Create a consistent time series plot with improved styling
    """
    # Calculate period-over-period growth
    if show_growth and len(data) > 1:
        data = data.copy()
        data['growth'] = data['value'].pct_change() * 100
    
    fig = px.line(
        data,
        x='week_start',
        y='value',
        title=title,
        markers=True,
        color_discrete_sequence=[color]
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
            text=title,
            x=0.5,
            y=0.95,
            xanchor='center',
            yanchor='top',
            font_size=24
        ),
        xaxis_title="Week Starting",
        yaxis_title=y_axis_title,
        height=600,
        xaxis=dict(tickangle=-45)
    )
    
    # Style the lines differently for actual vs extrapolated data
    for i, row in data.iterrows():
        if row['is_extrapolated']:
            fig.add_scatter(
                x=[row['week_start']],
                y=[row['value']],
                mode='markers+lines',
                line=dict(dash='dot', color=color),
                marker=dict(size=10, color=color, symbol='star'),
                name='Projected',
                showlegend=i == len(data) - 1,
                hovertemplate="<br>".join([
                    "<b>Week Starting:</b> %{x|%Y-%m-%d}",
                    f"<b>{y_axis_title}:</b> %{{y:.1f}} (Projected)",
                    "<extra></extra>"
                ])
            )
    
    # Update main trace
    fig.update_traces(
        line=dict(width=2),
        marker=dict(size=8),
        hovertemplate="<br>".join([
            "<b>Week Starting:</b> %{x|%Y-%m-%d}",
            f"<b>{y_axis_title}:</b> %{{y:.1f}}",
            f"<b>Growth:</b> {'+' if show_growth else ''}" + "%{customdata[0]:.1f}%" if show_growth else "",
            "<extra></extra>"
        ]),
        customdata=data[['growth']] if show_growth else None,
        selector=dict(mode='lines+markers')
    )
    
    return fig

def display_weekly_metrics(data_df: pd.DataFrame, 
                         metric_name: str,
                         date_column: str = 'created_at',
                         count_column: str = None,
                         agg_function: str = 'count',
                         color: str = '#1f77b4') -> None:
    """
    Display weekly metrics with improved visualization
    """
    st.header(f'{metric_name} (Weekly)')
    
    if data_df.empty:
        st.write(f"No data available for {metric_name}")
        return
    
    # Get weekly data with extrapolation
    weekly_data = get_extrapolated_weekly_data(
        data_df, 
        date_column, 
        count_column, 
        agg_function
    )
    
    # Create and display plot
    fig = create_time_series_plot(
        weekly_data,
        title=f'{metric_name} (Weekly)',
        y_axis_title=metric_name,
        color=color
    )
    
    st.plotly_chart(fig, use_container_width=True)
    
    # Display data table with clear extrapolation marking
    display_df = weekly_data.copy()
    display_df['Status'] = display_df['is_extrapolated'].map({True: '📊 Projected', False: '✓ Actual'})
    display_df = display_df.drop('is_extrapolated', axis=1)
    display_df.columns = ['Week Starting', 'Value', 'Status']
    
    st.subheader(f"Weekly {metric_name} Data")
    st.dataframe(
        display_df.sort_values('Week Starting', ascending=False),
        hide_index=True
    )

def display_weekly_streams(streams_df):
    display_weekly_metrics(
        streams_df,
        "Stream Count",
        'created_at',
        color='#1f77b4'
    )

def display_weekly_active_users(streams_df):
    display_weekly_metrics(
        streams_df,
        "Active Users",
        'created_at',
        'user_id',
        'unique_count',
        color='#ff7f0e'
    )
