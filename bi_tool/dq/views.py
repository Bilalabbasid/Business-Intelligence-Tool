"""
Data Quality API Views
REST API endpoints for managing and monitoring data quality.
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, List, Any

from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.pagination import PageNumberPagination
from django.db.models import Q, Count, Avg, Max, Min
from django.utils import timezone
from django_filters.rest_framework import DjangoFilterBackend
from django.http import HttpResponse, JsonResponse
import csv

from .models import (
    DQRule, DQRun, DQViolation, DQMetric, DQConfig, 
    DQAnomalyDetection, DQRuleTemplate, DQRunStatus, DQSeverity
)
from .serializers import (
    DQRuleSerializer, DQRunSerializer, DQViolationSerializer,
    DQMetricSerializer, DQConfigSerializer, DQAnomalyDetectionSerializer,
    DQRuleTemplateSerializer, DQRuleCreateSerializer, DQRunSummarySerializer
)
from .rules import dq_registry
from .tasks import execute_dq_check, execute_dq_rule_set
from .anomaly_detection import dq_anomaly_detector
from core.permissions import IsManagerOrAbove  # Using IsManagerOrAbove instead of IsDataEngineerOrAdmin

logger = logging.getLogger(__name__)


class StandardResultsSetPagination(PageNumberPagination):
    """Standard pagination for DQ API endpoints."""
    page_size = 50
    page_size_query_param = 'page_size'
    max_page_size = 1000


class DQRuleViewSet(viewsets.ModelViewSet):
    """ViewSet for managing data quality rules."""
    
    queryset = DQRule.objects.all().order_by('-created_at')
    serializer_class = DQRuleSerializer
    permission_classes = [IsAuthenticated, IsManagerOrAbove]
    pagination_class = StandardResultsSetPagination
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['check_type', 'severity', 'enabled', 'target_database']
    
    def get_serializer_class(self):
        if self.action in ['create', 'update', 'partial_update']:
            return DQRuleCreateSerializer
        return DQRuleSerializer
    
    @action(detail=False, methods=['get'])
    def summary(self, request):
        """Get summary statistics for DQ rules."""
        total_rules = self.queryset.count()
        enabled_rules = self.queryset.filter(enabled=True).count()
        
        # Rules by severity
        severity_counts = self.queryset.values('severity').annotate(
            count=Count('id')
        ).order_by('severity')
        
        # Rules by check type
        check_type_counts = self.queryset.values('check_type').annotate(
            count=Count('id')
        ).order_by('check_type')
        
        # Recent rule activity
        recent_runs = DQRun.objects.filter(
            finished_at__gte=timezone.now() - timedelta(hours=24)
        ).count()
        
        return Response({
            'total_rules': total_rules,
            'enabled_rules': enabled_rules,
            'disabled_rules': total_rules - enabled_rules,
            'severity_distribution': severity_counts,
            'check_type_distribution': check_type_counts,
            'recent_executions_24h': recent_runs
        })
    
    @action(detail=True, methods=['post'])
    def execute(self, request, pk=None):
        """Execute a specific DQ rule immediately."""
        rule = self.get_object()
        
        if not rule.enabled:
            return Response(
                {'error': 'Cannot execute disabled rule'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            # Execute asynchronously
            task = execute_dq_check.delay(rule.id)
            
            return Response({
                'message': f'DQ check execution started for rule: {rule.name}',
                'rule_id': rule.id,
                'task_id': task.id
            })
            
        except Exception as e:
            logger.error(f"Error executing DQ rule {pk}: {str(e)}")
            return Response(
                {'error': f'Failed to execute rule: {str(e)}'}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=True, methods=['get'])
    def runs(self, request, pk=None):
        """Get recent runs for a specific rule."""
        rule = self.get_object()
        
        # Get query parameters
        days = int(request.query_params.get('days', 7))
        limit = int(request.query_params.get('limit', 100))
        
        since_date = timezone.now() - timedelta(days=days)
        
        runs = DQRun.objects.filter(
            rule=rule,
            finished_at__gte=since_date
        ).order_by('-finished_at')[:limit]
        
        serializer = DQRunSummarySerializer(runs, many=True)
        return Response(serializer.data)
    
    @action(detail=True, methods=['get'])
    def violations(self, request, pk=None):
        """Get recent violations for a specific rule."""
        rule = self.get_object()
        
        days = int(request.query_params.get('days', 7))
        acknowledged = request.query_params.get('acknowledged')
        
        since_date = timezone.now() - timedelta(days=days)
        
        violations_qs = DQViolation.objects.filter(
            rule=rule,
            detected_at__gte=since_date
        )
        
        if acknowledged is not None:
            violations_qs = violations_qs.filter(
                acknowledged=(acknowledged.lower() == 'true')
            )
        
        violations = violations_qs.order_by('-detected_at')[:100]
        serializer = DQViolationSerializer(violations, many=True)
        return Response(serializer.data)
    
    @action(detail=True, methods=['get'])
    def metrics(self, request, pk=None):
        """Get metrics trend for a specific rule."""
        rule = self.get_object()
        
        days = int(request.query_params.get('days', 30))
        metric_name = request.query_params.get('metric', 'dq_violations_count')
        
        since_date = timezone.now() - timedelta(days=days)
        
        metrics = DQMetric.objects.filter(
            rule=rule,
            metric_name=metric_name,
            recorded_at__gte=since_date
        ).order_by('recorded_at').values('recorded_at', 'metric_value')
        
        return Response(list(metrics))
    
    @action(detail=False, methods=['post'])
    def bulk_execute(self, request):
        """Execute multiple rules in bulk."""
        rule_ids = request.data.get('rule_ids', [])
        batch_name = request.data.get('batch_name', f'bulk_{timezone.now().strftime("%Y%m%d_%H%M%S")}')
        
        if not rule_ids:
            return Response(
                {'error': 'No rule IDs provided'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Validate rules exist and are enabled
        valid_rules = DQRule.objects.filter(
            id__in=rule_ids, 
            enabled=True
        ).values_list('id', flat=True)
        
        if not valid_rules:
            return Response(
                {'error': 'No valid enabled rules found'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            # Execute as batch
            task = execute_dq_rule_set.delay(list(valid_rules), batch_name)
            
            return Response({
                'message': f'Bulk execution started for {len(valid_rules)} rules',
                'batch_name': batch_name,
                'rule_count': len(valid_rules),
                'task_id': task.id
            })
            
        except Exception as e:
            logger.error(f"Error in bulk execution: {str(e)}")
            return Response(
                {'error': f'Failed to start bulk execution: {str(e)}'}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=False, methods=['post'])
    def load_manifest(self, request):
        """Load rules from YAML manifest file."""
        manifest_data = request.data.get('manifest_content')
        
        if not manifest_data:
            return Response(
                {'error': 'No manifest content provided'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            # Save manifest content to temporary file and load
            import tempfile
            import os
            
            with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
                f.write(manifest_data)
                temp_file = f.name
            
            try:
                results = dq_registry.load_rules_from_manifest(temp_file)
                return Response(results)
            finally:
                os.unlink(temp_file)
                
        except Exception as e:
            logger.error(f"Error loading manifest: {str(e)}")
            return Response(
                {'error': f'Failed to load manifest: {str(e)}'}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=False, methods=['get'])
    def export_manifest(self, request):
        """Export rules to YAML manifest."""
        try:
            # Apply filters
            rule_filter = {}
            if request.query_params.get('enabled'):
                rule_filter['enabled'] = request.query_params.get('enabled').lower() == 'true'
            if request.query_params.get('check_type'):
                rule_filter['check_type'] = request.query_params.get('check_type')
            if request.query_params.get('severity'):
                rule_filter['severity'] = request.query_params.get('severity')
            
            # Export to temporary file
            import tempfile
            with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
                temp_file = f.name
            
            success = dq_registry.export_rules_to_manifest(temp_file, rule_filter)
            
            if success:
                with open(temp_file, 'r') as f:
                    content = f.read()
                
                response = HttpResponse(content, content_type='application/x-yaml')
                response['Content-Disposition'] = 'attachment; filename="dq_rules_manifest.yaml"'
                
                import os
                os.unlink(temp_file)
                
                return response
            else:
                return Response(
                    {'error': 'Failed to export manifest'}, 
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )
                
        except Exception as e:
            logger.error(f"Error exporting manifest: {str(e)}")
            return Response(
                {'error': f'Failed to export manifest: {str(e)}'}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class DQRunViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet for viewing DQ run history."""
    
    queryset = DQRun.objects.all().order_by('-completed_at')
    serializer_class = DQRunSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = StandardResultsSetPagination
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['status', 'rule__name', 'rule__check_type', 'rule__severity']
    
    @action(detail=False, methods=['get'])
    def summary(self, request):
        """Get summary of recent DQ runs."""
        # Get query parameters
        hours = int(request.query_params.get('hours', 24))
        since_time = timezone.now() - timedelta(hours=hours)
        
        # Base queryset
        runs_qs = self.queryset.filter(finished_at__gte=since_time)
        
        # Calculate summary statistics
        total_runs = runs_qs.count()
        successful_runs = runs_qs.filter(status=DQRunStatus.SUCCESS).count()
        failed_runs = runs_qs.filter(status=DQRunStatus.FAILED).count()
        
        # Total violations
        total_violations = runs_qs.aggregate(
            total=Count('violations_count')
        )['total'] or 0
        
        # Average duration
        avg_duration = runs_qs.aggregate(
            avg=Avg('duration_seconds')
        )['avg'] or 0
        
        # Rules with most violations
        top_violating_rules = runs_qs.filter(
            violations_count__gt=0
        ).values(
            'rule__name', 'rule__severity'
        ).annotate(
            total_violations=Count('violations_count')
        ).order_by('-total_violations')[:10]
        
        return Response({
            'time_window_hours': hours,
            'summary': {
                'total_runs': total_runs,
                'successful_runs': successful_runs,
                'failed_runs': failed_runs,
                'success_rate': (successful_runs / total_runs * 100) if total_runs > 0 else 0,
                'total_violations': total_violations,
                'avg_duration_seconds': round(avg_duration, 2)
            },
            'top_violating_rules': list(top_violating_rules)
        })
    
    @action(detail=True, methods=['get'])
    def violations(self, request, pk=None):
        """Get violations for a specific run."""
        run = self.get_object()
        violations = DQViolation.objects.filter(run=run).order_by('-detected_at')
        serializer = DQViolationSerializer(violations, many=True)
        return Response(serializer.data)


