import pandas as pd
import streamlit as st
import plotly.express as px

def get_month_boundaries():
    """
    Gets standardized month boundaries.
    Returns current month start and today's date in UTC.
    """
    today = pd.Timestamp.now(tz='UTC')
    current_month_start = today.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    return current_month_start, today

def calculate_monthly_retention(df: pd.DataFrame, date_column: str = 'created_at', 
                              user_column: str = 'user_id') -> pd.DataFrame:
    """
    Calculates true retention rates - percentage of users who return from previous month.
    """
    if df.empty:
        return pd.DataFrame()
    
    # Get current month boundary
    current_month_start, today = get_month_boundaries()
    
    # Ensure datetime
    df = df.copy()
    df[date_column] = pd.to_datetime(df[date_column], utc=True)
    
    # Get month start for each timestamp
    df['month_start'] = df[date_column].dt.to_period('M').dt.to_timestamp()
    
    # Separate current month and historical data
    current_month_mask = (df['month_start'] == current_month_start)
    current_month_data = df[current_month_mask]
    historical_data = df[~current_month_mask]
    
    # Process historical months
    monthly_users = []
    
    # Get all unique months
    all_months = sorted(historical_data['month_start'].unique())
    
    # Calculate retention for each month
    for i in range(1, len(all_months)):
        current_month = all_months[i]
        previous_month = all_months[i-1]
        
        # Get users from both months
        previous_users = set(historical_data[historical_data['month_start'] == previous_month][user_column])
        current_users = set(historical_data[historical_data['month_start'] == current_month][user_column])
        
        if previous_users:  # Avoid division by zero
            # Calculate users who returned
            retained_users = len(previous_users.intersection(current_users))
            retention_rate = (retained_users / len(previous_users)) * 100
            
            monthly_users.append({
                'month_start': current_month,
                'retained_users': retained_users,
                'previous_users': len(previous_users),
                'retention_rate': retention_rate,
                'is_extrapolated': False
            })
    
    # Handle current month if we have data
    if not current_month_data.empty and all_months:
        last_month = all_months[-1]
        last_month_users = set(historical_data[historical_data['month_start'] == last_month][user_column])
        current_users = set(current_month_data[user_column])
        
        if last_month_users:  # Avoid division by zero
            retained_users = len(last_month_users.intersection(current_users))
            retention_rate = (retained_users / len(last_month_users)) * 100
            
            monthly_users.append({
                'month_start': current_month_start,
                'retained_users': retained_users,
                'previous_users': len(last_month_users),
                'retention_rate': retention_rate,
                'is_extrapolated': True
            })
    
    return pd.DataFrame(monthly_users)

def create_monthly_plot(data: pd.DataFrame, title: str, color: str = '#FFD700'):
    """
    Creates a consistent monthly plot for retention metrics.
    """
    fig = px.line(
        data,
        x='month_start',
        y='retention_rate',
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
        xaxis_title="Month",
        yaxis_title="Retention Rate (%)",
        height=600,
        xaxis=dict(tickangle=-45),
        yaxis=dict(range=[0, 100])
    )
    
    # Style the current month differently
    for i, row in data.iterrows():
        if row['is_extrapolated']:
            fig.add_scatter(
                x=[row['month_start']],
                y=[row['retention_rate']],
                mode='markers',
                marker=dict(size=10, color=color, symbol='star'),
                name='Current Month',
                showlegend=True,
                hovertemplate="<br>".join([
                    "<b>Month:</b> %{x|%B %Y}",
                    "<b>Retention Rate:</b> %{y:.1f}% (In Progress)",
                    "<extra></extra>"
                ])
            )
    
    return fig