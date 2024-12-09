from utils import display_monthly_metrics

def display_monthly_active_users(streams_df):
    """
    Displays the Monthly Active Users (MAU) metric on the dashboard.
    
    Parameters:
        streams_df (pd.DataFrame): DataFrame containing stream data.
    """
    display_monthly_metrics(
        streams_df,
        "Active Users",
        date_column='created_at',
        count_column='user_id',
        agg_function='unique_count',
        color='#FF69B4'
    )
