from rest_framework import viewsets, status, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.pagination import PageNumberPagination
from django_filters.rest_framework import DjangoFilterBackend
from django_filters import rest_framework as django_filters
from django.db.models import Q, Sum, Count, Avg, Max, Min, F
from django.db import models
from django.utils import timezone
from datetime import datetime, timedelta
from decimal import Decimal

from analytics.models import Branch, Sales, Inventory, Customer, StaffPerformance, AuditLog
from .serializers import (
    BranchListSerializer, BranchDetailSerializer,
    SalesListSerializer, SalesDetailSerializer,
    InventoryListSerializer, InventoryDetailSerializer,
    CustomerListSerializer, CustomerDetailSerializer,
    StaffPerformanceListSerializer, StaffPerformanceDetailSerializer,
    AuditLogSerializer, BulkInventoryUpdateSerializer
)
from .permissions import (
    BranchPermission, SalesPermission, InventoryPermission,
    CustomerPermission, StaffPerformancePermission, AuditLogPermission,
    BranchFilterMixin
)


class StandardResultsSetPagination(PageNumberPagination):
    """
    Standard pagination class with configurable page size
    """
    page_size = 25
    page_size_query_param = 'page_size'
    max_page_size = 100


class LargeResultsSetPagination(PageNumberPagination):
    """
    Pagination class for larger datasets
    """
    page_size = 50
    page_size_query_param = 'page_size'
    max_page_size = 500


# Filter classes
class BranchFilter(django_filters.FilterSet):
    """
    Filter class for Branch model
    """
    name = django_filters.CharFilter(lookup_expr='icontains')
    city = django_filters.CharFilter(field_name='location__city', lookup_expr='icontains')
    country = django_filters.CharFilter(field_name='location__country', lookup_expr='icontains')
    manager = django_filters.CharFilter(field_name='manager__username', lookup_expr='icontains')
    is_active = django_filters.BooleanFilter()
    created_after = django_filters.DateFilter(field_name='created_at', lookup_expr='gte')
    created_before = django_filters.DateFilter(field_name='created_at', lookup_expr='lte')
    
    class Meta:
        model = Branch
        fields = ['name', 'city', 'country', 'manager', 'is_active', 'created_after', 'created_before']


class SalesFilter(django_filters.FilterSet):
    """
    Filter class for Sales model
    """
    branch = django_filters.CharFilter(field_name='branch__branch_id')
    branch_name = django_filters.CharFilter(field_name='branch__name', lookup_expr='icontains')
    date_from = django_filters.DateFilter(field_name='date', lookup_expr='gte')
    date_to = django_filters.DateFilter(field_name='date', lookup_expr='lte')
    payment_method = django_filters.ChoiceFilter(choices=Sales.PAYMENT_CHOICES)
    order_type = django_filters.ChoiceFilter(choices=Sales.ORDER_CHOICES)
    customer = django_filters.CharFilter(field_name='customer__customer_id')
    served_by = django_filters.CharFilter(field_name='served_by__username', lookup_expr='icontains')
    total_amount_min = django_filters.NumberFilter(field_name='total_amount', lookup_expr='gte')
    total_amount_max = django_filters.NumberFilter(field_name='total_amount', lookup_expr='lte')
    is_active = django_filters.BooleanFilter()
    
    class Meta:
        model = Sales
        fields = [
            'branch', 'branch_name', 'date_from', 'date_to',
            'payment_method', 'order_type', 'customer', 'served_by',
            'total_amount_min', 'total_amount_max', 'is_active'
        ]


