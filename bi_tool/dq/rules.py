"""
Data Quality Rule Registry and Rule Definitions
Manages rule registration, loading from manifests, and rule validation.
"""

import yaml
import json
import logging
from typing import Dict, List, Optional, Any
from django.core.exceptions import ValidationError
from django.conf import settings
from django.utils import timezone
from pathlib import Path
from .models import DQRule, DQCheckType, DQSeverity

logger = logging.getLogger(__name__)


class DQRuleRegistry:
    """Registry for data quality rules and rule templates."""
    
    def __init__(self):
        self._rules = {}
        self._templates = {}
        self._validators = {}
        self._loaded = False
    
    def register_rule_validator(self, check_type: str, validator_func):
        """Register a validator function for a specific check type."""
        self._validators[check_type] = validator_func
    
    def validate_rule_config(self, rule_config: Dict[str, Any]) -> List[str]:
        """Validate rule configuration and return list of errors."""
        errors = []
        
        # Required fields
        required_fields = ['name', 'check_type', 'target_collection', 'threshold', 'severity']
        for field in required_fields:
            if field not in rule_config:
                errors.append(f"Missing required field: {field}")
        
        # Check type validation
        if 'check_type' in rule_config:
            if rule_config['check_type'] not in [choice[0] for choice in DQCheckType.choices]:
                errors.append(f"Invalid check_type: {rule_config['check_type']}")
            
            # Use specific validator if available
            validator = self._validators.get(rule_config['check_type'])
            if validator:
                try:
                    validator_errors = validator(rule_config)
                    errors.extend(validator_errors)
                except Exception as e:
                    errors.append(f"Validator error: {str(e)}")
        
        # Severity validation
        if 'severity' in rule_config:
            if rule_config['severity'] not in [choice[0] for choice in DQSeverity.choices]:
                errors.append(f"Invalid severity: {rule_config['severity']}")
        
        # Threshold validation
        if 'threshold' in rule_config:
            try:
                float(rule_config['threshold'])
            except (ValueError, TypeError):
                errors.append("Threshold must be a number")
        
        # Schedule validation (basic cron format check)
        if 'schedule' in rule_config:
            schedule_parts = rule_config['schedule'].split()
            if len(schedule_parts) != 5:
                errors.append("Schedule must be in cron format (5 fields)")
        
        return errors
    
    def load_rules_from_manifest(self, manifest_path: str) -> Dict[str, Any]:
        """Load rules from YAML manifest file."""
        try:
            manifest_file = Path(manifest_path)
            if not manifest_file.exists():
                logger.error(f"Manifest file not found: {manifest_path}")
                return {"loaded": 0, "errors": [f"File not found: {manifest_path}"]}
            
            with open(manifest_file, 'r', encoding='utf-8') as f:
                manifest_data = yaml.safe_load(f)
            
            if not isinstance(manifest_data, dict) or 'rules' not in manifest_data:
                return {"loaded": 0, "errors": ["Invalid manifest format: missing 'rules' section"]}
            
            results = {"loaded": 0, "skipped": 0, "errors": []}
            
            for rule_config in manifest_data['rules']:
                try:
                    # Validate rule configuration
                    validation_errors = self.validate_rule_config(rule_config)
                    if validation_errors:
                        results["errors"].extend([f"Rule {rule_config.get('name', 'unknown')}: {err}" for err in validation_errors])
                        results["skipped"] += 1
                        continue
                    
                    # Create or update rule
                    rule, created = self.create_or_update_rule(rule_config)
                    if created:
                        results["loaded"] += 1
                        logger.info(f"Created rule: {rule.name}")
                    else:
                        logger.info(f"Updated rule: {rule.name}")
                
                except Exception as e:
                    error_msg = f"Error processing rule {rule_config.get('name', 'unknown')}: {str(e)}"
                    results["errors"].append(error_msg)
                    results["skipped"] += 1
                    logger.error(error_msg)
            
            return results
            
        except Exception as e:
            error_msg = f"Error loading manifest {manifest_path}: {str(e)}"
            logger.error(error_msg)
            return {"loaded": 0, "errors": [error_msg]}
    
    def create_or_update_rule(self, rule_config: Dict[str, Any]) -> tuple:
        """Create or update a DQ rule from configuration."""
        rule_name = rule_config['name']
        
        # Prepare rule data
        rule_data = {
            'name': rule_name,
            'description': rule_config.get('description', ''),
            'check_type': rule_config['check_type'],
            'target_database': rule_config.get('target_database', 'mongodb'),
            'target_collection': rule_config['target_collection'],
            'target_column': rule_config.get('target_column'),
            'threshold': float(rule_config['threshold']),
            'severity': rule_config['severity'],
            'schedule': rule_config.get('schedule', '0 */4 * * *'),  # Default: every 4 hours
            'enabled': rule_config.get('enabled', True),
            'owners': rule_config.get('owners', []),
            'tags': rule_config.get('tags', []),
            'query': rule_config.get('query'),
            'parameters': rule_config.get('parameters', {}),
            'timeout_seconds': rule_config.get('timeout_seconds', 300),
            'sample_size': rule_config.get('sample_size', 100),
            'use_sampling': rule_config.get('use_sampling', True),
        }
        
        # Create or update
        rule, created = DQRule.objects.update_or_create(
            name=rule_name,
            defaults=rule_data
        )
        
        return rule, created
    
    def export_rules_to_manifest(self, output_path: str, rule_filter: Optional[Dict] = None) -> bool:
        """Export existing rules to YAML manifest."""
        try:
            queryset = DQRule.objects.all()
            
            # Apply filters
            if rule_filter:
                if 'enabled' in rule_filter:
                    queryset = queryset.filter(enabled=rule_filter['enabled'])
                if 'check_type' in rule_filter:
                    queryset = queryset.filter(check_type=rule_filter['check_type'])
                if 'severity' in rule_filter:
                    queryset = queryset.filter(severity=rule_filter['severity'])
            
            rules_data = []
            for rule in queryset:
                rule_config = {
                    'name': rule.name,
                    'description': rule.description,
                    'check_type': rule.check_type,
                    'target_database': rule.target_database,
                    'target_collection': rule.target_collection,
                    'threshold': rule.threshold,
                    'severity': rule.severity,
                    'schedule': rule.schedule,
                    'enabled': rule.enabled,
                    'owners': rule.owners,
                    'tags': rule.tags,
                    'timeout_seconds': rule.timeout_seconds,
                    'sample_size': rule.sample_size,
                    'use_sampling': rule.use_sampling,
                }
                
                # Optional fields
                if rule.target_column:
                    rule_config['target_column'] = rule.target_column
                if rule.query:
                    rule_config['query'] = rule.query
                if rule.parameters:
                    rule_config['parameters'] = rule.parameters
                
                rules_data.append(rule_config)
            
            # Create manifest structure
            manifest_data = {
                'version': '1.0',
                'metadata': {
                    'description': 'Data Quality Rules Manifest',
                    'exported_at': str(timezone.now()),
                    'total_rules': len(rules_data)
                },
                'rules': rules_data
            }
            
            # Write to file
            with open(output_path, 'w', encoding='utf-8') as f:
                yaml.dump(manifest_data, f, default_flow_style=False, sort_keys=False, indent=2)
            
            logger.info(f"Exported {len(rules_data)} rules to {output_path}")
            return True
            
        except Exception as e:
            logger.error(f"Error exporting rules to manifest: {str(e)}")
            return False
    
    def get_rule_suggestions(self, target_collection: str, target_database: str = 'mongodb') -> List[Dict]:
        """Get rule suggestions based on data analysis."""
        suggestions = []
        
        try:
            # Analyze collection/table structure and suggest common rules
            if target_database == 'mongodb':
                suggestions.extend(self._get_mongodb_suggestions(target_collection))
            elif target_database in ['postgres', 'clickhouse']:
                suggestions.extend(self._get_sql_suggestions(target_collection, target_database))
            
        except Exception as e:
            logger.error(f"Error generating rule suggestions: {str(e)}")
        
        return suggestions
    
    def _get_mongodb_suggestions(self, collection_name: str) -> List[Dict]:
        """Generate rule suggestions for MongoDB collection."""
        suggestions = []
        
        try:
            from djongo import models
            from django.db import connections
            
            # Get sample documents to analyze structure
            # This would require connecting to MongoDB and analyzing the collection
            # For now, return common patterns based on collection name
            
            if 'sales' in collection_name.lower():
                suggestions.extend([
                    {
                        'name': f'{collection_name}_total_amount_not_null',
                        'check_type': 'null_rate',
                        'target_column': 'total_amount',
                        'threshold': 0.01,
                        'severity': 'CRITICAL',
                        'description': 'Total amount should not be null in sales records'
                    },
                    {
                        'name': f'{collection_name}_positive_amounts',
                        'check_type': 'range_check',
                        'target_column': 'total_amount',
                        'threshold': 0,
                        'severity': 'CRITICAL',
                        'description': 'Total amount should be positive'
                    }
                ])
            
            if 'inventory' in collection_name.lower():
                suggestions.append({
                    'name': f'{collection_name}_stock_levels',
                    'check_type': 'range_check',
                    'target_column': 'current_stock',
                    'threshold': 0,
                    'severity': 'WARN',
                    'description': 'Stock levels should not be negative'
                })
            
        except Exception as e:
            logger.warning(f"Error analyzing MongoDB collection {collection_name}: {str(e)}")
        
        return suggestions
    
    def _get_sql_suggestions(self, table_name: str, database_type: str) -> List[Dict]:
        """Generate rule suggestions for SQL table."""
        suggestions = []
        
        # Common SQL-based suggestions
        suggestions.extend([
            {
                'name': f'{table_name}_row_count_check',
                'check_type': 'row_count',
                'threshold': 1,
                'severity': 'CRITICAL',
                'description': f'Table {table_name} should not be empty'
            },
            {
                'name': f'{table_name}_primary_key_uniqueness',
                'check_type': 'uniqueness',
                'target_column': 'id',
                'threshold': 0,
                'severity': 'CRITICAL',
                'description': f'Primary key should be unique in {table_name}'
            }
        ])
        
        return suggestions


