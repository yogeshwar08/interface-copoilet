-- Database initialization script for aegisdb
CREATE TABLE IF NOT EXISTS users (
    id SERIAL PRIMARY KEY,
    username VARCHAR(100) NOT NULL UNIQUE,
    email VARCHAR(255) NOT NULL UNIQUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS customer_profiles (
    id SERIAL PRIMARY KEY,
    customer_id VARCHAR(50) NOT NULL UNIQUE,
    age INT NOT NULL,
    tenure_months INT NOT NULL,
    monthly_charges NUMERIC(10, 2) NOT NULL,
    total_charges NUMERIC(10, 2) NOT NULL,
    support_tickets INT DEFAULT 0,
    usage_hours NUMERIC(10, 2) DEFAULT 0.0,
    contract_type VARCHAR(50) NOT NULL,
    payment_method VARCHAR(50) NOT NULL,
    has_partner BOOLEAN DEFAULT FALSE
);

CREATE TABLE IF NOT EXISTS documents (
    id SERIAL PRIMARY KEY,
    filename VARCHAR(255) NOT NULL,
    document_type VARCHAR(50) DEFAULT 'pdf',
    page_count INT DEFAULT 1,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS approval_requests (
    id SERIAL PRIMARY KEY,
    approval_id VARCHAR(100) NOT NULL UNIQUE,
    tool VARCHAR(100) NOT NULL,
    arguments JSONB,
    agent VARCHAR(100) DEFAULT 'router_agent',
    status VARCHAR(50) DEFAULT 'pending',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    approved_at TIMESTAMP WITH TIME ZONE,
    rejected_at TIMESTAMP WITH TIME ZONE,
    thread_id VARCHAR(100)
);

-- Seed initial enterprise records
INSERT INTO users (username, email, created_at) VALUES
('alice_chen', 'alice.chen@enterprise.corp', '2024-01-15 08:30:00Z'),
('bob_martin', 'bob.martin@enterprise.corp', '2024-02-20 09:45:00Z'),
('carol_danvers', 'carol.danvers@enterprise.corp', '2024-03-10 11:20:00Z'),
('david_miller', 'david.miller@enterprise.corp', '2024-04-05 14:15:00Z'),
('eva_ross', 'eva.ross@enterprise.corp', '2024-05-12 16:50:00Z')
ON CONFLICT (username) DO NOTHING;

INSERT INTO customer_profiles (customer_id, age, tenure_months, monthly_charges, total_charges, support_tickets, usage_hours, contract_type, payment_method, has_partner) VALUES
('CUST-1001', 34, 18, 79.50, 1431.00, 2, 142.5, 'month-to-month', 'credit card', true),
('CUST-1002', 45, 36, 119.00, 4284.00, 0, 310.0, 'two-year', 'bank transfer', true),
('CUST-1003', 29, 6, 49.99, 299.94, 4, 88.0, 'month-to-month', 'electronic check', false),
('CUST-1004', 52, 48, 145.00, 6960.00, 1, 450.2, 'two-year', 'credit card', true),
('CUST-1005', 41, 24, 89.90, 2157.60, 6, 215.0, 'one-year', 'bank transfer', false)
ON CONFLICT (customer_id) DO NOTHING;

INSERT INTO documents (filename, document_type, page_count) VALUES
('01_Diabetes_Clinical_Guideline.pdf', 'clinical_guideline', 14),
('Enterprise_Information_Security_Policy.pdf', 'corporate_policy', 8),
('Q3_2024_Financial_Report_10Q.pdf', 'sec_filing', 42)
ON CONFLICT DO NOTHING;

INSERT INTO approval_requests (approval_id, tool, arguments, agent, status) VALUES
('APP-REQ-901', 'execute_database_migration', '{"target_version": "v1.4"}', 'sql_agent', 'approved'),
('APP-REQ-902', 'external_api_export', '{"format": "csv", "batch_size": 5000}', 'data_export_tool', 'pending'),
('APP-REQ-903', 'elevate_user_privilege', '{"user_id": 4, "role": "admin"}', 'iam_agent', 'rejected')
ON CONFLICT (approval_id) DO NOTHING;
