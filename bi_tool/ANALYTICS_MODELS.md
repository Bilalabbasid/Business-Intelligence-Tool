# Analytics Models Documentation

## Overview

The `analytics` app contains the core business data models for the BI tool, designed for restaurant chains with multiple branches. All models follow MongoDB document structure using Djongo and include comprehensive RBAC (Role-Based Access Control) support.

## Model Architecture

### Base Model

All models inherit from `BaseModel` which provides:
- UUID primary key
- Soft delete functionality (`is_active` flag)
- Automatic timestamps (`created_at`, `updated_at`)
- Common indexing patterns

### Role-Based Access Control

Models are designed with the following access patterns:

- **Super Admin**: Full access to all branches and data
- **Manager**: Access only to their assigned branch data
- **Analyst**: Read-only access to all branches for reporting
- **Staff**: Very limited access, only to their own performance records

## Models

### 1. Branch Model

**Purpose**: Represents restaurant branches/locations

**Key Features**:
- Embedded location document with GPS coordinates
- Branch manager assignment with role validation
- Opening hours stored as JSON
- Capacity tracking for seating management

**Fields**:
- `branch_id`: Unique identifier (indexed)
- `name`: Branch name
- `location`: Embedded Location document
- `manager`: ForeignKey to User (role=manager)
- `phone`, `email`: Contact information
- `opening_hours`: JSON field for flexible hour storage
- `capacity`: Maximum seating capacity

**Indexes**:
- `branch_id`, `name`, `manager`, `is_active`

**Validation**:
- Manager must have 'manager' role
- Manager can only be assigned to one branch

### 2. Sales Model

**Purpose**: Transaction records with embedded item details

**Key Features**:
- Embedded array of sale items using MongoDB arrays
- Multiple payment method support
- Customer loyalty integration
- Staff performance tracking integration
- Automatic inventory updates via signals

**Fields**:
- `sale_id`: Unique transaction identifier
- `branch`: ForeignKey to Branch
- `date`: Transaction timestamp
- `items`: ArrayField of embedded SaleItem documents
- `total_amount`, `tax_amount`, `discount_amount`: Financial tracking
- `payment_method`: Payment type (cash, card, online, etc.)
- `customer`: Optional customer reference
- `served_by`: Staff member who served (role=staff)
- `order_type`: Order classification (dine_in, takeaway, etc.)

**Embedded SaleItem Fields**:
- `item_name`, `category`: Item identification
- `quantity`, `unit_price`, `total`, `discount`: Pricing details

**Indexes**:
- `sale_id`, `branch+date`, `date`, `customer`, `payment_method`, `served_by`

**Auto-Generated IDs**: Format: `{BRANCH_PREFIX}_{YYYYMMDD}_{TIMESTAMP}`

### 3. Inventory Model

**Purpose**: Stock management and supply chain tracking

**Key Features**:
- Low stock alerts and reorder level tracking
- Expiry date management for perishables
- Supplier contact information
- Category-based organization
- Automatic stock updates from sales

**Fields**:
- `inventory_id`: Unique item identifier
- `branch`: ForeignKey to Branch
- `item_name`: Product name
- `category`: Item classification (food, beverage, packaging, etc.)
- `stock_quantity`: Current stock level
- `unit`: Measurement unit (kg, pcs, bottles, etc.)
- `reorder_level`: Minimum stock threshold
- `unit_cost`: Cost tracking
- `supplier`: Supplier name
- `supplier_contact`: JSON field for contact details
- `expiry_date`: For perishable items

**Indexes**:
- `inventory_id`, `branch+category`, `item_name`, `category`, `reorder_level`, `last_updated`

**Properties**:
- `is_low_stock`: Boolean check against reorder level
- `is_expired`: Date comparison for expired items

### 4. Customer Model

**Purpose**: Customer relationship management and loyalty tracking

**Key Features**:
- Loyalty points system with automatic point accumulation
- Purchase history tracking
- Branch preference management
- Customer segmentation via loyalty tiers
- Privacy-compliant data storage

