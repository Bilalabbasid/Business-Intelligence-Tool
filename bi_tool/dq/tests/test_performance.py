"""
Performance and load tests for DQ system.
"""

import pytest
import time
import concurrent.futures
from unittest.mock import Mock, patch
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

from dq.models import DQRule, DQRun, DQViolation
from dq.checks import DQCheckExecutor
from dq.tasks import execute_dq_rule, run_scheduled_checks


class TestDQPerformance:
    """Performance tests for DQ system components."""
    
    @pytest.mark.slow
    @pytest.mark.django_db
    def test_check_execution_performance(self, performance_test_data):
        """Test performance of DQ check execution on large datasets."""
        executor = DQCheckExecutor()
        
        # Mock database connection to return performance test data size
        with patch('dq.checks.create_engine') as mock_engine:
            mock_connection = Mock()
            mock_engine.return_value = mock_connection
            
            # Simulate large dataset query results
            mock_connection.execute.return_value.fetchone.return_value = (len(performance_test_data),)
            
            rule = DQRule(
                rule_type='row_count',
                database='test_db',
                table_name='large_table',
                params={'min_rows': 5000, 'max_rows': 50000}
            )
            
            # Measure execution time
            start_time = time.time()
            result = executor.execute_check(rule)
            execution_time = time.time() - start_time
            
            # Performance assertions
            assert execution_time < 5.0, f"Check execution took {execution_time}s, expected < 5s"
            assert result['passed'] is True
            assert result['records_checked'] == len(performance_test_data)
    
    @pytest.mark.slow
    @pytest.mark.django_db
    def test_bulk_rule_execution_performance(self):
        """Test performance of bulk rule execution."""
        # Create multiple rules
        rules = []
        for i in range(50):
            rule = DQRule.objects.create(
                name=f'performance_rule_{i}',
                rule_type='row_count',
                database='test_db',
                table_name=f'table_{i}',
                params={'min_rows': 100},
                is_active=True
            )
            rules.append(rule)
        
        with patch('dq.checks.create_engine') as mock_engine:
            mock_connection = Mock()
            mock_engine.return_value = mock_connection
            mock_connection.execute.return_value.fetchone.return_value = (150,)
            
            # Measure bulk execution time
            start_time = time.time()
            
            # Execute all rules
            for rule in rules:
                execute_dq_rule.apply(args=[rule.id])
            
            execution_time = time.time() - start_time
            
            # Performance assertions
            assert execution_time < 30.0, f"Bulk execution took {execution_time}s, expected < 30s"
            
            # Verify all runs were created
            runs_count = DQRun.objects.count()
            assert runs_count == 50
    
    @pytest.mark.slow
    def test_concurrent_check_execution(self):
        """Test concurrent execution of DQ checks."""
        num_concurrent_checks = 10
        
        # Create rules for concurrent execution
        rules = []
        for i in range(num_concurrent_checks):
            rule = DQRule.objects.create(
                name=f'concurrent_rule_{i}',
                rule_type='null_rate',
                database='test_db',
                table_name=f'table_{i}',
                column_name='test_column',
                params={'max_null_rate': 0.05},
                is_active=True
            )
            rules.append(rule)
        
        def execute_single_rule(rule_id):
            """Execute a single rule and return execution time."""
            start_time = time.time()
            
            with patch('dq.checks.create_engine') as mock_engine:
                mock_connection = Mock()
                mock_engine.return_value = mock_connection
                # Mock responses: total rows, null rows
                mock_connection.execute.side_effect = [
                    Mock(fetchone=Mock(return_value=(1000,))),  # total
                    Mock(fetchone=Mock(return_value=(25,)))     # nulls
                ]
                
                execute_dq_rule.apply(args=[rule_id])
            
            return time.time() - start_time
        
        # Execute rules concurrently
        start_time = time.time()
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            futures = [
                executor.submit(execute_single_rule, rule.id) 
                for rule in rules
            ]
            
            execution_times = [future.result() for future in futures]
        
        total_time = time.time() - start_time
        avg_execution_time = sum(execution_times) / len(execution_times)
        
        # Performance assertions
        assert total_time < 20.0, f"Concurrent execution took {total_time}s, expected < 20s"
        assert avg_execution_time < 3.0, f"Average execution time {avg_execution_time}s, expected < 3s"
    
    @pytest.mark.slow
    def test_anomaly_detection_performance(self, anomaly_test_data):
        """Test performance of anomaly detection algorithms."""
        from dq.anomaly_detection import DQAnomalyDetector
        
        detector = DQAnomalyDetector()
        large_dataset = np.random.normal(100, 15, 10000)  # 10k data points
        
        # Test Z-score performance
        start_time = time.time()
        z_anomalies = detector.detect_z_score_anomalies(large_dataset, threshold=2.5)
        z_time = time.time() - start_time
        
        # Test IQR performance
        start_time = time.time()
        iqr_anomalies = detector.detect_iqr_anomalies(large_dataset)
        iqr_time = time.time() - start_time
        
        # Test Isolation Forest performance
        start_time = time.time()
        if_anomalies = detector.detect_isolation_forest_anomalies(
            large_dataset.reshape(-1, 1)
        )
        if_time = time.time() - start_time
        
        # Performance assertions
        assert z_time < 1.0, f"Z-score detection took {z_time}s, expected < 1s"
        assert iqr_time < 1.0, f"IQR detection took {iqr_time}s, expected < 1s"
        assert if_time < 3.0, f"Isolation Forest took {if_time}s, expected < 3s"
        
        # Verify results are reasonable
        assert isinstance(z_anomalies, list)
        assert isinstance(iqr_anomalies, list)
        assert len(if_anomalies) == len(large_dataset)


