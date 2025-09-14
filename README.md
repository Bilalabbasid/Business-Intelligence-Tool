# Business Intelligence Tool 📊

A comprehensive, enterprise-grade Business Intelligence platform built with Django REST Framework and React, featuring advanced ETL capabilities, real-time analytics, and interactive dashboards.

![License](https://img.shields.io/badge/license-MIT-blue.svg)
![Python](https://img.shields.io/badge/python-3.9%2B-blue.svg)
![Django](https://img.shields.io/badge/django-4.2%2B-green.svg)
![React](https://img.shields.io/badge/react-18.0%2B-blue.svg)

## 🚀 Features

### 📈 **Analytics & Visualization**
- **Interactive Dashboards** with role-based access (Super Admin, Branch Manager, Analyst, Staff)
- **Advanced Charts** using Recharts (Line, Bar, Pie, Area, Heatmap, Cohort analysis)
- **Real-time KPI Metrics** with live data updates
- **Custom Chart Builder** with drag-and-drop interface
- **Export Capabilities** (PDF, Excel, PNG, SVG)
- **Mobile-responsive** design with dark/light themes

### 🔄 **ETL & Data Pipeline**
- **Multi-source Data Ingestion**: CSV uploads, REST APIs, Database connections
- **Automated Data Validation** with configurable rules and business logic
- **Advanced Data Transformation** (cleansing, normalization, enrichment)
- **Data Warehouse Management** (PostgreSQL/ClickHouse support)
- **Scheduled ETL Jobs** with Celery and Redis
- **Real-time Data Processing** with streaming capabilities

### 🏗️ **Architecture & Infrastructure**
- **Microservices Architecture** with Docker support
- **Scalable Task Queue** with Celery and Redis
- **Database Flexibility** (MongoDB for raw data, PostgreSQL/ClickHouse for warehouse)
- **API-first Design** with comprehensive REST endpoints
- **Enterprise Security** with JWT authentication and RBAC
- **Monitoring & Observability** with Flower, Prometheus, and Sentry

### 💼 **Business Intelligence Features**
- **Sales Analytics**: Revenue tracking, trend analysis, forecasting
- **Inventory Management**: Stock levels, turnover rates, demand planning
- **Staff Performance**: Individual metrics, team analytics, productivity tracking
- **Customer Analysis**: Segmentation, behavior analysis, loyalty programs
- **Financial Reporting**: P&L statements, cost analysis, margin tracking

## 🛠️ Technology Stack

### Backend
- **Django 4.2** - Web framework
- **Django REST Framework** - API development
- **MongoDB** - Raw data storage with Djongo
- **PostgreSQL/ClickHouse** - Data warehouse
- **Celery + Redis** - Task queue and caching
- **JWT Authentication** - Security

### Frontend
- **React 18** - UI framework
- **Vite** - Build tool and dev server
- **Tailwind CSS** - Styling framework
- **Recharts** - Data visualization
- **React Query** - Data fetching and state management
- **Headless UI** - Accessible UI components

### DevOps & Monitoring
- **Docker** - Containerization
- **Flower** - Celery monitoring
- **Prometheus** - Metrics collection
- **Sentry** - Error tracking
- **GitHub Actions** - CI/CD

## 📋 Prerequisites

- **Python 3.9+**
- **Node.js 16+**
- **MongoDB 5.0+**
- **PostgreSQL 13+** (optional: ClickHouse for analytics)
- **Redis 6.0+**
- **Docker & Docker Compose** (optional but recommended)

## 🚀 Quick Start

### 1. Clone the Repository
```bash
git clone https://github.com/Bilalabbasid/Business-Intelligence-Tool.git
cd Business-Intelligence-Tool
```

### 2. Backend Setup

#### Using Docker (Recommended)
```bash
# Start all services
docker-compose up -d

# Run migrations
docker-compose exec backend python manage.py migrate

# Create superuser
docker-compose exec backend python manage.py createsuperuser

# Load sample data
docker-compose exec backend python manage.py loaddata fixtures/sample_data.json
```

#### Manual Setup
```bash
cd bi_tool

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Environment setup
cp .env.example .env
# Edit .env with your configuration

# Database setup
python manage.py migrate
python manage.py createsuperuser

# Start Redis (required for Celery)
redis-server

# Start Celery worker (new terminal)
celery -A bi_tool worker -l info

# Start Celery beat scheduler (new terminal)
celery -A bi_tool beat -l info

# Start Django development server
python manage.py runserver
```

### 3. Frontend Setup
```bash
cd bi-frontend

# Install dependencies
npm install

# Start development server
npm run dev
```

### 4. Access the Application
- **Frontend**: http://localhost:5173
- **Backend API**: http://localhost:8000/api/
- **Admin Panel**: http://localhost:8000/admin/
- **API Documentation**: http://localhost:8000/api/docs/
- **Flower (Celery Monitor)**: http://localhost:5555

## 📁 Project Structure

```
Business-Intelligence-Tool/
├── bi_tool/                    # Django Backend
│   ├── analytics/              # Analytics models and logic
│   ├── api/                    # REST API endpoints
│   ├── core/                   # Core utilities and middleware
│   ├── etl/                    # ETL system
│   │   ├── connectors/         # Data source connectors
│   │   ├── utils/              # Validation, transformation utilities
│   │   ├── ddl/                # Database schemas
│   │   ├── models.py           # ETL data models
│   │   └── tasks.py            # Celery tasks
│   ├── bi_tool/                # Django settings
│   └── requirements.txt        # Python dependencies
├── bi-frontend/                # React Frontend
│   ├── src/
│   │   ├── components/         # Reusable UI components
│   │   ├── pages/              # Page components
│   │   ├── charts/             # Chart components
│   │   ├── hooks/              # Custom React hooks
│   │   ├── services/           # API services
│   │   └── utils/              # Utility functions
│   ├── package.json            # Node dependencies
│   └── vite.config.js          # Vite configuration
├── docker-compose.yml          # Docker services
├── .gitignore                  # Git ignore rules
└── README.md                   # This file
```

## 🔧 Configuration

### Environment Variables (.env)
```env
# Django Settings
DEBUG=True
SECRET_KEY=your-secret-key-here
ALLOWED_HOSTS=localhost,127.0.0.1

# Database Configuration
# MongoDB (Raw Data)
MONGODB_HOST=localhost
MONGODB_PORT=27017
MONGODB_DB=bi_raw_data

# PostgreSQL (Data Warehouse)
WAREHOUSE_DB_ENGINE=django.db.backends.postgresql
WAREHOUSE_DB_NAME=bi_warehouse
WAREHOUSE_DB_USER=postgres
WAREHOUSE_DB_PASSWORD=password
WAREHOUSE_DB_HOST=localhost
WAREHOUSE_DB_PORT=5432

# Redis Configuration
REDIS_URL=redis://localhost:6379/0

# Celery Configuration
CELERY_BROKER_URL=redis://localhost:6379/0
CELERY_RESULT_BACKEND=redis://localhost:6379/0

# JWT Configuration
JWT_SECRET_KEY=your-jwt-secret
JWT_ACCESS_TOKEN_LIFETIME_MINUTES=60
JWT_REFRESH_TOKEN_LIFETIME_DAYS=7

# External APIs
OPENAI_API_KEY=your-openai-key  # Optional: For AI insights
SENDGRID_API_KEY=your-sendgrid-key  # Optional: For email alerts

# Monitoring
SENTRY_DSN=your-sentry-dsn  # Optional: Error tracking
```

## 🔗 API Documentation

The API follows RESTful principles and is fully documented using Swagger/OpenAPI.

### Key Endpoints

#### Authentication
- `POST /api/auth/login/` - User login
- `POST /api/auth/refresh/` - Refresh JWT token
- `POST /api/auth/logout/` - User logout

#### Analytics
- `GET /api/analytics/dashboard/` - Dashboard data
- `GET /api/analytics/sales/` - Sales analytics
- `GET /api/analytics/inventory/` - Inventory analytics
- `GET /api/analytics/staff/` - Staff performance

#### ETL Management
- `POST /api/etl/upload/` - Upload data files
- `GET /api/etl/jobs/` - List ETL jobs
- `POST /api/etl/jobs/` - Create ETL job
- `GET /api/etl/jobs/{id}/status/` - Job status

#### Data Sources
- `GET /api/data-sources/` - List data sources
- `POST /api/data-sources/` - Add data source
- `POST /api/data-sources/{id}/sync/` - Sync data

### Sample API Responses

#### Dashboard Data
```json
{
  "kpis": {
    "total_revenue": 145000.50,
    "total_transactions": 1250,
    "avg_order_value": 116.00,
    "customer_growth": 15.5
  },
  "charts": {
    "daily_sales": [...],
    "top_products": [...],
    "branch_performance": [...]
  }
}
```

## 🎯 ETL System Deep Dive

### Data Sources
The ETL system supports multiple data sources:

1. **CSV File Upload**
   - Drag-and-drop interface
   - Automatic schema detection
   - Data validation and preview

2. **REST API Integration**
   - Configurable endpoints
   - Authentication support (API Key, OAuth, Basic)
   - Rate limiting and retry logic

3. **Database Connections**
   - PostgreSQL, MySQL, MongoDB
   - Connection pooling
   - Incremental data loading

### Data Processing Pipeline

1. **Extraction**: Data is pulled from various sources
2. **Validation**: Comprehensive data quality checks
3. **Transformation**: Data cleansing and normalization
4. **Loading**: Structured storage in data warehouse
5. **Aggregation**: Pre-computed metrics and KPIs

### Validation Rules
```python
# Example validation configuration
validation_rules = {
    'pos': [
        ValidationRule('order_id', 'required', {}, "Order ID is required"),
        ValidationRule('amount', 'type', {'type': 'decimal'}, "Invalid amount"),
        ValidationRule('amount', 'range', {'min': 0, 'max': 10000}, "Amount out of range"),
    ]
}
```

### Transformation Examples
```python
# Example transformation rules
transformation_rules = {
    'pos': [
        TransformationRule('sale_time', 'event_timestamp', 'format', {
            'format_type': 'date', 'format': '%Y-%m-%dT%H:%M:%SZ'
        }),
        TransformationRule('price', 'price', 'cast', {'type': 'decimal'}),
    ]
}
```

## 📊 Data Warehouse Schema

### Fact Tables
- **fact_sales**: Transaction-level sales data
- **fact_inventory**: Inventory movements and snapshots
- **fact_staff_performance**: Staff performance metrics
- **fact_customer_behavior**: Customer interaction data

### Dimension Tables
- **dim_date**: Date dimension with fiscal calendar
- **dim_product**: Product master with SCD Type 2
- **dim_customer**: Customer dimension with segmentation
- **dim_staff**: Staff dimension with hierarchy
- **dim_branch**: Branch/location dimension

### Aggregation Tables
- **agg_daily_sales**: Pre-aggregated daily sales summaries
- **agg_monthly_sales**: Monthly sales with customer metrics
- **agg_inventory_snapshot**: Daily inventory positions
- **agg_staff_performance**: Staff productivity metrics

## 🚀 Deployment

### Production Deployment with Docker

1. **Build and Deploy**
```bash
# Build production images
docker-compose -f docker-compose.prod.yml build

# Deploy to production
docker-compose -f docker-compose.prod.yml up -d

# Run migrations
docker-compose -f docker-compose.prod.yml exec backend python manage.py migrate

# Collect static files
docker-compose -f docker-compose.prod.yml exec backend python manage.py collectstatic
```

2. **SSL Configuration**
- Use nginx-proxy or Traefik for SSL termination
- Configure Let's Encrypt for automated SSL certificates

3. **Environment Setup**
```bash
# Production environment variables
export DEBUG=False
export ALLOWED_HOSTS=yourdomain.com
export DATABASE_URL=postgres://user:pass@host:port/dbname
export REDIS_URL=redis://redis-host:6379/0
```

### Cloud Deployment Options

#### AWS
- **EC2**: Virtual machine deployment
- **ECS**: Container orchestration
- **RDS**: Managed PostgreSQL
- **ElastiCache**: Managed Redis
- **S3**: File storage

#### Google Cloud Platform
- **Compute Engine**: VM instances
- **Cloud Run**: Serverless containers
- **Cloud SQL**: Managed databases
- **Memorystore**: Managed Redis

#### Azure
- **App Service**: Web app hosting
- **Container Instances**: Container deployment
- **Database for PostgreSQL**: Managed database
- **Cache for Redis**: Managed Redis

## 📱 Mobile & Progressive Web App

The frontend is built as a Progressive Web App (PWA) with:
- **Offline Support**: Works without internet connection
- **Mobile Optimization**: Touch-friendly interface
- **Push Notifications**: Real-time alerts
- **App-like Experience**: Installable on mobile devices

## 🔒 Security Features

### Authentication & Authorization
- **JWT-based Authentication**: Secure token-based auth
- **Role-based Access Control**: Fine-grained permissions
- **Multi-factor Authentication**: Optional 2FA support
- **Session Management**: Secure session handling

### Data Security
- **Data Encryption**: At-rest and in-transit encryption
- **Input Validation**: Comprehensive input sanitization
- **SQL Injection Prevention**: Parameterized queries
- **XSS Protection**: Content Security Policy headers

### API Security
- **Rate Limiting**: Prevent API abuse
- **CORS Configuration**: Controlled cross-origin requests
- **API Versioning**: Backward compatibility
- **Request Logging**: Comprehensive audit trails

## 🧪 Testing

### Backend Tests
```bash
# Run all tests
python manage.py test

# Run with coverage
coverage run --source='.' manage.py test
coverage report
coverage html  # Generate HTML coverage report
```

### Frontend Tests
```bash
# Unit tests
npm run test

# E2E tests
npm run test:e2e

# Test coverage
npm run test:coverage
```

### Load Testing
```bash
# Using locust for API load testing
pip install locust
locust -f tests/load_tests.py --host=http://localhost:8000
```

## 📈 Performance Optimization

### Backend Optimization
- **Database Indexing**: Optimized queries with proper indexes
- **Caching**: Redis-based caching for frequently accessed data
- **Connection Pooling**: Efficient database connections
- **Async Processing**: Celery for background tasks

### Frontend Optimization
- **Code Splitting**: Lazy loading of components
- **Image Optimization**: Compressed and responsive images
- **Bundle Optimization**: Minimized JavaScript bundles
- **CDN Integration**: Static asset delivery

### Database Optimization
- **Query Optimization**: Efficient SQL queries
- **Partitioning**: Table partitioning for large datasets
- **Materialized Views**: Pre-computed aggregations
- **Index Management**: Regular index maintenance

## 🔧 Monitoring & Maintenance

### Application Monitoring
- **Health Checks**: Automated system health monitoring
- **Performance Metrics**: Response times and throughput
- **Error Tracking**: Real-time error notifications
- **Log Aggregation**: Centralized logging system

### ETL Monitoring
- **Job Status**: Real-time ETL job monitoring
- **Data Quality**: Automated data quality checks
- **Alert System**: Email/SMS notifications for failures
- **Performance Metrics**: Processing times and volumes

### Maintenance Tasks
```bash
# Database maintenance
python manage.py optimize_database

# Clear old logs
python manage.py clear_old_logs --days=30

# Rebuild search indexes
python manage.py rebuild_index

# Update aggregations
python manage.py update_aggregations
```

## 🤝 Contributing

We welcome contributions! Please see our [Contributing Guide](CONTRIBUTING.md) for details.

### Development Setup
1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests for new functionality
5. Ensure all tests pass
6. Submit a pull request

### Code Style
- **Python**: Follow PEP 8 guidelines
- **JavaScript**: Use Prettier and ESLint
- **Commits**: Use conventional commit messages

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🆘 Support & Documentation

### Getting Help
- **GitHub Issues**: Bug reports and feature requests
- **Documentation**: Comprehensive docs at `/docs`
- **Email Support**: bilal.abbasi@example.com

### Additional Resources
- **API Documentation**: Interactive Swagger docs
- **Video Tutorials**: Setup and usage guides
- **Blog Posts**: Technical deep dives and best practices

## 🎯 Roadmap

### Short Term (Q4 2025)
- [ ] Advanced AI/ML analytics integration
- [ ] Real-time streaming data support
- [ ] Enhanced mobile app features
- [ ] Advanced user permissions system

### Medium Term (Q1-Q2 2026)
- [ ] Multi-tenant architecture
- [ ] Advanced forecasting models
- [ ] Custom report builder
- [ ] Integration marketplace

### Long Term (Q3-Q4 2026)
- [ ] Natural language query interface
- [ ] Embedded analytics widgets
- [ ] Advanced data governance
- [ ] Enterprise SSO integration

## 📊 Screenshots

### Dashboard
![Dashboard](docs/screenshots/dashboard.png)

### ETL Management
![ETL Management](docs/screenshots/etl-management.png)

### Analytics
![Analytics](docs/screenshots/analytics.png)

---

**Built with ❤️ by [Bilal Abbasi](https://github.com/Bilalabbasid)**

For more information, visit our [documentation site](https://docs.bi-tool.com) or check out the [live demo](https://demo.bi-tool.com).