from .monthly_utils import display_monthly_metrics

def display_monthly_total_streams(streams_df):
    display_monthly_metrics(
        streams_df,
        "Total Streams",
        'created_at',
        color='#9c27b0'
    )