class InventoryFilter(django_filters.FilterSet):
    """
    Filter class for Inventory model
    """
    branch = django_filters.CharFilter(field_name='branch__branch_id')
    branch_name = django_filters.CharFilter(field_name='branch__name', lookup_expr='icontains')
    item_name = django_filters.CharFilter(lookup_expr='icontains')
    category = django_filters.CharFilter(lookup_expr='icontains')
    supplier = django_filters.CharFilter(lookup_expr='icontains')
    stock_quantity_min = django_filters.NumberFilter(field_name='stock_quantity', lookup_expr='gte')
    stock_quantity_max = django_filters.NumberFilter(field_name='stock_quantity', lookup_expr='lte')
    low_stock = django_filters.BooleanFilter(method='filter_low_stock')
    expired = django_filters.BooleanFilter(method='filter_expired')
    expiry_date_before = django_filters.DateFilter(field_name='expiry_date', lookup_expr='lte')
    is_active = django_filters.BooleanFilter()
    
    def filter_low_stock(self, queryset, name, value):
        if value:
            return queryset.filter(stock_quantity__lte=F('reorder_level'))
        return queryset
    
    def filter_expired(self, queryset, name, value):
        if value:
            return queryset.filter(expiry_date__lte=timezone.now().date())
        return queryset
    
    class Meta:
        model = Inventory
        fields = [
            'branch', 'branch_name', 'item_name', 'category', 'supplier',
            'stock_quantity_min', 'stock_quantity_max', 'low_stock',
            'expired', 'expiry_date_before', 'is_active'
        ]


class CustomerFilter(django_filters.FilterSet):
    """
    Filter class for Customer model
    """
    name = django_filters.CharFilter(lookup_expr='icontains')
    email = django_filters.CharFilter(lookup_expr='icontains')
    phone = django_filters.CharFilter(lookup_expr='icontains')
    preferred_branch = django_filters.CharFilter(field_name='preferred_branch__branch_id')
    loyalty_points_min = django_filters.NumberFilter(field_name='loyalty_points', lookup_expr='gte')
    loyalty_points_max = django_filters.NumberFilter(field_name='loyalty_points', lookup_expr='lte')
    total_spent_min = django_filters.NumberFilter(field_name='total_spent', lookup_expr='gte')
    total_spent_max = django_filters.NumberFilter(field_name='total_spent', lookup_expr='lte')
    visit_count_min = django_filters.NumberFilter(field_name='visit_count', lookup_expr='gte')
    last_visit_from = django_filters.DateFilter(field_name='last_visit', lookup_expr='gte')
    last_visit_to = django_filters.DateFilter(field_name='last_visit', lookup_expr='lte')
    is_active = django_filters.BooleanFilter()
    
    class Meta:
        model = Customer
        fields = [
            'name', 'email', 'phone', 'preferred_branch',
            'loyalty_points_min', 'loyalty_points_max',
            'total_spent_min', 'total_spent_max',
            'visit_count_min', 'last_visit_from', 'last_visit_to',
            'is_active'
        ]


class StaffPerformanceFilter(django_filters.FilterSet):
    """
    Filter class for StaffPerformance model
    """
    staff = django_filters.CharFilter(field_name='staff__username', lookup_expr='icontains')
    branch = django_filters.CharFilter(field_name='branch__branch_id')
    shift_date_from = django_filters.DateFilter(field_name='shift_date', lookup_expr='gte')
    shift_date_to = django_filters.DateFilter(field_name='shift_date', lookup_expr='lte')
    hours_worked_min = django_filters.NumberFilter(field_name='hours_worked', lookup_expr='gte')
    hours_worked_max = django_filters.NumberFilter(field_name='hours_worked', lookup_expr='lte')
    sales_generated_min = django_filters.NumberFilter(field_name='sales_generated', lookup_expr='gte')
    sales_generated_max = django_filters.NumberFilter(field_name='sales_generated', lookup_expr='lte')
    customer_feedback_min = django_filters.NumberFilter(field_name='customer_feedback_score', lookup_expr='gte')
    customer_feedback_max = django_filters.NumberFilter(field_name='customer_feedback_score', lookup_expr='lte')
    is_active = django_filters.BooleanFilter()
    
    class Meta:
        model = StaffPerformance
        fields = [
            'staff', 'branch', 'shift_date_from', 'shift_date_to',
            'hours_worked_min', 'hours_worked_max',
            'sales_generated_min', 'sales_generated_max',
            'customer_feedback_min', 'customer_feedback_max',
            'is_active'
        ]


