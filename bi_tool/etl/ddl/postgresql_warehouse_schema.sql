-- PostgreSQL Data Warehouse Schema
-- Business Intelligence Tool - Fact and Dimension Tables

-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Date Dimension Table
CREATE TABLE IF NOT EXISTS dim_date (
    date_key DATE PRIMARY KEY,
    year INTEGER NOT NULL,
    quarter INTEGER NOT NULL,
    month INTEGER NOT NULL,
    month_name VARCHAR(20) NOT NULL,
    day INTEGER NOT NULL,
    day_of_week INTEGER NOT NULL,
    day_name VARCHAR(20) NOT NULL,
    week_of_year INTEGER NOT NULL,
    is_weekend BOOLEAN NOT NULL DEFAULT FALSE,
    is_holiday BOOLEAN NOT NULL DEFAULT FALSE,
    holiday_name VARCHAR(100),
    fiscal_year INTEGER,
    fiscal_quarter INTEGER,
    fiscal_month INTEGER,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Time Dimension Table
CREATE TABLE IF NOT EXISTS dim_time (
    time_key TIME PRIMARY KEY,
    hour INTEGER NOT NULL,
    minute INTEGER NOT NULL,
    second INTEGER NOT NULL,
    hour_12 INTEGER NOT NULL,
    am_pm VARCHAR(2) NOT NULL,
    hour_name VARCHAR(20) NOT NULL,
    shift VARCHAR(20) NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Product Dimension Table
CREATE TABLE IF NOT EXISTS dim_product (
    product_key UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    product_id VARCHAR(50) UNIQUE NOT NULL,
    product_name VARCHAR(200) NOT NULL,
    category VARCHAR(100),
    subcategory VARCHAR(100),
    brand VARCHAR(100),
    supplier VARCHAR(100),
    unit_price DECIMAL(10, 2),
    cost_price DECIMAL(10, 2),
    margin_percentage DECIMAL(5, 2),
    weight DECIMAL(8, 3),
    dimensions VARCHAR(50),
    barcode VARCHAR(50),
    sku VARCHAR(50),
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    effective_from DATE DEFAULT CURRENT_DATE,
    effective_to DATE
);

-- Customer Dimension Table
CREATE TABLE IF NOT EXISTS dim_customer (
    customer_key UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    customer_id VARCHAR(50) UNIQUE NOT NULL,
    customer_name VARCHAR(200) NOT NULL,
    customer_type VARCHAR(50) NOT NULL DEFAULT 'retail', -- retail, wholesale, corporate
    email VARCHAR(100),
    phone VARCHAR(20),
    address TEXT,
    city VARCHAR(100),
    state VARCHAR(100),
    postal_code VARCHAR(20),
    country VARCHAR(100) DEFAULT 'USA',
    registration_date DATE,
    birth_date DATE,
    gender VARCHAR(10),
    segment VARCHAR(50), -- premium, regular, budget
    loyalty_tier VARCHAR(50), -- gold, silver, bronze
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    effective_from DATE DEFAULT CURRENT_DATE,
    effective_to DATE
);

-- Staff Dimension Table
CREATE TABLE IF NOT EXISTS dim_staff (
    staff_key UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    staff_id VARCHAR(50) UNIQUE NOT NULL,
    staff_name VARCHAR(200) NOT NULL,
    position VARCHAR(100),
    department VARCHAR(100),
    branch_id VARCHAR(50),
    manager_id VARCHAR(50),
    hire_date DATE,
    termination_date DATE,
    salary DECIMAL(10, 2),
    commission_rate DECIMAL(5, 4),
    email VARCHAR(100),
    phone VARCHAR(20),
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    effective_from DATE DEFAULT CURRENT_DATE,
    effective_to DATE
);

-- Branch Dimension Table
CREATE TABLE IF NOT EXISTS dim_branch (
    branch_key UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    branch_id VARCHAR(50) UNIQUE NOT NULL,
    branch_name VARCHAR(200) NOT NULL,
    branch_code VARCHAR(20),
    address TEXT,
    city VARCHAR(100),
    state VARCHAR(100),
    postal_code VARCHAR(20),
    country VARCHAR(100) DEFAULT 'USA',
    region VARCHAR(100),
    area VARCHAR(100),
    manager_id VARCHAR(50),
    opening_date DATE,
    closing_date DATE,
    branch_type VARCHAR(50), -- flagship, regular, outlet
    size_category VARCHAR(50), -- large, medium, small
    phone VARCHAR(20),
    email VARCHAR(100),
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    effective_from DATE DEFAULT CURRENT_DATE,
    effective_to DATE
);

-- Sales Fact Table
CREATE TABLE IF NOT EXISTS fact_sales (
    sales_key UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    date_key DATE NOT NULL REFERENCES dim_date(date_key),
    time_key TIME NOT NULL REFERENCES dim_time(time_key),
    product_key UUID NOT NULL REFERENCES dim_product(product_key),
    customer_key UUID REFERENCES dim_customer(customer_key),
    staff_key UUID REFERENCES dim_staff(staff_key),
    branch_key UUID NOT NULL REFERENCES dim_branch(branch_key),
    
    -- Transaction details
    transaction_id VARCHAR(100) NOT NULL,
    line_number INTEGER NOT NULL DEFAULT 1,
    
    -- Measures
    quantity DECIMAL(10, 3) NOT NULL,
    unit_price DECIMAL(10, 2) NOT NULL,
    discount_amount DECIMAL(10, 2) DEFAULT 0,
    discount_percentage DECIMAL(5, 2) DEFAULT 0,
    tax_amount DECIMAL(10, 2) DEFAULT 0,
    total_amount DECIMAL(10, 2) NOT NULL,
    cost_amount DECIMAL(10, 2),
    profit_amount DECIMAL(10, 2),
    
    -- Additional attributes
    payment_method VARCHAR(50),
    currency VARCHAR(3) DEFAULT 'USD',
    exchange_rate DECIMAL(10, 4) DEFAULT 1.0,
    
    -- Metadata
    source_system VARCHAR(50) NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    
    CONSTRAINT uk_sales_transaction UNIQUE (transaction_id, line_number)
);

-- Inventory Fact Table
CREATE TABLE IF NOT EXISTS fact_inventory (
    inventory_key UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    date_key DATE NOT NULL REFERENCES dim_date(date_key),
    product_key UUID NOT NULL REFERENCES dim_product(product_key),
    branch_key UUID NOT NULL REFERENCES dim_branch(branch_key),
    
    -- Inventory measures
    opening_stock DECIMAL(10, 3) DEFAULT 0,
    closing_stock DECIMAL(10, 3) DEFAULT 0,
    stock_received DECIMAL(10, 3) DEFAULT 0,
    stock_sold DECIMAL(10, 3) DEFAULT 0,
    stock_adjusted DECIMAL(10, 3) DEFAULT 0,
    stock_transferred_in DECIMAL(10, 3) DEFAULT 0,
    stock_transferred_out DECIMAL(10, 3) DEFAULT 0,
    stock_damaged DECIMAL(10, 3) DEFAULT 0,
    stock_expired DECIMAL(10, 3) DEFAULT 0,
    
    -- Value measures
    opening_value DECIMAL(12, 2) DEFAULT 0,
    closing_value DECIMAL(12, 2) DEFAULT 0,
    average_cost DECIMAL(10, 2),
    
    -- Additional attributes
    reorder_level DECIMAL(10, 3),
    max_stock_level DECIMAL(10, 3),
    
    -- Metadata
    source_system VARCHAR(50) NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    
    CONSTRAINT uk_inventory_daily UNIQUE (date_key, product_key, branch_key)
);

-- Staff Performance Fact Table
CREATE TABLE IF NOT EXISTS fact_staff_performance (
    performance_key UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    date_key DATE NOT NULL REFERENCES dim_date(date_key),
    staff_key UUID NOT NULL REFERENCES dim_staff(staff_key),
    branch_key UUID NOT NULL REFERENCES dim_branch(branch_key),
    
    -- Performance measures
    hours_worked DECIMAL(5, 2) DEFAULT 0,
    hours_scheduled DECIMAL(5, 2) DEFAULT 0,
    overtime_hours DECIMAL(5, 2) DEFAULT 0,
    sales_amount DECIMAL(12, 2) DEFAULT 0,
    transaction_count INTEGER DEFAULT 0,
    customer_count INTEGER DEFAULT 0,
    items_sold INTEGER DEFAULT 0,
    returns_processed INTEGER DEFAULT 0,
    returns_amount DECIMAL(12, 2) DEFAULT 0,
    
    -- Calculated measures
    sales_per_hour DECIMAL(10, 2),
    average_transaction_value DECIMAL(10, 2),
    items_per_transaction DECIMAL(5, 2),
    attendance_rate DECIMAL(5, 2),
    
    -- Additional attributes
    shift VARCHAR(20),
    department VARCHAR(100),
    
    -- Metadata
    source_system VARCHAR(50) NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    
    CONSTRAINT uk_staff_performance_daily UNIQUE (date_key, staff_key, branch_key)
);

-- Customer Behavior Fact Table
CREATE TABLE IF NOT EXISTS fact_customer_behavior (
    behavior_key UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    date_key DATE NOT NULL REFERENCES dim_date(date_key),
    customer_key UUID NOT NULL REFERENCES dim_customer(customer_key),
    branch_key UUID REFERENCES dim_branch(branch_key),
    
    -- Behavior measures
    visit_count INTEGER DEFAULT 0,
    transaction_count INTEGER DEFAULT 0,
    total_spend DECIMAL(12, 2) DEFAULT 0,
    items_purchased INTEGER DEFAULT 0,
    categories_purchased INTEGER DEFAULT 0,
    avg_basket_value DECIMAL(10, 2),
    time_between_visits INTEGER, -- days
    
    -- Channel attributes
    channel VARCHAR(50), -- in-store, online, mobile
    
    -- Metadata
    source_system VARCHAR(50) NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    
    CONSTRAINT uk_customer_behavior_daily UNIQUE (date_key, customer_key, branch_key)
);

-- Aggregated Sales Summary Table
CREATE TABLE IF NOT EXISTS agg_daily_sales (
    date_key DATE NOT NULL,
    branch_id VARCHAR(50) NOT NULL,
    total_sales DECIMAL(15, 2) NOT NULL DEFAULT 0,
    total_transactions INTEGER NOT NULL DEFAULT 0,
    total_items INTEGER NOT NULL DEFAULT 0,
    unique_customers INTEGER NOT NULL DEFAULT 0,
    avg_transaction_value DECIMAL(10, 2),
    avg_items_per_transaction DECIMAL(5, 2),
    total_discount DECIMAL(12, 2) DEFAULT 0,
    total_tax DECIMAL(12, 2) DEFAULT 0,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    
    PRIMARY KEY (date_key, branch_id)
);

-- Aggregated Monthly Sales Table
CREATE TABLE IF NOT EXISTS agg_monthly_sales (
    month_key DATE NOT NULL, -- First day of month
    branch_id VARCHAR(50) NOT NULL,
    total_sales DECIMAL(15, 2) NOT NULL DEFAULT 0,
    total_transactions INTEGER NOT NULL DEFAULT 0,
    total_items INTEGER NOT NULL DEFAULT 0,
    unique_customers INTEGER NOT NULL DEFAULT 0,
    avg_transaction_value DECIMAL(10, 2),
    customer_retention_rate DECIMAL(5, 2),
    new_customers INTEGER DEFAULT 0,
    returning_customers INTEGER DEFAULT 0,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    
    PRIMARY KEY (month_key, branch_id)
);

-- Aggregated Inventory Snapshot Table
CREATE TABLE IF NOT EXISTS agg_inventory_snapshot (
    snapshot_date DATE NOT NULL,
    branch_id VARCHAR(50) NOT NULL,
    product_id VARCHAR(50) NOT NULL,
    current_stock DECIMAL(10, 3) NOT NULL,
    min_stock DECIMAL(10, 3),
    max_stock DECIMAL(10, 3),
    stock_value DECIMAL(12, 2),
    days_of_supply INTEGER,
    stock_status VARCHAR(20), -- low, normal, overstock
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    
    PRIMARY KEY (snapshot_date, branch_id, product_id)
);

-- Aggregated Staff Performance Table
CREATE TABLE IF NOT EXISTS agg_staff_performance (
    date_key DATE NOT NULL,
    staff_id VARCHAR(50) NOT NULL,
    branch_id VARCHAR(50) NOT NULL,
    total_sales DECIMAL(12, 2) DEFAULT 0,
    transaction_count INTEGER DEFAULT 0,
    hours_worked DECIMAL(5, 2) DEFAULT 0,
    sales_per_hour DECIMAL(10, 2),
    performance_score DECIMAL(5, 2),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    
    PRIMARY KEY (date_key, staff_id, branch_id)
);

-- Indexes for performance optimization
CREATE INDEX IF NOT EXISTS idx_fact_sales_date ON fact_sales (date_key);
CREATE INDEX IF NOT EXISTS idx_fact_sales_product ON fact_sales (product_key);
CREATE INDEX IF NOT EXISTS idx_fact_sales_customer ON fact_sales (customer_key);
CREATE INDEX IF NOT EXISTS idx_fact_sales_branch ON fact_sales (branch_key);
CREATE INDEX IF NOT EXISTS idx_fact_sales_transaction ON fact_sales (transaction_id);

CREATE INDEX IF NOT EXISTS idx_fact_inventory_date ON fact_inventory (date_key);
CREATE INDEX IF NOT EXISTS idx_fact_inventory_product ON fact_inventory (product_key);
CREATE INDEX IF NOT EXISTS idx_fact_inventory_branch ON fact_inventory (branch_key);

CREATE INDEX IF NOT EXISTS idx_fact_staff_date ON fact_staff_performance (date_key);
CREATE INDEX IF NOT EXISTS idx_fact_staff_staff ON fact_staff_performance (staff_key);
CREATE INDEX IF NOT EXISTS idx_fact_staff_branch ON fact_staff_performance (branch_key);

-- Populate date dimension with sample data
INSERT INTO dim_date (date_key, year, quarter, month, month_name, day, day_of_week, day_name, week_of_year, is_weekend)
SELECT 
    date_val::date as date_key,
    EXTRACT(YEAR FROM date_val) as year,
    EXTRACT(QUARTER FROM date_val) as quarter,
    EXTRACT(MONTH FROM date_val) as month,
    TO_CHAR(date_val, 'Month') as month_name,
    EXTRACT(DAY FROM date_val) as day,
    EXTRACT(DOW FROM date_val) as day_of_week,
    TO_CHAR(date_val, 'Day') as day_name,
    EXTRACT(WEEK FROM date_val) as week_of_year,
    CASE WHEN EXTRACT(DOW FROM date_val) IN (0, 6) THEN TRUE ELSE FALSE END as is_weekend
FROM generate_series('2020-01-01'::date, '2030-12-31'::date, '1 day'::interval) date_val
ON CONFLICT (date_key) DO NOTHING;

-- Populate time dimension
INSERT INTO dim_time (time_key, hour, minute, second, hour_12, am_pm, hour_name, shift)
SELECT 
    time_val::time as time_key,
    EXTRACT(HOUR FROM time_val) as hour,
    EXTRACT(MINUTE FROM time_val) as minute,
    EXTRACT(SECOND FROM time_val) as second,
    CASE 
        WHEN EXTRACT(HOUR FROM time_val) = 0 THEN 12
        WHEN EXTRACT(HOUR FROM time_val) > 12 THEN EXTRACT(HOUR FROM time_val) - 12
        ELSE EXTRACT(HOUR FROM time_val)
    END as hour_12,
    CASE WHEN EXTRACT(HOUR FROM time_val) < 12 THEN 'AM' ELSE 'PM' END as am_pm,
    TO_CHAR(time_val, 'HH24:MI') as hour_name,
    CASE 
        WHEN EXTRACT(HOUR FROM time_val) BETWEEN 6 AND 14 THEN 'Morning'
        WHEN EXTRACT(HOUR FROM time_val) BETWEEN 14 AND 22 THEN 'Evening'
        ELSE 'Night'
    END as shift
FROM generate_series('00:00:00'::time, '23:59:59'::time, '1 minute'::interval) time_val
ON CONFLICT (time_key) DO NOTHING;

-- Create partitioning for fact tables (monthly partitions)
-- Example for fact_sales table partitioning by month
-- CREATE TABLE fact_sales_2024_01 PARTITION OF fact_sales
-- FOR VALUES FROM ('2024-01-01') TO ('2024-02-01');

COMMENT ON TABLE dim_date IS 'Date dimension table with calendar and fiscal attributes';
COMMENT ON TABLE dim_time IS 'Time dimension table with hour, minute, second attributes';
COMMENT ON TABLE dim_product IS 'Product dimension table with SCD Type 2 support';
COMMENT ON TABLE dim_customer IS 'Customer dimension table with SCD Type 2 support';
COMMENT ON TABLE dim_staff IS 'Staff dimension table with SCD Type 2 support';
COMMENT ON TABLE dim_branch IS 'Branch dimension table with SCD Type 2 support';
COMMENT ON TABLE fact_sales IS 'Sales transactions fact table';
COMMENT ON TABLE fact_inventory IS 'Inventory movements and snapshots fact table';
COMMENT ON TABLE fact_staff_performance IS 'Staff performance metrics fact table';
COMMENT ON TABLE agg_daily_sales IS 'Pre-aggregated daily sales summary';
COMMENT ON TABLE agg_monthly_sales IS 'Pre-aggregated monthly sales summary';
COMMENT ON TABLE agg_inventory_snapshot IS 'Daily inventory snapshots';
COMMENT ON TABLE agg_staff_performance IS 'Daily staff performance aggregations';