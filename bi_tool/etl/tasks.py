"""
Celery Tasks for ETL Processing
"""

import json
import logging
import pandas as pd
import traceback
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple
from uuid import uuid4

from celery import shared_task, group, chain
from django.conf import settings
from django.db import transaction, connections
from django.utils import timezone
from django.core.mail import send_mail

from .models import (
    RawEvent, RawError, ETLJob, ETLRun, Checkpoint, 
    DataSource, AuditLog, ETLAlert
)
from .connectors.base import ConnectorRegistry
from .utils.validators import DataValidator
from .utils.transformers import DataTransformer
from .utils.warehouse import WarehouseManager
from .utils.alerts import AlertManager
from .utils.monitoring import MetricsCollector

logger = logging.getLogger(__name__)
metrics = MetricsCollector()
alert_manager = AlertManager()


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def ingest_data_batch(self, source_name: str, batch_data: List[Dict], 
                     batch_id: str = None, branch_id: int = None) -> Dict[str, Any]:
    """
    Ingest a batch of raw data into MongoDB.
    
    Args:
        source_name: Name of data source
        batch_data: List of raw data records
        batch_id: Optional batch identifier
        branch_id: Optional branch identifier
        
    Returns:
        Dict with ingestion results
    """
    run_id = str(uuid4())
    batch_id = batch_id or f"{source_name}_{int(datetime.now().timestamp())}"
    
    logger.info(f"Starting data ingestion: {source_name}, batch: {batch_id}, records: {len(batch_data)}")
    
    try:
        results = {
            'run_id': run_id,
            'batch_id': batch_id,
            'source': source_name,
            'total_records': len(batch_data),
            'ingested': 0,
            'duplicates': 0,
            'errors': 0,
            'started_at': timezone.now().isoformat(),
        }
        
        with metrics.timer('ingestion_duration'):
            for i, record in enumerate(batch_data):
                try:
                    # Generate unique ingest_id for deduplication
                    ingest_id = _generate_ingest_id(source_name, record, batch_id, i)
                    
                    # Check for duplicates
                    if RawEvent.objects.filter(ingest_id=ingest_id).exists():
                        results['duplicates'] += 1
                        logger.debug(f"Duplicate record skipped: {ingest_id}")
                        continue
                    
                    # Create raw event
                    raw_event = RawEvent(
                        ingest_id=ingest_id,
                        source=source_name,
                        batch_id=batch_id,
                        branch_id=branch_id,
                        raw_payload=record,
                        validation_status='pending'
                    )
                    raw_event.save()
                    results['ingested'] += 1
                    
                except Exception as e:
                    logger.error(f"Error ingesting record {i}: {e}")
                    results['errors'] += 1
                    
                    # Save to error collection
                    RawError(
                        ingest_id=ingest_id if 'ingest_id' in locals() else f"error_{batch_id}_{i}",
                        source=source_name,
                        batch_id=batch_id,
                        raw_payload=record,
                        error_type='ingestion',
                        error_message=str(e),
                        error_details={'traceback': traceback.format_exc()}
                    ).save()
        
        results['completed_at'] = timezone.now().isoformat()
        
        # Update metrics
        metrics.increment('records_ingested', results['ingested'])
        metrics.increment('records_duplicated', results['duplicates'])
        metrics.increment('ingestion_errors', results['errors'])
        
        # Log audit event
        AuditLog.objects.create(
            event_type='data_ingested',
            message=f"Ingested batch {batch_id} from {source_name}",
            details=results
        )
        
        # Schedule validation if records were ingested
        if results['ingested'] > 0:
            validate_data_batch.delay(batch_id)
        
        # Check error rate and alert if necessary
        error_rate = results['errors'] / results['total_records'] * 100 if results['total_records'] > 0 else 0
        if error_rate > 10:  # Alert if > 10% error rate
            alert_manager.create_alert(
                'high_error_rate',
                'high',
                f"High error rate in batch {batch_id}",
                f"Error rate: {error_rate:.2f}% ({results['errors']}/{results['total_records']})"
            )
        
        logger.info(f"Ingestion completed: {results}")
        return results
        
    except Exception as e:
        logger.error(f"Fatal error in ingestion task: {e}")
        
        # Create critical alert
        alert_manager.create_alert(
            'job_failure',
            'critical',
            f"Ingestion task failed for {source_name}",
            str(e)
        )
        
        # Retry with exponential backoff
        raise self.retry(exc=e, countdown=60 * (2 ** self.request.retries))


