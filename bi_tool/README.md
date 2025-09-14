# BI Tool Backend

A Django-based Business Intelligence tool backend with MongoDB integration and role-based access control for restaurants.

## Features

- **Role-Based Authentication System**
  - Super Admin: Access all branches and data
  - Branch Manager: Access only their branch data
  - Analyst: Read-only access to reports and dashboards
  - Staff: Limited access to task-specific endpoints

- **JWT Authentication** using `djangorestframework-simplejwt`
- **MongoDB Integration** using Djongo/PyMongo
- **RESTful APIs** with Django REST Framework
- **Comprehensive Permission System**
- **Session Management** and audit logging
- **Security Middleware** with proper CORS and security headers

## Tech Stack

- **Backend**: Django 4.2, Django REST Framework
- **Database**: MongoDB with Djongo adapter
- **Authentication**: JWT with djangorestframework-simplejwt
- **Environment Management**: python-decouple

## Project Structure

```
bi_tool/
├── bi_tool/                 # Main Django project
│   ├── __init__.py
│   ├── settings.py         # Project settings with MongoDB config
│   ├── urls.py             # Main URL configuration
│   ├── wsgi.py            # WSGI application
│   └── asgi.py            # ASGI application
├── core/                   # Core authentication app
│   ├── __init__.py
│   ├── apps.py
│   ├── models.py          # User and UserSession models
│   ├── serializers.py     # API serializers
│   ├── views.py           # API views
│   ├── permissions.py     # Custom permissions
│   ├── middleware.py      # RBAC middleware
│   ├── urls.py            # App URL patterns
│   ├── admin.py           # Django admin config
│   ├── signals.py         # Django signals
│   └── health_urls.py     # Health check endpoints
├── manage.py              # Django management script
├── requirements.txt       # Python dependencies
└── .env.example          # Environment variables template
```

## Setup Instructions

### 1. Prerequisites

- Python 3.8+
- MongoDB 4.4+
- Virtual environment (recommended)

### 2. Installation

```bash
# Clone the repository (if from git)
git clone <repository-url>
cd bi_tool

# Create and activate virtual environment
python -m venv venv
# On Windows:
venv\Scripts\activate
# On macOS/Linux:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### 3. Environment Configuration

```bash
# Copy environment template
cp .env.example .env

# Edit .env file with your settings
# Minimum required settings:
SECRET_KEY=your-super-secret-key-here
MONGO_URI=mongodb://localhost:27017
MONGO_DB_NAME=bi_tool_db
```

### 4. Database Setup

```bash
# Make migrations
python manage.py makemigrations

# Apply migrations
python manage.py migrate

# Create superuser
python manage.py createsuperuser
```

### 5. Run the Application

```bash
# Development server
python manage.py runserver

# The API will be available at:
# http://127.0.0.1:8000/api/
```

## API Endpoints

### Authentication Endpoints

| Endpoint | Method | Description | Access Level |
|----------|--------|-------------|--------------|
| `/api/auth/register/` | POST | User registration | Public |
| `/api/auth/login/` | POST | User login | Public |
| `/api/auth/token/refresh/` | POST | Refresh JWT token | Authenticated |
| `/api/auth/logout/` | POST | User logout | Authenticated |
| `/api/auth/profile/` | GET/PATCH | Get/update user profile | Authenticated |
| `/api/auth/password-change/` | POST | Change password | Authenticated |
| `/api/auth/sessions/` | GET | Get user sessions | Authenticated |
| `/api/auth/users/` | GET | List all users | Super Admin |
| `/api/auth/users/create/` | POST | Create user | Super Admin |

### Health Check Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/health/` | GET | Service health check |
| `/api/health/db/` | GET | Database health check |

## User Roles and Permissions

### Super Admin
- Access all branches and all data
- Manage users across all branches
- Full system configuration access
- Can export all data

### Branch Manager  
- Access only their assigned branch data
- Manage users within their branch
- View and export branch reports
- Limited system settings access

### Analyst
- Read-only access to all branches for reporting
- Cannot manage users
- Can view and export reports
- No system configuration access

### Staff
- Very limited access to task-specific endpoints
- Cannot manage users
- Cannot access reports
- No system configuration access

## Usage Examples

### 1. User Registration

```bash
curl -X POST http://127.0.0.1:8000/api/auth/register/ \
  -H "Content-Type: application/json" \
  -d '{
    "username": "manager1",
    "email": "manager1@restaurant.com",
    "password": "securepassword123",
    "password_confirm": "securepassword123",
    "role": "manager",
    "branch_id": "branch_001",
    "first_name": "John",
    "last_name": "Doe"
  }'
```

### 2. User Login

```bash
curl -X POST http://127.0.0.1:8000/api/auth/login/ \
  -H "Content-Type: application/json" \
  -d '{
    "username": "manager1",
    "password": "securepassword123"
  }'
```

### 3. Access Protected Endpoint

```bash
curl -X GET http://127.0.0.1:8000/api/auth/profile/ \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

## Security Features

- **JWT Authentication** with access and refresh tokens
- **Role-based Access Control** middleware
- **Branch-level Data Isolation** for managers and staff
- **Request Logging** for audit trails
- **Security Headers** middleware
- **Session Management** with IP tracking
- **Password Validation** and secure hashing

## Development

### Adding New Roles

1. Update `User.ROLE_CHOICES` in `models.py`
2. Update permissions in `middleware.py`
3. Add role-specific permissions in `permissions.py`
4. Update serializers and views as needed

### Adding New Endpoints

1. Create views in appropriate app
2. Add URL patterns to app's `urls.py`
3. Update middleware route permissions if needed
4. Add appropriate permission classes to views

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `SECRET_KEY` | Django secret key | Required |
| `DEBUG` | Debug mode | `True` |
| `ALLOWED_HOSTS` | Allowed host names | `localhost,127.0.0.1` |
| `MONGO_URI` | MongoDB connection string | `mongodb://localhost:27017` |
| `MONGO_DB_NAME` | Database name | `bi_tool_db` |
| `MONGO_USERNAME` | MongoDB username | Empty |
| `MONGO_PASSWORD` | MongoDB password | Empty |

## Production Deployment

1. Set `DEBUG=False` in environment
2. Configure proper `SECRET_KEY`
3. Set up MongoDB with authentication
4. Configure CORS settings for your frontend
5. Set up proper logging and monitoring
6. Configure SSL/TLS certificates
7. Set up reverse proxy (nginx/Apache)

## Testing

```bash
# Run tests
python manage.py test

# Run with coverage
pip install coverage
coverage run --source='.' manage.py test
coverage report
```

## Troubleshooting

### Common Issues

1. **MongoDB Connection Error**: Check MONGO_URI and ensure MongoDB is running
2. **Migration Issues**: Run `python manage.py makemigrations` and `python manage.py migrate`
3. **Permission Denied**: Check user roles and middleware configuration
4. **JWT Token Issues**: Ensure proper token format and expiration

### Logs

Check Django logs for detailed error information:
- Development: Console output
- Production: Check configured log files

## License

This project is licensed under the MIT License.

## Support

For support and questions, please contact the development team or create an issue in the repository.