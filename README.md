# Business Intelligence Tool 📊

A comprehensive, enterprise-grade Business Intelligence platform built with Django REST Framework and React, featuring advanced ETL capabilities, real-time analytics, and interactive dashboards.

Developer Quick Run (local)
---------------------------

These minimal steps start the backend and frontend for local development and quick testing.

1) Backend (in PowerShell):

```powershell
Set-Location 'C:\Users\Bilal.Abbasi\Desktop\BI\bi_tool'
.\.venv\Scripts\Activate.ps1
python manage.py migrate
python manage.py runserver 0.0.0.0:8000
```

2) Frontend (in a separate PowerShell window):

```powershell
Set-Location 'C:\Users\Bilal.Abbasi\Desktop\BI\bi-frontend'
npm install
npm run dev
```

3) Quick checks:

```powershell
Invoke-RestMethod -Uri 'http://localhost:8000/api/health/' -UseBasicParsing
$body = @{ username='admin@example.com'; password='password' } | ConvertTo-Json
Invoke-RestMethod -Method Post -Uri 'http://localhost:8000/api/auth/login/' -Body $body -ContentType 'application/json' -UseBasicParsing
Invoke-RestMethod -Uri 'http://localhost:3004/api/health/' -UseBasicParsing
```

![License](https://img.shields.io/badge/license-MIT-blue.svg)
![Python](https://img.shields.io/badge/python-3.9%2B-blue.svg)
![Django](https://img.shields.io/badge/django-4.2%2B-green.svg)
![React](https://img.shields.io/badge/react-18.0%2B-blue.svg)

## � Complete Environment Setup Guide

### 📋 Prerequisites Installation (Step-by-Step)

#### Step 1: Install Python 3.10

**Windows:**
1. **Download Python**:
   - Go to https://www.python.org/downloads/windows/
   - Download Python 3.10.x (latest stable version)
   - **CRITICAL**: Check "Add Python to PATH" during installation
   - **CRITICAL**: Check "Install pip" during installation

2. **Verify Installation**:
   ```powershell
   python --version
   # Should output: Python 3.10.x
   
   pip --version
   # Should output: pip 23.x.x
   ```

3. **If Python command not found**:
   ```powershell
   # Try these alternatives:
   python3 --version
   py --version
   py -3.10 --version
   ```

**macOS:**
```bash
# Install using Homebrew (recommended)
brew install python@3.10

# Or download from python.org
# https://www.python.org/downloads/macos/

# Verify installation
python3.10 --version
pip3.10 --version
```

**Linux (Ubuntu/Debian):**
```bash
sudo apt update
sudo apt install python3.10 python3.10-pip python3.10-venv python3.10-dev
sudo apt install build-essential libssl-dev libffi-dev

# Verify installation
python3.10 --version
pip3.10 --version
```

#### Step 2: Install Node.js 18+

**Windows:**
1. **Download Node.js**:
   - Go to https://nodejs.org/
   - Download LTS version (18.x or 20.x)
   - Run installer with default settings
   - **IMPORTANT**: Restart PowerShell after installation

2. **Verify Installation**:
   ```powershell
   node --version
   # Should output: v18.x.x or v20.x.x
   
   npm --version
   # Should output: 9.x.x or 10.x.x
   ```

3. **Fix npm permission issues (if needed)**:
   ```powershell
   # If npm install fails with permission errors
   npm config set prefix %APPDATA%\npm
   ```

**macOS:**
```bash
# Install using Homebrew
brew install node@18

# Or download from nodejs.org
# Verify installation
node --version
npm --version
```

**Linux:**
```bash
# Using NodeSource repository (recommended)
curl -fsSL https://deb.nodesource.com/setup_18.x | sudo -E bash -
sudo apt-get install -y nodejs

# Verify installation
node --version
npm --version
```

#### Step 3: Install Go 1.21+

**Windows:**
1. **Download Go**:
   - Go to https://golang.org/dl/
   - Download Windows installer (.msi file)
   - Run installer with default settings
   - **IMPORTANT**: Restart PowerShell after installation

2. **Verify Installation**:
   ```powershell
   go version
   # Should output: go version go1.21.x windows/amd64
   ```

3. **Set Go environment (if needed)**:
   ```powershell
   go env GOPATH
   go env GOROOT
   ```

**macOS:**
```bash
# Install using Homebrew
brew install go

# Or download from golang.org
# Verify installation
go version
```

**Linux:**
```bash
# Download and install manually
cd /tmp
wget https://go.dev/dl/go1.21.5.linux-amd64.tar.gz
sudo rm -rf /usr/local/go
sudo tar -C /usr/local -xzf go1.21.5.linux-amd64.tar.gz

# Add to PATH
echo 'export PATH=$PATH:/usr/local/go/bin' >> ~/.bashrc
source ~/.bashrc

# Verify installation
go version
```

#### Step 4: Install Docker Desktop

**Windows:**
1. **Check System Requirements**:
   - Windows 10/11 64-bit
   - WSL 2 feature enabled
   - Virtualization enabled in BIOS

2. **Enable WSL 2** (if not already enabled):
   ```powershell
   # Run as Administrator
   wsl --install
   # Restart computer when prompted
   ```

3. **Download and Install Docker**:
   - Go to https://www.docker.com/products/docker-desktop/
   - Download Docker Desktop for Windows
   - Run installer and follow prompts
   - **IMPORTANT**: Start Docker Desktop after installation

4. **Verify Installation**:
   ```powershell
   docker --version
   # Should output: Docker version 20.10.x or higher
   
   docker-compose --version
   # Should output: Docker Compose version v2.x.x
   ```

5. **Fix Docker Issues** (if docker command fails):
   ```powershell
   # Start Docker Desktop manually
   # Check if Docker Desktop is running in system tray
   
   # If still issues, try:
   docker context ls
   docker context use default
   ```

**macOS:**
```bash
# Download Docker Desktop from docker.com
# Or install using Homebrew Cask
brew install --cask docker

# Start Docker Desktop from Applications folder
# Verify installation
docker --version
docker-compose --version
```

**Linux:**
```bash
# Install Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh

# Add user to docker group
sudo usermod -aG docker $USER
newgrp docker

# Install Docker Compose
sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose

# Verify installation
docker --version
docker-compose --version
```

### 🚀 Project Setup (Complete Guide)

#### Step 1: Navigate to Project Directory

```bash
# Windows PowerShell
cd "C:\Users\Bilal.Abbasi\Desktop\BI"

# macOS/Linux
cd ~/path/to/BI
```

#### Step 2: Verify Project Structure

Your directory should contain:
```
BI/
├── bi_tool/              # Django Backend
├── bi-frontend/          # React Frontend
├── backup-cli/           # Go backup utility
├── logscan/             # Go log scanner
├── docker-compose.yml   # Docker configuration
├── .github/             # CI/CD workflows
└── README.md           # This file
```

### 🐳 Docker Setup (Recommended - Easiest Way)

#### Step 1: Start Docker Desktop
- **Windows**: Look for Docker Desktop in system tray, click to start
- **macOS**: Start Docker Desktop from Applications
- **Linux**: `sudo systemctl start docker`

#### Step 2: Verify Docker is Running
```bash
docker --version
docker-compose --version
docker info
```

#### Step 3: Build and Start All Services
```bash
# Navigate to project root
cd "C:\Users\Bilal.Abbasi\Desktop\BI"

# Start all services (this will take 5-15 minutes on first run)
docker-compose up -d

# Check status
docker-compose ps
```

**Expected Output:**
```
Name                    Command               State                    Ports
bi_postgres_1          docker-entrypoint.s ...   Up      0.0.0.0:5432->5432/tcp
bi_mongodb_1           docker-entrypoint.s ...   Up      0.0.0.0:27017->27017/tcp
bi_redis_1             docker-entrypoint.s ...   Up      0.0.0.0:6379->6379/tcp
bi_backend_1           python manage.py ru ...   Up      0.0.0.0:8000->8000/tcp
bi_frontend_1          npm run dev               Up      0.0.0.0:3000->3000/tcp
```

#### Step 4: Initialize Database and Create Admin User
```bash
# Run database migrations
docker-compose exec backend python manage.py migrate

# Create superuser account
docker-compose exec backend python manage.py createsuperuser
# Enter: username=admin, email=admin@company.com, password=admin123

# Load sample data (optional)
docker-compose exec backend python manage.py loaddata fixtures/sample_data.json
```

### 💻 Manual Setup (Development)

#### Step 1: Backend Setup

```bash
# Navigate to backend directory
cd bi_tool

# Create virtual environment
python -m venv venv

# Activate virtual environment
# Windows:
venv\Scripts\activate
# macOS/Linux:
source venv/bin/activate

# Install Python dependencies
pip install --upgrade pip
pip install -r requirements.txt

# Copy environment file
copy .env.example .env  # Windows
# cp .env.example .env  # macOS/Linux

# Edit .env file with your settings (see configuration section below)
```

**Required .env Configuration:**
```env
DEBUG=True
SECRET_KEY=your-secret-key-here-make-it-long-and-random
ALLOWED_HOSTS=localhost,127.0.0.1

# Database URLs
DATABASE_URL=postgresql://postgres:password@localhost:5432/bi_warehouse
MONGODB_URI=mongodb://localhost:27017/bi_raw_data
REDIS_URL=redis://localhost:6379/0

# JWT Settings
JWT_SECRET_KEY=another-long-random-secret-key
JWT_ACCESS_TOKEN_LIFETIME_MINUTES=60
JWT_REFRESH_TOKEN_LIFETIME_DAYS=7
```

#### Step 2: Database Setup (Manual)

**Install PostgreSQL:**
```bash
# Windows: Download from https://www.postgresql.org/download/windows/
# macOS: brew install postgresql
# Linux: sudo apt install postgresql postgresql-contrib

# Start PostgreSQL service
# Windows: Start via Services or pgAdmin
# macOS: brew services start postgresql
# Linux: sudo systemctl start postgresql
```

**Install MongoDB:**
```bash
# Windows: Download from https://www.mongodb.com/download-center/community
# macOS: brew install mongodb-community
# Linux: Follow official MongoDB installation guide

# Start MongoDB service
# Windows: Start via Services
# macOS: brew services start mongodb-community
# Linux: sudo systemctl start mongod
```

**Install Redis:**
```bash
# Windows: Download from https://github.com/microsoftarchive/redis/releases
# macOS: brew install redis
# Linux: sudo apt install redis-server

# Start Redis service
# Windows: Start via Services or run redis-server.exe
# macOS: brew services start redis
# Linux: sudo systemctl start redis
```

**Create Databases:**
```sql
-- Connect to PostgreSQL
psql -U postgres

-- Create database
CREATE DATABASE bi_warehouse;
CREATE USER bi_user WITH PASSWORD 'your_password';
GRANT ALL PRIVILEGES ON DATABASE bi_warehouse TO bi_user;
\q
```

#### Step 3: Run Backend Services

```bash
# In bi_tool directory with venv activated

# Run database migrations
python manage.py migrate

# Create superuser
python manage.py createsuperuser

# Start Celery worker (new terminal)
celery -A bi_tool worker -l info

# Start Celery beat (new terminal)
celery -A bi_tool beat -l info

# Start Django server
python manage.py runserver 0.0.0.0:8000
```

#### Step 4: Frontend Setup

```bash
# Open new terminal and navigate to frontend
cd bi-frontend

# Install Node.js dependencies
npm install

# If npm install fails, try:
npm install --legacy-peer-deps
# or
npm install --force

# Fix specific package issues
npm install @headlessui/react@latest
npm install @heroicons/react@latest

# Start development server
npm run dev
```

#### Step 5: Go Tools Setup

```bash
# Setup backup-cli tool
cd backup-cli
go mod tidy
go build -o backup-cli main.go

# Test backup tool
./backup-cli --help

# Setup logscan tool
cd ../logscan
go mod tidy
go build -o logscan main.go

# Test logscan tool
./logscan --help
```

### 🌐 Access Your Application

After setup, access these URLs:

- **🎯 Frontend Dashboard**: http://localhost:3000
- **🔗 Backend API**: http://localhost:8000/api/
- **⚙️ Admin Panel**: http://localhost:8000/admin/
- **📚 API Documentation**: http://localhost:8000/api/docs/
- **🌸 Celery Monitor**: http://localhost:5555 (if running Flower)

### 🧪 Quick Test Run

1. **Check Backend Health**:
   ```bash
   curl http://localhost:8000/api/health/
   # Should return: {"status": "healthy", ...}
   ```

2. **Login to Admin Panel**:
   - Go to http://localhost:8000/admin/
   - Login with your superuser credentials

3. **Access Frontend**:
   - Go to http://localhost:3000
   - Should see the BI Tool login page

### 🚨 Common Issues & Fixes

#### Docker Issues:
```bash
# If Docker won't start
# 1. Restart Docker Desktop
# 2. Check Windows features: Enable Hyper-V and WSL 2
# 3. Run as administrator:
docker-compose down
docker system prune -a
docker-compose build --no-cache
docker-compose up -d
```

#### Node.js Issues:
```bash
# If npm install fails
npm cache clean --force
rm -rf node_modules package-lock.json
npm install --legacy-peer-deps

# If specific packages fail
npm install @headlessui/react@^1.7.0 --save
npm install @heroicons/react@^2.0.0 --save
```

#### Python Issues:
```bash
# If pip install fails
python -m pip install --upgrade pip
pip install --upgrade setuptools wheel

# If virtual environment issues
python -m venv --clear venv
# Then reactivate and reinstall
```

#### Database Connection Issues:
```bash
# Check if services are running
# Windows:
netstat -an | findstr :5432  # PostgreSQL
netstat -an | findstr :27017 # MongoDB
netstat -an | findstr :6379  # Redis

# macOS/Linux:
lsof -i :5432  # PostgreSQL
lsof -i :27017 # MongoDB
lsof -i :6379  # Redis
```

### 👥 Default User Accounts

After setup, you'll have these account types:

1. **Super Admin** (created by you):
   - Username: admin
   - Email: admin@company.com
   - Access: Everything

2. **Sample Accounts** (if you loaded sample data):
   - Manager: manager@company.com / password123
   - Analyst: analyst@company.com / password123
   - Staff: staff@company.com / password123

## �🚀 Features

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