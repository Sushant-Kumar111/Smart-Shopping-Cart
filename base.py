import mysql.connector
import os
import sys
import random
from datetime import datetime, date

# ======================================================================
# COLOR FORMATTING UTILITIES (ANSI Escape Codes)
# ======================================================================
COLOR_HEADER = "\033[95m"
COLOR_BLUE = "\033[94m"
COLOR_CYAN = "\033[96m"
COLOR_GREEN = "\033[92m"
COLOR_WARNING = "\033[93m"
COLOR_FAIL = "\033[91m"
COLOR_BOLD = "\033[1m"
COLOR_RESET = "\033[0m"

# Enable ANSI codes on Windows Command Prompt if needed
if os.name == 'nt':
    os.system('color')

def print_color(text, color, bold=False):
    style = COLOR_BOLD if bold else ""
    print(f"{style}{color}{text}{COLOR_RESET}")

def print_banner(title):
    print("\n" + "=" * 60)
    print_color(f" {title.center(58)} ", COLOR_HEADER, bold=True)
    print("=" * 60)

# ======================================================================
# DATA TABLE FORMATTING UTILITY
# ======================================================================
def print_table(headers, rows):
    if not rows:
        print_color("   No records found.", COLOR_WARNING)
        return
        
    # Determine column widths based on headers and row values
    col_widths = [len(h) for h in headers]
    for row in rows:
        for idx, val in enumerate(row):
            val_str = str(val) if val is not None else ""
            if idx < len(col_widths):
                col_widths[idx] = max(col_widths[idx], len(val_str))
                
    # Generate separator line
    separator = "+" + "+".join("-" * (w + 2) for w in col_widths) + "+"
    
    # Print table header
    print(separator)
    header_str = "| " + " | ".join(str(h).ljust(col_widths[i]) for i, h in enumerate(headers)) + " |"
    print_color(header_str, COLOR_BLUE, bold=True)
    print(separator)
    
    # Print rows
    for row in rows:
        row_str = "| " + " | ".join(str(val if val is not None else "").ljust(col_widths[i]) for i, val in enumerate(row)) + " |"
        print(row_str)
        
    print(separator)

# ======================================================================
# SQL SCRIPT PARSING AND EXECUTION
# ======================================================================
def run_sql_script(conn, filepath):
    cursor = conn.cursor()
    if not os.path.exists(filepath):
        print_color(f"Error: Schema file '{filepath}' not found!", COLOR_FAIL)
        sys.exit(1)
        
    with open(filepath, 'r', encoding='utf-8') as f:
        sql_file = f.read()

    statements = []
    current_stmt = []
    current_delimiter = ';'
    
    for line in sql_file.split('\n'):
        stripped = line.strip()
        
        # Skip empty lines and comment lines
        if not stripped or stripped.startswith('--') or stripped.startswith('#'):
            continue
            
        # Check if line changes delimiter
        if stripped.upper().startswith('DELIMITER'):
            parts = stripped.split()
            if len(parts) > 1:
                current_delimiter = parts[1]
            continue
            
        current_stmt.append(line)
        
        # Check if statement is complete
        if stripped.endswith(current_delimiter):
            stmt_text = '\n'.join(current_stmt)
            # Remove the delimiter from the end of the text
            if stmt_text.endswith(current_delimiter):
                stmt_text = stmt_text[:-len(current_delimiter)]
            stmt_text = stmt_text.strip()
            if stmt_text:
                statements.append(stmt_text)
            current_stmt = []
            
    for stmt in statements:
        try:
            cursor.execute(stmt)
        except mysql.connector.Error as err:
            print_color(f"SQL Initialization Error:\nQuery: {stmt[:150]}...\nMessage: {err}", COLOR_FAIL)
            conn.rollback()
            cursor.close()
            raise err
            
    conn.commit()
    cursor.close()

