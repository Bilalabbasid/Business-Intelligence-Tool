from django.db import models
from django.utils import timezone
from django.core.validators import MinValueValidator, MaxValueValidator, EmailValidator
from django.core.exceptions import ValidationError
from djongo import models as djongo_models
import uuid
import json
from decimal import Decimal


class BaseModel(models.Model):
    """
    Abstract base model with common fields for all business entities
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    is_active = models.BooleanField(default=True, help_text='Soft delete flag')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        abstract = True
        
    def soft_delete(self):
        """Perform soft delete by setting is_active to False"""
        self.is_active = False
        self.save(update_fields=['is_active', 'updated_at'])


class Location(djongo_models.Model):
    """
    Embedded document for location information
    """
    address = models.CharField(max_length=255)
    city = models.CharField(max_length=100)
    state = models.CharField(max_length=100, blank=True)
    postal_code = models.CharField(max_length=20, blank=True)
    country = models.CharField(max_length=100)
    latitude = models.DecimalField(max_digits=10, decimal_places=8, null=True, blank=True)
    longitude = models.DecimalField(max_digits=11, decimal_places=8, null=True, blank=True)
    
    class Meta:
        abstract = True
    
    def __str__(self):
        return f"{self.address}, {self.city}, {self.country}"


class Branch(BaseModel):
    """
    Restaurant branch model
    """
    branch_id = models.CharField(
        max_length=50, 
        unique=True, 
        help_text='Unique branch identifier'
    )
    name = models.CharField(max_length=200)
    location = djongo_models.EmbeddedField(
        model_container=Location,
        help_text='Branch location details'
    )
    manager = models.ForeignKey(
        'core.User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        limit_choices_to={'role': 'manager'},
        related_name='managed_branches',
        help_text='Branch manager'
    )
    phone = models.CharField(max_length=20, blank=True)
    email = models.EmailField(blank=True)
    opening_hours = models.JSONField(
        default=dict,
        help_text='Store opening hours in JSON format'
    )
    capacity = models.PositiveIntegerField(
        null=True, 
        blank=True,
        help_text='Maximum seating capacity'
    )
    
    class Meta:
        db_table = 'branches'
        verbose_name = 'Branch'
        verbose_name_plural = 'Branches'
        ordering = ['name']
        indexes = [
            models.Index(fields=['branch_id']),
            models.Index(fields=['name']),
            models.Index(fields=['manager']),
            models.Index(fields=['is_active']),
        ]
    
    def __str__(self):
        return f"{self.name} ({self.branch_id})"
    
    def clean(self):
        """Validate branch data"""
        if self.manager and self.manager.role != 'manager':
            raise ValidationError({
                'manager': 'Selected user must have manager role.'
            })
        
        if self.manager and self.manager.branch_id and self.manager.branch_id != self.branch_id:
            raise ValidationError({
                'manager': 'Manager is already assigned to another branch.'
            })


class SaleItem(djongo_models.Model):
    """
    Embedded document for individual sale items
    """
    item_name = models.CharField(max_length=200)
    category = models.CharField(max_length=100, blank=True)
    quantity = models.PositiveIntegerField(validators=[MinValueValidator(1)])
    unit_price = models.DecimalField(
        max_digits=10, 
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.01'))]
    )
    total = models.DecimalField(
        max_digits=10, 
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.01'))]
    )
    discount = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        default=Decimal('0.00'),
        validators=[MinValueValidator(Decimal('0.00'))]
    )
    
    class Meta:
        abstract = True
    
    def clean(self):
        """Validate item data"""
        if self.total != (self.quantity * self.unit_price - self.discount):
            raise ValidationError('Total must equal (quantity * unit_price - discount)')
    
    def __str__(self):
        return f"{self.item_name} x{self.quantity}"


class Sales(BaseModel):
    """
    Sales transaction model
    """
    PAYMENT_METHODS = [
        ('cash', 'Cash'),
        ('card', 'Credit/Debit Card'),
        ('online', 'Online Payment'),
        ('loyalty', 'Loyalty Points'),
        ('voucher', 'Voucher/Gift Card'),
    ]
    
    sale_id = models.CharField(
        max_length=50, 
        unique=True,
        help_text='Unique sale identifier'
    )
    branch = models.ForeignKey(
        Branch,
        on_delete=models.CASCADE,
        related_name='sales'
    )
    date = models.DateTimeField(default=timezone.now)
    items = djongo_models.ArrayField(
        model_container=SaleItem,
        help_text='List of items in the sale'
    )
    total_amount = models.DecimalField(
        max_digits=12, 
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.01'))]
    )
    tax_amount = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        default=Decimal('0.00')
    )
    discount_amount = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        default=Decimal('0.00')
    )
    payment_method = models.CharField(
        max_length=20, 
        choices=PAYMENT_METHODS,
        default='cash'
    )
    customer = models.ForeignKey(
        'Customer',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='sales'
    )
    served_by = models.ForeignKey(
        'core.User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        limit_choices_to={'role': 'staff'},
        related_name='served_sales'
    )
    order_type = models.CharField(
        max_length=20,
        choices=[
            ('dine_in', 'Dine In'),
            ('takeaway', 'Takeaway'),
            ('delivery', 'Delivery'),
            ('online', 'Online Order'),
        ],
        default='dine_in'
    )
    
    class Meta:
        db_table = 'sales'
        verbose_name = 'Sale'
        verbose_name_plural = 'Sales'
        ordering = ['-date']
        indexes = [
            models.Index(fields=['sale_id']),
            models.Index(fields=['branch', 'date']),
            models.Index(fields=['date']),
            models.Index(fields=['customer']),
            models.Index(fields=['payment_method']),
            models.Index(fields=['served_by']),
            models.Index(fields=['is_active']),
        ]
    
    def __str__(self):
        return f"Sale {self.sale_id} - {self.branch.name} - ${self.total_amount}"
    
    def clean(self):
        """Validate sales data"""
        if self.served_by and self.served_by.role != 'staff':
            raise ValidationError({
                'served_by': 'Selected user must have staff role.'
            })


class Inventory(BaseModel):
    """
    Inventory management model
    """
    CATEGORIES = [
        ('food', 'Food Items'),
        ('beverage', 'Beverages'),
        ('packaging', 'Packaging Materials'),
        ('cleaning', 'Cleaning Supplies'),
        ('equipment', 'Equipment & Utensils'),
        ('other', 'Other'),
    ]
    
    UNITS = [
        ('kg', 'Kilograms'),
        ('g', 'Grams'),
        ('l', 'Liters'),
        ('ml', 'Milliliters'),
        ('pcs', 'Pieces'),
        ('box', 'Boxes'),
        ('pack', 'Packs'),
        ('bottle', 'Bottles'),
        ('can', 'Cans'),
    ]
    
    inventory_id = models.CharField(
        max_length=50, 
        unique=True,
        help_text='Unique inventory identifier'
    )
    branch = models.ForeignKey(
        Branch,
        on_delete=models.CASCADE,
        related_name='inventory_items'
    )
    item_name = models.CharField(max_length=200)
    category = models.CharField(max_length=20, choices=CATEGORIES)
    stock_quantity = models.DecimalField(
        max_digits=10, 
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.00'))]
    )
    unit = models.CharField(max_length=20, choices=UNITS, default='pcs')
    reorder_level = models.DecimalField(
        max_digits=10, 
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.00'))],
        help_text='Minimum stock threshold for reordering'
    )
    unit_cost = models.DecimalField(
        max_digits=10, 
        decimal_places=2,
        null=True,
        blank=True
    )
    supplier = models.CharField(max_length=200, blank=True)
    supplier_contact = models.JSONField(
        default=dict,
        help_text='Supplier contact information'
    )
    expiry_date = models.DateField(null=True, blank=True)
    last_updated = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'inventory'
        verbose_name = 'Inventory Item'
        verbose_name_plural = 'Inventory Items'
        ordering = ['item_name']
        unique_together = ['branch', 'item_name']
        indexes = [
            models.Index(fields=['inventory_id']),
            models.Index(fields=['branch', 'category']),
            models.Index(fields=['item_name']),
            models.Index(fields=['category']),
            models.Index(fields=['reorder_level']),
            models.Index(fields=['last_updated']),
            models.Index(fields=['is_active']),
        ]
    
    def __str__(self):
        return f"{self.item_name} - {self.branch.name} ({self.stock_quantity} {self.unit})"
    
    @property
    def is_low_stock(self):
        """Check if item is below reorder level"""
        return self.stock_quantity <= self.reorder_level
    
    @property
    def is_expired(self):
        """Check if item has expired"""
        if self.expiry_date:
            return timezone.now().date() > self.expiry_date
        return False


class Customer(BaseModel):
    """
    Customer model for loyalty and analytics
    """
    customer_id = models.CharField(
        max_length=50, 
        unique=True,
        help_text='Unique customer identifier'
    )
    name = models.CharField(max_length=200)
    email = models.EmailField(
        validators=[EmailValidator()],
        null=True,
        blank=True
    )
    phone = models.CharField(max_length=20, unique=True)
    date_of_birth = models.DateField(null=True, blank=True)
    loyalty_points = models.PositiveIntegerField(default=0)
    total_spent = models.DecimalField(
        max_digits=12, 
        decimal_places=2, 
        default=Decimal('0.00')
    )
    visit_count = models.PositiveIntegerField(default=0)
    preferred_branch = models.ForeignKey(
        Branch,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='preferred_customers'
    )
    preferences = models.JSONField(
        default=dict,
        help_text='Customer preferences (dietary, favorite items, etc.)'
    )
    last_visit = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        db_table = 'customers'
        verbose_name = 'Customer'
        verbose_name_plural = 'Customers'
        ordering = ['-last_visit']
        indexes = [
            models.Index(fields=['customer_id']),
            models.Index(fields=['phone']),
            models.Index(fields=['email']),
            models.Index(fields=['preferred_branch']),
            models.Index(fields=['loyalty_points']),
            models.Index(fields=['last_visit']),
            models.Index(fields=['is_active']),
        ]
    
    def __str__(self):
        return f"{self.name} ({self.customer_id})"
    
    def add_loyalty_points(self, points):
        """Add loyalty points to customer"""
        self.loyalty_points += points
        self.save(update_fields=['loyalty_points', 'updated_at'])
    
    def redeem_loyalty_points(self, points):
        """Redeem loyalty points"""
        if self.loyalty_points >= points:
            self.loyalty_points -= points
            self.save(update_fields=['loyalty_points', 'updated_at'])
            return True
        return False
    
    @property
    def loyalty_tier(self):
        """Calculate customer loyalty tier based on total spent"""
        if self.total_spent >= 1000:
            return 'Gold'
        elif self.total_spent >= 500:
            return 'Silver'
        elif self.total_spent >= 100:
            return 'Bronze'
        return 'Basic'


class StaffPerformance(BaseModel):
    """
    Staff performance tracking model
    """
    staff = models.ForeignKey(
        'core.User',
        on_delete=models.CASCADE,
        limit_choices_to={'role': 'staff'},
        related_name='performance_records'
    )
    branch = models.ForeignKey(
        Branch,
        on_delete=models.CASCADE,
        related_name='staff_performances'
    )
    shift_date = models.DateField()
    shift_start = models.TimeField()
    shift_end = models.TimeField()
    hours_worked = models.DecimalField(
        max_digits=4, 
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.00'))]
    )
    sales_generated = models.DecimalField(
        max_digits=12, 
        decimal_places=2, 
        default=Decimal('0.00')
    )
    orders_served = models.PositiveIntegerField(default=0)
    customer_feedback_score = models.DecimalField(
        max_digits=3, 
        decimal_places=2,
        null=True,
        blank=True,
        validators=[MinValueValidator(Decimal('0.00')), MaxValueValidator(Decimal('5.00'))],
        help_text='Average customer feedback score (0-5)'
    )
    tips_received = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        default=Decimal('0.00')
    )
    break_minutes = models.PositiveIntegerField(
        default=0,
        help_text='Total break time in minutes'
    )
    notes = models.TextField(blank=True)
    
    class Meta:
        db_table = 'staff_performance'
        verbose_name = 'Staff Performance'
        verbose_name_plural = 'Staff Performances'
        ordering = ['-shift_date', '-shift_start']
        unique_together = ['staff', 'branch', 'shift_date', 'shift_start']
        indexes = [
            models.Index(fields=['staff', 'shift_date']),
            models.Index(fields=['branch', 'shift_date']),
            models.Index(fields=['shift_date']),
            models.Index(fields=['customer_feedback_score']),
            models.Index(fields=['is_active']),
        ]
    
    def __str__(self):
        return f"{self.staff.username} - {self.branch.name} - {self.shift_date}"
    
    def clean(self):
        """Validate performance data"""
        if self.staff.role != 'staff':
            raise ValidationError({
                'staff': 'Selected user must have staff role.'
            })
        
        if self.shift_end <= self.shift_start:
            raise ValidationError({
                'shift_end': 'Shift end time must be after start time.'
            })
    
    @property
    def sales_per_hour(self):
        """Calculate sales per hour"""
        if self.hours_worked > 0:
            return self.sales_generated / self.hours_worked
        return Decimal('0.00')
    
    @property
    def orders_per_hour(self):
        """Calculate orders per hour"""
        if self.hours_worked > 0:
            return self.orders_served / float(self.hours_worked)
        return 0.0


class AuditLog(models.Model):
    """
    Audit log model to track all CRUD operations for compliance and security
    """
    ACTION_CHOICES = [
        ('create', 'Create'),
        ('update', 'Update'),
        ('delete', 'Delete'),
        ('view', 'View'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    action = models.CharField(max_length=10, choices=ACTION_CHOICES)
    model_name = models.CharField(max_length=100, help_text='Name of the model affected')
    model_record_id = models.CharField(max_length=255, help_text='ID of the affected record')
    user = models.ForeignKey(
        'core.User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='audit_logs'
    )
    user_role = models.CharField(max_length=20, help_text='Role of user at time of action')
    branch_id = models.CharField(
        max_length=100,
        null=True,
        blank=True,
        help_text='Branch context if applicable'
    )
    changes = models.JSONField(
        default=dict,
        help_text='JSON object containing before/after values for updates'
    )
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True)
    timestamp = models.DateTimeField(auto_now_add=True)
    
    # Additional context fields
    endpoint = models.CharField(max_length=200, blank=True, help_text='API endpoint accessed')
    request_method = models.CharField(max_length=10, blank=True)
    status_code = models.PositiveIntegerField(null=True, blank=True)
    
    class Meta:
        db_table = 'audit_logs'
        verbose_name = 'Audit Log'
        verbose_name_plural = 'Audit Logs'
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['model_name', 'timestamp']),
            models.Index(fields=['user', 'timestamp']),
            models.Index(fields=['action', 'timestamp']),
            models.Index(fields=['branch_id', 'timestamp']),
            models.Index(fields=['timestamp']),
        ]
    
    def __str__(self):
        user_info = f"{self.user.username} ({self.user_role})" if self.user else "Anonymous"
        return f"{self.action.title()} {self.model_name} by {user_info} at {self.timestamp}"
    
    @classmethod
    def log_action(cls, action, model_instance, user=None, request=None, changes=None):
        """
        Helper method to create audit log entries
        """
        try:
            # Get model information
            model_name = model_instance.__class__.__name__
            model_id = str(model_instance.pk) if hasattr(model_instance, 'pk') else 'unknown'
            
            # Get user information
            user_role = getattr(user, 'role', 'anonymous') if user else 'anonymous'
            branch_id = getattr(user, 'branch_id', None) if user else None
            
            # Get request information
            ip_address = None
            user_agent = ''
            endpoint = ''
            method = ''
            
            if request:
                ip_address = cls._get_client_ip(request)
                user_agent = request.META.get('HTTP_USER_AGENT', '')[:500]
                endpoint = request.path
                method = request.method
            
            # Create audit log entry
            audit_entry = cls.objects.create(
                action=action,
                model_name=model_name,
                model_record_id=model_id,
                user=user,
                user_role=user_role,
                branch_id=branch_id,
                changes=changes or {},
                ip_address=ip_address,
                user_agent=user_agent,
                endpoint=endpoint,
                request_method=method
            )
            
            return audit_entry
            
        except Exception as e:
            # Log error but don't break the main operation
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Failed to create audit log: {str(e)}")
            return None
    
    @staticmethod
    def _get_client_ip(request):
        """Get client IP address from request"""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            return x_forwarded_for.split(',')[0].strip()
        return request.META.get('REMOTE_ADDR')
    
    def get_changes_summary(self):
        """Get a human-readable summary of changes"""
        if not self.changes or self.action != 'update':
            return ''
        
        changes_list = []
        for field, change_data in self.changes.items():
            if isinstance(change_data, dict) and 'old' in change_data and 'new' in change_data:
                old_val = change_data['old']
                new_val = change_data['new']
                changes_list.append(f"{field}: '{old_val}' → '{new_val}'")
            else:
                changes_list.append(f"{field}: {change_data}")
        
        return '; '.join(changes_list)