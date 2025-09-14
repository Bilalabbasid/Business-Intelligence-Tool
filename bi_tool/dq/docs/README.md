# Data Quality System Documentation

## Overview

The Data Quality (DQ) system provides comprehensive monitoring, validation, and alerting for data integrity across the BI platform. It supports automated rule execution, anomaly detection, and multi-channel alerting to ensure high-quality data for business intelligence consumers.

## Architecture

### Core Components

1. **DQ Rules Engine** - Defines and manages data quality rules
2. **Check Executors** - Executes different types of data quality checks
3. **Anomaly Detection** - ML-based detection of data quality anomalies
4. **Alerting System** - Multi-channel notifications for violations
5. **API Layer** - REST endpoints for rule management and monitoring
6. **Admin Interface** - Django admin for system management

### Data Flow

```
Data Sources → DQ Rules → Check Execution → Violation Detection → Alerting → Acknowledgment
                ↓
         Metrics Collection → Anomaly Detection → Trend Analysis
```

## Features

### 🔍 Data Quality Checks

- **Row Count**: Validate data volume and detect missing data
- **Null Rate**: Monitor completeness of critical fields
- **Uniqueness**: Ensure primary key integrity and prevent duplicates
- **Range Check**: Validate business logic constraints
- **Cardinality**: Monitor dimensional changes and data drift
- **Referential Integrity**: Validate foreign key relationships
- **Timeliness**: Monitor data freshness and SLA compliance
- **Schema Drift**: Detect unexpected schema changes
- **Volume Anomaly**: ML-based detection of unusual data volumes

### 📊 Anomaly Detection

- **Statistical Methods**: Z-score, IQR-based outlier detection
- **Machine Learning**: Isolation Forest for multivariate anomalies
- **Seasonal Patterns**: Time-series analysis for cyclical data
- **Change Point Detection**: Identify structural breaks in data patterns

### 🔔 Multi-Channel Alerting

- **Email Notifications**: Rich HTML alerts with violation details
- **Slack Integration**: Real-time notifications to team channels  
- **PagerDuty Integration**: Critical alert escalation for production issues
- **Severity-Based Routing**: Intelligent alert routing based on impact

### 📈 Observability

- **Prometheus Metrics**: Performance and reliability monitoring
- **Grafana Dashboards**: Visual monitoring of DQ health
- **Trend Analysis**: Historical violation patterns and improvement tracking
- **Health Checks**: System status monitoring and automated diagnostics

## Quick Start

### 1. Setup Environment

```bash
# Install dependencies
pip install -r requirements.txt

# Configure environment variables
export DQ_EMAIL_ENABLED=true
export DQ_SLACK_WEBHOOK=https://hooks.slack.com/services/...
export REDIS_URL=redis://localhost:6379/0

# Run migrations
python manage.py migrate

# Load sample DQ rules
python manage.py load_dq_rules dq/manifests/sales_dq_rules.yaml
python manage.py load_dq_rules dq/manifests/inventory_dq_rules.yaml
```

### 2. Start Services

```bash
# Start Celery worker (in separate terminal)
celery -A bi_tool worker -l info -Q dq,etl,default

# Start Celery beat scheduler (in separate terminal)  
celery -A bi_tool beat -l info

# Start Django development server
python manage.py runserver
```

### 3. Execute First DQ Check

```bash
# Run all enabled rules
python manage.py run_dq_checks --all

# Run specific rule
python manage.py run_dq_checks --rule-name "sales_amount_not_null"

# Run by check type
python manage.py run_dq_checks --check-type "null_rate"
```

## Configuration

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `DQ_EMAIL_ENABLED` | Enable email alerting | `true` |
| `DQ_SLACK_WEBHOOK` | Slack webhook URL for notifications | `""` |
| `DQ_PAGERDUTY_KEY` | PagerDuty integration key | `""` |
| `DQ_RETENTION_DAYS` | Days to retain DQ run history | `90` |
| `DQ_ADMIN_EMAILS` | Comma-separated admin email addresses | `""` |
| `PROMETHEUS_GATEWAY_URL` | Prometheus push gateway URL | `""` |

### Rule Configuration

DQ rules are defined in YAML manifests with the following structure:

```yaml
version: '1.0'
metadata:
  description: 'Data Quality Rules for Sales Data'
  owner: 'Data Engineering Team'
  
rules:
  - name: sales_amount_not_null
    description: 'Sales amount should not be null'
    check_type: null_rate
    target_database: mongodb
    target_collection: sales_data
    target_column: total_amount
    threshold: 0.01  # Max 1% null rate
    severity: CRITICAL
    schedule: '0 */2 * * *'  # Every 2 hours
    enabled: true
    owners:
      - data-eng-team@company.com
    tags:
      - sales
      - critical
```

