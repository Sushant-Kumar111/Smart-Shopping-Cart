# Technical Interview Guide: Shopping Cart System Redesign

This guide explains the architecture, design patterns, security improvements, and MySQL database features introduced in the redesigned Shopping Cart project. Use this to prepare for your project technical interview.

---

## 1. Project Redesign: Before vs. After

| Feature | Base Version (Original) | Redesigned Version (New) | Why It Matters |
| :--- | :--- | :--- | :--- |
| **Normalization** | Unnormalized (Flat tables, redundant customer/product names in bill table). | Fully Normalized (3NF) across 5 separate tables with foreign key constraints. | Eliminates data redundancy, prevents database anomalies, and maintains referential integrity. |
| **Security** | Vulnerable to SQL Injection (uses `.format()` to inject raw strings into SQL queries). | Parameterized queries (`%s` placeholders passed via cursor parameters). | Prevents SQL injection attacks, protecting customer data and database stability. |
| **Business Logic** | Handled in Python code (manual updates to stock quantities in loops). | Handled at the database level using stored procedures and triggers. | Decouples business logic from client code, ensuring transactions remain consistent regardless of the client (web, mobile, or CLI). |
| **Error Handling** | Standard Python try-except (crashes or inserts invalid/out-of-stock items). | DB triggers throw formal exceptions (`SIGNAL SQLSTATE '45000'`) caught by Python. | Database acts as the final gatekeeper for data rules, ensuring inventory never drops below zero. |
| **Interface & Reports** | Primitive console prints using generic tabs `\t`. | Dynamically aligned ASCII tables (`print_table()`) and pre-calculated views. | Looks professional, matches industry CLI designs, and speeds up report generation. |

---

## 2. Relational Database Design & Normalization (3NF)

### What is Normalization?
Normalization is the process of organizing data in a database to reduce redundancy and eliminate anomalies. It involves dividing large tables into smaller tables and defining relationships between them.

### What are Database Anomalies?
If we do not normalize, we encounter three major anomalies:
1.  **Insertion Anomaly**: We cannot insert a bill without a product, or we cannot store a customer's address until they place their first bill if they are in the same table.
2.  **Update Anomaly**: If a customer changes their phone number and it is duplicated in every bill, we must update many records. If we miss one, we have inconsistent data.
3.  **Deletion Anomaly**: If we delete a customer's only transaction, we lose their customer profile (name, phone number, address) entirely.

### The 3NF Schema Breakdown
We split the schema into five distinct tables:
1.  **`customers`**: Unique record for each client (ID, name, email, phone, address, joining date).
2.  **`products`**: Unique record for each product (ID, name, stock quantity, unit price, discount percentage).
3.  **`bills`** (Order Master): General invoice details (Bill Number, Customer ID, Bill Date, Gross Total, Discount Total, Net Payable).
4.  **`bill_items`** (Order Details): Individual product line-items for each bill. Resolves the **Many-to-Many** relationship between Bills and Products (one bill has many products; one product can be in many bills).
5.  **`product_price_history`**: Audit trail. Keeps track of historic prices of products.

---

## 3. Advanced Database Features Explained

### A. SQL Functions (Scalar Functions)
*   **What they are**: Executable blocks of SQL that take inputs, perform operations, and return a single scalar value.
*   **Functions used**:
    *   `fn_calculate_item_total(quantity, price, discount)`: Computes the post-discount price for an item: 
        $$\text{Total} = (\text{Quantity} \times \text{Price}) \times \left(1 - \frac{\text{Discount}}{100}\right)$$
    *   `fn_get_customer_total_spent(cust_id)`: Aggregates net bill amounts for a single customer.
*   **Why use them**: Standardize pricing calculations. If the discount formula changes (e.g., compounding tax or loyalty calculations), we only change it in this function, and it automatically updates everywhere: views, billing procedures, and reports.

### B. SQL Triggers
*   **What they are**: Automated blocks of SQL code that execute ("fire") in response to events (`INSERT`, `UPDATE`, or `DELETE`) on a table.
*   **Triggers used**:
    *   `trg_check_stock_before_purchase` (`BEFORE INSERT ON bill_items`):
        *   Checks `products.stock_quantity` before inserting an item into `bill_items`.
        *   If the requested quantity is greater than the available stock, it throws an exception:
            ```sql
            SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Insufficient stock';
            ```
    *   `trg_update_stock_on_purchase` (`AFTER INSERT ON bill_items`):
        *   Automatically deducts the purchased quantity from `products.stock_quantity` after a successful item insertion.
    *   `trg_audit_product_price_change` (`AFTER UPDATE ON products`):
        *   Detects if `OLD.price` is different from `NEW.price`. If so, inserts a record into `product_price_history` containing the old price, new price, and timestamp.
*   **Why use them**: Triggers enforce **data integrity** and **business logic** at the database engine layer. They guarantee rules are followed even if a developer writes an buggy script that tries to bypass stock checks.

