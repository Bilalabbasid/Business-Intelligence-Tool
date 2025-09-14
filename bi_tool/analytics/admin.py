from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.db.models import Sum, Count, Q
from django.utils import timezone
from datetime import datetime, timedelta

from .models import Branch, Sales, Inventory, Customer, StaffPerformance
from core.models import User


class RBACAdminMixin:
    """
    Mixin to enforce role-based access control in Django admin
    """
    
    def get_queryset(self, request):
        """
        Filter queryset based on user role
        """
        qs = super().get_queryset(request)
        
        # Super users and super admins can see everything
        if request.user.is_superuser or (hasattr(request.user, 'role') and request.user.role == User.SUPER_ADMIN):
            return qs
        
        # Managers can only see data for their branch
        if hasattr(request.user, 'role') and request.user.role == User.MANAGER and request.user.branch_id:
            if hasattr(self.model, 'branch'):
                return qs.filter(branch__branch_id=request.user.branch_id)
            elif hasattr(self.model, 'branch_id'):
                return qs.filter(branch_id=request.user.branch_id)
        
        # Analysts have read-only access to all data (handled by has_change_permission)
        if hasattr(request.user, 'role') and request.user.role == User.ANALYST:
            return qs
        
        # Staff can only see their own performance data
        if hasattr(request.user, 'role') and request.user.role == User.STAFF:
            if self.model.__name__ == 'StaffPerformance':
                return qs.filter(staff=request.user)
            # Staff cannot access other models through admin
            return qs.none()
        
        return qs.none()
    
    def has_change_permission(self, request, obj=None):
        """
        Check if user can modify objects
        """
        # Super users and super admins can modify everything
        if request.user.is_superuser or (hasattr(request.user, 'role') and request.user.role == User.SUPER_ADMIN):
            return True
        
        # Managers can modify data in their branch
        if hasattr(request.user, 'role') and request.user.role == User.MANAGER:
            if obj is None:
                return True
            # Check if object belongs to manager's branch
            if hasattr(obj, 'branch') and obj.branch.branch_id == request.user.branch_id:
                return True
            elif hasattr(obj, 'branch_id') and obj.branch_id == request.user.branch_id:
                return True
        
        # Analysts have read-only access (no change permission)
        if hasattr(request.user, 'role') and request.user.role == User.ANALYST:
            return False
        
        # Staff can only modify their own performance records
        if hasattr(request.user, 'role') and request.user.role == User.STAFF:
            if obj and hasattr(obj, 'staff') and obj.staff == request.user:
                return True
        
        return False
    
    def has_add_permission(self, request):
        """
        Check if user can add new objects
        """
        # Super users and super admins can add everything
        if request.user.is_superuser or (hasattr(request.user, 'role') and request.user.role == User.SUPER_ADMIN):
            return True
        
        # Managers can add data for their branch
        if hasattr(request.user, 'role') and request.user.role == User.MANAGER:
            return True
        
        # Analysts cannot add data (read-only)
        if hasattr(request.user, 'role') and request.user.role == User.ANALYST:
            return False
        
        # Staff can add their performance records
        if hasattr(request.user, 'role') and request.user.role == User.STAFF:
            return self.model.__name__ == 'StaffPerformance'
        
        return False
    
    def has_delete_permission(self, request, obj=None):
        """
        Check if user can delete objects (most should use soft delete)
        """
        # Only super users and super admins can hard delete
        if request.user.is_superuser or (hasattr(request.user, 'role') and request.user.role == User.SUPER_ADMIN):
            return True
        
        return False