@shared_task(bind=True, max_retries=3)
def validate_data_batch(self, batch_id: str) -> Dict[str, Any]:
    """
    Validate a batch of raw events.
    
    Args:
        batch_id: Batch identifier to validate
        
    Returns:
        Dict with validation results
    """
    logger.info(f"Starting validation for batch: {batch_id}")
    
    try:
        # Get unvalidated events from this batch
        raw_events = RawEvent.objects.filter(
            batch_id=batch_id,
            validation_status='pending'
        )
        
        if not raw_events.exists():
            logger.info(f"No pending events found for batch: {batch_id}")
            return {'batch_id': batch_id, 'total': 0, 'validated': 0, 'invalid': 0}
        
        validator = DataValidator()
        results = {
            'batch_id': batch_id,
            'total': raw_events.count(),
            'validated': 0,
            'invalid': 0,
            'started_at': timezone.now().isoformat(),
        }
        
        for event in raw_events:
            try:
                # Validate the raw payload
                validation_result = validator.validate(event.source, event.raw_payload)
                
                if validation_result['is_valid']:
                    event.validation_status = 'valid'
                    event.validation_errors = {}
                    results['validated'] += 1
                else:
                    event.validation_status = 'invalid'
                    event.validation_errors = validation_result['errors']
                    results['invalid'] += 1
                    
                    # Move invalid records to error collection
                    RawError(
                        ingest_id=event.ingest_id,
                        source=event.source,
                        batch_id=event.batch_id,
                        raw_payload=event.raw_payload,
                        error_type='validation',
                        error_message='Data validation failed',
                        error_details=validation_result['errors']
                    ).save()
                
                event.save()
                
            except Exception as e:
                logger.error(f"Error validating event {event.ingest_id}: {e}")
                event.validation_status = 'invalid'
                event.validation_errors = {'system_error': str(e)}
                event.save()
                results['invalid'] += 1
        
        results['completed_at'] = timezone.now().isoformat()
        
        # Update metrics
        metrics.increment('records_validated', results['validated'])
        metrics.increment('validation_errors', results['invalid'])
        
        # Schedule enrichment for valid records
        if results['validated'] > 0:
            enrich_data_batch.delay(batch_id)
        
        logger.info(f"Validation completed: {results}")
        return results
        
    except Exception as e:
        logger.error(f"Error in validation task: {e}")
        raise self.retry(exc=e, countdown=60 * (2 ** self.request.retries))


@shared_task(bind=True, max_retries=3)
def enrich_data_batch(self, batch_id: str) -> Dict[str, Any]:
    """
    Enrich valid data with additional information.
    
    Args:
        batch_id: Batch identifier to enrich
        
    Returns:
        Dict with enrichment results
    """
    logger.info(f"Starting enrichment for batch: {batch_id}")
    
    try:
        # Get valid events from this batch
        raw_events = RawEvent.objects.filter(
            batch_id=batch_id,
            validation_status='valid'
        )
        
        if not raw_events.exists():
            logger.info(f"No valid events found for batch: {batch_id}")
            return {'batch_id': batch_id, 'total': 0, 'enriched': 0, 'failed': 0}
        
        transformer = DataTransformer()
        results = {
            'batch_id': batch_id,
            'total': raw_events.count(),
            'enriched': 0,
            'failed': 0,
            'started_at': timezone.now().isoformat(),
        }
        
        for event in raw_events:
            try:
                # Enrich the validated data
                enrichment_result = transformer.enrich(event.source, event.raw_payload)
                
                if enrichment_result['success']:
                    event.enriched_data = enrichment_result['data']
                    event.validation_status = 'enriched'
                    results['enriched'] += 1
                else:
                    logger.warning(f"Enrichment failed for {event.ingest_id}: {enrichment_result.get('error')}")
                    results['failed'] += 1
                
                event.save()
                
            except Exception as e:
                logger.error(f"Error enriching event {event.ingest_id}: {e}")
                results['failed'] += 1
        
        results['completed_at'] = timezone.now().isoformat()
        
        # Update metrics
        metrics.increment('records_enriched', results['enriched'])
        
        # Schedule aggregation for enriched records
        if results['enriched'] > 0:
            aggregate_batch_data.delay(batch_id)
        
        logger.info(f"Enrichment completed: {results}")
        return results
        
    except Exception as e:
        logger.error(f"Error in enrichment task: {e}")
        raise self.retry(exc=e, countdown=60 * (2 ** self.request.retries))


