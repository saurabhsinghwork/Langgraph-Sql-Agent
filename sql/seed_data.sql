-- Seed Data for LangGraph SQL Agent E-Commerce Database

-- Insert Customers
INSERT INTO customers (customer_id, first_name, last_name, email, city, state, created_at) VALUES
(1, 'Alice', 'Smith', 'alice.smith@example.com', 'New York', 'NY', '2025-01-10 09:30:00'),
(2, 'Bob', 'Jones', 'bob.jones@example.com', 'Los Angeles', 'CA', '2025-01-12 14:15:00'),
(3, 'Charlie', 'Brown', 'charlie.brown@example.com', 'Chicago', 'IL', '2025-01-15 11:20:00'),
(4, 'Diana', 'Prince', 'diana.prince@example.com', 'New York', 'NY', '2025-01-18 16:45:00'),
(5, 'Evan', 'Wright', 'evan.wright@example.com', 'Houston', 'TX', '2025-01-20 10:00:00'),
(6, 'Fiona', 'Gallagher', 'fiona.g@example.com', 'Chicago', 'IL', '2025-01-22 13:10:00'),
(7, 'George', 'Clark', 'george.clark@example.com', 'Seattle', 'WA', '2025-01-25 08:50:00'),
(8, 'Hannah', 'Abbott', 'hannah.a@example.com', 'Austin', 'TX', '2025-02-01 17:05:00'),
(9, 'Ian', 'Malcolm', 'ian.malcolm@example.com', 'Los Angeles', 'CA', '2025-02-05 12:30:00'),
(10, 'Julia', 'Roberts', 'julia.r@example.com', 'Miami', 'FL', '2025-02-08 15:40:00'),
(11, 'Kevin', 'Bacon', 'kevin.b@example.com', 'New York', 'NY', '2025-02-10 18:20:00'),
(12, 'Laura', 'Croft', 'laura.croft@example.com', 'Seattle', 'WA', '2025-02-12 09:15:00'),
(13, 'Michael', 'Scott', 'michael.scott@example.com', 'Austin', 'TX', '2025-02-15 11:00:00'),
(14, 'Nancy', 'Drew', 'nancy.drew@example.com', 'Chicago', 'IL', '2025-02-18 14:25:00'),
(15, 'Oscar', 'Martinez', 'oscar.m@example.com', 'Houston', 'TX', '2025-02-20 16:10:00');

-- Insert Products
INSERT INTO products (product_id, product_name, category, price, stock_quantity, created_at) VALUES
(1, 'Wireless Noise-Canceling Headphones', 'Electronics', 199.99, 45, '2025-01-01 08:00:00'),
(2, 'Mechanical Gaming Keyboard', 'Electronics', 129.50, 60, '2025-01-01 08:00:00'),
(3, 'Ultra-Slim 27-inch 4K Monitor', 'Electronics', 349.00, 25, '2025-01-02 08:00:00'),
(4, 'Ergonomic Wireless Mouse', 'Electronics', 49.99, 120, '2025-01-02 08:00:00'),
(5, 'Smartwatch with Heart Rate Monitor', 'Electronics', 179.95, 35, '2025-01-03 08:00:00'),
(6, 'Classic Organic Cotton T-Shirt', 'Clothing', 24.99, 200, '2025-01-03 08:00:00'),
(7, 'Slim-Fit Denim Jeans', 'Clothing', 59.99, 90, '2025-01-04 08:00:00'),
(8, 'Waterproof Winter Jacket', 'Clothing', 149.00, 40, '2025-01-04 08:00:00'),
(9, 'Breathable Running Shoes', 'Clothing', 89.50, 75, '2025-01-05 08:00:00'),
(10, 'Stainless Steel Chef Knife 8-inch', 'Home & Kitchen', 45.00, 80, '2025-01-05 08:00:00'),
(11, 'Non-Stick Ceramic Frying Pan', 'Home & Kitchen', 39.99, 110, '2025-01-06 08:00:00'),
(12, 'Electric Pour-Over Kettle', 'Home & Kitchen', 65.00, 50, '2025-01-06 08:00:00'),
(13, 'Robot Vacuum Cleaner', 'Home & Kitchen', 279.99, 20, '2025-01-07 08:00:00'),
(14, 'Designing Data-Intensive Applications', 'Books', 42.50, 85, '2025-01-07 08:00:00'),
(15, 'Clean Code: A Handbook of Agile Craft', 'Books', 37.95, 95, '2025-01-08 08:00:00'),
(16, 'The Pragmatic Programmer', 'Books', 44.00, 70, '2025-01-08 08:00:00'),
(17, 'Premium Yoga Mat with Alignment Lines', 'Sports', 34.99, 130, '2025-01-09 08:00:00'),
(18, 'Adjustable Dumbbell Set 50 lbs', 'Sports', 199.00, 30, '2025-01-09 08:00:00'),
(19, 'Insulated Stainless Steel Water Bottle', 'Sports', 22.50, 250, '2025-01-10 08:00:00'),
(20, 'Carbon Fiber Road Bike Helmet', 'Sports', 79.99, 45, '2025-01-10 08:00:00');