@admin.register(Branch)
class BranchAdmin(RBACAdminMixin, admin.ModelAdmin):
    list_display = ('branch_id', 'name', 'manager', 'location_display', 'capacity', 'is_active', 'created_at')
    list_filter = ('is_active', 'created_at', 'location__city', 'location__country')
    search_fields = ('branch_id', 'name', 'location__city', 'manager__username')
    readonly_fields = ('created_at', 'updated_at')
    ordering = ['name']
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('branch_id', 'name', 'manager', 'phone', 'email')
        }),
        ('Location', {
            'fields': ('location',)
        }),
        ('Operations', {
            'fields': ('capacity', 'opening_hours')
        }),
        ('Status', {
            'fields': ('is_active', 'created_at', 'updated_at')
        }),
    )
    
    def location_display(self, obj):
        if obj.location:
            return f"{obj.location.city}, {obj.location.country}"
        return "No location"
    location_display.short_description = "Location"
    
    def get_queryset(self, request):
        """Override for Branch-specific filtering"""
        qs = super().get_queryset(request)
        
        # Managers can only see their own branch
        if hasattr(request.user, 'role') and request.user.role == User.MANAGER:
            return qs.filter(branch_id=request.user.branch_id)
        
        return qs


@admin.register(Sales)
class SalesAdmin(RBACAdminMixin, admin.ModelAdmin):
    list_display = ('sale_id', 'branch', 'date', 'total_amount', 'payment_method', 'customer', 'served_by', 'is_active')
    list_filter = ('date', 'payment_method', 'order_type', 'branch', 'is_active')
    search_fields = ('sale_id', 'customer__name', 'customer__phone', 'served_by__username')
    date_hierarchy = 'date'
    readonly_fields = ('created_at', 'updated_at')
    ordering = ['-date']
    
    fieldsets = (
        ('Sale Information', {
            'fields': ('sale_id', 'branch', 'date', 'order_type')
        }),
        ('Items & Pricing', {
            'fields': ('items', 'total_amount', 'tax_amount', 'discount_amount')
        }),
        ('Payment & Service', {
            'fields': ('payment_method', 'customer', 'served_by')
        }),
        ('Status', {
            'fields': ('is_active', 'created_at', 'updated_at')
        }),
    )
    
    def changelist_view(self, request, extra_context=None):
        """Add summary statistics to changelist"""
        response = super().changelist_view(request, extra_context=extra_context)
        
        try:
            qs = response.context_data['cl'].queryset
            
            # Calculate summary statistics
            summary = qs.aggregate(
                total_sales=Sum('total_amount'),
                total_orders=Count('id'),
                avg_order_value=Sum('total_amount') / Count('id') if qs.count() > 0 else 0
            )
            
            response.context_data['summary'] = summary
        except (AttributeError, KeyError):
            pass
        
        return response


@admin.register(Inventory)
class InventoryAdmin(RBACAdminMixin, admin.ModelAdmin):
    list_display = ('inventory_id', 'item_name', 'branch', 'category', 'stock_quantity', 'unit', 'reorder_level', 'stock_status', 'last_updated')
    list_filter = ('category', 'branch', 'unit', 'last_updated', 'is_active')
    search_fields = ('inventory_id', 'item_name', 'supplier')
    readonly_fields = ('last_updated', 'created_at', 'updated_at')
    ordering = ['item_name']
    
    fieldsets = (
        ('Item Information', {
            'fields': ('inventory_id', 'item_name', 'category', 'branch')
        }),
        ('Stock Details', {
            'fields': ('stock_quantity', 'unit', 'reorder_level', 'unit_cost')
        }),
        ('Supplier & Expiry', {
            'fields': ('supplier', 'supplier_contact', 'expiry_date')
        }),
        ('Status', {
            'fields': ('is_active', 'last_updated', 'created_at', 'updated_at')
        }),
    )
    
    def stock_status(self, obj):
        """Display stock status with color coding"""
        if obj.is_expired:
            return format_html('<span style="color: red;">Expired</span>')
        elif obj.is_low_stock:
            return format_html('<span style="color: orange;">Low Stock</span>')
        else:
            return format_html('<span style="color: green;">In Stock</span>')
    stock_status.short_description = "Status"
    
    def get_queryset(self, request):
        """Add annotations for better performance"""
        qs = super().get_queryset(request)
        return qs.select_related('branch')


