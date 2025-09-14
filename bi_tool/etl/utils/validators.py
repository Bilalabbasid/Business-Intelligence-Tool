"""
Data Validation Utilities for ETL Processing
"""

import re
import logging
from decimal import Decimal, InvalidOperation
from datetime import datetime
from typing import Dict, List, Any, Optional, Union
from dataclasses import dataclass
import jsonschema
import pandas as pd

logger = logging.getLogger(__name__)


@dataclass
class ValidationRule:
    """Configuration for a validation rule."""
    field: str
    rule_type: str
    parameters: Dict[str, Any]
    error_message: str
    severity: str = 'error'  # 'error', 'warning'


class DataValidator:
    """
    Comprehensive data validation for ETL processes.
    """
    
    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or {}
        self.validation_rules = self._load_validation_rules()
        self.schema_cache = {}
    
    def validate(self, source: str, record: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate a single record against configured rules.
        
        Args:
            source: Data source name
            record: Record to validate
            
        Returns:
            Dict with validation results
        """
        errors = []
        warnings = []
        
        try:
            # Get validation rules for this source
            source_rules = self.validation_rules.get(source, [])
            
            # Apply each validation rule
            for rule in source_rules:
                try:
                    result = self._apply_rule(record, rule)
                    if not result['valid']:
                        if rule.severity == 'error':
                            errors.append({
                                'field': rule.field,
                                'rule': rule.rule_type,
                                'message': result['message'],
                                'value': record.get(rule.field)
                            })
                        else:
                            warnings.append({
                                'field': rule.field,
                                'rule': rule.rule_type,
                                'message': result['message'],
                                'value': record.get(rule.field)
                            })
                            
                except Exception as e:
                    logger.error(f"Error applying validation rule {rule.rule_type} to field {rule.field}: {e}")
                    errors.append({
                        'field': rule.field,
                        'rule': rule.rule_type,
                        'message': f"Validation rule error: {str(e)}",
                        'value': record.get(rule.field)
                    })
            
            # Apply schema validation if available
            schema_errors = self._validate_schema(source, record)
            errors.extend(schema_errors)
            
            # Apply business logic validation
            business_errors = self._validate_business_logic(source, record)
            errors.extend(business_errors)
            
            return {
                'is_valid': len(errors) == 0,
                'errors': errors,
                'warnings': warnings,
                'validated_at': datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Unexpected error in validation: {e}")
            return {
                'is_valid': False,
                'errors': [{
                    'field': '__system__',
                    'rule': 'system_error',
                    'message': f"Validation system error: {str(e)}",
                    'value': None
                }],
                'warnings': [],
                'validated_at': datetime.now().isoformat()
            }
    
    def validate_batch(self, source: str, records: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Validate a batch of records.
        
        Args:
            source: Data source name
            records: List of records to validate
            
        Returns:
            Batch validation results
        """
        batch_results = {
            'total_records': len(records),
            'valid_records': 0,
            'invalid_records': 0,
            'warnings': 0,
            'validation_details': [],
            'summary': {},
            'started_at': datetime.now().isoformat()
        }
        
        for i, record in enumerate(records):
            try:
                result = self.validate(source, record)
                
                record_info = {
                    'record_index': i,
                    'is_valid': result['is_valid'],
                    'error_count': len(result['errors']),
                    'warning_count': len(result['warnings']),
                    'errors': result['errors'],
                    'warnings': result['warnings']
                }
                
                batch_results['validation_details'].append(record_info)
                
                if result['is_valid']:
                    batch_results['valid_records'] += 1
                else:
                    batch_results['invalid_records'] += 1
                
                batch_results['warnings'] += len(result['warnings'])
                
            except Exception as e:
                logger.error(f"Error validating record {i}: {e}")
                batch_results['invalid_records'] += 1
                batch_results['validation_details'].append({
                    'record_index': i,
                    'is_valid': False,
                    'error_count': 1,
                    'warning_count': 0,
                    'errors': [{
                        'field': '__system__',
                        'rule': 'system_error',
                        'message': str(e),
                        'value': None
                    }],
                    'warnings': []
                })
        
        # Generate summary statistics
        batch_results['summary'] = self._generate_validation_summary(batch_results)
        batch_results['completed_at'] = datetime.now().isoformat()
        
        return batch_results
    
    def _apply_rule(self, record: Dict[str, Any], rule: ValidationRule) -> Dict[str, Any]:
        """
        Apply a single validation rule to a record.
        
        Args:
            record: Record to validate
            rule: Validation rule to apply
            
        Returns:
            Dict with validation result
        """
        field_value = record.get(rule.field)
        
        if rule.rule_type == 'required':
            return self._validate_required(field_value, rule)
        
        elif rule.rule_type == 'type':
            return self._validate_type(field_value, rule)
        
        elif rule.rule_type == 'range':
            return self._validate_range(field_value, rule)
        
        elif rule.rule_type == 'length':
            return self._validate_length(field_value, rule)
        
        elif rule.rule_type == 'pattern':
            return self._validate_pattern(field_value, rule)
        
        elif rule.rule_type == 'enum':
            return self._validate_enum(field_value, rule)
        
        elif rule.rule_type == 'date_format':
            return self._validate_date_format(field_value, rule)
        
        elif rule.rule_type == 'currency':
            return self._validate_currency(field_value, rule)
        
        elif rule.rule_type == 'email':
            return self._validate_email(field_value, rule)
        
        elif rule.rule_type == 'phone':
            return self._validate_phone(field_value, rule)
        
        elif rule.rule_type == 'custom':
            return self._validate_custom(field_value, rule, record)
        
        else:
            return {
                'valid': False,
                'message': f"Unknown validation rule type: {rule.rule_type}"
            }
    
    def _validate_required(self, value: Any, rule: ValidationRule) -> Dict[str, Any]:
        """Validate required field."""
        is_valid = value is not None and str(value).strip() != ''
        return {
            'valid': is_valid,
            'message': rule.error_message if not is_valid else ''
        }
    
    def _validate_type(self, value: Any, rule: ValidationRule) -> Dict[str, Any]:
        """Validate data type."""
        expected_type = rule.parameters.get('type')
        
        if value is None:
            return {'valid': True, 'message': ''}  # Allow None for non-required fields
        
        try:
            if expected_type == 'int':
                int(value)
            elif expected_type == 'float':
                float(value)
            elif expected_type == 'decimal':
                Decimal(str(value))
            elif expected_type == 'str':
                str(value)
            elif expected_type == 'bool':
                if str(value).lower() not in ['true', 'false', '1', '0', 'yes', 'no']:
                    raise ValueError("Invalid boolean value")
            elif expected_type == 'date':
                if isinstance(value, str):
                    datetime.strptime(value, rule.parameters.get('format', '%Y-%m-%d'))
            else:
                return {'valid': False, 'message': f"Unknown type: {expected_type}"}
            
            return {'valid': True, 'message': ''}
            
        except (ValueError, InvalidOperation):
            return {'valid': False, 'message': rule.error_message}
    
    def _validate_range(self, value: Any, rule: ValidationRule) -> Dict[str, Any]:
        """Validate numeric range."""
        if value is None:
            return {'valid': True, 'message': ''}
        
        try:
            num_value = float(value)
            min_val = rule.parameters.get('min')
            max_val = rule.parameters.get('max')
            
            if min_val is not None and num_value < min_val:
                return {'valid': False, 'message': rule.error_message}
            
            if max_val is not None and num_value > max_val:
                return {'valid': False, 'message': rule.error_message}
            
            return {'valid': True, 'message': ''}
            
        except (ValueError, TypeError):
            return {'valid': False, 'message': "Value must be numeric for range validation"}
    
    def _validate_length(self, value: Any, rule: ValidationRule) -> Dict[str, Any]:
        """Validate string length."""
        if value is None:
            return {'valid': True, 'message': ''}
        
        str_value = str(value)
        min_len = rule.parameters.get('min')
        max_len = rule.parameters.get('max')
        
        if min_len is not None and len(str_value) < min_len:
            return {'valid': False, 'message': rule.error_message}
        
        if max_len is not None and len(str_value) > max_len:
            return {'valid': False, 'message': rule.error_message}
        
        return {'valid': True, 'message': ''}
    
    def _validate_pattern(self, value: Any, rule: ValidationRule) -> Dict[str, Any]:
        """Validate regex pattern."""
        if value is None:
            return {'valid': True, 'message': ''}
        
        pattern = rule.parameters.get('pattern')
        if not pattern:
            return {'valid': False, 'message': "Pattern not specified"}
        
        try:
            if re.match(pattern, str(value)):
                return {'valid': True, 'message': ''}
            else:
                return {'valid': False, 'message': rule.error_message}
        except re.error:
            return {'valid': False, 'message': f"Invalid regex pattern: {pattern}"}
    
    def _validate_enum(self, value: Any, rule: ValidationRule) -> Dict[str, Any]:
        """Validate enumerated values."""
        if value is None:
            return {'valid': True, 'message': ''}
        
        allowed_values = rule.parameters.get('values', [])
        if value in allowed_values:
            return {'valid': True, 'message': ''}
        else:
            return {'valid': False, 'message': rule.error_message}
    
    def _validate_date_format(self, value: Any, rule: ValidationRule) -> Dict[str, Any]:
        """Validate date format."""
        if value is None:
            return {'valid': True, 'message': ''}
        
        date_format = rule.parameters.get('format', '%Y-%m-%d')
        
        try:
            datetime.strptime(str(value), date_format)
            return {'valid': True, 'message': ''}
        except ValueError:
            return {'valid': False, 'message': rule.error_message}
    
    def _validate_currency(self, value: Any, rule: ValidationRule) -> Dict[str, Any]:
        """Validate currency format."""
        if value is None:
            return {'valid': True, 'message': ''}
        
        # Remove currency symbols and commas
        cleaned_value = str(value).replace('$', '').replace(',', '').strip()
        
        try:
            float(cleaned_value)
            return {'valid': True, 'message': ''}
        except ValueError:
            return {'valid': False, 'message': rule.error_message}
    
    def _validate_email(self, value: Any, rule: ValidationRule) -> Dict[str, Any]:
        """Validate email format."""
        if value is None:
            return {'valid': True, 'message': ''}
        
        email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        
        if re.match(email_pattern, str(value)):
            return {'valid': True, 'message': ''}
        else:
            return {'valid': False, 'message': rule.error_message}
    
    def _validate_phone(self, value: Any, rule: ValidationRule) -> Dict[str, Any]:
        """Validate phone number format."""
        if value is None:
            return {'valid': True, 'message': ''}
        
        # Basic phone validation - can be customized based on requirements
        phone_pattern = r'^[\+]?[1-9][\d]{0,15}$'  # International format
        
        # Clean phone number
        cleaned_phone = re.sub(r'[^\d\+]', '', str(value))
        
        if re.match(phone_pattern, cleaned_phone):
            return {'valid': True, 'message': ''}
        else:
            return {'valid': False, 'message': rule.error_message}
    
    def _validate_custom(self, value: Any, rule: ValidationRule, record: Dict[str, Any]) -> Dict[str, Any]:
        """Apply custom validation logic."""
        custom_function = rule.parameters.get('function')
        if not custom_function:
            return {'valid': False, 'message': "Custom function not specified"}
        
        try:
            # Custom functions should be registered in the config
            if custom_function in self.config.get('custom_validators', {}):
                validator_func = self.config['custom_validators'][custom_function]
                result = validator_func(value, rule.parameters, record)
                
                if isinstance(result, bool):
                    return {'valid': result, 'message': rule.error_message if not result else ''}
                elif isinstance(result, dict):
                    return result
                else:
                    return {'valid': False, 'message': "Custom validator returned invalid result"}
            else:
                return {'valid': False, 'message': f"Custom validator not found: {custom_function}"}
                
        except Exception as e:
            return {'valid': False, 'message': f"Custom validation error: {str(e)}"}
    
    def _validate_schema(self, source: str, record: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Validate against JSON schema if available."""
        schema = self._get_schema(source)
        if not schema:
            return []
        
        try:
            jsonschema.validate(record, schema)
            return []
            
        except jsonschema.ValidationError as e:
            return [{
                'field': e.path[-1] if e.path else '__root__',
                'rule': 'schema',
                'message': e.message,
                'value': record.get(e.path[-1]) if e.path else None
            }]
        except Exception as e:
            return [{
                'field': '__schema__',
                'rule': 'schema_error',
                'message': f"Schema validation error: {str(e)}",
                'value': None
            }]
    
    def _validate_business_logic(self, source: str, record: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Apply source-specific business logic validation."""
        errors = []
        
        try:
            if source in ['pos', 'api_sales']:
                errors.extend(self._validate_sales_business_logic(record))
            elif source == 'inventory':
                errors.extend(self._validate_inventory_business_logic(record))
            elif source == 'staff':
                errors.extend(self._validate_staff_business_logic(record))
                
        except Exception as e:
            logger.error(f"Error in business logic validation for {source}: {e}")
            errors.append({
                'field': '__business_logic__',
                'rule': 'business_logic_error',
                'message': f"Business logic validation error: {str(e)}",
                'value': None
            })
        
        return errors
    
    def _validate_sales_business_logic(self, record: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Validate sales-specific business logic."""
        errors = []
        
        # Example: Validate that total amount matches item prices * quantities
        try:
            quantity = float(record.get('quantity', 0))
            price = float(record.get('price', 0))
            total = float(record.get('total_amount', 0))
            
            expected_total = quantity * price
            if abs(total - expected_total) > 0.01:  # Allow for rounding
                errors.append({
                    'field': 'total_amount',
                    'rule': 'business_logic',
                    'message': f"Total amount {total} doesn't match quantity × price ({expected_total})",
                    'value': total
                })
                
        except (ValueError, TypeError):
            # Let type validation handle this
            pass
        
        # Example: Validate reasonable quantity ranges
        try:
            quantity = float(record.get('quantity', 0))
            if quantity > 1000:  # Configurable threshold
                errors.append({
                    'field': 'quantity',
                    'rule': 'business_logic',
                    'message': f"Unusually high quantity: {quantity}",
                    'value': quantity
                })
        except (ValueError, TypeError):
            pass
        
        return errors
    
    def _validate_inventory_business_logic(self, record: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Validate inventory-specific business logic."""
        errors = []
        
        # Example: Validate stock levels
        try:
            stock_level = float(record.get('current_stock', 0))
            if stock_level < 0:
                errors.append({
                    'field': 'current_stock',
                    'rule': 'business_logic',
                    'message': "Stock level cannot be negative",
                    'value': stock_level
                })
        except (ValueError, TypeError):
            pass
        
        return errors
    
    def _validate_staff_business_logic(self, record: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Validate staff-specific business logic."""
        errors = []
        
        # Example: Validate work hours
        try:
            hours_worked = float(record.get('hours_worked', 0))
            if hours_worked > 16:  # More than 16 hours in a day seems unusual
                errors.append({
                    'field': 'hours_worked',
                    'rule': 'business_logic',
                    'message': f"Unusually high work hours: {hours_worked}",
                    'value': hours_worked
                })
        except (ValueError, TypeError):
            pass
        
        return errors
    
    def _load_validation_rules(self) -> Dict[str, List[ValidationRule]]:
        """Load validation rules from configuration."""
        # Default validation rules for different sources
        default_rules = {
            'pos': [
                ValidationRule('order_id', 'required', {}, "Order ID is required"),
                ValidationRule('item_id', 'required', {}, "Item ID is required"),
                ValidationRule('quantity', 'type', {'type': 'int'}, "Quantity must be an integer"),
                ValidationRule('quantity', 'range', {'min': 1, 'max': 1000}, "Quantity must be between 1 and 1000"),
                ValidationRule('price', 'type', {'type': 'decimal'}, "Price must be a valid decimal"),
                ValidationRule('price', 'range', {'min': 0, 'max': 10000}, "Price must be between 0 and 10000"),
                ValidationRule('sale_time', 'date_format', {'format': '%Y-%m-%d %H:%M:%S'}, "Invalid sale time format"),
            ],
            'csv_upload': [
                ValidationRule('uploaded_at', 'required', {}, "Upload timestamp is required"),
            ],
            'api': [
                ValidationRule('timestamp', 'required', {}, "Timestamp is required"),
            ]
        }
        
        # Merge with custom rules from config
        custom_rules = self.config.get('validation_rules', {})
        
        for source, rules in custom_rules.items():
            rule_objects = []
            for rule_config in rules:
                rule_objects.append(ValidationRule(
                    field=rule_config['field'],
                    rule_type=rule_config['rule_type'],
                    parameters=rule_config.get('parameters', {}),
                    error_message=rule_config['error_message'],
                    severity=rule_config.get('severity', 'error')
                ))
            default_rules[source] = rule_objects
        
        return default_rules
    
    def _get_schema(self, source: str) -> Optional[Dict[str, Any]]:
        """Get JSON schema for source."""
        if source in self.schema_cache:
            return self.schema_cache[source]
        
        # Load schema from config or file
        schemas = self.config.get('schemas', {})
        schema = schemas.get(source)
        
        if schema:
            self.schema_cache[source] = schema
        
        return schema
    
    def _generate_validation_summary(self, batch_results: Dict[str, Any]) -> Dict[str, Any]:
        """Generate summary statistics for batch validation."""
        error_counts = {}
        warning_counts = {}
        
        for record_result in batch_results['validation_details']:
            for error in record_result['errors']:
                key = f"{error['field']}:{error['rule']}"
                error_counts[key] = error_counts.get(key, 0) + 1
            
            for warning in record_result['warnings']:
                key = f"{warning['field']}:{warning['rule']}"
                warning_counts[key] = warning_counts.get(key, 0) + 1
        
        return {
            'error_rate': batch_results['invalid_records'] / batch_results['total_records'] * 100,
            'warning_rate': batch_results['warnings'] / batch_results['total_records'] * 100,
            'most_common_errors': sorted(error_counts.items(), key=lambda x: x[1], reverse=True)[:5],
            'most_common_warnings': sorted(warning_counts.items(), key=lambda x: x[1], reverse=True)[:5]
        }