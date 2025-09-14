"""
Data Quality Celery Tasks
Handles scheduling and execution of data quality checks.
"""

import logging
import json
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from celery import shared_task, group, chord
from celery.exceptions import Retry
from django.utils import timezone
from django.core.cache import cache
from django.db import transaction
from django.conf import settings

from .models import DQRule, DQRun, DQViolation, DQMetric, DQRunStatus, DQSeverity
from .checks import DQCheckExecutor
from .alerts import DQAlertManager

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def execute_dq_check(self, rule_id: int, run_id: Optional[int] = None) -> Dict[str, Any]:
    """Execute a single data quality check."""
    try:
        # Get rule
        rule = DQRule.objects.select_related().get(id=rule_id, enabled=True)
        logger.info(f"Executing DQ check: {rule.name}")
        
        # Create or get run record
        if run_id:
            dq_run = DQRun.objects.get(id=run_id)
            dq_run.status = DQRunStatus.RUNNING
            dq_run.started_at = timezone.now()
            dq_run.save()
        else:
            dq_run = DQRun.objects.create(
                rule=rule,
                status=DQRunStatus.RUNNING,
                started_at=timezone.now(),
                triggered_by='scheduler'
            )
        
        # Execute check
        executor = DQCheckExecutor()
        result = executor.execute_check(rule, dq_run.id)
        
        # Update run with results
        with transaction.atomic():
            dq_run.status = DQRunStatus.SUCCESS if result['success'] else DQRunStatus.FAILED
            dq_run.finished_at = timezone.now()
            dq_run.duration_seconds = (dq_run.finished_at - dq_run.started_at).total_seconds()
            dq_run.rows_scanned = result.get('rows_scanned', 0)
            dq_run.violations_count = result.get('violations_count', 0)
            dq_run.result_details = result
            dq_run.save()
            
            # Record metrics
            record_dq_metrics.delay(rule_id, dq_run.id, result)
            
            # Handle violations and alerting
            if result.get('violations_count', 0) > 0:
                process_dq_violations.delay(rule_id, dq_run.id, result.get('violations', []))
        
        # Cache recent result for monitoring
        cache_key = f"dq_rule_last_result:{rule_id}"
        cache.set(cache_key, {
            'run_id': dq_run.id,
            'status': dq_run.status,
            'violations_count': dq_run.violations_count,
            'executed_at': dq_run.finished_at.isoformat(),
            'duration': dq_run.duration_seconds
        }, timeout=3600)
        
        logger.info(f"DQ check completed: {rule.name}, violations: {dq_run.violations_count}")
        
        return {
            'success': True,
            'rule_id': rule_id,
            'run_id': dq_run.id,
            'violations_count': dq_run.violations_count,
            'duration': dq_run.duration_seconds
        }
        
    except DQRule.DoesNotExist:
        logger.error(f"DQ rule not found or disabled: {rule_id}")
        return {'success': False, 'error': 'Rule not found or disabled'}
        
    except Exception as exc:
        logger.error(f"Error executing DQ check {rule_id}: {str(exc)}")
        
        # Update run status if exists
        try:
            if 'dq_run' in locals():
                dq_run.status = DQRunStatus.FAILED
                dq_run.finished_at = timezone.now()
                dq_run.error_message = str(exc)
                dq_run.save()
        except Exception:
            pass
        
        # Retry on transient errors
        if self.request.retries < self.max_retries:
            logger.info(f"Retrying DQ check {rule_id}, attempt {self.request.retries + 1}")
            raise self.retry(countdown=60 * (2 ** self.request.retries))
        
        return {'success': False, 'error': str(exc)}


@shared_task
def execute_dq_rule_set(rule_ids: List[int], batch_name: str = None) -> Dict[str, Any]:
    """Execute a set of DQ rules in parallel."""
    logger.info(f"Executing DQ rule set: {len(rule_ids)} rules, batch: {batch_name}")
    
    # Create parallel tasks
    job = group(execute_dq_check.s(rule_id) for rule_id in rule_ids)
    result = job.apply_async()
    
    # Wait for all tasks and collect results
    results = result.get()
    
    # Aggregate results
    summary = {
        'batch_name': batch_name,
        'total_rules': len(rule_ids),
        'successful': sum(1 for r in results if r.get('success')),
        'failed': sum(1 for r in results if not r.get('success')),
        'total_violations': sum(r.get('violations_count', 0) for r in results),
        'results': results,
        'executed_at': timezone.now().isoformat()
    }
    
    logger.info(f"DQ rule set completed - Success: {summary['successful']}, Failed: {summary['failed']}, Violations: {summary['total_violations']}")
    
    # Send batch summary if configured
    if summary['total_violations'] > 0 or summary['failed'] > 0:
        send_dq_batch_alert.delay(summary)
    
    return summary


