CREATE DATABASE IF NOT EXISTS SHOPPING_MALL;
USE SHOPPING_MALL;

-- ======================================================================
-- 1. TABLE STRUCTURES (Normalized to 3NF)
-- ======================================================================

-- Customer Table
CREATE TABLE IF NOT EXISTS customers (
    customer_id VARCHAR(10) PRIMARY KEY,
    customer_name VARCHAR(50) NOT NULL,
    email VARCHAR(100) UNIQUE,
    phone_no CHAR(10) NOT NULL UNIQUE,
    address VARCHAR(100),
    joining_date DATE NOT NULL
);

-- Product Table
CREATE TABLE IF NOT EXISTS products (
    product_id VARCHAR(10) PRIMARY KEY,
    product_name VARCHAR(100) NOT NULL,
    stock_quantity INT NOT NULL CHECK (stock_quantity >= 0),
    price DECIMAL(10, 2) NOT NULL CHECK (price >= 0),
    discount_percent DECIMAL(5, 2) DEFAULT 0.00 CHECK (discount_percent BETWEEN 0 AND 100)
);

-- Bill Master Table
CREATE TABLE IF NOT EXISTS bills (
    bill_no INT AUTO_INCREMENT PRIMARY KEY,
    customer_id VARCHAR(10) NOT NULL,
    bill_date DATETIME DEFAULT CURRENT_TIMESTAMP,
    total_amount DECIMAL(10, 2) DEFAULT 0.00,
    discount_amount DECIMAL(10, 2) DEFAULT 0.00,
    net_amount DECIMAL(10, 2) DEFAULT 0.00,
    FOREIGN KEY (customer_id) REFERENCES customers(customer_id) ON DELETE CASCADE
);

-- Bill Items Table (Order Details)
CREATE TABLE IF NOT EXISTS bill_items (
    bill_item_id INT AUTO_INCREMENT PRIMARY KEY,
    bill_no INT NOT NULL,
    product_id VARCHAR(10) NOT NULL,
    quantity INT NOT NULL CHECK (quantity > 0),
    unit_price DECIMAL(10, 2) NOT NULL,
    discount_percent DECIMAL(5, 2) DEFAULT 0.00,
    item_total DECIMAL(10, 2) NOT NULL,
    FOREIGN KEY (bill_no) REFERENCES bills(bill_no) ON DELETE CASCADE,
    FOREIGN KEY (product_id) REFERENCES products(product_id) ON DELETE CASCADE
);

