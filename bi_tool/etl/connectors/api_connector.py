"""
REST API Connector for Data Ingestion
"""

import requests
import json
import logging
import time
from typing import Dict, List, Any, Tuple, Optional
from datetime import datetime, timedelta
from urllib.parse import urljoin, urlencode

from .base import APIConnector, ConnectorRegistry, DataExtractionError, AuthenticationError, RateLimitError

logger = logging.getLogger(__name__)


class RestAPIConnector(APIConnector):
    """
    Connector for REST API data ingestion with authentication and pagination support.
    """
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.base_url = config.get('base_url', '').rstrip('/')
        self.auth_type = config.get('auth_type', 'none')
        self.auth_config = config.get('auth_config', {})
        self.timeout = config.get('timeout', 30)
        self.max_retries = config.get('max_retries', 3)
        self.retry_delay = config.get('retry_delay', 1)
        self.headers = config.get('headers', {})
        self.pagination_config = config.get('pagination', {})
        
        # Initialize session
        self.session = requests.Session()
        self.session.headers.update(self.headers)
    
    def extract(self, query_params: Dict[str, Any] = None) -> List[Dict[str, Any]]:
        """
        Extract data from REST API endpoint.
        
        Args:
            query_params: Parameters including 'endpoint', filters, pagination
            
        Returns:
            List of records as dictionaries
        """
        if not query_params or 'endpoint' not in query_params:
            raise DataExtractionError("API endpoint must be provided in query_params")
        
        endpoint = query_params['endpoint']
        filters = query_params.get('filters', {})
        use_pagination = query_params.get('paginate', True)
        
        try:
            self.ensure_authenticated()
            
            all_data = []
            
            if use_pagination and self.pagination_config:
                # Extract with pagination
                all_data = self._extract_paginated(endpoint, filters)
            else:
                # Extract single request
                response_data = self.make_request(endpoint, filters)
                all_data = self._extract_records_from_response(response_data)
            
            self.log_activity('extract', {
                'endpoint': endpoint,
                'records_extracted': len(all_data),
                'filters': filters
            })
            
            return all_data
            
        except Exception as e:
            logger.error(f"Error extracting from API: {e}")
            raise DataExtractionError(f"API extraction failed: {str(e)}")
    
    def _extract_paginated(self, endpoint: str, filters: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Extract data with pagination support.
        
        Args:
            endpoint: API endpoint
            filters: Query filters
            
        Returns:
            List of all records across pages
        """
        all_data = []
        page = self.pagination_config.get('start_page', 1)
        page_size = self.pagination_config.get('page_size', 100)
        max_pages = self.pagination_config.get('max_pages', 1000)
        
        page_param = self.pagination_config.get('page_param', 'page')
        size_param = self.pagination_config.get('size_param', 'limit')
        
        for page_num in range(page, page + max_pages):
            try:
                # Add pagination parameters
                page_filters = filters.copy()
                page_filters[page_param] = page_num
                page_filters[size_param] = page_size
                
                logger.debug(f"Fetching page {page_num} from {endpoint}")
                response_data = self.make_request(endpoint, page_filters)
                
                # Extract records from response
                page_records = self._extract_records_from_response(response_data)
                
                if not page_records:
                    # No more data
                    break
                
                all_data.extend(page_records)
                
                # Check if this was the last page
                if self._is_last_page(response_data, page_records, page_size):
                    break
                
                # Rate limiting between pages
                if self.rate_limit > 0:
                    time.sleep(60.0 / self.rate_limit)
                
            except Exception as e:
                logger.error(f"Error fetching page {page_num}: {e}")
                if page_num == page:
                    # If first page fails, re-raise the error
                    raise
                else:
                    # For subsequent pages, log warning and continue
                    logger.warning(f"Skipping page {page_num} due to error: {e}")
                    break
        
        return all_data
    
    def _extract_records_from_response(self, response_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Extract records from API response based on configuration.
        
        Args:
            response_data: Full API response
            
        Returns:
            List of records
        """
        # Default extraction - assumes records are in 'data' field or root level
        data_field = self.config.get('data_field', 'data')
        
        if data_field and data_field in response_data:
            records = response_data[data_field]
        elif isinstance(response_data, list):
            records = response_data
        else:
            # If no data field specified and response is dict, try common fields
            for field in ['data', 'results', 'items', 'records']:
                if field in response_data and isinstance(response_data[field], list):
                    records = response_data[field]
                    break
            else:
                # Wrap single record in list
                records = [response_data]
        
        # Ensure records is a list
        if not isinstance(records, list):
            records = [records]
        
        # Add metadata to each record
        enriched_records = []
        for record in records:
            if isinstance(record, dict):
                record['_api_source'] = self.name
                record['_api_extracted_at'] = datetime.now().isoformat()
                enriched_records.append(record)
            else:
                # Handle non-dict records
                enriched_records.append({
                    'value': record,
                    '_api_source': self.name,
                    '_api_extracted_at': datetime.now().isoformat()
                })
        
        return enriched_records
    
    def _is_last_page(self, response_data: Dict[str, Any], records: List[Dict], 
                     expected_page_size: int) -> bool:
        """
        Determine if this is the last page of results.
        
        Args:
            response_data: Full API response
            records: Extracted records
            expected_page_size: Expected number of records per page
            
        Returns:
            True if this is the last page
        """
        # Method 1: Check if fewer records than expected page size
        if len(records) < expected_page_size:
            return True
        
        # Method 2: Check pagination metadata in response
        pagination_info = response_data.get('pagination', {})
        if pagination_info:
            if 'has_next' in pagination_info:
                return not pagination_info['has_next']
            if 'total_pages' in pagination_info and 'current_page' in pagination_info:
                return pagination_info['current_page'] >= pagination_info['total_pages']
        
        # Method 3: Check for empty results
        return len(records) == 0
    
    def make_request(self, endpoint: str, params: Dict[str, Any] = None, 
                    method: str = 'GET') -> Dict[str, Any]:
        """
        Make HTTP request to API with retries and error handling.
        
        Args:
            endpoint: API endpoint (relative to base_url)
            params: Request parameters
            method: HTTP method
            
        Returns:
            Response data as dictionary
        """
        url = urljoin(self.base_url, endpoint.lstrip('/'))
        params = params or {}
        
        for attempt in range(self.max_retries + 1):
            try:
                self.rate_limit_check()
                
                if method.upper() == 'GET':
                    response = self.session.get(
                        url, 
                        params=params, 
                        timeout=self.timeout
                    )
                elif method.upper() == 'POST':
                    response = self.session.post(
                        url,
                        json=params,
                        timeout=self.timeout
                    )
                else:
                    raise DataExtractionError(f"Unsupported HTTP method: {method}")
                
                # Check for rate limiting
                if response.status_code == 429:
                    retry_after = int(response.headers.get('Retry-After', 60))
                    logger.warning(f"Rate limited, waiting {retry_after} seconds")
                    time.sleep(retry_after)
                    raise RateLimitError("Rate limit exceeded")
                
                # Check for authentication errors
                if response.status_code == 401:
                    logger.warning("Authentication failed, attempting to re-authenticate")
                    self.auth_token = None  # Clear invalid token
                    self.ensure_authenticated()
                    raise AuthenticationError("Authentication required")
                
                # Raise for other HTTP errors
                response.raise_for_status()
                
                # Parse JSON response
                try:
                    return response.json()
                except json.JSONDecodeError:
                    # Return raw text if not JSON
                    return {'raw_response': response.text}
                
            except (requests.RequestException, RateLimitError, AuthenticationError) as e:
                if attempt < self.max_retries:
                    wait_time = self.retry_delay * (2 ** attempt)  # Exponential backoff
                    logger.warning(f"Request failed (attempt {attempt + 1}), retrying in {wait_time}s: {e}")
                    time.sleep(wait_time)
                else:
                    logger.error(f"Request failed after {self.max_retries + 1} attempts: {e}")
                    raise DataExtractionError(f"API request failed: {str(e)}")
            except Exception as e:
                logger.error(f"Unexpected error in API request: {e}")
                raise DataExtractionError(f"Unexpected error: {str(e)}")
    
    def authenticate(self) -> bool:
        """
        Authenticate with the API based on auth_type configuration.
        
        Returns:
            True if authentication successful
        """
        try:
            if self.auth_type == 'none':
                return True
            
            elif self.auth_type == 'api_key':
                api_key = self.auth_config.get('api_key')
                if not api_key:
                    raise AuthenticationError("API key not provided")
                
                key_header = self.auth_config.get('header', 'X-API-Key')
                self.session.headers[key_header] = api_key
                self.auth_token = api_key
                return True
            
            elif self.auth_type == 'bearer':
                token = self.auth_config.get('token')
                if not token:
                    raise AuthenticationError("Bearer token not provided")
                
                self.session.headers['Authorization'] = f'Bearer {token}'
                self.auth_token = token
                return True
            
            elif self.auth_type == 'basic':
                username = self.auth_config.get('username')
                password = self.auth_config.get('password')
                if not username or not password:
                    raise AuthenticationError("Username and password required for basic auth")
                
                from requests.auth import HTTPBasicAuth
                self.session.auth = HTTPBasicAuth(username, password)
                self.auth_token = f"{username}:{password}"
                return True
            
            elif self.auth_type == 'oauth':
                return self._authenticate_oauth()
            
            else:
                raise AuthenticationError(f"Unsupported auth type: {self.auth_type}")
                
        except Exception as e:
            logger.error(f"Authentication failed: {e}")
            return False
    
    def _authenticate_oauth(self) -> bool:
        """
        Authenticate using OAuth 2.0 flow.
        
        Returns:
            True if authentication successful
        """
        token_url = self.auth_config.get('token_url')
        client_id = self.auth_config.get('client_id')
        client_secret = self.auth_config.get('client_secret')
        
        if not all([token_url, client_id, client_secret]):
            raise AuthenticationError("OAuth configuration incomplete")
        
        token_data = {
            'grant_type': 'client_credentials',
            'client_id': client_id,
            'client_secret': client_secret
        }
        
        response = requests.post(token_url, data=token_data, timeout=self.timeout)
        response.raise_for_status()
        
        token_info = response.json()
        access_token = token_info.get('access_token')
        
        if not access_token:
            raise AuthenticationError("No access token in OAuth response")
        
        self.auth_token = access_token
        self.session.headers['Authorization'] = f'Bearer {access_token}'
        
        # Set token expiration if provided
        expires_in = token_info.get('expires_in')
        if expires_in:
            self.auth_expires = datetime.now() + timedelta(seconds=expires_in - 60)  # 60s buffer
        
        return True
    
    def validate_config(self) -> Tuple[bool, List[str]]:
        """
        Validate connector configuration.
        
        Returns:
            Tuple of (is_valid, list_of_errors)
        """
        errors = []
        
        # Validate base URL
        if not self.base_url:
            errors.append("base_url is required")
        elif not self.base_url.startswith(('http://', 'https://')):
            errors.append("base_url must start with http:// or https://")
        
        # Validate timeout
        if self.timeout <= 0:
            errors.append("timeout must be positive")
        
        # Validate retry settings
        if self.max_retries < 0:
            errors.append("max_retries must be non-negative")
        
        if self.retry_delay <= 0:
            errors.append("retry_delay must be positive")
        
        # Validate authentication config
        if self.auth_type not in ['none', 'api_key', 'bearer', 'basic', 'oauth']:
            errors.append(f"Unsupported auth_type: {self.auth_type}")
        
        if self.auth_type == 'api_key' and not self.auth_config.get('api_key'):
            errors.append("api_key required for api_key auth_type")
        
        if self.auth_type == 'bearer' and not self.auth_config.get('token'):
            errors.append("token required for bearer auth_type")
        
        if self.auth_type == 'basic':
            if not self.auth_config.get('username'):
                errors.append("username required for basic auth_type")
            if not self.auth_config.get('password'):
                errors.append("password required for basic auth_type")
        
        if self.auth_type == 'oauth':
            required_fields = ['token_url', 'client_id', 'client_secret']
            for field in required_fields:
                if not self.auth_config.get(field):
                    errors.append(f"{field} required for oauth auth_type")
        
        # Validate pagination config
        if self.pagination_config:
            if 'page_size' in self.pagination_config and self.pagination_config['page_size'] <= 0:
                errors.append("pagination page_size must be positive")
        
        return len(errors) == 0, errors
    
    def health_check(self, config: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Check API connectivity and authentication.
        
        Args:
            config: Optional config override
            
        Returns:
            Dict with health status
        """
        start_time = datetime.now()
        
        try:
            # Test authentication
            auth_success = self.authenticate()
            
            if not auth_success:
                return {
                    'healthy': False,
                    'response_time': (datetime.now() - start_time).total_seconds() * 1000,
                    'error': 'Authentication failed',
                    'timestamp': start_time.isoformat(),
                    'connector_type': 'rest_api'
                }
            
            # Test connectivity with a simple request
            health_endpoint = config.get('health_endpoint') if config else self.config.get('health_endpoint')
            
            if health_endpoint:
                try:
                    self.make_request(health_endpoint, method='GET')
                    connectivity_success = True
                    connectivity_error = None
                except Exception as e:
                    connectivity_success = False
                    connectivity_error = str(e)
            else:
                # Skip connectivity test if no health endpoint configured
                connectivity_success = True
                connectivity_error = None
            
            response_time = (datetime.now() - start_time).total_seconds() * 1000
            
            return {
                'healthy': auth_success and connectivity_success,
                'response_time': response_time,
                'error': connectivity_error,
                'timestamp': start_time.isoformat(),
                'connector_type': 'rest_api',
                'authentication': 'success' if auth_success else 'failed',
                'connectivity': 'success' if connectivity_success else 'failed'
            }
            
        except Exception as e:
            response_time = (datetime.now() - start_time).total_seconds() * 1000
            return {
                'healthy': False,
                'response_time': response_time,
                'error': str(e),
                'timestamp': start_time.isoformat(),
                'connector_type': 'rest_api'
            }


# Register the connector
ConnectorRegistry.register('rest_api', RestAPIConnector)
ConnectorRegistry.register('api', RestAPIConnector)  # Alias