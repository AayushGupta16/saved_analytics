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
        try:
            # Pagination logic for Streams, Highlights, and Livestreams
            streams_data = []
            highlights_data = []
            livestreams_data = []

            # Fetch streams in batches
            batch_size = 1000
            offset = 0
            while True:
                response = self.supabase.from_('Streams').select('*').limit(batch_size).offset(offset).execute()
                if not response.data:
                    break
                streams_data.extend(response.data)
                offset += batch_size

            # Fetch highlights in batches
            offset = 0
            while True:
                response = self.supabase.from_('Highlights').select('*').limit(batch_size).offset(offset).execute()
                if not response.data:
                    break
                highlights_data.extend(response.data)
                offset += batch_size

            # Fetch livestreams in batches
            offset = 0
            while True:
                response = self.supabase.from_('Livestreams').select('*').limit(batch_size).offset(offset).execute()
                if not response.data:
                    break
                livestreams_data.extend(response.data)
                offset += batch_size

            # Convert to dataframes
            streams_df = pd.DataFrame(streams_data)
            highlights_df = pd.DataFrame(highlights_data)
            livestreams_df = pd.DataFrame(livestreams_data)
            
            # Debugging: Log counts of rows retrieved
            print(f"Total Streams data count: {len(streams_df)}")
            print(f"Total Highlights data count: {len(highlights_df)}")
            print(f"Total Livestreams data count: {len(livestreams_df)}")

            # Filter out developer data
            if not streams_df.empty:
                streams_df = streams_df[~streams_df['user_id'].isin(self.developer_ids)]
            if not highlights_df.empty:
                highlights_df = highlights_df[~highlights_df['user_id'].isin(self.developer_ids)]
            if not livestreams_df.empty:
                livestreams_df = livestreams_df[~livestreams_df['user_id'].isin(self.developer_ids)]

            # Convert timestamps
            for df in [streams_df, highlights_df, livestreams_df]:
                if not df.empty:
                    df['created_at'] = pd.to_datetime(df['created_at'], utc=True)
                    df['created_at'] = df['created_at'].dt.tz_localize(None)  # Remove timezone information
                    print(df[['created_at']].head())  # Debugging: Log a sample of timestamps
                    
            return streams_df, highlights_df, livestreams_df
        except Exception as e:
            print(f"Error loading data: {e}")
            return pd.DataFrame(), pd.DataFrame(), pd.DataFrame()

    def _calculate_metrics(self, interval='week'):
        """Calculate all metrics for given interval"""
        streams_df, highlights_df, livestreams_df = self._load_raw_data()
        
        if streams_df.empty and highlights_df.empty and livestreams_df.empty:
            return pd.DataFrame()
            
        # Determine period starts
        if interval == 'week':
            streams_df['period_start'] = streams_df['created_at'].dt.to_period('W-SAT').dt.start_time
            if not highlights_df.empty:
                highlights_df['period_start'] = highlights_df['created_at'].dt.to_period('W-SAT').dt.start_time
            if not livestreams_df.empty:
                livestreams_df['period_start'] = livestreams_df['created_at'].dt.to_period('W-SAT').dt.start_time
        else:  # month
            streams_df['period_start'] = streams_df['created_at'].dt.to_period('M').dt.start_time
            if not highlights_df.empty:
                highlights_df['period_start'] = highlights_df['created_at'].dt.to_period('M').dt.start_time
            if not livestreams_df.empty:
                livestreams_df['period_start'] = livestreams_df['created_at'].dt.to_period('M').dt.start_time

        metrics = {}
        
        # User Activity Metrics
        if not streams_df.empty or not livestreams_df.empty:
            # Get all user activity periods
            all_activity = pd.DataFrame()
            
            if not streams_df.empty:
                all_activity = pd.concat([all_activity, 
                    streams_df[['user_id', 'period_start']]
                ])
            
            if not livestreams_df.empty:
                all_activity = pd.concat([all_activity, 
                    livestreams_df[['user_id', 'period_start']]
                ])
            
            # Calculate active users from combined activity
            grouped_activity = all_activity.groupby('period_start')
            metrics['active_users'] = grouped_activity['user_id'].nunique()
            
            # New Users (based on first activity)
            first_activity = all_activity.groupby('user_id')['period_start'].min().reset_index()
            new_users_series = first_activity.groupby('period_start').size()
            metrics['new_users'] = new_users_series.reindex(metrics['active_users'].index, fill_value=0)
            
        # Stream Metrics
        if not streams_df.empty:
            grouped_streams = streams_df.groupby('period_start')
            metrics['total_streams'] = grouped_streams.size()
            metrics['avg_streams_per_user'] = (metrics['total_streams'] / metrics['active_users']).round(4)

        # Livestream Metrics
        if not livestreams_df.empty:
            grouped_livestreams = livestreams_df.groupby('period_start')
            metrics['total_livestreams'] = grouped_livestreams.size()
            livestream_users = grouped_livestreams['user_id'].nunique()
            metrics['avg_livestreams_per_user'] = (metrics['total_livestreams'] / livestream_users).round(4)

        # Highlight Engagement Metrics
        if not highlights_df.empty:
            # Separate highlights by type
            vod_highlights = highlights_df[highlights_df['stream_id'].notna()]
            live_highlights = highlights_df[highlights_df['livestream_id'].notna()]
            
            # Like Ratio by type
            for df, prefix in [(vod_highlights, 'vod'), (live_highlights, 'live')]:
                if not df.empty:
                    rated_highlights = df[df['liked'].notna()]
                    if not rated_highlights.empty:
                        grouped = rated_highlights.groupby('period_start')
                        likes = grouped['liked'].apply(lambda x: (x == True).sum())
                        total_rated = grouped.size()
                        metrics[f'{prefix}_like_ratio'] = ((likes / total_rated) * 100).round(4)
            
            # Share Rate by type
            for df, prefix in [(vod_highlights, 'vod'), (live_highlights, 'live')]:
                if not df.empty:
                    df['is_shared'] = (df['downloaded'] | df['link_copied'])
                    grouped = df.groupby('period_start')
                    shares = grouped['is_shared'].sum()
                    total = grouped.size()
                    metrics[f'{prefix}_share_rate'] = ((shares / total) * 100).round(4)
            
            # Downloads by type (already implemented)
            downloaded_highlights = highlights_df[highlights_df['downloaded'] == True]
            grouped_downloads = downloaded_highlights.groupby('period_start')
            metrics['vod_downloads'] = grouped_downloads.apply(
                lambda x: x[x['stream_id'].notna()].shape[0]
            )
            metrics['livestream_downloads'] = grouped_downloads.apply(
                lambda x: x[x['livestream_id'].notna()].shape[0]
            )

        # Convert to DataFrame
        metrics_df = pd.DataFrame(metrics)
        metrics_df.index.name = 'period_start'
        return metrics_df

    def load_all_metrics(self):
        """Load both weekly and monthly metrics"""
        self.weekly_metrics = self._calculate_metrics('week')
        self.monthly_metrics = self._calculate_metrics('month')
