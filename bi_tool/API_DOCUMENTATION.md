# BI Tool REST API Documentation

## Overview
The BI Tool REST API provides comprehensive endpoints for managing business intelligence data including branches, sales, inventory, customers, and staff performance. The API implements Role-Based Access Control (RBAC) with JWT authentication.

## Authentication
All API endpoints require JWT authentication. Include the access token in the Authorization header:
```
Authorization: Bearer <your-access-token>
```

### Authentication Endpoints
- `POST /api/auth/register/` - User registration
- `POST /api/auth/login/` - User login (returns JWT tokens)
- `POST /api/auth/refresh/` - Refresh access token
- `POST /api/auth/logout/` - User logout
- `GET /api/auth/profile/` - Get user profile

## Role-Based Access Control (RBAC)

### Roles and Permissions

#### SUPER_ADMIN
- Full access to all endpoints and data across all branches
- Can create, read, update, and delete all resources
- Can access audit logs and system-wide analytics

#### MANAGER  
- Full access to their assigned branch's data
- Can manage branch information, sales, inventory, customers, and staff performance
- Can access audit logs for their branch
- Cannot access other branches' data

#### ANALYST
- Read-only access to their assigned branch's data
- Can view all analytics and reports for their branch
- Can access audit logs for their branch (read-only)
- Cannot modify data

#### STAFF
- Limited access focused on daily operations
- Can create sales records and view their own sales
- Can view and update inventory stock levels
- Can view and create customers
- Can view their own performance records
- Cannot access other staff members' detailed data

## API Endpoints

### Base URL
```
/api/v1/
```

### Branches
Manage branch information and locations.

#### List Branches
```
GET /api/v1/branches/
```

**Query Parameters:**
- `name` - Filter by branch name (case-insensitive)
- `city` - Filter by city (case-insensitive)
- `country` - Filter by country (case-insensitive)
- `manager` - Filter by manager username (case-insensitive)
- `is_active` - Filter by active status (true/false)
- `created_after` - Filter branches created after date (YYYY-MM-DD)
- `created_before` - Filter branches created before date (YYYY-MM-DD)
- `search` - Search across name, city, country, manager
- `ordering` - Order results by: name, created_at, location__city
- `page` - Page number
- `page_size` - Results per page (max 100)

**Response:**
```json
{
    "count": 25,
    "next": "http://api/v1/branches/?page=2",
    "previous": null,
    "results": [
        {
            "id": 1,
            "branch_id": "BR001",
            "name": "Downtown Branch",
            "manager_name": "John Doe",
            "location_display": "New York, USA",
            "phone": "+1-555-0123",
            "email": "downtown@company.com",
            "capacity": 50,
            "is_active": true,
            "created_at": "2023-01-15T10:30:00Z"
        }
    ]
}
```

#### Get Branch Details
```
GET /api/v1/branches/{id}/
```

**Response:**
```json
{
    "id": 1,
    "branch_id": "BR001",
    "name": "Downtown Branch",
    "location": {
        "address": "123 Main St",
        "city": "New York",
        "state": "NY",
        "postal_code": "10001",
        "country": "USA",
        "latitude": "40.7128",
        "longitude": "-74.0060"
    },
    "manager": 2,
    "manager_details": {
        "id": 2,
        "username": "john_doe",
        "full_name": "John Doe",
        "email": "john@company.com"
    },
    "phone": "+1-555-0123",
    "email": "downtown@company.com",
    "opening_hours": {
        "monday": "9:00-18:00",
        "tuesday": "9:00-18:00"
    },
    "capacity": 50,
    "stats": {
        "total_customers": 1250,
        "inventory_items": 89,
        "recent_sales_count": 45,
        "recent_revenue": "12500.00",
        "staff_count": 8
    },
    "is_active": true,
    "created_at": "2023-01-15T10:30:00Z",
    "updated_at": "2023-11-20T15:45:00Z"
}
```

