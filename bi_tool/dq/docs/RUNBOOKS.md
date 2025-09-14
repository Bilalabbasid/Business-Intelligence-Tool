# Data Quality System Runbooks

## Overview

This document provides operational procedures for managing the Data Quality (DQ) system in production environments. These runbooks are designed for SRE teams, data engineers, and on-call personnel.

## 🚨 Emergency Procedures

### Critical Alert: High Violation Rate

**Symptoms**: Multiple critical DQ rules failing simultaneously

**Immediate Actions**:
1. Check system health: `curl -f http://api/v1/dq/health/`
2. Verify data pipeline status: `python manage.py run_dq_checks --rule-name "sales_data_not_empty"`
3. Check upstream data sources for issues
4. Notify stakeholders if data quality SLA is breached

**Investigation Steps**:
```bash
# Check recent failures
python manage.py export_dq_data violations violations_last_hour.json --days=1

# Identify affected systems
grep -i "CRITICAL\|HIGH" logs/django.log | tail -20

# Check for data pipeline failures
celery -A bi_tool inspect active | grep -i failed
```

### System Down: DQ Checks Not Running

**Symptoms**: No recent DQ runs, health check failing

**Immediate Actions**:
1. Check Celery worker status: `celery -A bi_tool inspect active`
2. Verify Redis connectivity: `redis-cli ping`
3. Check database connectivity: `python manage.py check`
4. Restart services if necessary

**Recovery Steps**:
```bash
# Restart Celery worker
sudo systemctl restart celery-worker

# Restart Celery beat scheduler
sudo systemctl restart celery-beat

# Check service status
sudo systemctl status celery-worker celery-beat

# Verify recovery
python manage.py run_dq_checks --rule-name "test_rule" --async
```

---

## 🔧 Routine Operations

### Daily Health Check

**Schedule**: Every morning at 9 AM

**Procedure**:
```bash
#!/bin/bash
# daily_dq_healthcheck.sh

echo "=== Daily DQ Health Check $(date) ==="

# 1. System Health
echo "Checking system health..."
curl -s http://api/v1/dq/health/ | jq .

# 2. Recent Activity
echo "Recent DQ activity (last 24h)..."
python manage.py export_dq_data runs runs_summary.json --days=1 --format=json

# 3. Active Rules
echo "Active rules count..."
python manage.py shell -c "
from dq.models import DQRule
print(f'Total rules: {DQRule.objects.count()}')
print(f'Enabled rules: {DQRule.objects.filter(enabled=True).count()}')
"

# 4. Unacknowledged Violations
echo "Unacknowledged violations..."
python manage.py shell -c "
from dq.models import DQViolation
from datetime import datetime, timedelta
since = datetime.now() - timedelta(hours=24)
count = DQViolation.objects.filter(detected_at__gte=since, acknowledged=False).count()
print(f'Unacknowledged violations (24h): {count}')
"

# 5. Worker Status
echo "Celery worker status..."
celery -A bi_tool inspect stats | grep -E "(pool|rusage)"

echo "=== Health Check Complete ==="
```

### Weekly Rule Review

**Schedule**: Every Monday at 10 AM

**Procedure**:
```bash
#!/bin/bash
# weekly_rule_review.sh

echo "=== Weekly DQ Rule Review $(date) ==="

# 1. Rule Performance Analysis
python manage.py shell -c "
from dq.models import DQRule, DQRun
from django.db.models import Count, Avg
from datetime import datetime, timedelta

since = datetime.now() - timedelta(days=7)

# Rules with high failure rate
failing_rules = DQRule.objects.filter(
    runs__finished_at__gte=since
).annotate(
    total_runs=Count('runs'),
    failed_runs=Count('runs', filter=Q(runs__status='FAILED'))
).filter(failed_runs__gt=0).order_by('-failed_runs')

print('Rules with failures (last 7 days):')
for rule in failing_rules:
    failure_rate = (rule.failed_runs / rule.total_runs) * 100
    print(f'  {rule.name}: {rule.failed_runs}/{rule.total_runs} ({failure_rate:.1f}%)')
"

# 2. Rule Coverage Analysis  
echo "Rule coverage by database:"
python manage.py shell -c "
from dq.models import DQRule
from collections import Counter
coverage = Counter(DQRule.objects.filter(enabled=True).values_list('target_database', flat=True))
for db, count in coverage.items():
    print(f'  {db}: {count} rules')
"

# 3. Export rule performance report
python manage.py export_dq_data runs weekly_performance.json --days=7

echo "=== Rule Review Complete ==="
```

