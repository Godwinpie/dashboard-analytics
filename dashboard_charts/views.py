from django.shortcuts import render
from django.views import View
from django.http import JsonResponse
from django.contrib.auth.mixins import LoginRequiredMixin

from .analytics import AdAnalytics


class DashboardView(LoginRequiredMixin, View):
    """Main dashboard with all charts"""
    login_url = 'users:login'
    redirect_field_name = 'next'  
    
    def get(self, request):
        try:
            analytics = AdAnalytics()
            df = analytics.df

            # Get unique values for filters
            strategists = sorted(
                df['Strategist'].fillna('Unknown').replace('', 'Unknown').unique().tolist()
            ) if 'Strategist' in df.columns else []

            editors = sorted(
                df['Editor/Designer'].fillna('Unknown').replace('', 'Unknown').unique().tolist()
            ) if 'Editor/Designer' in df.columns else []

            # Get chart access for user (superuser gets all)
            if request.user.is_superuser:
                allowed_charts = [
                    "win_rate", "win_rate_strategist", "win_rate_product", "win_rate_adtype",
                    "adtype_ratio", "product_ratio", "format_ratio", "production_time", "editing_time", "creatives_volume"
                ]
            else:
                try:
                    allowed_charts = list(request.user.chart_access.charts)
                except Exception:
                    allowed_charts = []

            context = {
                'strategists': strategists,
                'editors': editors,
                'allowed_charts': allowed_charts,
                'error': None
            }
        except Exception as e:
            context = {
                'strategists': [],
                'editors': [],
                'allowed_charts': [],
                'error': str(e)
            }
        return render(request, 'dashboard.html', context)


# Helper function to convert numpy/pandas types to native Python types
def convert_to_serializable(obj):
    """Convert numpy/pandas types to native Python types"""
    import numpy as np
    
    if isinstance(obj, (np.integer, np.int64)):
        return int(obj)
    elif isinstance(obj, (np.floating, np.float64)):
        return float(obj)
    elif isinstance(obj, np.ndarray):
        return obj.tolist()
    elif isinstance(obj, list):
        return [convert_to_serializable(item) for item in obj]
    elif isinstance(obj, dict):
        return {key: convert_to_serializable(value) for key, value in obj.items()}
    return obj


# API Endpoints for Chart Data
class WinRateChartAPI(LoginRequiredMixin, View):
    """Win Rate per month/week"""
    login_url = 'users:login'
    
    def get(self, request):
        period = request.GET.get('period', 'month')
        
        try:
            analytics = AdAnalytics()
            data = analytics.get_win_rate_by_period(period)
            
            response_data = {
                'labels': convert_to_serializable(data['labels']),
                'datasets': [{
                    'label': f'Win Rate (%) - {period.capitalize()}',
                    'data': convert_to_serializable(data['data']),
                    'borderColor': '#36A2EB',
                    'backgroundColor': 'rgba(54, 162, 235, 0.2)',
                    'borderWidth': 2,
                    'fill': True,
                    'tension': 0.4
                }]
            }
            
            return JsonResponse(response_data)
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)


class WinRateByStrategistAPI(LoginRequiredMixin, View):
    """Win Rate per Strategist"""
    login_url = 'users:login'
    
    def get(self, request):
        period = request.GET.get('period', 'month')
        
        try:
            analytics = AdAnalytics()
            data = analytics.get_win_rate_by_strategist(period)
            
            # Add colors to datasets
            colors = ['#FF6384', '#36A2EB', '#FFCE56', '#4BC0C0', '#9966FF', '#FF9F40', '#FF6B6B', '#4ECDC4']
            for idx, dataset in enumerate(data['datasets']):
                dataset['borderColor'] = colors[idx % len(colors)]
                dataset['backgroundColor'] = 'rgba(0, 0, 0, 0)'
                dataset['tension'] = 0.4
                dataset['data'] = convert_to_serializable(dataset['data'])
            
            response_data = {
                'labels': convert_to_serializable(data['labels']),
                'datasets': data['datasets']
            }
            
            return JsonResponse(response_data)
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)


class WinRateByProductAPI(LoginRequiredMixin, View):
    """Win Rate per Product"""
    login_url = 'users:login'
    
    # Product-specific color mapping
    PRODUCT_COLORS = {
        'V34': '#9966FF',           # Purple
        'Whitening Kit': '#36A2EB', # Blue
        'Plaque Remover': '#FFCE56', # Yellow
    }
    DEFAULT_COLORS = ['#FF6384', '#4BC0C0', '#FF9F40', '#FF6B6B', '#4ECDC4']
    
    def get(self, request):
        period = request.GET.get('period', 'month')
        
        try:
            analytics = AdAnalytics()
            data = analytics.get_win_rate_by_product(period)
            
            default_color_idx = 0
            for dataset in data['datasets']:
                product_label = dataset.get('label', '')
                if product_label in self.PRODUCT_COLORS:
                    color = self.PRODUCT_COLORS[product_label]
                else:
                    color = self.DEFAULT_COLORS[default_color_idx % len(self.DEFAULT_COLORS)]
                    default_color_idx += 1
                dataset['borderColor'] = color
                dataset['backgroundColor'] = 'rgba(0, 0, 0, 0)'
                dataset['tension'] = 0.4
                dataset['data'] = convert_to_serializable(dataset['data'])
            
            response_data = {
                'labels': convert_to_serializable(data['labels']),
                'datasets': data['datasets']
            }
            
            return JsonResponse(response_data)
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)


