# E-Commerce Database Schema Documentation

This document describes the schema structure, data types, constraints, and business semantics of the local MySQL e-commerce database used by the LangGraph SQL Agent.

## Overview of Approved Tables

Only the following four tables are permitted for query generation and execution:
1. `customers`
2. `products`
3. `orders`
4. `order_items`

Any attempt to query tables outside this list is rejected by the SQL validation policy before database execution.

---

## 1. `customers` Table

Stores registered customer accounts and geographical location.

| Column | Data Type | Nullable | Key | Description |
|---|---|---|---|---|
| `customer_id` | `INT` | No | PK (Auto-increment) | Unique customer identifier |
| `first_name` | `VARCHAR(50)` | No | | Customer given name |
| `last_name` | `VARCHAR(50)` | No | | Customer family/surname |
| `email` | `VARCHAR(100)` | No | Unique | Primary email address |
| `city` | `VARCHAR(50)` | No | Index | City of residence (e.g., 'New York', 'Chicago') |
| `state` | `VARCHAR(50)` | No | | State or province code (e.g., 'NY', 'CA', 'TX') |
| `created_at` | `TIMESTAMP` | Yes | | Timestamp when customer account was registered |

---

## 2. `products` Table

Stores product catalog items, categories, pricing, and stock inventory.

| Column | Data Type | Nullable | Key | Description |
|---|---|---|---|---|
| `product_id` | `INT` | No | PK (Auto-increment) | Unique product identifier |
| `product_name` | `VARCHAR(100)` | No | | Full product title |
| `category` | `VARCHAR(50)` | No | Index | Category name ('Electronics', 'Clothing', 'Home & Kitchen', 'Books', 'Sports') |
| `price` | `DECIMAL(10,2)` | No | Index | Current retail unit price |
| `stock_quantity` | `INT` | No | | Units remaining in inventory |
| `created_at` | `TIMESTAMP` | Yes | | Timestamp when product was added to catalog |

---

## 3. `orders` Table

Stores purchase orders placed by customers.

| Column | Data Type | Nullable | Key | Description |
|---|---|---|---|---|
| `order_id` | `INT` | No | PK (Auto-increment) | Unique order identifier |
| `customer_id` | `INT` | No | FK (customers) | ID of the customer who placed the order |
| `order_date` | `DATETIME` | No | Index | Timestamp when the order was placed |
| `status` | `VARCHAR(20)` | No | Index | Order status: 'Completed', 'Shipped', 'Pending', 'Cancelled' |
| `total_amount` | `DECIMAL(10,2)` | No | | Total financial value of the order |

### Foreign Keys
- `fk_orders_customer`: `orders.customer_id` references `customers.customer_id` (`ON DELETE RESTRICT ON UPDATE CASCADE`)

---

## 4. `order_items` Table

Line items linking products to orders with quantity and pricing at time of purchase.

| Column | Data Type | Nullable | Key | Description |
|---|---|---|---|---|
| `order_item_id` | `INT` | No | PK (Auto-increment) | Unique line item identifier |
| `order_id` | `INT` | No | FK (orders) | Reference to parent order |
| `product_id` | `INT` | No | FK (products) | Reference to purchased product |
| `quantity` | `INT` | No | | Number of units purchased |
| `unit_price` | `DECIMAL(10,2)` | No | | Unit price charged at time of order |
| `subtotal` | `DECIMAL(10,2)` | No | | Line total: `quantity * unit_price` |

### Foreign Keys
- `fk_items_order`: `order_items.order_id` references `orders.order_id` (`ON DELETE CASCADE ON UPDATE CASCADE`)
- `fk_items_product`: `order_items.product_id` references `products.product_id` (`ON DELETE RESTRICT ON UPDATE CASCADE`)

---

## Common Join Patterns

1. **Customer Orders**:
   ```sql
   SELECT c.first_name, c.last_name, o.order_id, o.order_date, o.total_amount
   FROM customers c
   JOIN orders o ON c.customer_id = o.customer_id;
   ```

2. **Order Details with Product Names**:
   ```sql
   SELECT o.order_id, p.product_name, oi.quantity, oi.unit_price, oi.subtotal
   FROM orders o
   JOIN order_items oi ON o.order_id = oi.order_id
   JOIN products p ON oi.product_id = p.product_id;
   ```

3. **Total Sales Revenue by Product Category**:
   ```sql
   SELECT p.category, SUM(oi.subtotal) AS total_revenue
   FROM order_items oi
   JOIN products p ON oi.product_id = p.product_id
   GROUP BY p.category
   ORDER BY total_revenue DESC;
   ```