class DQViolationViewSet(viewsets.ModelViewSet):
    """ViewSet for managing DQ violations."""
    
    queryset = DQViolation.objects.all().order_by('-created_at')
    serializer_class = DQViolationSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = StandardResultsSetPagination
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['severity', 'acknowledged', 'rule__name', 'rule__check_type']
    
    @action(detail=True, methods=['post'])
    def acknowledge(self, request, pk=None):
        """Acknowledge a violation."""
        violation = self.get_object()
        
        violation.acknowledged = True
        violation.acknowledged_by = request.user.username
        violation.acknowledged_at = timezone.now()
        violation.acknowledgment_note = request.data.get('note', '')
        violation.save()
        
        return Response({
            'message': 'Violation acknowledged',
            'acknowledged_at': violation.acknowledged_at,
            'acknowledged_by': violation.acknowledged_by
        })
    
    @action(detail=False, methods=['post'])
    def bulk_acknowledge(self, request):
        """Acknowledge multiple violations in bulk."""
        violation_ids = request.data.get('violation_ids', [])
        note = request.data.get('note', '')
        
        if not violation_ids:
            return Response(
                {'error': 'No violation IDs provided'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        updated_count = DQViolation.objects.filter(
            id__in=violation_ids,
            acknowledged=False
        ).update(
            acknowledged=True,
            acknowledged_by=request.user.username,
            acknowledged_at=timezone.now(),
            acknowledgment_note=note
        )
        
        return Response({
            'message': f'Acknowledged {updated_count} violations',
            'updated_count': updated_count
        })
    
    @action(detail=False, methods=['get'])
    def export_csv(self, request):
        """Export violations to CSV."""
        # Apply filters
        violations_qs = self.filter_queryset(self.get_queryset())
        
        # Limit to prevent large exports
        limit = int(request.query_params.get('limit', 10000))
        violations = violations_qs[:limit]
        
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="dq_violations.csv"'
        
        writer = csv.writer(response)
        writer.writerow([
            'ID', 'Rule Name', 'Violation Type', 'Severity', 'Description',
            'Detected At', 'Acknowledged', 'Acknowledged By', 'Run ID'
        ])
        
        for violation in violations:
            writer.writerow([
                violation.id,
                violation.rule.name,
                violation.violation_type,
                violation.severity,
                violation.description,
                violation.detected_at,
                violation.acknowledged,
                violation.acknowledged_by or '',
                violation.run_id
            ])
        
        return response


class DQMetricViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet for viewing DQ metrics."""
    
    queryset = DQMetric.objects.all().order_by('-timestamp')
    serializer_class = DQMetricSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = StandardResultsSetPagination
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['metric_name', 'rule__name']
    
    @action(detail=False, methods=['get'])
    def time_series(self, request):
        """Get time series data for metrics."""
        metric_name = request.query_params.get('metric_name', 'dq_violations_count')
        days = int(request.query_params.get('days', 7))
        rule_name = request.query_params.get('rule_name')
        
        since_date = timezone.now() - timedelta(days=days)
        
        metrics_qs = self.queryset.filter(
            metric_name=metric_name,
            recorded_at__gte=since_date
        )
        
        if rule_name:
            metrics_qs = metrics_qs.filter(rule__name=rule_name)
        
        metrics = metrics_qs.values(
            'recorded_at', 'metric_value', 'rule__name'
        ).order_by('recorded_at')
        
        return Response(list(metrics))


class DQAnomalyDetectionViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet for viewing anomaly detection results."""
    
    queryset = DQAnomalyDetection.objects.all().order_by('-detected_at')
    serializer_class = DQAnomalyDetectionSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = StandardResultsSetPagination
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['detection_method', 'rule__name']
    
    @action(detail=False, methods=['post'])
    def detect_anomalies(self, request):
        """Trigger anomaly detection for specified rules."""
        rule_ids = request.data.get('rule_ids', [])
        method = request.data.get('method', 'statistical')
        lookback_days = int(request.data.get('lookback_days', 30))
        
        if not rule_ids:
            return Response(
                {'error': 'No rule IDs provided'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        results = []
        for rule_id in rule_ids:
            try:
                anomalies = dq_anomaly_detector.detect_anomalies(
                    rule_id=rule_id,
                    method=method,
                    lookback_days=lookback_days
                )
                
                results.append({
                    'rule_id': rule_id,
                    'anomalies_found': len([a for a in anomalies if a.is_anomaly]),
                    'total_checks': len(anomalies)
                })
                
            except Exception as e:
                results.append({
                    'rule_id': rule_id,
                    'error': str(e)
                })
        
        return Response({
            'method': method,
            'lookback_days': lookback_days,
            'results': results
        })


class DQConfigViewSet(viewsets.ModelViewSet):
    """ViewSet for managing DQ system configuration."""
    
    queryset = DQConfig.objects.all()
    serializer_class = DQConfigSerializer
    permission_classes = [IsAuthenticated, IsManagerOrAbove]


class DQRuleTemplateViewSet(viewsets.ModelViewSet):
    """ViewSet for managing DQ rule templates."""
    
    queryset = DQRuleTemplate.objects.all().order_by('category', 'name')
    serializer_class = DQRuleTemplateSerializer
    permission_classes = [IsAuthenticated, IsManagerOrAbove]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['category', 'check_type', 'enabled']


@action(detail=False, methods=['get'])
def health_check(request):
    """Health check endpoint for DQ system."""
    try:
        # Basic system health checks
        health_data = {
            'status': 'healthy',
            'timestamp': timezone.now().isoformat(),
            'checks': {
                'database': 'pass',
                'rules_count': DQRule.objects.filter(enabled=True).count(),
                'recent_runs': DQRun.objects.filter(
                    finished_at__gte=timezone.now() - timedelta(hours=1)
                ).count()
            }
        }
        
        # Check for system issues
        if health_data['checks']['rules_count'] == 0:
            health_data['status'] = 'warning'
            health_data['checks']['database'] = 'warn - no enabled rules'
        
        if health_data['checks']['recent_runs'] == 0:
            health_data['status'] = 'warning'
            health_data['checks']['recent_activity'] = 'warn - no recent executions'
        
        return JsonResponse(health_data)
        
    except Exception as e:
        return JsonResponse({
            'status': 'unhealthy',
            'timestamp': timezone.now().isoformat(),
            'error': str(e)
        }, status=500)