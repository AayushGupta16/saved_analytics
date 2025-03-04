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
    def _load_raw_data(_self, interval='week', force_reload=False):
        """Load and clean data from Supabase"""
        try:
            # Check if we already have cached data stored in persistent state
            if hasattr(st.session_state, 'cached_raw_data') and not force_reload:
                cached_streams_df, cached_highlights_df, cached_livestreams_df, cached_bots_df, cached_urls_df = st.session_state.cached_raw_data
                
                # Get timestamps for last data point in each dataset
                last_timestamps = {}
                if not cached_streams_df.empty:
                    last_timestamps['Streams'] = cached_streams_df['created_at'].max()
                if not cached_highlights_df.empty:
                    last_timestamps['Highlights'] = cached_highlights_df['created_at'].max()
                if not cached_livestreams_df.empty:
                    last_timestamps['Livestreams'] = cached_livestreams_df['created_at'].max()
                if not cached_bots_df.empty:
                    last_timestamps['Bots'] = cached_bots_df['created_at'].max()
                if not cached_urls_df.empty:
                    last_timestamps['Urls'] = cached_urls_df['created_at'].max()
                
                # Fetch only new data (since the last timestamp) and append to cached data
                streams_data = []
                highlights_data = []
                livestreams_data = []
                bots_data = []
                urls_data = []
                
                # Function to fetch new records for a table
                def fetch_new_records(table_name, last_timestamp):
                    new_records = []
                    batch_size = 1000
                    offset = 0
                    
                    if last_timestamp:
                        # Convert timestamp to ISO format for Supabase
                        iso_timestamp = last_timestamp.isoformat()
                        
                        while True:
                            response = _self.supabase.from_(table_name).select('*').filter('created_at', 'gt', iso_timestamp).limit(batch_size).offset(offset).execute()
                            if not response.data:
                                break
                            new_records.extend(response.data)
                            offset += batch_size
                    else:
                        # If no timestamp (first load), get all records
                        while True:
                            response = _self.supabase.from_(table_name).select('*').limit(batch_size).offset(offset).execute()
                            if not response.data:
                                break
                            new_records.extend(response.data)
                            offset += batch_size
                            
                    return new_records
                
                # Fetch new records for each table
                streams_data = fetch_new_records('Streams', last_timestamps.get('Streams'))
                highlights_data = fetch_new_records('Highlights', last_timestamps.get('Highlights'))
                livestreams_data = fetch_new_records('Livestreams', last_timestamps.get('Livestreams'))
                bots_data = fetch_new_records('Bots', last_timestamps.get('Bots'))
                urls_data = fetch_new_records('Urls', last_timestamps.get('Urls'))
                
                print(f"Fetched new data: Streams: {len(streams_data)}, Highlights: {len(highlights_data)}, "
                      f"Livestreams: {len(livestreams_data)}, Bots: {len(bots_data)}, Urls: {len(urls_data)}")
                
                # If we have new data, append it to the cached data
                if any([streams_data, highlights_data, livestreams_data, bots_data, urls_data]):
                    # Convert new data to dataframes
                    new_streams_df = pd.DataFrame(streams_data) if streams_data else pd.DataFrame()
                    new_highlights_df = pd.DataFrame(highlights_data) if highlights_data else pd.DataFrame()
                    new_livestreams_df = pd.DataFrame(livestreams_data) if livestreams_data else pd.DataFrame()
                    new_bots_df = pd.DataFrame(bots_data) if bots_data else pd.DataFrame()
                    new_urls_df = pd.DataFrame(urls_data) if urls_data else pd.DataFrame()
                    
                    # Process new dataframes (convert timestamps)
                    for df in [new_streams_df, new_highlights_df, new_livestreams_df, new_bots_df, new_urls_df]:
                        if not df.empty and 'created_at' in df.columns:
                            df['created_at'] = pd.to_datetime(df['created_at'], utc=True)
                            df['created_at'] = df['created_at'].dt.tz_localize(None)
                    
                    # Combine with cached data
                    streams_df = pd.concat([cached_streams_df, new_streams_df], ignore_index=True) if not new_streams_df.empty else cached_streams_df
                    highlights_df = pd.concat([cached_highlights_df, new_highlights_df], ignore_index=True) if not new_highlights_df.empty else cached_highlights_df
                    livestreams_df = pd.concat([cached_livestreams_df, new_livestreams_df], ignore_index=True) if not new_livestreams_df.empty else cached_livestreams_df
                    bots_df = pd.concat([cached_bots_df, new_bots_df], ignore_index=True) if not new_bots_df.empty else cached_bots_df
                    urls_df = pd.concat([cached_urls_df, new_urls_df], ignore_index=True) if not new_urls_df.empty else cached_urls_df
                    
                    # Update session state with combined data
                    st.session_state.cached_raw_data = (streams_df, highlights_df, livestreams_df, bots_df, urls_df)
                    
                    return streams_df, highlights_df, livestreams_df, bots_df, urls_df
                else:
                    # No new data, return cached data as is
                    return cached_streams_df, cached_highlights_df, cached_livestreams_df, cached_bots_df, cached_urls_df
            
            # If no cached data or force reload requested, fetch all data from scratch
            streams_data = []
            highlights_data = []
            livestreams_data = []
            bots_data = []
            urls_data = []
            
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
            
            # Store the processed dataframes in session_state for future use
            st.session_state.cached_raw_data = (streams_df, highlights_df, livestreams_df, bots_df, urls_df)
            
            return streams_df, highlights_df, livestreams_df, bots_df, urls_df
        except Exception as e:
            print(f"Error loading data: {e}")
            return pd.DataFrame(), pd.DataFrame(), pd.DataFrame(), pd.DataFrame(), pd.DataFrame()

    def _calculate_metrics(self, interval='week'):
        """Calculate all metrics for given interval"""
        # Use cached raw data but don't cache the calculations
        streams_df, highlights_df, livestreams_df, bots_df, urls_df = self._load_raw_data(interval)
        
        # Initialize empty DataFrame with proper columns
        empty_metrics = pd.DataFrame(columns=[
            'active_users', 'new_users', 'total_streams', 'avg_streams_per_user',
            'total_livestreams', 'avg_livestreams_per_user', 'vod_like_ratio',
            'live_like_ratio', 'vod_share_rate', 'live_share_rate',
            'vod_downloads', 'livestream_downloads', 'new_bots', 'total_url_views',
            'avg_views_per_url', 'urls_with_views_percent', 'churn_rate'
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
            if not urls_df.empty:
                urls_df['period_start'] = urls_df['created_at'].dt.floor('D')
        elif interval == 'week':
            streams_df['period_start'] = streams_df['created_at'].dt.to_period('W-SAT').dt.start_time
            if not highlights_df.empty:
                highlights_df['period_start'] = highlights_df['created_at'].dt.to_period('W-SAT').dt.start_time
            if not livestreams_df.empty:
                livestreams_df['period_start'] = livestreams_df['created_at'].dt.to_period('W-SAT').dt.start_time
            if not bots_df.empty:
                bots_df['period_start'] = bots_df['created_at'].dt.to_period('W-SAT').dt.start_time
            if not urls_df.empty:
                urls_df['period_start'] = urls_df['created_at'].dt.to_period('W-SAT').dt.start_time
        else:  # month
            streams_df['period_start'] = streams_df['created_at'].dt.to_period('M').dt.start_time
            if not highlights_df.empty:
                highlights_df['period_start'] = highlights_df['created_at'].dt.to_period('M').dt.start_time
            if not livestreams_df.empty:
                livestreams_df['period_start'] = livestreams_df['created_at'].dt.to_period('M').dt.start_time
            if not bots_df.empty:
                bots_df['period_start'] = bots_df['created_at'].dt.to_period('M').dt.start_time
            if not urls_df.empty:
                urls_df['period_start'] = urls_df['created_at'].dt.to_period('M').dt.start_time

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
                active_urls = urls_df[urls_df['view_count'] > 1].copy()  # Create a copy to avoid the warning
                if not active_urls.empty:
                    if interval == 'day':
                        active_urls.loc[:, 'period_start'] = active_urls['created_at'].dt.floor('D')
                    elif interval == 'week':
                        active_urls.loc[:, 'period_start'] = active_urls['created_at'].dt.to_period('W-SAT').dt.start_time
                    else:  # month
                        active_urls.loc[:, 'period_start'] = active_urls['created_at'].dt.to_period('M').dt.start_time
                    
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

        # URL View Metrics
        if not urls_df.empty:
            grouped_urls = urls_df.groupby('period_start')
            metrics['total_url_views'] = grouped_urls['view_count'].sum()
            # Calculate average views per URL
            url_counts = grouped_urls.size()  # number of URLs per period
            metrics['avg_views_per_url'] = (metrics['total_url_views'] / url_counts).round(2)
            
            # Calculate percentage of URLs with views
            urls_with_views = grouped_urls.apply(lambda x: (x['view_count'] > 0).sum())
            metrics['urls_with_views_percent'] = ((urls_with_views / url_counts) * 100).round(2)

        # Churn Rate Calculation
        if not all_activity.empty:
            # Get unique active users per period
            active_users_per_period = all_activity.groupby(['period_start', 'user_id']).size().reset_index()[['period_start', 'user_id']]
            
            # Create a set of periods for iteration
            periods = sorted(active_users_per_period['period_start'].unique())
            
            churn_rates = {}
            for i in range(1, len(periods)):
                current_period = periods[i]
                previous_period = periods[i-1]
                
                # Get users from both periods
                previous_users = set(active_users_per_period[active_users_per_period['period_start'] == previous_period]['user_id'])
                current_users = set(active_users_per_period[active_users_per_period['period_start'] == current_period]['user_id'])
                
                # Calculate churned users (in previous but not in current)
                churned_users = len(previous_users - current_users)
                
                # Calculate churn rate
                if len(previous_users) > 0:
                    churn_rate = (churned_users / len(previous_users)) * 100
                    churn_rates[current_period] = round(churn_rate, 2)
            
            if churn_rates:
                metrics['churn_rate'] = pd.Series(churn_rates)

        # Convert to DataFrame
        metrics_df = pd.DataFrame(metrics)
        metrics_df.index.name = 'period_start'
        
        # Ensure all expected columns exist, fill with 0 if missing
        for col in empty_metrics.columns:
            if col not in metrics_df.columns:
                metrics_df[col] = 0
            
        return metrics_df

    def load_all_metrics(self, force_reload=False):
        """Load daily, weekly and monthly metrics
        
        Args:
            force_reload (bool): If True, reload all data from database regardless of cache state
        """
        print("Loading raw data...")
        raw_data = self._load_raw_data('week', force_reload=force_reload)
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
