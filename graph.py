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

def display_metrics_dashboard(data_loader):
    """
    Main dashboard display function
    """
    # Add period selector
    period = st.radio("Select Period", ["Weekly", "Monthly"], horizontal=True)
    metrics = data_loader.weekly_metrics if period == "Weekly" else data_loader.monthly_metrics
    
    # Summary Cards Row
    st.subheader("Current Period Summary")
    col1, col2, col3 = st.columns(3)
    
    # Get most recent complete period's data
    current_period = datetime.now(timezone.utc)
    latest_metrics = {
        'active_users': metrics['active_users'].iloc[-2],  # -2 to get last complete period
        'avg_streams': metrics['avg_streams_per_user'].iloc[-2],
        'share_rate': metrics['share_rate'].iloc[-2] if 'share_rate' in metrics else 0
    }
    
    with col1:
        st.metric("Active Users", f"{latest_metrics['active_users']:,.0f}")
    with col2:
        st.metric("Avg Streams/User", f"{latest_metrics['avg_streams']:.1f}")
    with col3:
        st.metric("Share Rate", f"{latest_metrics['share_rate']:.1f}%")

    # User Activity Section
    st.header("User Activity")
    
    # Active Users Plot
    fig_active = create_metric_plot(
        metrics,
        'active_users',
        'Active Users Over Time',
        '#1f77b4'
    )
    st.plotly_chart(fig_active, use_container_width=True)
    
    # Average Streams per User Plot
    fig_streams = create_metric_plot(
        metrics,
        'avg_streams_per_user',
        'Average Streams per User',
        '#2ca02c'
    )
    st.plotly_chart(fig_streams, use_container_width=True)
    
    # Total Streams Plot
    fig_total = create_metric_plot(
        metrics,
        'total_streams',
        'Total Streams',
        '#ff7f0e'
    )
    st.plotly_chart(fig_total, use_container_width=True)
    
    # Highlight Engagement Section
    st.header("Highlight Engagement")
    
    # Like/Dislike Ratio Plot
    if 'like_ratio' in metrics:
        fig_likes = create_metric_plot(
            metrics,
            'like_ratio',
            'Like Ratio (%)',
            '#d62728'
        )
        st.plotly_chart(fig_likes, use_container_width=True)
    
    # Share Rate Plot
    if 'share_rate' in metrics:
        fig_shares = create_metric_plot(
            metrics,
            'share_rate',
            'Share Rate (%)',
            '#9467bd'
        )
        st.plotly_chart(fig_shares, use_container_width=True)