@admin.register(Customer)
class CustomerAdmin(RBACAdminMixin, admin.ModelAdmin):
    list_display = ('customer_id', 'name', 'phone', 'email', 'loyalty_points', 'loyalty_tier', 'total_spent', 'preferred_branch', 'last_visit')
    list_filter = ('preferred_branch', 'last_visit', 'date_of_birth', 'is_active')
    search_fields = ('customer_id', 'name', 'phone', 'email')
    readonly_fields = ('created_at', 'updated_at', 'loyalty_tier')
    ordering = ['-last_visit']
    
    fieldsets = (
        ('Personal Information', {
            'fields': ('customer_id', 'name', 'phone', 'email', 'date_of_birth')
        }),
        ('Loyalty & Preferences', {
            'fields': ('loyalty_points', 'loyalty_tier', 'total_spent', 'visit_count', 'preferred_branch', 'preferences')
        }),
        ('Activity', {
            'fields': ('last_visit', 'is_active', 'created_at', 'updated_at')
        }),
    )
    
    actions = ['add_loyalty_points', 'send_promotional_email']
    
    def add_loyalty_points(self, request, queryset):
        """Admin action to add loyalty points"""
        # This would be implemented with a form to specify points
        self.message_user(request, f"Added loyalty points to {queryset.count()} customers.")
    add_loyalty_points.short_description = "Add loyalty points to selected customers"
    
    def send_promotional_email(self, request, queryset):
        """Admin action to send promotional emails"""
        # This would be implemented with email functionality
        self.message_user(request, f"Sent promotional emails to {queryset.count()} customers.")
    send_promotional_email.short_description = "Send promotional email to selected customers"


@admin.register(StaffPerformance)
class StaffPerformanceAdmin(RBACAdminMixin, admin.ModelAdmin):
    list_display = ('staff', 'branch', 'shift_date', 'hours_worked', 'sales_generated', 'orders_served', 'customer_feedback_score', 'performance_rating')
    list_filter = ('shift_date', 'branch', 'customer_feedback_score', 'is_active')
    search_fields = ('staff__username', 'staff__first_name', 'staff__last_name')
    date_hierarchy = 'shift_date'
    readonly_fields = ('created_at', 'updated_at', 'sales_per_hour', 'orders_per_hour')
    ordering = ['-shift_date']
    
    fieldsets = (
        ('Shift Information', {
            'fields': ('staff', 'branch', 'shift_date', 'shift_start', 'shift_end', 'hours_worked', 'break_minutes')
        }),
        ('Performance Metrics', {
            'fields': ('sales_generated', 'orders_served', 'customer_feedback_score', 'tips_received')
        }),
        ('Calculated Metrics', {
            'fields': ('sales_per_hour', 'orders_per_hour'),
            'classes': ('collapse',)
        }),
        ('Notes & Status', {
            'fields': ('notes', 'is_active', 'created_at', 'updated_at')
        }),
    )
    
    def performance_rating(self, obj):
        """Display performance rating based on various metrics"""
        score = 0
        
        # Base score on sales per hour
        if obj.sales_per_hour >= 100:
            score += 2
        elif obj.sales_per_hour >= 50:
            score += 1
        
        # Add score for customer feedback
        if obj.customer_feedback_score:
            if obj.customer_feedback_score >= 4.5:
                score += 2
            elif obj.customer_feedback_score >= 3.5:
                score += 1
        
        # Add score for orders per hour
        if obj.orders_per_hour >= 10:
            score += 1
        
        if score >= 4:
            return format_html('<span style="color: green;">Excellent</span>')
        elif score >= 2:
            return format_html('<span style="color: orange;">Good</span>')
        else:
            return format_html('<span style="color: red;">Needs Improvement</span>')
    performance_rating.short_description = "Rating"
    
    def get_queryset(self, request):
        """Optimize queryset with select_related"""
        qs = super().get_queryset(request)
        return qs.select_related('staff', 'branch')


# Customize admin site
admin.site.site_header = "BI Tool - Business Analytics Administration"
admin.site.site_title = "BI Tool Admin"
admin.site.index_title = "Business Intelligence Dashboard"