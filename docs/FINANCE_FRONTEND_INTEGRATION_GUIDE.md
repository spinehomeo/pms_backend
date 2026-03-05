# Finance Module - Frontend Integration Guide

## 📋 Table of Contents
1. [Overview](#overview)
2. [API Endpoints](#api-endpoints)
3. [Frontend Views](#frontend-views)
4. [Component Architecture](#component-architecture)
5. [Data Flow](#data-flow)
6. [State Management](#state-management)
7. [Integration Patterns](#integration-patterns)
8. [Error Handling](#error-handling)
9. [Examples](#examples)

---

## Overview

The finance module provides a comprehensive cash ledger system for doctors. Key features:
- **Multiple Cash Books**: Independent ledgers per doctor (Medicine, Equipment, General, etc.)
- **Flexible Transactions**: Record CASH_IN or CASH_OUT with categories
- **Custom Fields**: Add extra data fields per cash book (supplier name, invoice number, etc.)
- **Running Balance**: Automatic balance calculation maintained across all transactions
- **Financial Reports**: Summary view across all books

### Key Concepts

```
Doctor (User)
    ↓
Cash Books (Multiple ledgers)
    ├─ Medicine Book
    ├─ Equipment Book
    └─ General Book
        ↓
        ├─ Transactions (CASH_IN/CASH_OUT)
        ├─ Custom Fields (Supplier, Invoice#, etc.)
        └─ Running Balance Snapshots
```

---

## API Endpoints

### 1. Cash Books Management

#### **GET** `/api/v1/finance/cash-books`
List all cash books for the authenticated doctor.

**Query Parameters:**
```typescript
{
  active_only?: boolean = true,    // Filter active books only
  skip?: number = 0,               // Pagination offset
  limit?: number = 100             // Pagination limit (max 1000)
}
```

**Response:**
```json
{
  "data": [
    {
      "id": "550e8400-e29b-41d4-a716-446655440000",
      "name": "Medicine Book",
      "description": "Pharmacy stock purchases",
      "is_active": true,
      "doctor_id": "550e8400-e29b-41d4-a716-446655440001",
      "created_at": "2026-02-28T10:00:00Z",
      "updated_at": "2026-02-28T10:30:00Z"
    }
  ],
  "count": 3
}
```

**Frontend Use:**
```typescript
// In React with TanStack Query
const { data: cashBooks, isPending } = useQuery({
  queryKey: ['finance', 'cash-books'],
  queryFn: () => fetch('/api/v1/finance/cash-books').then(r => r.json())
})

// Display in dropdown/sidebar
return (
  <select onChange={(e) => setSelectedBook(e.target.value)}>
    {cashBooks?.data.map(book => (
      <option key={book.id} value={book.id}>{book.name}</option>
    ))}
  </select>
)
```

---

#### **POST** `/api/v1/finance/cash-books`
Create a new cash book.

**Request Body:**
```json
{
  "name": "Equipment Book",
  "description": "Clinic equipment purchases and maintenance"
}
```

**Response:** (Same as single book above)

**Frontend Use:**
```typescript
const createBook = useMutation({
  mutationFn: (payload) => 
    fetch('/api/v1/finance/cash-books', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    }).then(r => r.json()),
  onSuccess: () => {
    queryClient.invalidateQueries({ queryKey: ['finance', 'cash-books'] })
  }
})

// In form
const handleCreate = (name, description) => {
  createBook.mutate({ name, description })
}
```

---

#### **GET** `/api/v1/finance/cash-books/{cash_book_id}`
Get a specific cash book's details.

**Response:** Single cash book object (see POST response)

---

#### **PATCH** `/api/v1/finance/cash-books/{cash_book_id}`
Update a cash book.

**Request Body:**
```json
{
  "name": "Updated Medicine Book",
  "description": "Updated description",
  "is_active": true
}
```

**Response:** Updated cash book object

---

#### **DELETE** `/api/v1/finance/cash-books/{cash_book_id}`
Delete a cash book (⚠️ hard delete - also deletes all transactions).

**Response:**
```json
{
  "message": "Cash book deleted successfully"
}
```

---

### 2. Custom Fields Management

#### **POST** `/api/v1/finance/cash-books/{cash_book_id}/custom-fields`
Add a custom field to a cash book.

**Request Body:**
```json
{
  "field_key": "supplier_name",
  "field_label": "Supplier Name",
  "field_type": "text",              // text | number | date | boolean
  "is_required": false,
  "display_order": 1
}
```

**Response:**
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440002",
  "cash_book_id": "550e8400-e29b-41d4-a716-446655440000",
  "field_key": "supplier_name",
  "field_label": "Supplier Name",
  "field_type": "text",
  "is_required": false,
  "display_order": 1,
  "is_active": true
}
```

**Frontend Use:**
```typescript
// Dynamic form field generation
const renderCustomField = (field, value, onChange) => {
  const commonProps = {
    key: field.id,
    label: field.field_label,
    required: field.is_required,
    onChange: (val) => onChange(field.field_key, val)
  }

  switch(field.field_type) {
    case 'text':
      return <input type="text" {...commonProps} defaultValue={value} />
    case 'number':
      return <input type="number" {...commonProps} defaultValue={value} />
    case 'date':
      return <input type="date" {...commonProps} defaultValue={value} />
    case 'boolean':
      return <input type="checkbox" {...commonProps} defaultChecked={value} />
    default:
      return null
  }
}
```

---

#### **GET** `/api/v1/finance/cash-books/{cash_book_id}/custom-fields`
List custom fields for a cash book.

**Query Parameters:**
```typescript
{
  active_only?: boolean = true
}
```

**Response:**
```json
[
  {
    "id": "550e8400-e29b-41d4-a716-446655440002",
    "cash_book_id": "550e8400-e29b-41d4-a716-446655440000",
    "field_key": "supplier_name",
    "field_label": "Supplier Name",
    "field_type": "text",
    "is_required": false,
    "display_order": 1,
    "is_active": true
  }
]
```

---

#### **PATCH** `/api/v1/finance/custom-fields/{field_id}`
Update a custom field definition.

**Request Body:**
```json
{
  "field_label": "Updated Label",
  "field_type": "text",
  "is_required": true,
  "display_order": 2
}
```

---

#### **DELETE** `/api/v1/finance/custom-fields/{field_id}`
Soft-delete a custom field (hides from UI but keeps data).

**Response:**
```json
{
  "message": "Custom field deactivated successfully"
}
```

---

### 3. Transactions Management

#### **POST** `/api/v1/finance/transactions`
Create a new transaction.

**Request Body:**
```json
{
  "cash_book_id": "550e8400-e29b-41d4-a716-446655440000",
  "nature_code": "CASH_IN",              // or CASH_OUT
  "category_code": "CONSULTATION",       // or MEDICINE_PURCHASE, EQUIPMENT, etc.
  "amount": 5000.00,
  "transaction_date": "2026-02-28",
  "remarks": "Patient consultation fee",
  "custom_field_values": {
    "supplier_name": "John Medical Store",
    "invoice_number": "INV-2026-001"
  }
}
```

**Response:**
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440003",
  "cash_book_id": "550e8400-e29b-41d4-a716-446655440000",
  "doctor_id": "550e8400-e29b-41d4-a716-446655440001",
  "transaction_date": "2026-02-28",
  "amount": 5000.00,
  "remarks": "Patient consultation fee",
  "running_balance": 15000.00,
  "nature_code": "CASH_IN",
  "category_code": "CONSULTATION",
  "is_deleted": false,
  "created_at": "2026-02-28T10:00:00Z",
  "updated_at": null
}
```

**Frontend Use:**
```typescript
// Transaction form with dynamic custom fields
const createTransaction = useMutation({
  mutationFn: (payload) =>
    fetch('/api/v1/finance/transactions', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    }).then(r => r.json()),
  onSuccess: () => {
    queryClient.invalidateQueries({ queryKey: ['finance', 'transactions'] })
    // Reset form, show success notification
  }
})

// In form submission
const handleTransactionSubmit = (formData) => {
  createTransaction.mutate({
    cash_book_id: selectedBook.id,
    nature_code: formData.nature,
    category_code: formData.category,
    amount: parseFloat(formData.amount),
    transaction_date: formData.date,
    remarks: formData.remarks,
    custom_field_values: formData.customFields
  })
}
```

---

#### **GET** `/api/v1/finance/transactions`
List transactions for a cash book.

**Query Parameters:**
```typescript
{
  cash_book_id: string,              // Required - UUID
  start_date?: string,               // ISO date: 2026-02-28
  end_date?: string,
  nature_code?: string,              // Filter: CASH_IN or CASH_OUT
  category_code?: string,            // Filter: CONSULTATION, etc.
  include_deleted?: boolean = false,
  skip?: number = 0,
  limit?: number = 100
}
```

**Response:**
```json
{
  "data": [
    {
      "id": "550e8400-e29b-41d4-a716-446655440003",
      "cash_book_id": "550e8400-e29b-41d4-a716-446655440000",
      "doctor_id": "550e8400-e29b-41d4-a716-446655440001",
      "transaction_date": "2026-02-28",
      "amount": 5000.00,
      "running_balance": 15000.00,
      "nature_code": "CASH_IN",
      "category_code": "CONSULTATION",
      "is_deleted": false,
      "created_at": "2026-02-28T10:00:00Z",
      "updated_at": null
    }
  ],
  "count": 42
}
```

**Frontend Use:**
```typescript
const { data: transactions } = useQuery({
  queryKey: ['finance', 'transactions', selectedBook.id],
  queryFn: () => 
    fetch(`/api/v1/finance/transactions?cash_book_id=${selectedBook.id}`)
      .then(r => r.json()),
  enabled: !!selectedBook
})

// Display in table
return (
  <table>
    <thead>
      <tr>
        <th>Date</th>
        <th>Description</th>
        <th>Amount</th>
        <th>Type</th>
        <th>Balance</th>
      </tr>
    </thead>
    <tbody>
      {transactions?.data.map(txn => (
        <tr key={txn.id}>
          <td>{txn.transaction_date}</td>
          <td>{txn.remarks}</td>
          <td className={txn.nature_code === 'CASH_IN' ? 'text-green' : 'text-red'}>
            {txn.nature_code === 'CASH_IN' ? '+' : '-'}{txn.amount}
          </td>
          <td>{txn.category_code}</td>
          <td className="font-bold">{txn.running_balance}</td>
        </tr>
      ))}
    </tbody>
  </table>
)
```

---

#### **GET** `/api/v1/finance/transactions/{transaction_id}`
Get a specific transaction.

**Response:** Single transaction object

---

#### **PATCH** `/api/v1/finance/transactions/{transaction_id}`
Update a transaction.

**Request Body:**
```json
{
  "amount": 5500.00,
  "transaction_date": "2026-02-28",
  "nature_code": "CASH_IN",
  "category_code": "CONSULTATION",
  "remarks": "Updated remarks",
  "custom_field_values": {
    "supplier_name": "Updated Name"
  }
}
```

**Note:** If amount or nature_code changes, all subsequent transactions' balances are recalculated.

---

#### **DELETE** `/api/v1/finance/transactions/{transaction_id}`
Soft-delete a transaction (marks as deleted, recalculates balances).

**Response:**
```json
{
  "message": "Transaction deleted successfully"
}
```

---

### 4. Balance & Reports

#### **GET** `/api/v1/finance/cash-books/{cash_book_id}/current-balance`
Get the current running balance for a cash book.

**Response:**
```json
{
  "cash_book_id": "550e8400-e29b-41d4-a716-446655440000",
  "current_balance": 15000.00
}
```

**Frontend Use:**
```typescript
// Display balance in header
const { data: balance } = useQuery({
  queryKey: ['finance', 'balance', selectedBook.id],
  queryFn: () =>
    fetch(`/api/v1/finance/cash-books/${selectedBook.id}/current-balance`)
      .then(r => r.json())
})

return <div className="balance-card">{balance?.current_balance.toFixed(2)}</div>
```

---

#### **GET** `/api/v1/finance/cash-books/{cash_book_id}/summary`
Get financial summary for a single cash book.

**Query Parameters:**
```typescript
{
  start_date?: string,  // ISO date
  end_date?: string
}
```

**Response:**
```json
{
  "cash_book_id": "550e8400-e29b-41d4-a716-446655440000",
  "name": "Medicine Book",
  "total_cash_in": 50000.00,
  "total_cash_out": 35000.00,
  "net_balance": 15000.00,
  "current_balance": 15000.00,
  "transaction_count": 42
}
```

**Frontend Use:**
```typescript
// Dashboard summary cards
const { data: summary } = useQuery({
  queryKey: ['finance', 'summary', selectedBook.id],
  queryFn: () =>
    fetch(`/api/v1/finance/cash-books/${selectedBook.id}/summary`)
      .then(r => r.json())
})

return (
  <div className="summary-grid">
    <Card title="Income" value={`Rs${summary?.total_cash_in}`} icon="arrow-up" />
    <Card title="Expenses" value={`Rs${summary?.total_cash_out}`} icon="arrow-down" />
    <Card title="Net Balance" value={`Rs${summary?.net_balance}`} icon="scale" />
    <Card title="Transactions" value={summary?.transaction_count} icon="receipt" />
  </div>
)
```

---

#### **GET** `/api/v1/finance/summary`
Get consolidated summary across ALL cash books for the doctor.

**Query Parameters:**
```typescript
{
  start_date?: string,
  end_date?: string
}
```

**Response:**
```json
{
  "total_cash_in": 100000.00,
  "total_cash_out": 70000.00,
  "net_balance": 30000.00,
  "total_current_balance": 30000.00,
  "transaction_count": 85,
  "books": [
    {
      "cash_book_id": "550e8400-e29b-41d4-a716-446655440000",
      "name": "Medicine Book",
      "total_cash_in": 50000.00,
      "total_cash_out": 35000.00,
      "net_balance": 15000.00,
      "current_balance": 15000.00,
      "transaction_count": 42
    },
    {
      "cash_book_id": "550e8400-e29b-41d4-a716-446655440004",
      "name": "Equipment Book",
      "total_cash_in": 50000.00,
      "total_cash_out": 35000.00,
      "net_balance": 15000.00,
      "current_balance": 15000.00,
      "transaction_count": 43
    }
  ]
}
```

---

## Frontend Views

### 1. Finance Dashboard (Main View)

```
┌─────────────────────────────────────────────────────────────┐
│                    FINANCE DASHBOARD                         │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  Cash Book Selector: [Medicine Book ▼]                      │
│                                                              │
│  ┌──────────────┬──────────────┬──────────────┬──────────────┐
│  │ Income       │ Expenses     │ Net Balance  │ Transactions │
│  │ Rs50,000      │ Rs35,000      │ Rs15,000      │ 42           │
│  └──────────────┴──────────────┴──────────────┴──────────────┘
│                                                              │
│  [+ Add Transaction] [📊 Reports] [⚙️ Settings]             │
│                                                              │
│  Transactions Table:                                         │
│  ┌──────────┬─────────────────┬────────┬──────────┬──────────┐
│  │ Date     │ Description     │ Amount │ Type     │ Balance  │
│  ├──────────┼─────────────────┼────────┼──────────┼──────────┤
│  │ 2026-02-28│ Consultation    │ +5000  │ CASH_IN  │ 15,000   │
│  │ 2026-02-27│ Medicine Stock  │ -3000  │ CASH_OUT │ 10,000   │
│  │ 2026-02-26│ Clinic Rent     │ -5000  │ CASH_OUT │ 13,000   │
│  └──────────┴─────────────────┴────────┴──────────┴──────────┘
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

---

### 2. Add Transaction Modal

```
┌─────────────────────────────────────────────────────────────┐
│                  ADD NEW TRANSACTION                         │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  Transaction Type *                                          │
│  [○ Cash In  ○ Cash Out]                                     │
│                                                              │
│  Category *                                                  │
│  [Select Category ▼]                                         │
│                                                              │
│  Amount *                                                    │
│  [________] Rs                                                │
│                                                              │
│  Transaction Date *                                          │
│  [2026-02-28]                                                │
│                                                              │
│  Remarks                                                     │
│  [__________________________________]                       │
│                                                              │
│  Custom Fields:                                              │
│  Supplier Name:   [___________________]                      │
│  Invoice Number:  [___________________]                      │
│  Expiry Date:     [2026-12-31]                               │
│                                                              │
│                      [Cancel]  [Save Transaction]            │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

---

### 3. Manage Cash Books View

```
┌─────────────────────────────────────────────────────────────┐
│                  MANAGE CASH BOOKS                           │
├─────────────────────────────────────────────────────────────┤
│                                              [+ New Cash Book]│
│                                                              │
│  Cash Books:                                                 │
│  ┌───────────────────────────────────────────────────────────┐
│  │ [📕] Medicine Book                 Rs15,000    [Edit] [Del]│
│  │      Medicines and pharmacy stock                          │
│  └───────────────────────────────────────────────────────────┘
│  ┌───────────────────────────────────────────────────────────┐
│  │ [📗] Equipment Book                Rs10,000    [Edit] [Del] │
│  │      Medical equipment purchases                           │
│  └───────────────────────────────────────────────────────────┘
│  ┌───────────────────────────────────────────────────────────┐
│  │ [📙] General Book                   Rs5,000    [Edit] [Del] │
│  │      Miscellaneous transactions                            │
│  └───────────────────────────────────────────────────────────┘
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

---

### 4. Custom Fields Configuration

```
┌─────────────────────────────────────────────────────────────┐
│          CUSTOMIZE FIELDS - Medicine Book                    │
├─────────────────────────────────────────────────────────────┤
│                                         [+ Add Custom Field] │
│                                                              │
│  Fields Configuration:                                       │
│  ┌───────────────────────────────────────────────────────────┐
│  │ ☰  Supplier Name         (Text, Required)    [Edit] [Del] │
│  ├───────────────────────────────────────────────────────────┤
│  │ ☰  Invoice Number        (Text)              [Edit] [Del] │
│  ├───────────────────────────────────────────────────────────┤
│  │ ☰  Expiry Date           (Date)              [Edit] [Del] │
│  ├───────────────────────────────────────────────────────────┤
│  │ ☰  Batch Code            (Text)              [Edit] [Del] │
│  └───────────────────────────────────────────────────────────┘
│                                                              │
│  Drag to reorder fields                                      │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

---

### 5. Financial Reports View

```
┌─────────────────────────────────────────────────────────────┐
│                   FINANCIAL REPORTS                          │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  Period: [From 2026-01-01] [To 2026-02-28] [Update]        │
│                                                              │
│  Overall Summary:                                            │
│  Total Income:      Rs100,000                                 │
│  Total Expenses:    Rs70,000                                  │
│  Net Profit:        Rs30,000                                  │
│                                                              │
│  ┌──────────────┬──────────┬──────────┬──────────┐           │
│  │ Cash Book    │ Income   │ Expenses │ Balance  │           │
│  ├──────────────┼──────────┼──────────┼──────────┤           │
│  │ Medicine     │ 50,000   │ 35,000   │ 15,000   │           │
│  │ Equipment    │ 50,000   │ 35,000   │ 15,000   │           │
│  └──────────────┴──────────┴──────────┴──────────┘           │
│                                                              │
│  [📥 Export to PDF] [📊 Download CSV]                        │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

---

## Component Architecture

### Recommended React Component Structure

```
FinanceModule/
├── pages/
│   ├── FinanceDashboard.tsx
│   ├── ManageCashBooks.tsx
│   ├── FinancialReports.tsx
│   └── TransactionHistory.tsx
├── components/
│   ├── CashBookSelector.tsx
│   ├── TransactionTable.tsx
│   ├── AddTransactionModal.tsx
│   ├── SummaryCards.tsx
│   ├── CustomFieldsManager.tsx
│   ├── TransactionForm.tsx
│   └── BalanceDisplay.tsx
├── hooks/
│   ├── useFinance.ts
│   ├── useTransactions.ts
│   ├── useCashBooks.ts
│   └── useFinanceSummary.ts
├── services/
│   └── financeApi.ts
├── types/
│   └── finance.ts
└── utils/
    ├── formatters.ts
    └── validators.ts
```

---

## Data Flow

### Transaction Creation Flow

```
User Input
    ↓
TransactionForm Component
    ├─ Validates input
    ├─ Fetches custom fields for cash book
    └─ Prepares payload
         ↓
    POST /api/v1/finance/transactions
         ↓
    Backend Processing
    ├─ Validates enum codes
    ├─ Calculates running balance
    ├─ Stores transaction
    ├─ Saves custom field values
    └─ Returns transaction object
         ↓
    Frontend Handler
    ├─ Invalidates queries
    ├─ Updates local state
    ├─ Refreshes transaction list
    ├─ Updates balance display
    └─ Shows success notification
```

---

## State Management

### Using TanStack Query (React Query)

```typescript
// services/financeApi.ts
export const financeApi = {
  // Cash Books
  getCashBooks: (params?: QueryParams) =>
    fetch(`/api/v1/finance/cash-books?${new URLSearchParams(params)}`).then(r => r.json()),
  
  createCashBook: (payload: CashBookCreate) =>
    fetch('/api/v1/finance/cash-books', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    }).then(r => r.json()),

  // Transactions
  getTransactions: (cashBookId: string, params?: QueryParams) =>
    fetch(`/api/v1/finance/transactions?cash_book_id=${cashBookId}&${new URLSearchParams(params)}`).then(r => r.json()),
  
  createTransaction: (payload: FinanceTransactionCreate) =>
    fetch('/api/v1/finance/transactions', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    }).then(r => r.json()),

  // Reports
  getBalance: (cashBookId: string) =>
    fetch(`/api/v1/finance/cash-books/${cashBookId}/current-balance`).then(r => r.json()),
  
  getSummary: (cashBookId: string, params?: QueryParams) =>
    fetch(`/api/v1/finance/cash-books/${cashBookId}/summary?${new URLSearchParams(params)}`).then(r => r.json()),
  
  getDoctorSummary: (params?: QueryParams) =>
    fetch(`/api/v1/finance/summary?${new URLSearchParams(params)}`).then(r => r.json())
}

// hooks/useFinance.ts
export const useCashBooks = () =>
  useQuery({
    queryKey: ['finance', 'cash-books'],
    queryFn: () => financeApi.getCashBooks()
  })

export const useTransactions = (cashBookId: string | null) =>
  useQuery({
    queryKey: ['finance', 'transactions', cashBookId],
    queryFn: () => financeApi.getTransactions(cashBookId!),
    enabled: !!cashBookId
  })

export const useFinanceSummary = (cashBookId: string | null) =>
  useQuery({
    queryKey: ['finance', 'summary', cashBookId],
    queryFn: () => financeApi.getSummary(cashBookId!),
    enabled: !!cashBookId
  })

export const useDoctorFinanceSummary = () =>
  useQuery({
    queryKey: ['finance', 'summary'],
    queryFn: () => financeApi.getDoctorSummary()
  })

export const useCreateTransaction = () => {
  const queryClient = useQueryClient()
  
  return useMutation({
    mutationFn: (payload: FinanceTransactionCreate) => 
      financeApi.createTransaction(payload),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['finance', 'transactions'] })
      queryClient.invalidateQueries({ queryKey: ['finance', 'summary'] })
    }
  })
}
```

---

## Integration Patterns

### 1. Category & Nature Enums (Dynamic)

```typescript
// These come from the dynamic enum system
// Fetch them from /enums/doctor/TransactionNature and /enums/doctor/TransactionCategory

const { data: natures } = useQuery({
  queryKey: ['enums', 'TransactionNature'],
  queryFn: () => 
    fetch('/api/v1/enums/doctor/TransactionNature').then(r => r.json())
})

const { data: categories } = useQuery({
  queryKey: ['enums', 'TransactionCategory'],
  queryFn: () =>
    fetch('/api/v1/enums/doctor/TransactionCategory').then(r => r.json())
})

// Use in dropdowns
return (
  <>
    <select name="nature_code">
      {natures?.map(nature => (
        <option key={nature.value} value={nature.value}>
          {nature.label}
        </option>
      ))}
    </select>

    <select name="category_code">
      {categories?.map(cat => (
        <option key={cat.value} value={cat.value}>
          {cat.label}
        </option>
      ))}
    </select>
  </>
)
```

---

### 2. Error Handling

```typescript
const createTransaction = useMutation({
  mutationFn: financeApi.createTransaction,
  onError: (error: any) => {
    const message = error?.response?.data?.detail || 'Failed to create transaction'
    
    // Show error toast
    toast.error(message)
    
    // Handle specific errors
    if (error?.response?.status === 400) {
      // Validation error - show field errors
      toast.error('Please check all required fields')
    }
    if (error?.response?.status === 403) {
      // Permission error - access denied
      toast.error('You cannot access this cash book')
    }
  }
})
```

---

### 3. Pagination

```typescript
const TransactionList = ({ cashBookId }) => {
  const [page, setPage] = useState(0)
  const pageSize = 20

  const { data: transactions } = useQuery({
    queryKey: ['finance', 'transactions', cashBookId, page],
    queryFn: () => 
      financeApi.getTransactions(cashBookId, {
        skip: page * pageSize,
        limit: pageSize
      })
  })

  return (
    <>
      <TransactionTable data={transactions?.data} />
      <Pagination
        currentPage={page}
        totalItems={transactions?.count}
        itemsPerPage={pageSize}
        onPageChange={setPage}
      />
    </>
  )
}
```

---

### 4. Filtering & Sorting

```typescript
const [filters, setFilters] = useState({
  startDate: null,
  endDate: null,
  natureCode: null,
  categoryCode: null,
  sortBy: 'date', // date or balance
  sortOrder: 'desc' // asc or desc
})

const { data: transactions } = useQuery({
  queryKey: ['finance', 'transactions', cashBookId, filters],
  queryFn: () => 
    financeApi.getTransactions(cashBookId, {
      start_date: filters.startDate,
      end_date: filters.endDate,
      nature_code: filters.natureCode,
      category_code: filters.categoryCode
    })
})

return (
  <>
    <FilterBar filters={filters} onChange={setFilters} />
    <TransactionTable data={transactions?.data} />
  </>
)
```

---

## Examples

### Complete Transaction Form Example

```typescript
import React, { useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { financeApi } from '@/services/financeApi'

interface TransactionFormProps {
  cashBookId: string
  onSuccess?: () => void
}

export const TransactionForm: React.FC<TransactionFormProps> = ({
  cashBookId,
  onSuccess
}) => {
  const queryClient = useQueryClient()
  const [formData, setFormData] = useState({
    nature_code: 'CASH_IN',
    category_code: '',
    amount: '',
    transaction_date: new Date().toISOString().split('T')[0],
    remarks: '',
    custom_field_values: {}
  })

  // Fetch dropdowns
  const { data: natures } = useQuery({
    queryKey: ['enums', 'TransactionNature'],
    queryFn: () => 
      fetch('/api/v1/enums/doctor/TransactionNature').then(r => r.json())
  })

  const { data: categories } = useQuery({
    queryKey: ['enums', 'TransactionCategory'],
    queryFn: () =>
      fetch('/api/v1/enums/doctor/TransactionCategory').then(r => r.json())
  })

  // Fetch custom fields
  const { data: customFields } = useQuery({
    queryKey: ['finance', 'custom-fields', cashBookId],
    queryFn: () =>
      fetch(`/api/v1/finance/cash-books/${cashBookId}/custom-fields`)
        .then(r => r.json())
  })

  // Create transaction mutation
  const { mutate: createTransaction, isPending } = useMutation({
    mutationFn: (payload) => 
      fetch('/api/v1/finance/transactions', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      }).then(r => r.json()),
    onSuccess: () => {
      // Invalidate cache
      queryClient.invalidateQueries({ 
        queryKey: ['finance', 'transactions', cashBookId] 
      })
      queryClient.invalidateQueries({ 
        queryKey: ['finance', 'summary', cashBookId] 
      })
      
      // Reset form
      setFormData(prev => ({
        ...prev,
        amount: '',
        remarks: '',
        custom_field_values: {}
      }))
      
      // Call success callback
      onSuccess?.()
    },
    onError: (error: any) => {
      alert(error?.response?.data?.detail || 'Error creating transaction')
    }
  })

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    
    createTransaction({
      cash_book_id: cashBookId,
      nature_code: formData.nature_code,
      category_code: formData.category_code,
      amount: parseFloat(formData.amount),
      transaction_date: formData.transaction_date,
      remarks: formData.remarks,
      custom_field_values: formData.custom_field_values
    })
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      {/* Nature Selection */}
      <div>
        <label className="block text-sm font-medium">Transaction Type *</label>
        <select
          value={formData.nature_code}
          onChange={(e) => setFormData({ 
            ...formData, 
            nature_code: e.target.value 
          })}
          className="mt-1 block w-full border rounded px-3 py-2"
        >
          {natures?.map(nature => (
            <option key={nature.value} value={nature.value}>
              {nature.label}
            </option>
          ))}
        </select>
      </div>

      {/* Category Selection */}
      <div>
        <label className="block text-sm font-medium">Category *</label>
        <select
          value={formData.category_code}
          onChange={(e) => setFormData({ 
            ...formData, 
            category_code: e.target.value 
          })}
          required
          className="mt-1 block w-full border rounded px-3 py-2"
        >
          <option value="">Select Category</option>
          {categories?.map(cat => (
            <option key={cat.value} value={cat.value}>
              {cat.label}
            </option>
          ))}
        </select>
      </div>

      {/* Amount */}
      <div>
        <label className="block text-sm font-medium">Amount *</label>
        <input
          type="number"
          value={formData.amount}
          onChange={(e) => setFormData({ 
            ...formData, 
            amount: e.target.value 
          })}
          required
          min="0"
          step="0.01"
          className="mt-1 block w-full border rounded px-3 py-2"
          placeholder="0.00"
        />
      </div>

      {/* Date */}
      <div>
        <label className="block text-sm font-medium">Transaction Date *</label>
        <input
          type="date"
          value={formData.transaction_date}
          onChange={(e) => setFormData({ 
            ...formData, 
            transaction_date: e.target.value 
          })}
          className="mt-1 block w-full border rounded px-3 py-2"
        />
      </div>

      {/* Remarks */}
      <div>
        <label className="block text-sm font-medium">Remarks</label>
        <textarea
          value={formData.remarks}
          onChange={(e) => setFormData({ 
            ...formData, 
            remarks: e.target.value 
          })}
          className="mt-1 block w-full border rounded px-3 py-2"
          rows={3}
        />
      </div>

      {/* Custom Fields */}
      {customFields?.length > 0 && (
        <div className="border-t pt-4">
          <h3 className="font-medium text-sm mb-3">Additional Information</h3>
          {customFields.map(field => (
            <div key={field.id} className="mb-3">
              <label className="block text-sm font-medium">
                {field.field_label}
                {field.is_required && <span className="text-red-500">*</span>}
              </label>
              {field.field_type === 'text' && (
                <input
                  type="text"
                  value={formData.custom_field_values[field.field_key] || ''}
                  onChange={(e) => setFormData({
                    ...formData,
                    custom_field_values: {
                      ...formData.custom_field_values,
                      [field.field_key]: e.target.value
                    }
                  })}
                  required={field.is_required}
                  className="mt-1 block w-full border rounded px-3 py-2"
                />
              )}
              {field.field_type === 'number' && (
                <input
                  type="number"
                  value={formData.custom_field_values[field.field_key] || ''}
                  onChange={(e) => setFormData({
                    ...formData,
                    custom_field_values: {
                      ...formData.custom_field_values,
                      [field.field_key]: e.target.value
                    }
                  })}
                  required={field.is_required}
                  className="mt-1 block w-full border rounded px-3 py-2"
                />
              )}
              {field.field_type === 'date' && (
                <input
                  type="date"
                  value={formData.custom_field_values[field.field_key] || ''}
                  onChange={(e) => setFormData({
                    ...formData,
                    custom_field_values: {
                      ...formData.custom_field_values,
                      [field.field_key]: e.target.value
                    }
                  })}
                  required={field.is_required}
                  className="mt-1 block w-full border rounded px-3 py-2"
                />
              )}
              {field.field_type === 'boolean' && (
                <input
                  type="checkbox"
                  checked={formData.custom_field_values[field.field_key] || false}
                  onChange={(e) => setFormData({
                    ...formData,
                    custom_field_values: {
                      ...formData.custom_field_values,
                      [field.field_key]: e.target.checked
                    }
                  })}
                  className="mt-1"
                />
              )}
            </div>
          ))}
        </div>
      )}

      {/* Submit Button */}
      <button
        type="submit"
        disabled={isPending}
        className="w-full bg-blue-500 text-white py-2 rounded hover:bg-blue-600 disabled:opacity-50"
      >
        {isPending ? 'Saving...' : 'Add Transaction'}
      </button>
    </form>
  )
}
```

---

## Integration Checklist

- [ ] Setup API service layer (`services/financeApi.ts`)
- [ ] Create custom hooks (`hooks/useFinance.ts`)
- [ ] Create reusable components (TransactionForm, SummaryCards, etc.)
- [ ] Implement state management with TanStack Query
- [ ] Add error handling and notifications
- [ ] Create Finance Dashboard page
- [ ] Create Manage Cash Books page
- [ ] Create Financial Reports page
- [ ] Setup dynamic enum fetching
- [ ] Add custom fields dynamic rendering
- [ ] Test transaction CRUD operations
- [ ] Test balance calculations
- [ ] Performance: Implement pagination for large transaction lists
- [ ] Add input validation
- [ ] Add loading states
- [ ] Test edge cases (zero balance, negative balance, date filters)
- [ ] Setup error tracking/logging
- [ ] Add analytics tracking for finance operations
- [ ] Create E2E tests

---

**Happy coding! 🚀**
