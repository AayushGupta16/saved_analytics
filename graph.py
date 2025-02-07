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

def display_metrics_dashboard(data_loader):
    """Display the metrics dashboard"""
    metrics = data_loader.weekly_metrics
    
    # User Activity Section
    st.header("User Activity")
    
    # Active Users
    fig_active = create_metric_plot(
        metrics,
        'active_users',
        'Active Users Over Time',
        '#1f77b4'
    )
    st.plotly_chart(fig_active, use_container_width=True)
    
    # New Users
    if 'new_users' in metrics:
        fig_new = create_metric_plot(
            metrics,
            'new_users',
            'New User Sign-ups',
            '#2ca02c'
        )
        st.plotly_chart(fig_new, use_container_width=True)
    
    # Add Bot Sign-ups graph after New Users
    if 'new_bots' in metrics:
        fig_bots = create_metric_plot(
            metrics,
            'new_bots',
            'Bot Sign-ups',
            '#9467bd'  # Purple color
        )
        st.plotly_chart(fig_bots, use_container_width=True)
    
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
        st.plotly_chart(fig_total, use_container_width=True)
    
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
        st.plotly_chart(fig_avg, use_container_width=True)
    
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
        st.plotly_chart(fig_likes, use_container_width=True)
    
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
        st.plotly_chart(fig_shares, use_container_width=True)
    
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
        st.plotly_chart(fig_downloads, use_container_width=True)