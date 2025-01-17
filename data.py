import pandas as pd
from supabase import create_client
from datetime import datetime, timedelta

class AnalyticsDataLoader:
    def __init__(self, supabase_url, supabase_key, developer_ids):
        self.supabase = create_client(supabase_url, supabase_key)
        self.developer_ids = developer_ids
        self.weekly_metrics = {}
        self.monthly_metrics = {}
        
    def _get_first_sunday(self, df):
        """Get the first Sunday after the earliest data point"""
        if df.empty:
            return None
        
        earliest_date = df['created_at'].min()
        days_until_sunday = (6 - earliest_date.weekday()) % 7
        first_sunday = earliest_date + timedelta(days=days_until_sunday)
        return first_sunday.replace(hour=0, minute=0, second=0, microsecond=0)
    
    def _load_raw_data(self):
        """Load and clean data from Supabase"""
        # Load streams and highlights
        streams_data = self.supabase.from_('Streams').select('*').execute()
        highlights_data = self.supabase.from_('Highlights').select('*').execute()
        
        # Convert to dataframes
        streams_df = pd.DataFrame(streams_data.data)
        highlights_df = pd.DataFrame(highlights_data.data)
        
        # Filter out developer data
        if not streams_df.empty:
            streams_df = streams_df[~streams_df['user_id'].isin(self.developer_ids)]
        if not highlights_df.empty:
            highlights_df = highlights_df[~highlights_df['user_id'].isin(self.developer_ids)]
            
        # Convert timestamps
        for df in [streams_df, highlights_df]:
            if not df.empty:
                df['created_at'] = pd.to_datetime(df['created_at'], utc=True)
                
        return streams_df, highlights_df

    def _calculate_metrics(self, interval='week'):
        """Calculate all metrics for given interval"""
        streams_df, highlights_df = self._load_raw_data()
        
        if streams_df.empty and highlights_df.empty:
            return pd.DataFrame()  # Return empty DataFrame instead of dict
            
        # Determine period starts
        if interval == 'week':
            # Align to Sunday-Saturday
            streams_df['period_start'] = streams_df['created_at'].dt.to_period('W-SAT').dt.start_time
            if not highlights_df.empty:
                highlights_df['period_start'] = highlights_df['created_at'].dt.to_period('W-SAT').dt.start_time
        else:  # month
            streams_df['period_start'] = streams_df['created_at'].dt.to_period('M').dt.start_time
            if not highlights_df.empty:
                highlights_df['period_start'] = highlights_df['created_at'].dt.to_period('M').dt.start_time

        metrics = {}
        
        # Calculate metrics per period
        grouped_streams = streams_df.groupby('period_start')
        metrics['active_users'] = grouped_streams['user_id'].nunique()
        metrics['total_streams'] = grouped_streams.size()
        metrics['avg_streams_per_user'] = (metrics['total_streams'] / metrics['active_users']).round(4)
        
        if not highlights_df.empty:
            # Only include rated highlights
            rated_highlights = highlights_df[highlights_df['liked'].notna()]
            if not rated_highlights.empty:
                grouped_highlights = rated_highlights.groupby('period_start')
                likes = grouped_highlights['liked'].apply(lambda x: (x == True).sum())
                total_rated = grouped_highlights.size()
                metrics['like_ratio'] = ((likes / total_rated) * 100).round(4)
            
            # Calculate share rate
            highlights_df['is_shared'] = (highlights_df['downloaded'] | highlights_df['link_copied'])
            grouped_shares = highlights_df.groupby('period_start')
            shares = grouped_shares['is_shared'].sum()
            total_highlights = grouped_shares.size()
            metrics['share_rate'] = ((shares / total_highlights) * 100).round(4)
        
        # Convert to DataFrame
        metrics_df = pd.DataFrame(metrics)
        metrics_df.index.name = 'period_start'  # Set index name
        return metrics_df

    def load_all_metrics(self):
        """Load both weekly and monthly metrics"""
        self.weekly_metrics = self._calculate_metrics('week')
        self.monthly_metrics = self._calculate_metrics('month')