-- Price Change Log (Audit Log Table)
CREATE TABLE IF NOT EXISTS product_price_history (
    audit_id INT AUTO_INCREMENT PRIMARY KEY,
    product_id VARCHAR(10) NOT NULL,
    old_price DECIMAL(10, 2),
    new_price DECIMAL(10, 2),
    changed_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- ======================================================================
-- 2. SQL FUNCTIONS
-- ======================================================================

DROP FUNCTION IF EXISTS fn_calculate_item_total;
DELIMITER //
CREATE FUNCTION fn_calculate_item_total(quantity INT, price DECIMAL(10, 2), discount DECIMAL(5, 2))
RETURNS DECIMAL(10, 2)
DETERMINISTIC
BEGIN
    DECLARE subtotal DECIMAL(10, 2);
    SET subtotal = quantity * price;
    RETURN ROUND(subtotal - (subtotal * discount / 100), 2);
END //
DELIMITER ;

DROP FUNCTION IF EXISTS fn_get_customer_total_spent;
DELIMITER //
CREATE FUNCTION fn_get_customer_total_spent(cust_id VARCHAR(10))
RETURNS DECIMAL(10, 2)
DETERMINISTIC
BEGIN
    DECLARE total DECIMAL(10, 2);
    SELECT IFNULL(SUM(net_amount), 0.00) INTO total FROM bills WHERE customer_id = cust_id;
    RETURN total;
END //
DELIMITER ;

-- ======================================================================
-- 3. SQL PROCEDURES
-- ======================================================================

-- Procedure to create a new empty bill
DROP PROCEDURE IF EXISTS sp_create_bill;
DELIMITER //
CREATE PROCEDURE sp_create_bill(IN p_customer_id VARCHAR(10), OUT p_bill_no INT)
BEGIN
    INSERT INTO bills (customer_id, total_amount, discount_amount, net_amount)
    VALUES (p_customer_id, 0.00, 0.00, 0.00);
    SET p_bill_no = LAST_INSERT_ID();
END //
DELIMITER ;

-- Procedure to add items to a bill
DROP PROCEDURE IF EXISTS sp_add_bill_item;
DELIMITER //
CREATE PROCEDURE sp_add_bill_item(IN p_bill_no INT, IN p_product_id VARCHAR(10), IN p_quantity INT)
BEGIN
    DECLARE v_price DECIMAL(10, 2);
    DECLARE v_discount DECIMAL(5, 2);
    DECLARE v_item_total DECIMAL(10, 2);
    DECLARE v_item_discount_amt DECIMAL(10, 2);
    DECLARE v_item_gross_amt DECIMAL(10, 2);

    -- Retrieve product price and discount
    SELECT price, discount_percent INTO v_price, v_discount
    FROM products WHERE product_id = p_product_id;

    -- Calculate total price using function
    SET v_item_total = fn_calculate_item_total(p_quantity, v_price, v_discount);
    SET v_item_gross_amt = p_quantity * v_price;
    SET v_item_discount_amt = v_item_gross_amt - v_item_total;

    -- Insert record into bill_items
    -- (The trg_check_stock_before_purchase trigger will check availability and rollback if stock is too low)
    -- (The trg_update_stock_on_purchase trigger will decrement stock quantity)
    INSERT INTO bill_items (bill_no, product_id, quantity, unit_price, discount_percent, item_total)
    VALUES (p_bill_no, p_product_id, p_quantity, v_price, v_discount, v_item_total);

    -- Update bill totals
    UPDATE bills
    SET total_amount = total_amount + v_item_gross_amt,
        discount_amount = discount_amount + v_item_discount_amt,
        net_amount = net_amount + v_item_total
    WHERE bill_no = p_bill_no;
END //
DELIMITER ;

-- Procedure to fetch detailed customer report
DROP PROCEDURE IF EXISTS sp_get_customer_report;
DELIMITER //
CREATE PROCEDURE sp_get_customer_report(IN p_customer_id VARCHAR(10))
BEGIN
    SELECT b.bill_no, b.bill_date, b.total_amount, b.discount_amount, b.net_amount
    FROM bills b
    WHERE b.customer_id = p_customer_id
    ORDER BY b.bill_date DESC;
END //
DELIMITER ;

-- ======================================================================
-- 4. SQL TRIGGERS
-- ======================================================================

-- Trigger to check if stock is available BEFORE purchase
DROP TRIGGER IF EXISTS trg_check_stock_before_purchase;
DELIMITER //
CREATE TRIGGER trg_check_stock_before_purchase
BEFORE INSERT ON bill_items
FOR EACH ROW
BEGIN
    DECLARE v_available_stock INT;
    SELECT stock_quantity INTO v_available_stock
    FROM products WHERE product_id = NEW.product_id;

    IF v_available_stock IS NULL THEN
        SIGNAL SQLSTATE '45000'
        SET MESSAGE_TEXT = 'Product not found';
    ELSEIF v_available_stock < NEW.quantity THEN
        SIGNAL SQLSTATE '45000'
        SET MESSAGE_TEXT = 'Insufficient stock';
    END IF;
END //
DELIMITER ;

-- Trigger to update product stock level AFTER purchase item addition
DROP TRIGGER IF EXISTS trg_update_stock_on_purchase;
DELIMITER //
CREATE TRIGGER trg_update_stock_on_purchase
AFTER INSERT ON bill_items
FOR EACH ROW
BEGIN
    UPDATE products
    SET stock_quantity = stock_quantity - NEW.quantity
    WHERE product_id = NEW.product_id;
END //
DELIMITER ;

-- Trigger to record history logs when a product price changes
DROP TRIGGER IF EXISTS trg_audit_product_price_change;
DELIMITER //
CREATE TRIGGER trg_audit_product_price_change
AFTER UPDATE ON products
FOR EACH ROW
BEGIN
    IF OLD.price <> NEW.price THEN
        INSERT INTO product_price_history (product_id, old_price, new_price)
        VALUES (NEW.product_id, OLD.price, NEW.price);
    END IF;
END //
DELIMITER ;

-- ======================================================================
-- 5. DATABASE VIEWS
-- ======================================================================

-- View for sales invoice item level breakdown
CREATE OR REPLACE VIEW view_sales_invoice_details AS
SELECT 
    b.bill_no,
    b.bill_date,
    c.customer_id,
    c.customer_name,
    c.phone_no,
    p.product_id,
    p.product_name,
    bi.quantity,
    bi.unit_price,
    bi.discount_percent,
    bi.item_total,
    b.total_amount AS invoice_total_gross,
    b.discount_amount AS invoice_total_discount,
    b.net_amount AS invoice_net_payable
FROM bills b
JOIN customers c ON b.customer_id = c.customer_id
JOIN bill_items bi ON b.bill_no = bi.bill_no
JOIN products p ON bi.product_id = p.product_id;

-- View of customers list alongside metrics (bills count and total spent via function)
CREATE OR REPLACE VIEW view_customer_spending_summary AS
SELECT 
    c.customer_id,
    c.customer_name,
    c.phone_no,
    COUNT(b.bill_no) AS total_bills,
    fn_get_customer_total_spent(c.customer_id) AS total_spent
FROM customers c
LEFT JOIN bills b ON c.customer_id = b.customer_id
GROUP BY c.customer_id, c.customer_name, c.phone_no;

-- View for listing products with stock levels below 5
CREATE OR REPLACE VIEW view_low_stock_alerts AS
SELECT 
    product_id,
    product_name,
    stock_quantity,
    price
FROM products
WHERE stock_quantity < 5;
