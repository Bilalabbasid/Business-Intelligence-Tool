"""
Data Quality URL Configuration
URL routing for DQ API endpoints.
"""

from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

# Create router and register viewsets
router = DefaultRouter()
router.register(r'rules', views.DQRuleViewSet, basename='dq-rules')
router.register(r'runs', views.DQRunViewSet, basename='dq-runs')
router.register(r'violations', views.DQViolationViewSet, basename='dq-violations')
router.register(r'metrics', views.DQMetricViewSet, basename='dq-metrics')
router.register(r'anomalies', views.DQAnomalyDetectionViewSet, basename='dq-anomalies')
router.register(r'config', views.DQConfigViewSet, basename='dq-config')
router.register(r'templates', views.DQRuleTemplateViewSet, basename='dq-templates')

app_name = 'dq'

urlpatterns = [
    # API routes
    path('api/v1/', include(router.urls)),
    
    # Health check endpoint
    path('health/', views.health_check, name='health-check'),
]