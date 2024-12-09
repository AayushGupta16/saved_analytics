from .monthly_utils import display_monthly_metrics

def display_monthly_active_users(streams_df):
    display_monthly_metrics(
        streams_df,
        "Active Users",
        'created_at',
        'user_id',
        'unique_count',
        color='#FF69B4'
    )