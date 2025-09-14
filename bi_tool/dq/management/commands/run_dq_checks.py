"""
Django management command to execute DQ checks manually.
"""

from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone
from dq.models import DQRule
from dq.tasks import execute_dq_check, execute_dq_rule_set


class Command(BaseCommand):
    help = 'Execute data quality checks manually'

    def add_arguments(self, parser):
        parser.add_argument(
            '--rule-id',
            type=int,
            help='Execute a specific rule by ID'
        )
        
        parser.add_argument(
            '--rule-name',
            type=str,
            help='Execute a specific rule by name'
        )
        
        parser.add_argument(
            '--check-type',
            type=str,
            choices=['row_count', 'null_rate', 'uniqueness', 'range_check', 
                    'cardinality', 'ref_integrity', 'timeliness', 'schema_drift', 'volume_anomaly'],
            help='Execute all rules of a specific check type'
        )
        
        parser.add_argument(
            '--severity',
            type=str,
            choices=['CRITICAL', 'HIGH', 'MEDIUM', 'LOW', 'INFO'],
            help='Execute all rules of a specific severity'
        )
        
        parser.add_argument(
            '--all',
            action='store_true',
            help='Execute all enabled rules'
        )
        
        parser.add_argument(
            '--batch-name',
            type=str,
            help='Custom batch name for execution tracking'
        )
        
        parser.add_argument(
            '--async',
            action='store_true',
            dest='asynchronous',
            help='Execute asynchronously (default: synchronous for single rules)'
        )

    def handle(self, *args, **options):
        rule_id = options.get('rule_id')
        rule_name = options.get('rule_name')
        check_type = options.get('check_type')
        severity = options.get('severity')
        execute_all = options.get('all')
        batch_name = options.get('batch_name', f'manual_{timezone.now().strftime("%Y%m%d_%H%M%S")}')
        asynchronous = options.get('asynchronous', False)
        
        # Validate arguments
        arg_count = sum(bool(x) for x in [rule_id, rule_name, check_type, severity, execute_all])
        if arg_count == 0:
            raise CommandError('Must specify one of: --rule-id, --rule-name, --check-type, --severity, or --all')
        elif arg_count > 1:
            raise CommandError('Can only specify one selection criteria at a time')
        
        try:
            # Build queryset based on options
            if rule_id:
                rules = DQRule.objects.filter(id=rule_id, enabled=True)
                if not rules.exists():
                    raise CommandError(f'Rule with ID {rule_id} not found or not enabled')
                    
            elif rule_name:
                rules = DQRule.objects.filter(name=rule_name, enabled=True)
                if not rules.exists():
                    raise CommandError(f'Rule with name "{rule_name}" not found or not enabled')
                    
            elif check_type:
                rules = DQRule.objects.filter(check_type=check_type, enabled=True)
                
            elif severity:
                rules = DQRule.objects.filter(severity=severity, enabled=True)
                
            elif execute_all:
                rules = DQRule.objects.filter(enabled=True)
            
            rule_count = rules.count()
            if rule_count == 0:
                raise CommandError('No matching enabled rules found')
            
            self.stdout.write(f'Found {rule_count} rule(s) to execute')
            
            # Execute rules
            if rule_count == 1 and not asynchronous:
                # Single rule execution - synchronous by default
                rule = rules.first()
                self.stdout.write(f'Executing rule: {rule.name}')
                
                task = execute_dq_check.delay(rule.id)
                self.stdout.write(f'Task started with ID: {task.id}')
                
                # Wait for completion and show result
                try:
                    result = task.get(timeout=300)  # 5 minute timeout
                    if result.get('success'):
                        self.stdout.write(
                            self.style.SUCCESS(
                                f'Rule execution completed successfully. '
                                f'Violations: {result.get("violations_count", 0)}'
                            )
                        )
                    else:
                        self.stdout.write(
                            self.style.ERROR(
                                f'Rule execution failed: {result.get("error", "Unknown error")}'
                            )
                        )
                except Exception as e:
                    self.stdout.write(
                        self.style.ERROR(f'Task execution failed: {str(e)}')
                    )
                    
            else:
                # Multiple rules or async execution
                rule_ids = list(rules.values_list('id', flat=True))
                self.stdout.write(f'Executing {len(rule_ids)} rules asynchronously in batch: {batch_name}')
                
                task = execute_dq_rule_set.delay(rule_ids, batch_name)
                self.stdout.write(f'Batch task started with ID: {task.id}')
                self.stdout.write('Use Celery monitoring tools to track progress')
                
                if not asynchronous:
                    self.stdout.write('Waiting for batch completion...')
                    try:
                        result = task.get(timeout=600)  # 10 minute timeout
                        self.stdout.write(
                            self.style.SUCCESS(
                                f'Batch execution completed. '
                                f'Success: {result.get("successful", 0)}, '
                                f'Failed: {result.get("failed", 0)}, '
                                f'Total violations: {result.get("total_violations", 0)}'
                            )
                        )
                    except Exception as e:
                        self.stdout.write(
                            self.style.ERROR(f'Batch execution failed: {str(e)}')
                        )
                        
        except Exception as e:
            raise CommandError(f'Failed to execute DQ checks: {str(e)}')