@shared_task(bind=True, max_retries=5)
def aggregate_batch_data(self, batch_id: str, job_name: str = None) -> Dict[str, Any]:
    """
    Aggregate processed data into warehouse tables.
    
    Args:
        batch_id: Batch identifier to aggregate
        job_name: Optional specific aggregation job name
        
    Returns:
        Dict with aggregation results
    """
    run_id = str(uuid4())
    logger.info(f"Starting aggregation for batch: {batch_id}, job: {job_name}")
    
    try:
        # Get enriched events from this batch
        raw_events = RawEvent.objects.filter(
            batch_id=batch_id,
            validation_status='enriched',
            processed=False
        )
        
        if not raw_events.exists():
            logger.info(f"No enriched unprocessed events found for batch: {batch_id}")
            return {'batch_id': batch_id, 'total': 0, 'processed': 0, 'failed': 0}
        
        warehouse = WarehouseManager()
        results = {
            'run_id': run_id,
            'batch_id': batch_id,
            'job_name': job_name,
            'total': raw_events.count(),
            'processed': 0,
            'failed': 0,
            'started_at': timezone.now().isoformat(),
        }
        
        # Group events by source for efficient processing
        events_by_source = {}
        for event in raw_events:
            if event.source not in events_by_source:
                events_by_source[event.source] = []
            events_by_source[event.source].append(event)
        
        # Process each source
        for source, events in events_by_source.items():
            try:
                logger.info(f"Processing {len(events)} events from source: {source}")
                
                # Convert events to DataFrame for efficient processing
                records = []
                event_ids = []
                
                for event in events:
                    # Combine raw payload with enriched data
                    combined_data = {**event.raw_payload, **event.enriched_data}
                    records.append(combined_data)
                    event_ids.append(event.ingest_id)
                
                df = pd.DataFrame(records)
                
                # Aggregate based on source type
                if source in ['pos', 'api_sales']:
                    aggregation_results = warehouse.aggregate_sales_data(df, batch_id, run_id)
                elif source in ['inventory']:
                    aggregation_results = warehouse.aggregate_inventory_data(df, batch_id, run_id)
                elif source in ['staff']:
                    aggregation_results = warehouse.aggregate_staff_data(df, batch_id, run_id)
                else:
                    logger.warning(f"No aggregation handler for source: {source}")
                    continue
                
                # Mark events as processed
                for event in events:
                    event.processed = True
                    event.processed_at = timezone.now()
                    event.etl_run_id = run_id
                    event.save()
                
                results['processed'] += len(events)
                logger.info(f"Successfully processed {len(events)} events from {source}")
                
            except Exception as e:
                logger.error(f"Error processing source {source}: {e}")
                results['failed'] += len(events)
                
                # Create alert for processing failure
                alert_manager.create_alert(
                    'job_failure',
                    'high',
                    f"Aggregation failed for source {source}",
                    f"Batch: {batch_id}, Error: {str(e)}"
                )
        
        results['completed_at'] = timezone.now().isoformat()
        
        # Update metrics
        metrics.increment('records_aggregated', results['processed'])
        metrics.increment('aggregation_errors', results['failed'])
        
        # Log audit event
        AuditLog.objects.create(
            event_type='data_aggregated',
            message=f"Aggregated batch {batch_id}",
            details=results
        )
        
        logger.info(f"Aggregation completed: {results}")
        return results
        
    except Exception as e:
        logger.error(f"Error in aggregation task: {e}")
        
        # Create critical alert
        alert_manager.create_alert(
            'job_failure',
            'critical',
            f"Aggregation task failed for batch {batch_id}",
            str(e)
        )
        
        raise self.retry(exc=e, countdown=60 * (2 ** self.request.retries))


