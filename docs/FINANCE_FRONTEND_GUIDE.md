# Finance Module Frontend Integration Guide

## Table of Contents
1. [Overview](#overview)
2. [Database Setup](#database-setup)
3. [API Endpoints](#api-endpoints)
4. [Frontend Views & UI](#frontend-views--ui)
5. [Integration Examples](#integration-examples)
6. [Error Handling](#error-handling)
7. [State Management](#state-management)

---

## Overview

The Finance Module provides a complete cash ledger system for doctors with:
- **Multi-ledger support**: Doctors can create separate cash books (Medicine, Equipment, General)
- **Transaction tracking**: Record income/expenses with automatic running balance
- **Custom fields**: Extensible schemas per ledger (Supplier, Invoice #, Expiry Date, etc.)
- **Financial reports**: Per-book and aggregated summaries
- **Soft deletes**: Audit trail for deleted transactions
- **Dynamic enums**: Transaction natures and categories managed dynamically

**Key Concepts:**
- **CashBook**: Independent ledger owned by a doctor
- **Transaction**: Single income/expense entry with running balance
- **Custom Fields**: Additional metadata per transaction
- **Nature**: CASH_IN or CASH_OUT (income vs. expense)
- **Category**: Classification (MEDICINE_PURCHASE, CONSULTATION, SALARY, etc.)

---

## Database Setup

### Step 1: Generate Alembic Migration

```bash
# From project root
cd f:\2_PROJECTS\B_PMS\pms_backend

# Generate migration for finance tables
alembic revision --autogenerate -m "Add finance module tables"
```

### Step 2: Review Generated Migration

Check the generated file in `alembic/versions/` - it should create:
- `finance_cash_book`
- `finance_cash_book_custom_field`
- `finance_transaction`
- `finance_transaction_custom_field_value`

### Step 3: Apply Migration

```bash
# Apply migration to database
alembic upgrade head
```

### Step 4: Seed Enums

```bash
# Seed core enums
python scripts/seed_enums.py

# Seed finance-specific enums
python scripts/seed_finance_enums.py
```

---

## API Endpoints

### Authentication
All endpoints require Bearer token in Authorization header:
```
Authorization: Bearer {jwt_token}
```

### Enum Reference

**Transaction Nature** (from `/enums/doctor/TransactionNature`):
- `CASH_IN` - Income / Sales / Receipts
- `CASH_OUT` - Expenses / Purchases / Payments

**Transaction Category** (from `/enums/doctor/TransactionCategory`):
- `MEDICINE_PURCHASE` - Medicines and pharmacy stock
- `CONSULTATION` - Patient consultation income
- `EQUIPMENT` - Medical or clinic equipment
- `UTILITIES` - Electricity, water, internet
- `SALARY` - Staff salary payments
- `RENT` - Clinic or office rent
- `LAB_INCOME` - Laboratory test income
- `PROCEDURE_INCOME` - Minor procedure income
- `OTHER` - Miscellaneous

---

## CASH BOOK ENDPOINTS

### 1. Create Cash Book
**POST** `/finance/cash-books`

Create a new named ledger for the doctor.

**Request:**
```bash
curl -X POST http://localhost:8000/finance/cash-books \
  -H "Authorization: Bearer {token}" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Medicine Book",
    "description": "Track medicine purchases and sales"
  }'
```

**Response (200):**
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "name": "Medicine Book",
  "description": "Track medicine purchases and sales",
  "is_active": true,
  "doctor_id": "1ffd1a39-e9a3-46d3-8cd3-950dab11455e",
  "created_at": "2026-02-28T11:20:00",
  "updated_at": null
}
```

**Frontend View:**
```typescript
// CashBookForm.tsx
import { useState } from 'react'
import { useMutation, useQueryClient } from '@tanstack/react-query'

export function CashBookForm() {
  const [name, setName] = useState('')
  const [description, setDescription] = useState('')
  const queryClient = useQueryClient()

  const createBook = useMutation({
    mutationFn: (data) => fetch('/finance/cash-books', {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${getToken()}`,
        'Content-Type': 'application/json'
      },
      body: JSON.stringify(data)
    }).then(r => r.json()),
    onSuccess: () => {
      queryClient.invalidateQueries(['cashBooks'])
      setName('')
      setDescription('')
      alert('Cash book created!')
    }
  })

  return (
    <form onSubmit={(e) => {
      e.preventDefault()
      createBook.mutate({ name, description })
    }}>
      <input 
        type="text" 
        placeholder="Book name (e.g., Medicine Book)"
        value={name}
        onChange={(e) => setName(e.target.value)}
        required
      />
      <textarea
        placeholder="Description (optional)"
        value={description}
        onChange={(e) => setDescription(e.target.value)}
      />
      <button type="submit" disabled={createBook.isPending}>
        Create Book
      </button>
    </form>
  )
}
```

---

### 2. List Cash Books
**GET** `/finance/cash-books?active_only=true&skip=0&limit=100`

Get all cash books owned by the authenticated doctor.

**Query Parameters:**
- `active_only` (boolean, default: true) - Only return active books
- `skip` (integer, default: 0) - Pagination offset
- `limit` (integer, default: 100, max: 1000) - Page size

**Request:**
```bash
curl -X GET "http://localhost:8000/finance/cash-books?active_only=true&skip=0&limit=100" \
  -H "Authorization: Bearer {token}"
```

**Response (200):**
```json
{
  "data": [
    {
      "id": "550e8400-e29b-41d4-a716-446655440000",
      "name": "Medicine Book",
      "description": "Track medicine purchases",
      "is_active": true,
      "doctor_id": "1ffd1a39-e9a3-46d3-8cd3-950dab11455e",
      "created_at": "2026-02-28T11:20:00",
      "updated_at": null
    },
    {
      "id": "660e8400-e29b-41d4-a716-446655440001",
      "name": "Equipment Book",
      "description": "Medical equipment purchases",
      "is_active": true,
      "doctor_id": "1ffd1a39-e9a3-46d3-8cd3-950dab11455e",
      "created_at": "2026-02-28T11:22:00",
      "updated_at": null
    }
  ],
  "count": 2
}
```

**Frontend View:**
```typescript
// CashBookList.tsx
import { useQuery } from '@tanstack/react-query'

export function CashBookList() {
  const { data, isLoading } = useQuery({
    queryKey: ['cashBooks'],
    queryFn: () => fetch('/finance/cash-books', {
      headers: { 'Authorization': `Bearer ${getToken()}` }
    }).then(r => r.json())
  })

  if (isLoading) return <div>Loading...</div>

  return (
    <div className="cash-books">
      <h2>My Cash Books</h2>
      <div className="books-grid">
        {data?.data?.map(book => (
          <div key={book.id} className="book-card">
            <h3>{book.name}</h3>
            <p>{book.description}</p>
            <div className="book-meta">
              <span className="status">
                {book.is_active ? '✓ Active' : '✗ Inactive'}
              </span>
              <span className="date">
                Created: {new Date(book.created_at).toLocaleDateString()}
              </span>
            </div>
            <div className="book-actions">
              <button onClick={() => viewTransactions(book.id)}>
                View Transactions
              </button>
              <button onClick={() => editBook(book.id)}>Edit</button>
              <button onClick={() => deleteBook(book.id)}>Delete</button>
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}
```

---

### 3. Get Single Cash Book
**GET** `/finance/cash-books/{cash_book_id}`

Retrieve details of a specific cash book.

**Request:**
```bash
curl -X GET http://localhost:8000/finance/cash-books/550e8400-e29b-41d4-a716-446655440000 \
  -H "Authorization: Bearer {token}"
```

**Response (200):**
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "name": "Medicine Book",
  "description": "Track medicine purchases",
  "is_active": true,
  "doctor_id": "1ffd1a39-e9a3-46d3-8cd3-950dab11455e",
  "created_at": "2026-02-28T11:20:00",
  "updated_at": null
}
```

---

### 4. Update Cash Book
**PATCH** `/finance/cash-books/{cash_book_id}`

Edit name, description, or active status.

**Request:**
```bash
curl -X PATCH http://localhost:8000/finance/cash-books/550e8400-e29b-41d4-a716-446655440000 \
  -H "Authorization: Bearer {token}" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Medicine & Pharmacy Book",
    "is_active": true
  }'
```

**Response (200):**
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "name": "Medicine & Pharmacy Book",
  "description": "Track medicine purchases",
  "is_active": true,
  "doctor_id": "1ffd1a39-e9a3-46d3-8cd3-950dab11455e",
  "created_at": "2026-02-28T11:20:00",
  "updated_at": "2026-02-28T11:25:00"
}
```

---

### 5. Delete Cash Book
**DELETE** `/finance/cash-books/{cash_book_id}`

Hard-delete a cash book and all its transactions. (Consider deactivating instead: PATCH with `is_active: false`)

**Request:**
```bash
curl -X DELETE http://localhost:8000/finance/cash-books/550e8400-e29b-41d4-a716-446655440000 \
  -H "Authorization: Bearer {token}"
```

**Response (200):**
```json
{
  "message": "Cash book deleted successfully"
}
```

---

## CUSTOM FIELDS ENDPOINTS

Custom fields allow you to attach additional metadata to transactions (e.g., supplier name, invoice number, expiry date).

### 1. Add Custom Field
**POST** `/finance/cash-books/{cash_book_id}/custom-fields`

Define a custom field schema for a book.

**Request:**
```bash
curl -X POST http://localhost:8000/finance/cash-books/550e8400-e29b-41d4-a716-446655440000/custom-fields \
  -H "Authorization: Bearer {token}" \
  -H "Content-Type: application/json" \
  -d '{
    "field_key": "supplier_name",
    "field_label": "Supplier Name",
    "field_type": "text",
    "is_required": true,
    "display_order": 1
  }'
```

**Field Types:**
- `text` - Plain text input
- `number` - Numeric input (for quantities, units, etc.)
- `date` - Date picker
- `boolean` - Checkbox

**Response (200):**
```json
{
  "id": "770e8400-e29b-41d4-a716-446655440002",
  "cash_book_id": "550e8400-e29b-41d4-a716-446655440000",
  "field_key": "supplier_name",
  "field_label": "Supplier Name",
  "field_type": "text",
  "is_required": true,
  "display_order": 1,
  "is_active": true
}
```

**Frontend View:**
```typescript
// CustomFieldForm.tsx
export function CustomFieldForm({ cashBookId }) {
  const [fields, setFields] = useState([
    { field_key: '', field_label: '', field_type: 'text', is_required: false, display_order: 0 }
  ])

  const addField = () => {
    setFields([...fields, { 
      field_key: '', 
      field_label: '', 
      field_type: 'text', 
      is_required: false, 
      display_order: fields.length 
    }])
  }

  return (
    <div className="custom-fields-form">
      <h3>Define Custom Fields</h3>
      {fields.map((field, idx) => (
        <div key={idx} className="field-row">
          <input
            placeholder="Field key (e.g., supplier_name)"
            value={field.field_key}
            onChange={(e) => {
              const newFields = [...fields]
              newFields[idx].field_key = e.target.value
              setFields(newFields)
            }}
          />
          <input
            placeholder="Field label (e.g., Supplier Name)"
            value={field.field_label}
            onChange={(e) => {
              const newFields = [...fields]
              newFields[idx].field_label = e.target.value
              setFields(newFields)
            }}
          />
          <select 
            value={field.field_type}
            onChange={(e) => {
              const newFields = [...fields]
              newFields[idx].field_type = e.target.value
              setFields(newFields)
            }}
          >
            <option value="text">Text</option>
            <option value="number">Number</option>
            <option value="date">Date</option>
            <option value="boolean">Checkbox</option>
          </select>
          <label>
            <input 
              type="checkbox"
              checked={field.is_required}
              onChange={(e) => {
                const newFields = [...fields]
                newFields[idx].is_required = e.target.checked
                setFields(newFields)
              }}
            />
            Required
          </label>
        </div>
      ))}
      <button onClick={addField}>+ Add Field</button>
      <button onClick={saveFields}>Save All Fields</button>
    </div>
  )
}
```

---

### 2. List Custom Fields
**GET** `/finance/cash-books/{cash_book_id}/custom-fields?active_only=true`

Get custom field definitions for a book.

**Request:**
```bash
curl -X GET "http://localhost:8000/finance/cash-books/550e8400-e29b-41d4-a716-446655440000/custom-fields" \
  -H "Authorization: Bearer {token}"
```

**Response (200):**
```json
[
  {
    "id": "770e8400-e29b-41d4-a716-446655440002",
    "cash_book_id": "550e8400-e29b-41d4-a716-446655440000",
    "field_key": "supplier_name",
    "field_label": "Supplier Name",
    "field_type": "text",
    "is_required": true,
    "display_order": 1,
    "is_active": true
  },
  {
    "id": "880e8400-e29b-41d4-a716-446655440003",
    "cash_book_id": "550e8400-e29b-41d4-a716-446655440000",
    "field_key": "invoice_number",
    "field_label": "Invoice Number",
    "field_type": "text",
    "is_required": false,
    "display_order": 2,
    "is_active": true
  }
]
```

---

### 3. Update Custom Field
**PATCH** `/finance/custom-fields/{field_id}`

Modify a custom field definition (cannot change field_key).

**Request:**
```bash
curl -X PATCH http://localhost:8000/finance/custom-fields/770e8400-e29b-41d4-a716-446655440002 \
  -H "Authorization: Bearer {token}" \
  -H "Content-Type: application/json" \
  -d '{
    "field_label": "Vendor Name",
    "is_required": false,
    "display_order": 2
  }'
```

**Response (200):**
```json
{
  "id": "770e8400-e29b-41d4-a716-446655440002",
  "cash_book_id": "550e8400-e29b-41d4-a716-446655440000",
  "field_key": "supplier_name",
  "field_label": "Vendor Name",
  "field_type": "text",
  "is_required": false,
  "display_order": 2,
  "is_active": true
}
```

---

### 4. Deactivate Custom Field
**DELETE** `/finance/custom-fields/{field_id}`

Soft-delete (deactivate) a custom field. Historical values preserved.

**Request:**
```bash
curl -X DELETE http://localhost:8000/finance/custom-fields/770e8400-e29b-41d4-a716-446655440002 \
  -H "Authorization: Bearer {token}"
```

**Response (200):**
```json
{
  "message": "Custom field deactivated successfully"
}
```

---

## TRANSACTION ENDPOINTS

### 1. Create Transaction
**POST** `/finance/transactions`

Record a new income or expense.

**Request:**
```bash
curl -X POST http://localhost:8000/finance/transactions \
  -H "Authorization: Bearer {token}" \
  -H "Content-Type: application/json" \
  -d '{
    "cash_book_id": "550e8400-e29b-41d4-a716-446655440000",
    "nature_code": "CASH_OUT",
    "category_code": "MEDICINE_PURCHASE",
    "amount": 5000.50,
    "transaction_date": "2026-02-28",
    "remarks": "Monthly medicine stock purchase",
    "custom_field_values": {
      "supplier_name": "ABC Pharmacy",
      "invoice_number": "INV-2026-001"
    }
  }'
```

**Response (200):**
```json
{
  "id": "990e8400-e29b-41d4-a716-446655440004",
  "cash_book_id": "550e8400-e29b-41d4-a716-446655440000",
  "doctor_id": "1ffd1a39-e9a3-46d3-8cd3-950dab11455e",
  "nature_code": "CASH_OUT",
  "category_code": "MEDICINE_PURCHASE",
  "amount": 5000.50,
  "transaction_date": "2026-02-28",
  "remarks": "Monthly medicine stock purchase",
  "running_balance": -5000.50,
  "is_deleted": false,
  "created_at": "2026-02-28T11:30:00",
  "updated_at": null
}
```

**Frontend View:**
```typescript
// TransactionForm.tsx
import { useMutation, useQuery } from '@tanstack/react-query'

export function TransactionForm({ cashBookId }) {
  const [formData, setFormData] = useState({
    nature_code: 'CASH_OUT',
    category_code: '',
    amount: '',
    transaction_date: new Date().toISOString().split('T')[0],
    remarks: '',
    custom_field_values: {}
  })

  const { data: enums } = useQuery({
    queryKey: ['enums'],
    queryFn: () => Promise.all([
      fetch('/enums/doctor/TransactionNature', {
        headers: { 'Authorization': `Bearer ${getToken()}` }
      }).then(r => r.json()),
      fetch('/enums/doctor/TransactionCategory', {
        headers: { 'Authorization': `Bearer ${getToken()}` }
      }).then(r => r.json())
    ]).then(([natures, categories]) => ({ natures, categories }))
  })

  const createTxn = useMutation({
    mutationFn: (data) => fetch('/finance/transactions', {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${getToken()}`,
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({ ...data, cash_book_id: cashBookId })
    }).then(r => r.json()),
    onSuccess: () => {
      alert('Transaction recorded!')
      setFormData({ ...formData, amount: '', remarks: '', custom_field_values: {} })
    }
  })

  return (
    <form onSubmit={(e) => {
      e.preventDefault()
      createTxn.mutate(formData)
    }}>
      <div className="form-group">
        <label>Transaction Type</label>
        <select
          value={formData.nature_code}
          onChange={(e) => setFormData({ ...formData, nature_code: e.target.value })}
        >
          {enums?.natures?.map(n => (
            <option key={n.value} value={n.value}>
              {n.label}
            </option>
          ))}
        </select>
      </div>

      <div className="form-group">
        <label>Category</label>
        <select
          value={formData.category_code}
          onChange={(e) => setFormData({ ...formData, category_code: e.target.value })}
          required
        >
          <option value="">Select category...</option>
          {enums?.categories?.map(c => (
            <option key={c.value} value={c.value}>
              {c.label}
            </option>
          ))}
        </select>
      </div>

      <div className="form-group">
        <label>Amount</label>
        <input
          type="number"
          step="0.01"
          value={formData.amount}
          onChange={(e) => setFormData({ ...formData, amount: parseFloat(e.target.value) })}
          required
        />
      </div>

      <div className="form-group">
        <label>Date</label>
        <input
          type="date"
          value={formData.transaction_date}
          onChange={(e) => setFormData({ ...formData, transaction_date: e.target.value })}
        />
      </div>

      <div className="form-group">
        <label>Remarks</label>
        <textarea
          value={formData.remarks}
          onChange={(e) => setFormData({ ...formData, remarks: e.target.value })}
        />
      </div>

      <button type="submit" disabled={createTxn.isPending}>
        {createTxn.isPending ? 'Recording...' : 'Record Transaction'}
      </button>
    </form>
  )
}
```

---

### 2. List Transactions
**GET** `/finance/transactions?cash_book_id={id}&start_date=&end_date=&nature_code=&category_code=&include_deleted=false&skip=0&limit=100`

Get transactions for a cash book with optional filters.

**Query Parameters:**
- `cash_book_id` (**required**) - UUID of cash book
- `start_date` (optional) - Filter >= this date (ISO format)
- `end_date` (optional) - Filter <= this date (ISO format)
- `nature_code` (optional) - "CASH_IN" or "CASH_OUT"
- `category_code` (optional) - Filter by category
- `include_deleted` (boolean, default: false) - Include soft-deleted transactions
- `skip` (integer, default: 0) - Pagination offset
- `limit` (integer, default: 100) - Page size

**Request:**
```bash
curl -X GET "http://localhost:8000/finance/transactions?cash_book_id=550e8400-e29b-41d4-a716-446655440000&start_date=2026-02-01&end_date=2026-02-28" \
  -H "Authorization: Bearer {token}"
```

**Response (200):**
```json
{
  "data": [
    {
      "id": "990e8400-e29b-41d4-a716-446655440004",
      "cash_book_id": "550e8400-e29b-41d4-a716-446655440000",
      "doctor_id": "1ffd1a39-e9a3-46d3-8cd3-950dab11455e",
      "nature_code": "CASH_OUT",
      "category_code": "MEDICINE_PURCHASE",
      "amount": 5000.50,
      "transaction_date": "2026-02-28",
      "remarks": "Monthly medicines",
      "running_balance": -5000.50,
      "is_deleted": false,
      "created_at": "2026-02-28T11:30:00",
      "updated_at": null
    },
    {
      "id": "aa0e8400-e29b-41d4-a716-446655440005",
      "cash_book_id": "550e8400-e29b-41d4-a716-446655440000",
      "doctor_id": "1ffd1a39-e9a3-46d3-8cd3-950dab11455e",
      "nature_code": "CASH_IN",
      "category_code": "CONSULTATION",
      "amount": 1500.00,
      "transaction_date": "2026-02-28",
      "remarks": "Patient consultation",
      "running_balance": -3500.50,
      "is_deleted": false,
      "created_at": "2026-02-28T14:45:00",
      "updated_at": null
    }
  ],
  "count": 2
}
```

**Frontend View:**
```typescript
// TransactionList.tsx
export function TransactionList({ cashBookId }) {
  const [filters, setFilters] = useState({
    start_date: '',
    end_date: '',
    nature_code: '',
    category_code: ''
  })

  const { data: transactions, isLoading } = useQuery({
    queryKey: ['transactions', cashBookId, filters],
    queryFn: () => {
      const params = new URLSearchParams({
        cash_book_id: cashBookId,
        ...filters,
        skip: '0',
        limit: '100'
      })
      return fetch(`/finance/transactions?${params}`, {
        headers: { 'Authorization': `Bearer ${getToken()}` }
      }).then(r => r.json())
    }
  })

  return (
    <div className="transaction-list">
      <div className="filters">
        <input
          type="date"
          value={filters.start_date}
          onChange={(e) => setFilters({ ...filters, start_date: e.target.value })}
          placeholder="From date"
        />
        <input
          type="date"
          value={filters.end_date}
          onChange={(e) => setFilters({ ...filters, end_date: e.target.value })}
          placeholder="To date"
        />
        <select
          value={filters.nature_code}
          onChange={(e) => setFilters({ ...filters, nature_code: e.target.value })}
        >
          <option value="">All Types</option>
          <option value="CASH_IN">Income</option>
          <option value="CASH_OUT">Expense</option>
        </select>
      </div>

      {isLoading ? <div>Loading...</div> : (
        <table>
          <thead>
            <tr>
              <th>Date</th>
              <th>Category</th>
              <th>Type</th>
              <th>Amount</th>
              <th>Running Balance</th>
              <th>Actions</th>
            </tr>
          </thead>
          <tbody>
            {transactions?.data?.map(txn => (
              <tr key={txn.id} className={txn.nature_code === 'CASH_IN' ? 'income' : 'expense'}>
                <td>{new Date(txn.transaction_date).toLocaleDateString()}</td>
                <td>{txn.category_code}</td>
                <td>{txn.nature_code === 'CASH_IN' ? '↓ In' : '↑ Out'}</td>
                <td className="amount">
                  {txn.nature_code === 'CASH_IN' ? '+' : '-'}{txn.amount.toFixed(2)}
                </td>
                <td className={txn.running_balance >= 0 ? 'positive' : 'negative'}>
                  {txn.running_balance.toFixed(2)}
                </td>
                <td>
                  <button onClick={() => editTxn(txn.id)}>Edit</button>
                  <button onClick={() => deleteTxn(txn.id)}>Delete</button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  )
}
```

---

### 3. Get Single Transaction
**GET** `/finance/transactions/{transaction_id}`

Retrieve full details of a transaction.

**Request:**
```bash
curl -X GET http://localhost:8000/finance/transactions/990e8400-e29b-41d4-a716-446655440004 \
  -H "Authorization: Bearer {token}"
```

**Response (200):**
```json
{
  "id": "990e8400-e29b-41d4-a716-446655440004",
  "cash_book_id": "550e8400-e29b-41d4-a716-446655440000",
  "doctor_id": "1ffd1a39-e9a3-46d3-8cd3-950dab11455e",
  "nature_code": "CASH_OUT",
  "category_code": "MEDICINE_PURCHASE",
  "amount": 5000.50,
  "transaction_date": "2026-02-28",
  "remarks": "Monthly medicine stock",
  "running_balance": -5000.50,
  "is_deleted": false,
  "created_at": "2026-02-28T11:30:00",
  "updated_at": null
}
```

---

### 4. Update Transaction
**PATCH** `/finance/transactions/{transaction_id}`

Modify transaction details. Changing amount/nature recalculates running balances.

**Request:**
```bash
curl -X PATCH http://localhost:8000/finance/transactions/990e8400-e29b-41d4-a716-446655440004 \
  -H "Authorization: Bearer {token}" \
  -H "Content-Type: application/json" \
  -d '{
    "amount": 5500.75,
    "remarks": "Adjusted medicine purchase",
    "custom_field_values": {
      "supplier_name": "XYZ Pharmacy"
    }
  }'
```

**Response (200):**
```json
{
  "id": "990e8400-e29b-41d4-a716-446655440004",
  "cash_book_id": "550e8400-e29b-41d4-a716-446655440000",
  "doctor_id": "1ffd1a39-e9a3-46d3-8cd3-950dab11455e",
  "nature_code": "CASH_OUT",
  "category_code": "MEDICINE_PURCHASE",
  "amount": 5500.75,
  "transaction_date": "2026-02-28",
  "remarks": "Adjusted medicine purchase",
  "running_balance": -5500.75,
  "is_deleted": false,
  "created_at": "2026-02-28T11:30:00",
  "updated_at": "2026-02-28T12:00:00"
}
```

---

### 5. Delete Transaction (Soft Delete)
**DELETE** `/finance/transactions/{transaction_id}`

Soft-delete a transaction (mark as deleted, preserve data, recalculate balances).

**Request:**
```bash
curl -X DELETE http://localhost:8000/finance/transactions/990e8400-e29b-41d4-a716-446655440004 \
  -H "Authorization: Bearer {token}"
```

**Response (200):**
```json
{
  "message": "Transaction deleted successfully"
}
```

---

## BALANCE & SUMMARY ENDPOINTS

### 1. Get Current Balance
**GET** `/finance/cash-books/{cash_book_id}/current-balance`

Quick check of current running balance.

**Request:**
```bash
curl -X GET http://localhost:8000/finance/cash-books/550e8400-e29b-41d4-a716-446655440000/current-balance \
  -H "Authorization: Bearer {token}"
```

**Response (200):**
```json
{
  "cash_book_id": "550e8400-e29b-41d4-a716-446655440000",
  "current_balance": -3500.50
}
```

**Frontend Widget:**
```typescript
// BalanceWidget.tsx
export function BalanceWidget({ cashBookId }) {
  const { data } = useQuery({
    queryKey: ['balance', cashBookId],
    queryFn: () => fetch(`/finance/cash-books/${cashBookId}/current-balance`, {
      headers: { 'Authorization': `Bearer ${getToken()}` }
    }).then(r => r.json()),
    refetchInterval: 30000 // Refresh every 30 seconds
  })

  return (
    <div className="balance-widget">
      <h3>Current Balance</h3>
      <div className={`balance-amount ${data?.current_balance >= 0 ? 'positive' : 'negative'}`}>
        {data?.current_balance?.toFixed(2)}
      </div>
    </div>
  )
}
```

---

### 2. Get Cash Book Summary
**GET** `/finance/cash-books/{cash_book_id}/summary?start_date=&end_date=`

Financial summary for a single cash book.

**Query Parameters:**
- `start_date` (optional) - ISO date
- `end_date` (optional) - ISO date

**Request:**
```bash
curl -X GET "http://localhost:8000/finance/cash-books/550e8400-e29b-41d4-a716-446655440000/summary" \
  -H "Authorization: Bearer {token}"
```

**Response (200):**
```json
{
  "cash_book_id": "550e8400-e29b-41d4-a716-446655440000",
  "name": "Medicine Book",
  "total_cash_in": 15000.00,
  "total_cash_out": 18500.75,
  "net_balance": -3500.75,
  "current_balance": -3500.75,
  "transaction_count": 5
}
```

**Frontend Dashboard:**
```typescript
// CashBookDashboard.tsx
export function CashBookDashboard({ cashBookId }) {
  const { data: summary } = useQuery({
    queryKey: ['summary', cashBookId],
    queryFn: () => fetch(`/finance/cash-books/${cashBookId}/summary`, {
      headers: { 'Authorization': `Bearer ${getToken()}` }
    }).then(r => r.json())
  })

  return (
    <div className="dashboard">
      <div className="summary-grid">
        <div className="card income">
          <h4>Total Income</h4>
          <p className="amount">+{summary?.total_cash_in?.toFixed(2)}</p>
        </div>
        <div className="card expense">
          <h4>Total Expenses</h4>
          <p className="amount">-{summary?.total_cash_out?.toFixed(2)}</p>
        </div>
        <div className={`card net ${summary?.net_balance >= 0 ? 'positive' : 'negative'}`}>
          <h4>Net Balance</h4>
          <p className="amount">{summary?.net_balance?.toFixed(2)}</p>
        </div>
        <div className="card">
          <h4>Transactions</h4>
          <p className="count">{summary?.transaction_count}</p>
        </div>
      </div>
    </div>
  )
}
```

---

### 3. Get Doctor Summary (All Books)
**GET** `/finance/summary?start_date=&end_date=`

Aggregated financial summary for all cash books.

**Request:**
```bash
curl -X GET "http://localhost:8000/finance/summary" \
  -H "Authorization: Bearer {token}"
```

**Response (200):**
```json
{
  "total_cash_in": 45000.00,
  "total_cash_out": 52500.75,
  "net_balance": -7500.75,
  "total_current_balance": -7500.75,
  "transaction_count": 15,
  "books": [
    {
      "cash_book_id": "550e8400-e29b-41d4-a716-446655440000",
      "name": "Medicine Book",
      "total_cash_in": 15000.00,
      "total_cash_out": 18500.75,
      "net_balance": -3500.75,
      "current_balance": -3500.75,
      "transaction_count": 5
    },
    {
      "cash_book_id": "660e8400-e29b-41d4-a716-446655440001",
      "name": "Equipment Book",
      "total_cash_in": 30000.00,
      "total_cash_out": 34000.00,
      "net_balance": -4000.00,
      "current_balance": -4000.00,
      "transaction_count": 10
    }
  ]
}
```

---

## Frontend Views & UI

### Overall Finance Dashboard

```typescript
// FinanceDashboard.tsx
import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'

export function FinanceDashboard() {
  const [activeCashBook, setActiveCashBook] = useState(null)

  const { data: books } = useQuery({
    queryKey: ['cashBooks'],
    queryFn: fetchCashBooks
  })

  const { data: summary } = useQuery({
    queryKey: ['summary'],
    queryFn: () => fetch('/finance/summary', {
      headers: { 'Authorization': `Bearer ${getToken()}` }
    }).then(r => r.json())
  })

  return (
    <div className="finance-dashboard">
      {/* Header Section */}
      <div className="header">
        <h1>💰 Finance Management</h1>
        <button className="btn-primary" onClick={() => openCreateBookDialog()}>
          + Create Cash Book
        </button>
      </div>

      {/* Overview Cards */}
      <div className="overview">
        <div className="card total-income">
          <span className="label">Total Income</span>
          <span className="value">+Rs{summary?.total_cash_in?.toLocaleString('en-IN', { minimumFractionDigits: 2 })}</span>
        </div>
        <div className="card total-expense">
          <span className="label">Total Expenses</span>
          <span className="value">-Rs{summary?.total_cash_out?.toLocaleString('en-IN', { minimumFractionDigits: 2 })}</span>
        </div>
        <div className={`card net-balance ${summary?.net_balance >= 0 ? 'positive' : 'negative'}`}>
          <span className="label">Net Balance</span>
          <span className="value">Rs{summary?.net_balance?.toLocaleString('en-IN', { minimumFractionDigits: 2 })}</span>
        </div>
      </div>

      {/* Cash Books Section */}
      <div className="cash-books-section">
        <h2>My Cash Books</h2>
        <div className="books-grid">
          {books?.data?.map(book => (
            <div
              key={book.id}
              className={`book-card ${activeCashBook?.id === book.id ? 'active' : ''}`}
              onClick={() => setActiveCashBook(book)}
            >
              <h3>{book.name}</h3>
              <p className="description">{book.description}</p>
              <div className="book-footer">
                <span className="status">{book.is_active ? '✓ Active' : '✗ Inactive'}</span>
                <button onClick={(e) => { e.stopPropagation(); editBook(book) }}>⚙ Edit</button>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Transactions Section */}
      {activeCashBook && (
        <div className="transactions-section">
          <div className="section-header">
            <h2>Transactions: {activeCashBook.name}</h2>
            <button className="btn-primary" onClick={() => openTransactionForm()}>
              + Record Transaction
            </button>
          </div>

          <TransactionList cashBookId={activeCashBook.id} />

          <div className="section-header">
            <h3>Book Summary</h3>
          </div>
          <CashBookSummary cashBookId={activeCashBook.id} />
        </div>
      )}
    </div>
  )
}
```

### Styled CSS (Tailwind example)

```css
/* FinanceDashboard.css */
.finance-dashboard {
  @apply p-6 bg-gray-50 min-h-screen;
}

.header {
  @apply flex justify-between items-center mb-8;
}

.header h1 {
  @apply text-3xl font-bold text-gray-900;
}

.overview {
  @apply grid grid-cols-3 gap-6 mb-8;
}

.card {
  @apply bg-white rounded-lg shadow p-6 flex flex-col;
}

.card.total-income .value {
  @apply text-2xl font-bold text-green-600;
}

.card.total-expense .value {
  @apply text-2xl font-bold text-red-600;
}

.card.net-balance.positive .value {
  @apply text-2xl font-bold text-green-600;
}

.card.net-balance.negative .value {
  @apply text-2xl font-bold text-red-600;
}

.books-grid {
  @apply grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-4;
}

.book-card {
  @apply bg-white rounded-lg shadow p-4 cursor-pointer hover:shadow-md transition-shadow border-2 border-transparent;
}

.book-card.active {
  @apply border-blue-500 shadow-lg;
}

.transactions-section {
  @apply mt-8 bg-white rounded-lg shadow p-6;
}

.section-header {
  @apply flex justify-between items-center mb-6;
}
```

---

## State Management (React Query)

```typescript
// hooks/useFinance.ts
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'

const API_BASE = 'http://localhost:8000/finance'

export function useCashBooks() {
  return useQuery({
    queryKey: ['cashBooks'],
    queryFn: () => fetch(`${API_BASE}/cash-books`, {
      headers: { 'Authorization': `Bearer ${getToken()}` }
    }).then(r => r.json())
  })
}

export function useCreateCashBook() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (data) => fetch(`${API_BASE}/cash-books`, {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${getToken()}`,
        'Content-Type': 'application/json'
      },
      body: JSON.stringify(data)
    }).then(r => r.json()),
    onSuccess: () => {
      queryClient.invalidateQueries(['cashBooks'])
    }
  })
}

export function useTransactions(cashBookId) {
  return useQuery({
    queryKey: ['transactions', cashBookId],
    queryFn: () => fetch(`${API_BASE}/transactions?cash_book_id=${cashBookId}`, {
      headers: { 'Authorization': `Bearer ${getToken()}` }
    }).then(r => r.json()),
    enabled: !!cashBookId
  })
}

export function useCreateTransaction() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (data) => fetch(`${API_BASE}/transactions`, {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${getToken()}`,
        'Content-Type': 'application/json'
      },
      body: JSON.stringify(data)
    }).then(r => r.json()),
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries(['transactions', variables.cash_book_id])
      queryClient.invalidateQueries(['summary'])
    }
  })
}

export function useCashBookSummary(cashBookId) {
  return useQuery({
    queryKey: ['summary', cashBookId],
    queryFn: () => fetch(`${API_BASE}/cash-books/${cashBookId}/summary`, {
      headers: { 'Authorization': `Bearer ${getToken()}` }
    }).then(r => r.json()),
    enabled: !!cashBookId
  })
}

export function useFinanceSummary() {
  return useQuery({
    queryKey: ['summary'],
    queryFn: () => fetch(`${API_BASE}/summary`, {
      headers: { 'Authorization': `Bearer ${getToken()}` }
    }).then(r => r.json())
  })
}
```

---

## Error Handling

```typescript
// Error responses and handling
export function handleFinanceError(error) {
  const status = error.response?.status
  const message = error.response?.data?.detail || error.message

  switch(status) {
    case 400:
      return `Invalid request: ${message}`
    case 403:
      return `Access denied: ${message}`
    case 404:
      return `Not found: ${message}`
    case 500:
      return `Server error: Please try again later`
    default:
      return `Error: ${message}`
  }
}

// Usage in mutation
const { mutate, error, isError } = useCreateTransaction()

{isError && (
  <div className="alert alert-error">
    {handleFinanceError(error)}
  </div>
)}
```

---

## Next Steps

1. ✅ Apply database migrations (`alembic upgrade head`)
2. ✅ Seed enums (`python scripts/seed_enums.py && python scripts/seed_finance_enums.py`)
3. ✅ Test endpoints with Swagger UI (`http://localhost:8000/docs`)
4. ✅ Implement React Query hooks
5. ✅ Build dashboard UI with provided components
6. ✅ Add error handling and validation
7. ✅ Deploy to production

---

## Support & Troubleshooting

**Common Issues:**

- **Table doesn't exist**: Run `alembic upgrade head`
- **Enum validation fails**: Run `python scripts/seed_finance_enums.py`
- **Authorization errors**: Verify JWT token is valid and doctor role is set
- **Running balance incorrect**: Ensure transactions are ordered by date

For more help, check the API documentation at `/docs` when server is running.
