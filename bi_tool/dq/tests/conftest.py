"""
Test configuration and fixtures for DQ system testing.
"""

import pytest
import os
import django
from django.conf import settings
from django.test.utils import get_runner
from unittest.mock import Mock, patch
import tempfile
from datetime import datetime, timedelta

# Configure Django for pytest
def pytest_configure():
    """Configure Django settings for pytest."""
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'bi_tool.settings')
    django.setup()


@pytest.fixture(scope='session')
def django_db_setup():
    """Setup test database."""
    from django.core.management import call_command
    call_command('migrate', '--run-syncdb', verbosity=0, interactive=False)


@pytest.fixture
def mock_database_connection():
    """Mock database connection for testing."""
    with patch('dq.checks.create_engine') as mock_engine:
        mock_connection = Mock()
        mock_engine.return_value = mock_connection
        yield mock_connection


@pytest.fixture
def sample_test_data():
    """Sample test data for DQ checks."""
    import pandas as pd
    return pd.DataFrame({
        'id': range(1, 101),
        'name': [f'User_{i}' if i % 10 != 0 else None for i in range(1, 101)],
        'email': [f'user{i}@test.com' for i in range(1, 101)],
        'age': [25 + (i % 50) for i in range(1, 101)],
        'created_at': [datetime.now() - timedelta(hours=i) for i in range(1, 101)],
        'score': [85.5 + (i % 30) - 15 for i in range(1, 101)]
    })


@pytest.fixture
def temp_yaml_file():
    """Create temporary YAML configuration file."""
    yaml_content = '''
databases:
  test_db:
    connection: "postgresql://test:test@localhost/test"
    tables:
      users:
        rules:
          - name: "users_completeness_check"
            type: "null_rate"
            column: "email"
            params:
              max_null_rate: 0.05
            severity: "HIGH"
          - name: "users_row_count_check"
            type: "row_count"
            params:
              min_rows: 100
              max_rows: 10000
            severity: "MEDIUM"
      products:
        rules:
          - name: "products_uniqueness_check"
            type: "uniqueness"
            column: "sku"
            params:
              min_uniqueness_rate: 0.99
            severity: "CRITICAL"
'''
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
        f.write(yaml_content)
        f.flush()
        yield f.name
    
    # Cleanup
    os.unlink(f.name)


@pytest.fixture
def mock_celery_task():
    """Mock Celery task for testing."""
    with patch('celery.current_app.send_task') as mock_task:
        mock_result = Mock()
        mock_result.id = 'test-task-id'
        mock_result.successful.return_value = True
        mock_task.return_value = mock_result
        yield mock_task


@pytest.fixture
def mock_alert_channels():
    """Mock alert channels for testing."""
    mocks = {}
    
    with patch('dq.alerts.send_mail') as mock_email:
        mock_email.return_value = True
        mocks['email'] = mock_email
        
        with patch('requests.post') as mock_post:
            mock_post.return_value.status_code = 200
            mocks['http'] = mock_post
            
            yield mocks


@pytest.fixture(scope='function')
def clean_db():
    """Ensure clean database state for each test."""
    from dq.models import DQRule, DQRun, DQViolation, DQMetric, DQConfig
    
    # Clean up before test
    DQViolation.objects.all().delete()
    DQRun.objects.all().delete()
    DQRule.objects.all().delete()
    DQMetric.objects.all().delete()
    DQConfig.objects.all().delete()
    
    yield
    
    # Clean up after test
    DQViolation.objects.all().delete()
    DQRun.objects.all().delete()
    DQRule.objects.all().delete()
    DQMetric.objects.all().delete()
    DQConfig.objects.all().delete()


@pytest.fixture
def anomaly_test_data():
    """Generate test data with known anomalies for anomaly detection testing."""
    import numpy as np
    
    # Normal data with some pattern
    np.random.seed(42)  # For reproducible tests
    normal_data = np.random.normal(100, 10, 100)
    
    # Add known anomalies
    anomalous_data = normal_data.copy()
    anomalous_data[20] = 200  # High anomaly
    anomalous_data[50] = 20   # Low anomaly
    anomalous_data[80] = 180  # Another high anomaly
    
    return {
        'normal': normal_data,
        'with_anomalies': anomalous_data,
        'known_anomaly_indices': [20, 50, 80]
    }


@pytest.fixture
def performance_test_data():
    """Generate large dataset for performance testing."""
    import pandas as pd
    import numpy as np
    
    n_rows = 10000
    return pd.DataFrame({
        'id': range(n_rows),
        'category': np.random.choice(['A', 'B', 'C', 'D'], n_rows),
        'value': np.random.normal(100, 20, n_rows),
        'is_active': np.random.choice([True, False], n_rows),
        'created_at': pd.date_range('2023-01-01', periods=n_rows, freq='H')
    })


# Pytest markers for different test categories
pytest.mark.unit = pytest.mark.unit
pytest.mark.integration = pytest.mark.integration
pytest.mark.slow = pytest.mark.slow
pytest.mark.celery = pytest.mark.celery