# ViewSets
class BranchViewSet(BranchFilterMixin, viewsets.ModelViewSet):
    """
    ViewSet for Branch model with RBAC and filtering
    """
    queryset = Branch.objects.filter(is_active=True).select_related('manager')
    permission_classes = [BranchPermission]
    pagination_class = StandardResultsSetPagination
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_class = BranchFilter
    search_fields = ['name', 'location__city', 'location__country', 'manager__username']
    ordering_fields = ['name', 'created_at', 'location__city']
    ordering = ['-created_at']
    
    def get_serializer_class(self):
        """Return appropriate serializer based on action"""
        if self.action in ['list']:
            return BranchListSerializer
        return BranchDetailSerializer
    
    def get_queryset(self):
        """Filter queryset based on user's branch access"""
        queryset = super().get_queryset()
        return self.filter_queryset_by_branch(self.request, queryset)
    
    @action(detail=True, methods=['get'])
    def performance_summary(self, request, pk=None):
        """Get performance summary for a branch"""
        branch = self.get_object()
        
        # Get date range (default to last 30 days)
        end_date = timezone.now().date()
        start_date = end_date - timedelta(days=30)
        
        if 'start_date' in request.query_params:
            start_date = datetime.strptime(request.query_params['start_date'], '%Y-%m-%d').date()
        if 'end_date' in request.query_params:
            end_date = datetime.strptime(request.query_params['end_date'], '%Y-%m-%d').date()
        
        # Calculate metrics
        sales_data = branch.sales.filter(
            date__range=[start_date, end_date],
            is_active=True
        ).aggregate(
            total_sales=Count('id'),
            total_revenue=Sum('total_amount'),
            avg_order_value=Avg('total_amount')
        )
        
        performance_data = branch.staff_performances.filter(
            shift_date__range=[start_date, end_date],
            is_active=True
        ).aggregate(
            total_shifts=Count('id'),
            total_hours=Sum('hours_worked'),
            avg_customer_rating=Avg('customer_feedback_score')
        )
        
        inventory_data = branch.inventory_items.filter(is_active=True).aggregate(
            total_items=Count('id'),
            low_stock_items=Count('id', filter=Q(stock_quantity__lte=F('reorder_level'))),
            total_inventory_value=Sum(F('stock_quantity') * F('unit_cost'))
        )
        
        return Response({
            'branch_id': branch.branch_id,
            'branch_name': branch.name,
            'date_range': {
                'start_date': start_date,
                'end_date': end_date
            },
            'sales_metrics': {
                'total_sales': sales_data['total_sales'] or 0,
                'total_revenue': sales_data['total_revenue'] or Decimal('0.00'),
                'avg_order_value': sales_data['avg_order_value'] or Decimal('0.00')
            },
            'performance_metrics': {
                'total_shifts': performance_data['total_shifts'] or 0,
                'total_hours_worked': performance_data['total_hours'] or 0,
                'avg_customer_rating': performance_data['avg_customer_rating'] or 0
            },
            'inventory_metrics': {
                'total_items': inventory_data['total_items'] or 0,
                'low_stock_items': inventory_data['low_stock_items'] or 0,
                'total_inventory_value': inventory_data['total_inventory_value'] or Decimal('0.00')
            }
        })