class TestDQLoadTesting:
    """Load testing scenarios for DQ system."""
    
    @pytest.mark.slow
    @pytest.mark.django_db
    def test_high_volume_violations_handling(self):
        """Test system behavior under high violation volume."""
        # Create a rule that will generate many violations
        rule = DQRule.objects.create(
            name='high_volume_test_rule',
            rule_type='row_count',
            database='test_db',
            table_name='test_table',
            params={'min_rows': 1000000},  # Very high threshold
            severity='HIGH',
            is_active=True
        )
        
        run = DQRun.objects.create(
            rule=rule,
            status='RUNNING',
            records_checked=0
        )
        
        # Generate many violations
        start_time = time.time()
        violations = []
        
        for i in range(1000):  # 1000 violations
            violations.append(DQViolation(
                run=run,
                severity='HIGH',
                message=f'Test violation {i}',
                record_id=f'record_{i}'
            ))
        
        # Bulk create violations
        DQViolation.objects.bulk_create(violations, batch_size=100)
        
        creation_time = time.time() - start_time
        
        # Verify performance and data integrity
        assert creation_time < 10.0, f"Violation creation took {creation_time}s, expected < 10s"
        
        violation_count = DQViolation.objects.filter(run=run).count()
        assert violation_count == 1000
    
    @pytest.mark.slow
    @pytest.mark.django_db
    def test_rule_registry_scale(self):
        """Test rule registry performance with large number of rules."""
        from dq.rules import DQRuleRegistry
        
        registry = DQRuleRegistry()
        
        # Create large rules configuration
        large_config = {
            'databases': {}
        }
        
        # Generate 100 databases with 50 tables each, 5 rules per table
        for db_id in range(10):  # 10 databases
            db_name = f'test_db_{db_id}'
            large_config['databases'][db_name] = {
                'connection': f'postgresql://test:test@localhost/{db_name}',
                'tables': {}
            }
            
            for table_id in range(20):  # 20 tables per database
                table_name = f'table_{table_id}'
                large_config['databases'][db_name]['tables'][table_name] = {
                    'rules': []
                }
                
                for rule_id in range(3):  # 3 rules per table
                    large_config['databases'][db_name]['tables'][table_name]['rules'].append({
                        'name': f'{db_name}_{table_name}_rule_{rule_id}',
                        'type': 'row_count',
                        'params': {'min_rows': 100}
                    })
        
        # Measure registration time
        start_time = time.time()
        registry.register_rules_from_config(large_config)
        registration_time = time.time() - start_time
        
        # Measure retrieval time
        start_time = time.time()
        all_rules = registry.get_all_rules()
        retrieval_time = time.time() - start_time
        
        # Performance assertions
        expected_rules = 10 * 20 * 3  # 600 rules
        assert len(all_rules) == expected_rules
        assert registration_time < 5.0, f"Rule registration took {registration_time}s, expected < 5s"
        assert retrieval_time < 1.0, f"Rule retrieval took {retrieval_time}s, expected < 1s"
    
    @pytest.mark.slow
    def test_memory_usage_under_load(self):
        """Test memory usage during intensive operations."""
        import psutil
        import gc
        
        process = psutil.Process()
        initial_memory = process.memory_info().rss / 1024 / 1024  # MB
        
        # Perform memory-intensive operations
        large_datasets = []
        for i in range(10):
            # Create large pandas DataFrames
            df = pd.DataFrame({
                'id': range(10000),
                'data': np.random.random(10000),
                'category': np.random.choice(['A', 'B', 'C'], 10000)
            })
            large_datasets.append(df)
        
        peak_memory = process.memory_info().rss / 1024 / 1024  # MB
        
        # Clean up
        del large_datasets
        gc.collect()
        
        final_memory = process.memory_info().rss / 1024 / 1024  # MB
        
        # Memory usage assertions
        memory_increase = peak_memory - initial_memory
        memory_leak = final_memory - initial_memory
        
        assert memory_increase > 0, "Memory should increase during intensive operations"
        assert memory_leak < 50, f"Memory leak of {memory_leak}MB detected, expected < 50MB"
    
    @pytest.mark.slow
    @pytest.mark.django_db
    def test_database_connection_pooling(self):
        """Test database connection handling under load."""
        # Simulate many concurrent database operations
        def simulate_db_operation():
            """Simulate a database-intensive DQ check."""
            with patch('dq.checks.create_engine') as mock_engine:
                mock_connection = Mock()
                mock_engine.return_value = mock_connection
                mock_connection.execute.return_value.fetchone.return_value = (100,)
                
                executor = DQCheckExecutor()
                rule = DQRule(
                    rule_type='row_count',
                    database='test_db',
                    table_name='test_table',
                    params={'min_rows': 50}
                )
                
                return executor.execute_check(rule)
        
        # Execute many operations concurrently
        start_time = time.time()
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=20) as executor:
            futures = [
                executor.submit(simulate_db_operation) 
                for _ in range(100)
            ]
            
            results = [future.result() for future in futures]
        
        execution_time = time.time() - start_time
        
        # Verify all operations completed successfully
        assert len(results) == 100
        assert all(result['passed'] for result in results)
        assert execution_time < 15.0, f"Concurrent DB operations took {execution_time}s, expected < 15s"
    
    @pytest.mark.slow
    def test_alert_system_under_load(self):
        """Test alert system performance under high load."""
        from dq.alerts import DQAlertManager
        
        alert_manager = DQAlertManager()
        
        # Create many violations to trigger alerts
        rule = DQRule.objects.create(
            name='load_test_rule',
            rule_type='row_count',
            database='test_db',
            table_name='test_table',
            severity='HIGH'
        )
        
        run = DQRun.objects.create(
            rule=rule,
            status='COMPLETED'
        )
        
        violations = []
        for i in range(50):  # 50 violations
            violations.append(DQViolation.objects.create(
                run=run,
                severity='HIGH',
                message=f'Load test violation {i}'
            ))
        
        # Mock alert channels
        with patch('dq.alerts.send_mail') as mock_email, \
             patch('requests.post') as mock_post:
            
            mock_email.return_value = True
            mock_post.return_value.status_code = 200
            
            # Measure alert processing time
            start_time = time.time()
            
            for violation in violations:
                alert_manager.send_email_alert(violation, ['test@example.com'])
            
            alert_time = time.time() - start_time
            
            # Performance assertions
            assert alert_time < 30.0, f"Alert processing took {alert_time}s, expected < 30s"
            assert mock_email.call_count == 50
    
    @pytest.mark.slow
    def test_metrics_collection_performance(self):
        """Test performance of metrics collection and storage."""
        from dq.models import DQMetric
        
        # Generate many metrics
        start_time = time.time()
        
        rule = DQRule.objects.create(
            name='metrics_test_rule',
            rule_type='row_count',
            database='test_db',
            table_name='test_table'
        )
        
        metrics = []
        for i in range(1000):  # 1000 metrics
            metrics.append(DQMetric(
                rule=rule,
                metric_name='test_metric',
                metric_value=i * 1.5,
                labels={'batch': str(i // 100)},
                recorded_at=datetime.now() - timedelta(minutes=i)
            ))
        
        # Bulk create metrics
        DQMetric.objects.bulk_create(metrics, batch_size=100)
        
        creation_time = time.time() - start_time
        
        # Query metrics
        start_time = time.time()
        recent_metrics = DQMetric.objects.filter(
            recorded_at__gte=datetime.now() - timedelta(hours=1)
        ).count()
        query_time = time.time() - start_time
        
        # Performance assertions
        assert creation_time < 5.0, f"Metrics creation took {creation_time}s, expected < 5s"
        assert query_time < 1.0, f"Metrics query took {query_time}s, expected < 1s"
        assert DQMetric.objects.count() == 1000


if __name__ == '__main__':
    # Run performance tests
    pytest.main([
        __file__,
        '-v',
        '-m', 'slow',
        '--tb=short'
    ])