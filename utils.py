import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta, timezone
import numpy as np

def get_extrapolated_monthly_data(df: pd.DataFrame, 
                                  date_column: str, 
                                  count_column: str = None, 
                                  agg_function: str = 'count') -> pd.DataFrame:
    """
    Calculate monthly data with clear extrapolation for the current month.
    
    Parameters:
        df (pd.DataFrame): DataFrame with the data.
        date_column (str): Name of the date column.
        count_column (str, optional): Column to count unique values from (optional).
        agg_function (str, optional): 'count', 'mean', 'unique_count', or 'retention'.
    
    Returns:
        pd.DataFrame: Aggregated monthly data with extrapolated current month.
    """
    if df.empty:
        return pd.DataFrame()
    
    # Ensure datetime is UTC
    df = df.copy()
    df[date_column] = pd.to_datetime(df[date_column], utc=True)
    
    # Get current month information
    today = pd.Timestamp.now(tz='UTC')
    current_month_start = today.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    days_in_month = today.days_in_month
    days_elapsed = (today - current_month_start).days + 1
    
    # Separate current month and historical data
    current_month = df[df[date_column] >= current_month_start]
    historical_data = df[df[date_column] < current_month_start]
    
    # Aggregate historical data based on function type
    if agg_function == 'retention':
        monthly_data = calculate_retention(historical_data, date_column)
    else:
        if agg_function == 'unique_count':
            monthly_data = historical_data.groupby(pd.Grouper(key=date_column, freq='M'))[count_column].nunique()
        elif agg_function == 'mean':
            grouped = historical_data.groupby([pd.Grouper(key=date_column, freq='M'), count_column]).size()
            monthly_data = grouped.groupby(level=0).mean()
        else:  # count
            monthly_data = historical_data.groupby(pd.Grouper(key=date_column, freq='M')).size()
        
        monthly_data = monthly_data.reset_index()
        monthly_data.columns = ['date', 'value']
    
    monthly_data['is_extrapolated'] = False
    
    # Calculate and append extrapolated data if we have current month data
    if not current_month.empty:
        if agg_function == 'retention':
            # Special handling for retention metrics
            current_value = calculate_current_month_retention(current_month, historical_data, date_column)
        else:
            if agg_function == 'unique_count':
                current_value = current_month[count_column].nunique()
            elif agg_function == 'mean':
                current_value = current_month.groupby(count_column).size().mean()
            else:
                current_value = len(current_month)
            
            # Extrapolate to full month
            current_value = np.ceil((current_value / days_elapsed) * days_in_month)
        
        extrapolated_row = pd.DataFrame({
            'date': [current_month_start],
            'value': [current_value],
            'is_extrapolated': [True]
        })
        
        monthly_data = pd.concat([monthly_data, extrapolated_row], ignore_index=True)
    
    return monthly_data.sort_values('date', ascending=True)

def create_monthly_plot(data: pd.DataFrame, 
                        title: str,
                        y_axis_title: str,
                        color: str = '#1f77b4',
                        show_growth: bool = True) -> go.Figure:
    """
    Create a consistent monthly plot with improved styling.
    
    Parameters:
        data (pd.DataFrame): DataFrame containing monthly data.
        title (str): Title of the plot.
        y_axis_title (str): Label for the Y-axis.
        color (str, optional): Color of the plot line.
        show_growth (bool, optional): Whether to display growth metrics.
    
    Returns:
        go.Figure: Plotly figure object.
    """
    # Calculate month-over-month growth
    if show_growth and len(data) > 1:
        data = data.copy()
        data['growth'] = data['value'].pct_change() * 100
    
    fig = px.line(
        data,
        x='date',
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
        xaxis_title="Month",
        yaxis_title=y_axis_title,
        height=600,
        xaxis=dict(tickangle=-45)
    )
    
    # Style the lines differently for actual vs extrapolated data
    for i, row in data.iterrows():
        if row['is_extrapolated']:
            fig.add_scatter(
                x=[row['date']],
                y=[row['value']],
                mode='markers+lines',
                line=dict(dash='dot', color=color),
                marker=dict(size=10, color=color, symbol='star'),
                name='Projected',
                showlegend=i == len(data) - 1,
                hovertemplate="<br>".join([
                    "<b>Month:</b> %{x|%B %Y}",
                    f"<b>{y_axis_title}:</b> %{{y:.1f}} (Projected)",
                    "<extra></extra>"
                ])
            )
    
    # Update main trace
    fig.update_traces(
        line=dict(width=2),
        marker=dict(size=8),
        hovertemplate="<br>".join([
            "<b>Month:</b> %{x|%B %Y}",
            f"<b>{y_axis_title}:</b> %{{y:.1f}}",
            f"<b>MoM Growth:</b> {'+' if show_growth else ''}%{{customdata[0]:.1f}}%" if show_growth else "",
            "<extra></extra>"
        ]),
        customdata=data[['growth']] if show_growth else None,
        selector=dict(mode='lines+markers')
    )
    
    return fig