# ======================================================================
# DATABASE CONNECTION INITIALIZATION
# ======================================================================
def connect_db():
    # Attempt typical local connection credentials
    credentials = [
        {"host": "localhost", "user": "root", "password": "1234"},
        {"host": "localhost", "user": "root", "password": ""},
    ]
    
    mydb = None
    for cred in credentials:
        try:
            mydb = mysql.connector.connect(
                host=cred["host"],
                user=cred["user"],
                password=cred["password"]
            )
            if mydb.is_connected():
                print_color(f"Connected successfully as '{cred['user']}'!", COLOR_GREEN)
                break
        except mysql.connector.Error:
            continue
            
    if mydb is None or not mydb.is_connected():
        print_color("\nFailed to connect with default MySQL credentials.", COLOR_WARNING)
        host = input("Enter MySQL Host (default: localhost): ").strip() or "localhost"
        user = input("Enter MySQL User (default: root): ").strip() or "root"
        password = input("Enter MySQL Password: ")
        try:
            mydb = mysql.connector.connect(host=host, user=user, password=password)
            print_color("Connected successfully!", COLOR_GREEN)
        except mysql.connector.Error as e:
            print_color(f"Database Connection Error: {e}", COLOR_FAIL)
            sys.exit(1)
            
    # Check if database exists, initialize if not
    try:
        cursor = mydb.cursor()
        cursor.execute("SHOW DATABASES LIKE 'SHOPPING_MALL'")
        db_exists = cursor.fetchone()
        cursor.close()
        
        if not db_exists:
            print_color("Database 'SHOPPING_MALL' not detected. Running schema.sql setup...", COLOR_CYAN)
            run_sql_script(mydb, "schema.sql")
            print_color("Database setup complete!", COLOR_GREEN)
        else:
            mydb.database = 'SHOPPING_MALL'
    except mysql.connector.Error as e:
        print_color(f"Schema Initialization Check Failed: {e}", COLOR_FAIL)
        sys.exit(1)
        
    return mydb

# ======================================================================
# CUSTOMER OPERATION MODULE
# ======================================================================
def generate_customer_id(cursor):
    cursor.execute("SELECT customer_id FROM customers WHERE customer_id LIKE 'CUST%' ORDER BY customer_id DESC LIMIT 1")
    row = cursor.fetchone()
    if row:
        last_id = row[0]
        try:
            num = int(last_id[4:]) + 1
            return f"CUST{num:03d}"
        except ValueError:
            pass
    return "CUST001"

def add_customer(mydb):
    print_banner("ADD NEW CUSTOMER")
    cursor = mydb.cursor()
    
    # Generate sequential customer ID
    cust_id = generate_customer_id(cursor)
    print(f"Assigned Customer ID: {cust_id}")
    
    name = input("Enter Customer Name: ").strip()
    if not name:
        print_color("Error: Name cannot be empty.", COLOR_FAIL)
        cursor.close()
        return
        
    email = input("Enter Email Address (optional): ").strip() or None
    
    while True:
        phone = input("Enter 10-digit Phone Number: ").strip()
        if len(phone) == 10 and phone.isdigit():
            break
        print_color("Error: Phone number must be exactly 10 digits.", COLOR_FAIL)
        
    address = input("Enter Address: ").strip() or None
    joining_date = date.today().strftime("%Y-%m-%d")
    
    try:
        query = """INSERT INTO customers (customer_id, customer_name, email, phone_no, address, joining_date)
                   VALUES (%s, %s, %s, %s, %s, %s)"""
        cursor.execute(query, (cust_id, name, email, phone, address, joining_date))
        mydb.commit()
        print_color(f"Customer '{name}' registered successfully with ID {cust_id}!", COLOR_GREEN)
    except mysql.connector.Error as e:
        print_color(f"Database Error: {e}", COLOR_FAIL)
        mydb.rollback()
    finally:
        cursor.close()

