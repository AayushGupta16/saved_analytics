from utils import display_weekly_metrics

def display_weekly_streams(streams_df):
    """
    Displays the Weekly Stream Counts metric on the dashboard.
    
    Parameters:
        streams_df (pd.DataFrame): DataFrame containing stream data.
    """
    display_weekly_metrics(
        streams_df,
        "Stream Count",
        date_column='created_at',
        color='#1f77b4'
    )
    

def display_weekly_active_users(streams_df):
    """
    Displays the Weekly Active Users metric on the dashboard.
    
    Parameters:
        streams_df (pd.DataFrame): DataFrame containing stream data.
    """
    display_weekly_metrics(
        streams_df,
        "Active Users",
        date_column='created_at',
        count_column='user_id',
        agg_function='unique_count',
        color='#ff7f0e'
    )
