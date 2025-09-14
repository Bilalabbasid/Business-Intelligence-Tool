"""
Data Warehouse Management Utilities for ETL Processing
"""

import logging
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Any, Optional, Union
from decimal import Decimal
import pandas as pd
from sqlalchemy import create_engine, text, MetaData, Table, inspect
from sqlalchemy.orm import sessionmaker
from django.conf import settings
import clickhouse_connect

logger = logging.getLogger(__name__)


class WarehouseManager:
    """
    Comprehensive data warehouse management for ETL processes.
    Handles aggregation, fact/dimension table operations, and data warehouse maintenance.
    """
    
    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or {}
        self.warehouse_type = self.config.get('warehouse_type', 'postgresql')
        self.connection = None
        self.session = None
        self.aggregation_rules = self._load_aggregation_rules()
    
    def connect(self):
        """Establish connection to data warehouse."""
        try:
            if self.warehouse_type == 'postgresql':
                self._connect_postgresql()
            elif self.warehouse_type == 'clickhouse':
                self._connect_clickhouse()
            else:
                raise ValueError(f"Unsupported warehouse type: {self.warehouse_type}")
                
            logger.info(f"Connected to {self.warehouse_type} warehouse")
            
        except Exception as e:
            logger.error(f"Failed to connect to warehouse: {e}")
            raise
    
    def disconnect(self):
        """Close warehouse connection."""
        try:
            if self.session:
                self.session.close()
            if self.connection:
                self.connection.close()
            logger.info("Disconnected from warehouse")
        except Exception as e:
            logger.error(f"Error disconnecting from warehouse: {e}")
    
    def aggregate_data(self, source: str, date_range: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
        """
        Aggregate raw data for data warehouse.
        
        Args:
            source: Data source name
            date_range: Optional date range filter
            
        Returns:
            Aggregation results
        """
        try:
            results = {
                'source': source,
                'aggregation_started': datetime.now().isoformat(),
                'total_processed': 0,
                'tables_updated': [],
                'errors': []
            }
            
            # Get aggregation rules for source
            source_rules = self.aggregation_rules.get(source, [])
            
            for rule in source_rules:
                try:
                    logger.info(f"Processing aggregation rule: {rule['name']}")
                    
                    # Execute aggregation
                    rule_result = self._execute_aggregation_rule(rule, date_range)
                    
                    results['tables_updated'].append({
                        'rule_name': rule['name'],
                        'target_table': rule['target_table'],
                        'records_processed': rule_result.get('records_processed', 0),
                        'records_inserted': rule_result.get('records_inserted', 0),
                        'records_updated': rule_result.get('records_updated', 0)
                    })
                    
                    results['total_processed'] += rule_result.get('records_processed', 0)
                    
                except Exception as e:
                    logger.error(f"Error in aggregation rule {rule['name']}: {e}")
                    results['errors'].append({
                        'rule_name': rule['name'],
                        'error': str(e)
                    })
            
            results['aggregation_completed'] = datetime.now().isoformat()
            return results
            
        except Exception as e:
            logger.error(f"Error in data aggregation: {e}")
            raise
    
    def create_fact_table_entry(self, fact_type: str, data: Dict[str, Any]) -> bool:
        """
        Create entry in fact table.
        
        Args:
            fact_type: Type of fact table (sales, inventory, etc.)
            data: Fact data
            
        Returns:
            Success status
        """
        try:
            if fact_type == 'sales':
                return self._create_sales_fact(data)
            elif fact_type == 'inventory':
                return self._create_inventory_fact(data)
            elif fact_type == 'staff_performance':
                return self._create_staff_performance_fact(data)
            else:
                logger.warning(f"Unknown fact type: {fact_type}")
                return False
                
        except Exception as e:
            logger.error(f"Error creating fact table entry: {e}")
            return False
    
    def update_dimension_tables(self, dimension_updates: Dict[str, List[Dict[str, Any]]]) -> Dict[str, Any]:
        """
        Update dimension tables with new/changed data.
        
        Args:
            dimension_updates: Dictionary of dimension table updates
            
        Returns:
            Update results
        """
        results = {
            'updated_dimensions': [],
            'total_records': 0,
            'errors': []
        }
        
        try:
            for dimension_name, records in dimension_updates.items():
                try:
                    result = self._update_dimension_table(dimension_name, records)
                    results['updated_dimensions'].append({
                        'dimension': dimension_name,
                        'records_processed': len(records),
                        'records_inserted': result.get('inserted', 0),
                        'records_updated': result.get('updated', 0)
                    })
                    results['total_records'] += len(records)
                    
                except Exception as e:
                    logger.error(f"Error updating dimension {dimension_name}: {e}")
                    results['errors'].append({
                        'dimension': dimension_name,
                        'error': str(e)
                    })
            
            return results
            
        except Exception as e:
            logger.error(f"Error updating dimension tables: {e}")
            raise
    
    def execute_warehouse_maintenance(self) -> Dict[str, Any]:
        """
        Execute routine warehouse maintenance tasks.
        
        Returns:
            Maintenance results
        """
        results = {
            'maintenance_started': datetime.now().isoformat(),
            'tasks_completed': [],
            'errors': []
        }
        
        try:
            # Update statistics
            self._update_table_statistics()
            results['tasks_completed'].append('table_statistics')
            
            # Rebuild indexes
            self._rebuild_indexes()
            results['tasks_completed'].append('index_rebuild')
            
            # Partition maintenance
            self._maintain_partitions()
            results['tasks_completed'].append('partition_maintenance')
            
            # Cleanup old data
            self._cleanup_old_data()
            results['tasks_completed'].append('data_cleanup')
            
            results['maintenance_completed'] = datetime.now().isoformat()
            return results
            
        except Exception as e:
            logger.error(f"Error in warehouse maintenance: {e}")
            results['errors'].append(str(e))
            return results
    
    def _connect_postgresql(self):
        """Connect to PostgreSQL warehouse."""
        from django.db import connections
        
        # Use Django's database connection for PostgreSQL
        warehouse_db = connections['warehouse'] if 'warehouse' in connections else connections['default']
        
        # Create SQLAlchemy engine for advanced operations
        db_settings = warehouse_db.settings_dict
        connection_string = (
            f"postgresql://{db_settings['USER']}:{db_settings['PASSWORD']}"
            f"@{db_settings['HOST']}:{db_settings['PORT']}/{db_settings['NAME']}"
        )
        
        engine = create_engine(connection_string)
        Session = sessionmaker(bind=engine)
        
        self.connection = engine
        self.session = Session()
    
    def _connect_clickhouse(self):
        """Connect to ClickHouse warehouse."""
        host = self.config.get('clickhouse_host', 'localhost')
        port = self.config.get('clickhouse_port', 8123)
        username = self.config.get('clickhouse_username', 'default')
        password = self.config.get('clickhouse_password', '')
        database = self.config.get('clickhouse_database', 'warehouse')
        
        self.connection = clickhouse_connect.get_client(
            host=host,
            port=port,
            username=username,
            password=password,
            database=database
        )
    
    def _execute_aggregation_rule(self, rule: Dict[str, Any], date_range: Optional[Dict[str, str]]) -> Dict[str, Any]:
        """Execute a single aggregation rule."""
        source_table = rule['source_table']
        target_table = rule['target_table']
        aggregation_type = rule['aggregation_type']
        
        # Build aggregation query
        if aggregation_type == 'daily_sales':
            return self._aggregate_daily_sales(rule, date_range)
        elif aggregation_type == 'monthly_sales':
            return self._aggregate_monthly_sales(rule, date_range)
        elif aggregation_type == 'inventory_snapshot':
            return self._aggregate_inventory_snapshot(rule, date_range)
        elif aggregation_type == 'staff_performance':
            return self._aggregate_staff_performance(rule, date_range)
        else:
            # Generic aggregation
            return self._generic_aggregation(rule, date_range)
    
    def _aggregate_daily_sales(self, rule: Dict[str, Any], date_range: Optional[Dict[str, str]]) -> Dict[str, Any]:
        """Aggregate daily sales data."""
        try:
            # Build date filter
            date_filter = ""
            if date_range:
                start_date = date_range.get('start_date')
                end_date = date_range.get('end_date')
                if start_date and end_date:
                    date_filter = f"AND event_timestamp >= '{start_date}' AND event_timestamp < '{end_date}'"
            
            if self.warehouse_type == 'postgresql':
                query = f"""
                INSERT INTO {rule['target_table']} 
                (date_key, branch_id, total_sales, total_transactions, avg_transaction_value, created_at)
                SELECT 
                    DATE(event_timestamp) as date_key,
                    branch_id,
                    SUM(CAST(total_amount AS DECIMAL)) as total_sales,
                    COUNT(*) as total_transactions,
                    AVG(CAST(total_amount AS DECIMAL)) as avg_transaction_value,
                    NOW() as created_at
                FROM raw_events 
                WHERE _source IN ('pos', 'api_sales')
                {date_filter}
                GROUP BY DATE(event_timestamp), branch_id
                ON CONFLICT (date_key, branch_id) 
                DO UPDATE SET 
                    total_sales = EXCLUDED.total_sales,
                    total_transactions = EXCLUDED.total_transactions,
                    avg_transaction_value = EXCLUDED.avg_transaction_value,
                    updated_at = NOW()
                """
            else:  # ClickHouse
                query = f"""
                INSERT INTO {rule['target_table']} 
                SELECT 
                    toDate(event_timestamp) as date_key,
                    branch_id,
                    sum(toDecimal64(total_amount, 2)) as total_sales,
                    count(*) as total_transactions,
                    avg(toDecimal64(total_amount, 2)) as avg_transaction_value,
                    now() as created_at
                FROM raw_events 
                WHERE _source IN ('pos', 'api_sales')
                {date_filter}
                GROUP BY date_key, branch_id
                """
            
            result = self._execute_query(query)
            
            return {
                'records_processed': result.get('rowcount', 0),
                'records_inserted': result.get('rowcount', 0),
                'records_updated': 0
            }
            
        except Exception as e:
            logger.error(f"Error in daily sales aggregation: {e}")
            raise
    
    def _aggregate_monthly_sales(self, rule: Dict[str, Any], date_range: Optional[Dict[str, str]]) -> Dict[str, Any]:
        """Aggregate monthly sales data."""
        try:
            date_filter = ""
            if date_range:
                start_date = date_range.get('start_date')
                end_date = date_range.get('end_date')
                if start_date and end_date:
                    date_filter = f"AND event_timestamp >= '{start_date}' AND event_timestamp < '{end_date}'"
            
            if self.warehouse_type == 'postgresql':
                query = f"""
                INSERT INTO {rule['target_table']} 
                (month_key, branch_id, total_sales, total_transactions, unique_customers, created_at)
                SELECT 
                    DATE_TRUNC('month', event_timestamp) as month_key,
                    branch_id,
                    SUM(CAST(total_amount AS DECIMAL)) as total_sales,
                    COUNT(*) as total_transactions,
                    COUNT(DISTINCT customer_id) as unique_customers,
                    NOW() as created_at
                FROM raw_events 
                WHERE _source IN ('pos', 'api_sales')
                {date_filter}
                GROUP BY DATE_TRUNC('month', event_timestamp), branch_id
                ON CONFLICT (month_key, branch_id) 
                DO UPDATE SET 
                    total_sales = EXCLUDED.total_sales,
                    total_transactions = EXCLUDED.total_transactions,
                    unique_customers = EXCLUDED.unique_customers,
                    updated_at = NOW()
                """
            else:  # ClickHouse
                query = f"""
                INSERT INTO {rule['target_table']} 
                SELECT 
                    toStartOfMonth(event_timestamp) as month_key,
                    branch_id,
                    sum(toDecimal64(total_amount, 2)) as total_sales,
                    count(*) as total_transactions,
                    uniq(customer_id) as unique_customers,
                    now() as created_at
                FROM raw_events 
                WHERE _source IN ('pos', 'api_sales')
                {date_filter}
                GROUP BY month_key, branch_id
                """
            
            result = self._execute_query(query)
            
            return {
                'records_processed': result.get('rowcount', 0),
                'records_inserted': result.get('rowcount', 0),
                'records_updated': 0
            }
            
        except Exception as e:
            logger.error(f"Error in monthly sales aggregation: {e}")
            raise
    
    def _aggregate_inventory_snapshot(self, rule: Dict[str, Any], date_range: Optional[Dict[str, str]]) -> Dict[str, Any]:
        """Aggregate inventory snapshot data."""
        try:
            # Create daily inventory snapshots
            if self.warehouse_type == 'postgresql':
                query = f"""
                INSERT INTO {rule['target_table']} 
                (snapshot_date, branch_id, product_id, current_stock, min_stock, max_stock, stock_value, created_at)
                SELECT DISTINCT ON (DATE(event_timestamp), branch_id, product_id)
                    DATE(event_timestamp) as snapshot_date,
                    branch_id,
                    product_id,
                    CAST(current_stock AS INTEGER),
                    CAST(min_stock AS INTEGER),
                    CAST(max_stock AS INTEGER),
                    CAST(current_stock AS INTEGER) * CAST(unit_price AS DECIMAL) as stock_value,
                    NOW() as created_at
                FROM raw_events 
                WHERE _source = 'inventory'
                AND event_timestamp >= CURRENT_DATE - INTERVAL '7 days'
                ORDER BY DATE(event_timestamp), branch_id, product_id, event_timestamp DESC
                ON CONFLICT (snapshot_date, branch_id, product_id) 
                DO UPDATE SET 
                    current_stock = EXCLUDED.current_stock,
                    stock_value = EXCLUDED.stock_value,
                    updated_at = NOW()
                """
            else:  # ClickHouse
                query = f"""
                INSERT INTO {rule['target_table']} 
                SELECT 
                    toDate(event_timestamp) as snapshot_date,
                    branch_id,
                    product_id,
                    argMax(toInt32(current_stock), event_timestamp) as current_stock,
                    argMax(toInt32(min_stock), event_timestamp) as min_stock,
                    argMax(toInt32(max_stock), event_timestamp) as max_stock,
                    argMax(toInt32(current_stock), event_timestamp) * argMax(toDecimal64(unit_price, 2), event_timestamp) as stock_value,
                    now() as created_at
                FROM raw_events 
                WHERE _source = 'inventory'
                AND event_timestamp >= today() - 7
                GROUP BY snapshot_date, branch_id, product_id
                """
            
            result = self._execute_query(query)
            
            return {
                'records_processed': result.get('rowcount', 0),
                'records_inserted': result.get('rowcount', 0),
                'records_updated': 0
            }
            
        except Exception as e:
            logger.error(f"Error in inventory snapshot aggregation: {e}")
            raise
    
    def _aggregate_staff_performance(self, rule: Dict[str, Any], date_range: Optional[Dict[str, str]]) -> Dict[str, Any]:
        """Aggregate staff performance data."""
        try:
            if self.warehouse_type == 'postgresql':
                query = f"""
                INSERT INTO {rule['target_table']} 
                (date_key, staff_id, branch_id, total_sales, transaction_count, hours_worked, sales_per_hour, created_at)
                SELECT 
                    DATE(s.event_timestamp) as date_key,
                    s.staff_id,
                    s.branch_id,
                    COALESCE(SUM(CAST(s.total_amount AS DECIMAL)), 0) as total_sales,
                    COALESCE(COUNT(s.transaction_id), 0) as transaction_count,
                    COALESCE(MAX(CAST(h.hours_worked AS DECIMAL)), 8) as hours_worked,
                    CASE 
                        WHEN MAX(CAST(h.hours_worked AS DECIMAL)) > 0 
                        THEN SUM(CAST(s.total_amount AS DECIMAL)) / MAX(CAST(h.hours_worked AS DECIMAL))
                        ELSE 0 
                    END as sales_per_hour,
                    NOW() as created_at
                FROM raw_events s
                LEFT JOIN raw_events h ON DATE(s.event_timestamp) = DATE(h.event_timestamp) 
                    AND s.staff_id = h.staff_id AND h._source = 'staff'
                WHERE s._source IN ('pos', 'api_sales')
                AND s.staff_id IS NOT NULL
                GROUP BY DATE(s.event_timestamp), s.staff_id, s.branch_id
                ON CONFLICT (date_key, staff_id, branch_id) 
                DO UPDATE SET 
                    total_sales = EXCLUDED.total_sales,
                    transaction_count = EXCLUDED.transaction_count,
                    hours_worked = EXCLUDED.hours_worked,
                    sales_per_hour = EXCLUDED.sales_per_hour,
                    updated_at = NOW()
                """
            
            result = self._execute_query(query)
            
            return {
                'records_processed': result.get('rowcount', 0),
                'records_inserted': result.get('rowcount', 0),
                'records_updated': 0
            }
            
        except Exception as e:
            logger.error(f"Error in staff performance aggregation: {e}")
            raise
    
    def _generic_aggregation(self, rule: Dict[str, Any], date_range: Optional[Dict[str, str]]) -> Dict[str, Any]:
        """Execute generic aggregation based on rule configuration."""
        try:
            # Build query from rule configuration
            source_table = rule['source_table']
            target_table = rule['target_table']
            group_by_fields = rule.get('group_by', [])
            aggregation_fields = rule.get('aggregations', [])
            
            # Build SELECT clause
            select_fields = group_by_fields.copy()
            for agg in aggregation_fields:
                field = agg['field']
                function = agg['function']
                alias = agg.get('alias', f"{function}_{field}")
                select_fields.append(f"{function}({field}) as {alias}")
            
            select_clause = ", ".join(select_fields)
            group_clause = ", ".join(group_by_fields) if group_by_fields else ""
            
            # Build date filter
            date_filter = ""
            if date_range:
                start_date = date_range.get('start_date')
                end_date = date_range.get('end_date')
                if start_date and end_date:
                    date_filter = f"AND event_timestamp >= '{start_date}' AND event_timestamp < '{end_date}'"
            
            query = f"""
            INSERT INTO {target_table} 
            SELECT {select_clause}, NOW() as created_at
            FROM {source_table}
            WHERE 1=1 {date_filter}
            {f"GROUP BY {group_clause}" if group_clause else ""}
            """
            
            result = self._execute_query(query)
            
            return {
                'records_processed': result.get('rowcount', 0),
                'records_inserted': result.get('rowcount', 0),
                'records_updated': 0
            }
            
        except Exception as e:
            logger.error(f"Error in generic aggregation: {e}")
            raise
    
    def _create_sales_fact(self, data: Dict[str, Any]) -> bool:
        """Create sales fact table entry."""
        try:
            if self.warehouse_type == 'postgresql':
                query = """
                INSERT INTO fact_sales 
                (date_key, time_key, customer_key, product_key, staff_key, branch_key,
                 quantity, unit_price, discount, total_amount, cost, profit, created_at)
                VALUES (:date_key, :time_key, :customer_key, :product_key, :staff_key, :branch_key,
                        :quantity, :unit_price, :discount, :total_amount, :cost, :profit, NOW())
                """
                self.session.execute(text(query), data)
                self.session.commit()
            
            return True
            
        except Exception as e:
            logger.error(f"Error creating sales fact: {e}")
            return False
    
    def _create_inventory_fact(self, data: Dict[str, Any]) -> bool:
        """Create inventory fact table entry."""
        try:
            if self.warehouse_type == 'postgresql':
                query = """
                INSERT INTO fact_inventory 
                (date_key, product_key, branch_key, opening_stock, closing_stock, 
                 stock_received, stock_sold, stock_adjusted, created_at)
                VALUES (:date_key, :product_key, :branch_key, :opening_stock, :closing_stock,
                        :stock_received, :stock_sold, :stock_adjusted, NOW())
                """
                self.session.execute(text(query), data)
                self.session.commit()
            
            return True
            
        except Exception as e:
            logger.error(f"Error creating inventory fact: {e}")
            return False
    
    def _create_staff_performance_fact(self, data: Dict[str, Any]) -> bool:
        """Create staff performance fact table entry."""
        try:
            if self.warehouse_type == 'postgresql':
                query = """
                INSERT INTO fact_staff_performance 
                (date_key, staff_key, branch_key, hours_worked, sales_amount, 
                 transaction_count, customer_count, created_at)
                VALUES (:date_key, :staff_key, :branch_key, :hours_worked, :sales_amount,
                        :transaction_count, :customer_count, NOW())
                """
                self.session.execute(text(query), data)
                self.session.commit()
            
            return True
            
        except Exception as e:
            logger.error(f"Error creating staff performance fact: {e}")
            return False
    
    def _update_dimension_table(self, dimension_name: str, records: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Update specific dimension table."""
        try:
            inserted = 0
            updated = 0
            
            for record in records:
                if dimension_name == 'dim_product':
                    result = self._upsert_product_dimension(record)
                elif dimension_name == 'dim_customer':
                    result = self._upsert_customer_dimension(record)
                elif dimension_name == 'dim_staff':
                    result = self._upsert_staff_dimension(record)
                elif dimension_name == 'dim_branch':
                    result = self._upsert_branch_dimension(record)
                else:
                    logger.warning(f"Unknown dimension: {dimension_name}")
                    continue
                
                if result == 'inserted':
                    inserted += 1
                elif result == 'updated':
                    updated += 1
            
            return {'inserted': inserted, 'updated': updated}
            
        except Exception as e:
            logger.error(f"Error updating dimension table {dimension_name}: {e}")
            raise
    
    def _upsert_product_dimension(self, data: Dict[str, Any]) -> str:
        """Upsert product dimension record."""
        try:
            if self.warehouse_type == 'postgresql':
                query = """
                INSERT INTO dim_product (product_id, product_name, category, subcategory, 
                                       brand, unit_price, created_at, is_active)
                VALUES (:product_id, :product_name, :category, :subcategory, 
                        :brand, :unit_price, NOW(), true)
                ON CONFLICT (product_id) 
                DO UPDATE SET 
                    product_name = EXCLUDED.product_name,
                    category = EXCLUDED.category,
                    subcategory = EXCLUDED.subcategory,
                    brand = EXCLUDED.brand,
                    unit_price = EXCLUDED.unit_price,
                    updated_at = NOW()
                RETURNING CASE WHEN xmax = 0 THEN 'inserted' ELSE 'updated' END as action
                """
                
                result = self.session.execute(text(query), data)
                action = result.fetchone()[0]
                self.session.commit()
                return action
            
            return 'unknown'
            
        except Exception as e:
            logger.error(f"Error upserting product dimension: {e}")
            raise
    
    def _upsert_customer_dimension(self, data: Dict[str, Any]) -> str:
        """Upsert customer dimension record."""
        try:
            if self.warehouse_type == 'postgresql':
                query = """
                INSERT INTO dim_customer (customer_id, customer_name, customer_type,
                                        registration_date, is_active, created_at)
                VALUES (:customer_id, :customer_name, :customer_type,
                        :registration_date, true, NOW())
                ON CONFLICT (customer_id) 
                DO UPDATE SET 
                    customer_name = EXCLUDED.customer_name,
                    customer_type = EXCLUDED.customer_type,
                    updated_at = NOW()
                RETURNING CASE WHEN xmax = 0 THEN 'inserted' ELSE 'updated' END as action
                """
                
                result = self.session.execute(text(query), data)
                action = result.fetchone()[0]
                self.session.commit()
                return action
            
            return 'unknown'
            
        except Exception as e:
            logger.error(f"Error upserting customer dimension: {e}")
            raise
    
    def _upsert_staff_dimension(self, data: Dict[str, Any]) -> str:
        """Upsert staff dimension record."""
        try:
            if self.warehouse_type == 'postgresql':
                query = """
                INSERT INTO dim_staff (staff_id, staff_name, position, branch_id,
                                     hire_date, is_active, created_at)
                VALUES (:staff_id, :staff_name, :position, :branch_id,
                        :hire_date, true, NOW())
                ON CONFLICT (staff_id) 
                DO UPDATE SET 
                    staff_name = EXCLUDED.staff_name,
                    position = EXCLUDED.position,
                    branch_id = EXCLUDED.branch_id,
                    updated_at = NOW()
                RETURNING CASE WHEN xmax = 0 THEN 'inserted' ELSE 'updated' END as action
                """
                
                result = self.session.execute(text(query), data)
                action = result.fetchone()[0]
                self.session.commit()
                return action
            
            return 'unknown'
            
        except Exception as e:
            logger.error(f"Error upserting staff dimension: {e}")
            raise
    
    def _upsert_branch_dimension(self, data: Dict[str, Any]) -> str:
        """Upsert branch dimension record."""
        try:
            if self.warehouse_type == 'postgresql':
                query = """
                INSERT INTO dim_branch (branch_id, branch_name, location, region,
                                      opening_date, is_active, created_at)
                VALUES (:branch_id, :branch_name, :location, :region,
                        :opening_date, true, NOW())
                ON CONFLICT (branch_id) 
                DO UPDATE SET 
                    branch_name = EXCLUDED.branch_name,
                    location = EXCLUDED.location,
                    region = EXCLUDED.region,
                    updated_at = NOW()
                RETURNING CASE WHEN xmax = 0 THEN 'inserted' ELSE 'updated' END as action
                """
                
                result = self.session.execute(text(query), data)
                action = result.fetchone()[0]
                self.session.commit()
                return action
            
            return 'unknown'
            
        except Exception as e:
            logger.error(f"Error upserting branch dimension: {e}")
            raise
    
    def _execute_query(self, query: str, parameters: Dict[str, Any] = None) -> Dict[str, Any]:
        """Execute query and return results."""
        try:
            if self.warehouse_type == 'postgresql':
                result = self.session.execute(text(query), parameters or {})
                self.session.commit()
                return {'rowcount': result.rowcount}
            
            elif self.warehouse_type == 'clickhouse':
                result = self.connection.command(query)
                return {'rowcount': 0}  # ClickHouse doesn't return rowcount easily
            
        except Exception as e:
            logger.error(f"Error executing query: {e}")
            if self.session:
                self.session.rollback()
            raise
    
    def _update_table_statistics(self):
        """Update table statistics for query optimization."""
        try:
            if self.warehouse_type == 'postgresql':
                tables = ['fact_sales', 'fact_inventory', 'fact_staff_performance',
                         'dim_product', 'dim_customer', 'dim_staff', 'dim_branch', 'dim_date']
                
                for table in tables:
                    self.session.execute(text(f"ANALYZE {table}"))
                
                self.session.commit()
                logger.info("Updated table statistics")
            
        except Exception as e:
            logger.error(f"Error updating table statistics: {e}")
    
    def _rebuild_indexes(self):
        """Rebuild database indexes."""
        try:
            if self.warehouse_type == 'postgresql':
                # Reindex critical tables
                critical_tables = ['fact_sales', 'fact_inventory', 'dim_product', 'dim_customer']
                
                for table in critical_tables:
                    self.session.execute(text(f"REINDEX TABLE {table}"))
                
                self.session.commit()
                logger.info("Rebuilt indexes")
            
        except Exception as e:
            logger.error(f"Error rebuilding indexes: {e}")
    
    def _maintain_partitions(self):
        """Maintain table partitions."""
        try:
            if self.warehouse_type == 'postgresql':
                # Create new partitions for next month
                next_month = (datetime.now() + timedelta(days=32)).replace(day=1)
                partition_name = f"fact_sales_{next_month.strftime('%Y_%m')}"
                
                create_partition_query = f"""
                CREATE TABLE IF NOT EXISTS {partition_name} 
                PARTITION OF fact_sales
                FOR VALUES FROM ('{next_month.strftime('%Y-%m-01')}') 
                TO ('{(next_month + timedelta(days=32)).replace(day=1).strftime('%Y-%m-01')}')
                """
                
                self.session.execute(text(create_partition_query))
                self.session.commit()
                logger.info(f"Created partition {partition_name}")
            
        except Exception as e:
            logger.error(f"Error maintaining partitions: {e}")
    
    def _cleanup_old_data(self):
        """Clean up old data based on retention policies."""
        try:
            # Remove old raw events (older than configured retention period)
            retention_days = self.config.get('raw_data_retention_days', 90)
            cutoff_date = datetime.now() - timedelta(days=retention_days)
            
            if self.warehouse_type == 'postgresql':
                cleanup_query = """
                DELETE FROM raw_events 
                WHERE event_timestamp < :cutoff_date
                """
                
                result = self.session.execute(text(cleanup_query), {'cutoff_date': cutoff_date})
                self.session.commit()
                
                logger.info(f"Cleaned up {result.rowcount} old raw events")
            
        except Exception as e:
            logger.error(f"Error cleaning up old data: {e}")
    
    def _load_aggregation_rules(self) -> Dict[str, List[Dict[str, Any]]]:
        """Load aggregation rules from configuration."""
        default_rules = {
            'pos': [
                {
                    'name': 'daily_sales_aggregation',
                    'source_table': 'raw_events',
                    'target_table': 'agg_daily_sales',
                    'aggregation_type': 'daily_sales',
                    'schedule': 'daily'
                },
                {
                    'name': 'monthly_sales_aggregation',
                    'source_table': 'raw_events', 
                    'target_table': 'agg_monthly_sales',
                    'aggregation_type': 'monthly_sales',
                    'schedule': 'monthly'
                }
            ],
            'inventory': [
                {
                    'name': 'inventory_snapshot',
                    'source_table': 'raw_events',
                    'target_table': 'agg_inventory_snapshot',
                    'aggregation_type': 'inventory_snapshot',
                    'schedule': 'daily'
                }
            ],
            'staff': [
                {
                    'name': 'staff_performance_aggregation',
                    'source_table': 'raw_events',
                    'target_table': 'agg_staff_performance',
                    'aggregation_type': 'staff_performance',
                    'schedule': 'daily'
                }
            ]
        }
        
        # Load custom rules from config
        custom_rules = self.config.get('aggregation_rules', {})
        default_rules.update(custom_rules)
        
        return default_rules