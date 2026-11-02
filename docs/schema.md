# MCA & GST Database Schema Documentation

This document describes the schema structure, data types, constraints, and relationships for the **Ministry of Corporate Affairs (MCA)** and **Goods & Services Tax (GST)** databases used by the LangGraph SQL Agents.

---

## Architecture Overview

The system operates across two separate, authoritative databases:
1. **MCA Database (`mca_db`)**: Manages registered Indian corporate entities and their directors.
2. **GST Database (`gst_db`)**: Manages registered taxpayers, turnover slabs, trade names, and taxpayer compliance states.

---

## 🏛️ Part 1: MCA Corporate Database

### 1. `companies` Table
Stores official corporate registrations from the Ministry of Corporate Affairs.

| Column | Data Type | Nullable | Key | Description |
|---|---|---|---|---|
| `cin_llpin` | `VARCHAR(21)` | No | PK | Corporate Identification Number (CIN) or LLPIN |
| `company_name` | `VARCHAR(200)` | No | Index | Registered legal name of the entity |
| `entity_type` | `VARCHAR(50)` | Yes | | Type of entity (e.g., 'Company', 'LLP') |
| `registration_date` | `DATE / VARCHAR` | Yes | | Date of incorporation |
| `state` | `VARCHAR(100)` | Yes | Index | State where registered office is located |
| `city_district` | `VARCHAR(100)` | Yes | | District / city location |
| `pincode` | `VARCHAR(10)` | Yes | | Postal PIN code |
| `roc` | `VARCHAR(50)` | Yes | | Registrar of Companies office jurisdiction |
| `activity_code` | `VARCHAR(20)` | Yes | | Industrial / business activity classification code |
| `activity_description`| `TEXT` | Yes | | Description of corporate business activities |
| `class` | `VARCHAR(50)` | Yes | | Class of company (e.g., 'Private', 'Public') |
| `category` | `VARCHAR(100)` | Yes | | Category of company |
| `subcategory` | `VARCHAR(100)` | Yes | | Subcategory of company |
| `authorized_capital` | `BIGINT / DECIMAL` | Yes | Index | Total authorized share capital in INR |
| `paid_up_capital` | `BIGINT / DECIMAL` | Yes | | Paid-up share capital in INR |
| `registered_address` | `TEXT` | Yes | | Complete official registered postal address |
| `search_document` | `TEXT` | Yes | FULLTEXT | Consolidated virtual document for multi-column search |

---

### 2. `directors` Table
Stores appointed directors and designated partners associated with registered entities.

| Column | Data Type | Nullable | Key | Description |
|---|---|---|---|---|
| `din` | `VARCHAR(10)` | No | PK | Director Identification Number (DIN) |
| `cin_llpin` | `VARCHAR(21)` | No | FK | Reference to parent entity in `companies` |
| `director_name` | `VARCHAR(150)` | No | Index | Full legal name of the director |
| `designation` | `VARCHAR(80)` | Yes | | Role (e.g., 'Director', 'Managing Director') |
| `director_dob` | `DATE / VARCHAR` | Yes | | Date of birth |
| `gender` | `VARCHAR(20)` | Yes | | Gender classification |
| `director_email` | `VARCHAR(120)` | Yes | | Official registered email contact |
| `director_mobile` | `VARCHAR(20)` | Yes | | Official registered mobile contact |

#### Foreign Key Relationship
- `directors.cin_llpin` $\rightarrow$ `companies.cin_llpin`

---

## 🧾 Part 2: GST Taxpayer Database

### 3. `taxpayers` Table
Stores Goods and Services Tax (GST) registered entities and taxpayers across India.

| Column | Data Type | Nullable | Key | Description |
|---|---|---|---|---|
| `gstin` | `VARCHAR(15)` | No | PK | 15-digit Goods and Services Tax Identification Number |
| `legal_name` | `VARCHAR(200)` | No | Index | Formal legal entity name |
| `trade_name` | `VARCHAR(200)` | Yes | Index | Commercial operating trade brand name |
| `constitution` | `VARCHAR(100)` | Yes | | Constitution of business (e.g., 'Private Limited', 'Partnership') |
| `taxpayer_type` | `VARCHAR(50)` | Yes | | Taxpayer classification (e.g., 'Regular', 'Composition') |
| `nature_of_business` | `TEXT` | Yes | | Primary and secondary business activities |
| `turnover_slab` | `VARCHAR(50)` | Yes | Index | Annual turnover slab category (e.g., 'Rs. 0 to 40 lakhs', '500+ Cr') |
| `turnover_fy` | `VARCHAR(20)` | Yes | | Financial year associated with the turnover slab |
| `registration_date` | `DATE / VARCHAR` | Yes | | Date of GST registration |
| `status` | `VARCHAR(50)` | Yes | Index | Taxpayer status (e.g., 'Active', 'ACT', 'Cancelled') |
| `pan` | `VARCHAR(10)` | Yes | Index | 10-digit Permanent Account Number derived from GSTIN |
| `mobile` | `VARCHAR(20)` | Yes | | Registered taxpayer phone |
| `email` | `VARCHAR(120)` | Yes | | Registered taxpayer email |
| `address` | `TEXT` | Yes | | Principal place of business address |
| `city` | `VARCHAR(100)` | Yes | Index | Principal city location |
| `state` | `VARCHAR(100)` | Yes | Index | State of registration |
| `search_document` | `TEXT` | Yes | FULLTEXT | Consolidated virtual document for multi-column search |

---

## 🔒 Security & Table Allowlist

The AST validator ([`src/validation/validator.py`](file:///c:/Users/Admin/Desktop/langgraph-sql-agent/src/validation/validator.py)) enforces a strict allowlist:
- **MCA Agent**: Authorized to access `companies` and `directors`.
- **GST Agent**: Authorized to access `taxpayers`.

Any SQL query attempting to access tables outside these authorized sets is rejected before execution.