def modify_customer(mydb):
    print_banner("MODIFY CUSTOMER DETAILS")
    cust_id = input("Enter Customer ID to update: ").strip().upper()
    
    cursor = mydb.cursor()
    cursor.execute("SELECT customer_name, email, phone_no, address FROM customers WHERE customer_id = %s", (cust_id,))
    customer = cursor.fetchone()
    
    if not customer:
        print_color(f"Error: Customer with ID '{cust_id}' does not exist.", COLOR_FAIL)
        cursor.close()
        return
        
    print(f"Current Details - Name: {customer[0]}, Email: {customer[1]}, Phone: {customer[2]}, Address: {customer[3]}")
    
    print("\nSelect what to update:")
    print("1. Update Name")
    print("2. Update Email")
    print("3. Update Phone Number")
    print("4. Update Address")
    print("5. Cancel")
    
    choice = input("Enter choice (1-5): ").strip()
    if choice == '1':
        new_val = input("Enter New Name: ").strip()
        query = "UPDATE customers SET customer_name = %s WHERE customer_id = %s"
    elif choice == '2':
        new_val = input("Enter New Email: ").strip() or None
        query = "UPDATE customers SET email = %s WHERE customer_id = %s"
    elif choice == '3':
        while True:
            new_val = input("Enter New 10-digit Phone: ").strip()
            if len(new_val) == 10 and new_val.isdigit():
                break
            print_color("Error: Phone number must be exactly 10 digits.", COLOR_FAIL)
        query = "UPDATE customers SET phone_no = %s WHERE customer_id = %s"
    elif choice == '4':
        new_val = input("Enter New Address: ").strip() or None
        query = "UPDATE customers SET address = %s WHERE customer_id = %s"
    else:
        print_color("Update cancelled.", COLOR_WARNING)
        cursor.close()
        return
        
    try:
        cursor.execute(query, (new_val, cust_id))
        mydb.commit()
        print_color("Customer record updated successfully!", COLOR_GREEN)
    except mysql.connector.Error as e:
        print_color(f"Database Error: {e}", COLOR_FAIL)
        mydb.rollback()
    finally:
        cursor.close()

def delete_customer(mydb):
    print_banner("DELETE CUSTOMER")
    cust_id = input("Enter Customer ID to delete: ").strip().upper()
    
    cursor = mydb.cursor()
    cursor.execute("SELECT customer_name FROM customers WHERE customer_id = %s", (cust_id,))
    customer = cursor.fetchone()
    
    if not customer:
        print_color(f"Error: Customer with ID '{cust_id}' does not exist.", COLOR_FAIL)
        cursor.close()
        return
        
    confirm = input(f"Are you sure you want to delete customer '{customer[0]}' (ID: {cust_id})? (y/n): ").strip().lower()
    if confirm == 'y':
        try:
            cursor.execute("DELETE FROM customers WHERE customer_id = %s", (cust_id,))
            mydb.commit()
            print_color("Customer profile deleted successfully.", COLOR_GREEN)
        except mysql.connector.Error as e:
            print_color(f"Database Error: {e}", COLOR_FAIL)
            mydb.rollback()
    else:
        print_color("Deletion aborted.", COLOR_WARNING)
        
    cursor.close()

def show_customers_directory(mydb):
    print_banner("REGISTERED CUSTOMERS DIRECTORY")
    cursor = mydb.cursor()
    # Query view_customer_spending_summary
    cursor.execute("SELECT customer_id, customer_name, phone_no, total_bills, total_spent FROM view_customer_spending_summary")
    rows = cursor.fetchall()
    
    headers = ["Customer ID", "Customer Name", "Phone No", "Total Bills", "Total Spent ($)"]
    print_table(headers, rows)
    cursor.close()