#### Create Branch
```
POST /api/v1/branches/
```

**Request Body:**
```json
{
    "branch_id": "BR002",
    "name": "Uptown Branch",
    "location": {
        "address": "456 Oak Ave",
        "city": "New York",
        "state": "NY",
        "postal_code": "10025",
        "country": "USA"
    },
    "manager": 3,
    "phone": "+1-555-0124",
    "email": "uptown@company.com",
    "capacity": 75
}
```

#### Update Branch
```
PUT /api/v1/branches/{id}/
PATCH /api/v1/branches/{id}/
```

#### Get Branch Performance Summary
```
GET /api/v1/branches/{id}/performance_summary/
```

**Query Parameters:**
- `start_date` - Start date for metrics (YYYY-MM-DD)
- `end_date` - End date for metrics (YYYY-MM-DD)

### Sales
Manage sales transactions and revenue data.

#### List Sales
```
GET /api/v1/sales/
```

**Query Parameters:**
- `branch` - Filter by branch ID
- `branch_name` - Filter by branch name (case-insensitive)
- `date_from` - Filter sales from date (YYYY-MM-DD)
- `date_to` - Filter sales to date (YYYY-MM-DD)
- `payment_method` - Filter by payment method (CASH, CARD, ONLINE)
- `order_type` - Filter by order type (DINE_IN, TAKEOUT, DELIVERY)
- `customer` - Filter by customer ID
- `served_by` - Filter by staff username (case-insensitive)
- `total_amount_min` - Minimum total amount
- `total_amount_max` - Maximum total amount
- `is_active` - Filter by active status
- `search` - Search across sale_id, customer__name, served_by__username
- `ordering` - Order by: date, total_amount, created_at

#### Create Sale
```
POST /api/v1/sales/
```

**Request Body:**
```json
{
    "branch": 1,
    "date": "2023-11-20",
    "items": [
        {
            "item_name": "Coffee",
            "category": "Beverages",
            "quantity": 2,
            "unit_price": "4.50",
            "total": "9.00",
            "discount": "0.00"
        }
    ],
    "total_amount": "9.72",
    "tax_amount": "0.72",
    "discount_amount": "0.00",
    "payment_method": "CARD",
    "order_type": "DINE_IN",
    "customer": 15
}
```

#### Daily Sales Summary
```
GET /api/v1/sales/daily_summary/?date=2023-11-20
```

#### Revenue Trends
```
GET /api/v1/sales/revenue_trends/?days=30
```

### Inventory
Manage inventory items and stock levels.

#### List Inventory
```
GET /api/v1/inventory/
```

**Query Parameters:**
- `branch` - Filter by branch ID
- `item_name` - Filter by item name (case-insensitive)
- `category` - Filter by category (case-insensitive)
- `supplier` - Filter by supplier (case-insensitive)
- `stock_quantity_min` - Minimum stock quantity
- `stock_quantity_max` - Maximum stock quantity
- `low_stock` - Filter low stock items (true/false)
- `expired` - Filter expired items (true/false)
- `expiry_date_before` - Filter items expiring before date

#### Low Stock Alert
```
GET /api/v1/inventory/low_stock_alert/
```

#### Expiry Alert
```
GET /api/v1/inventory/expiry_alert/?days=30
```

#### Bulk Update Stock
```
POST /api/v1/inventory/bulk_update_stock/
```

**Request Body:**
```json
{
    "updates": [
        {
            "inventory_id": "INV001",
            "stock_quantity": "150"
        },
        {
            "inventory_id": "INV002", 
            "stock_quantity": "75"
        }
    ]
}
```

### Customers
Manage customer information and loyalty programs.

#### List Customers
```
GET /api/v1/customers/
```

