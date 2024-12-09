from utils import display_weekly_metrics

def display_avg_streams_per_user(streams_df):
    """
    Displays the Average Streams per User metric on the dashboard.
    
    Parameters:
        streams_df (pd.DataFrame): DataFrame containing stream data.
    """
    display_weekly_metrics(
        streams_df,
        "Average Streams per User",
        date_column='created_at',
        count_column='user_id',
        agg_function='mean',
        color='orange'
    )