def search_customer_report(mydb):
    print_banner("SEARCH CUSTOMER SPENDING REPORT")
    cust_id = input("Enter Customer ID: ").strip().upper()
    
    cursor = mydb.cursor()
    cursor.execute("SELECT customer_name, phone_no, email FROM customers WHERE customer_id = %s", (cust_id,))
    customer = cursor.fetchone()
    
    if not customer:
        print_color(f"Customer with ID '{cust_id}' not found.", COLOR_FAIL)
        cursor.close()
        return
        
    print_color(f"Customer Name: {customer[0]} | Phone: {customer[1]} | Email: {customer[2]}", COLOR_CYAN, bold=True)
    
    # Call stored procedure sp_get_customer_report
    try:
        cursor.execute("CALL sp_get_customer_report(%s)", (cust_id,))
        rows = cursor.fetchall()
        
        print("\nPurchase Invoices:")
        headers = ["Invoice No", "Invoice Date", "Gross Amount ($)", "Discount Amount ($)", "Net Payable ($)"]
        print_table(headers, rows)
    except mysql.connector.Error as e:
        print_color(f"Error fetching report: {e}", COLOR_FAIL)
    finally:
        cursor.close()

# ======================================================================
# PRODUCT OPERATION MODULE
# ======================================================================
def add_product(mydb):
    print_banner("ADD NEW PRODUCT STOCK")
    cursor = mydb.cursor()
    
    print_color("  Tip: Product ID format — e.g. PROD01, PROD02, ... (auto-converted to uppercase)", COLOR_CYAN)
    prod_id = input("Enter Product ID (e.g. PROD01): ").strip().upper()
    if not prod_id:
        print_color("Error: Product ID cannot be empty.", COLOR_FAIL)
        cursor.close()
        return
        
    cursor.execute("SELECT product_name, stock_quantity FROM products WHERE product_id = %s", (prod_id,))
    existing = cursor.fetchone()
    if existing:
        print_color(f"Product ID '{prod_id}' already exists as '{existing[0]}' (Current Stock: {existing[1]})", COLOR_WARNING)
        choice = input("Do you want to add quantity to existing stock instead? (y/n): ").strip().lower()
        if choice == 'y':
            try:
                qty = int(input("Enter quantity to add: "))
                if qty < 0:
                    raise ValueError()
                cursor.execute("UPDATE products SET stock_quantity = stock_quantity + %s WHERE product_id = %s", (qty, prod_id))
                mydb.commit()
                print_color("Stock replenished successfully!", COLOR_GREEN)
            except ValueError:
                print_color("Invalid quantity input.", COLOR_FAIL)
            except mysql.connector.Error as e:
                print_color(f"Database Error: {e}", COLOR_FAIL)
        cursor.close()
        return

    name = input("Enter Product Name: ").strip()
    try:
        qty = int(input("Enter Initial Quantity: "))
        price = float(input("Enter Selling Price ($): "))
        discount = float(input("Enter Discount Rate (%): "))
        
        if qty < 0 or price < 0 or not (0 <= discount <= 100):
            raise ValueError()
            
        query = """INSERT INTO products (product_id, product_name, stock_quantity, price, discount_percent)
                   VALUES (%s, %s, %s, %s, %s)"""
        cursor.execute(query, (prod_id, name, qty, price, discount))
        mydb.commit()
        print_color(f"Product '{name}' added successfully!", COLOR_GREEN)
    except ValueError:
        print_color("Error: Invalid numeric values entered for quantity, price, or discount.", COLOR_FAIL)
    except mysql.connector.Error as e:
        print_color(f"Database Error: {e}", COLOR_FAIL)
        mydb.rollback()
    finally:
        cursor.close()

