"""
CSV File Connector for Data Ingestion
"""

import csv
import pandas as pd
import logging
from typing import Dict, List, Any, Tuple, Optional
from datetime import datetime
import os
from io import StringIO

from .base import FileConnector, ConnectorRegistry, DataExtractionError, ConfigurationError

logger = logging.getLogger(__name__)


class CSVConnector(FileConnector):
    """
    Connector for CSV file ingestion with validation and type inference.
    """
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.encoding = config.get('encoding', 'utf-8')
        self.delimiter = config.get('delimiter', ',')
        self.quote_char = config.get('quote_char', '"')
        self.skip_rows = config.get('skip_rows', 0)
        self.max_rows = config.get('max_rows', None)
        self.required_columns = config.get('required_columns', [])
        self.column_mapping = config.get('column_mapping', {})
        self.date_columns = config.get('date_columns', [])
        self.numeric_columns = config.get('numeric_columns', [])
        
    def extract(self, query_params: Dict[str, Any] = None) -> List[Dict[str, Any]]:
        """
        Extract data from CSV file.
        
        Args:
            query_params: Should contain 'file_path' or 'file_content'
            
        Returns:
            List of records as dictionaries
        """
        if not query_params:
            raise DataExtractionError("No query parameters provided")
        
        file_path = query_params.get('file_path')
        file_content = query_params.get('file_content')
        
        if not file_path and not file_content:
            raise DataExtractionError("Either file_path or file_content must be provided")
        
        try:
            self.rate_limit_check()
            
            if file_content:
                # Read from string content (e.g., uploaded file content)
                data = self._read_from_content(file_content)
            else:
                # Read from file path
                is_valid, errors = self.validate_file(file_path)
                if not is_valid:
                    raise DataExtractionError(f"File validation failed: {'; '.join(errors)}")
                
                data = self.read_file(file_path)
            
            # Apply transformations
            data = self._apply_transformations(data)
            
            # Validate required columns
            self._validate_required_columns(data)
            
            self.log_activity('extract', {
                'source': file_path or 'content',
                'records_extracted': len(data),
                'columns': list(data[0].keys()) if data else []
            })
            
            return data
            
        except Exception as e:
            logger.error(f"Error extracting from CSV: {e}")
            raise DataExtractionError(f"CSV extraction failed: {str(e)}")
    
    def read_file(self, file_path: str, **kwargs) -> List[Dict[str, Any]]:
        """
        Read data from CSV file.
        
        Args:
            file_path: Path to the CSV file
            **kwargs: Additional parameters
            
        Returns:
            List of records as dictionaries
        """
        try:
            # Use pandas for robust CSV reading
            df = pd.read_csv(
                file_path,
                encoding=self.encoding,
                delimiter=self.delimiter,
                quotechar=self.quote_char,
                skiprows=self.skip_rows,
                nrows=self.max_rows,
                dtype='object'  # Read everything as string initially
            )
            
            # Convert DataFrame to list of dictionaries
            return df.fillna('').to_dict('records')
            
        except Exception as e:
            raise DataExtractionError(f"Error reading CSV file {file_path}: {str(e)}")
    
    def _read_from_content(self, content: str) -> List[Dict[str, Any]]:
        """
        Read data from CSV content string.
        
        Args:
            content: CSV content as string
            
        Returns:
            List of records as dictionaries
        """
        try:
            # Use StringIO to read from string content
            df = pd.read_csv(
                StringIO(content),
                encoding=self.encoding,
                delimiter=self.delimiter,
                quotechar=self.quote_char,
                skiprows=self.skip_rows,
                nrows=self.max_rows,
                dtype='object'  # Read everything as string initially
            )
            
            return df.fillna('').to_dict('records')
            
        except Exception as e:
            raise DataExtractionError(f"Error reading CSV content: {str(e)}")
    
    def _apply_transformations(self, data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Apply transformations to the extracted data.
        
        Args:
            data: Raw extracted data
            
        Returns:
            Transformed data
        """
        if not data:
            return data
        
        transformed_data = []
        
        for record in data:
            try:
                transformed_record = {}
                
                for original_column, value in record.items():
                    # Apply column mapping
                    column_name = self.column_mapping.get(original_column, original_column)
                    
                    # Type conversions
                    if column_name in self.date_columns:
                        value = self._parse_date(value)
                    elif column_name in self.numeric_columns:
                        value = self._parse_numeric(value)
                    
                    transformed_record[column_name] = value
                
                # Add metadata
                transformed_record['_csv_row_number'] = len(transformed_data) + 1
                transformed_record['_csv_source'] = self.name
                transformed_record['_csv_processed_at'] = datetime.now().isoformat()
                
                transformed_data.append(transformed_record)
                
            except Exception as e:
                logger.warning(f"Error transforming record {len(transformed_data) + 1}: {e}")
                # Continue processing other records
                continue
        
        return transformed_data
    
    def _parse_date(self, value: str) -> Optional[str]:
        """Parse date string to ISO format."""
        if not value or pd.isna(value):
            return None
        
        try:
            # Try to parse date with pandas
            parsed_date = pd.to_datetime(value, infer_datetime_format=True)
            return parsed_date.isoformat()
        except:
            logger.warning(f"Could not parse date: {value}")
            return str(value)  # Return as string if parsing fails
    
    def _parse_numeric(self, value: str) -> Optional[float]:
        """Parse numeric string to float."""
        if not value or pd.isna(value):
            return None
        
        try:
            # Remove common formatting characters
            cleaned_value = str(value).replace(',', '').replace('$', '').replace('%', '')
            return float(cleaned_value)
        except:
            logger.warning(f"Could not parse numeric: {value}")
            return None
    
    def _validate_required_columns(self, data: List[Dict[str, Any]]):
        """
        Validate that required columns are present.
        
        Args:
            data: Extracted data
            
        Raises:
            DataExtractionError: If required columns are missing
        """
        if not data or not self.required_columns:
            return
        
        available_columns = set(data[0].keys())
        missing_columns = set(self.required_columns) - available_columns
        
        if missing_columns:
            raise DataExtractionError(
                f"Required columns missing: {', '.join(missing_columns)}"
            )
    
    def validate_config(self) -> Tuple[bool, List[str]]:
        """
        Validate connector configuration.
        
        Returns:
            Tuple of (is_valid, list_of_errors)
        """
        errors = []
        
        # Validate encoding
        try:
            'test'.encode(self.encoding)
        except LookupError:
            errors.append(f"Invalid encoding: {self.encoding}")
        
        # Validate delimiter
        if not self.delimiter:
            errors.append("Delimiter cannot be empty")
        
        # Validate quote character
        if len(self.quote_char) != 1:
            errors.append("Quote character must be a single character")
        
        # Validate skip_rows
        if self.skip_rows < 0:
            errors.append("skip_rows must be non-negative")
        
        # Validate max_rows
        if self.max_rows is not None and self.max_rows <= 0:
            errors.append("max_rows must be positive")
        
        # Validate required columns
        if not isinstance(self.required_columns, list):
            errors.append("required_columns must be a list")
        
        # Validate column mapping
        if not isinstance(self.column_mapping, dict):
            errors.append("column_mapping must be a dictionary")
        
        return len(errors) == 0, errors
    
    def health_check(self, config: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Check connector health (for file connector, this is mainly config validation).
        
        Args:
            config: Optional config override
            
        Returns:
            Dict with health status
        """
        start_time = datetime.now()
        
        try:
            # Validate current config
            is_valid, errors = self.validate_config()
            
            response_time = (datetime.now() - start_time).total_seconds() * 1000
            
            return {
                'healthy': is_valid,
                'response_time': response_time,
                'error': '; '.join(errors) if errors else None,
                'timestamp': start_time.isoformat(),
                'connector_type': 'csv',
                'config_valid': is_valid
            }
            
        except Exception as e:
            response_time = (datetime.now() - start_time).total_seconds() * 1000
            return {
                'healthy': False,
                'response_time': response_time,
                'error': str(e),
                'timestamp': start_time.isoformat(),
                'connector_type': 'csv'
            }
    
    def preview_file(self, file_path: str = None, file_content: str = None, 
                    max_rows: int = 10) -> Dict[str, Any]:
        """
        Preview CSV file structure and sample data.
        
        Args:
            file_path: Path to CSV file
            file_content: CSV content as string
            max_rows: Maximum rows to preview
            
        Returns:
            Dict with preview information
        """
        try:
            # Temporarily override max_rows for preview
            original_max_rows = self.max_rows
            self.max_rows = max_rows
            
            if file_content:
                sample_data = self._read_from_content(file_content)
            elif file_path:
                sample_data = self.read_file(file_path)
            else:
                raise ValueError("Either file_path or file_content must be provided")
            
            # Restore original max_rows
            self.max_rows = original_max_rows
            
            # Analyze structure
            preview_info = {
                'total_preview_rows': len(sample_data),
                'columns': list(sample_data[0].keys()) if sample_data else [],
                'sample_data': sample_data[:5],  # Show first 5 rows
                'column_types': {},
                'missing_required_columns': [],
                'encoding': self.encoding,
                'delimiter': self.delimiter
            }
            
            # Analyze column types
            if sample_data:
                for column in preview_info['columns']:
                    sample_values = [str(row.get(column, '')) for row in sample_data if row.get(column)]
                    preview_info['column_types'][column] = self._infer_column_type(sample_values)
            
            # Check required columns
            if self.required_columns:
                available_columns = set(preview_info['columns'])
                preview_info['missing_required_columns'] = list(
                    set(self.required_columns) - available_columns
                )
            
            return preview_info
            
        except Exception as e:
            logger.error(f"Error previewing CSV file: {e}")
            raise DataExtractionError(f"Preview failed: {str(e)}")
    
    def _infer_column_type(self, sample_values: List[str]) -> str:
        """
        Infer column type from sample values.
        
        Args:
            sample_values: Sample values from the column
            
        Returns:
            Inferred type ('numeric', 'date', 'text')
        """
        if not sample_values:
            return 'text'
        
        # Remove empty values
        non_empty_values = [v for v in sample_values if v.strip()]
        if not non_empty_values:
            return 'text'
        
        # Check if numeric
        numeric_count = 0
        for value in non_empty_values:
            try:
                float(value.replace(',', '').replace('$', '').replace('%', ''))
                numeric_count += 1
            except:
                pass
        
        if numeric_count / len(non_empty_values) > 0.8:
            return 'numeric'
        
        # Check if date
        date_count = 0
        for value in non_empty_values:
            try:
                pd.to_datetime(value, infer_datetime_format=True)
                date_count += 1
            except:
                pass
        
        if date_count / len(non_empty_values) > 0.8:
            return 'date'
        
        return 'text'


# Register the connector
ConnectorRegistry.register('csv', CSVConnector)