@shared_task
def schedule_dq_checks():
    """Scheduled task to run DQ checks based on their cron schedules."""
    from crontab import CronTab
    
    logger.info("Scheduling DQ checks based on cron expressions")
    current_time = timezone.now()
    
    # Find rules that should run now (within last minute)
    eligible_rules = []
    
    for rule in DQRule.objects.filter(enabled=True):
        try:
            cron = CronTab(rule.schedule)
            
            # Check if rule should have run in the last minute
            last_minute = current_time - timedelta(minutes=1)
            if cron.test(last_minute) or cron.test(current_time):
                
                # Check if rule hasn't run recently (avoid duplicates)
                cache_key = f"dq_rule_last_run:{rule.id}"
                last_run = cache.get(cache_key)
                
                if not last_run or (current_time - datetime.fromisoformat(last_run)).total_seconds() > 3300:  # 55 minutes
                    eligible_rules.append(rule.id)
                    cache.set(cache_key, current_time.isoformat(), timeout=3600)
                    
        except Exception as e:
            logger.error(f"Error parsing cron schedule for rule {rule.id}: {str(e)}")
    
    if eligible_rules:
        logger.info(f"Executing {len(eligible_rules)} scheduled DQ checks")
        execute_dq_rule_set.delay(eligible_rules, f"scheduled_{current_time.strftime('%Y%m%d_%H%M')}")
    else:
        logger.info("No DQ checks scheduled at this time")
    
    # Cleanup old runs
    cleanup_old_dq_runs.delay()


@shared_task
def process_dq_violations(rule_id: int, run_id: int, violations_data: List[Dict]) -> None:
    """Process and store DQ violations."""
    try:
        rule = DQRule.objects.get(id=rule_id)
        dq_run = DQRun.objects.get(id=run_id)
        
        logger.info(f"Processing {len(violations_data)} violations for rule: {rule.name}")
        
        # Create violation records
        violations = []
        for violation_data in violations_data:
            violation = DQViolation(
                rule=rule,
                run=dq_run,
                violation_type=violation_data.get('type', 'unknown'),
                description=violation_data.get('description', ''),
                severity=rule.severity,
                detected_at=timezone.now(),
                sample_data=violation_data.get('sample_data', {}),
                metadata=violation_data.get('metadata', {}),
                acknowledged=False
            )
            violations.append(violation)
        
        # Bulk create violations
        DQViolation.objects.bulk_create(violations, batch_size=1000)
        
        # Trigger alerting based on severity and rule configuration
        if rule.severity in [DQSeverity.CRITICAL, DQSeverity.HIGH]:
            send_dq_alert.delay(rule_id, run_id, len(violations))
        
        logger.info(f"Created {len(violations)} violation records for rule: {rule.name}")
        
    except Exception as e:
        logger.error(f"Error processing violations for rule {rule_id}: {str(e)}")


@shared_task
def record_dq_metrics(rule_id: int, run_id: int, result_data: Dict) -> None:
    """Record DQ metrics for monitoring and trending."""
    try:
        rule = DQRule.objects.get(id=rule_id)
        dq_run = DQRun.objects.get(id=run_id)
        
        # Record various metrics
        metrics_to_record = [
            {
                'metric_name': 'dq_check_duration',
                'value': dq_run.duration_seconds,
                'tags': {'rule_name': rule.name, 'check_type': rule.check_type}
            },
            {
                'metric_name': 'dq_violations_count',
                'value': dq_run.violations_count,
                'tags': {'rule_name': rule.name, 'severity': rule.severity}
            },
            {
                'metric_name': 'dq_rows_scanned',
                'value': dq_run.rows_scanned,
                'tags': {'rule_name': rule.name, 'database': rule.target_database}
            }
        ]
        
        # Add check-specific metrics
        if 'pass_rate' in result_data:
            metrics_to_record.append({
                'metric_name': 'dq_pass_rate',
                'value': result_data['pass_rate'],
                'tags': {'rule_name': rule.name}
            })
        
        # Store metrics in database
        for metric_data in metrics_to_record:
            DQMetric.objects.create(
                rule=rule,
                run=dq_run,
                metric_name=metric_data['metric_name'],
                metric_value=metric_data['value'],
                tags=metric_data.get('tags', {}),
                recorded_at=timezone.now()
            )
        
        # Export to Prometheus/monitoring system if configured
        export_metrics_to_prometheus.delay(metrics_to_record)
        
        logger.debug(f"Recorded {len(metrics_to_record)} metrics for rule: {rule.name}")
        
    except Exception as e:
        logger.error(f"Error recording metrics for rule {rule_id}: {str(e)}")


