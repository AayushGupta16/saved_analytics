from .monthly_utils import display_monthly_metrics

def display_monthly_retention(streams_df):
    display_monthly_metrics(
        streams_df,
        "User Retention",
        'created_at',
        agg_function='retention',
        color='#FFD700'
    )