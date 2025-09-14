"""
Unit tests for DSAR Handler
"""
import unittest
from unittest.mock import Mock, patch, MagicMock
import json
import os
import tempfile
import shutil

# Import the DSAR handler (assumes ops directory is in Python path)
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from dsar import DSARHandler


class TestDSARHandler(unittest.TestCase):
    
    def setUp(self):
        """Set up test fixtures with temporary directory."""
        self.test_dir = tempfile.mkdtemp()
        self.handler = DSARHandler(output_dir=self.test_dir)
        
    def tearDown(self):
        """Clean up test fixtures."""
        shutil.rmtree(self.test_dir)
    
    @patch('dsar.MongoClient')
    def test_find_pii_mongo_success(self, mock_mongo_client):
        """Test successful MongoDB PII discovery."""
        # Mock MongoDB client and collection
        mock_collection = Mock()
        mock_collection.find.return_value = [
            {'_id': '123', 'email': 'test@example.com', 'name': 'John Doe'},
            {'_id': '456', 'email': 'test@example.com', 'phone': '555-0123'}
        ]
        
        mock_db = Mock()
        mock_db.__getitem__.return_value = mock_collection
        
        mock_client = Mock()
        mock_client.__getitem__.return_value = mock_db
        mock_mongo_client.return_value = mock_client
        
        self.handler.mongo_client = mock_client
        
        # Test the method
        results = self.handler.find_pii_mongo('testdb', 'users', 'email', 'test@example.com')
        
        self.assertEqual(len(results), 2)
        self.assertEqual(results[0]['email'], 'test@example.com')
        mock_collection.find.assert_called_once_with({'email': 'test@example.com'})
    
    @patch('dsar.psycopg2')
    def test_find_pii_postgres_success(self, mock_psycopg2):
        """Test successful PostgreSQL PII discovery."""
        # Mock PostgreSQL connection and cursor
        mock_cursor = Mock()
        mock_cursor.fetchall.return_value = [
            {'id': 1, 'email': 'test@example.com', 'name': 'John Doe'},
            {'id': 2, 'email': 'test@example.com', 'phone': '555-0123'}
        ]
        
        mock_conn = Mock()
        mock_conn.cursor.return_value.__enter__.return_value = mock_cursor
        
        self.handler.pg_conn = mock_conn
        
        # Test the method
        results = self.handler.find_pii_postgres('public.users', 'email', 'test@example.com')
        
        self.assertEqual(len(results), 2)
        mock_cursor.execute.assert_called_once_with(
            "SELECT * FROM public.users WHERE email = %s", 
            ('test@example.com',)
        )
    
    def test_anonymize_record(self):
        """Test record anonymization."""
        record = {
            'id': 123,
            'name': 'John Doe',
            'email': 'john@example.com',
            'phone': '555-0123',
            'address': '123 Main St'
        }
        pii_fields = ['email', 'phone', 'address']
        
        anonymized = self.handler.anonymize_record(record.copy(), pii_fields)
        
        self.assertEqual(anonymized['id'], 123)
        self.assertEqual(anonymized['name'], 'John Doe')
        self.assertIsNone(anonymized['email'])
        self.assertIsNone(anonymized['phone'])
        self.assertIsNone(anonymized['address'])
    
    def test_export_data(self):
        """Test data export to JSON file."""
        test_data = [
            {'id': 1, 'name': 'John'},
            {'id': 2, 'name': 'Jane'}
        ]
        filename = 'test_export.json'
        
        result_path = self.handler.export_data(test_data, filename)
        
        # Verify file was created
        expected_path = os.path.join(self.test_dir, filename)
        self.assertEqual(result_path, expected_path)
        self.assertTrue(os.path.exists(expected_path))
        
        # Verify content
        with open(expected_path, 'r') as f:
            loaded_data = json.load(f)
        
        self.assertEqual(loaded_data, test_data)
    
    @patch('dsar.psycopg2')
    @patch('dsar.MongoClient')
    def test_handle_request_full_workflow(self, mock_mongo_client, mock_psycopg2):
        """Test complete DSAR request handling workflow."""
        # Mock MongoDB
        mock_mongo_collection = Mock()
        mock_mongo_collection.find.return_value = [
            {'_id': '123', 'email': 'test@example.com', 'name': 'John'}
        ]
        mock_mongo_db = Mock()
        mock_mongo_db.__getitem__.return_value = mock_mongo_collection
        mock_mongo_client_instance = Mock()
        mock_mongo_client_instance.__getitem__.return_value = mock_mongo_db
        mock_mongo_client.return_value = mock_mongo_client_instance
        
        # Mock PostgreSQL
        mock_pg_cursor = Mock()
        mock_pg_cursor.fetchall.return_value = [
            {'id': 1, 'email': 'test@example.com', 'name': 'John'}
        ]
        mock_pg_conn = Mock()
        mock_pg_conn.cursor.return_value.__enter__.return_value = mock_pg_cursor
        
        # Set up handler
        self.handler.mongo_client = mock_mongo_client_instance
        self.handler.pg_conn = mock_pg_conn
        
        # Execute request
        result_path = self.handler.handle_request(email='test@example.com', anonymize=False)
        
        # Verify result
        self.assertTrue(os.path.exists(result_path))
        
        # Load and verify report
        with open(result_path, 'r') as f:
            report = json.load(f)
        
        self.assertEqual(report['identifier'], 'test@example.com')
        self.assertFalse(report['anonymize'])
        self.assertIn('mongo', report['results'])
        self.assertIn('postgres', report['results'])
    
    def test_handle_request_no_databases(self):
        """Test DSAR request when no databases are configured."""
        # Handler with no database connections
        handler_no_db = DSARHandler(output_dir=self.test_dir)
        handler_no_db.mongo_client = None
        handler_no_db.pg_conn = None
        
        result_path = handler_no_db.handle_request(email='test@example.com')
        
        # Should still create a report file
        self.assertTrue(os.path.exists(result_path))
        
        with open(result_path, 'r') as f:
            report = json.load(f)
        
        self.assertEqual(report['identifier'], 'test@example.com')
        self.assertEqual(report['results'], {})


class TestDSARHandlerIntegration(unittest.TestCase):
    """Integration tests that would run against real databases in test environment."""
    
    def setUp(self):
        """Set up integration test environment."""
        self.test_dir = tempfile.mkdtemp()
        
    def tearDown(self):
        """Clean up integration test environment."""
        shutil.rmtree(self.test_dir)
    
    @unittest.skip("Requires test database setup")
    def test_real_mongodb_integration(self):
        """Integration test with real MongoDB (skipped by default)."""
        # This would test against a real test MongoDB instance
        # Requires TEST_MONGO_URI environment variable
        test_uri = os.getenv('TEST_MONGO_URI')
        if not test_uri:
            self.skipTest("TEST_MONGO_URI not set")
        
        handler = DSARHandler(mongo_uri=test_uri, output_dir=self.test_dir)
        # ... actual integration test code
    
    @unittest.skip("Requires test database setup")
    def test_real_postgres_integration(self):
        """Integration test with real PostgreSQL (skipped by default)."""
        # This would test against a real test PostgreSQL instance
        # Requires TEST_POSTGRES_URI environment variable
        test_uri = os.getenv('TEST_POSTGRES_URI')
        if not test_uri:
            self.skipTest("TEST_POSTGRES_URI not set")
        
        handler = DSARHandler(postgres_uri=test_uri, output_dir=self.test_dir)
        # ... actual integration test code


if __name__ == '__main__':
    unittest.main()