class SalesViewSet(BranchFilterMixin, viewsets.ModelViewSet):
    """
    ViewSet for Sales model with RBAC and filtering
    """
    queryset = Sales.objects.filter(is_active=True).select_related(
        'branch', 'customer', 'served_by'
    ).prefetch_related('branch__manager')
    permission_classes = [SalesPermission]
    pagination_class = StandardResultsSetPagination
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_class = SalesFilter
    search_fields = ['sale_id', 'customer__name', 'served_by__username']
    ordering_fields = ['date', 'total_amount', 'created_at']
    ordering = ['-date', '-created_at']
    
    def get_serializer_class(self):
        """Return appropriate serializer based on action"""
        if self.action in ['list']:
            return SalesListSerializer
        return SalesDetailSerializer
    
    def get_queryset(self):
        """Filter queryset based on user's branch access and role"""
        queryset = super().get_queryset()
        queryset = self.filter_queryset_by_branch(self.request, queryset)
        
        # Additional filtering for STAFF role
        if self.request.user.role == self.request.user.STAFF:
            if self.action in ['update', 'partial_update', 'destroy']:
                queryset = queryset.filter(served_by=self.request.user)
        
        return queryset
    
    def perform_create(self, serializer):
        """Set served_by to current user on creation"""
        serializer.save(served_by=self.request.user)
    
    @action(detail=False, methods=['get'])
    def daily_summary(self, request):
        """Get daily sales summary"""
        date_param = request.query_params.get('date', timezone.now().date())
        if isinstance(date_param, str):
            date_param = datetime.strptime(date_param, '%Y-%m-%d').date()
        
        queryset = self.filter_queryset_by_branch(request, self.get_queryset())
        daily_sales = queryset.filter(date=date_param)
        
        summary = daily_sales.aggregate(
            total_sales=Count('id'),
            total_revenue=Sum('total_amount'),
            avg_order_value=Avg('total_amount'),
            cash_sales=Count('id', filter=Q(payment_method='CASH')),
            card_sales=Count('id', filter=Q(payment_method='CARD')),
            online_sales=Count('id', filter=Q(payment_method='ONLINE'))
        )
        
        return Response({
            'date': date_param,
            'summary': summary,
            'sales_by_hour': list(
                daily_sales.extra(
                    select={'hour': "strftime('%%H', created_at)"}
                ).values('hour').annotate(
                    sales_count=Count('id'),
                    revenue=Sum('total_amount')
                ).order_by('hour')
            )
        })
    
    @action(detail=False, methods=['get'])
    def revenue_trends(self, request):
        """Get revenue trends over time"""
        days = int(request.query_params.get('days', 30))
        end_date = timezone.now().date()
        start_date = end_date - timedelta(days=days)
        
        queryset = self.filter_queryset_by_branch(request, self.get_queryset())
        trends = queryset.filter(
            date__range=[start_date, end_date]
        ).extra(
            select={'date_str': "date(date)"}
        ).values('date_str').annotate(
            daily_revenue=Sum('total_amount'),
            daily_sales=Count('id'),
            avg_order_value=Avg('total_amount')
        ).order_by('date_str')
        
        return Response({
            'period': {'start_date': start_date, 'end_date': end_date},
            'trends': list(trends)
        })