class WinRateByAdTypeAPI(LoginRequiredMixin, View):
    """Win Rate per Ad Type"""
    login_url = 'users:login'
    
    def get(self, request):
        period = request.GET.get('period', 'month')
        
        try:
            analytics = AdAnalytics()
            data = analytics.get_win_rate_by_ad_type(period)
            
            colors = ['#FF6384', '#36A2EB', '#FFCE56', '#4BC0C0', '#9966FF', '#FF9F40', '#FF6B6B', '#4ECDC4']
            for idx, dataset in enumerate(data['datasets']):
                dataset['borderColor'] = colors[idx % len(colors)]
                dataset['backgroundColor'] = 'rgba(0, 0, 0, 0)'
                dataset['tension'] = 0.4
                dataset['data'] = convert_to_serializable(dataset['data'])
            
            response_data = {
                'labels': convert_to_serializable(data['labels']),
                'datasets': data['datasets']
            }
            
            return JsonResponse(response_data)
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)


class AdTypeRatioAPI(LoginRequiredMixin, View):
    """Ad Type ratio - Stacked Bar"""
    login_url = 'users:login'
    
    def get(self, request):
        period = request.GET.get('period', 'month')
        status = request.GET.get('status', None)
        
        try:
            analytics = AdAnalytics()
            data = analytics.get_ad_type_ratio(period, status)
            
            # Convert data in datasets
            for dataset in data['datasets']:
                dataset['data'] = convert_to_serializable(dataset['data'])
            
            response_data = {
                'labels': convert_to_serializable(data['labels']),
                'datasets': data['datasets']
            }
            
            return JsonResponse(response_data)
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)


class ProductRatioAPI(LoginRequiredMixin, View):
    """Product ratio - Stacked Bar"""
    login_url = 'users:login'
    
    def get(self, request):
        period = request.GET.get('period', 'month')
        status = request.GET.get('status', None)
        
        try:
            analytics = AdAnalytics()
            data = analytics.get_product_ratio(period, status)
            
            # Convert data in datasets
            for dataset in data['datasets']:
                dataset['data'] = convert_to_serializable(dataset['data'])
            
            response_data = {
                'labels': convert_to_serializable(data['labels']),
                'datasets': data['datasets']
            }
            
            return JsonResponse(response_data)
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)


class FormatRatioAPI(LoginRequiredMixin, View):
    """Format ratio - Stacked Bar"""
    login_url = 'users:login'
    
    def get(self, request):
        period = request.GET.get('period', 'month')
        status = request.GET.get('status', None)
        
        try:
            analytics = AdAnalytics()
            data = analytics.get_format_ratio(period, status)
            
            # Convert data in datasets
            for dataset in data['datasets']:
                dataset['data'] = convert_to_serializable(dataset['data'])
            
            response_data = {
                'labels': convert_to_serializable(data['labels']),
                'datasets': data['datasets']
            }
            
            return JsonResponse(response_data)
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)


class AvgProductionTimeAPI(LoginRequiredMixin, View):
    """Average production time (Ad time to ready)"""
    login_url = 'users:login'
    
    def get(self, request):
        strategist = request.GET.get('strategist', None)
        period = request.GET.get('period', 'month')
        
        try:
            analytics = AdAnalytics()
            data = analytics.get_avg_production_time(strategist, period)
            
            response_data = {
                'labels': convert_to_serializable(data['labels']),
                'datasets': [{
                    'label': f'Avg Production Time (days) - {strategist or "All"}',
                    'data': convert_to_serializable(data['data']),
                    'borderColor': '#FF6384',
                    'backgroundColor': 'rgba(255, 99, 132, 0.2)',
                    'borderWidth': 2,
                    'fill': True,
                    'tension': 0.4
                }]
            }
            
            return JsonResponse(response_data)
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)


class AvgEditingTimeAPI(LoginRequiredMixin, View):
    """Average editing time (Editing Duration in hours)"""
    login_url = 'users:login'
    
    def get(self, request):
        editor = request.GET.get('editor', None)
        period = request.GET.get('period', 'month')  # Add period parameter
        
        try:
            analytics = AdAnalytics()
            data = analytics.get_avg_editing_time(editor, period)
            
            response_data = {
                'labels': convert_to_serializable(data['labels']),
                'datasets': [{
                    'label': f'Avg Editing Time (hours) - {editor or "All"}',
                    'data': convert_to_serializable(data['data']),
                    'borderColor': '#4BC0C0',
                    'backgroundColor': 'rgba(75, 192, 192, 0.2)',
                    'borderWidth': 2,
                    'fill': True,
                    'tension': 0.4
                }]
            }
            
            return JsonResponse(response_data)
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)


class CreativesVolumeAPI(LoginRequiredMixin, View):
    """Creatives volume"""
    login_url = 'users:login'
    
    def get(self, request):
        period = request.GET.get('period', 'month')
        strategist = request.GET.get('strategist', None)
        status = request.GET.get('status', None)
        
        try:
            analytics = AdAnalytics()
            data = analytics.get_creatives_volume(period, strategist, status)
            
            response_data = {
                'labels': convert_to_serializable(data['labels']),
                'datasets': [{
                    'label': f'Creatives Volume - {strategist or "Total"}',
                    'data': convert_to_serializable(data['data']),
                    'borderColor': '#9966FF',
                    'backgroundColor': 'rgba(153, 102, 255, 0.2)',
                    'borderWidth': 2,
                    'fill': True,
                    'tension': 0.4
                }]
            }
            
            return JsonResponse(response_data)
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)


