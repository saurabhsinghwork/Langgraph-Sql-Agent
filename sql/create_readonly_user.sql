-- Script to create dedicated read-only MySQL user for the LangGraph SQL Agent
-- Execute this script as MySQL root/administrator.
-- Replace 'ecommerce_db' with your actual database name if different.
-- Replace 'readonly_agent' and 'AgentSecurePassword123!' with your desired credentials.

-- 1. Create the user restricted to localhost/local connections
CREATE USER IF NOT EXISTS 'readonly_agent'@'localhost' IDENTIFIED BY 'AgentSecurePassword123!';
CREATE USER IF NOT EXISTS 'readonly_agent'@'127.0.0.1' IDENTIFIED BY 'AgentSecurePassword123!';

-- 2. Grant only SELECT permissions on the approved e-commerce tables
-- Explicitly deny or omit any INSERT, UPDATE, DELETE, DROP, ALTER, CREATE, GRANT privileges
GRANT SELECT ON ecommerce_db.customers TO 'readonly_agent'@'localhost';
GRANT SELECT ON ecommerce_db.products TO 'readonly_agent'@'localhost';
GRANT SELECT ON ecommerce_db.orders TO 'readonly_agent'@'localhost';
GRANT SELECT ON ecommerce_db.order_items TO 'readonly_agent'@'localhost';

GRANT SELECT ON ecommerce_db.customers TO 'readonly_agent'@'127.0.0.1';
GRANT SELECT ON ecommerce_db.products TO 'readonly_agent'@'127.0.0.1';
GRANT SELECT ON ecommerce_db.orders TO 'readonly_agent'@'127.0.0.1';
GRANT SELECT ON ecommerce_db.order_items TO 'readonly_agent'@'127.0.0.1';

-- 3. Flush privileges to apply changes immediately
FLUSH PRIVILEGES;

-- 4. Verification queries (run to verify permissions):
-- SHOW GRANTS FOR 'readonly_agent'@'localhost';
