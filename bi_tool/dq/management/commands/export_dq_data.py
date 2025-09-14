"""
Django management command to export DQ rules and data.
"""

import os
import json
import csv
from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone
from datetime import timedelta
from dq.models import DQRule, DQRun, DQViolation, DQMetric
from dq.rules import dq_registry


class Command(BaseCommand):
    help = 'Export data quality rules and operational data'

    def add_arguments(self, parser):
        parser.add_argument(
            'export_type',
            choices=['rules', 'runs', 'violations', 'metrics', 'manifest'],
            help='Type of data to export'
        )
        
        parser.add_argument(
            'output_file',
            type=str,
            help='Output file path'
        )
        
        parser.add_argument(
            '--format',
            choices=['json', 'csv', 'yaml'],
            default='json',
            help='Export format (default: json)'
        )
        
        parser.add_argument(
            '--days',
            type=int,
            default=30,
            help='Number of days to export (for runs, violations, metrics)'
        )
        
        parser.add_argument(
            '--rule-name',
            type=str,
            help='Filter by rule name'
        )
        
        parser.add_argument(
            '--check-type',
            type=str,
            help='Filter by check type'
        )
        
        parser.add_argument(
            '--severity',
            type=str,
            help='Filter by severity'
        )
        
        parser.add_argument(
            '--limit',
            type=int,
            default=10000,
            help='Maximum number of records to export'
        )

    def handle(self, *args, **options):
        export_type = options['export_type']
        output_file = options['output_file']
        format_type = options['format']
        days = options['days']
        rule_name = options.get('rule_name')
        check_type = options.get('check_type')
        severity = options.get('severity')
        limit = options['limit']
        
        self.stdout.write(f'Exporting {export_type} to {output_file} in {format_type} format')
        
        try:
            if export_type == 'manifest':
                self._export_rules_manifest(output_file, rule_name, check_type, severity)
            elif export_type == 'rules':
                self._export_rules(output_file, format_type, rule_name, check_type, severity)
            elif export_type == 'runs':
                self._export_runs(output_file, format_type, days, rule_name, limit)
            elif export_type == 'violations':
                self._export_violations(output_file, format_type, days, rule_name, limit)
            elif export_type == 'metrics':
                self._export_metrics(output_file, format_type, days, rule_name, limit)
                
            self.stdout.write(self.style.SUCCESS(f'Export completed: {output_file}'))
            
        except Exception as e:
            raise CommandError(f'Export failed: {str(e)}')

    def _export_rules_manifest(self, output_file, rule_name, check_type, severity):
        """Export rules as YAML manifest."""
        rule_filter = {}
        if rule_name:
            rule_filter['name'] = rule_name
        if check_type:
            rule_filter['check_type'] = check_type
        if severity:
            rule_filter['severity'] = severity
            
        success = dq_registry.export_rules_to_manifest(output_file, rule_filter)
        if not success:
            raise CommandError('Failed to export rules manifest')

    def _export_rules(self, output_file, format_type, rule_name, check_type, severity):
        """Export rules data."""
        queryset = DQRule.objects.all()
        
        # Apply filters
        if rule_name:
            queryset = queryset.filter(name__icontains=rule_name)
        if check_type:
            queryset = queryset.filter(check_type=check_type)
        if severity:
            queryset = queryset.filter(severity=severity)
        
        rules = list(queryset.values(
            'id', 'name', 'description', 'check_type', 'target_database',
            'target_collection', 'target_column', 'threshold', 'severity',
            'schedule', 'enabled', 'owners', 'tags', 'created_at', 'updated_at'
        ))
        
        # Convert datetime objects to strings
        for rule in rules:
            rule['created_at'] = rule['created_at'].isoformat() if rule['created_at'] else None
            rule['updated_at'] = rule['updated_at'].isoformat() if rule['updated_at'] else None
        
        self._write_data(output_file, format_type, rules, 'rules')

    def _export_runs(self, output_file, format_type, days, rule_name, limit):
        """Export runs data."""
        since_date = timezone.now() - timedelta(days=days)
        
        queryset = DQRun.objects.filter(finished_at__gte=since_date)
        
        if rule_name:
            queryset = queryset.filter(rule__name__icontains=rule_name)
        
        runs = list(queryset.select_related('rule').values(
            'id', 'rule__name', 'status', 'started_at', 'finished_at',
            'duration_seconds', 'rows_scanned', 'violations_count',
            'triggered_by', 'error_message'
        ).order_by('-finished_at')[:limit])
        
        # Convert datetime objects to strings
        for run in runs:
            run['started_at'] = run['started_at'].isoformat() if run['started_at'] else None
            run['finished_at'] = run['finished_at'].isoformat() if run['finished_at'] else None
        
        self._write_data(output_file, format_type, runs, 'runs')

    def _export_violations(self, output_file, format_type, days, rule_name, limit):
        """Export violations data."""
        since_date = timezone.now() - timedelta(days=days)
        
        queryset = DQViolation.objects.filter(detected_at__gte=since_date)
        
        if rule_name:
            queryset = queryset.filter(rule__name__icontains=rule_name)
        
        violations = list(queryset.select_related('rule', 'run').values(
            'id', 'rule__name', 'run__id', 'violation_type', 'description',
            'severity', 'detected_at', 'acknowledged', 'acknowledged_by',
            'acknowledged_at', 'acknowledgment_note'
        ).order_by('-detected_at')[:limit])
        
        # Convert datetime objects to strings
        for violation in violations:
            violation['detected_at'] = violation['detected_at'].isoformat() if violation['detected_at'] else None
            violation['acknowledged_at'] = violation['acknowledged_at'].isoformat() if violation['acknowledged_at'] else None
        
        self._write_data(output_file, format_type, violations, 'violations')

    def _export_metrics(self, output_file, format_type, days, rule_name, limit):
        """Export metrics data."""
        since_date = timezone.now() - timedelta(days=days)
        
        queryset = DQMetric.objects.filter(recorded_at__gte=since_date)
        
        if rule_name:
            queryset = queryset.filter(rule__name__icontains=rule_name)
        
        metrics = list(queryset.select_related('rule').values(
            'id', 'rule__name', 'metric_name', 'metric_value',
            'tags', 'recorded_at'
        ).order_by('-recorded_at')[:limit])
        
        # Convert datetime objects to strings
        for metric in metrics:
            metric['recorded_at'] = metric['recorded_at'].isoformat() if metric['recorded_at'] else None
        
        self._write_data(output_file, format_type, metrics, 'metrics')

    def _write_data(self, output_file, format_type, data, data_type):
        """Write data to file in specified format."""
        # Create output directory if it doesn't exist
        os.makedirs(os.path.dirname(output_file), exist_ok=True)
        
        if format_type == 'json':
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump({
                    'export_type': data_type,
                    'exported_at': timezone.now().isoformat(),
                    'total_records': len(data),
                    'data': data
                }, f, indent=2, ensure_ascii=False)
                
        elif format_type == 'csv':
            if not data:
                raise CommandError('No data to export')
                
            with open(output_file, 'w', newline='', encoding='utf-8') as f:
                writer = csv.DictWriter(f, fieldnames=data[0].keys())
                writer.writeheader()
                writer.writerows(data)
                
        elif format_type == 'yaml':
            import yaml
            with open(output_file, 'w', encoding='utf-8') as f:
                yaml.dump({
                    'export_type': data_type,
                    'exported_at': timezone.now().isoformat(),
                    'total_records': len(data),
                    'data': data
                }, f, default_flow_style=False, sort_keys=False, indent=2)