**Query Parameters:**
- `name` - Filter by name (case-insensitive)
- `email` - Filter by email (case-insensitive)
- `phone` - Filter by phone (case-insensitive)
- `preferred_branch` - Filter by preferred branch ID
- `loyalty_points_min` - Minimum loyalty points
- `loyalty_points_max` - Maximum loyalty points
- `total_spent_min` - Minimum total spent
- `total_spent_max` - Maximum total spent
- `visit_count_min` - Minimum visit count
- `last_visit_from` - Filter customers who visited from date
- `last_visit_to` - Filter customers who visited to date

#### Loyalty Tiers
```
GET /api/v1/customers/loyalty_tiers/
```

### Staff Performance
Manage and track staff performance metrics.

#### List Staff Performance
```
GET /api/v1/staff-performance/
```

**Query Parameters:**
- `staff` - Filter by staff username (case-insensitive)
- `branch` - Filter by branch ID
- `shift_date_from` - Filter from shift date (YYYY-MM-DD)
- `shift_date_to` - Filter to shift date (YYYY-MM-DD)
- `hours_worked_min` - Minimum hours worked
- `hours_worked_max` - Maximum hours worked
- `sales_generated_min` - Minimum sales generated
- `sales_generated_max` - Maximum sales generated
- `customer_feedback_min` - Minimum customer feedback score
- `customer_feedback_max` - Maximum customer feedback score

#### Performance Rankings
```
GET /api/v1/staff-performance/performance_rankings/?days=30
```

### Audit Logs
View system audit logs and activity tracking.

#### List Audit Logs
```
GET /api/v1/audit-logs/
```

**Query Parameters:**
- `search` - Search across action, model_name, user__username, endpoint
- `ordering` - Order by: timestamp, action, model_name

#### Activity Summary
```
GET /api/v1/audit-logs/activity_summary/?days=7
```

## Error Handling

### Standard HTTP Status Codes
- `200 OK` - Successful GET, PUT, PATCH
- `201 Created` - Successful POST
- `204 No Content` - Successful DELETE
- `400 Bad Request` - Invalid request data
- `401 Unauthorized` - Authentication required
- `403 Forbidden` - Permission denied
- `404 Not Found` - Resource not found
- `500 Internal Server Error` - Server error

### Error Response Format
```json
{
    "error": "Permission denied",
    "detail": "You do not have permission to perform this action.",
    "code": "permission_denied"
}
```

### Validation Errors
```json
{
    "field_name": [
        "This field is required."
    ],
    "non_field_errors": [
        "Total amount must match sum of items."
    ]
}
```

## Rate Limiting
API requests are rate-limited per user:
- Authenticated users: 1000 requests/hour
- Unauthenticated: 100 requests/hour

## Pagination
All list endpoints support pagination:
- Default page size: 25
- Maximum page size: 100
- Use `page` and `page_size` query parameters

## Filtering and Search
Most list endpoints support:
- **Filtering**: Use specific field parameters
- **Search**: Use `search` parameter for full-text search
- **Ordering**: Use `ordering` parameter (prefix with `-` for descending)

## Data Formats
- **Dates**: ISO 8601 format (YYYY-MM-DD)
- **Timestamps**: ISO 8601 format (YYYY-MM-DDTHH:MM:SSZ)
- **Decimals**: String format with up to 2 decimal places
- **Currency**: Decimal values in system currency

## Example Usage

### Get Daily Sales for a Branch
```bash
curl -H "Authorization: Bearer <token>" \
     "http://api/v1/sales/?branch=BR001&date_from=2023-11-20&date_to=2023-11-20"
```

### Create a New Customer
```bash
curl -X POST \
     -H "Authorization: Bearer <token>" \
     -H "Content-Type: application/json" \
     -d '{"name":"John Smith","email":"john@example.com","phone":"555-0123","preferred_branch":1}' \
     "http://api/v1/customers/"
```

### Update Inventory Stock
```bash
curl -X PATCH \
     -H "Authorization: Bearer <token>" \
     -H "Content-Type: application/json" \
     -d '{"stock_quantity":50}' \
     "http://api/v1/inventory/123/"
```