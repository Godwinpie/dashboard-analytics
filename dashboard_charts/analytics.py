import pandas as pd
from .services import NotionService


class AdAnalytics:
    """Analytics for advertising data"""
    
    def __init__(self):
        self.service = NotionService()
        self.df = self.service.fetch_data()
    
    def _sort_periods_chronologically(self, periods):
        """
        Sort period strings chronologically (ascending order: Jan 2024, Feb 2024, etc.)
        Handles formats like: 'Jan 2024', '2024-01', '2024Q1', '2024-W01', '24-01'
        """
        # Convert to list to avoid numpy array ambiguity issues
        if hasattr(periods, 'tolist'):
            periods = periods.tolist()
        else:
            periods = list(periods) if periods is not None else []
        
        if len(periods) == 0:
            return []
        
        # Try to parse and sort periods
        try:
            # Create a list of tuples: (original_string, parsed_datetime)
            parsed_periods = []
            for period in periods:
                period_str = str(period).strip()
                try:
                    # Handle different period formats
                    if 'Q' in period_str:  # Quarter format like '2024Q1' or '2024-Q1'
                        parts = period_str.replace('Q', '-Q').split('-Q')
                        year = int(parts[0])
                        quarter = int(parts[1])
                        # Use first month of quarter
                        month = (quarter - 1) * 3 + 1
                        dt = pd.Timestamp(year=year, month=month, day=1)
                    elif 'W' in period_str.upper():  # Week format like '2024-W01' or '2024W01'
                        # Parse ISO week format
                        try:
                            dt = pd.Period(period_str, freq='W').start_time
                        except Exception:
                            # Try alternate week format parsing
                            year_part = period_str[:4]
                            week_part = ''.join(filter(str.isdigit, period_str[4:]))
                            dt = pd.to_datetime(f'{year_part}-W{week_part.zfill(2)}-1', format='%Y-W%W-%w')
                    elif '-' in period_str and len(period_str) <= 7:  # Month format like '2024-01' or '24-01'
                        try:
                            dt = pd.Period(period_str, freq='M').start_time
                        except Exception:
                            # Try parsing with to_datetime
                            dt = pd.to_datetime(period_str, format='%Y-%m')
                    else:  # Try to parse as date string like 'Jan 2024' or 'January 2024'
                        try:
                            dt = pd.to_datetime(period_str, format='%b %Y')
                        except Exception:
                            try:
                                dt = pd.to_datetime(period_str, format='%B %Y')
                            except Exception:
                                # Last resort: let pandas infer the format
                                dt = pd.to_datetime(period_str)
                    
                    parsed_periods.append((period, dt))
                except Exception:
                    # If parsing fails, use the period as is with a fallback date
                    parsed_periods.append((period, pd.Timestamp.min))
            
            # Sort by the parsed datetime (ascending order)
            parsed_periods.sort(key=lambda x: x[1])
            
            # Return just the original strings in sorted order
            return [p[0] for p in parsed_periods]
        except Exception:
            # Fallback to original list if sorting fails
            return list(periods)
    
    def get_win_rate_by_period(self, period='month'):
        """
        Win Rate per month, week, or quarter
        Returns: {labels: [], data: []}
        """
        df = self.df.copy()
        
        if 'Launch Date' not in df.columns or df.empty:
            return {'labels': [], 'data': []}
        
        # Remove rows without Launch Date
        df = df[df['Launch Date'].notna()]
        
        # Group by period
        if period == 'week':
            if 'Launch YY-WW' in df.columns:
                df['Period'] = df['Launch YY-WW']
            else:
                df['Period'] = df['Launch Date'].dt.to_period('W').astype(str)
        elif period == 'quarter':
            df['Period'] = df['Launch Date'].dt.to_period('Q').astype(str)
        else:  # month
            if 'Launch Month' in df.columns:
                df['Period'] = df['Launch Month']
            else:
                df['Period'] = df['Launch Date'].dt.to_period('M').astype(str)
        
        result = {}
        for period_val, group in df.groupby('Period'):
            result[period_val] = self.service.calculate_win_rate(group)
        
        # Sort periods chronologically
        sorted_periods = self._sort_periods_chronologically(list(result.keys()))
        
        return {
            'labels': sorted_periods,
            'data': [result[p] for p in sorted_periods]
        }
    
    def get_win_rate_by_strategist(self, period='month'):
        """
        Win Rate per Strategist per month/week/quarter
        Returns: {labels: [], datasets: [{label: '', data: []}]}
        """
        df = self.df.copy()

        if 'Launch Date' not in df.columns or 'Strategist' not in df.columns or df.empty:
            return {'labels': [], 'datasets': []}
        
        df = df[df['Launch Date'].notna()]
        
        # Group by period
        if period == 'week':
            if 'Launch YY-WW' in df.columns:
                df['Period'] = df['Launch YY-WW']
            else:
                df['Period'] = df['Launch Date'].dt.to_period('W').astype(str)
        elif period == 'quarter':
            df['Period'] = df['Launch Date'].dt.to_period('Q').astype(str)
        else:
            if 'Launch Month' in df.columns:
                df['Period'] = df['Launch Month']
            else:
                df['Period'] = df['Launch Date'].dt.to_period('M').astype(str)
        
        # Sort periods chronologically
        periods = self._sort_periods_chronologically(df['Period'].unique())
        strategists = df['Strategist'].dropna().unique()
        
        datasets = []
        for strategist in strategists:
            data = []
            for period_val in periods:
                subset = df[(df['Period'] == period_val) & (df['Strategist'] == strategist)]
                win_rate = self.service.calculate_win_rate(subset)
                data.append(win_rate)
            
            datasets.append({
                'label': strategist,
                'data': data,
                'borderWidth': 2,
                'fill': False
            })
        
        return {
            'labels': periods,
            'datasets': datasets
        }
    
    def get_win_rate_by_product(self, period='month'):
        """Win Rate per Product per month/week/quarter"""
        df = self.df.copy()
        
        if 'Launch Date' not in df.columns or 'Product' not in df.columns or df.empty:
            return {'labels': [], 'datasets': []}
        
        df = df[df['Launch Date'].notna()]
        
        if period == 'week':
            if 'Launch YY-WW' in df.columns:
                df['Period'] = df['Launch YY-WW']
            else:
                df['Period'] = df['Launch Date'].dt.to_period('W').astype(str)
        elif period == 'quarter':
            df['Period'] = df['Launch Date'].dt.to_period('Q').astype(str)
        else:
            if 'Launch Month' in df.columns:
                df['Period'] = df['Launch Month']
            else:
                df['Period'] = df['Launch Date'].dt.to_period('M').astype(str)
        
        # Sort periods chronologically
        periods = self._sort_periods_chronologically(df['Period'].unique())
        products = df['Product'].dropna().unique()
        
        datasets = []
        for product in products:
            data = []
            for period_val in periods:
                subset = df[(df['Period'] == period_val) & (df['Product'] == product)]
                win_rate = self.service.calculate_win_rate(subset)
                data.append(win_rate)
            
            datasets.append({
                'label': product,
                'data': data,
                'borderWidth': 2,
                'fill': False
            })
        
        return {
            'labels': periods,
            'datasets': datasets
        }
    
    def get_win_rate_by_ad_type(self, period='month'):
        """Win Rate per Ad Type per month/week/quarter"""
        df = self.df.copy()
        
        if 'Launch Date' not in df.columns or 'Type' not in df.columns or df.empty:
            return {'labels': [], 'datasets': []}
        
        df = df[df['Launch Date'].notna()]
        
        if period == 'week':
            if 'Launch YY-WW' in df.columns:
                df['Period'] = df['Launch YY-WW']
            else:
                df['Period'] = df['Launch Date'].dt.to_period('W').astype(str)
        elif period == 'quarter':
            df['Period'] = df['Launch Date'].dt.to_period('Q').astype(str)
        else:
            if 'Launch Month' in df.columns:
                df['Period'] = df['Launch Month']
            else:
                df['Period'] = df['Launch Date'].dt.to_period('M').astype(str)
        
        # Sort periods chronologically
        periods = self._sort_periods_chronologically(df['Period'].unique())
        ad_types = df['Type'].dropna().unique()
        
        datasets = []
        for ad_type in ad_types:
            data = []
            for period_val in periods:
                subset = df[(df['Period'] == period_val) & (df['Type'] == ad_type)]
                win_rate = self.service.calculate_win_rate(subset)
                data.append(win_rate)
            
            datasets.append({
                'label': ad_type,
                'data': data,
                'borderWidth': 2,
                'fill': False
            })
        
        return {
            'labels': periods,
            'datasets': datasets
        }
    
    def get_ad_type_ratio(self, period='month', status=None):
        """Ad Type ratio per month/quarter - Stacked Bar Chart"""
        df = self.df.copy()
        
        if 'Launch Date' not in df.columns or 'Type' not in df.columns or df.empty:
            return {'labels': [], 'datasets': []}
        
        df = df[df['Launch Date'].notna()]
        
        # Filter by status if provided
        if status and 'Status' in df.columns:
            df = df[df['Status'].str.lower() == status.lower()]
        
        if period == 'quarter':
            df['Period'] = df['Launch Date'].dt.to_period('Q').astype(str)
        elif period == 'week':
            # Convert week to month for ratio charts
            if 'Launch Month' in df.columns:
                df['Period'] = df['Launch Month']
            else:
                df['Period'] = df['Launch Date'].dt.to_period('M').astype(str)
        else:
            if 'Launch Month' in df.columns:
                df['Period'] = df['Launch Month']
            else:
                df['Period'] = df['Launch Date'].dt.to_period('M').astype(str)
        
        # Sort periods chronologically
        periods = self._sort_periods_chronologically(df['Period'].unique())
        ad_types = df['Type'].dropna().unique()
        
        datasets = []
        colors = ['#FF6384', '#36A2EB', '#FFCE56', '#4BC0C0', '#9966FF', '#FF9F40', '#FF6B6B', '#4ECDC4']
        
        for idx, ad_type in enumerate(ad_types):
            data = []
            for period_val in periods:
                count = len(df[(df['Period'] == period_val) & (df['Type'] == ad_type)])
                data.append(count)
            
            datasets.append({
                'label': ad_type,
                'data': data,
                'backgroundColor': colors[idx % len(colors)]
            })
        
        return {
            'labels': periods,
            'datasets': datasets
        }
    
    def get_product_ratio(self, period='month', status=None):
        """Product ratio per month/quarter - Stacked Bar Chart"""
        df = self.df.copy()
        
        if 'Launch Date' not in df.columns or 'Product' not in df.columns or df.empty:
            return {'labels': [], 'datasets': []}
        
        # Filter rows with valid Launch Date
        df = df[df['Launch Date'].notna()]
        
        # Filter by status if provided
        if status and 'Status' in df.columns:
            df = df[df['Status'].str.lower() == status.lower()]
        
        # Fill empty Product values
        df['Product'] = df['Product'].fillna('Unknown').replace('', 'Unknown')
        
        if period == 'quarter':
            df['Period'] = df['Launch Date'].dt.to_period('Q').astype(str)
        elif period == 'week':
            if 'Launch Month' in df.columns:
                df['Period'] = df['Launch Month']
            else:
                df['Period'] = df['Launch Date'].dt.to_period('M').astype(str)
        else:
            if 'Launch Month' in df.columns:
                df['Period'] = df['Launch Month']
            else:
                df['Period'] = df['Launch Date'].dt.to_period('M').astype(str)
        
        # Sort periods chronologically
        periods = self._sort_periods_chronologically(df['Period'].dropna().unique())
        products = df['Product'].dropna().unique()
        
        datasets = []
        # Product-specific color mapping
        product_colors = {
            'V34': '#9966FF',           # Purple
            'Whitening Kit': '#36A2EB', # Blue
            'Plaque Remover': '#FFCE56', # Yellow
        }
        default_colors = ['#FF6384', '#4BC0C0', '#FF9F40', '#FF6B6B', '#4ECDC4']
        default_color_idx = 0
        
        for product in products:
            data = []
            for period_val in periods:
                count = len(df[(df['Period'] == period_val) & (df['Product'] == product)])
                data.append(count)
            
            # Get product-specific color or use default
            if product in product_colors:
                color = product_colors[product]
            else:
                color = default_colors[default_color_idx % len(default_colors)]
                default_color_idx += 1
            
            datasets.append({
                'label': "Unknown" if product=="" else product,
                'data': data,
                'backgroundColor': color
            })
        
        return {
            'labels': periods,
            'datasets': datasets
        }
    
    def get_format_ratio(self, period='month', status=None):
        """Format ratio per month/quarter - Stacked Bar Chart"""
        df = self.df.copy()
        
        if 'Launch Date' not in df.columns or 'Format' not in df.columns or df.empty:
            return {'labels': [], 'datasets': []}
        
        df = df[df['Launch Date'].notna()]
        
        # Filter by status if provided
        if status and 'Status' in df.columns:
            df = df[df['Status'].str.lower() == status.lower()]
        
        if period == 'quarter':
            df['Period'] = df['Launch Date'].dt.to_period('Q').astype(str)
        elif period == 'week':
            if 'Launch Month' in df.columns:
                df['Period'] = df['Launch Month']
            else:
                df['Period'] = df['Launch Date'].dt.to_period('M').astype(str)
        else:
            if 'Launch Month' in df.columns:
                df['Period'] = df['Launch Month']
            else:
                df['Period'] = df['Launch Date'].dt.to_period('M').astype(str)
        
        # Sort periods chronologically
        periods = self._sort_periods_chronologically(df['Period'].unique())
        formats = df['Format'].dropna().unique()
        
        datasets = []
        colors = ['#FF6384', '#36A2EB', '#FFCE56', '#4BC0C0', '#9966FF', '#FF9F40', '#FF6B6B', '#4ECDC4']
        
        for idx, format_type in enumerate(formats):
            data = []
            for period_val in periods:
                count = len(df[(df['Period'] == period_val) & (df['Format'] == format_type)])
                data.append(count)
            
            datasets.append({
                'label': format_type,
                'data': data,
                'backgroundColor': colors[idx % len(colors)]
            })
        
        return {
            'labels': periods,
            'datasets': datasets
        }
    
    def get_avg_production_time(self, strategist=None, period='month'):
        """Average ad production time (Ad time to ready) filtered by strategist"""
        df = self.df.copy()
        
        if 'Ad time to ready (days)' not in df.columns or 'Launch Date' not in df.columns:
            return {'labels': [], 'data': []}
        
        # Remove rows without Launch Date
        df = df[df['Launch Date'].notna()]
        
        # Remove rows with invalid or missing production time data
        df = df[df['Ad time to ready (days)'].notna()]

        # Additional check: ensure values are numeric and positive
        df = df[df['Ad time to ready (days)'] > 0]

        if df.empty:
            return {'labels': [], 'data': []}
        
        if strategist:
            df = df[df['Strategist'] == strategist]
            
            if df.empty:
                return {'labels': [], 'data': []}
        
        if period == 'quarter':
            df['Period'] = df['Launch Date'].dt.to_period('Q').astype(str)
        elif period == 'week':
            if 'Launch YY-WW' in df.columns:
                df['Period'] = df['Launch YY-WW']
            else:
                df['Period'] = df['Launch Date'].dt.to_period('W').astype(str)
        else:
            if 'Launch Month' in df.columns:
                df['Period'] = df['Launch Month']
            else:
                df['Period'] = df['Launch Date'].dt.to_period('M').astype(str)
        
        # Group by period and calculate mean
        result = df.groupby('Period')['Ad time to ready (days)'].mean().round(2)
        
        # Sort chronologically
        sorted_periods = self._sort_periods_chronologically(list(result.index))
        
        return {
            'labels': sorted_periods,
            'data': [result[p] for p in sorted_periods]
        }
    
    def get_avg_editing_time(self, editor=None, period='month'):
        """Average ad editing time (Editing Duration) filtered by editor/designer"""
        df = self.df.copy()
        
        if 'Editing Duration (minutes)' not in df.columns or 'Launch Date' not in df.columns:
            return {'labels': [], 'data': []}
        
        df = df[df['Launch Date'].notna()]
        df = df[df['Editing Duration (minutes)'].notna()]
        
        # Convert minutes to hours for better readability
        df['Editing Duration (hours)'] = df['Editing Duration (minutes)'] / 60
        
        if editor:
            df = df[df['Editor/Designer'] == editor]
        
        if period == 'quarter':
            df['Period'] = df['Launch Date'].dt.to_period('Q').astype(str)
        elif period == 'week':
            if 'Launch YY-WW' in df.columns:
                df['Period'] = df['Launch YY-WW']
            else:
                df['Period'] = df['Launch Date'].dt.to_period('W').astype(str)
        else:
            if 'Launch Month' in df.columns:
                df['Period'] = df['Launch Month']
            else:
                df['Period'] = df['Launch Date'].dt.to_period('M').astype(str)
        
        result = df.groupby('Period')['Editing Duration (hours)'].mean().round(2)
        
        # Sort chronologically
        sorted_periods = self._sort_periods_chronologically(list(result.index))
        
        return {
            'labels': sorted_periods,
            'data': [result[p] for p in sorted_periods]
        }
    
    def get_creatives_volume(self, period='month', strategist=None, status=None):
        """Creatives volume - total and per strategist - per week/month/quarter"""
        df = self.df.copy()
        
        if 'Launch Date' not in df.columns or df.empty:
            return {'labels': [], 'data': []}
        
        df = df[df['Launch Date'].notna()]
        
        # Filter by status if provided
        if status and 'Status' in df.columns:
            df = df[df['Status'].str.lower() == status.lower()]
        
        if strategist:
            df = df[df['Strategist'] == strategist]
        
        if period == 'week':
            if 'Launch YY-WW' in df.columns:
                df['Period'] = df['Launch YY-WW']
            else:
                df['Period'] = df['Launch Date'].dt.to_period('W').astype(str)
        elif period == 'quarter':
            df['Period'] = df['Launch Date'].dt.to_period('Q').astype(str)
        else:
            if 'Launch Month' in df.columns:
                df['Period'] = df['Launch Month']
            else:
                df['Period'] = df['Launch Date'].dt.to_period('M').astype(str)
        
        result = df.groupby('Period').size()
        
        # Sort chronologically
        sorted_periods = self._sort_periods_chronologically(list(result.index))
        
        return {
            'labels': sorted_periods,
            'data': [result[p] for p in sorted_periods]
        }