-- Insert Orders
INSERT INTO orders (order_id, customer_id, order_date, status, total_amount) VALUES
(101, 1, '2025-02-01 10:15:00', 'Completed', 249.98),
(102, 2, '2025-02-02 11:30:00', 'Completed', 349.00),
(103, 3, '2025-02-03 14:00:00', 'Completed', 80.45),
(104, 4, '2025-02-04 16:20:00', 'Completed', 199.99),
(105, 1, '2025-02-05 09:45:00', 'Completed', 104.98),
(106, 5, '2025-02-06 13:10:00', 'Completed', 179.95),
(107, 6, '2025-02-07 15:00:00', 'Completed', 228.99),
(108, 7, '2025-02-08 12:20:00', 'Completed', 65.00),
(109, 8, '2025-02-09 18:00:00', 'Completed', 199.00),
(110, 2, '2025-02-10 10:30:00', 'Completed', 179.49),
(111, 9, '2025-02-11 14:15:00', 'Shipped', 279.99),
(112, 10, '2025-02-12 11:00:00', 'Completed', 42.50),
(113, 11, '2025-02-13 16:40:00', 'Shipped', 139.98),
(114, 12, '2025-02-14 09:20:00', 'Pending', 199.99),
(115, 3, '2025-02-15 15:30:00', 'Completed', 129.50),
(116, 13, '2025-02-16 12:00:00', 'Cancelled', 59.99),
(117, 4, '2025-02-17 17:15:00', 'Completed', 37.95),
(118, 14, '2025-02-18 10:50:00', 'Completed', 104.99),
(119, 15, '2025-02-19 13:45:00', 'Shipped', 57.49),
(120, 1, '2025-02-20 16:00:00', 'Completed', 349.00);

-- Insert Order Items
INSERT INTO order_items (order_item_id, order_id, product_id, quantity, unit_price, subtotal) VALUES
-- Order 101: Alice Smith
(1, 101, 1, 1, 199.99, 199.99),
(2, 101, 4, 1, 49.99, 49.99),
-- Order 102: Bob Jones
(3, 102, 3, 1, 349.00, 349.00),
-- Order 103: Charlie Brown
(4, 103, 14, 1, 42.50, 42.50),
(5, 103, 15, 1, 37.95, 37.95),
-- Order 104: Diana Prince
(6, 104, 1, 1, 199.99, 199.99),
-- Order 105: Alice Smith
(7, 105, 6, 2, 24.99, 49.98),
(8, 105, 17, 1, 34.99, 34.99),
(9, 105, 19, 1, 20.01, 20.01),
-- Order 106: Evan Wright
(10, 106, 5, 1, 179.95, 179.95),
-- Order 107: Fiona Gallagher
(11, 107, 8, 1, 149.00, 149.00),
(12, 107, 20, 1, 79.99, 79.99),
-- Order 108: George Clark
(13, 108, 12, 1, 65.00, 65.00),
-- Order 109: Hannah Abbott
(14, 109, 18, 1, 199.00, 199.00),
-- Order 110: Bob Jones
(15, 110, 9, 1, 89.50, 89.50),
(16, 110, 9, 1, 89.99, 89.99),
-- Order 111: Ian Malcolm
(17, 111, 13, 1, 279.99, 279.99),
-- Order 112: Julia Roberts
(18, 112, 14, 1, 42.50, 42.50),
-- Order 113: Kevin Bacon
(19, 113, 7, 1, 59.99, 59.99),
(20, 113, 20, 1, 79.99, 79.99),
-- Order 114: Laura Croft
(21, 114, 1, 1, 199.99, 199.99),
-- Order 115: Charlie Brown
(22, 115, 2, 1, 129.50, 129.50),
-- Order 116: Michael Scott
(23, 116, 7, 1, 59.99, 59.99),
-- Order 117: Diana Prince
(24, 117, 15, 1, 37.95, 37.95),
-- Order 118: Nancy Drew
(25, 118, 10, 1, 45.00, 45.00),
(26, 118, 7, 1, 59.99, 59.99),
-- Order 119: Oscar Martinez
(27, 119, 17, 1, 34.99, 34.99),
(28, 119, 19, 1, 22.50, 22.50),
-- Order 120: Alice Smith
(29, 120, 3, 1, 349.00, 349.00);