**Fields**:
- `customer_id`: Unique customer identifier
- `name`: Customer full name
- `email`: Email address (optional, validated)
- `phone`: Primary contact (required, unique)
- `date_of_birth`: For birthday promotions
- `loyalty_points`: Accumulated reward points
- `total_spent`: Lifetime purchase value
- `visit_count`: Number of visits
- `preferred_branch`: Most frequently visited branch
- `preferences`: JSON field for dietary preferences, favorites
- `last_visit`: Last transaction date

**Indexes**:
- `customer_id`, `phone`, `email`, `preferred_branch`, `loyalty_points`, `last_visit`

**Methods**:
- `add_loyalty_points(points)`: Add reward points
- `redeem_loyalty_points(points)`: Redeem points with validation
- `loyalty_tier`: Property calculating tier based on spend (Basic, Bronze, Silver, Gold)

### 5. StaffPerformance Model

**Purpose**: Employee performance tracking and analytics

**Key Features**:
- Shift-based tracking with precise timing
- Sales performance metrics
- Customer feedback integration
- Productivity calculations
- Tips tracking for service evaluation

**Fields**:
- `staff`: ForeignKey to User (role=staff)
- `branch`: ForeignKey to Branch
- `shift_date`: Work date
- `shift_start`, `shift_end`: Precise timing
- `hours_worked`: Calculated work duration
- `sales_generated`: Revenue attributed to staff
- `orders_served`: Number of orders handled
- `customer_feedback_score`: Average rating (0-5)
- `tips_received`: Service quality indicator
- `break_minutes`: Break time tracking
- `notes`: Manager notes or observations

**Indexes**:
- `staff+shift_date`, `branch+shift_date`, `shift_date`, `customer_feedback_score`

**Unique Constraints**:
- `(staff, branch, shift_date, shift_start)` - Prevents duplicate shifts

**Calculated Properties**:
- `sales_per_hour`: Revenue efficiency
- `orders_per_hour`: Service speed metric

## MongoDB Integration

### Djongo Configuration

Models use Djongo for seamless Django ORM integration with MongoDB:

```python
DATABASES = {
    'default': {
        'ENGINE': 'djongo',
        'NAME': 'bi_tool_db',
        'CLIENT': {
            'host': 'mongodb://localhost:27017',
            'username': '',
            'password': '',
            'authSource': 'admin',
        }
    }
}
```

### Embedded Documents

**Location Document** (used in Branch):
```python
{
    "address": "123 Main St",
    "city": "New York",
    "state": "NY",
    "postal_code": "10001",
    "country": "USA",
    "latitude": 40.7128,
    "longitude": -74.0060
}
```

**SaleItem Document** (used in Sales):
```python
{
    "item_name": "Margherita Pizza",
    "category": "Pizza",
    "quantity": 2,
    "unit_price": 12.99,
    "total": 25.98,
    "discount": 0.00
}
```

### Database Indexes

Optimized for common query patterns:

```python
# Branch queries by location and manager
db.branches.createIndex({"branch_id": 1})
db.branches.createIndex({"manager": 1, "is_active": 1})

# Sales queries by date and branch
db.sales.createIndex({"branch": 1, "date": -1})
db.sales.createIndex({"date": -1, "is_active": 1})

# Inventory queries for stock management
db.inventory.createIndex({"branch": 1, "category": 1})
db.inventory.createIndex({"reorder_level": 1, "stock_quantity": 1})

# Customer queries for CRM
db.customers.createIndex({"phone": 1})
db.customers.createIndex({"loyalty_points": -1})

# Performance queries for HR analytics
db.staff_performance.createIndex({"staff": 1, "shift_date": -1})
db.staff_performance.createIndex({"branch": 1, "shift_date": -1})
```

## Signal Integration

Automated business logic through Django signals:

### Sales Processing
- **Customer Updates**: Automatically update total_spent, visit_count, loyalty_points
- **Inventory Updates**: Deduct stock quantities for sold items
- **Staff Performance**: Update sales_generated and orders_served metrics
- **Low Stock Alerts**: Log warnings when inventory drops below reorder level

