# File: metrics/utils.py
import pandas as pd
import streamlit as st
import plotly.express as px

def get_week_boundaries():
    """
    Gets standardized week boundaries using Sunday as start of week.
    Returns current week start and today's date in UTC.
    """
    today = pd.Timestamp.now(tz='UTC')
    days_since_sunday = today.weekday() + 1  # +1 because weekday() has Monday as 0
    current_week_start = today - pd.Timedelta(days=days_since_sunday if days_since_sunday < 7 else 0)
    current_week_start = current_week_start.replace(hour=0, minute=0, second=0, microsecond=0)
    return current_week_start, today

def calculate_week_starts(df, date_column='created_at'):
    """
    Calculates week starts consistently for a dataframe.
    Uses Sunday as the start of each week.
    """
    if not pd.api.types.is_datetime64_any_dtype(df[date_column]):
        df = df.copy()
        df[date_column] = pd.to_datetime(df[date_column], utc=True)
    
    days_to_sunday = df[date_column].dt.weekday + 1
    week_starts = df[date_column] - pd.to_timedelta(days_to_sunday, unit='D')
    return week_starts.dt.normalize()  # normalize to midnight UTC

def create_weekly_plot(data: pd.DataFrame, 
                      title: str,
                      y_axis_title: str,
                      color: str = '#1f77b4'):
    """
    Creates a consistent weekly plot with proper styling.
    """
    fig = px.line(
        data,
        x='week_start',
        y='value',
        title=title,
        markers=True,
        color_discrete_sequence=[color]
    )
    
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
    
    # Style the current week differently
    for i, row in data.iterrows():
        if row['is_extrapolated']:
            fig.add_scatter(
                x=[row['week_start']],
                y=[row['value']],
                mode='markers',
                marker=dict(size=10, color=color, symbol='star'),
                name='Current Week',
                showlegend=True,
                hovertemplate="<br>".join([
                    "<b>Week Starting:</b> %{x|%Y-%m-%d}",
                    f"<b>{y_axis_title}:</b> %{{y}} (In Progress)",
                    "<extra></extra>"
                ])
            )
    
    return fig

def get_weekly_metrics(df: pd.DataFrame, 
                      date_column: str = 'created_at',
                      value_column: str = None,
                      agg_function: str = 'count') -> pd.DataFrame:
    """
    Calculates weekly metrics with consistent handling of current week.
    
    Parameters:
        df: DataFrame with the data
        date_column: Name of the date column
        value_column: Column to aggregate (optional)
        agg_function: 'count', 'unique_count', or 'mean'
    """
    if df.empty:
        return pd.DataFrame()
    
    # Calculate current week boundary
    current_week_start, today = get_week_boundaries()
    
    # Calculate week starts for all data points
    df = df.copy()
    df['week_start'] = calculate_week_starts(df, date_column)
    
    # Separate current week and historical data
    current_week_mask = (df['week_start'] == current_week_start)
    current_week_data = df[current_week_mask]
    historical_data = df[~current_week_mask]
    
    # Process historical data
    if agg_function == 'unique_count':
        weekly_data = historical_data.groupby('week_start')[value_column].nunique()
    elif agg_function == 'mean':
        weekly_data = historical_data.groupby(['week_start', value_column]).size().reset_index(name='count')
        weekly_data = weekly_data.groupby('week_start')['count'].mean()
    else:  # count
        weekly_data = historical_data.groupby('week_start').size()
    
    weekly_data = weekly_data.reset_index(name='value')
    weekly_data['is_extrapolated'] = False
    
    # Add current week data without projection
    if not current_week_data.empty:
        if agg_function == 'unique_count':
            current_value = current_week_data[value_column].nunique()
        elif agg_function == 'mean':
            current_value = current_week_data.groupby(value_column).size().mean()
        else:
            current_value = len(current_week_data)
        
        current_week_row = pd.DataFrame({
            'week_start': [current_week_start],
            'value': [current_value],
            'is_extrapolated': [True]
        })
        
        weekly_data = pd.concat([weekly_data, current_week_row], ignore_index=True)
    
    return weekly_data.sort_values('week_start', ascending=True)

def display_weekly_data(data: pd.DataFrame, metric_name: str, color: str = '#1f77b4'):
    """
    Displays weekly data with consistent formatting.
    """
    fig = create_weekly_plot(
        data,
        title=f'{metric_name} (Weekly)',
        y_axis_title=metric_name,
        color=color
    )
    
    st.plotly_chart(fig, use_container_width=True)
    
    st.subheader(f"Weekly {metric_name} Data")
    display_df = data.copy()
    display_df['Status'] = display_df['is_extrapolated'].map({True: '📊 In Progress', False: '✓ Complete'})
    display_df = display_df.drop('is_extrapolated', axis=1)
    display_df.columns = ['Week Starting', metric_name, 'Status']
    
    st.dataframe(
        display_df.sort_values('Week Starting', ascending=False),
        hide_index=True
    )

    