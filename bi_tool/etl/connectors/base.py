"""
Base Connector Classes and Registry for Data Ingestion
"""

import abc
import time
import logging
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime

logger = logging.getLogger(__name__)


class BaseConnector(abc.ABC):
    """
    Abstract base class for all data connectors.
    """
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.name = config.get('name', self.__class__.__name__)
        self.rate_limit = config.get('rate_limit', 60)  # requests per minute
        self.last_request_time = 0
        
    @abc.abstractmethod
    def extract(self, query_params: Dict[str, Any] = None) -> List[Dict[str, Any]]:
        """
        Extract data from the source.
        
        Args:
            query_params: Optional query parameters for filtering/pagination
            
        Returns:
            List of records as dictionaries
        """
        pass
    
    @abc.abstractmethod
    def validate_config(self) -> Tuple[bool, List[str]]:
        """
        Validate connector configuration.
        
        Returns:
            Tuple of (is_valid, list_of_errors)
        """
        pass
    
    @abc.abstractmethod
    def health_check(self, config: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Check if the data source is accessible and healthy.
        
        Args:
            config: Optional config override for health check
            
        Returns:
            Dict with health status information
        """
        pass
    
    def rate_limit_check(self):
        """
        Enforce rate limiting between requests.
        """
        if self.rate_limit <= 0:
            return
            
        time_since_last = time.time() - self.last_request_time
        min_interval = 60.0 / self.rate_limit  # seconds between requests
        
        if time_since_last < min_interval:
            sleep_time = min_interval - time_since_last
            logger.debug(f"Rate limiting: sleeping {sleep_time:.2f}s")
            time.sleep(sleep_time)
        
        self.last_request_time = time.time()
    
    def log_activity(self, activity_type: str, details: Dict[str, Any]):
        """
        Log connector activity for monitoring and debugging.
        """
        logger.info(f"{self.name} - {activity_type}: {details}")
    
    def get_incremental_checkpoint(self, checkpoint_config: Dict[str, Any]) -> Any:
        """
        Get the last checkpoint for incremental data loading.
        
        Args:
            checkpoint_config: Configuration for checkpoint retrieval
            
        Returns:
            Checkpoint value (timestamp, ID, etc.)
        """
        # Default implementation - subclasses can override
        from ..models import Checkpoint
        
        try:
            checkpoint = Checkpoint.objects.get(
                source=self.name,
                checkpoint_type=checkpoint_config.get('type', 'timestamp')
            )
            return checkpoint.checkpoint_value
        except Checkpoint.DoesNotExist:
            # Return default checkpoint if none exists
            return checkpoint_config.get('default_checkpoint')
    
    def update_checkpoint(self, checkpoint_value: Any, checkpoint_config: Dict[str, Any]):
        """
        Update the checkpoint after successful data extraction.
        
        Args:
            checkpoint_value: New checkpoint value
            checkpoint_config: Checkpoint configuration
        """
        from ..models import Checkpoint
        
        checkpoint, created = Checkpoint.objects.update_or_create(
            source=self.name,
            checkpoint_type=checkpoint_config.get('type', 'timestamp'),
            defaults={
                'checkpoint_value': str(checkpoint_value),
                'checkpoint_data': checkpoint_config
            }
        )
        
        action = "Created" if created else "Updated"
        logger.info(f"{action} checkpoint for {self.name}: {checkpoint_value}")


class DatabaseConnector(BaseConnector):
    """
    Base class for database connectors (MySQL, PostgreSQL, etc.).
    """
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.connection = None
        self.connection_pool = None
    
    @abc.abstractmethod
    def get_connection(self):
        """Get database connection."""
        pass
    
    @abc.abstractmethod
    def execute_query(self, query: str, params: Dict[str, Any] = None) -> List[Dict[str, Any]]:
        """Execute SQL query and return results."""
        pass
    
    def close_connection(self):
        """Close database connection."""
        if self.connection:
            self.connection.close()
            self.connection = None


class APIConnector(BaseConnector):
    """
    Base class for REST API connectors.
    """
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.session = None
        self.auth_token = None
        self.auth_expires = None
    
    @abc.abstractmethod
    def authenticate(self) -> bool:
        """Authenticate with the API."""
        pass
    
    @abc.abstractmethod
    def make_request(self, endpoint: str, params: Dict[str, Any] = None, 
                    method: str = 'GET') -> Dict[str, Any]:
        """Make HTTP request to API."""
        pass
    
    def is_authenticated(self) -> bool:
        """Check if current authentication is valid."""
        if not self.auth_token:
            return False
        
        if self.auth_expires and datetime.now() >= self.auth_expires:
            return False
        
        return True
    
    def ensure_authenticated(self):
        """Ensure we have valid authentication."""
        if not self.is_authenticated():
            if not self.authenticate():
                raise Exception(f"Authentication failed for {self.name}")


class FileConnector(BaseConnector):
    """
    Base class for file-based connectors (CSV, Excel, JSON, etc.).
    """
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.supported_formats = ['csv', 'xlsx', 'xls', 'json', 'xml']
    
    @abc.abstractmethod
    def read_file(self, file_path: str, **kwargs) -> List[Dict[str, Any]]:
        """Read data from file."""
        pass
    
    def detect_file_format(self, file_path: str) -> str:
        """Detect file format from extension."""
        extension = file_path.lower().split('.')[-1]
        if extension in self.supported_formats:
            return extension
        raise ValueError(f"Unsupported file format: {extension}")
    
    def validate_file(self, file_path: str) -> Tuple[bool, List[str]]:
        """Validate file before processing."""
        import os
        
        errors = []
        
        # Check if file exists
        if not os.path.exists(file_path):
            errors.append(f"File does not exist: {file_path}")
            return False, errors
        
        # Check file size
        file_size = os.path.getsize(file_path)
        max_size = self.config.get('max_file_size', 100 * 1024 * 1024)  # 100MB default
        
        if file_size > max_size:
            errors.append(f"File too large: {file_size} bytes (max: {max_size})")
        
        # Check file format
        try:
            self.detect_file_format(file_path)
        except ValueError as e:
            errors.append(str(e))
        
        return len(errors) == 0, errors


class ConnectorRegistry:
    """
    Registry for managing data connectors.
    """
    
    _connectors = {}
    
    @classmethod
    def register(cls, connector_type: str, connector_class):
        """
        Register a connector class.
        
        Args:
            connector_type: Type identifier for the connector
            connector_class: Connector class to register
        """
        cls._connectors[connector_type] = connector_class
        logger.info(f"Registered connector: {connector_type}")
    
    @classmethod
    def get_connector(cls, connector_type: str, config: Dict[str, Any] = None):
        """
        Get a connector instance by type.
        
        Args:
            connector_type: Type of connector to get
            config: Configuration for the connector
            
        Returns:
            Connector instance or None if not found
        """
        if connector_type not in cls._connectors:
            logger.error(f"Connector not found: {connector_type}")
            return None
        
        try:
            connector_class = cls._connectors[connector_type]
            return connector_class(config or {})
        except Exception as e:
            logger.error(f"Error creating connector {connector_type}: {e}")
            return None
    
    @classmethod
    def list_connectors(cls) -> List[str]:
        """
        Get list of registered connector types.
        
        Returns:
            List of connector type names
        """
        return list(cls._connectors.keys())
    
    @classmethod
    def validate_all_configs(cls) -> Dict[str, List[str]]:
        """
        Validate configurations for all registered connectors.
        
        Returns:
            Dict mapping connector types to validation errors
        """
        results = {}
        
        for connector_type, connector_class in cls._connectors.items():
            try:
                # Create instance with minimal config for validation
                instance = connector_class({'name': f'test_{connector_type}'})
                is_valid, errors = instance.validate_config()
                if not is_valid:
                    results[connector_type] = errors
            except Exception as e:
                results[connector_type] = [f"Error creating instance: {str(e)}"]
        
        return results


class ConnectorError(Exception):
    """Base exception class for connector errors."""
    pass


class AuthenticationError(ConnectorError):
    """Raised when authentication fails."""
    pass


class RateLimitError(ConnectorError):
    """Raised when rate limit is exceeded."""
    pass


class DataExtractionError(ConnectorError):
    """Raised when data extraction fails."""
    pass


class ConfigurationError(ConnectorError):
    """Raised when connector configuration is invalid."""
    pass