from .weekly_intervals import display_weekly_metrics

def display_avg_streams_per_user(streams_df):
    display_weekly_metrics(
        streams_df,
        "Average Streams per User",
        'created_at',
        'user_id',
        'mean',
        color='orange'
    )