### Monthly Cleanup

**Schedule**: First Sunday of each month at 2 AM

**Procedure**:
```bash
#!/bin/bash
# monthly_dq_cleanup.sh

echo "=== Monthly DQ Cleanup $(date) ==="

# 1. Archive old violations
python manage.py shell -c "
from dq.models import DQViolation
from datetime import datetime, timedelta

cutoff = datetime.now() - timedelta(days=180)
old_violations = DQViolation.objects.filter(detected_at__lt=cutoff)
count = old_violations.count()
print(f'Archiving {count} violations older than 180 days...')
# old_violations.delete()  # Uncomment to actually delete
print('Cleanup complete')
"

# 2. Optimize database
echo "Optimizing database..."
python manage.py shell -c "
from django.db import connection
cursor = connection.cursor()
cursor.execute('VACUUM ANALYZE dq_dqrun;')
cursor.execute('VACUUM ANALYZE dq_dqviolation;')
cursor.execute('VACUUM ANALYZE dq_dqmetric;')
print('Database optimization complete')
"

# 3. Update rule statistics
echo "Updating rule statistics..."
python manage.py shell -c "
from dq.models import DQRule
for rule in DQRule.objects.all():
    # Update any cached statistics
    pass
print('Statistics update complete')
"

echo "=== Cleanup Complete ==="
```

---

## 🔍 Troubleshooting Guides

### Issue: Rules Not Executing on Schedule

**Symptoms**: 
- Rules have valid cron schedules but aren't running automatically
- Manual execution works fine

**Diagnosis**:
```bash
# Check Celery beat scheduler
sudo systemctl status celery-beat

# Check beat scheduler logs
sudo journalctl -u celery-beat -f

# Verify scheduled tasks
python manage.py shell -c "
from django_celery_beat.models import PeriodicTask
tasks = PeriodicTask.objects.filter(enabled=True)
print(f'Active periodic tasks: {tasks.count()}')
for task in tasks:
    print(f'  {task.name}: {task.crontab}')
"
```

**Resolution**:
1. Restart Celery beat: `sudo systemctl restart celery-beat`
2. Check Redis connectivity: `redis-cli ping`
3. Verify timezone settings match between beat scheduler and rules
4. Check for conflicting periodic tasks

### Issue: High Memory Usage in Workers

**Symptoms**:
- Worker processes consuming excessive memory
- Out of memory errors in logs
- Slow check execution

**Diagnosis**:
```bash
# Check worker memory usage
ps aux | grep celery | grep -v grep

# Monitor worker statistics
celery -A bi_tool inspect stats

# Check for large datasets being processed
python manage.py shell -c "
from dq.models import DQRule
large_rules = DQRule.objects.filter(sample_size__gt=50000, use_sampling=False)
print(f'Rules without sampling: {large_rules.count()}')
for rule in large_rules:
    print(f'  {rule.name}: {rule.sample_size} samples')
"
```

**Resolution**:
1. Enable sampling for large datasets:
   ```python
   # Update rule configuration
   rule.use_sampling = True
   rule.sample_size = 10000
   rule.save()
   ```
2. Reduce worker concurrency: `celery -A bi_tool worker --concurrency=2`
3. Add memory limits to worker processes
4. Implement result cleanup in tasks

### Issue: Database Connection Timeouts

**Symptoms**:
- Frequent connection timeout errors
- Rules failing with database connectivity issues
- Long-running queries

**Diagnosis**:
```bash
# Check database connections
python manage.py shell -c "
from django.db import connections
for db in connections:
    conn = connections[db]
    print(f'{db}: {conn.settings_dict}')
"

# Monitor active connections
# For PostgreSQL:
psql -c "SELECT count(*) FROM pg_stat_activity WHERE state = 'active';"

# For MongoDB:
mongo --eval "db.serverStatus().connections"
```