## API Reference

### Rules Management

#### List Rules
```http
GET /api/v1/dq/api/v1/rules/
```

#### Create Rule
```http
POST /api/v1/dq/api/v1/rules/
Content-Type: application/json

{
  "name": "customer_id_not_null",
  "check_type": "null_rate",
  "target_database": "mongodb",
  "target_collection": "customers",
  "target_column": "customer_id",
  "threshold": 0.0,
  "severity": "CRITICAL",
  "schedule": "0 */4 * * *",
  "owners": ["data-team@company.com"]
}
```

#### Execute Rule
```http
POST /api/v1/dq/api/v1/rules/{id}/execute/
```

### Monitoring

#### Get Rule Runs
```http
GET /api/v1/dq/api/v1/rules/{id}/runs/?days=7&limit=50
```

#### Get Violations
```http
GET /api/v1/dq/api/v1/violations/?acknowledged=false&days=1
```

#### Acknowledge Violations
```http
POST /api/v1/dq/api/v1/violations/{id}/acknowledge/
Content-Type: application/json

{
  "note": "Issue investigated and resolved"
}
```

## Rule Types Guide

### 1. Row Count Check
Validates that tables/collections have expected number of records.

```yaml
- name: daily_sales_volume
  check_type: row_count
  target_collection: sales_data
  threshold: 100
  parameters:
    comparison: gte  # >=
    time_window: 24h
```

### 2. Null Rate Check
Monitors completeness of critical fields.

```yaml
- name: customer_id_completeness
  check_type: null_rate
  target_collection: sales_data
  target_column: customer_id
  threshold: 0.02  # Max 2% null rate
```

### 3. Uniqueness Check
Ensures primary key integrity.

```yaml
- name: transaction_id_unique
  check_type: uniqueness
  target_collection: sales_data
  target_column: transaction_id
  threshold: 0  # No duplicates allowed
```

### 4. Range Check
Validates business logic constraints.

```yaml
- name: sales_amount_positive
  check_type: range_check
  target_collection: sales_data
  target_column: total_amount
  threshold: 0.01  # Max 1% violations
  parameters:
    min_value: 0.01
    max_value: 1000000
```

### 5. Cardinality Check
Monitors dimensional stability.

```yaml
- name: product_categories_stable
  check_type: cardinality
  target_collection: sales_data
  target_column: product_category
  threshold: 50  # Max 50 distinct values
  parameters:
    comparison: lte
```

### 6. Referential Integrity Check
Validates foreign key relationships.

```yaml
- name: customer_reference_valid
  check_type: ref_integrity
  target_collection: sales_data
  target_column: customer_id
  threshold: 0.02  # Max 2% invalid references
  parameters:
    ref_database: postgres
    ref_table: customers
    ref_column: customer_id
```

### 7. Timeliness Check
Monitors data freshness.

```yaml
- name: sales_data_fresh
  check_type: timeliness
  target_collection: sales_data
  target_column: created_at
  threshold: 3600  # 1 hour in seconds
  parameters:
    time_format: iso8601
```

### 8. Schema Drift Check
Detects schema changes.

```yaml
- name: sales_schema_stable
  check_type: schema_drift
  target_collection: sales_data
  threshold: 3  # Max 3 schema changes
  parameters:
    compare_window: 7d
    ignore_new_fields: false
```

### 9. Volume Anomaly Check
ML-based volume anomaly detection.

```yaml
- name: daily_sales_anomaly
  check_type: volume_anomaly
  target_collection: sales_data
  threshold: 0.3  # 30% deviation
  parameters:
    time_window: 24h
    anomaly_method: statistical
```

## Alerting Configuration

### Email Alerts

Configure SMTP settings in Django settings:

```python
DQ_EMAIL_CONFIG = {
    'enabled': True,
    'smtp_host': 'smtp.company.com',
    'smtp_port': 587,
    'use_tls': True,
    'username': 'dq-alerts@company.com',
    'password': 'secure_password',
    'from_address': 'dq-alerts@company.com',
    'admin_emails': ['data-eng@company.com'],
}
```

### Slack Integration

1. Create a Slack app and webhook
2. Set environment variable: `DQ_SLACK_WEBHOOK=https://hooks.slack.com/...`
3. Configure channel routing in rule owners