class InventoryViewSet(BranchFilterMixin, viewsets.ModelViewSet):
    """
    ViewSet for Inventory model with RBAC and filtering
    """
    queryset = Inventory.objects.filter(is_active=True).select_related('branch')
    permission_classes = [InventoryPermission]
    pagination_class = StandardResultsSetPagination
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_class = InventoryFilter
    search_fields = ['item_name', 'category', 'supplier']
    ordering_fields = ['item_name', 'stock_quantity', 'expiry_date', 'last_updated']
    ordering = ['-last_updated']
    
    def get_serializer_class(self):
        """Return appropriate serializer based on action"""
        if self.action in ['list']:
            return InventoryListSerializer
        return InventoryDetailSerializer
    
    def get_queryset(self):
        """Filter queryset based on user's branch access"""
        queryset = super().get_queryset()
        return self.filter_queryset_by_branch(self.request, queryset)
    
    @action(detail=False, methods=['get'])
    def low_stock_alert(self, request):
        """Get items with low stock levels"""
        queryset = self.filter_queryset_by_branch(request, self.get_queryset())
        low_stock_items = queryset.filter(stock_quantity__lte=F('reorder_level'))
        
        serializer = self.get_serializer(low_stock_items, many=True)
        return Response({
            'low_stock_count': low_stock_items.count(),
            'items': serializer.data
        })
    
    @action(detail=False, methods=['get'])
    def expiry_alert(self, request):
        """Get items nearing expiry"""
        days_ahead = int(request.query_params.get('days', 30))
        alert_date = timezone.now().date() + timedelta(days=days_ahead)
        
        queryset = self.filter_queryset_by_branch(request, self.get_queryset())
        expiring_items = queryset.filter(
            expiry_date__lte=alert_date,
            expiry_date__gte=timezone.now().date()
        ).order_by('expiry_date')
        
        serializer = self.get_serializer(expiring_items, many=True)
        return Response({
            'alert_period_days': days_ahead,
            'expiring_items_count': expiring_items.count(),
            'items': serializer.data
        })
    
    @action(detail=False, methods=['post'])
    def bulk_update_stock(self, request):
        """Bulk update stock quantities"""
        serializer = BulkInventoryUpdateSerializer(data=request.data)
        if serializer.is_valid():
            updates = serializer.validated_data['updates']
            updated_items = []
            errors = []
            
            for update_data in updates:
                try:
                    inventory_id = update_data['inventory_id']
                    new_quantity = Decimal(update_data['stock_quantity'])
                    
                    item = Inventory.objects.get(
                        inventory_id=inventory_id,
                        is_active=True
                    )
                    
                    # Check permissions for this specific item
                    if not self.get_object_permission_check()(request, self, item):
                        errors.append({
                            'inventory_id': inventory_id,
                            'error': 'Permission denied'
                        })
                        continue
                    
                    old_quantity = item.stock_quantity
                    item.stock_quantity = new_quantity
                    item.save()
                    
                    updated_items.append({
                        'inventory_id': inventory_id,
                        'old_quantity': old_quantity,
                        'new_quantity': new_quantity
                    })
                    
                except Inventory.DoesNotExist:
                    errors.append({
                        'inventory_id': inventory_id,
                        'error': 'Item not found'
                    })
                except Exception as e:
                    errors.append({
                        'inventory_id': inventory_id,
                        'error': str(e)
                    })
            
            return Response({
                'updated_items': updated_items,
                'errors': errors,
                'summary': {
                    'total_requested': len(updates),
                    'successfully_updated': len(updated_items),
                    'failed': len(errors)
                }
            })
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class CustomerViewSet(BranchFilterMixin, viewsets.ModelViewSet):
    """
    ViewSet for Customer model with RBAC and filtering
    """
    queryset = Customer.objects.filter(is_active=True).select_related('preferred_branch')
    permission_classes = [CustomerPermission]
    pagination_class = StandardResultsSetPagination
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_class = CustomerFilter
    search_fields = ['name', 'email', 'phone', 'customer_id']
    ordering_fields = ['name', 'total_spent', 'loyalty_points', 'last_visit', 'created_at']
    ordering = ['-last_visit', '-created_at']
    
    def get_serializer_class(self):
        """Return appropriate serializer based on action"""
        if self.action in ['list']:
            return CustomerListSerializer
        return CustomerDetailSerializer
    
    def get_queryset(self):
        """Filter queryset based on user's branch access"""
        queryset = super().get_queryset()
        
        # Filter by preferred branch for branch-specific roles
        if self.request.user.role != self.request.user.SUPER_ADMIN:
            user_branches = [self.request.user.branch_id] if self.request.user.branch_id else []
            if user_branches:
                queryset = queryset.filter(
                    Q(preferred_branch__branch_id__in=user_branches) |
                    Q(preferred_branch__isnull=True)
                )
            else:
                return queryset.none()
        
        return queryset
    
    @action(detail=False, methods=['get'])
    def loyalty_tiers(self, request):
        """Get customer distribution by loyalty tiers"""
        queryset = self.get_queryset()
        
        tier_distribution = {}
        for tier_code, tier_name in Customer.LOYALTY_TIERS:
            tier_distribution[tier_name] = queryset.filter(
                loyalty_points__gte=Customer.get_tier_threshold(tier_code)
            ).count()
        
        top_customers = queryset.order_by('-total_spent')[:10]
        top_serializer = CustomerListSerializer(top_customers, many=True)
        
        return Response({
            'tier_distribution': tier_distribution,
            'total_customers': queryset.count(),
            'top_customers_by_spending': top_serializer.data
        })