@shared_task
def send_dq_alert(rule_id: int, run_id: int, violations_count: int) -> None:
    """Send DQ alert for rule violations."""
    try:
        rule = DQRule.objects.get(id=rule_id)
        dq_run = DQRun.objects.get(id=run_id)
        
        alert_manager = DQAlertManager()
        
        alert_data = {
            'rule_name': rule.name,
            'check_type': rule.check_type,
            'severity': rule.severity,
            'violations_count': violations_count,
            'threshold': rule.threshold,
            'target': f"{rule.target_database}.{rule.target_collection}",
            'owners': rule.owners,
            'run_id': run_id,
            'detected_at': dq_run.finished_at.isoformat(),
            'tags': rule.tags
        }
        
        alert_manager.send_alert(alert_data)
        
        logger.info(f"Alert sent for rule: {rule.name}, violations: {violations_count}")
        
    except Exception as e:
        logger.error(f"Error sending alert for rule {rule_id}: {str(e)}")


@shared_task
def send_dq_batch_alert(batch_summary: Dict) -> None:
    """Send batch alert for multiple rule failures."""
    try:
        if batch_summary.get('failed', 0) > 0 or batch_summary.get('total_violations', 0) > 10:
            alert_manager = DQAlertManager()
            alert_manager.send_batch_alert(batch_summary)
            logger.info(f"Batch alert sent for: {batch_summary.get('batch_name', 'unknown')}")
            
    except Exception as e:
        logger.error(f"Error sending batch alert: {str(e)}")


@shared_task
def export_metrics_to_prometheus(metrics_data: List[Dict]) -> None:
    """Export DQ metrics to Prometheus/monitoring system."""
    try:
        # This would integrate with your Prometheus gateway or monitoring system
        # For now, we'll log the metrics
        for metric in metrics_data:
            logger.info(f"METRIC: {metric['metric_name']}={metric['value']} {metric.get('tags', {})}")
        
        # TODO: Implement actual Prometheus push gateway integration
        # import requests
        # prometheus_gateway_url = settings.PROMETHEUS_GATEWAY_URL
        # if prometheus_gateway_url:
        #     for metric in metrics_data:
        #         # Format and push to Prometheus
        #         pass
        
    except Exception as e:
        logger.error(f"Error exporting metrics to Prometheus: {str(e)}")


@shared_task
def cleanup_old_dq_runs():
    """Clean up old DQ run records based on retention policy."""
    try:
        retention_days = getattr(settings, 'DQ_RETENTION_DAYS', 90)
        cutoff_date = timezone.now() - timedelta(days=retention_days)
        
        # Delete old runs and related violations
        old_runs = DQRun.objects.filter(finished_at__lt=cutoff_date)
        old_violations = DQViolation.objects.filter(run__finished_at__lt=cutoff_date)
        old_metrics = DQMetric.objects.filter(recorded_at__lt=cutoff_date)
        
        deleted_runs = old_runs.count()
        deleted_violations = old_violations.count()
        deleted_metrics = old_metrics.count()
        
        old_runs.delete()
        old_violations.delete()
        old_metrics.delete()
        
        logger.info(f"Cleaned up old DQ records: {deleted_runs} runs, {deleted_violations} violations, {deleted_metrics} metrics")
        
    except Exception as e:
        logger.error(f"Error cleaning up old DQ runs: {str(e)}")


@shared_task
def run_dq_health_check() -> Dict[str, Any]:
    """Run health check for DQ system."""
    health_status = {
        'timestamp': timezone.now().isoformat(),
        'status': 'healthy',
        'checks': []
    }
    
    try:
        # Check database connectivity
        rule_count = DQRule.objects.filter(enabled=True).count()
        health_status['checks'].append({
            'name': 'database_connectivity',
            'status': 'pass',
            'message': f'{rule_count} active DQ rules found'
        })
        
        # Check recent executions
        recent_runs = DQRun.objects.filter(
            finished_at__gte=timezone.now() - timedelta(hours=24)
        ).count()
        
        if recent_runs > 0:
            health_status['checks'].append({
                'name': 'recent_executions',
                'status': 'pass',
                'message': f'{recent_runs} DQ checks executed in last 24h'
            })
        else:
            health_status['checks'].append({
                'name': 'recent_executions',
                'status': 'warn',
                'message': 'No DQ checks executed in last 24h'
            })
            health_status['status'] = 'degraded'
        
        # Check for high failure rate
        failed_runs = DQRun.objects.filter(
            finished_at__gte=timezone.now() - timedelta(hours=24),
            status=DQRunStatus.FAILED
        ).count()
        
        failure_rate = (failed_runs / recent_runs * 100) if recent_runs > 0 else 0
        
        if failure_rate > 20:
            health_status['checks'].append({
                'name': 'failure_rate',
                'status': 'fail',
                'message': f'High failure rate: {failure_rate:.1f}%'
            })
            health_status['status'] = 'unhealthy'
        else:
            health_status['checks'].append({
                'name': 'failure_rate',
                'status': 'pass',
                'message': f'Failure rate: {failure_rate:.1f}%'
            })
        
        return health_status
        
    except Exception as e:
        logger.error(f"DQ health check failed: {str(e)}")
        health_status['status'] = 'unhealthy'
        health_status['checks'].append({
            'name': 'health_check',
            'status': 'fail',
            'message': f'Health check error: {str(e)}'
        })
        return health_status