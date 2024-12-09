from utils import display_monthly_metrics

def display_monthly_retention(streams_df):
    """
    Displays the User Retention metric on the dashboard.
    
    Parameters:
        streams_df (pd.DataFrame): DataFrame containing stream data.
    """
    display_monthly_metrics(
        streams_df,
        "User Retention",
        date_column='created_at',
        agg_function='retention',
        color='#FFD700'
    )