def display_monthly_metrics(data_df: pd.DataFrame, 
                            metric_name: str,
                            date_column: str = 'created_at',
                            count_column: str = None,
                            agg_function: str = 'count',
                            color: str = '#1f77b4') -> None:
    """
    Display monthly metrics with improved visualization.
    
    Parameters:
        data_df (pd.DataFrame): DataFrame containing the data.
        metric_name (str): Name of the metric to display.
        date_column (str, optional): Name of the date column.
        count_column (str, optional): Column to count unique values from.
        agg_function (str, optional): Aggregation function ('count', 'mean', 'unique_count', 'retention').
        color (str, optional): Color for the plot.
    """
    st.header(f'{metric_name} (Monthly)')
    
    if data_df.empty:
        st.write(f"No data available for {metric_name}")
        return
    
    # Get monthly data with extrapolation
    monthly_data = get_extrapolated_monthly_data(
        data_df, 
        date_column, 
        count_column, 
        agg_function
    )
    
    # Create and display plot
    fig = create_monthly_plot(
        monthly_data,
        title=f'{metric_name} (Monthly)',
        y_axis_title=metric_name,
        color=color
    )
    
    st.plotly_chart(fig, use_container_width=True)
    
    # Display data table with clear extrapolation marking
    display_df = monthly_data.copy()
    display_df['Status'] = display_df['is_extrapolated'].map({True: '📊 Projected', False: '✓ Actual'})
    display_df = display_df.drop('is_extrapolated', axis=1)
    display_df.columns = ['Month', 'Value', 'Status']
    display_df['Month'] = display_df['Month'].dt.strftime('%B %Y')
    
    st.subheader(f"Monthly {metric_name} Data")
    st.dataframe(
        display_df.sort_values('Month', ascending=False),
        hide_index=True
    )

def display_new_user_signups_metric(users_df: pd.DataFrame):
    """
    Displays the New User Signups metric on the dashboard.
    
    Parameters:
        users_df (pd.DataFrame): DataFrame containing user data.
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

def display_weekly_metrics(data_df: pd.DataFrame, 
                           metric_name: str,
                           date_column: str = 'created_at',
                           count_column: str = None,
                           agg_function: str = 'count',
                           color: str = '#1f77b4') -> None:
    """
    Display weekly metrics with improved visualization.
    
    Parameters:
        data_df (pd.DataFrame): DataFrame containing the data.
        metric_name (str): Name of the metric to display.
        date_column (str, optional): Name of the date column.
        count_column (str, optional): Column to count unique values from.
        agg_function (str, optional): Aggregation function ('count', 'mean', 'unique_count').
        color (str, optional): Color for the plot.
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


def display_new_user_signups_metric(users_df: pd.DataFrame):
    """
    Displays the New User Signups metric on the dashboard.
    
    Parameters:
        users_df (pd.DataFrame): DataFrame containing user data.
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

def get_extrapolated_weekly_data(df: pd.DataFrame, 
                                 date_column: str, 
                                 count_column: str = None, 
                                 agg_function: str = 'count') -> pd.DataFrame:
    """
    Calculate weekly data with extrapolation for the current week.
    
    Parameters:
        df (pd.DataFrame): DataFrame with the data.
        date_column (str): Name of the date column.
        count_column (str, optional): Column to count unique values from (optional).
        agg_function (str, optional): 'count', 'mean', 'unique_count'.
    
    Returns:
        pd.DataFrame: Aggregated weekly data with extrapolated current week.
    """
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

def create_time_series_plot(data: pd.DataFrame, 
                            title: str,
                            y_axis_title: str,
                            color: str = '#1f77b4',
                            show_growth: bool = True) -> go.Figure:
    """
    Create a consistent time series plot with improved styling.
    
    Parameters:
        data (pd.DataFrame): DataFrame containing time series data.
        title (str): Title of the plot.
        y_axis_title (str): Label for the Y-axis.
        color (str, optional): Color of the plot line.
        show_growth (bool, optional): Whether to display growth metrics.
    
    Returns:
        go.Figure: Plotly figure object.
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
            f"<b>Growth:</b> {'+' if show_growth else ''}%{{customdata[0]:.1f}}%" if show_growth else "",
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
    Display weekly metrics with improved visualization.
    
    Parameters:
        data_df (pd.DataFrame): DataFrame containing the data.
        metric_name (str): Name of the metric to display.
        date_column (str, optional): Name of the date column.
        count_column (str, optional): Column to count unique values from.
        agg_function (str, optional): Aggregation function ('count', 'mean', 'unique_count').
        color (str, optional): Color for the plot.
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