### PagerDuty Integration

1. Create PagerDuty integration
2. Set environment variable: `DQ_PAGERDUTY_KEY=your_integration_key`
3. Critical and high severity alerts automatically escalate

## Monitoring and Observability

### Grafana Dashboard

The system exports metrics to Prometheus for visualization:

- **DQ Check Success Rate**: Percentage of successful checks
- **Violation Trends**: Time-series of data quality violations
- **Check Execution Duration**: Performance monitoring
- **Rule Coverage**: Active vs inactive rules
- **Alert Response Time**: Time to acknowledgment

### Health Checks

Monitor system health at `/api/v1/dq/health/`:

```json
{
  "status": "healthy",
  "timestamp": "2024-01-01T12:00:00Z",
  "checks": {
    "database": "pass",
    "rules_count": 45,
    "recent_runs": 123,
    "failure_rate": 2.3
  }
}
```

## Troubleshooting

### Common Issues

#### 1. Rules Not Executing
- Check Celery worker is running: `celery -A bi_tool inspect active`
- Verify rule is enabled: `python manage.py shell -c "from dq.models import DQRule; print(DQRule.objects.filter(enabled=True).count())"`
- Check schedule syntax: Must be valid cron expression

#### 2. Database Connection Errors
- Verify connection settings in `DATA_WAREHOUSE_CONFIG`
- Test connectivity: `python manage.py check`
- Check firewall and network access

#### 3. Alerts Not Sending
- Verify SMTP/Slack/PagerDuty configuration
- Check rule owners are valid email addresses
- Review alert logs: `tail -f logs/django.log | grep -i alert`

#### 4. High Memory Usage
- Reduce `sample_size` in rules
- Enable sampling: `use_sampling: true`
- Tune Celery worker concurrency

### Performance Optimization

#### 1. Database Optimization
```yaml
# Use sampling for large datasets
sample_size: 10000
use_sampling: true

# Optimize queries with indexes
parameters:
  use_index: true
  hint: "INDEX(sales_data, created_at)"
```

#### 2. Execution Optimization
```yaml
# Reduce timeout for faster feedback
timeout_seconds: 60

# Stagger heavy checks
schedule: '15 */6 * * *'  # Offset from hour boundaries
```

#### 3. Resource Management
```bash
# Tune Celery worker concurrency
celery -A bi_tool worker -l info --concurrency=4 -Q dq

# Use separate queue for heavy checks
celery -A bi_tool worker -l info -Q dq_heavy --concurrency=2
```

## Development

### Adding New Check Types

1. **Define Check Logic**: Extend `DQCheckExecutor` in `checks.py`
2. **Update Models**: Add new choice to `DQCheckType`
3. **Add Validator**: Register validator in `rules.py`
4. **Write Tests**: Add unit tests in `tests/`
5. **Update Documentation**: Add examples and configuration

### Testing

```bash
# Run all DQ tests
python manage.py test dq

# Run specific test
python manage.py test dq.tests.test_checks

# Test with coverage
coverage run --source='.' manage.py test dq
coverage report
```

### Contributing

1. Fork the repository
2. Create feature branch: `git checkout -b feature/new-check-type`
3. Write tests and implementation
4. Update documentation
5. Submit pull request

## Production Deployment

### Infrastructure Requirements

- **Redis**: For Celery message broker
- **PostgreSQL**: For metadata and configuration
- **MongoDB**: For raw data storage (optional)
- **SMTP Server**: For email alerts
- **Monitoring**: Prometheus + Grafana

### Deployment Checklist

- [ ] Configure production database connections
- [ ] Set up Redis cluster for high availability
- [ ] Configure email/Slack/PagerDuty integrations
- [ ] Deploy Celery workers with proper scaling
- [ ] Set up monitoring and alerting
- [ ] Configure log aggregation
- [ ] Run security audit
- [ ] Perform load testing
- [ ] Document runbooks

### Scaling Considerations

- **Horizontal Scaling**: Multiple Celery workers across nodes
- **Queue Segmentation**: Separate queues by priority/type
- **Database Optimization**: Read replicas for reporting
- **Caching**: Redis for frequent rule lookups
- **Archive Strategy**: Move old data to cold storage

## Support

- **Documentation**: [Internal Wiki](https://wiki.company.com/dq)
- **Issues**: Create ticket in Jira/GitHub
- **Slack**: #data-quality-support
- **Email**: data-eng-team@company.com

---

*This documentation is maintained by the Data Engineering team. Last updated: 2024-01-01*