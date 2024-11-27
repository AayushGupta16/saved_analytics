from supabase import create_client
import streamlit as st
import pandas as pd
from datetime import datetime, timedelta, timezone
import matplotlib.pyplot as plt
from matplotlib.dates import DateFormatter
import plotly.express as px
import plotly.graph_objects as go
import numpy as np
import os
from dotenv import load_dotenv

load_dotenv()

def get_weekly_intervals(df, date_column, count_column=None):
    if df.empty:
        return pd.DataFrame()
    
    # Convert timestamps to datetime
    df = df.copy()
    df[date_column] = pd.to_datetime(df[date_column])
    
    # Get the most recent date and generate intervals backwards
    end_date = df[date_column].max()
    # Round to nearest day
    end_date = end_date.replace(hour=0, minute=0, second=0, microsecond=0)
    
    # Generate list of dates at 7-day intervals
    dates = []
    counts = []
    current_date = end_date
    
    while current_date >= df[date_column].min():
        interval_start = current_date - timedelta(days=6)  # Get data for previous 7 days
        
        mask = (df[date_column] > interval_start) & (df[date_column] <= current_date)
        if count_column:
            count = df[mask][count_column].nunique()
        else:
            count = len(df[mask])
            
        dates.append(current_date)
        counts.append(count)
        current_date -= timedelta(days=7)
    
    return pd.DataFrame({
        'date': dates,
        'count': counts
    })

def get_avg_streams_per_user(df, date_column):
    if df.empty:
        return pd.DataFrame()
    
    # Convert timestamps to datetime
    df = df.copy()
    df[date_column] = pd.to_datetime(df[date_column])
    
    # Get the most recent date and generate intervals backwards
    end_date = df[date_column].max()
    # Round to nearest day
    end_date = end_date.replace(hour=0, minute=0, second=0, microsecond=0)
    
    # Generate list of dates at 7-day intervals
    dates = []
    avgs = []
    current_date = end_date
    
    while current_date >= df[date_column].min():
        interval_start = current_date - timedelta(days=6)  # Get data for previous 7 days
        
        mask = (df[date_column] > interval_start) & (df[date_column] <= current_date)
        period_data = df[mask]
        
        if not period_data.empty:
            # Count streams per user for this period
            streams_per_user = period_data.groupby('user_id').size()
            avg_streams = streams_per_user.mean()
            # Truncate to 2 decimal places
            avg_streams = np.floor(avg_streams * 100) / 100
        else:
            avg_streams = 0
            
        dates.append(current_date)
        avgs.append(avg_streams)
        current_date -= timedelta(days=7)
    
    return pd.DataFrame({
        'date': dates,
        'avg_streams': avgs
    })

def get_monthly_total_streams(streams_df, date_column='created_at'):
    if streams_df.empty:
        return pd.DataFrame()
    
    df = streams_df.copy()
    df[date_column] = pd.to_datetime(df[date_column])
    
    monthly_totals = df.groupby(pd.Grouper(key=date_column, freq='ME')).size().reset_index()
    monthly_totals.columns = ['date', 'total_streams']
    
    monthly_totals['mom_growth'] = monthly_totals['total_streams'].pct_change() * 100
    monthly_totals['mom_growth'] = monthly_totals['mom_growth'].round(2)
    
    return monthly_totals

def get_monthly_active_users(streams_df, date_column='created_at'):
    if streams_df.empty:
        return pd.DataFrame()
    
    df = streams_df.copy()
    df[date_column] = pd.to_datetime(df[date_column])
    
    monthly_users = df.groupby(pd.Grouper(key=date_column, freq='ME'))['user_id'].nunique().reset_index()
    monthly_users.columns = ['date', 'total_users']
    
    monthly_users['mom_growth'] = monthly_users['total_users'].pct_change() * 100
    monthly_users['mom_growth'] = monthly_users['mom_growth'].round(2)
    
    return monthly_users

def get_monthly_retention(streams_df, date_column='created_at'):
    if streams_df.empty:
        return pd.DataFrame()
    
    df = streams_df.copy()
    df[date_column] = pd.to_datetime(df[date_column])
    
    # Get user activity by month
    user_monthly = df.groupby([pd.Grouper(key=date_column, freq='M'), 'user_id']).size().reset_index()
    
    retention_data = []
    months = sorted(user_monthly[date_column].unique())
    
    for i in range(1, len(months)):
        current_month = months[i]
        previous_month = months[i-1]
        
        # Get users in previous month
        previous_users = set(user_monthly[user_monthly[date_column] == previous_month]['user_id'])
        
        # Get users in current month
        current_users = set(user_monthly[user_monthly[date_column] == current_month]['user_id'])
        
        # Find retained users (users from previous month who are also in current month)
        retained_users = len(previous_users.intersection(current_users))
        previous_users_count = len(previous_users)
        
        # Calculate retention rate
        retention_rate = (retained_users / previous_users_count * 100) if previous_users_count > 0 else 0
        
        retention_data.append({
            'date': current_month,
            'retention_rate': round(retention_rate, 2),
            'retained_count': retained_users,
            'previous_month_count': previous_users_count
        })
    
    retention_df = pd.DataFrame(retention_data)
    
    # Calculate MoM growth in retention rate
    if not retention_df.empty:
        retention_df['mom_growth'] = retention_df['retention_rate'].pct_change() * 100
        retention_df['mom_growth'] = retention_df['mom_growth'].round(2)
    
    return retention_df