@shared_task(bind=True, max_retries=3)
def run_etl_job(self, job_id: int, manual_trigger: bool = False, 
               user_id: int = None, reason: str = None) -> Dict[str, Any]:
    """
    Execute a complete ETL job from start to finish.
    
    Args:
        job_id: ETL job ID to execute
        manual_trigger: Whether this was manually triggered
        user_id: User ID who triggered (if manual)
        reason: Reason for manual trigger
        
    Returns:
        Dict with job execution results
    """
    run_id = str(uuid4())
    
    try:
        job = ETLJob.objects.get(id=job_id)
        logger.info(f"Starting ETL job: {job.name} (ID: {job_id})")
        
        # Create ETL run record
        etl_run = ETLRun.objects.create(
            run_id=run_id,
            job=job,
            status='running',
            started_at=timezone.now(),
            config_snapshot=job.__dict__,
            triggered_by_id=user_id,
            trigger_reason=reason
        )
        
        # Log audit event
        AuditLog.objects.create(
            event_type='job_started',
            job=job,
            run=etl_run,
            user_id=user_id,
            message=f"Started ETL job: {job.name}",
            details={'manual_trigger': manual_trigger, 'reason': reason}
        )
        
        # Execute job based on type
        results = None
        if job.job_type == 'ingestion':
            results = _execute_ingestion_job(job, etl_run)
        elif job.job_type == 'validation':
            results = _execute_validation_job(job, etl_run)
        elif job.job_type == 'transformation':
            results = _execute_transformation_job(job, etl_run)
        elif job.job_type == 'aggregation':
            results = _execute_aggregation_job(job, etl_run)
        elif job.job_type == 'cleanup':
            results = _execute_cleanup_job(job, etl_run)
        
        # Update ETL run with results
        etl_run.status = 'success'
        etl_run.completed_at = timezone.now()
        etl_run.duration_seconds = (etl_run.completed_at - etl_run.started_at).total_seconds()
        etl_run.rows_processed = results.get('processed', 0)
        etl_run.rows_failed = results.get('failed', 0)
        etl_run.save()
        
        # Update job last run timestamp
        job.last_run_at = timezone.now()
        job.save()
        
        # Log completion
        AuditLog.objects.create(
            event_type='job_completed',
            job=job,
            run=etl_run,
            message=f"Completed ETL job: {job.name}",
            details=results
        )
        
        logger.info(f"ETL job completed successfully: {job.name}")
        return results
        
    except ETLJob.DoesNotExist:
        logger.error(f"ETL job not found: {job_id}")
        raise
        
    except Exception as e:
        logger.error(f"Error executing ETL job {job_id}: {e}")
        
        # Update run status
        if 'etl_run' in locals():
            etl_run.status = 'failed'
            etl_run.error_message = str(e)
            etl_run.completed_at = timezone.now()
            etl_run.save()
        
        # Create alert
        alert_manager.create_alert(
            'job_failure',
            'high',
            f"ETL job failed: {job.name if 'job' in locals() else job_id}",
            str(e)
        )
        
        raise self.retry(exc=e, countdown=60 * (2 ** self.request.retries))


@shared_task
def cleanup_old_data():
    """
    Clean up old data based on retention policies.
    """
    logger.info("Starting data cleanup task")
    
    try:
        results = {
            'raw_events_deleted': 0,
            'raw_errors_deleted': 0,
            'runs_archived': 0,
            'alerts_cleaned': 0,
        }
        
        # Clean up old raw events (default: 365 days)
        retention_days = getattr(settings, 'ETL_RAW_DATA_RETENTION_DAYS', 365)
        cutoff_date = timezone.now() - timedelta(days=retention_days)
        
        old_events = RawEvent.objects.filter(
            received_at__lt=cutoff_date,
            processed=True
        )
        results['raw_events_deleted'] = old_events.count()
        old_events.delete()
        
        # Clean up old error records (default: 90 days)
        error_retention_days = getattr(settings, 'ETL_ERROR_RETENTION_DAYS', 90)
        error_cutoff_date = timezone.now() - timedelta(days=error_retention_days)
        
        old_errors = RawError.objects.filter(
            failed_at__lt=error_cutoff_date,
            resolved=True
        )
        results['raw_errors_deleted'] = old_errors.count()
        old_errors.delete()
        
        # Archive old ETL runs (default: keep 30 days detailed, archive older)
        run_retention_days = getattr(settings, 'ETL_RUN_RETENTION_DAYS', 30)
        run_cutoff_date = timezone.now() - timedelta(days=run_retention_days)
        
        old_runs = ETLRun.objects.filter(
            created_at__lt=run_cutoff_date
        )
        # Archive instead of delete (implementation would depend on archival strategy)
        results['runs_archived'] = old_runs.count()
        
        # Clean up resolved alerts (default: 7 days)
        alert_retention_days = getattr(settings, 'ETL_ALERT_RETENTION_DAYS', 7)
        alert_cutoff_date = timezone.now() - timedelta(days=alert_retention_days)
        
        old_alerts = ETLAlert.objects.filter(
            resolved_at__lt=alert_cutoff_date,
            status='resolved'
        )
        results['alerts_cleaned'] = old_alerts.count()
        old_alerts.delete()
        
        logger.info(f"Cleanup completed: {results}")
        return results
        
    except Exception as e:
        logger.error(f"Error in cleanup task: {e}")
        raise


