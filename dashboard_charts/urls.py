"""dashboard_charts URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/2.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include

from dashboard_charts import views
from users import views as user_views

urlpatterns = [
    path('admin/', admin.site.urls),
    
    path('', include('users.urls')),
    path('', views.DashboardView.as_view(), name='dashboard'),
    
    # Chart API Endpoints
    path('api/win-rate/', views.WinRateChartAPI.as_view(), name='api_win_rate'),
    path('api/win-rate-strategist/', views.WinRateByStrategistAPI.as_view(), name='api_win_rate_strategist'),
    path('api/win-rate-product/', views.WinRateByProductAPI.as_view(), name='api_win_rate_product'),
    path('api/win-rate-adtype/', views.WinRateByAdTypeAPI.as_view(), name='api_win_rate_adtype'),
    path('api/adtype-ratio/', views.AdTypeRatioAPI.as_view(), name='api_adtype_ratio'),
    path('api/product-ratio/', views.ProductRatioAPI.as_view(), name='api_product_ratio'),
    path('api/format-ratio/', views.FormatRatioAPI.as_view(), name='api_format_ratio'),
    path('api/production-time/', views.AvgProductionTimeAPI.as_view(), name='api_production_time'),
    path('api/editing-time/', views.AvgEditingTimeAPI.as_view(), name='api_editing_time'),
    path('api/creatives-volume/', views.CreativesVolumeAPI.as_view(), name='api_creatives_volume'),
    
    # User Management API
    path('api/remove-user/<int:user_id>/', user_views.RemoveUserAPIView.as_view(), name='api_remove_user'),

]
