import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go  # Add this line
from datetime import datetime, timezone
import numpy as np


def get_extrapolated_monthly_data(df: pd.DataFrame, 
                                  date_column: str, 
                                  count_column: str = None, 
                                  agg_function: str = 'count') -> pd.DataFrame:
    """
    Calculate monthly data with clear extrapolation for the current month.
    
    Parameters:
        df: DataFrame with the data
        date_column: Name of the date column
        count_column: Column to count unique values from (optional)
        agg_function: 'count', 'mean', 'unique_count', or 'retention'
    """
    if df.empty:
        return pd.DataFrame()
    
    # Ensure datetime is UTC
    df = df.copy()
    df[date_column] = pd.to_datetime(df[date_column], utc=True)
    
    # Get current month information
    today = pd.Timestamp.now(tz='UTC')
    current_month_start = today.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    days_in_month = today.days_in_month  # Updated line
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
                        show_growth: bool = True) -> go.Figure:  # Updated type annotation
    """
    Create a consistent monthly plot with improved styling
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
            f"<b>MoM Growth:</b> {'+' if show_growth else ''}" + "%{customdata[0]:.1f}%" if show_growth else "",
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
    Display monthly metrics with improved visualization
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

# Helper function for retention calculations
def calculate_retention(df: pd.DataFrame, date_column: str) -> pd.DataFrame:
    """Calculate historical retention rates"""
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
    """Calculate retention rate for the current month"""
    last_month = pd.Timestamp.now(tz='UTC').replace(day=1) - pd.Timedelta(days=1)
    last_month_users = set(historical_data[
        historical_data[date_column].dt.month == last_month.month
    ]['user_id'])
    current_users = set(current_data['user_id'])
    
    retained_users = len(last_month_users.intersection(current_users))
    return (retained_users / len(last_month_users) * 100) if last_month_users else 0