@shared_task
def health_check_sources():
    """
    Check health of all data sources.
    """
    logger.info("Starting data source health check")
    
    try:
        sources = DataSource.objects.filter(is_active=True)
        results = {
            'total_sources': sources.count(),
            'healthy': 0,
            'unhealthy': 0,
            'sources': {}
        }
        
        for source in sources:
            try:
                # Get connector for this source
                connector = ConnectorRegistry.get_connector(source.source_type)
                if connector:
                    health_status = connector.health_check(source.connection_config)
                    
                    source.connection_status = 'connected' if health_status['healthy'] else 'failed'
                    source.last_connected_at = timezone.now()
                    source.avg_response_time = health_status.get('response_time', 0)
                    source.save()
                    
                    if health_status['healthy']:
                        results['healthy'] += 1
                    else:
                        results['unhealthy'] += 1
                        
                        # Create alert for unhealthy source
                        alert_manager.create_alert(
                            'connection_failure',
                            'medium',
                            f"Data source health check failed: {source.name}",
                            health_status.get('error', 'Unknown health check failure')
                        )
                    
                    results['sources'][source.name] = health_status
                    
            except Exception as e:
                logger.error(f"Health check failed for source {source.name}: {e}")
                source.connection_status = 'failed'
                source.save()
                results['unhealthy'] += 1
        
        logger.info(f"Health check completed: {results}")
        return results
        
    except Exception as e:
        logger.error(f"Error in health check task: {e}")
        raise


# Helper functions
def _generate_ingest_id(source: str, record: Dict, batch_id: str, index: int) -> str:
    """Generate unique ingest ID for deduplication."""
    # Try to use business keys if available
    business_keys = []
    
    if source in ['pos', 'api_sales']:
        business_keys = ['order_id', 'transaction_id', 'receipt_number']
    elif source == 'inventory':
        business_keys = ['product_id', 'location_id', 'timestamp']
    elif source == 'staff':
        business_keys = ['employee_id', 'shift_id', 'date']
    
    # Use business key if available
    for key in business_keys:
        if key in record and record[key]:
            return f"{source}_{key}_{record[key]}"
    
    # Fallback to batch-based ID
    return f"{source}_{batch_id}_{index}"


def _execute_ingestion_job(job: ETLJob, etl_run: ETLRun) -> Dict[str, Any]:
    """Execute data ingestion job."""
    connector = ConnectorRegistry.get_connector(job.source_config.get('type'))
    if not connector:
        raise ValueError(f"No connector found for type: {job.source_config.get('type')}")
    
    # Fetch data from source
    data = connector.extract(job.source_config)
    
    # Ingest in batches
    batch_size = job.source_config.get('batch_size', 1000)
    total_records = len(data)
    processed = 0
    
    for i in range(0, total_records, batch_size):
        batch = data[i:i + batch_size]
        batch_id = f"{job.name}_{etl_run.run_id}_{i // batch_size}"
        
        result = ingest_data_batch.delay(
            job.source_config.get('source_name', job.name),
            batch,
            batch_id
        ).get()
        
        processed += result.get('ingested', 0)
    
    return {
        'total_records': total_records,
        'processed': processed,
        'batches': (total_records // batch_size) + (1 if total_records % batch_size else 0)
    }


def _execute_validation_job(job: ETLJob, etl_run: ETLRun) -> Dict[str, Any]:
    """Execute data validation job."""
    # Implementation would depend on specific validation rules
    pass


def _execute_transformation_job(job: ETLJob, etl_run: ETLRun) -> Dict[str, Any]:
    """Execute data transformation job."""
    # Implementation would depend on specific transformation rules
    pass


def _execute_aggregation_job(job: ETLJob, etl_run: ETLRun) -> Dict[str, Any]:
    """Execute data aggregation job."""
    # Implementation would depend on specific aggregation rules
    pass


def _execute_cleanup_job(job: ETLJob, etl_run: ETLRun) -> Dict[str, Any]:
    """Execute data cleanup job."""
    return cleanup_old_data.delay().get()