### C. Stored Procedures
*   **What they are**: Precompiled SQL statements stored in the database that can accept parameters and execute complex transactional routines.
*   **Procedures used**:
    *   `sp_create_bill(customer_id, OUT bill_no)`: Places a new entry in `bills` and returns the auto-incremented invoice number.
    *   `sp_add_bill_item(bill_no, product_id, quantity)`: Gathers product price/discount metadata, calls the scalar function to get the price, inserts it into `bill_items` (which fires the stock check trigger), and updates the master bill's gross, discount, and net totals.
    *   `sp_get_customer_report(customer_id)`: Returns all previous invoices for a customer.
*   **Why use them**:
    *   **Performance**: Minimizes client-server roundtrips. Instead of querying the price, running math in Python, inserting the item, and then updating totals, we do it in one single call: `CALL sp_add_bill_item(...)`.
    *   **Abstraction**: Hides complex table relationships from client code.

### D. Database Views
*   **What they are**: Virtual tables represented by a saved SQL query. You query views exactly like a normal table.
*   **Views used**:
    *   `view_sales_invoice_details`: Joins customer, bills, bill items, and product details. Used to print clean invoices.
    *   `view_customer_spending_summary`: Aggregates customer purchase totals.
    *   `view_low_stock_alerts`: Shows products with stock < 5.
*   **Why use them**: Replaces massive, multi-join queries with simple statements (e.g. `SELECT * FROM view_low_stock_alerts`). This simplifies the Python code and makes database queries easier to optimize.

---

## 4. Python Application Architecture

### SQL Injection Prevention
*   **The Threat**: In the old code:
    ```python
    mycursor.execute("SELECT * FROM CUSTOMER_TABLE where CUSTOMER_ID= '{}'".format(z))
    ```
    If an attacker entered `' OR '1'='1`, the query executed as:
    ```sql
    SELECT * FROM CUSTOMER_TABLE where CUSTOMER_ID= '' OR '1'='1'
    ```
    This prints *all* customers in the database, bypassing search logic.
*   **The Solution**: Parameterized queries:
    ```python
    cursor.execute("SELECT customer_name FROM customers WHERE customer_id = %s", (cust_id,))
    ```
    The MySQL driver treats the input strictly as a literal value (a search ID string), neutralising any SQL commands.

### Delimiter Parsing in Python
MySQL script engines use the `DELIMITER` command to change the statement terminator from `;` to `//`. This lets you write routines (procedures/functions) that contain semicolons inside their `BEGIN...END` blocks without executing prematurely.
Because standard Python drivers do not support the client-side `DELIMITER` keyword natively, we wrote a line-by-line parser in `base.py` (`run_sql_script`) that dynamically switches delimiters, groups multi-line triggers and procedures, and executes them cleanly.

---

## 5. Potential Interview Questions & Answers

### Q1: Why did you choose MySQL stored procedures/triggers instead of performing the logic inside Python?
**Answer**: By implementing calculations (functions) and stock validations (triggers) inside MySQL, we create a **thick database model** that enforces business rules directly on the data. If we build a mobile app, a web app, and a CLI app in the future, we don't have to duplicate the stock-check code in Swift, Javascript, and Python. The database acts as a single, consistent gatekeeper. It also saves network bandwidth by reducing the number of SQL queries sent back and forth.

### Q2: What is the difference between a Stored Procedure and a Function?
**Answer**: 
*   **Stored Procedure**: Invoked with `CALL`. It can return multiple values (via `OUT` parameters) or a complete result set. It can contain transactions (`COMMIT`/`ROLLBACK`) and perform writes to tables.
*   **Function**: Invoked directly inside SQL queries (e.g., `SELECT fn_calculate(...)`). It must return exactly one value of a defined type. It is deterministic/non-deterministic and cannot perform table modifications or run transaction control commands.

### Q3: Explain how your application handles race conditions when two customers buy the last item at the exact same time.
**Answer**: Our database schema enforces a `CHECK (stock_quantity >= 0)` constraint on the `products` table. Additionally, when a purchase is made, the `BEFORE INSERT` trigger on `bill_items` validates that the available stock is sufficient. If two clients execute concurrently, MySQL handles rows using internal locks. The transaction that updates the stock first locks the product row. The second transaction waits, detects that the stock is now depleted, and the trigger aborts the insert with `SIGNAL SQLSTATE '45000'`. Python catches this exception, rolls back the transaction, and outputs a friendly message: "Transaction Denied: Insufficient stock".

### Q4: Why did you use `LEFT JOIN` in `view_customer_spending_summary` instead of `INNER JOIN`?
**Answer**: An `INNER JOIN` only returns rows where there is a match in both tables. If a customer is newly registered and hasn't placed any bills yet, an `INNER JOIN` would exclude them from the summary. By using a `LEFT JOIN` from `customers` to `bills`, we guarantee that *all* customers are listed, showing 0 bills and $0.00 spent.

### Q5: What is SQLSTATE '45000' that you used in your triggers?
**Answer**: `SQLSTATE` is a five-character code defined by SQL standards to indicate database error conditions. The state `'45000'` is a generic state that represents a "user-defined exception". We use it to trigger a runtime database error from our custom code (like inventory checks), which rolls back the query and alerts the client application.
