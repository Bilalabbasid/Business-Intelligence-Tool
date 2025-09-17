"""
Simple URL configuration for bi_tool project.
"""
from django.contrib import admin
from django.urls import path
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.contrib.auth import authenticate, get_user_model
from rest_framework_simplejwt.tokens import RefreshToken
import json

# SimpleJWT views
from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
)

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


# Simple development auth/login endpoint to satisfy frontend calls
@csrf_exempt
def dev_login(request):
    if request.method != 'POST':
        return JsonResponse({'detail': 'Method not allowed'}, status=405)
    try:
        payload = json.loads(request.body.decode('utf-8') or '{}')
    except Exception:
        payload = {}

    username = payload.get('username') or payload.get('email') or payload.get('email_or_username')
    password = payload.get('password')

    # Very small dev-only auth check (replace with real auth in production)
    if username and password and (username == 'admin@example.com' and password == 'password'):
        User = get_user_model()
        user, created = User.objects.get_or_create(
            username='admin',
            defaults={'email': 'admin@example.com'}
        )
        # Ensure user has a usable password (we won't set it here for dev)
        # Create JWT tokens for the user
        refresh = RefreshToken.for_user(user)
        return JsonResponse({
            'access': str(refresh.access_token),
            'refresh': str(refresh),
            'user': {'username': user.username, 'email': user.email}
        })
    return JsonResponse({'detail': 'Invalid credentials'}, status=401)


@require_http_methods(['GET'])
def profile_view(request):
    # If using JWTAuthentication, request.user will be set when proper Authorization header is present
    user = getattr(request, 'user', None)
    if user and user.is_authenticated:
        return JsonResponse({'username': user.username, 'email': user.email})
    return JsonResponse({'detail': 'Not authenticated'}, status=401)


@require_http_methods(['POST'])
@csrf_exempt
def logout_view(request):
    # For JWT, logout is typically client-side (delete tokens). We'll accept the request and return success.
    return JsonResponse({'detail': 'Logged out'})

urlpatterns = [
    # Django admin
    path('admin/', admin.site.urls),
    
    # API endpoints
    path('api/health/', health_check, name='health'),
    path('api/', api_overview, name='api_overview'),
    path('api/demo-data/', demo_data, name='demo_data'),
    # Development login (kept for testing) and JWT endpoints
    path('api/auth/login/', dev_login, name='dev_login'),
    path('api/auth/token/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('api/auth/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('api/auth/profile/', profile_view, name='profile'),
    path('api/auth/logout/', logout_view, name='logout'),
]