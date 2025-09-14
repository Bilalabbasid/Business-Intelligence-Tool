"""
Comprehensive test suite for Data Quality system components.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from django.test import TestCase, TransactionTestCase
from django.db import transaction
from django.core.management import call_command
from celery import Celery
from celery.result import AsyncResult
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from decimal import Decimal

from ..models import (
    DQRule, DQRun, DQViolation, DQConfig, 
    DQAnomalyDetection, DQMetric, DQRuleTemplate
)
from ..checks import DQCheckExecutor
from ..rules import DQRuleRegistry
from ..tasks import execute_dq_rule, run_scheduled_checks
from ..alerts import DQAlertManager
from ..anomaly_detection import DQAnomalyDetector


class DQModelsTestCase(TestCase):
    """Test DQ model functionality."""
    
    def setUp(self):
        self.config = DQConfig.objects.create(
            key='test_db_connection',
            value='postgresql://test:test@localhost/test',
            description='Test database connection'
        )
        
        self.rule = DQRule.objects.create(
            name='test_null_check',
            description='Test null rate check',
            rule_type='null_rate',
            database='test_db',
            table_name='test_table',
            column_name='test_column',
            threshold=0.05,
            severity='HIGH',
            schedule='0 */6 * * *',
            is_active=True,
            params={'max_null_rate': 0.05}
        )
    
    def test_dq_rule_creation(self):
        """Test DQRule model creation and validation."""
        self.assertEqual(self.rule.name, 'test_null_check')
        self.assertEqual(self.rule.rule_type, 'null_rate')
        self.assertTrue(self.rule.is_active)
        self.assertEqual(self.rule.severity, 'HIGH')
    
    def test_dq_rule_string_representation(self):
        """Test DQRule string representation."""
        expected = f"test_null_check (null_rate) - HIGH"
        self.assertEqual(str(self.rule), expected)
    
    def test_dq_run_creation(self):
        """Test DQRun model creation."""
        run = DQRun.objects.create(
            rule=self.rule,
            status='COMPLETED',
            started_at=datetime.now(),
            completed_at=datetime.now(),
            records_checked=1000,
            violations_found=25,
            execution_time=15.5,
            metadata={'query_time': 12.3}
        )
        
        self.assertEqual(run.rule, self.rule)
        self.assertEqual(run.status, 'COMPLETED')
        self.assertEqual(run.records_checked, 1000)
        self.assertEqual(run.violations_found, 25)
    
    def test_dq_violation_creation(self):
        """Test DQViolation model creation."""
        run = DQRun.objects.create(
            rule=self.rule,
            status='COMPLETED'
        )
        
        violation = DQViolation.objects.create(
            run=run,
            severity='HIGH',
            message='Null rate exceeded threshold',
            details={'actual_rate': 0.08, 'threshold': 0.05},
            record_id='test_record_123'
        )
        
        self.assertEqual(violation.run, run)
        self.assertEqual(violation.severity, 'HIGH')
        self.assertIn('exceeded', violation.message)
    
    def test_dq_rule_template_creation(self):
        """Test DQRuleTemplate model creation."""
        template = DQRuleTemplate.objects.create(
            name='Null Check Template',
            rule_type='null_rate',
            description='Template for null rate checks',
            default_params={
                'max_null_rate': 0.05,
                'alert_threshold': 0.1
            },
            default_severity='MEDIUM',
            category='completeness'
        )
        
        self.assertEqual(template.name, 'Null Check Template')
        self.assertEqual(template.rule_type, 'null_rate')
        self.assertEqual(template.category, 'completeness')


class DQCheckExecutorTestCase(TestCase):
    """Test DQ check execution logic."""
    
    def setUp(self):
        self.executor = DQCheckExecutor()
        self.mock_connection = MagicMock()
        
        # Sample data for testing
        self.sample_data = pd.DataFrame({
            'id': range(1, 101),
            'name': ['User_' + str(i) if i % 10 != 0 else None for i in range(1, 101)],
            'email': [f'user{i}@test.com' for i in range(1, 101)],
            'age': [25 + (i % 50) for i in range(1, 101)],
            'created_at': [datetime.now() - timedelta(hours=i) for i in range(1, 101)]
        })
    
    @patch('dq.checks.create_engine')
    def test_row_count_check(self, mock_create_engine):
        """Test row count check execution."""
        mock_create_engine.return_value = self.mock_connection
        
        # Mock query result
        self.mock_connection.execute.return_value.fetchone.return_value = (100,)
        
        rule = DQRule(
            rule_type='row_count',
            database='test_db',
            table_name='users',
            params={'min_rows': 50, 'max_rows': 200}
        )
        
        result = self.executor.execute_check(rule)
        
        self.assertTrue(result['passed'])
        self.assertEqual(result['records_checked'], 100)
        self.assertEqual(result['violations_found'], 0)
    
    @patch('dq.checks.create_engine')
    def test_null_rate_check(self, mock_create_engine):
        """Test null rate check execution."""
        mock_create_engine.return_value = self.mock_connection
        
        # Mock query results: total rows and null rows
        self.mock_connection.execute.side_effect = [
            MagicMock(fetchone=MagicMock(return_value=(100,))),  # total
            MagicMock(fetchone=MagicMock(return_value=(10,)))    # nulls
        ]
        
        rule = DQRule(
            rule_type='null_rate',
            database='test_db',
            table_name='users',
            column_name='name',
            params={'max_null_rate': 0.05}
        )
        
        result = self.executor.execute_check(rule)
        
        self.assertFalse(result['passed'])  # 10% null rate > 5% threshold
        self.assertEqual(result['records_checked'], 100)
        self.assertEqual(result['violations_found'], 1)
    
    @patch('dq.checks.create_engine')
    def test_uniqueness_check(self, mock_create_engine):
        """Test uniqueness check execution."""
        mock_create_engine.return_value = self.mock_connection
        
        # Mock query results: total rows and distinct rows
        self.mock_connection.execute.side_effect = [
            MagicMock(fetchone=MagicMock(return_value=(100,))),  # total
            MagicMock(fetchone=MagicMock(return_value=(95,)))    # distinct
        ]
        
        rule = DQRule(
            rule_type='uniqueness',
            database='test_db',
            table_name='users',
            column_name='email',
            params={'min_uniqueness_rate': 0.98}
        )
        
        result = self.executor.execute_check(rule)
        
        self.assertFalse(result['passed'])  # 95% uniqueness < 98% threshold
        self.assertEqual(result['violations_found'], 1)
    
    def test_check_type_validation(self):
        """Test invalid check type handling."""
        rule = DQRule(
            rule_type='invalid_check_type',
            database='test_db',
            table_name='users'
        )
        
        with self.assertRaises(ValueError):
            self.executor.execute_check(rule)


class DQRuleRegistryTestCase(TestCase):
    """Test DQ rule registry functionality."""
    
    def setUp(self):
        self.registry = DQRuleRegistry()
    
    def test_rule_registration(self):
        """Test rule registration and retrieval."""
        rules_data = {
            'databases': {
                'test_db': {
                    'connection': 'postgresql://test:test@localhost/test',
                    'tables': {
                        'users': {
                            'rules': [
                                {
                                    'name': 'users_row_count',
                                    'type': 'row_count',
                                    'params': {'min_rows': 100}
                                }
                            ]
                        }
                    }
                }
            }
        }
        
        self.registry.register_rules_from_config(rules_data)
        rules = self.registry.get_rules_by_database('test_db')
        
        self.assertEqual(len(rules), 1)
        self.assertEqual(rules[0].name, 'users_row_count')
        self.assertEqual(rules[0].rule_type, 'row_count')
    
    def test_rule_validation(self):
        """Test rule configuration validation."""
        invalid_rules_data = {
            'databases': {
                'test_db': {
                    'tables': {
                        'users': {
                            'rules': [
                                {
                                    'name': 'invalid_rule',
                                    'type': 'invalid_type'  # Invalid rule type
                                }
                            ]
                        }
                    }
                }
            }
        }
        
        with self.assertRaises(ValueError):
            self.registry.register_rules_from_config(invalid_rules_data)
    
    @patch('dq.rules.yaml.safe_load')
    @patch('builtins.open')
    def test_yaml_config_loading(self, mock_open, mock_yaml_load):
        """Test YAML configuration file loading."""
        mock_yaml_load.return_value = {
            'databases': {
                'test_db': {
                    'connection': 'postgresql://test:test@localhost/test',
                    'tables': {
                        'products': {
                            'rules': [
                                {
                                    'name': 'product_completeness',
                                    'type': 'null_rate',
                                    'column': 'name',
                                    'params': {'max_null_rate': 0.01}
                                }
                            ]
                        }
                    }
                }
            }
        }
        
        self.registry.load_rules_from_yaml('test_config.yaml')
        rules = self.registry.get_all_rules()
        
        self.assertEqual(len(rules), 1)
        self.assertEqual(rules[0].name, 'product_completeness')


class DQTasksTestCase(TransactionTestCase):
    """Test Celery task execution."""
    
    def setUp(self):
        self.rule = DQRule.objects.create(
            name='test_async_rule',
            rule_type='row_count',
            database='test_db',
            table_name='test_table',
            params={'min_rows': 100},
            is_active=True
        )
    
    @patch('dq.tasks.DQCheckExecutor.execute_check')
    def test_execute_dq_rule_task_success(self, mock_execute):
        """Test successful DQ rule execution task."""
        mock_execute.return_value = {
            'passed': True,
            'records_checked': 150,
            'violations_found': 0,
            'execution_time': 5.2,
            'details': {}
        }
        
        result = execute_dq_rule.apply(args=[self.rule.id])
        
        self.assertTrue(result.successful())
        
        # Verify DQRun was created
        run = DQRun.objects.filter(rule=self.rule).first()
        self.assertIsNotNone(run)
        self.assertEqual(run.status, 'COMPLETED')
        self.assertEqual(run.records_checked, 150)
    
    @patch('dq.tasks.DQCheckExecutor.execute_check')
    def test_execute_dq_rule_task_failure(self, mock_execute):
        """Test failed DQ rule execution task."""
        mock_execute.side_effect = Exception('Database connection failed')
        
        result = execute_dq_rule.apply(args=[self.rule.id])
        
        self.assertFalse(result.successful())
        
        # Verify DQRun was created with failure status
        run = DQRun.objects.filter(rule=self.rule).first()
        self.assertIsNotNone(run)
        self.assertEqual(run.status, 'FAILED')
    
    @patch('dq.tasks.execute_dq_rule.delay')
    def test_run_scheduled_checks_task(self, mock_execute_delay):
        """Test scheduled checks execution task."""
        # Create multiple active rules
        DQRule.objects.create(
            name='rule_2',
            rule_type='null_rate',
            database='test_db',
            table_name='test_table',
            column_name='test_column',
            is_active=True
        )
        
        mock_execute_delay.return_value = Mock(id='task_123')
        
        result = run_scheduled_checks.apply()
        
        self.assertTrue(result.successful())
        self.assertEqual(mock_execute_delay.call_count, 2)  # 2 active rules


class DQAlertsTestCase(TestCase):
    """Test DQ alerting functionality."""
    
    def setUp(self):
        self.alert_manager = DQAlertManager()
        self.rule = DQRule.objects.create(
            name='test_alert_rule',
            rule_type='row_count',
            database='test_db',
            table_name='test_table',
            severity='HIGH'
        )
        
        self.run = DQRun.objects.create(
            rule=self.rule,
            status='FAILED',
            records_checked=0,
            violations_found=1
        )
        
        self.violation = DQViolation.objects.create(
            run=self.run,
            severity='HIGH',
            message='Row count below threshold'
        )
    
    @patch('dq.alerts.send_mail')
    def test_email_alert_sending(self, mock_send_mail):
        """Test email alert sending."""
        mock_send_mail.return_value = True
        
        result = self.alert_manager.send_email_alert(
            self.violation,
            ['admin@test.com']
        )
        
        self.assertTrue(result)
        mock_send_mail.assert_called_once()
        
        # Check email content
        args, kwargs = mock_send_mail.call_args
        self.assertIn('Data Quality Alert', kwargs['subject'])
        self.assertIn('HIGH', kwargs['message'])
    
    @patch('requests.post')
    def test_slack_alert_sending(self, mock_post):
        """Test Slack alert sending."""
        mock_post.return_value.status_code = 200
        
        result = self.alert_manager.send_slack_alert(
            self.violation,
            'https://hooks.slack.com/test-webhook'
        )
        
        self.assertTrue(result)
        mock_post.assert_called_once()
        
        # Check Slack payload
        payload = mock_post.call_args[1]['json']
        self.assertIn('Data Quality Alert', payload['text'])
    
    @patch('requests.post')
    def test_pagerduty_alert_sending(self, mock_post):
        """Test PagerDuty alert sending."""
        mock_post.return_value.status_code = 202
        
        result = self.alert_manager.send_pagerduty_alert(
            self.violation,
            'test-routing-key'
        )
        
        self.assertTrue(result)
        mock_post.assert_called_once()
        
        # Check PagerDuty payload
        payload = mock_post.call_args[1]['json']
        self.assertEqual(payload['event_action'], 'trigger')
        self.assertEqual(payload['payload']['severity'], 'error')
    
    def test_alert_routing_by_severity(self):
        """Test alert routing based on severity."""
        # Test critical alert routing
        critical_violation = DQViolation.objects.create(
            run=self.run,
            severity='CRITICAL',
            message='Critical data quality issue'
        )
        
        channels = self.alert_manager.get_alert_channels(critical_violation)
        
        # Critical should include all channels
        expected_channels = ['email', 'slack', 'pagerduty']
        self.assertEqual(set(channels), set(expected_channels))
        
        # Test low severity alert routing
        low_violation = DQViolation.objects.create(
            run=self.run,
            severity='LOW',
            message='Low priority issue'
        )
        
        channels = self.alert_manager.get_alert_channels(low_violation)
        
        # Low should only include email
        self.assertEqual(channels, ['email'])


class DQAnomalyDetectionTestCase(TestCase):
    """Test anomaly detection functionality."""
    
    def setUp(self):
        self.detector = DQAnomalyDetector()
        
        # Create historical metrics data
        self.historical_data = [
            {'value': 100, 'timestamp': datetime.now() - timedelta(hours=i)}
            for i in range(24, 0, -1)
        ]
        
        # Add some anomalous values
        self.historical_data.extend([
            {'value': 150, 'timestamp': datetime.now() - timedelta(hours=2)},  # High
            {'value': 50, 'timestamp': datetime.now() - timedelta(hours=1)}    # Low
        ])
    
    def test_statistical_anomaly_detection(self):
        """Test statistical anomaly detection methods."""
        values = [item['value'] for item in self.historical_data]
        
        # Test Z-score method
        z_anomalies = self.detector.detect_z_score_anomalies(values, threshold=2.0)
        self.assertTrue(len(z_anomalies) > 0)
        
        # Test IQR method
        iqr_anomalies = self.detector.detect_iqr_anomalies(values)
        self.assertTrue(len(iqr_anomalies) > 0)
    
    def test_isolation_forest_detection(self):
        """Test isolation forest anomaly detection."""
        data = np.array([[item['value']] for item in self.historical_data])
        
        anomalies = self.detector.detect_isolation_forest_anomalies(data)
        
        self.assertIsInstance(anomalies, list)
        # Should detect some anomalies
        self.assertTrue(len([a for a in anomalies if a == -1]) > 0)
    
    def test_time_series_anomaly_detection(self):
        """Test time series specific anomaly detection."""
        # Create time series data with trend and seasonal pattern
        timestamps = [datetime.now() - timedelta(hours=i) for i in range(168, 0, -1)]
        values = [100 + 10 * np.sin(2 * np.pi * i / 24) + np.random.normal(0, 2) 
                 for i in range(168)]
        
        # Add anomalies
        values[50] = 200  # Spike
        values[100] = 20  # Dip
        
        df = pd.DataFrame({'timestamp': timestamps, 'value': values})
        
        anomalies = self.detector.detect_time_series_anomalies(
            df, 
            timestamp_col='timestamp',
            value_col='value'
        )
        
        self.assertTrue(len(anomalies) > 0)
        # Should detect the injected anomalies
        self.assertIn(50, anomalies)
        self.assertIn(100, anomalies)


class DQManagementCommandsTestCase(TestCase):
    """Test management commands functionality."""
    
    def setUp(self):
        # Create test rule for commands to work with
        self.rule = DQRule.objects.create(
            name='test_command_rule',
            rule_type='row_count',
            database='test_db',
            table_name='test_table',
            is_active=True
        )
    
    @patch('builtins.open')
    @patch('yaml.safe_load')
    def test_load_dq_rules_command(self, mock_yaml_load, mock_open):
        """Test load_dq_rules management command."""
        mock_yaml_load.return_value = {
            'databases': {
                'test_db': {
                    'connection': 'postgresql://test:test@localhost/test',
                    'tables': {
                        'new_table': {
                            'rules': [
                                {
                                    'name': 'new_rule',
                                    'type': 'null_rate',
                                    'column': 'test_column',
                                    'params': {'max_null_rate': 0.05}
                                }
                            ]
                        }
                    }
                }
            }
        }
        
        call_command('load_dq_rules', 'test_manifest.yaml')
        
        # Verify rule was created
        new_rule = DQRule.objects.filter(name='new_rule').first()
        self.assertIsNotNone(new_rule)
        self.assertEqual(new_rule.rule_type, 'null_rate')
    
    @patch('dq.tasks.execute_dq_rule.delay')
    def test_run_dq_checks_command(self, mock_execute_delay):
        """Test run_dq_checks management command."""
        mock_execute_delay.return_value = Mock(id='task_123')
        
        call_command('run_dq_checks', '--async')
        
        # Verify task was scheduled
        mock_execute_delay.assert_called_with(self.rule.id)
    
    def test_export_dq_data_command(self, ):
        """Test export_dq_data management command."""
        # Create test data
        run = DQRun.objects.create(
            rule=self.rule,
            status='COMPLETED',
            records_checked=100,
            violations_found=5
        )
        
        DQViolation.objects.create(
            run=run,
            severity='MEDIUM',
            message='Test violation'
        )
        
        with patch('builtins.open', create=True) as mock_open:
            mock_file = MagicMock()
            mock_open.return_value.__enter__.return_value = mock_file
            
            call_command('export_dq_data', '--format', 'json', '--output', 'test.json')
            
            # Verify file was written
            mock_open.assert_called()
            mock_file.write.assert_called()


class DQIntegrationTestCase(TransactionTestCase):
    """Integration tests for complete DQ workflows."""
    
    def setUp(self):
        self.config = DQConfig.objects.create(
            key='test_db_connection',
            value='postgresql://test:test@localhost/test'
        )
    
    @patch('dq.checks.create_engine')
    @patch('dq.alerts.send_mail')
    def test_complete_dq_workflow(self, mock_send_mail, mock_create_engine):
        """Test complete DQ check workflow from rule to alert."""
        # Setup mock database
        mock_connection = MagicMock()
        mock_create_engine.return_value = mock_connection
        mock_connection.execute.return_value.fetchone.return_value = (50,)  # Low row count
        
        # Create rule that will fail
        rule = DQRule.objects.create(
            name='integration_test_rule',
            rule_type='row_count',
            database='test_db',
            table_name='test_table',
            params={'min_rows': 100},  # Will fail with 50 rows
            severity='HIGH',
            is_active=True
        )
        
        # Execute check
        from dq.tasks import execute_dq_rule
        result = execute_dq_rule.apply(args=[rule.id])
        
        # Verify check execution
        self.assertTrue(result.successful())
        
        # Verify run was created
        run = DQRun.objects.filter(rule=rule).first()
        self.assertIsNotNone(run)
        self.assertEqual(run.status, 'COMPLETED')
        
        # Verify violation was created
        violation = DQViolation.objects.filter(run=run).first()
        self.assertIsNotNone(violation)
        self.assertEqual(violation.severity, 'HIGH')
        
        # Verify alert was sent (mocked)
        mock_send_mail.assert_called()


# Pytest fixtures and parametrized tests
@pytest.fixture
def sample_dq_rule():
    """Fixture providing a sample DQ rule."""
    return DQRule.objects.create(
        name='pytest_rule',
        rule_type='null_rate',
        database='test_db',
        table_name='test_table',
        column_name='test_column',
        params={'max_null_rate': 0.05},
        severity='MEDIUM',
        is_active=True
    )


@pytest.mark.parametrize("rule_type,expected_checks", [
    ('row_count', ['min_rows', 'max_rows']),
    ('null_rate', ['max_null_rate']),
    ('uniqueness', ['min_uniqueness_rate']),
    ('range_check', ['min_value', 'max_value']),
])
def test_rule_parameter_validation(rule_type, expected_checks):
    """Parametrized test for rule parameter validation."""
    from dq.checks import DQCheckExecutor
    executor = DQCheckExecutor()
    
    # This would be expanded to test actual parameter validation logic
    assert rule_type in executor.get_supported_check_types()


@pytest.mark.django_db
def test_dq_metrics_recording(sample_dq_rule):
    """Test DQ metrics are properly recorded."""
    metric = DQMetric.objects.create(
        rule=sample_dq_rule,
        metric_name='check_duration',
        metric_value=15.5,
        labels={'database': 'test_db', 'table': 'test_table'}
    )
    
    assert metric.rule == sample_dq_rule
    assert metric.metric_value == 15.5
    assert 'database' in metric.labels


if __name__ == '__main__':
    # Run tests using Django's test runner
    import django
    from django.conf import settings
    from django.test.utils import get_runner
    
    django.setup()
    TestRunner = get_runner(settings)
    test_runner = TestRunner()
    failures = test_runner.run_tests(['dq.tests'])
    
    if failures:
        exit(1)