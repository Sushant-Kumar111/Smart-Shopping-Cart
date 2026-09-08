# 🛒 Smart Shopping Cart

A **database-driven terminal billing & inventory management system** built with **Python** and **MySQL**.  
Simulates a real-world retail mall checkout system with full CRUD operations, automated billing, stock management, and audit logging.

---

## 📋 Table of Contents

- [Features](#-features)
- [Tech Stack](#-tech-stack)
- [Database Architecture](#-database-architecture)
- [Project Structure](#-project-structure)
- [Setup & Installation](#-setup--installation)
- [How to Run](#-how-to-run)
- [Module Walkthrough](#-module-walkthrough)
- [ID Format Guide](#-id-format-guide)
- [Sample Invoice Output](#-sample-invoice-output)

---

## ✨ Features

### 🧑‍💼 Customer Management
- Register new customers with auto-generated IDs (e.g. `CUST001`)
- Modify customer name, email, phone, or address
- Delete customer profiles
- View all registered customers with total spending summary
- Search individual customer purchase history

### 📦 Product Inventory
- Add new products with custom ID (e.g. `PROD01`), name, quantity, price, and discount
- Replenish existing product stock
- Modify product details (price change triggers audit log automatically)
- Delete products from inventory
- View all available stock
- Low stock alerts for products with fewer than 5 units
- Full price change audit history

### 🧾 Billing & Invoicing
- Create invoices linked to registered customers
- Add multiple products in one invoice session
- Real-time stock validation — auto-rejects if stock is insufficient
- Automatic discount calculations per item
- Beautifully formatted terminal invoice printout
- View all past invoices and reprint any invoice

---

## 🛠 Tech Stack

| Layer        | Technology                          |
|--------------|-------------------------------------|
| Language     | Python 3.x                          |
| Database     | MySQL (via mysql-connector-python)  |
| Interface    | Terminal / CLI (ANSI colored output)|
| DB Schema    | Normalized to 3NF                   |

---

## 🗄 Database Architecture

### Tables

| Table                  | Description                              |
|------------------------|------------------------------------------|
| customers              | Stores customer profiles                 |
| products               | Stores product catalog and stock levels  |
| bills                  | Master invoice records                   |
| bill_items             | Line items within each invoice           |
| product_price_history  | Audit log for price changes              |

### Stored Procedures

| Procedure               | Purpose                                                   |
|-------------------------|-----------------------------------------------------------|
| sp_create_bill          | Creates a new empty invoice                               |
| sp_add_bill_item        | Adds a product to a bill with price/discount calculation  |
| sp_get_customer_report  | Returns full invoice history for a customer               |

### Functions

| Function                    | Purpose                                          |
|-----------------------------|--------------------------------------------------|
| fn_calculate_item_total     | Calculates discounted total for a bill item      |
| fn_get_customer_total_spent | Returns lifetime total spend for a customer      |

### Triggers

| Trigger                          | Event                      | Purpose                                      |
|----------------------------------|----------------------------|----------------------------------------------|
| trg_check_stock_before_purchase  | BEFORE INSERT on bill_items| Rejects purchase if stock is insufficient    |
| trg_update_stock_on_purchase     | AFTER INSERT on bill_items | Decrements product stock after purchase      |
| trg_audit_product_price_change   | AFTER UPDATE on products   | Logs old/new price to audit table            |

### Views

| View                          | Purpose                                        |
|-------------------------------|------------------------------------------------|
| view_sales_invoice_details    | Full item-level invoice breakdown              |
| view_customer_spending_summary| Customers listed with total bills and spending |
| view_low_stock_alerts         | Products with stock less than 5 units          |

---

## 📁 Project Structure

```
Smart-Shopping-Cart/
│
├── base.py              # Main Python application (all modules)
├── schema.sql           # Full MySQL schema (tables, triggers, views, procedures)
├── interview_guide.md   # Conceptual Q&A guide for the project
└── README.md            # This file
```

---

## ⚙️ Setup & Installation

### Prerequisites

- Python 3.8+
- MySQL Server running locally
- mysql-connector-python package

### Step 1 — Install Python dependency

```bash
pip install mysql-connector-python
```

### Step 2 — Start MySQL Server

Make sure MySQL is running on localhost.  
The app automatically tries these credentials:
- root / 1234
- root / (empty password)

If neither works, you will be prompted to enter your credentials manually.

### Step 3 — No manual DB setup needed

The app automatically detects if the SHOPPING_MALL database exists.  
If not found, it runs schema.sql to create all tables, procedures, triggers, and views automatically.

---

## ▶️ How to Run

```bash
python base.py
```

You will see the Main Control Panel:

```
============================================================
                    MAIN CONTROL PANEL
============================================================
1. Product Inventory Menu
2. Customer Management Menu
3. Billing & Sales Invoices
4. Exit
```

---

## 🧭 Module Walkthrough

### Product Inventory Menu
```
1. Add/Replenish Product Stock
2. Modify Product Details
3. Delete Product from Inventory
4. Display All Available Stocks
5. Display Low Stock Warnings (< 5 items)
6. View Product Price Audit Logs
7. Return to Main Menu
```

### Customer Management Menu
```
1. Add New Customer Profile
2. Modify Customer Details
3. Delete Customer Profile
4. View Customers Directory
5. Search Customer & Spending Report
6. Return to Main Menu
```

### Billing & Sales Invoices
```
1. Create New Invoice (Checkout)
2. View Sales Invoices Directory
3. Return to Main Menu
```

---

## 🪪 ID Format Guide

| Entity      | Format                          | Example         |
|-------------|----------------------------------|-----------------|
| Customer ID | CUST + 3 digits (auto-generated) | CUST001, CUST002|
| Product ID  | PROD + 2 digits (admin-defined)  | PROD01, PROD02  |
| Invoice No  | Auto-incremented integer         | 1, 2, 3         |

> **Note:** All IDs are automatically converted to **UPPERCASE** regardless of how you type them.

---

## 🧾 Sample Invoice Output

```
**********************************************************************
                     THE GREAT INDIAN MALL
                      INDIRA NAGAR, LUCKNOW
          Contact: support@greatindianmall.com | Tel: 011-91522123
**********************************************************************
 Invoice ID   : 1                         Date/Time : 2026-09-09 00:30:00
 Customer ID  : CUST001                   Phone     : 9876543210
 Customer Name: Sushant Kumar
----------------------------------------------------------------------
Product ID   Product Name         Qty    Unit Price   Disc%  Total
----------------------------------------------------------------------
PROD01       Wireless Headphones  2      .00     10%    .00
PROD02       USB-C Hub            1      .00     5%     .00
----------------------------------------------------------------------
                                        Gross Total:      $   6400.00
                                        Total Discount:   $    760.00
                                        Net Payable:      $   5640.00
**********************************************************************
              Thank you for shopping with us! See you soon!
**********************************************************************
```

---

## 👨‍💻 Author

**Sushant Kumar**  
GitHub: [Sushant-Kumar111](https://github.com/Sushant-Kumar111)

---

## 📄 License

This project is open source and available under the [MIT License](LICENSE).
