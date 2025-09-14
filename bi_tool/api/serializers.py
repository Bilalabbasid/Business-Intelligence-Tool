from rest_framework import serializers
from decimal import Decimal
from datetime import datetime, date
from django.utils import timezone
from django.contrib.auth import get_user_model

from analytics.models import Branch, Sales, Inventory, Customer, StaffPerformance, AuditLog, Location, SaleItem
from core.models import User

User = get_user_model()


class LocationSerializer(serializers.Serializer):
    """
    Serializer for embedded Location documents
    """
    address = serializers.CharField(max_length=255)
    city = serializers.CharField(max_length=100)
    state = serializers.CharField(max_length=100, required=False, allow_blank=True)
    postal_code = serializers.CharField(max_length=20, required=False, allow_blank=True)
    country = serializers.CharField(max_length=100)
    latitude = serializers.DecimalField(max_digits=10, decimal_places=8, required=False, allow_null=True)
    longitude = serializers.DecimalField(max_digits=11, decimal_places=8, required=False, allow_null=True)


class SaleItemSerializer(serializers.Serializer):
    """
    Serializer for embedded SaleItem documents
    """
    item_name = serializers.CharField(max_length=200)
    category = serializers.CharField(max_length=100, required=False, allow_blank=True)
    quantity = serializers.IntegerField(min_value=1)
    unit_price = serializers.DecimalField(max_digits=10, decimal_places=2, min_value=Decimal('0.01'))
    total = serializers.DecimalField(max_digits=10, decimal_places=2, min_value=Decimal('0.01'))
    discount = serializers.DecimalField(max_digits=10, decimal_places=2, min_value=Decimal('0.00'), default=Decimal('0.00'))
    
    def validate(self, data):
        """Validate that total equals (quantity * unit_price - discount)"""
        expected_total = (data['quantity'] * data['unit_price']) - data.get('discount', Decimal('0.00'))
        if data['total'] != expected_total:
            raise serializers.ValidationError({
                'total': f'Total must equal (quantity * unit_price - discount). Expected: {expected_total}'
            })
        return data


class BranchListSerializer(serializers.ModelSerializer):
    """
    Lightweight serializer for branch list views
    """
    manager_name = serializers.CharField(source='manager.get_full_name', read_only=True)
    location_display = serializers.SerializerMethodField()
    
    class Meta:
        model = Branch
        fields = [
            'id', 'branch_id', 'name', 'manager_name', 'location_display',
            'phone', 'email', 'capacity', 'is_active', 'created_at'
        ]
        read_only_fields = ['id', 'created_at']
    
    def get_location_display(self, obj):
        if obj.location:
            return f"{obj.location.city}, {obj.location.country}"
        return None