**Resolution**:
1. Increase connection pool size in Django settings
2. Add connection timeout configuration
3. Implement query optimization:
   ```python
   # Add indexes for frequently queried columns
   # Optimize rule queries with hints
   parameters:
     use_index: true
     query_hint: "INDEX(table_name, column_name)"
   ```
4. Consider read replicas for DQ checks

### Issue: Alert Fatigue

**Symptoms**:
- Too many low-priority alerts
- Important alerts getting missed
- Team ignoring DQ notifications

**Diagnosis**:
```bash
# Analyze alert volume
python manage.py shell -c "
from dq.models import DQViolation
from collections import Counter
from datetime import datetime, timedelta

since = datetime.now() - timedelta(days=7)
violations = DQViolation.objects.filter(detected_at__gte=since)

by_severity = Counter(violations.values_list('severity', flat=True))
by_rule = Counter(violations.values_list('rule__name', flat=True))

print('Violations by severity (last 7 days):')
for severity, count in by_severity.most_common():
    print(f'  {severity}: {count}')

print('\nTop violating rules:')
for rule, count in by_rule.most_common(10):
    print(f'  {rule}: {count}')
"
```

**Resolution**:
1. Adjust rule thresholds to reduce noise:
   ```yaml
   # Example: Increase null rate threshold
   threshold: 0.05  # Allow 5% nulls instead of 1%
   ```
2. Implement alert suppression:
   ```python
   # Add cooldown period for repeated violations
   parameters:
     alert_cooldown_minutes: 60
   ```
3. Use escalation policies:
   - INFO/LOW → Slack only
   - MEDIUM → Email + Slack
   - HIGH/CRITICAL → Email + Slack + PagerDuty
4. Batch similar violations in single alert

---

## 📊 Monitoring and Metrics

### Key Performance Indicators

**System Health Metrics**:
- DQ Check Success Rate: Target >95%
- Average Check Duration: Target <30 seconds
- Alert Response Time: Target <15 minutes
- System Availability: Target 99.9%

**Data Quality Metrics**:
- Critical Rule Pass Rate: Target 100%
- High Priority Rule Pass Rate: Target >98%
- Data Freshness SLA: Target <2 hours
- Schema Stability: Target <5 changes per month

### Monitoring Setup

**Grafana Dashboard Panels**:
1. DQ Check Success Rate (time series)
2. Violations by Severity (pie chart)
3. Top Failing Rules (table)
4. Check Execution Duration (histogram)
5. Alert Response Times (time series)
6. Worker Queue Length (gauge)

**Alerts Configuration**:
```yaml
# Grafana alerts
alerts:
  - name: "DQ Check Failure Rate High"
    condition: "failure_rate > 10"
    for: "5m"
    labels:
      severity: "warning"
    annotations:
      summary: "DQ check failure rate is high"
      
  - name: "Critical DQ Rule Failed"
    condition: "critical_violations > 0"
    for: "1m"
    labels:
      severity: "critical"
    annotations:
      summary: "Critical DQ rule violation detected"
```

### Log Analysis

**Common Log Patterns**:
```bash
# Find failed checks
grep "Error executing DQ check" logs/django.log

# Monitor alert sending
grep "Alert sent for rule" logs/django.log

# Check for timeout issues  
grep "timeout" logs/celery.log

# Monitor memory usage
grep "MemoryError\|OutOfMemory" logs/celery.log
```

---

## 🛠️ Maintenance Procedures

### Rule Lifecycle Management

**Adding New Rules**:
1. Create rule manifest file
2. Validate configuration: `python manage.py load_dq_rules --dry-run manifest.yaml`
3. Deploy to staging environment
4. Test rule execution: `python manage.py run_dq_checks --rule-name "new_rule"`
5. Monitor for 24 hours
6. Deploy to production
7. Update documentation

**Updating Existing Rules**:
1. Export current rule: `python manage.py export_dq_data rules current_rule.json --rule-name "rule_name"`
2. Create backup of rule configuration
3. Update rule via API or admin interface
4. Test updated rule
5. Monitor for regression
6. Rollback if issues detected

**Retiring Rules**:
1. Disable rule: `rule.enabled = False`
2. Monitor for 48 hours to ensure no dependencies
3. Archive historical data
4. Delete rule and related data
5. Update documentation

### Performance Tuning