### ID Generation
- **Customer ID**: Format `CUST_{phone_suffix}{timestamp}`
- **Sale ID**: Format `{branch_prefix}_{YYYYMMDD}_{timestamp}`
- **Inventory ID**: Format `{branch_prefix}_{category}_{timestamp}`

### Data Validation
- **Branch-Manager**: Ensure managers are properly assigned to branches
- **Stock Levels**: Validate sufficient inventory for sales
- **Shift Times**: Ensure logical shift start/end times

## RBAC Implementation

### Admin Interface Access

```python
class RBACAdminMixin:
    def get_queryset(self, request):
        # Super Admin: All data
        if request.user.role == User.SUPER_ADMIN:
            return qs
        
        # Manager: Only their branch data
        if request.user.role == User.MANAGER:
            return qs.filter(branch__branch_id=request.user.branch_id)
        
        # Analyst: All data (read-only)
        if request.user.role == User.ANALYST:
            return qs
        
        # Staff: Only their performance data
        if request.user.role == User.STAFF:
            return qs.filter(staff=request.user)
```

### API Access Control

Middleware and view-level permissions ensure data isolation:

```python
# Branch access validation
def can_access_branch(self, branch_id):
    if self.role in [User.SUPER_ADMIN, User.ANALYST]:
        return True
    return self.branch_id == branch_id
```

## Usage Examples

### Creating a Sale

```python
from analytics.models import Sales, SaleItem, Branch, Customer

# Create sale with embedded items
sale = Sales.objects.create(
    branch=branch,
    customer=customer,
    total_amount=Decimal('25.98'),
    payment_method='card',
    items=[
        SaleItem(
            item_name='Margherita Pizza',
            quantity=2,
            unit_price=Decimal('12.99'),
            total=Decimal('25.98')
        )
    ]
)
# Automatic signals will update customer loyalty, staff performance, and inventory
```

### Inventory Management

```python
from analytics.models import Inventory

# Check low stock items
low_stock_items = Inventory.objects.filter(
    stock_quantity__lte=models.F('reorder_level'),
    is_active=True
)

# Update stock levels
inventory_item = Inventory.objects.get(inventory_id='NYC_FOO_123456')
inventory_item.stock_quantity -= 5
inventory_item.save()  # Triggers low stock alert if needed
```

### Customer Analytics

```python
from analytics.models import Customer
from django.db.models import Sum, Count

# Customer segmentation by loyalty tier
gold_customers = Customer.objects.filter(total_spent__gte=1000)
silver_customers = Customer.objects.filter(total_spent__gte=500, total_spent__lt=1000)

# Top customers by spend
top_customers = Customer.objects.order_by('-total_spent')[:10]

# Customer visit patterns
frequent_visitors = Customer.objects.filter(visit_count__gte=10)
```

### Performance Analytics

```python
from analytics.models import StaffPerformance
from django.db.models import Avg, Sum

# Monthly staff performance
monthly_performance = StaffPerformance.objects.filter(
    shift_date__year=2025,
    shift_date__month=9
).aggregate(
    avg_sales=Avg('sales_generated'),
    total_hours=Sum('hours_worked'),
    avg_feedback=Avg('customer_feedback_score')
)

# Top performing staff
top_performers = StaffPerformance.objects.values('staff__username').annotate(
    total_sales=Sum('sales_generated'),
    avg_feedback=Avg('customer_feedback_score')
).order_by('-total_sales')
```

## Best Practices

### Data Integrity
- Always use model validation methods (`clean()`)
- Implement proper foreign key constraints
- Use soft delete for historical data preservation
- Validate embedded document data before saving

### Performance Optimization
- Use `select_related()` for foreign key queries
- Implement proper indexing for query patterns
- Use `aggregate()` functions for reporting queries
- Cache frequently accessed data (branch info, menu items)

### Security
- Always filter data by user's accessible branches
- Validate user permissions before data access
- Log all data modifications for audit trails
- Use environment variables for sensitive configuration

### Monitoring
- Monitor low stock alerts
- Track customer satisfaction scores
- Watch for unusual sales patterns
- Monitor staff performance trends