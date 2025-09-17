"""
Simple URL configuration for bi_tool project.
"""
from django.contrib import admin
from django.urls import path
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
import json

def health_check(request):
    """Simple health check endpoint"""
    return JsonResponse({
        'status': 'healthy',
        'message': 'BI Tool backend is running',
        'version': '1.0.0'
    })

def api_overview(request):
    """API overview endpoint"""
    return JsonResponse({
        'message': 'BI Tool API',
        'endpoints': {
            'health': '/api/health/',
            'admin': '/admin/',
            'api': '/api/',
        },
        'status': 'active'
    })

@csrf_exempt
def demo_data(request):
    """Demo data endpoint for frontend testing"""
    if request.method == 'GET':
        return JsonResponse({
            'sales_data': [
                {'date': '2025-01-01', 'amount': 15000, 'branch': 'Main'},
                {'date': '2025-01-02', 'amount': 18000, 'branch': 'Main'},
                {'date': '2025-01-03', 'amount': 22000, 'branch': 'Main'},
            ],
            'kpis': {
                'total_revenue': 145000,
                'total_orders': 1250,
                'avg_order_value': 116,
                'growth_rate': 12.5
            },
            'branches': [
                {'id': 1, 'name': 'Main Branch', 'revenue': 75000},
                {'id': 2, 'name': 'Downtown', 'revenue': 45000},
                {'id': 3, 'name': 'Mall Location', 'revenue': 25000},
            ]
        })
    return JsonResponse({'error': 'Method not allowed'}, status=405)

urlpatterns = [
    # Django admin
    path('admin/', admin.site.urls),
    
    # API endpoints
    path('api/health/', health_check, name='health'),
    path('api/', api_overview, name='api_overview'),
    path('api/demo-data/', demo_data, name='demo_data'),
]