def get_weekly_signups(users_df: pd.DataFrame, date_column: str = 'created_at') -> pd.DataFrame:
    """
    Assigns each data point to a fixed weekly interval starting from Sept 29, 2024.
    
    Parameters:
        users_df (pd.DataFrame): DataFrame containing user data.
        date_column (str, optional): Name of the date column.
    
    Returns:
        pd.DataFrame: Aggregated weekly signups data with extrapolation.
    """
    if users_df.empty:
        return pd.DataFrame()
    
    # Ensure datetime is UTC and copy the dataframe
    df = users_df.copy()
    df[date_column] = pd.to_datetime(df[date_column], utc=True)
    
    # Get current time and week boundary
    today = pd.Timestamp.now(tz='UTC')
    
    # Calculate the start of the current week (Sunday)
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
    
    # Separate current week and historical data using exact timestamp comparison
    current_week_mask = (df['week_start'] == current_week_start)
    current_week_data = df[current_week_mask]
    historical_data = df[~current_week_mask]
    
    # Process historical data
    weekly_signups = historical_data.groupby('week_start').size().reset_index(name='new_users')
    weekly_signups['is_extrapolated'] = False
    
    # Handle current week projection if we have data
    if not current_week_data.empty:
        # Get current week signup count
        current_signups = len(current_week_data)
        
        # Ensure we don't divide by zero
        days_elapsed = max(1, days_elapsed)
        
        # Extrapolate to full week
        estimated_signups = int(np.ceil((current_signups / days_elapsed) * 7))
        
        # Add current week as extrapolated data
        current_week_row = pd.DataFrame({
            'week_start': [current_week_start],
            'new_users': [estimated_signups],
            'is_extrapolated': [True]  # Always mark current week as extrapolated
        })
        
        weekly_signups = pd.concat([weekly_signups, current_week_row], ignore_index=True)
    
    return weekly_signups.sort_values('week_start', ascending=False)

def create_time_series_plot(data: pd.DataFrame, 
                            title: str,
                            y_axis_title: str,
                            color: str = '#1f77b4',
                            show_growth: bool = True) -> go.Figure:
    """
    Create a consistent time series plot with improved styling.
    
    Parameters:
        data (pd.DataFrame): DataFrame containing time series data.
        title (str): Title of the plot.
        y_axis_title (str): Label for the Y-axis.
        color (str, optional): Color of the plot line.
        show_growth (bool, optional): Whether to display growth metrics.
    
    Returns:
        go.Figure: Plotly figure object.
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
            f"<b>Growth:</b> {'+' if show_growth else ''}%{{customdata[0]:.1f}}%" if show_growth else "",
            "<extra></extra>"
        ]),
        customdata=data[['growth']] if show_growth else None,
        selector=dict(mode='lines+markers')
    )
    
    return fig

def calculate_retention(df: pd.DataFrame, date_column: str) -> pd.DataFrame:
    """
    Calculate historical retention rates.
    
    Parameters:
        df (pd.DataFrame): DataFrame containing user activity data.
        date_column (str): Name of the date column.
    
    Returns:
        pd.DataFrame: DataFrame containing retention rates per month.
    """
    # Calculate monthly user cohorts
    monthly_users = df.groupby([pd.Grouper(key=date_column, freq='M'), 'user_id']).size().reset_index()
    months = sorted(monthly_users[date_column].unique())
    
    retention_data = []
    for i in range(1, len(months)):
        current_month = months[i]
        previous_month = months[i-1]
        
        previous_users = set(monthly_users[monthly_users[date_column] == previous_month]['user_id'])
        current_users = set(monthly_users[monthly_users[date_column] == current_month]['user_id'])
        
        retained_users = len(previous_users.intersection(current_users))
        retention_rate = (retained_users / len(previous_users) * 100) if previous_users else 0
        
        retention_data.append({
            'date': current_month,
            'value': retention_rate
        })
    
    return pd.DataFrame(retention_data)

def calculate_current_month_retention(current_data: pd.DataFrame, 
                                     historical_data: pd.DataFrame, 
                                     date_column: str) -> float:
    """
    Calculate retention rate for the current month.
    
    Parameters:
        current_data (pd.DataFrame): DataFrame containing current month data.
        historical_data (pd.DataFrame): DataFrame containing historical data.
        date_column (str): Name of the date column.
    
    Returns:
        float: Retention rate percentage.
    """
    last_month = pd.Timestamp.now(tz='UTC').replace(day=1) - pd.Timedelta(days=1)
    last_month_users = set(historical_data[
        historical_data[date_column].dt.month == last_month.month
    ]['user_id'])
    current_users = set(current_data['user_id'])
    
    retained_users = len(last_month_users.intersection(current_users))
    return (retained_users / len(last_month_users) * 100) if last_month_users else 0

def get_extrapolated_weekly_data(df: pd.DataFrame, 
                                 date_column: str, 
                                 count_column: str = None, 
                                 agg_function: str = 'count') -> pd.DataFrame:
    """
    Calculate weekly data with extrapolation for the current week.
    
    Parameters:
        df (pd.DataFrame): DataFrame with the data.
        date_column (str): Name of the date column.
        count_column (str, optional): Column to count unique values from (optional).
        agg_function (str, optional): 'count', 'mean', 'unique_count'.
    
    Returns:
        pd.DataFrame: Aggregated weekly data with extrapolated current week.
    """
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

def display_new_user_signups_metric(users_df: pd.DataFrame):
    """
    Displays the New User Signups metric on the dashboard.
    
    Parameters:
        users_df (pd.DataFrame): DataFrame containing user data.
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