**Query Optimization**:
```python
# Example optimization for large tables
rule_config = {
    "parameters": {
        "use_index": True,
        "query_hint": "/*+ USE_INDEX(table_name, idx_created_at) */",
        "partition_column": "created_date",
        "parallel_degree": 4
    }
}
```

**Worker Tuning**:
```bash
# CPU-optimized workers for compute-heavy checks
celery -A bi_tool worker -Q dq_compute --concurrency=8 --pool=threads

# Memory-optimized workers for large data scans  
celery -A bi_tool worker -Q dq_memory --concurrency=2 --pool=prefork

# I/O-optimized workers for database checks
celery -A bi_tool worker -Q dq_database --concurrency=4 --pool=gevent
```

### Disaster Recovery

**Backup Procedures**:
```bash
#!/bin/bash
# backup_dq_config.sh

# Backup rule configurations
python manage.py export_dq_data manifest dq_rules_backup.yaml

# Backup database
pg_dump bi_tool_db > dq_backup_$(date +%Y%m%d).sql

# Upload to secure storage
aws s3 cp dq_rules_backup.yaml s3://backup-bucket/dq/$(date +%Y%m%d)/
aws s3 cp dq_backup_$(date +%Y%m%d).sql s3://backup-bucket/dq/$(date +%Y%m%d)/
```

**Recovery Procedures**:
```bash
#!/bin/bash
# restore_dq_config.sh

# Restore database
psql bi_tool_db < dq_backup_20240101.sql

# Restore rule configurations
python manage.py load_dq_rules dq_rules_backup.yaml

# Verify restoration
python manage.py run_dq_checks --all --dry-run
```

---

## 📞 Escalation Procedures

### Severity Levels

**CRITICAL (P1)**:
- System completely down
- Data pipeline failures affecting production
- Security incidents
- **Response Time**: 15 minutes
- **Escalation**: Immediate PagerDuty alert + phone call

**HIGH (P2)**:
- Multiple rule failures
- Performance degradation >50%
- SLA breach imminent
- **Response Time**: 30 minutes  
- **Escalation**: PagerDuty alert + email

**MEDIUM (P3)**:
- Individual rule failures
- Performance issues
- Configuration problems
- **Response Time**: 2 hours
- **Escalation**: Email + Slack

**LOW (P4)**:
- Documentation updates
- Enhancement requests
- Non-urgent maintenance
- **Response Time**: 24 hours
- **Escalation**: Ticket assignment

### Contact Information

**Primary On-Call**: Data Engineering Team
- Slack: #data-eng-oncall
- PagerDuty: data-eng-primary
- Email: data-eng-oncall@company.com

**Secondary On-Call**: SRE Team  
- Slack: #sre-oncall
- PagerDuty: sre-primary
- Email: sre-oncall@company.com

**Management Escalation**:
- Data Engineering Manager: manager@company.com
- VP Engineering: vp-eng@company.com

---

## 📋 Checklists

### New Environment Setup

- [ ] Deploy DQ application code
- [ ] Configure database connections
- [ ] Set up Redis/message broker
- [ ] Configure Celery workers
- [ ] Load initial DQ rules
- [ ] Configure alerting channels
- [ ] Set up monitoring dashboards
- [ ] Test end-to-end functionality
- [ ] Document environment-specific configs
- [ ] Train operations team

### Incident Response Checklist

- [ ] Acknowledge alert within SLA
- [ ] Assess severity and impact
- [ ] Notify stakeholders if needed
- [ ] Investigate root cause
- [ ] Implement temporary fix if possible
- [ ] Monitor for resolution
- [ ] Implement permanent fix
- [ ] Document lessons learned
- [ ] Update runbooks if needed
- [ ] Conduct post-incident review

### Monthly Review Checklist

- [ ] Review system performance metrics
- [ ] Analyze rule effectiveness
- [ ] Check for unused/redundant rules
- [ ] Update rule thresholds based on trends
- [ ] Review alert fatigue metrics
- [ ] Update contact information
- [ ] Test disaster recovery procedures
- [ ] Update documentation
- [ ] Plan capacity improvements
- [ ] Schedule rule retirement

---

*This runbook is maintained by the Data Engineering SRE team. Last updated: 2024-01-01*
*For emergency assistance, contact the on-call engineer via PagerDuty or Slack #data-eng-oncall*