def modify_product(mydb):
    print_banner("MODIFY PRODUCT DETAILS")
    prod_id = input("Enter Product ID to update: ").strip().upper()
    
    cursor = mydb.cursor()
    cursor.execute("SELECT product_name, stock_quantity, price, discount_percent FROM products WHERE product_id = %s", (prod_id,))
    product = cursor.fetchone()
    
    if not product:
        print_color(f"Error: Product '{prod_id}' does not exist.", COLOR_FAIL)
        cursor.close()
        return
        
    print(f"Current Details - Name: {product[0]}, Stock: {product[1]}, Price: ${product[2]}, Discount: {product[3]}%")
    
    print("\nSelect detail to update:")
    print("1. Update Name")
    print("2. Update Stock Quantity")
    print("3. Update Price (Triggers Audit log)")
    print("4. Update Discount Percentage")
    print("5. Cancel")
    
    choice = input("Enter choice (1-5): ").strip()
    if choice == '1':
        new_val = input("Enter New Name: ").strip()
        query = "UPDATE products SET product_name = %s WHERE product_id = %s"
        params = (new_val, prod_id)
    elif choice == '2':
        try:
            new_val = int(input("Enter New Stock Quantity: "))
            if new_val < 0:
                raise ValueError()
            query = "UPDATE products SET stock_quantity = %s WHERE product_id = %s"
            params = (new_val, prod_id)
        except ValueError:
            print_color("Invalid stock input.", COLOR_FAIL)
            cursor.close()
            return
    elif choice == '3':
        try:
            new_val = float(input("Enter New Price ($): "))
            if new_val < 0:
                raise ValueError()
            query = "UPDATE products SET price = %s WHERE product_id = %s"
            params = (new_val, prod_id)
        except ValueError:
            print_color("Invalid price input.", COLOR_FAIL)
            cursor.close()
            return
    elif choice == '4':
        try:
            new_val = float(input("Enter New Discount Percentage (%): "))
            if not (0 <= new_val <= 100):
                raise ValueError()
            query = "UPDATE products SET discount_percent = %s WHERE product_id = %s"
            params = (new_val, prod_id)
        except ValueError:
            print_color("Invalid discount percentage.", COLOR_FAIL)
            cursor.close()
            return
    else:
        print_color("Update cancelled.", COLOR_WARNING)
        cursor.close()
        return
        
    try:
        cursor.execute(query, params)
        mydb.commit()
        print_color("Product updated successfully!", COLOR_GREEN)
    except mysql.connector.Error as e:
        print_color(f"Database Error: {e}", COLOR_FAIL)
        mydb.rollback()
    finally:
        cursor.close()

def delete_product(mydb):
    print_banner("DELETE PRODUCT")
    prod_id = input("Enter Product ID to delete: ").strip().upper()
    
    cursor = mydb.cursor()
    cursor.execute("SELECT product_name FROM products WHERE product_id = %s", (prod_id,))
    product = cursor.fetchone()
    
    if not product:
        print_color(f"Error: Product '{prod_id}' does not exist.", COLOR_FAIL)
        cursor.close()
        return
        
    confirm = input(f"Are you sure you want to delete product '{product[0]}' (ID: {prod_id})? (y/n): ").strip().lower()
    if confirm == 'y':
        try:
            cursor.execute("DELETE FROM products WHERE product_id = %s", (prod_id,))
            mydb.commit()
            print_color("Product removed successfully.", COLOR_GREEN)
        except mysql.connector.Error as e:
            print_color(f"Database Error: {e}", COLOR_FAIL)
            mydb.rollback()
    else:
        print_color("Deletion aborted.", COLOR_WARNING)
        
    cursor.close()

def show_all_products(mydb):
    print_banner("AVAILABLE STOCKS")
    cursor = mydb.cursor()
    cursor.execute("SELECT product_id, product_name, stock_quantity, price, discount_percent FROM products")
    rows = cursor.fetchall()
    
    headers = ["Product ID", "Product Name", "Quantity Left", "Price ($)", "Discount (%)"]
    print_table(headers, rows)
    cursor.close()

def show_low_stock_alerts(mydb):
    print_banner("LOW STOCK WARNINGS (STOCK < 5)")
    cursor = mydb.cursor()
    # Query view_low_stock_alerts
    cursor.execute("SELECT product_id, product_name, stock_quantity, price FROM view_low_stock_alerts")
    rows = cursor.fetchall()
    
    headers = ["Product ID", "Product Name", "Quantity Remaining", "Price ($)"]
    print_table(headers, rows)
    cursor.close()

def show_price_audit_history(mydb):
    print_banner("PRODUCT PRICE AUDIT LOGS")
    cursor = mydb.cursor()
    cursor.execute("""
        SELECT h.audit_id, h.product_id, p.product_name, h.old_price, h.new_price, h.changed_at 
        FROM product_price_history h 
        JOIN products p ON h.product_id = p.product_id 
        ORDER BY h.changed_at DESC
    """)
    rows = cursor.fetchall()
    
    headers = ["Audit ID", "Product ID", "Product Name", "Old Price ($)", "New Price ($)", "Timestamp"]
    print_table(headers, rows)
    cursor.close()

