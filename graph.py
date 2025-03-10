import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timezone

def create_metric_plot(data, metric_name, title, color='#1f77b4'):
    """
    Creates a consistent plotly plot for any metric
    """
    if data.empty:
        return None
        
    fig = px.line(
        data.reset_index(),  # Reset index to make period_start a column
        x='period_start',
        y=metric_name,
        title=title,
        markers=True,
    )
    
    fig.update_traces(
        line_color=color,
        marker_color=color,
        marker_size=8
    )
    
    fig.update_layout(
        hovermode='x unified',
        hoverlabel=dict(
            bgcolor="white",
            font_size=14,
        ),
        title=dict(
            text=title,
            x=0.5,
            y=0.95,
            xanchor='center',
            yanchor='top',
            font_size=24
        ),
        xaxis_title="Period Start",
        yaxis_title=metric_name,
        height=400,
        showlegend=False
    )
    
    return fig

def create_dual_line_plot(data, metric1_name, metric2_name, title, color1='#1f77b4', color2='#ff7f0e'):
    """Creates a plotly plot with two lines"""
    if data.empty:
        return None
    
    fig = go.Figure()
    
    # Add first line
    fig.add_trace(go.Scatter(
        x=data.index,
        y=data[metric1_name],
        name='VOD',
        line=dict(color=color1),
        marker=dict(color=color1, size=8)
    ))
    
    # Add second line
    fig.add_trace(go.Scatter(
        x=data.index,
        y=data[metric2_name],
        name='Livestream',
        line=dict(color=color2),
        marker=dict(color=color2, size=8)
    ))
    
    fig.update_layout(
        hovermode='x unified',
        hoverlabel=dict(
            bgcolor="white",
            font_size=14,
        ),
        title=dict(
            text=title,
            x=0.5,
            y=0.95,
            xanchor='center',
            yanchor='top',
            font_size=24
        ),
        xaxis_title="Period Start",
        yaxis_title="Count",
        height=400,
        showlegend=True,
        legend=dict(
            yanchor="top",
            y=0.99,
            xanchor="left",
            x=0.01
        )
    )
    
    return fig

def display_metrics_dashboard(data_loader, period):
    """Display the metrics dashboard"""
    # Map selection to corresponding metrics
    metrics_map = {
        "Daily": data_loader.daily_metrics,
        "Weekly": data_loader.weekly_metrics,
        "Monthly": data_loader.monthly_metrics
    }
    
    metrics = metrics_map[period]
    
    # User Activity Section
    st.header("User Activity")
    
    # Active Users
    fig_active = create_metric_plot(
        metrics,
        'active_users',
        'Active Users Over Time',
        '#1f77b4'
    )
    if fig_active is not None:
        st.plotly_chart(fig_active, use_container_width=True)
    else:
        st.info("No active user data available for this period")
    
    # New Users
    if 'new_users' in metrics:
        fig_new = create_metric_plot(
            metrics,
            'new_users',
            'New User Sign-ups',
            '#2ca02c'
        )
        if fig_new is not None:
            st.plotly_chart(fig_new, use_container_width=True)
        else:
            st.info("No new user data available for this period")
    
    # Churn Rate
    if 'churn_rate' in metrics:
        fig_churn = create_metric_plot(
            metrics,
            'churn_rate',
            'User Churn Rate (%)',
            '#d62728'  # Red color
        )
        if fig_churn is not None:
            st.plotly_chart(fig_churn, use_container_width=True)
        else:
            st.info("No churn rate data available for this period")
    
    # Add Bot Sign-ups graph after New Users
    if 'new_bots' in metrics:
        fig_bots = create_metric_plot(
            metrics,
            'new_bots',
            'Bot Sign-ups',
            '#9467bd'  # Purple color
        )
        if fig_bots is not None:
            st.plotly_chart(fig_bots, use_container_width=True)
        else:
            st.info("No bot sign-up data available for this period")
    
    # Stream Activity Section
    st.header("Stream Activity")
    
    # Total Activity
    if 'total_streams' in metrics and 'total_livestreams' in metrics:
        fig_total = create_dual_line_plot(
            metrics,
            'total_streams',
            'total_livestreams',
            'Total Activity',
            '#1f77b4',
            '#ff7f0e'
        )
        if fig_total is not None:
            st.plotly_chart(fig_total, use_container_width=True)
        else:
            st.info("No total activity data available for this period")
    
    # Average Activity per User
    if 'avg_streams_per_user' in metrics and 'avg_livestreams_per_user' in metrics:
        fig_avg = create_dual_line_plot(
            metrics,
            'avg_streams_per_user',
            'avg_livestreams_per_user',
            'Average Activity per User',
            '#2ca02c',
            '#d62728'
        )
        if fig_avg is not None:
            st.plotly_chart(fig_avg, use_container_width=True)
        else:
            st.info("No average activity data available for this period")
    
    # URL Views Section
    st.header("URL Views")

    # Total URL Views
    if 'total_url_views' in metrics:
        fig_url_views = create_metric_plot(
            metrics,
            'total_url_views',
            'Total URL Views Over Time',
            '#17becf'  # Light blue color
        )
        if fig_url_views is not None:
            st.plotly_chart(fig_url_views, use_container_width=True)
        else:
            st.info("No URL view data available for this period")
    
    # Average Views per URL
    if 'avg_views_per_url' in metrics:
        fig_avg_views = create_metric_plot(
            metrics,
            'avg_views_per_url',
            'Average Views per URL',
            '#e377c2'  # Pink color
        )
        if fig_avg_views is not None:
            st.plotly_chart(fig_avg_views, use_container_width=True)
        else:
            st.info("No average URL views data available for this period")
    
    # Percentage of URLs with Views
    if 'urls_with_views_percent' in metrics:
        fig_url_percent = create_metric_plot(
            metrics,
            'urls_with_views_percent',
            'Percentage of URLs with Views',
            '#7f7f7f'  # Gray color
        )
        if fig_url_percent is not None:
            st.plotly_chart(fig_url_percent, use_container_width=True)
        else:
            st.info("No URL percentage data available for this period")
    
    # Highlight Engagement Section
    st.header("Highlight Engagement")
    
    # Like Ratio
    if 'vod_like_ratio' in metrics and 'live_like_ratio' in metrics:
        fig_likes = create_dual_line_plot(
            metrics,
            'vod_like_ratio',
            'live_like_ratio',
            'Like Ratio (%)',
            '#9467bd',
            '#8c564b'
        )
        if fig_likes is not None:
            st.plotly_chart(fig_likes, use_container_width=True)
        else:
            st.info("No like ratio data available for this period")
    
    # Share Rate
    if 'vod_share_rate' in metrics and 'live_share_rate' in metrics:
        fig_shares = create_dual_line_plot(
            metrics,
            'vod_share_rate',
            'live_share_rate',
            'Share Rate (%)',
            '#e377c2',
            '#7f7f7f'
        )
        if fig_shares is not None:
            st.plotly_chart(fig_shares, use_container_width=True)
        else:
            st.info("No share rate data available for this period")
    
    # Downloaded Highlights
    if 'vod_downloads' in metrics and 'livestream_downloads' in metrics:
        fig_downloads = create_dual_line_plot(
            metrics,
            'vod_downloads',
            'livestream_downloads',
            'Downloaded Highlights',
            '#bcbd22',
            '#17becf'
        )
        if fig_downloads is not None:
            st.plotly_chart(fig_downloads, use_container_width=True)
        else:
            st.info("No downloaded highlights data available for this period")