# Rule-specific validators
def validate_null_rate_rule(rule_config: Dict[str, Any]) -> List[str]:
    """Validate null rate rule configuration."""
    errors = []
    
    if 'target_column' not in rule_config:
        errors.append("null_rate check requires 'target_column'")
    
    if 'threshold' in rule_config:
        threshold = rule_config['threshold']
        if threshold < 0 or threshold > 1:
            errors.append("null_rate threshold should be between 0 and 1")
    
    return errors


def validate_range_check_rule(rule_config: Dict[str, Any]) -> List[str]:
    """Validate range check rule configuration."""
    errors = []
    
    if 'target_column' not in rule_config:
        errors.append("range_check requires 'target_column'")
    
    parameters = rule_config.get('parameters', {})
    if 'min_value' not in parameters and 'max_value' not in parameters:
        errors.append("range_check requires at least min_value or max_value in parameters")
    
    return errors


def validate_uniqueness_rule(rule_config: Dict[str, Any]) -> List[str]:
    """Validate uniqueness rule configuration."""
    errors = []
    
    if 'target_column' not in rule_config and 'query' not in rule_config:
        errors.append("uniqueness check requires 'target_column' or custom 'query'")
    
    return errors


def validate_row_count_rule(rule_config: Dict[str, Any]) -> List[str]:
    """Validate row count rule configuration."""
    errors = []
    
    parameters = rule_config.get('parameters', {})
    if 'comparison' in parameters:
        valid_comparisons = ['gt', 'gte', 'lt', 'lte', 'eq']
        if parameters['comparison'] not in valid_comparisons:
            errors.append(f"row_count comparison must be one of: {valid_comparisons}")
    
    return errors


# Global registry instance
dq_registry = DQRuleRegistry()

# Register validators
dq_registry.register_rule_validator('null_rate', validate_null_rate_rule)
dq_registry.register_rule_validator('range_check', validate_range_check_rule)
dq_registry.register_rule_validator('uniqueness', validate_uniqueness_rule)
dq_registry.register_rule_validator('row_count', validate_row_count_rule)