# ======================================================================
# BILLING & TRANSACTION MODULE
# ======================================================================
def create_bill_flow(mydb):
    print_banner("NEW BILLING INVOICE TRANSACTION")
    cursor = mydb.cursor()
    
    # 1. Customer Verification/Registration
    cust_id = input("Enter Customer ID: ").strip().upper()
    cursor.execute("SELECT customer_name FROM customers WHERE customer_id = %s", (cust_id,))
    cust_row = cursor.fetchone()
    
    if not cust_row:
        print_color(f"Customer '{cust_id}' is not registered.", COLOR_WARNING)
        choice = input("Do you want to register them now? (y/n): ").strip().lower()
        if choice == 'y':
            cust_id = generate_customer_id(cursor)
            print(f"Assigned Customer ID: {cust_id}")
            name = input("Enter Customer Name: ").strip()
            if not name:
                print_color("Invalid Customer Name. Aborting.", COLOR_FAIL)
                cursor.close()
                return
            email = input("Enter Email: ").strip() or None
            while True:
                phone = input("Enter 10-digit Phone: ").strip()
                if len(phone) == 10 and phone.isdigit():
                    break
                print_color("Error: Must be 10 digits.", COLOR_FAIL)
            address = input("Enter Address: ").strip() or None
            joining_date = date.today().strftime("%Y-%m-%d")
            
            try:
                cursor.execute("""INSERT INTO customers (customer_id, customer_name, email, phone_no, address, joining_date)
                                  VALUES (%s, %s, %s, %s, %s, %s)""", (cust_id, name, email, phone, address, joining_date))
                mydb.commit()
                print_color("Customer registered successfully!", COLOR_GREEN)
            except mysql.connector.Error as e:
                print_color(f"Failed to register customer: {e}", COLOR_FAIL)
                cursor.close()
                return
        else:
            print_color("Cannot process transaction without a customer.", COLOR_FAIL)
            cursor.close()
            return

    # 2. Create Master Bill record via procedure
    try:
        # Call procedure to insert empty bill and fetch bill_no
        cursor.execute("CALL sp_create_bill(%s, @bill_no)", (cust_id,))
        cursor.execute("SELECT @bill_no")
        bill_no = cursor.fetchone()[0]
        mydb.commit()
        print_color(f"Created Invoice #{bill_no}. Add items below.", COLOR_CYAN)
    except mysql.connector.Error as e:
        print_color(f"Database error while generating invoice: {e}", COLOR_FAIL)
        cursor.close()
        return

    # 3. Add Items Loop
    while True:
        prod_id = input("\nEnter Product ID to purchase: ").strip().upper()
        
        # Check product existence
        cursor.execute("SELECT product_name, stock_quantity, price FROM products WHERE product_id = %s", (prod_id,))
        prod_row = cursor.fetchone()
        if not prod_row:
            print_color("Product ID not found. Please try again.", COLOR_WARNING)
            continue
            
        print(f"Product: {prod_row[0]} | Stock Available: {prod_row[1]} | Unit Price: ${prod_row[2]}")
        
        try:
            qty = int(input("Enter purchase quantity: "))
            if qty <= 0:
                print_color("Quantity must be greater than zero.", COLOR_WARNING)
                continue
                
            # Attempt to add to bill items via procedure
            # (Triggers check stock before insert & update stock after insert)
            cursor.execute("CALL sp_add_bill_item(%s, %s, %s)", (bill_no, prod_id, qty))
            mydb.commit()
            print_color(f"Successfully added {qty} of '{prod_row[0]}' to cart.", COLOR_GREEN)
            
        except mysql.connector.Error as e:
            # Catch custom triggers SQLSTATE 45000 errors (Insufficient stock / Product not found)
            print_color(f"Transaction Denied: {e.msg}", COLOR_FAIL)
            mydb.rollback()
        except ValueError:
            print_color("Invalid quantity format.", COLOR_WARNING)
            
        choice = input("Add more products to this invoice? (y/n): ").strip().lower()
        if choice != 'y':
            break
            
    # 4. Generate & Display Final invoice from view
    print_invoice(mydb, bill_no)
    cursor.close()

