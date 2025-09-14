"""
Data Transformation Utilities for ETL Processing
"""

import logging
import re
from datetime import datetime, timezone
from decimal import Decimal
from typing import Dict, List, Any, Optional, Callable, Union
from dataclasses import dataclass
import hashlib
import json

logger = logging.getLogger(__name__)


@dataclass
class TransformationRule:
    """Configuration for a transformation rule."""
    source_field: str
    target_field: str
    transform_type: str
    parameters: Dict[str, Any]
    condition: Optional[str] = None  # Optional condition for applying transformation


class DataTransformer:
    """
    Comprehensive data transformation for ETL processes.
    """
    
    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or {}
        self.transformation_rules = self._load_transformation_rules()
        self.custom_transformers = self._load_custom_transformers()
    
    def transform(self, source: str, record: Dict[str, Any]) -> Dict[str, Any]:
        """
        Transform a single record according to configured rules.
        
        Args:
            source: Data source name
            record: Record to transform
            
        Returns:
            Transformed record
        """
        try:
            # Start with original record
            transformed_record = record.copy()
            
            # Add metadata fields
            transformed_record['_source'] = source
            transformed_record['_processed_at'] = datetime.now(timezone.utc).isoformat()
            transformed_record['_record_hash'] = self._generate_record_hash(record)
            
            # Apply transformation rules
            source_rules = self.transformation_rules.get(source, [])
            
            for rule in source_rules:
                try:
                    # Check condition if specified
                    if rule.condition and not self._evaluate_condition(rule.condition, transformed_record):
                        continue
                    
                    # Apply transformation
                    transformed_value = self._apply_transformation(
                        transformed_record.get(rule.source_field),
                        rule.transform_type,
                        rule.parameters,
                        transformed_record
                    )
                    
                    # Set transformed value
                    if rule.target_field:
                        transformed_record[rule.target_field] = transformed_value
                    else:
                        transformed_record[rule.source_field] = transformed_value
                        
                except Exception as e:
                    logger.error(f"Error applying transformation rule {rule.transform_type} to field {rule.source_field}: {e}")
                    # Continue with other transformations
            
            # Apply source-specific transformations
            transformed_record = self._apply_source_specific_transformations(source, transformed_record)
            
            # Apply standardization
            transformed_record = self._apply_standardization(transformed_record)
            
            return transformed_record
            
        except Exception as e:
            logger.error(f"Error transforming record: {e}")
            # Return original record with error metadata
            error_record = record.copy()
            error_record['_transformation_error'] = str(e)
            error_record['_processed_at'] = datetime.now(timezone.utc).isoformat()
            return error_record
    
    def transform_batch(self, source: str, records: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Transform a batch of records.
        
        Args:
            source: Data source name
            records: List of records to transform
            
        Returns:
            Batch transformation results
        """
        results = {
            'total_records': len(records),
            'successful_transforms': 0,
            'failed_transforms': 0,
            'transformed_records': [],
            'errors': [],
            'started_at': datetime.now().isoformat()
        }
        
        for i, record in enumerate(records):
            try:
                transformed_record = self.transform(source, record)
                
                if '_transformation_error' in transformed_record:
                    results['failed_transforms'] += 1
                    results['errors'].append({
                        'record_index': i,
                        'error': transformed_record['_transformation_error']
                    })
                else:
                    results['successful_transforms'] += 1
                
                results['transformed_records'].append(transformed_record)
                
            except Exception as e:
                logger.error(f"Error transforming record {i}: {e}")
                results['failed_transforms'] += 1
                results['errors'].append({
                    'record_index': i,
                    'error': str(e)
                })
                
                # Add original record with error metadata
                error_record = record.copy()
                error_record['_transformation_error'] = str(e)
                results['transformed_records'].append(error_record)
        
        results['completed_at'] = datetime.now().isoformat()
        return results
    
    def _apply_transformation(self, value: Any, transform_type: str, parameters: Dict[str, Any], record: Dict[str, Any]) -> Any:
        """
        Apply a single transformation to a value.
        
        Args:
            value: Value to transform
            transform_type: Type of transformation
            parameters: Transformation parameters
            record: Complete record for context
            
        Returns:
            Transformed value
        """
        if transform_type == 'cast':
            return self._transform_cast(value, parameters)
        
        elif transform_type == 'format':
            return self._transform_format(value, parameters)
        
        elif transform_type == 'normalize':
            return self._transform_normalize(value, parameters)
        
        elif transform_type == 'extract':
            return self._transform_extract(value, parameters)
        
        elif transform_type == 'replace':
            return self._transform_replace(value, parameters)
        
        elif transform_type == 'calculate':
            return self._transform_calculate(value, parameters, record)
        
        elif transform_type == 'lookup':
            return self._transform_lookup(value, parameters)
        
        elif transform_type == 'concatenate':
            return self._transform_concatenate(value, parameters, record)
        
        elif transform_type == 'split':
            return self._transform_split(value, parameters)
        
        elif transform_type == 'encrypt':
            return self._transform_encrypt(value, parameters)
        
        elif transform_type == 'mask':
            return self._transform_mask(value, parameters)
        
        elif transform_type == 'custom':
            return self._transform_custom(value, parameters, record)
        
        else:
            logger.warning(f"Unknown transformation type: {transform_type}")
            return value
    
    def _transform_cast(self, value: Any, parameters: Dict[str, Any]) -> Any:
        """Cast value to specific type."""
        target_type = parameters.get('type')
        
        if value is None:
            return None
        
        try:
            if target_type == 'int':
                return int(float(value))  # Handle decimal strings
            elif target_type == 'float':
                return float(value)
            elif target_type == 'decimal':
                return Decimal(str(value))
            elif target_type == 'str':
                return str(value)
            elif target_type == 'bool':
                if isinstance(value, bool):
                    return value
                str_val = str(value).lower()
                return str_val in ['true', '1', 'yes', 'y', 'on']
            elif target_type == 'datetime':
                if isinstance(value, datetime):
                    return value
                return datetime.fromisoformat(str(value).replace('Z', '+00:00'))
            else:
                logger.warning(f"Unknown cast type: {target_type}")
                return value
                
        except (ValueError, TypeError) as e:
            logger.error(f"Error casting value {value} to {target_type}: {e}")
            return value
    
    def _transform_format(self, value: Any, parameters: Dict[str, Any]) -> Any:
        """Format value according to specified format."""
        format_type = parameters.get('format_type')
        format_string = parameters.get('format')
        
        if value is None:
            return None
        
        try:
            if format_type == 'date':
                if isinstance(value, str):
                    # Parse date from string
                    input_format = parameters.get('input_format', '%Y-%m-%d')
                    dt = datetime.strptime(value, input_format)
                else:
                    dt = value
                
                return dt.strftime(format_string or '%Y-%m-%d')
            
            elif format_type == 'number':
                num_value = float(value)
                if format_string:
                    return format_string.format(num_value)
                else:
                    # Default decimal formatting
                    decimals = parameters.get('decimals', 2)
                    return f"{num_value:.{decimals}f}"
            
            elif format_type == 'string':
                return format_string.format(value) if format_string else str(value)
            
            else:
                return str(value)
                
        except (ValueError, TypeError) as e:
            logger.error(f"Error formatting value {value}: {e}")
            return value
    
    def _transform_normalize(self, value: Any, parameters: Dict[str, Any]) -> Any:
        """Normalize value (case, whitespace, etc.)."""
        if value is None:
            return None
        
        str_value = str(value)
        
        # Normalize whitespace
        if parameters.get('trim', True):
            str_value = str_value.strip()
        
        if parameters.get('remove_extra_spaces', True):
            str_value = re.sub(r'\s+', ' ', str_value)
        
        # Normalize case
        case_option = parameters.get('case')
        if case_option == 'upper':
            str_value = str_value.upper()
        elif case_option == 'lower':
            str_value = str_value.lower()
        elif case_option == 'title':
            str_value = str_value.title()
        elif case_option == 'sentence':
            str_value = str_value.capitalize()
        
        # Remove special characters if specified
        if parameters.get('remove_special_chars'):
            allowed_chars = parameters.get('allowed_chars', 'a-zA-Z0-9 ')
            str_value = re.sub(f'[^{allowed_chars}]', '', str_value)
        
        return str_value
    
    def _transform_extract(self, value: Any, parameters: Dict[str, Any]) -> Any:
        """Extract part of value using regex or substring."""
        if value is None:
            return None
        
        str_value = str(value)
        
        if 'regex' in parameters:
            pattern = parameters['regex']
            group = parameters.get('group', 0)
            
            try:
                match = re.search(pattern, str_value)
                if match:
                    return match.group(group)
                else:
                    return parameters.get('default', '')
            except re.error as e:
                logger.error(f"Invalid regex pattern {pattern}: {e}")
                return str_value
        
        elif 'start' in parameters or 'end' in parameters:
            start = parameters.get('start', 0)
            end = parameters.get('end')
            
            if end is not None:
                return str_value[start:end]
            else:
                return str_value[start:]
        
        else:
            return str_value
    
    def _transform_replace(self, value: Any, parameters: Dict[str, Any]) -> Any:
        """Replace parts of value."""
        if value is None:
            return None
        
        str_value = str(value)
        
        # Handle multiple replacements
        replacements = parameters.get('replacements', [])
        for replacement in replacements:
            pattern = replacement['pattern']
            replace_with = replacement['replace_with']
            use_regex = replacement.get('regex', False)
            
            if use_regex:
                str_value = re.sub(pattern, replace_with, str_value)
            else:
                str_value = str_value.replace(pattern, replace_with)
        
        # Handle single replacement (backward compatibility)
        if 'pattern' in parameters:
            pattern = parameters['pattern']
            replace_with = parameters.get('replace_with', '')
            use_regex = parameters.get('regex', False)
            
            if use_regex:
                str_value = re.sub(pattern, replace_with, str_value)
            else:
                str_value = str_value.replace(pattern, replace_with)
        
        return str_value
    
    def _transform_calculate(self, value: Any, parameters: Dict[str, Any], record: Dict[str, Any]) -> Any:
        """Perform calculations using value and other record fields."""
        operation = parameters.get('operation')
        
        if operation == 'multiply':
            multiplier = parameters.get('multiplier', 1)
            return float(value or 0) * multiplier
        
        elif operation == 'divide':
            divisor = parameters.get('divisor', 1)
            return float(value or 0) / divisor if divisor != 0 else 0
        
        elif operation == 'add':
            addend = parameters.get('addend', 0)
            return float(value or 0) + addend
        
        elif operation == 'subtract':
            subtrahend = parameters.get('subtrahend', 0)
            return float(value or 0) - subtrahend
        
        elif operation == 'percentage':
            total_field = parameters.get('total_field')
            total_value = float(record.get(total_field, 1))
            return (float(value or 0) / total_value * 100) if total_value != 0 else 0
        
        elif operation == 'formula':
            # Evaluate formula with record context
            formula = parameters.get('formula')
            safe_dict = {k: v for k, v in record.items() if isinstance(v, (int, float, complex))}
            safe_dict['value'] = float(value or 0)
            
            try:
                # Simple expression evaluation (be careful with security)
                return eval(formula, {"__builtins__": {}}, safe_dict)
            except Exception as e:
                logger.error(f"Error evaluating formula {formula}: {e}")
                return value
        
        else:
            logger.warning(f"Unknown calculation operation: {operation}")
            return value
    
    def _transform_lookup(self, value: Any, parameters: Dict[str, Any]) -> Any:
        """Lookup value from mapping table."""
        lookup_table = parameters.get('table', {})
        default_value = parameters.get('default')
        
        return lookup_table.get(str(value), default_value if default_value is not None else value)
    
    def _transform_concatenate(self, value: Any, parameters: Dict[str, Any], record: Dict[str, Any]) -> Any:
        """Concatenate value with other fields."""
        fields = parameters.get('fields', [])
        separator = parameters.get('separator', '')
        
        values = [str(value or '')]
        for field in fields:
            field_value = record.get(field, '')
            values.append(str(field_value))
        
        return separator.join(values)
    
    def _transform_split(self, value: Any, parameters: Dict[str, Any]) -> Any:
        """Split value and return specific part."""
        if value is None:
            return None
        
        separator = parameters.get('separator', ',')
        index = parameters.get('index', 0)
        
        parts = str(value).split(separator)
        
        try:
            return parts[index].strip() if index < len(parts) else ''
        except IndexError:
            return ''
    
    def _transform_encrypt(self, value: Any, parameters: Dict[str, Any]) -> Any:
        """Encrypt sensitive value."""
        if value is None:
            return None
        
        # Simple hash-based encryption for demonstration
        # In production, use proper encryption libraries
        algorithm = parameters.get('algorithm', 'sha256')
        
        if algorithm == 'sha256':
            return hashlib.sha256(str(value).encode()).hexdigest()
        elif algorithm == 'md5':
            return hashlib.md5(str(value).encode()).hexdigest()
        else:
            logger.warning(f"Unknown encryption algorithm: {algorithm}")
            return value
    
    def _transform_mask(self, value: Any, parameters: Dict[str, Any]) -> Any:
        """Mask sensitive data."""
        if value is None:
            return None
        
        str_value = str(value)
        mask_char = parameters.get('mask_char', '*')
        
        # Mask types
        mask_type = parameters.get('type', 'partial')
        
        if mask_type == 'full':
            return mask_char * len(str_value)
        
        elif mask_type == 'partial':
            show_first = parameters.get('show_first', 2)
            show_last = parameters.get('show_last', 2)
            
            if len(str_value) <= show_first + show_last:
                return mask_char * len(str_value)
            
            masked_section = mask_char * (len(str_value) - show_first - show_last)
            return str_value[:show_first] + masked_section + str_value[-show_last:]
        
        elif mask_type == 'email':
            if '@' in str_value:
                username, domain = str_value.split('@', 1)
                masked_username = username[0] + mask_char * (len(username) - 1)
                return f"{masked_username}@{domain}"
            else:
                return str_value
        
        else:
            return str_value
    
    def _transform_custom(self, value: Any, parameters: Dict[str, Any], record: Dict[str, Any]) -> Any:
        """Apply custom transformation."""
        function_name = parameters.get('function')
        
        if function_name in self.custom_transformers:
            transformer_func = self.custom_transformers[function_name]
            try:
                return transformer_func(value, parameters, record)
            except Exception as e:
                logger.error(f"Error in custom transformer {function_name}: {e}")
                return value
        else:
            logger.warning(f"Custom transformer not found: {function_name}")
            return value
    
    def _apply_source_specific_transformations(self, source: str, record: Dict[str, Any]) -> Dict[str, Any]:
        """Apply transformations specific to data source."""
        if source == 'pos':
            return self._transform_pos_data(record)
        elif source == 'api_sales':
            return self._transform_api_sales_data(record)
        elif source == 'csv_upload':
            return self._transform_csv_data(record)
        elif source == 'inventory':
            return self._transform_inventory_data(record)
        else:
            return record
    
    def _transform_pos_data(self, record: Dict[str, Any]) -> Dict[str, Any]:
        """Transform POS-specific data."""
        # Standardize currency amounts
        if 'price' in record:
            try:
                # Remove currency symbols and normalize
                price_str = str(record['price']).replace('$', '').replace(',', '')
                record['price'] = float(price_str)
            except (ValueError, TypeError):
                pass
        
        # Calculate derived fields
        if 'quantity' in record and 'price' in record:
            try:
                record['line_total'] = float(record['quantity']) * float(record['price'])
            except (ValueError, TypeError):
                pass
        
        # Standardize timestamps
        if 'sale_time' in record:
            record['sale_time'] = self._standardize_timestamp(record['sale_time'])
        
        return record
    
    def _transform_api_sales_data(self, record: Dict[str, Any]) -> Dict[str, Any]:
        """Transform API sales data."""
        # Map API field names to standard field names
        field_mapping = {
            'id': 'transaction_id',
            'customer_id': 'customer_id',
            'amount': 'total_amount',
            'created_at': 'sale_time'
        }
        
        for api_field, standard_field in field_mapping.items():
            if api_field in record and standard_field not in record:
                record[standard_field] = record[api_field]
        
        return record
    
    def _transform_csv_data(self, record: Dict[str, Any]) -> Dict[str, Any]:
        """Transform CSV upload data."""
        # Handle common CSV issues
        for key, value in record.items():
            if isinstance(value, str):
                # Remove BOM characters
                record[key] = value.replace('\ufeff', '')
                
                # Handle empty strings
                if value.strip() == '':
                    record[key] = None
        
        return record
    
    def _transform_inventory_data(self, record: Dict[str, Any]) -> Dict[str, Any]:
        """Transform inventory data."""
        # Calculate inventory metrics
        if 'current_stock' in record and 'min_stock' in record:
            try:
                current = float(record['current_stock'])
                minimum = float(record['min_stock'])
                record['stock_status'] = 'low' if current <= minimum else 'normal'
                record['stock_ratio'] = current / minimum if minimum > 0 else 0
            except (ValueError, TypeError):
                pass
        
        return record
    
    def _apply_standardization(self, record: Dict[str, Any]) -> Dict[str, Any]:
        """Apply standard transformations to all records."""
        # Standardize common field names
        field_standardization = {
            'id': 'record_id',
            'timestamp': 'event_timestamp',
            'created': 'created_at',
            'modified': 'updated_at'
        }
        
        for old_field, new_field in field_standardization.items():
            if old_field in record and new_field not in record:
                record[new_field] = record[old_field]
        
        # Ensure required metadata fields
        if '_processed_at' not in record:
            record['_processed_at'] = datetime.now(timezone.utc).isoformat()
        
        return record
    
    def _standardize_timestamp(self, timestamp_value: Any) -> str:
        """Standardize timestamp to ISO format."""
        if timestamp_value is None:
            return None
        
        try:
            if isinstance(timestamp_value, datetime):
                return timestamp_value.isoformat()
            
            # Try to parse various timestamp formats
            timestamp_str = str(timestamp_value)
            
            # Common formats to try
            formats = [
                '%Y-%m-%d %H:%M:%S',
                '%Y-%m-%d %H:%M:%S.%f',
                '%Y-%m-%dT%H:%M:%S',
                '%Y-%m-%dT%H:%M:%S.%f',
                '%Y-%m-%dT%H:%M:%SZ',
                '%Y-%m-%d',
                '%m/%d/%Y %H:%M:%S',
                '%m/%d/%Y'
            ]
            
            for fmt in formats:
                try:
                    dt = datetime.strptime(timestamp_str, fmt)
                    return dt.isoformat()
                except ValueError:
                    continue
            
            # If all formats fail, return original
            logger.warning(f"Could not parse timestamp: {timestamp_value}")
            return timestamp_str
            
        except Exception as e:
            logger.error(f"Error standardizing timestamp {timestamp_value}: {e}")
            return str(timestamp_value)
    
    def _generate_record_hash(self, record: Dict[str, Any]) -> str:
        """Generate hash for record deduplication."""
        # Create a stable representation of the record
        # Exclude metadata fields from hash calculation
        excluded_fields = {'_source', '_processed_at', '_record_hash', '_transformation_error'}
        
        hash_dict = {k: v for k, v in record.items() if k not in excluded_fields}
        
        # Create consistent JSON representation
        record_json = json.dumps(hash_dict, sort_keys=True, default=str)
        
        # Generate SHA-256 hash
        return hashlib.sha256(record_json.encode()).hexdigest()
    
    def _evaluate_condition(self, condition: str, record: Dict[str, Any]) -> bool:
        """Evaluate condition for conditional transformations."""
        try:
            # Simple condition evaluation
            # Format: "field operator value" (e.g., "status == 'active'")
            
            # More sophisticated condition evaluation could use a parser
            # For now, use basic eval with restricted context
            safe_dict = {k: v for k, v in record.items()}
            return eval(condition, {"__builtins__": {}}, safe_dict)
            
        except Exception as e:
            logger.error(f"Error evaluating condition {condition}: {e}")
            return False
    
    def _load_transformation_rules(self) -> Dict[str, List[TransformationRule]]:
        """Load transformation rules from configuration."""
        # Default transformation rules
        default_rules = {
            'pos': [
                TransformationRule('sale_time', 'event_timestamp', 'format', {
                    'format_type': 'date', 'format': '%Y-%m-%dT%H:%M:%SZ'
                }),
                TransformationRule('price', 'price', 'cast', {'type': 'decimal'}),
                TransformationRule('quantity', 'quantity', 'cast', {'type': 'int'}),
            ],
            'csv_upload': [
                TransformationRule('', '', 'normalize', {'trim': True, 'case': 'lower'})
            ]
        }
        
        # Load custom rules from config
        custom_rules = self.config.get('transformation_rules', {})
        
        for source, rules in custom_rules.items():
            rule_objects = []
            for rule_config in rules:
                rule_objects.append(TransformationRule(
                    source_field=rule_config['source_field'],
                    target_field=rule_config.get('target_field', ''),
                    transform_type=rule_config['transform_type'],
                    parameters=rule_config.get('parameters', {}),
                    condition=rule_config.get('condition')
                ))
            default_rules[source] = rule_objects
        
        return default_rules
    
    def _load_custom_transformers(self) -> Dict[str, Callable]:
        """Load custom transformer functions."""
        return self.config.get('custom_transformers', {})