class BranchDetailSerializer(serializers.ModelSerializer):
    """
    Detailed serializer for branch detail/create/update views
    """
    location = LocationSerializer()
    manager_details = serializers.SerializerMethodField()
    stats = serializers.SerializerMethodField()
    
    class Meta:
        model = Branch
        fields = [
            'id', 'branch_id', 'name', 'location', 'manager', 'manager_details',
            'phone', 'email', 'opening_hours', 'capacity', 'stats',
            'is_active', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at', 'stats']
    
    def get_manager_details(self, obj):
        if obj.manager:
            return {
                'id': obj.manager.id,
                'username': obj.manager.username,
                'full_name': obj.manager.get_full_name(),
                'email': obj.manager.email
            }
        return None
    
    def get_stats(self, obj):
        """Get basic branch statistics"""
        from django.db.models import Count, Sum
        
        # Get current date range for stats (last 30 days)
        end_date = timezone.now()
        start_date = end_date - timezone.timedelta(days=30)
        
        recent_sales = obj.sales.filter(date__gte=start_date, is_active=True)
        
        return {
            'total_customers': obj.preferred_customers.filter(is_active=True).count(),
            'inventory_items': obj.inventory_items.filter(is_active=True).count(),
            'recent_sales_count': recent_sales.count(),
            'recent_revenue': recent_sales.aggregate(Sum('total_amount'))['total_amount__sum'] or Decimal('0.00'),
            'staff_count': obj.staff_performances.values('staff').distinct().count()
        }
    
    def create(self, validated_data):
        location_data = validated_data.pop('location', {})
        branch = Branch.objects.create(**validated_data)
        
        # Set location if provided
        if location_data:
            for attr, value in location_data.items():
                setattr(branch.location, attr, value)
            branch.save()
        
        return branch
    
    def update(self, instance, validated_data):
        location_data = validated_data.pop('location', {})
        
        # Update branch fields
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        
        # Update location if provided
        if location_data:
            for attr, value in location_data.items():
                setattr(instance.location, attr, value)
        
        instance.save()
        return instance


class SalesListSerializer(serializers.ModelSerializer):
    """
    Serializer for sales list views
    """
    branch_name = serializers.CharField(source='branch.name', read_only=True)
    customer_name = serializers.CharField(source='customer.name', read_only=True)
    served_by_name = serializers.CharField(source='served_by.get_full_name', read_only=True)
    items_count = serializers.SerializerMethodField()
    
    class Meta:
        model = Sales
        fields = [
            'id', 'sale_id', 'branch_name', 'date', 'total_amount',
            'payment_method', 'order_type', 'customer_name', 'served_by_name',
            'items_count', 'is_active'
        ]
    
    def get_items_count(self, obj):
        return len(obj.items) if obj.items else 0


class SalesDetailSerializer(serializers.ModelSerializer):
    """
    Detailed serializer for sales detail/create/update views
    """
    items = SaleItemSerializer(many=True)
    branch_details = BranchListSerializer(source='branch', read_only=True)
    customer_details = serializers.SerializerMethodField()
    served_by_details = serializers.SerializerMethodField()
    
    class Meta:
        model = Sales
        fields = [
            'id', 'sale_id', 'branch', 'branch_details', 'date', 'items',
            'total_amount', 'tax_amount', 'discount_amount', 'payment_method',
            'order_type', 'customer', 'customer_details', 'served_by', 'served_by_details',
            'is_active', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']
    
    def get_customer_details(self, obj):
        if obj.customer:
            return {
                'id': obj.customer.id,
                'name': obj.customer.name,
                'phone': obj.customer.phone,
                'loyalty_points': obj.customer.loyalty_points
            }
        return None
    
    def get_served_by_details(self, obj):
        if obj.served_by:
            return {
                'id': obj.served_by.id,
                'username': obj.served_by.username,
                'full_name': obj.served_by.get_full_name()
            }
        return None
    
    def validate(self, data):
        """Validate sales data"""
        items = data.get('items', [])
        if not items:
            raise serializers.ValidationError({'items': 'At least one item is required'})
        
        # Validate total amount matches items
        expected_total = sum(item['total'] for item in items)
        expected_total -= data.get('discount_amount', Decimal('0.00'))
        expected_total += data.get('tax_amount', Decimal('0.00'))
        
        if abs(data['total_amount'] - expected_total) > Decimal('0.01'):  # Allow for small rounding differences
            raise serializers.ValidationError({
                'total_amount': f'Total amount should be {expected_total} based on items'
            })
        
        return data
    
    def create(self, validated_data):
        items_data = validated_data.pop('items')
        sale = Sales.objects.create(**validated_data)
        
        # Items are already embedded, no need to create separately
        return sale


class InventoryListSerializer(serializers.ModelSerializer):
    """
    Serializer for inventory list views
    """
    branch_name = serializers.CharField(source='branch.name', read_only=True)
    stock_status = serializers.SerializerMethodField()
    
    class Meta:
        model = Inventory
        fields = [
            'id', 'inventory_id', 'branch_name', 'item_name', 'category',
            'stock_quantity', 'unit', 'reorder_level', 'stock_status',
            'supplier', 'last_updated', 'is_active'
        ]
    
    def get_stock_status(self, obj):
        if obj.is_expired:
            return 'expired'
        elif obj.is_low_stock:
            return 'low_stock'
        else:
            return 'in_stock'


class InventoryDetailSerializer(serializers.ModelSerializer):
    """
    Detailed serializer for inventory detail/create/update views
    """
    branch_details = BranchListSerializer(source='branch', read_only=True)
    stock_status = serializers.SerializerMethodField()
    
    class Meta:
        model = Inventory
        fields = [
            'id', 'inventory_id', 'branch', 'branch_details', 'item_name',
            'category', 'stock_quantity', 'unit', 'reorder_level', 'unit_cost',
            'supplier', 'supplier_contact', 'expiry_date', 'stock_status',
            'is_active', 'last_updated', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'last_updated', 'created_at', 'updated_at']
    
    def get_stock_status(self, obj):
        status = {
            'is_low_stock': obj.is_low_stock,
            'is_expired': obj.is_expired,
            'status': 'in_stock'
        }
        
        if obj.is_expired:
            status['status'] = 'expired'
        elif obj.is_low_stock:
            status['status'] = 'low_stock'
        
        return status
    
    def validate_stock_quantity(self, value):
        """Ensure stock quantity is not negative"""
        if value < 0:
            raise serializers.ValidationError("Stock quantity cannot be negative")
        return value


class CustomerListSerializer(serializers.ModelSerializer):
    """
    Serializer for customer list views
    """
    preferred_branch_name = serializers.CharField(source='preferred_branch.name', read_only=True)
    loyalty_tier = serializers.CharField(read_only=True)
    
    class Meta:
        model = Customer
        fields = [
            'id', 'customer_id', 'name', 'phone', 'email', 'loyalty_points',
            'loyalty_tier', 'total_spent', 'visit_count', 'preferred_branch_name',
            'last_visit', 'is_active'
        ]


class CustomerDetailSerializer(serializers.ModelSerializer):
    """
    Detailed serializer for customer detail/create/update views
    """
    preferred_branch_details = BranchListSerializer(source='preferred_branch', read_only=True)
    loyalty_tier = serializers.CharField(read_only=True)
    recent_purchases = serializers.SerializerMethodField()
    
    class Meta:
        model = Customer
        fields = [
            'id', 'customer_id', 'name', 'email', 'phone', 'date_of_birth',
            'loyalty_points', 'loyalty_tier', 'total_spent', 'visit_count',
            'preferred_branch', 'preferred_branch_details', 'preferences',
            'last_visit', 'recent_purchases', 'is_active', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'customer_id', 'total_spent', 'visit_count', 'last_visit', 'created_at', 'updated_at']
    
    def get_recent_purchases(self, obj):
        """Get recent purchases for this customer"""
        recent_sales = obj.sales.filter(is_active=True).order_by('-date')[:5]
        return SalesListSerializer(recent_sales, many=True).data


class StaffPerformanceListSerializer(serializers.ModelSerializer):
    """
    Serializer for staff performance list views
    """
    staff_name = serializers.CharField(source='staff.get_full_name', read_only=True)
    branch_name = serializers.CharField(source='branch.name', read_only=True)
    performance_score = serializers.SerializerMethodField()
    
    class Meta:
        model = StaffPerformance
        fields = [
            'id', 'staff_name', 'branch_name', 'shift_date', 'hours_worked',
            'sales_generated', 'orders_served', 'customer_feedback_score',
            'performance_score', 'is_active'
        ]
    
    def get_performance_score(self, obj):
        """Calculate a simple performance score"""
        score = 0
        if obj.sales_per_hour >= 100:
            score += 30
        elif obj.sales_per_hour >= 50:
            score += 20
        elif obj.sales_per_hour >= 25:
            score += 10
        
        if obj.customer_feedback_score:
            score += int(obj.customer_feedback_score * 10)  # 0-50 points
        
        if obj.orders_per_hour >= 10:
            score += 20
        elif obj.orders_per_hour >= 5:
            score += 10
        
        return min(score, 100)  # Cap at 100


class StaffPerformanceDetailSerializer(serializers.ModelSerializer):
    """
    Detailed serializer for staff performance detail/create/update views
    """
    staff_details = serializers.SerializerMethodField()
    branch_details = BranchListSerializer(source='branch', read_only=True)
    calculated_metrics = serializers.SerializerMethodField()
    
    class Meta:
        model = StaffPerformance
        fields = [
            'id', 'staff', 'staff_details', 'branch', 'branch_details',
            'shift_date', 'shift_start', 'shift_end', 'hours_worked',
            'sales_generated', 'orders_served', 'customer_feedback_score',
            'tips_received', 'break_minutes', 'notes', 'calculated_metrics',
            'is_active', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']
    
    def get_staff_details(self, obj):
        return {
            'id': obj.staff.id,
            'username': obj.staff.username,
            'full_name': obj.staff.get_full_name(),
            'email': obj.staff.email
        }
    
    def get_calculated_metrics(self, obj):
        return {
            'sales_per_hour': obj.sales_per_hour,
            'orders_per_hour': obj.orders_per_hour,
            'performance_score': StaffPerformanceListSerializer.get_performance_score(StaffPerformanceListSerializer(), obj)
        }
    
    def validate(self, data):
        """Validate performance data"""
        if data['shift_end'] <= data['shift_start']:
            raise serializers.ValidationError({
                'shift_end': 'Shift end time must be after start time'
            })
        
        if data.get('customer_feedback_score') and (data['customer_feedback_score'] < 0 or data['customer_feedback_score'] > 5):
            raise serializers.ValidationError({
                'customer_feedback_score': 'Customer feedback score must be between 0 and 5'
            })
        
        return data


class AuditLogSerializer(serializers.ModelSerializer):
    """
    Serializer for audit log entries
    """
    user_details = serializers.SerializerMethodField()
    changes_summary = serializers.CharField(source='get_changes_summary', read_only=True)
    
    class Meta:
        model = AuditLog
        fields = [
            'id', 'action', 'model_name', 'model_record_id', 'user_details',
            'user_role', 'branch_id', 'changes', 'changes_summary',
            'ip_address', 'endpoint', 'request_method', 'status_code',
            'timestamp'
        ]
        read_only_fields = ['id', 'timestamp']
    
    def get_user_details(self, obj):
        if obj.user:
            return {
                'id': obj.user.id,
                'username': obj.user.username,
                'full_name': obj.user.get_full_name()
            }
        return None


# Utility serializers for common operations

class BulkInventoryUpdateSerializer(serializers.Serializer):
    """
    Serializer for bulk inventory updates
    """
    updates = serializers.ListField(
        child=serializers.DictField(
            child=serializers.CharField()
        ),
        min_length=1
    )
    
    def validate_updates(self, value):
        """Validate bulk update data"""
        required_fields = ['inventory_id', 'stock_quantity']
        
        for update in value:
            for field in required_fields:
                if field not in update:
                    raise serializers.ValidationError(f"Each update must include {field}")
            
            # Validate stock quantity
            try:
                stock_qty = Decimal(update['stock_quantity'])
                if stock_qty < 0:
                    raise serializers.ValidationError(f"Stock quantity cannot be negative for {update['inventory_id']}")
            except (ValueError, TypeError):
                raise serializers.ValidationError(f"Invalid stock quantity for {update['inventory_id']}")
        
        return value


class DateRangeFilterSerializer(serializers.Serializer):
    """
    Serializer for date range filtering
    """
    start_date = serializers.DateField(required=False)
    end_date = serializers.DateField(required=False)
    
    def validate(self, data):
        start_date = data.get('start_date')
        end_date = data.get('end_date')
        
        if start_date and end_date and start_date > end_date:
            raise serializers.ValidationError("start_date must be before end_date")
        
        return data