def print_invoice(mydb, bill_no):
    cursor = mydb.cursor()
    # Query invoice breakdown view
    cursor.execute("""
        SELECT bill_date, customer_id, customer_name, phone_no, 
               product_id, product_name, quantity, unit_price, 
               discount_percent, item_total, invoice_total_gross, 
               invoice_total_discount, invoice_net_payable
        FROM view_sales_invoice_details
        WHERE bill_no = %s
    """, (bill_no,))
    
    rows = cursor.fetchall()
    if not rows:
        print_color(f"\nInvoice #{bill_no} is empty.", COLOR_WARNING)
        cursor.close()
        return

    first_row = rows[0]
    bill_date = first_row[0]
    cust_id = first_row[1]
    cust_name = first_row[2]
    phone = first_row[3]
    gross_total = first_row[10]
    discount_total = first_row[11]
    net_payable = first_row[12]

    # Print Gorgeous Invoice
    print("\n" + "*" * 70)
    print_color("THE GREAT INDIAN MALL".center(70), COLOR_HEADER, bold=True)
    print_color("INDIRA NAGAR, LUCKNOW".center(70), COLOR_HEADER)
    print_color("Contact: support@greatindianmall.com | Tel: 011-91522123".center(70), COLOR_RESET)
    print("*" * 70)
    print(f" Invoice ID   : {bill_no:<25} Date/Time : {bill_date}")
    print(f" Customer ID  : {cust_id:<25} Phone     : {phone}")
    print(f" Customer Name: {cust_name}")
    print("-" * 70)
    
    # Items table headers
    print(f"{'Product ID':<12} {'Product Name':<20} {'Qty':<6} {'Unit Price':<12} {'Disc%':<7} {'Total ($)':<10}")
    print("-" * 70)
    for row in rows:
        p_id, p_name, qty, price, disc, total = row[4], row[5], row[6], row[7], row[8], row[9]
        # Truncate long product names for clean table formatting
        p_name_display = p_name[:18] + '..' if len(p_name) > 20 else p_name
        print(f"{p_id:<12} {p_name_display:<20} {qty:<6} ${price:<11} {disc:<6}% ${total:<10}")
        
    print("-" * 70)
    print(f"{'':<40} Gross Total:      ${gross_total:>10}")
    print(f"{'':<40} Total Discount:   ${discount_total:>10}")
    print_color(f"{'':<40} Net Payable:      ${net_payable:>10}", COLOR_GREEN, bold=True)
    print("*" * 70)
    print_color("Thank you for shopping with us! See you soon!".center(70), COLOR_CYAN)
    print("*" * 70 + "\n")
    
    cursor.close()

def view_all_invoices(mydb):
    print_banner("SALES INVOICES DIRECTORY")
    cursor = mydb.cursor()
    cursor.execute("""
        SELECT b.bill_no, b.bill_date, b.customer_id, c.customer_name, 
               b.total_amount, b.discount_amount, b.net_amount 
        FROM bills b 
        JOIN customers c ON b.customer_id = c.customer_id
        ORDER BY b.bill_no DESC
    """)
    rows = cursor.fetchall()
    
    headers = ["Invoice No", "Date", "Customer ID", "Customer Name", "Gross ($)", "Discount ($)", "Net Paid ($)"]
    print_table(headers, rows)
    
    if rows:
        details_choice = input("Enter Invoice No to print details (or press enter to skip): ").strip()
        if details_choice.isdigit():
            print_invoice(mydb, int(details_choice))
    cursor.close()