def create_analytics_dashboard():
    # Initialize Supabase client
    supabase_url = st.secrets["env"]["SUPABASE_URL"]
    supabase_key = st.secrets["env"]["SUPABASE_KEY"]
    supabase = create_client(supabase_url, supabase_key)

    # List of developer user IDs to exclude
    developer_ids = st.secrets["env"]["DEVELOPER_IDS"].split(',')

    try:
        # Fetch data from all tables
        streams = pd.DataFrame(supabase.from_('Streams').select('*').execute().data)
        highlights = pd.DataFrame(supabase.from_('Highlights').select('*').execute().data)
        users = pd.DataFrame(supabase.from_('Users').select('*').execute().data)

        # Filter out developer data
        streams = streams[~streams['user_id'].isin(developer_ids)]
        highlights = highlights[~highlights['user_id'].isin(developer_ids)]
        users = users[~users['user_id'].isin(developer_ids)]

        st.title('Platform Analytics (Excluding Developer Activity)')

        # Convert timestamps to datetime
        streams['created_at'] = pd.to_datetime(streams['created_at'])
        users['created_at'] = pd.to_datetime(users['created_at'])

        # General Metrics Section
        st.header('General Metrics')
        col1, col2, col3, col4 = st.columns(4)

        # 1. Average streams per week per user
        if not streams.empty:
            # Get the most recent average by using the same function
            avg_streams_data = get_avg_streams_per_user(streams, 'created_at')
            if not avg_streams_data.empty:
                # Get the most recent average
                latest_avg = avg_streams_data.iloc[0]['avg_streams']
                col1.metric("Avg Streams/Week/User", f"{latest_avg}")
            else:
                col1.metric("Avg Streams/Week/User", "0")
        else:
            col1.metric("Avg Streams/Week/User", "No data")
        

        if not streams.empty:
            monthly_streams = get_monthly_total_streams(streams)
            st.header('Monthly Total Streams')
            total_streams = len(streams)
            col2.metric("Total Streams Processed", total_streams)
            
            fig = px.line(
                monthly_streams,
                x='date',
                y='total_streams',
                text='mom_growth',  # Add this line to include the text data
                title='Monthly Total Streams with MoM Growth',
                markers=True,
                color_discrete_sequence=['#9c27b0']
            )
            
            fig.update_layout(
                hovermode='x',
                hoverlabel=dict(
                    bgcolor="white",
                    font=dict(
                        color="black",
                        size=14
                    ),
                    bordercolor="black"
                ),
                title=dict(
                    text='Monthly Total Streams with MoM Growth',
                    x=0.5,
                    y=0.95,
                    xanchor='center',
                    yanchor='top',
                    font=dict(
                        size=24
                    )
                ),
                xaxis_title="Date",
                yaxis_title="Total Streams",
                height=600,
                xaxis=dict(tickangle=-45)
            )
            
            fig.update_traces(
                line=dict(width=2, color='#9c27b0'),
                marker=dict(size=10, color='#9c27b0'),
                texttemplate="+%{text:.1f}%",
                textposition="top center",
                textfont=dict(size=14),
                hovertemplate="<br>".join([
                    "<b>Date:</b> %{x|%Y-%m-%d}",
                    "<b>Monthly Streams:</b> %{y}",
                    "<b>MoM Growth:</b> %{text:.1f}%",
                    "<extra></extra>"
                ])
            )
            
            st.plotly_chart(fig, use_container_width=True)
            st.dataframe(monthly_streams.sort_values('date', ascending=False))

        # 3. Total Users
        if not users.empty:
            total_users = len(users)
            col3.metric("Total Users", total_users)
        else:
            col3.metric("Premium Users", premium_users)

        # Premium Users Count
        if not users.empty:
            premium_users = users[users['is_paying'] == True].shape[0]
            col4.metric("Premium Users", premium_users)
        else:
            col4.metric("Premium Users", "No data")

        # Average Streams per User by 7-Day Intervals
        st.header('Average Streams per User (7-Day Intervals)')
        if not streams.empty:
            avg_streams_data = get_avg_streams_per_user(streams, 'created_at')
            
            fig = px.line(
                avg_streams_data,
                x='date',
                y='avg_streams',
                title='Average Streams per User (7-Day Intervals)',
                markers=True,
                color_discrete_sequence=['orange']
            )
            
            fig.update_layout(
                hovermode='x',
                hoverlabel=dict(
                    bgcolor="white",
                    font=dict(
                        color="black",
                        size=14
                    ),
                    bordercolor="black"
                ),
                title=dict(
                    text='Average Streams per User (7-Day Intervals)',
                    x=0.5,
                    y=0.95,
                    xanchor='center',
                    yanchor='top',
                    font=dict(
                        size=24
                    )
                ),
                xaxis_title="Date",
                yaxis_title="Average Streams per User",
                height=600,
                xaxis=dict(tickangle=-45)
            )
            
            fig.update_traces(
                line=dict(width=2, color='orange'),
                marker=dict(size=10, color='orange'),
                hovertemplate="<br>".join([
                    "<b>Date:</b> %{x|%Y-%m-%d}",
                    "<b>Avg Streams per User:</b> %{y:.2f}",
                    "<extra></extra>"
                ])
            )
            
            st.plotly_chart(fig, use_container_width=True)
            
            st.subheader("7-Day Interval Average Streams per User Data")
            st.dataframe(avg_streams_data.sort_values('date', ascending=False))
            
        # Time Series Analysis - Weekly Intervals
        st.header('Activity Over Time (7-Day Intervals)')
        if not streams.empty:
            weekly_activity = get_weekly_intervals(streams, 'created_at')
            
            fig = px.line(
                weekly_activity, 
                x='date',
                y='count',
                title='Stream Count (7-Day Intervals)',
                markers=True
            )
            
            fig.update_layout(
                hovermode='x',
                hoverlabel=dict(
                    bgcolor="white",
                    font=dict(
                        color="black",
                        size=14
                    ),
                    bordercolor="black"
                ),
                title=dict(
                    text='Stream Count (7-Day Intervals)',
                    x=0.5,
                    y=0.95,
                    xanchor='center',
                    yanchor='top',
                    font=dict(
                        size=24
                    )
                ),
                xaxis_title="Date",
                yaxis_title="Number of Streams",
                height=600,
                xaxis=dict(tickangle=-45)
            )

            fig.update_traces(
                line=dict(width=2),
                marker=dict(size=10),
                hovertemplate="<br>".join([
                    "<b>Date:</b> %{x|%Y-%m-%d}",
                    "<b>Streams:</b> %{y}",
                    "<extra></extra>"
                ])
            )
            
            st.plotly_chart(fig, use_container_width=True)
            
            st.subheader("7-Day Interval Stream Data")
            st.dataframe(weekly_activity.sort_values('date', ascending=False))

        #MoM Active Users
        if not streams.empty:
            monthly_users = get_monthly_active_users(streams)
            st.header('Monthly Active Users')

            fig = px.line(
                monthly_users,
                x='date',
                y='total_users',
                text='mom_growth',
                title='Monthly Active Users with MoM Growth',
                markers=True,
                color_discrete_sequence=['#FF69B4']
            )
            
            fig.update_layout(
                hovermode='x',
                hoverlabel=dict(
                    bgcolor="white",
                    font=dict(
                        color="black",
                        size=14
                    ),
                    bordercolor="black"
                ),
                title=dict(
                    text='Monthly Active Users with MoM Growth',
                    x=0.5,
                    y=0.95,
                    xanchor='center',
                    yanchor='top',
                    font=dict(
                        size=24
                    )
                ),
                xaxis_title="Date",
                yaxis_title="Total Active Users",
                height=600,
                xaxis=dict(tickangle=-45)
            )
            
            fig.update_traces(
                line=dict(width=2, color='#FF69B4'),
                marker=dict(size=10, color='#FF69B4'),
                texttemplate="+%{text:.1f}%",
                textposition="top center",
                textfont=dict(size=14),
                hovertemplate="<br>".join([
                    "<b>Date:</b> %{x|%Y-%m-%d}",
                    "<b>Monthly Active Users:</b> %{y}",
                    "<b>MoM Growth:</b> %{text:.1f}%",
                    "<extra></extra>"
                ])
            )
            
            st.plotly_chart(fig, use_container_width=True)
            st.dataframe(monthly_users.sort_values('date', ascending=False))

        # Active Users by 7-Day Intervals
        st.header('Active Users (7-Day Intervals)')
        if not streams.empty:
            weekly_users = get_weekly_intervals(streams, 'created_at', 'user_id')
            
            fig = px.line(
                weekly_users,
                x='date',
                y='count',
                title='Active Users (7-Day Intervals)',
                markers=True,
                color_discrete_sequence=['red']
            )
            
            fig.update_layout(
                hovermode='x',
                hoverlabel=dict(
                    bgcolor="white",
                    font=dict(
                        color="black",
                        size=14
                    ),
                    bordercolor="black"
                ),
                title=dict(
                    text='Active Users (7-Day Intervals)',
                    x=0.5,
                    y=0.95,
                    xanchor='center',
                    yanchor='top',
                    font=dict(
                        size=24
                    )
                ),
                xaxis_title="Date",
                yaxis_title="Number of Active Users",
                height=600,
                xaxis=dict(tickangle=-45)
            )
            
            fig.update_traces(
                line=dict(width=2, color='red'),
                marker=dict(size=10, color='red'),
                hovertemplate="<br>".join([
                    "<b>Date:</b> %{x|%Y-%m-%d}",
                    "<b>Active Users:</b> %{y}",
                    "<extra></extra>"
                ])
            )
            
            st.plotly_chart(fig, use_container_width=True)
            
            st.subheader("7-Day Interval Active Users Data")
            st.dataframe(weekly_users.sort_values('date', ascending=False))

        #Retention
        if not streams.empty:
            monthly_retention = get_monthly_retention(streams)
            st.header('Monthly Retention')
                
            fig = px.line(
                monthly_retention,
                x='date',
                y='retention_rate',
                text='mom_growth',
                title='Monthly Retention with MoM Growth',
                markers=True,
                color_discrete_sequence=['#FFD700']
            )

            fig.update_layout(
                hovermode='x',
                hoverlabel=dict(
                    bgcolor="white",
                    font=dict(
                        color="black",
                        size=14
                    ),
                    bordercolor="black"
                ),
                title=dict(
                    text='Monthly Retention with MoM Growth',
                    x=0.5,
                    y=0.95,
                    xanchor='center',
                    yanchor='top',
                    font=dict(
                        size=24
                    )
                ),
                xaxis_title="Date",
                yaxis_title="Retention Rate (%)",
                height=600,
                xaxis=dict(tickangle=-45)
            )

            fig.update_traces(
                line=dict(width=2, color='#FFD700'),
                marker=dict(size=10, color='#FFD700'),
                texttemplate="<br>".join([
                    "%{text:.1f}%" if "%{text}" != "nan" else ""  # Don't show anything for NaN values
                ]),
                textposition="top center",
                textfont=dict(size=14),
                hovertemplate="<br>".join([
                    "<b>Date:</b> %{x|%Y-%m-%d}",
                    "<b>Retention Rate:</b> %{y:.1f}%",
                    "<b>Previous Month Users:</b> %{customdata[0]}",
                    "<b>Retained Users:</b> %{customdata[1]}",
                    "<b>MoM Growth:</b> %{text:.1f}%" if "%{text}" != "nan" else "<b>MoM Growth:</b> N/A",
                    "<extra></extra>"
                ]),
                customdata=monthly_retention[['previous_month_count', 'retained_count']]
            )

            st.plotly_chart(fig, use_container_width=True)
            st.dataframe(monthly_retention.sort_values('date', ascending=False))

        # New Users by 7-Day Intervals
        st.header('New User Signups (7-Day Intervals)')
        if not users.empty:
            weekly_signups = get_weekly_intervals(users, 'created_at')
            
            fig = px.line(
                weekly_signups,
                x='date',
                y='count',
                title='New User Signups (7-Day Intervals)',
                markers=True,
                color_discrete_sequence=['green']
            )
            
            fig.update_layout(
                hovermode='x',
                hoverlabel=dict(
                    bgcolor="white",
                    font=dict(
                        color="black",
                        size=14
                    ),
                    bordercolor="black"
                ),
                title=dict(
                    text='New User Signups (7-Day Intervals)',
                    x=0.5,
                    y=0.95,
                    xanchor='center',
                    yanchor='top',
                    font=dict(
                        size=24
                    )
                ),
                xaxis_title="Date",
                yaxis_title="Number of New Users",
                height=600,
                xaxis=dict(tickangle=-45)
            )
            
            fig.update_traces(
                line=dict(width=2, color='green'),
                marker=dict(size=10, color='green'),
                hovertemplate="<br>".join([
                    "<b>Date:</b> %{x|%Y-%m-%d}",
                    "<b>New Users:</b> %{y}",
                    "<extra></extra>"
                ])
            )
            
            st.plotly_chart(fig, use_container_width=True)
            
            st.subheader("7-Day Interval New Users Data")
            st.dataframe(weekly_signups.sort_values('date', ascending=False))

    except Exception as e:
        st.error(f"An error occurred: {str(e)}")
        st.write("Please check your database connection and try again.")


if __name__ == "__main__":
    create_analytics_dashboard()