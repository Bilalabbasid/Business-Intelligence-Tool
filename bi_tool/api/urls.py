from django.urls import path, include
from rest_framework.routers import DefaultRouter
from rest_framework.documentation import include_docs_urls

from .views import (
    BranchViewSet,
    SalesViewSet,
    InventoryViewSet,
    CustomerViewSet,
    StaffPerformanceViewSet,
    AuditLogViewSet
)

# Create router and register viewsets
router = DefaultRouter()
router.register(r'branches', BranchViewSet, basename='branch')
router.register(r'sales', SalesViewSet, basename='sales')
router.register(r'inventory', InventoryViewSet, basename='inventory')
router.register(r'customers', CustomerViewSet, basename='customer')
router.register(r'staff-performance', StaffPerformanceViewSet, basename='staffperformance')
router.register(r'audit-logs', AuditLogViewSet, basename='auditlog')

# API URL patterns
urlpatterns = [
    # API root
    path('', include(router.urls)),
    
    # API Documentation (if needed)
    path('docs/', include_docs_urls(title='BI Tool API')),
]

# URL name patterns for reference:
# branches/ - GET (list), POST (create)
# branches/{id}/ - GET (retrieve), PUT (update), PATCH (partial_update), DELETE (destroy)
# branches/{id}/performance_summary/ - GET (custom action)
# 
# sales/ - GET (list), POST (create)
# sales/{id}/ - GET (retrieve), PUT (update), PATCH (partial_update), DELETE (destroy)
# sales/daily_summary/ - GET (custom action)
# sales/revenue_trends/ - GET (custom action)
# 
# inventory/ - GET (list), POST (create)
# inventory/{id}/ - GET (retrieve), PUT (update), PATCH (partial_update), DELETE (destroy)
# inventory/low_stock_alert/ - GET (custom action)
# inventory/expiry_alert/ - GET (custom action)
# inventory/bulk_update_stock/ - POST (custom action)
# 
# customers/ - GET (list), POST (create)
# customers/{id}/ - GET (retrieve), PUT (update), PATCH (partial_update), DELETE (destroy)
# customers/loyalty_tiers/ - GET (custom action)
# 
# staff-performance/ - GET (list), POST (create)
# staff-performance/{id}/ - GET (retrieve), PUT (update), PATCH (partial_update), DELETE (destroy)
# staff-performance/performance_rankings/ - GET (custom action)
# 
# audit-logs/ - GET (list)
# audit-logs/{id}/ - GET (retrieve)
# audit-logs/activity_summary/ - GET (custom action)