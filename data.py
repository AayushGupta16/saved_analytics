import pandas as pd
from supabase import create_client
from datetime import datetime, timedelta
import streamlit as st

class AnalyticsDataLoader:
    def __init__(self, supabase_url, supabase_key, developer_ids):
        self.supabase = create_client(supabase_url, supabase_key)
        self.developer_ids = developer_ids
        self.daily_metrics = pd.DataFrame()
        self.weekly_metrics = pd.DataFrame()
        self.monthly_metrics = pd.DataFrame()
        
    def _get_first_sunday(self, df):
        """Get the first Sunday after the earliest data point"""
        if df.empty:
            return None
        
        earliest_date = df['created_at'].min()
        days_until_sunday = (6 - earliest_date.weekday()) % 7
        first_sunday = earliest_date + timedelta(days=days_until_sunday)
        return first_sunday.replace(hour=0, minute=0, second=0, microsecond=0)
    
    @st.cache_data(ttl=600)  # Cache for 10 minutes
    def _load_raw_data(_self):
        """Load and clean data from Supabase"""
        try:
            # Pagination logic for Streams, Highlights, and Livestreams
            streams_data = []
            highlights_data = []
            livestreams_data = []
            bots_data = []  # New array for bots

            # Fetch streams in batches
            batch_size = 1000
            offset = 0
            while True:
                response = _self.supabase.from_('Streams').select('*').limit(batch_size).offset(offset).execute()
                if not response.data:
                    break
                streams_data.extend(response.data)
                offset += batch_size

            # Fetch highlights in batches
            offset = 0
            while True:
                response = _self.supabase.from_('Highlights').select('*').limit(batch_size).offset(offset).execute()
                if not response.data:
                    break
                highlights_data.extend(response.data)
                offset += batch_size

            # Fetch livestreams in batches
            offset = 0
            while True:
                response = _self.supabase.from_('Livestreams').select('*').limit(batch_size).offset(offset).execute()
                if not response.data:
                    break
                livestreams_data.extend(response.data)
                offset += batch_size

            # Fetch bots in batches
            offset = 0
            batch_size = 1000
            while True:
                response = _self.supabase.from_('Bots').select('*').limit(batch_size).offset(offset).execute()
                if not response.data:
                    break
                bots_data.extend(response.data)
                offset += batch_size

            # Fetch urls in batches
            offset = 0
            urls_data = []
            while True:
                response = _self.supabase.from_('Urls').select('*').limit(batch_size).offset(offset).execute()
                if not response.data:
                    break
                urls_data.extend(response.data)
                offset += batch_size

            # Convert to dataframes
            streams_df = pd.DataFrame(streams_data)
            highlights_df = pd.DataFrame(highlights_data)
            livestreams_df = pd.DataFrame(livestreams_data)
            bots_df = pd.DataFrame(bots_data)  # New dataframe for bots
            urls_df = pd.DataFrame(urls_data)
            
            # Debugging: Log counts of rows retrieved
            print(f"Total Streams data count: {len(streams_df)}")
            print(f"Total Highlights data count: {len(highlights_df)}")
            print(f"Total Livestreams data count: {len(livestreams_df)}")
            print(f"Total Bots data count: {len(bots_df)}")
            print(f"Total Urls data count: {len(urls_df)}")

            # Filter out developer data
            if not streams_df.empty:
                streams_df = streams_df[~streams_df['user_id'].isin(_self.developer_ids)]
            if not highlights_df.empty:
                highlights_df = highlights_df[~highlights_df['user_id'].isin(_self.developer_ids)]
            if not livestreams_df.empty:
                livestreams_df = livestreams_df[~livestreams_df['user_id'].isin(_self.developer_ids)]

            # Convert timestamps
            for df in [streams_df, highlights_df, livestreams_df]:
                if not df.empty:
                    df['created_at'] = pd.to_datetime(df['created_at'], utc=True)
                    df['created_at'] = df['created_at'].dt.tz_localize(None)  # Remove timezone information
                    print(df[['created_at']].head())  # Debugging: Log a sample of timestamps
            
            if not bots_df.empty:
                bots_df['created_at'] = pd.to_datetime(bots_df['created_at'], utc=True)
                bots_df['created_at'] = bots_df['created_at'].dt.tz_localize(None)
            
            # Convert timestamps for urls_df
            if not urls_df.empty:
                urls_df['created_at'] = pd.to_datetime(urls_df['created_at'], utc=True)
                urls_df['created_at'] = urls_df['created_at'].dt.tz_localize(None)
            
            return streams_df, highlights_df, livestreams_df, bots_df, urls_df
        except Exception as e:
            print(f"Error loading data: {e}")
            return pd.DataFrame(), pd.DataFrame(), pd.DataFrame(), pd.DataFrame(), pd.DataFrame()

    def _calculate_metrics(self, interval='week'):
        """Calculate all metrics for given interval"""
        # Use cached raw data but don't cache the calculations
        streams_df, highlights_df, livestreams_df, bots_df, urls_df = self._load_raw_data()
        
        # Initialize empty DataFrame with proper columns
        empty_metrics = pd.DataFrame(columns=[
            'active_users', 'new_users', 'total_streams', 'avg_streams_per_user',
            'total_livestreams', 'avg_livestreams_per_user', 'vod_like_ratio',
            'live_like_ratio', 'vod_share_rate', 'live_share_rate',
            'vod_downloads', 'livestream_downloads', 'new_bots'
        ])
        empty_metrics.index.name = 'period_start'
        
        if streams_df.empty and highlights_df.empty and livestreams_df.empty:
            return empty_metrics
            
        # Determine period starts
        if interval == 'day':
            streams_df['period_start'] = streams_df['created_at'].dt.floor('D')
            if not highlights_df.empty:
                highlights_df['period_start'] = highlights_df['created_at'].dt.floor('D')
            if not livestreams_df.empty:
                livestreams_df['period_start'] = livestreams_df['created_at'].dt.floor('D')
            if not bots_df.empty:
                bots_df['period_start'] = bots_df['created_at'].dt.floor('D')
        elif interval == 'week':
            streams_df['period_start'] = streams_df['created_at'].dt.to_period('W-SAT').dt.start_time
            if not highlights_df.empty:
                highlights_df['period_start'] = highlights_df['created_at'].dt.to_period('W-SAT').dt.start_time
            if not livestreams_df.empty:
                livestreams_df['period_start'] = livestreams_df['created_at'].dt.to_period('W-SAT').dt.start_time
            if not bots_df.empty:
                bots_df['period_start'] = bots_df['created_at'].dt.to_period('W-SAT').dt.start_time
        else:  # month
            streams_df['period_start'] = streams_df['created_at'].dt.to_period('M').dt.start_time
            if not highlights_df.empty:
                highlights_df['period_start'] = highlights_df['created_at'].dt.to_period('M').dt.start_time
            if not livestreams_df.empty:
                livestreams_df['period_start'] = livestreams_df['created_at'].dt.to_period('M').dt.start_time
            if not bots_df.empty:
                bots_df['period_start'] = bots_df['created_at'].dt.to_period('M').dt.start_time

        metrics = {}
        
        # User Activity Metrics
        if not streams_df.empty or not urls_df.empty:
            # Get all user activity periods
            all_activity = pd.DataFrame()
            
            # Add users who have converted streams
            if not streams_df.empty:
                all_activity = pd.concat([all_activity, 
                    streams_df[['user_id', 'period_start']]
                ])
            
            # Add users who have urls with view_count > 1
            if not urls_df.empty:
                # Filter urls with view_count > 1
                active_urls = urls_df[urls_df['view_count'] > 1]
                if not active_urls.empty:
                    active_urls['period_start'] = active_urls['created_at'].dt.floor('D')
                    if interval == 'week':
                        active_urls['period_start'] = active_urls['created_at'].dt.to_period('W-SAT').dt.start_time
                    elif interval == 'month':
                        active_urls['period_start'] = active_urls['created_at'].dt.to_period('M').dt.start_time
                    
                    all_activity = pd.concat([all_activity, 
                        active_urls[['user_id', 'period_start']]
                    ])
            
            if not all_activity.empty:
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

        # Add bot metrics after existing metrics calculations
        if not bots_df.empty:
            if interval == 'day':
                bots_df['period_start'] = bots_df['created_at'].dt.floor('D')
            else:
                bots_df['period_start'] = bots_df['created_at'].dt.to_period(
                    'W-SAT' if interval == 'week' else 'M'
                ).dt.start_time
            grouped_bots = bots_df.groupby('period_start')
            metrics['new_bots'] = grouped_bots.size()

        # Convert to DataFrame
        metrics_df = pd.DataFrame(metrics)
        metrics_df.index.name = 'period_start'
        
        # Ensure all expected columns exist, fill with 0 if missing
        for col in empty_metrics.columns:
            if col not in metrics_df.columns:
                metrics_df[col] = 0
            
        return metrics_df

    def load_all_metrics(self):
        """Load daily, weekly and monthly metrics"""
        print("Loading raw data...")
        raw_data = self._load_raw_data()
        streams_df, highlights_df, livestreams_df, bots_df, urls_df = raw_data
        
        print(f"Raw data loaded: \n"
              f"Streams: {len(streams_df)} rows\n"
              f"Highlights: {len(highlights_df)} rows\n"
              f"Livestreams: {len(livestreams_df)} rows\n"
              f"Bots: {len(bots_df)} rows\n"
              f"Urls: {len(urls_df)} rows")
        
        # Calculate metrics for each interval using the same raw data
        print("Calculating metrics...")
        self.daily_metrics = self._calculate_metrics('day')
        self.weekly_metrics = self._calculate_metrics('week')
        self.monthly_metrics = self._calculate_metrics('month')
        
        print(f"Metrics calculated:\n"
              f"Daily: {len(self.daily_metrics)} periods\n"
              f"Weekly: {len(self.weekly_metrics)} periods\n"
              f"Monthly: {len(self.monthly_metrics)} periods")
