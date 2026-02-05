import json
import asyncio
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from .analytics import AdAnalytics


class ChartStreamConsumer(AsyncWebsocketConsumer):
    """WebSocket consumer for live chart data streaming"""
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.streaming_task = None
        self.is_streaming = False
        self.interval = 30  # Default 30 seconds
    
    async def connect(self):
        """Handle WebSocket connection - Check authentication"""
        # Check if user is authenticated
        user = self.scope.get("user")
        
        if not user or not user.is_authenticated:
            # Reject connection if not authenticated
            await self.close(code=4001)
            return
        
        await self.accept()
        print(f"WebSocket connected for user: {user.username}")
        
        await self.send(text_data=json.dumps({
            'type': 'connection',
            'status': 'connected',
            'message': f'WebSocket connected successfully for {user.username}',
            'user': user.username
        }))
    
    async def disconnect(self, close_code):
        """Handle WebSocket disconnection"""
        print(f"WebSocket disconnected: {close_code}")
        self.is_streaming = False
        
        if self.streaming_task:
            self.streaming_task.cancel()
    
    async def receive(self, text_data):
        """Handle incoming WebSocket messages"""
        try:
            data = json.loads(text_data)
            command = data.get('command')
            
            if command == 'start_stream':
                self.interval = data.get('interval', 30)
                await self.start_streaming()
                
            elif command == 'stop_stream':
                await self.stop_streaming()
                
            elif command == 'get_chart':
                chart_type = data.get('chart_type')
                params = data.get('params', {})
                await self.send_chart_data(chart_type, params)
                
        except Exception as e:
            await self.send(text_data=json.dumps({
                'type': 'error',
                'message': str(e)
            }))
    
    async def start_streaming(self):
        """Start streaming chart data"""
        if self.is_streaming:
            return
        
        self.is_streaming = True
        
        await self.send(text_data=json.dumps({
            'type': 'stream_status',
            'status': 'started',
            'interval': self.interval
        }))
        
        # Start background task for streaming
        self.streaming_task = asyncio.create_task(self.stream_data())
    
    async def stop_streaming(self):
        """Stop streaming chart data"""
        self.is_streaming = False
        
        if self.streaming_task:
            self.streaming_task.cancel()
            self.streaming_task = None
        
        await self.send(text_data=json.dumps({
            'type': 'stream_status',
            'status': 'stopped'
        }))
    
    async def stream_data(self):
        """Background task to continuously stream data"""
        while self.is_streaming:
            try:
                # Fetch and send all chart data
                await self.send_all_charts()
                
                # Wait for interval before next update
                await asyncio.sleep(self.interval)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                print(f"Streaming error: {e}")
                await asyncio.sleep(self.interval)
    
    async def send_all_charts(self):
        """Send data for all charts"""
        try:
            analytics = await self.get_analytics()
            
            # Get all chart data
            charts_data = {
                'type': 'charts_update',
                'timestamp': asyncio.get_event_loop().time(),
                'charts': {}
            }
            
            # This will be populated with actual data
            await self.send(text_data=json.dumps(charts_data))
            
        except Exception as e:
            print(f"Error sending charts: {e}")
    
    async def send_chart_data(self, chart_type, params):
        """Send data for a specific chart"""
        try:
            analytics = await self.get_analytics()
            
            chart_data = await self.get_chart_by_type(analytics, chart_type, params)
            
            await self.send(text_data=json.dumps({
                'type': 'chart_data',
                'chart_type': chart_type,
                'data': chart_data,
                'params': params
            }))
            
        except Exception as e:
            await self.send(text_data=json.dumps({
                'type': 'error',
                'chart_type': chart_type,
                'message': str(e)
            }))
    
    @database_sync_to_async
    def get_analytics(self):
        """Get analytics instance"""
        return AdAnalytics()
    
    @database_sync_to_async
    def get_chart_by_type(self, analytics, chart_type, params):
        """Get specific chart data"""
        period = params.get('period', 'month')
        strategist = params.get('strategist', None)
        editor = params.get('editor', None)
        
        if chart_type == 'win_rate':
            return analytics.get_win_rate_by_period(period)
        elif chart_type == 'win_rate_strategist':
            return analytics.get_win_rate_by_strategist(period)
        elif chart_type == 'win_rate_product':
            return analytics.get_win_rate_by_product(period)
        elif chart_type == 'win_rate_adtype':
            return analytics.get_win_rate_by_ad_type(period)
        elif chart_type == 'adtype_ratio':
            return analytics.get_ad_type_ratio(period)
        elif chart_type == 'product_ratio':
            return analytics.get_product_ratio(period)
        elif chart_type == 'format_ratio':
            return analytics.get_format_ratio(period)
        elif chart_type == 'production_time':
            return analytics.get_avg_production_time(strategist, period)
        elif chart_type == 'editing_time':
            return analytics.get_avg_editing_time(editor, period)
        elif chart_type == 'creatives_volume':
            return analytics.get_creatives_volume(period, strategist)
        else:
            return {'labels': [], 'data': []}
