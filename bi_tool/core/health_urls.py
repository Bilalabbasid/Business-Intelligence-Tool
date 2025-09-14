from django.urls import path
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
import json

@require_http_methods(["GET"])
@csrf_exempt
def health_check(request):
    """
    Health check endpoint for monitoring
    """
    return JsonResponse({
        'status': 'healthy',
        'service': 'bi_tool',
        'version': '1.0.0'
    })

@require_http_methods(["GET"])
@csrf_exempt
def database_health(request):
    """
    Database health check
    """
    try:
        from .models import User
        User.objects.first()  # Simple database query
        return JsonResponse({
            'status': 'healthy',
            'database': 'connected'
        })
    except Exception as e:
        return JsonResponse({
            'status': 'unhealthy',
            'database': 'error',
            'error': str(e)
        }, status=503)

urlpatterns = [
    path('', health_check, name='health-check'),
    path('db/', database_health, name='database-health'),
]