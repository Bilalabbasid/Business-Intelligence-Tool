"""
Database Connector for Data Ingestion
"""

import logging
import pandas as pd
import psycopg2
import pymongo
from typing import Dict, List, Any, Tuple, Optional
from datetime import datetime
import sqlalchemy
from sqlalchemy import create_engine, text
import mysql.connector

from .base import DatabaseConnector, ConnectorRegistry, DataExtractionError, ConfigurationError

logger = logging.getLogger(__name__)


class PostgreSQLConnector(DatabaseConnector):
    """
    Connector for PostgreSQL database ingestion.
    """
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.host = config.get('host', 'localhost')
        self.port = config.get('port', 5432)
        self.database = config.get('database')
        self.username = config.get('username')
        self.password = config.get('password')
        self.ssl_mode = config.get('ssl_mode', 'prefer')
        self.connection_timeout = config.get('connection_timeout', 30)
        self.query_timeout = config.get('query_timeout', 300)
        
        # Build connection string
        self.connection_string = self._build_connection_string()
    
    def get_connection(self):
        """Get database connection."""
        if not self.connection:
            try:
                self.connection = psycopg2.connect(
                    host=self.host,
                    port=self.port,
                    database=self.database,
                    user=self.username,
                    password=self.password,
                    sslmode=self.ssl_mode,
                    connect_timeout=self.connection_timeout
                )
                self.connection.set_session(autocommit=True)
            except Exception as e:
                raise DataExtractionError(f"Failed to connect to PostgreSQL: {str(e)}")
        
        return self.connection
    
    def _build_connection_string(self) -> str:
        """Build SQLAlchemy connection string."""
        return (f"postgresql://{self.username}:{self.password}@"
                f"{self.host}:{self.port}/{self.database}")
    
    def extract(self, query_params: Dict[str, Any] = None) -> List[Dict[str, Any]]:
        """
        Extract data using SQL query.
        
        Args:
            query_params: Should contain 'query' or 'table' with optional filters
            
        Returns:
            List of records as dictionaries
        """
        if not query_params:
            raise DataExtractionError("No query parameters provided")
        
        query = query_params.get('query')
        table = query_params.get('table')
        
        if not query and not table:
            raise DataExtractionError("Either 'query' or 'table' must be provided")
        
        try:
            self.rate_limit_check()
            
            if query:
                data = self.execute_query(query, query_params.get('params', {}))
            else:
                data = self._extract_from_table(table, query_params)
            
            self.log_activity('extract', {
                'query': query or f"SELECT * FROM {table}",
                'records_extracted': len(data),
                'params': query_params.get('params', {})
            })
            
            return data
            
        except Exception as e:
            logger.error(f"Error extracting from PostgreSQL: {e}")
            raise DataExtractionError(f"PostgreSQL extraction failed: {str(e)}")
    
    def execute_query(self, query: str, params: Dict[str, Any] = None) -> List[Dict[str, Any]]:
        """
        Execute SQL query and return results.
        
        Args:
            query: SQL query string
            params: Query parameters
            
        Returns:
            List of records as dictionaries
        """
        try:
            # Use pandas for efficient query execution
            engine = create_engine(self.connection_string)
            
            df = pd.read_sql(
                text(query),
                engine,
                params=params or {},
                chunksize=None
            )
            
            # Convert to list of dictionaries
            records = df.to_dict('records')
            
            # Add metadata
            for record in records:
                record['_db_source'] = self.name
                record['_db_extracted_at'] = datetime.now().isoformat()
            
            return records
            
        except Exception as e:
            raise DataExtractionError(f"Query execution failed: {str(e)}")
    
    def _extract_from_table(self, table: str, query_params: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Extract data from a specific table with filters.
        
        Args:
            table: Table name
            query_params: Query parameters including filters
            
        Returns:
            List of records
        """
        # Build SELECT query with filters
        columns = query_params.get('columns', ['*'])
        where_clause = query_params.get('where')
        order_by = query_params.get('order_by')
        limit = query_params.get('limit')
        offset = query_params.get('offset', 0)
        
        # Build query
        if isinstance(columns, list):
            columns_str = ', '.join(columns)
        else:
            columns_str = str(columns)
        
        query = f"SELECT {columns_str} FROM {table}"
        
        if where_clause:
            query += f" WHERE {where_clause}"
        
        if order_by:
            query += f" ORDER BY {order_by}"
        
        if limit:
            query += f" LIMIT {limit}"
        
        if offset:
            query += f" OFFSET {offset}"
        
        return self.execute_query(query, query_params.get('params', {}))
    
    def validate_config(self) -> Tuple[bool, List[str]]:
        """Validate connector configuration."""
        errors = []
        
        if not self.host:
            errors.append("host is required")
        
        if not isinstance(self.port, int) or not (1 <= self.port <= 65535):
            errors.append("port must be a valid integer between 1 and 65535")
        
        if not self.database:
            errors.append("database is required")
        
        if not self.username:
            errors.append("username is required")
        
        if not self.password:
            errors.append("password is required")
        
        if self.connection_timeout <= 0:
            errors.append("connection_timeout must be positive")
        
        if self.query_timeout <= 0:
            errors.append("query_timeout must be positive")
        
        return len(errors) == 0, errors
    
    def health_check(self, config: Dict[str, Any] = None) -> Dict[str, Any]:
        """Check database connectivity."""
        start_time = datetime.now()
        
        try:
            # Test connection
            test_connection = psycopg2.connect(
                host=self.host,
                port=self.port,
                database=self.database,
                user=self.username,
                password=self.password,
                sslmode=self.ssl_mode,
                connect_timeout=self.connection_timeout
            )
            
            # Test query
            cursor = test_connection.cursor()
            cursor.execute("SELECT 1")
            result = cursor.fetchone()
            
            cursor.close()
            test_connection.close()
            
            response_time = (datetime.now() - start_time).total_seconds() * 1000
            
            return {
                'healthy': True,
                'response_time': response_time,
                'error': None,
                'timestamp': start_time.isoformat(),
                'connector_type': 'postgresql',
                'test_result': result[0] if result else None
            }
            
        except Exception as e:
            response_time = (datetime.now() - start_time).total_seconds() * 1000
            return {
                'healthy': False,
                'response_time': response_time,
                'error': str(e),
                'timestamp': start_time.isoformat(),
                'connector_type': 'postgresql'
            }


class MySQLConnector(DatabaseConnector):
    """
    Connector for MySQL database ingestion.
    """
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.host = config.get('host', 'localhost')
        self.port = config.get('port', 3306)
        self.database = config.get('database')
        self.username = config.get('username')
        self.password = config.get('password')
        self.charset = config.get('charset', 'utf8mb4')
        self.connection_timeout = config.get('connection_timeout', 30)
    
    def get_connection(self):
        """Get database connection."""
        if not self.connection:
            try:
                self.connection = mysql.connector.connect(
                    host=self.host,
                    port=self.port,
                    database=self.database,
                    user=self.username,
                    password=self.password,
                    charset=self.charset,
                    connection_timeout=self.connection_timeout,
                    autocommit=True
                )
            except Exception as e:
                raise DataExtractionError(f"Failed to connect to MySQL: {str(e)}")
        
        return self.connection
    
    def extract(self, query_params: Dict[str, Any] = None) -> List[Dict[str, Any]]:
        """Extract data using SQL query."""
        if not query_params:
            raise DataExtractionError("No query parameters provided")
        
        query = query_params.get('query')
        table = query_params.get('table')
        
        if not query and not table:
            raise DataExtractionError("Either 'query' or 'table' must be provided")
        
        try:
            self.rate_limit_check()
            
            if query:
                data = self.execute_query(query, query_params.get('params', {}))
            else:
                data = self._extract_from_table(table, query_params)
            
            self.log_activity('extract', {
                'query': query or f"SELECT * FROM {table}",
                'records_extracted': len(data)
            })
            
            return data
            
        except Exception as e:
            logger.error(f"Error extracting from MySQL: {e}")
            raise DataExtractionError(f"MySQL extraction failed: {str(e)}")
    
    def execute_query(self, query: str, params: Dict[str, Any] = None) -> List[Dict[str, Any]]:
        """Execute SQL query and return results."""
        try:
            connection = self.get_connection()
            cursor = connection.cursor(dictionary=True)
            
            cursor.execute(query, params or {})
            results = cursor.fetchall()
            
            # Add metadata
            for record in results:
                record['_db_source'] = self.name
                record['_db_extracted_at'] = datetime.now().isoformat()
            
            cursor.close()
            return results
            
        except Exception as e:
            raise DataExtractionError(f"Query execution failed: {str(e)}")
    
    def _extract_from_table(self, table: str, query_params: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Extract data from a specific table with filters."""
        # Similar implementation to PostgreSQL but with MySQL syntax
        columns = query_params.get('columns', ['*'])
        where_clause = query_params.get('where')
        order_by = query_params.get('order_by')
        limit = query_params.get('limit')
        offset = query_params.get('offset', 0)
        
        if isinstance(columns, list):
            columns_str = ', '.join(columns)
        else:
            columns_str = str(columns)
        
        query = f"SELECT {columns_str} FROM {table}"
        
        if where_clause:
            query += f" WHERE {where_clause}"
        
        if order_by:
            query += f" ORDER BY {order_by}"
        
        if limit:
            query += f" LIMIT {limit}"
            if offset:
                query += f" OFFSET {offset}"
        
        return self.execute_query(query, query_params.get('params', {}))
    
    def validate_config(self) -> Tuple[bool, List[str]]:
        """Validate connector configuration."""
        errors = []
        
        if not self.host:
            errors.append("host is required")
        
        if not isinstance(self.port, int) or not (1 <= self.port <= 65535):
            errors.append("port must be a valid integer between 1 and 65535")
        
        if not self.database:
            errors.append("database is required")
        
        if not self.username:
            errors.append("username is required")
        
        if not self.password:
            errors.append("password is required")
        
        return len(errors) == 0, errors
    
    def health_check(self, config: Dict[str, Any] = None) -> Dict[str, Any]:
        """Check database connectivity."""
        start_time = datetime.now()
        
        try:
            test_connection = mysql.connector.connect(
                host=self.host,
                port=self.port,
                database=self.database,
                user=self.username,
                password=self.password,
                connection_timeout=self.connection_timeout
            )
            
            cursor = test_connection.cursor()
            cursor.execute("SELECT 1")
            result = cursor.fetchone()
            
            cursor.close()
            test_connection.close()
            
            response_time = (datetime.now() - start_time).total_seconds() * 1000
            
            return {
                'healthy': True,
                'response_time': response_time,
                'error': None,
                'timestamp': start_time.isoformat(),
                'connector_type': 'mysql',
                'test_result': result[0] if result else None
            }
            
        except Exception as e:
            response_time = (datetime.now() - start_time).total_seconds() * 1000
            return {
                'healthy': False,
                'response_time': response_time,
                'error': str(e),
                'timestamp': start_time.isoformat(),
                'connector_type': 'mysql'
            }


class MongoDBConnector(DatabaseConnector):
    """
    Connector for MongoDB data ingestion.
    """
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.host = config.get('host', 'localhost')
        self.port = config.get('port', 27017)
        self.database = config.get('database')
        self.username = config.get('username')
        self.password = config.get('password')
        self.auth_source = config.get('auth_source', 'admin')
        self.connection_timeout = config.get('connection_timeout', 30)
    
    def get_connection(self):
        """Get MongoDB connection."""
        if not self.connection:
            try:
                if self.username and self.password:
                    connection_string = (f"mongodb://{self.username}:{self.password}@"
                                       f"{self.host}:{self.port}/{self.database}"
                                       f"?authSource={self.auth_source}")
                else:
                    connection_string = f"mongodb://{self.host}:{self.port}/{self.database}"
                
                self.connection = pymongo.MongoClient(
                    connection_string,
                    serverSelectionTimeoutMS=self.connection_timeout * 1000
                )
                
                # Test connection
                self.connection.admin.command('ping')
                
            except Exception as e:
                raise DataExtractionError(f"Failed to connect to MongoDB: {str(e)}")
        
        return self.connection
    
    def extract(self, query_params: Dict[str, Any] = None) -> List[Dict[str, Any]]:
        """Extract data from MongoDB collection."""
        if not query_params:
            raise DataExtractionError("No query parameters provided")
        
        collection_name = query_params.get('collection')
        if not collection_name:
            raise DataExtractionError("Collection name must be provided")
        
        try:
            self.rate_limit_check()
            
            client = self.get_connection()
            db = client[self.database]
            collection = db[collection_name]
            
            # Build query
            filter_query = query_params.get('filter', {})
            projection = query_params.get('projection')
            sort = query_params.get('sort')
            limit = query_params.get('limit')
            skip = query_params.get('skip', 0)
            
            # Execute query
            cursor = collection.find(filter_query, projection)
            
            if sort:
                cursor = cursor.sort(sort)
            
            if skip:
                cursor = cursor.skip(skip)
            
            if limit:
                cursor = cursor.limit(limit)
            
            # Convert to list
            results = list(cursor)
            
            # Convert ObjectIds to strings and add metadata
            for record in results:
                if '_id' in record:
                    record['_id'] = str(record['_id'])
                record['_mongo_source'] = self.name
                record['_mongo_extracted_at'] = datetime.now().isoformat()
            
            self.log_activity('extract', {
                'collection': collection_name,
                'filter': filter_query,
                'records_extracted': len(results)
            })
            
            return results
            
        except Exception as e:
            logger.error(f"Error extracting from MongoDB: {e}")
            raise DataExtractionError(f"MongoDB extraction failed: {str(e)}")
    
    def execute_query(self, query: str, params: Dict[str, Any] = None) -> List[Dict[str, Any]]:
        """MongoDB doesn't use SQL queries - use extract method instead."""
        raise NotImplementedError("MongoDB uses extract method with collection queries")
    
    def validate_config(self) -> Tuple[bool, List[str]]:
        """Validate connector configuration."""
        errors = []
        
        if not self.host:
            errors.append("host is required")
        
        if not isinstance(self.port, int) or not (1 <= self.port <= 65535):
            errors.append("port must be a valid integer between 1 and 65535")
        
        if not self.database:
            errors.append("database is required")
        
        return len(errors) == 0, errors
    
    def health_check(self, config: Dict[str, Any] = None) -> Dict[str, Any]:
        """Check MongoDB connectivity."""
        start_time = datetime.now()
        
        try:
            client = self.get_connection()
            
            # Test with ping command
            result = client.admin.command('ping')
            
            response_time = (datetime.now() - start_time).total_seconds() * 1000
            
            return {
                'healthy': True,
                'response_time': response_time,
                'error': None,
                'timestamp': start_time.isoformat(),
                'connector_type': 'mongodb',
                'ping_result': result
            }
            
        except Exception as e:
            response_time = (datetime.now() - start_time).total_seconds() * 1000
            return {
                'healthy': False,
                'response_time': response_time,
                'error': str(e),
                'timestamp': start_time.isoformat(),
                'connector_type': 'mongodb'
            }


# Register connectors
ConnectorRegistry.register('postgresql', PostgreSQLConnector)
ConnectorRegistry.register('postgres', PostgreSQLConnector)  # Alias
ConnectorRegistry.register('mysql', MySQLConnector)
ConnectorRegistry.register('mongodb', MongoDBConnector)
ConnectorRegistry.register('mongo', MongoDBConnector)  # Alias