# ======================================================================
# MENU ROUTER LOGIC
# ======================================================================
def product_menu(mydb):
    while True:
        print_banner("PRODUCT INVENTORY MENU")
        print_color("1. Add/Replenish Product Stock", COLOR_CYAN)
        print_color("2. Modify Product Details", COLOR_CYAN)
        print_color("3. Delete Product from Inventory", COLOR_CYAN)
        print_color("4. Display All Available Stocks", COLOR_CYAN)
        print_color("5. Display Low Stock Warnings (< 5 items)", COLOR_CYAN)
        print_color("6. View Product Price Audit Logs", COLOR_CYAN)
        print_color("7. Return to Main Menu", COLOR_CYAN)
        
        choice = input("\nEnter selection (1-7): ").strip()
        if choice == '1':
            add_product(mydb)
        elif choice == '2':
            modify_product(mydb)
        elif choice == '3':
            delete_product(mydb)
        elif choice == '4':
            show_all_products(mydb)
        elif choice == '5':
            show_low_stock_alerts(mydb)
        elif choice == '6':
            show_price_audit_history(mydb)
        elif choice == '7':
            break
        else:
            print_color("Invalid choice. Try again.", COLOR_FAIL)

def customer_menu(mydb):
    while True:
        print_banner("CUSTOMER MANAGEMENT MENU")
        print_color("1. Add New Customer Profile", COLOR_CYAN)
        print_color("2. Modify Customer Details", COLOR_CYAN)
        print_color("3. Delete Customer Profile", COLOR_CYAN)
        print_color("4. View Customers Directory", COLOR_CYAN)
        print_color("5. Search Customer & Spending Report", COLOR_CYAN)
        print_color("6. Return to Main Menu", COLOR_CYAN)
        
        choice = input("\nEnter selection (1-6): ").strip()
        if choice == '1':
            add_customer(mydb)
        elif choice == '2':
            modify_customer(mydb)
        elif choice == '3':
            delete_customer(mydb)
        elif choice == '4':
            show_customers_directory(mydb)
        elif choice == '5':
            search_customer_report(mydb)
        elif choice == '6':
            break
        else:
            print_color("Invalid choice. Try again.", COLOR_FAIL)

def bill_menu(mydb):
    while True:
        print_banner("BILLING & SALES INVOICES")
        print_color("1. Create New Invoice (Checkout)", COLOR_CYAN)
        print_color("2. View Sales Invoices Directory", COLOR_CYAN)
        print_color("3. Return to Main Menu", COLOR_CYAN)
        
        choice = input("\nEnter selection (1-3): ").strip()
        if choice == '1':
            create_bill_flow(mydb)
        elif choice == '2':
            view_all_invoices(mydb)
        elif choice == '3':
            break
        else:
            print_color("Invalid choice. Try again.", COLOR_FAIL)

def main():
    print_color("=" * 60, COLOR_HEADER, bold=True)
    print_color("       WELCOME TO THE GREAT INDIAN MALL SYSTEM REDESIGNED       ", COLOR_HEADER, bold=True)
    print_color("=" * 60, COLOR_HEADER, bold=True)
    
    mydb = connect_db()
    
    while True:
        print_banner("MAIN CONTROL PANEL")
        print_color("1. Product Inventory Menu", COLOR_CYAN)
        print_color("2. Customer Management Menu", COLOR_CYAN)
        print_color("3. Billing & Transactions Menu", COLOR_CYAN)
        print_color("4. Exit Application", COLOR_CYAN)
        
        choice = input("\nEnter selection (1-4): ").strip()
        if choice == '1':
            product_menu(mydb)
        elif choice == '2':
            customer_menu(mydb)
        elif choice == '3':
            bill_menu(mydb)
        elif choice == '4':
            print_color("\nClosing connections. Goodbye!", COLOR_HEADER, bold=True)
            mydb.close()
            sys.exit(0)
        else:
            print_color("Invalid choice. Try again.", COLOR_FAIL)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print_color("\nProgram terminated by user. Goodbye!", COLOR_HEADER, bold=True)
        sys.exit(0)