class StaffPerformanceViewSet(BranchFilterMixin, viewsets.ModelViewSet):
    """
    ViewSet for StaffPerformance model with RBAC and filtering
    """
    queryset = StaffPerformance.objects.filter(is_active=True).select_related('staff', 'branch')
    permission_classes = [StaffPerformancePermission]
    pagination_class = StandardResultsSetPagination
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_class = StaffPerformanceFilter
    search_fields = ['staff__username', 'staff__first_name', 'staff__last_name']
    ordering_fields = ['shift_date', 'hours_worked', 'sales_generated', 'customer_feedback_score']
    ordering = ['-shift_date']
    
    def get_serializer_class(self):
        """Return appropriate serializer based on action"""
        if self.action in ['list']:
            return StaffPerformanceListSerializer
        return StaffPerformanceDetailSerializer
    
    def get_queryset(self):
        """Filter queryset based on user's branch access and role"""
        queryset = super().get_queryset()
        queryset = self.filter_queryset_by_branch(self.request, queryset)
        
        # Additional filtering for STAFF role - they can only see their own performance
        if self.request.user.role == self.request.user.STAFF:
            queryset = queryset.filter(staff=self.request.user)
        
        return queryset
    
    @action(detail=False, methods=['get'])
    def performance_rankings(self, request):
        """Get staff performance rankings"""
        # Get date range
        days = int(request.query_params.get('days', 30))
        end_date = timezone.now().date()
        start_date = end_date - timedelta(days=days)
        
        queryset = self.get_queryset().filter(
            shift_date__range=[start_date, end_date]
        )
        
        # Calculate performance metrics per staff member
        staff_performance = queryset.values(
            'staff__id', 'staff__username', 'staff__first_name', 'staff__last_name'
        ).annotate(
            total_hours=Sum('hours_worked'),
            total_sales=Sum('sales_generated'),
            total_orders=Sum('orders_served'),
            avg_feedback=Avg('customer_feedback_score'),
            shifts_count=Count('id')
        ).annotate(
            sales_per_hour=Sum('sales_generated') / Sum('hours_worked'),
            orders_per_hour=Sum('orders_served') / Sum('hours_worked')
        ).order_by('-sales_per_hour')
        
        return Response({
            'period': {'start_date': start_date, 'end_date': end_date},
            'staff_rankings': list(staff_performance)
        })


class AuditLogViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Read-only ViewSet for AuditLog model
    """
    queryset = AuditLog.objects.all().select_related('user').order_by('-timestamp')
    serializer_class = AuditLogSerializer
    permission_classes = [AuditLogPermission]
    pagination_class = LargeResultsSetPagination
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['action', 'model_name', 'user__username', 'endpoint']
    ordering_fields = ['timestamp', 'action', 'model_name']
    ordering = ['-timestamp']
    
    def get_queryset(self):
        """Filter queryset based on user's branch access"""
        queryset = super().get_queryset()
        
        if self.request.user.role != self.request.user.SUPER_ADMIN:
            user_branches = [self.request.user.branch_id] if self.request.user.branch_id else []
            if user_branches:
                queryset = queryset.filter(branch_id__in=user_branches)
            else:
                return queryset.none()
        
        return queryset
    
    @action(detail=False, methods=['get'])
    def activity_summary(self, request):
        """Get activity summary for audit logs"""
        # Get date range
        days = int(request.query_params.get('days', 7))
        end_date = timezone.now()
        start_date = end_date - timedelta(days=days)
        
        queryset = self.get_queryset().filter(
            timestamp__range=[start_date, end_date]
        )
        
        activity_by_action = queryset.values('action').annotate(
            count=Count('id')
        ).order_by('-count')
        
        activity_by_user = queryset.values(
            'user__username'
        ).annotate(
            count=Count('id')
        ).order_by('-count')[:10]
        
        activity_by_model = queryset.values('model_name').annotate(
            count=Count('id')
        ).order_by('-count')
        
        return Response({
            'period': {'start_date': start_date, 'end_date': end_date},
            'total_activities': queryset.count(),
            'activity_by_action': list(activity_by_action),
            'top_users': list(activity_by_user),
            'activity_by_model': list(activity_by_model)
        })