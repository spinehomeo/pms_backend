# Onsite Patient Handling - Frontend Implementation Guide

**For**: Frontend Developers (React, Vue, Angular, etc.)  
**Purpose**: Implement patient search, registration, and review UI for walk-in consultations  
**Last Updated**: March 6, 2026

---

## 📋 Table of Contents

1. [Overview](#overview)
2. [Architecture](#architecture)
3. [Authentication](#authentication)
4. [Endpoint Integration](#endpoint-integration)
5. [UI Components](#ui-components)
6. [Form Implementation](#form-implementation)
7. [State Management](#state-management)
8. [Error Handling](#error-handling)
9. [Complete Workflow Example](#complete-workflow-example)
10. [Code Examples](#code-examples)
11. [Testing Guide](#testing-guide)
12. [Performance Tips](#performance-tips)
13. [Accessibility](#accessibility)

---

## Overview

The onsite patient system provides **3 endpoints** for managing walk-in patients:

| Endpoint | Purpose | HTTP Method |
|----------|---------|------------|
| **Search** | Find existing patients | GET `/patients/onsite/search` |
| **Quick-Register** | Create new patient (minimal info) | POST `/patients/onsite/quick-register` |
| **Get Details** | Retrieve full patient info | GET `/patients/onsite/{patient_id}` |

### What You're Building

A **3-step patient intake flow**:

```
Step 1: SEARCH
  ↓ User enters phone or name
  ↓ Display matching patients or "not found"
  
Step 2: REGISTER (if not found)
  ↓ User fills quick form (2 required fields)
  ↓ Display new patient with ID
  
Step 3: REVIEW (before consultation)
  ↓ Display full patient profile
  ↓ Allow quick edits if needed
  ↓ Proceed to consultation
```

---

## Architecture

### High-Level Flow

```
┌─────────────────────────────────────────────────────────┐
│                   FRONTEND UI LAYER                     │
├─────────────────────────────────────────────────────────┤
│
│  ┌─────────────────┐  ┌─────────────────┐  ┌──────────────┐
│  │  Search Form    │  │ Register Form   │  │ Patient View │
│  │ (Phone/Name)    │  │ (Name + Phone)  │  │  (Full Info) │
│  └────────┬────────┘  └────────┬────────┘  └──────┬───────┘
│           │                    │                   │
│           └────────────────────┼───────────────────┘
│                                │
├─────────────────────────────────────────────────────────┤
│              SERVICE LAYER (HTTP CLIENT)                │
├─────────────────────────────────────────────────────────┤
│
│              ┌─────────────────────────────┐
│              │ API Service (axios/fetch)   │
│              │ - Handle auth headers       │
│              │ - Manage requests/errors    │
│              │ - Parse responses           │
│              └──────────┬──────────────────┘
│                         │
├─────────────────────────────────────────────────────────┤
│              STATE MANAGEMENT LAYER                     │
├─────────────────────────────────────────────────────────┤
│
│    ┌──────────────────────────────────────────┐
│    │  Store/State (Redux, Context, Pinia)     │
│    │  - searchResults                         │
│    │  - currentPatient                        │
│    │  - isLoading                             │
│    │  - errors                                │
│    └──────────────────────────────────────────┘
│
└─────────────────────────────────────────────────────────┘
         │
         │ (API calls)
         ↓
┌─────────────────────────────────────────────────────────┐
│              BACKEND API (Our Endpoints)                │
├─────────────────────────────────────────────────────────┤
│  GET  /api/v1/patients/onsite/search                   │
│  POST /api/v1/patients/onsite/quick-register           │
│  GET  /api/v1/patients/onsite/{patient_id}            │
└─────────────────────────────────────────────────────────┘
```

### State Model

```javascript
{
  // Current step in workflow
  step: 'search' | 'register' | 'review',
  
  // Search results
  searchResults: [
    {
      id: string,
      full_name: string,
      phone: string,
      gender: string,
      cnic: string,
      is_match_by_phone: boolean,
      is_match_by_name: boolean,
      match_score: number  // 0.0 - 1.0
    }
  ],
  
  // Selected/created patient
  currentPatient: {
    id: string,
    full_name: string,
    phone: string,
    gender: string,
    cnic: string,
    is_temp_cnic: boolean,
    date_of_birth?: string,
    email?: string,
    city?: string,
    medical_history?: string,
    drug_allergies?: string,
    // ... other fields
  },
  
  // UI state
  isLoading: boolean,
  isSearching: boolean,
  isRegistering: boolean,
  error: string | null,
  successMessage: string | null
}
```

---

## Authentication

All endpoints require a Bearer token in the Authorization header.

### Getting the Token

```javascript
// User logs in (existing login flow)
const response = await fetch('/api/v1/login', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    email: 'doctor@clinic.com',
    password: 'password'
  })
});

const data = await response.json();
const token = data.access_token; // Save this

// Store token (localStorage, sessionStorage, or cookie)
localStorage.setItem('auth_token', token);
```

### Creating API Service with Auth

```javascript
// apiService.js or api.ts
class APIService {
  constructor() {
    this.baseURL = 'http://localhost:8000/api/v1';
    this.token = localStorage.getItem('auth_token');
  }

  getHeaders() {
    return {
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${this.token}`
    };
  }

  async request(endpoint, options = {}) {
    try {
      const response = await fetch(`${this.baseURL}${endpoint}`, {
        headers: this.getHeaders(),
        ...options
      });

      if (!response.ok) {
        const error = await response.json();
        throw {
          status: response.status,
          message: error.detail || 'An error occurred',
          data: error
        };
      }

      return await response.json();
    } catch (error) {
      throw error;
    }
  }
}

export const apiService = new APIService();
```

---

## Endpoint Integration

### 1️⃣ Search Patients Endpoint

**Backend**: `GET /api/v1/patients/onsite/search`

#### Frontend Service Method

```javascript
// apiService.js
async searchPatients(phone = null, full_name = null) {
  const params = new URLSearchParams();
  
  if (phone) params.append('phone', phone);
  if (full_name) params.append('full_name', full_name);

  return this.request(`/patients/onsite/search?${params.toString()}`);
}
```

#### Usage in Component

```javascript
// PatientSearch.jsx (React example)
import React, { useState } from 'react';
import { apiService } from './apiService';

export function PatientSearchForm() {
  const [phone, setPhone] = useState('');
  const [fullName, setFullName] = useState('');
  const [results, setResults] = useState([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState(null);

  const handleSearch = async (e) => {
    e.preventDefault();
    setIsLoading(true);
    setError(null);

    try {
      // Validation
      if (!phone && !fullName) {
        setError('Please enter phone or name');
        return;
      }

      // Call API
      const data = await apiService.searchPatients(phone, fullName);
      setResults(data);

      if (data.length === 0) {
        setError('No patients found matching this criteria');
      }
    } catch (err) {
      setError(err.message || 'Search failed');
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <form onSubmit={handleSearch}>
      <div>
        <label>Phone Number</label>
        <input
          type="tel"
          value={phone}
          onChange={(e) => setPhone(e.target.value)}
          placeholder="03001234567"
        />
      </div>

      <div>
        <label>Full Name</label>
        <input
          type="text"
          value={fullName}
          onChange={(e) => setFullName(e.target.value)}
          placeholder="Ali Hassan"
        />
      </div>

      <button type="submit" disabled={isLoading}>
        {isLoading ? 'Searching...' : 'Search Patient'}
      </button>

      {error && <div className="error">{error}</div>}

      {results.length > 0 && (
        <div className="results">
          <h3>Found {results.length} Patient(s)</h3>
          {results.map((patient) => (
            <PatientCard key={patient.id} patient={patient} />
          ))}
        </div>
      )}
    </form>
  );
}

function PatientCard({ patient }) {
  return (
    <div className="patient-card">
      <h4>{patient.full_name}</h4>
      <p>Phone: {patient.phone}</p>
      {patient.is_match_by_phone && <badge>Phone Match</badge>}
      {patient.is_match_by_name && <badge>Name Match</badge>}
      <p className="score">Match Score: {(patient.match_score * 100).toFixed(0)}%</p>
      <button>Select This Patient</button>
    </div>
  );
}
```

#### Response Format

```json
[
  {
    "id": "550e8400-e29b-41d4-a716-446655440000",
    "full_name": "Ali Hassan",
    "phone": "03001234567",
    "gender": "male",
    "cnic": "42101-1234567-1",
    "is_match_by_phone": true,
    "is_match_by_name": false,
    "match_score": 0.9
  }
]
```

---

### 2️⃣ Quick-Register Endpoint

**Backend**: `POST /api/v1/patients/onsite/quick-register`

#### Frontend Service Method

```javascript
// apiService.js
async quickRegisterPatient(patientData) {
  return this.request('/patients/onsite/quick-register', {
    method: 'POST',
    body: JSON.stringify(patientData)
  });
}
```

#### Usage in Component

```javascript
// QuickRegisterForm.jsx (React example)
import React, { useState } from 'react';
import { apiService } from './apiService';

export function QuickRegisterForm({ onSuccess }) {
  const [formData, setFormData] = useState({
    full_name: '',
    phone: '',
    gender: 'unknown',
    city: '',
    email: ''
  });

  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState(null);

  const handleChange = (e) => {
    const { name, value } = e.target;
    setFormData(prev => ({
      ...prev,
      [name]: value
    }));
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setIsLoading(true);
    setError(null);

    try {
      // Validation
      if (!formData.full_name.trim()) {
        setError('Full name is required');
        return;
      }
      if (!formData.phone.trim()) {
        setError('Phone number is required');
        return;
      }

      // Phone format validation (adjust to your country format)
      const phoneRegex = /^03\d{9}$/; // Pakistan format
      if (!phoneRegex.test(formData.phone)) {
        setError('Invalid phone format (expected: 03001234567)');
        return;
      }

      // Call API
      const newPatient = await apiService.quickRegisterPatient(formData);

      // Success
      onSuccess(newPatient);
    } catch (err) {
      if (err.status === 409) {
        setError('Patient with this phone number already exists');
      } else {
        setError(err.message || 'Registration failed');
      }
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <form onSubmit={handleSubmit}>
      <h3>Quick Register New Patient</h3>

      <div className="form-group">
        <label>Full Name *</label>
        <input
          type="text"
          name="full_name"
          value={formData.full_name}
          onChange={handleChange}
          placeholder="Ahmed Khan"
          required
        />
      </div>

      <div className="form-group">
        <label>Phone Number *</label>
        <input
          type="tel"
          name="phone"
          value={formData.phone}
          onChange={handleChange}
          placeholder="03001234567"
          required
        />
      </div>

      <div className="form-group">
        <label>Gender</label>
        <select name="gender" value={formData.gender} onChange={handleChange}>
          <option value="unknown">Select Gender</option>
          <option value="male">Male</option>
          <option value="female">Female</option>
          <option value="other">Other</option>
        </select>
      </div>

      <div className="form-group">
        <label>City</label>
        <input
          type="text"
          name="city"
          value={formData.city}
          onChange={handleChange}
          placeholder="Karachi"
        />
      </div>

      <div className="form-group">
        <label>Email</label>
        <input
          type="email"
          name="email"
          value={formData.email}
          onChange={handleChange}
          placeholder="patient@example.com"
        />
      </div>

      {error && <div className="error-message">{error}</div>}

      <button type="submit" disabled={isLoading}>
        {isLoading ? 'Registering...' : 'Register Patient'}
      </button>

      <p className="hint">* Required fields. Other fields can be updated later.</p>
    </form>
  );
}
```

#### Request Format

```json
{
  "full_name": "Ahmed Khan",
  "phone": "03109876543",
  "gender": "male",
  "city": "Karachi",
  "email": "ahmed@example.com"
}
```

#### Response Format (201 Created)

```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "full_name": "Ahmed Khan",
  "phone": "03109876543",
  "gender": "male",
  "cnic": "TEMP-A1B2C3D4E5",
  "is_temp_cnic": true,
  "date_of_birth": null,
  "email": "ahmed@example.com",
  "city": "Karachi",
  "created_date": "2026-03-05",
  "is_active": true
}
```

---

### 3️⃣ Get Patient Details Endpoint

**Backend**: `GET /api/v1/patients/onsite/{patient_id}`

#### Frontend Service Method

```javascript
// apiService.js
async getPatientDetails(patientId) {
  return this.request(`/patients/onsite/${patientId}`);
}
```

#### Usage in Component

```javascript
// PatientReviewForm.jsx (React example)
import React, { useState, useEffect } from 'react';
import { apiService } from './apiService';

export function PatientReviewForm({ patientId, onProceed }) {
  const [patient, setPatient] = useState(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState(null);
  const [isEditing, setIsEditing] = useState(false);
  const [editedData, setEditedData] = useState({});

  useEffect(() => {
    fetchPatient();
  }, [patientId]);

  const fetchPatient = async () => {
    setIsLoading(true);
    setError(null);

    try {
      const data = await apiService.getPatientDetails(patientId);
      setPatient(data);
      setEditedData(data);
    } catch (err) {
      setError(err.message || 'Failed to load patient');
    } finally {
      setIsLoading(false);
    }
  };

  const handleEdit = (field, value) => {
    setEditedData(prev => ({
      ...prev,
      [field]: value
    }));
  };

  if (isLoading) {
    return <div>Loading patient information...</div>;
  }

  if (error) {
    return <div className="error">{error}</div>;
  }

  if (!patient) {
    return <div className="error">Patient not found</div>;
  }

  return (
    <div className="patient-review">
      <h3>Patient Information</h3>

      {patient.is_temp_cnic && (
        <div className="warning">
          ⚠️ This patient has a temporary CNIC ({patient.cnic}). 
          You can update it later.
        </div>
      )}

      <div className="patient-fields">
        <PatientField
          label="Full Name"
          value={editedData.full_name}
          readOnly
        />
        <PatientField
          label="Phone"
          value={editedData.phone}
          readOnly
        />
        <PatientField
          label="Gender"
          value={editedData.gender || 'Not specified'}
          readOnly
        />
        <PatientField
          label="CNIC"
          value={editedData.cnic}
          readOnly
        />
        <PatientField
          label="Date of Birth"
          value={editedData.date_of_birth || 'Not provided'}
          readOnly
        />
        <PatientField
          label="Email"
          value={editedData.email || 'Not provided'}
          readOnly
        />
        <PatientField
          label="City"
          value={editedData.city || 'Not provided'}
          readOnly
        />
        <PatientField
          label="Medical History"
          value={editedData.medical_history || 'None'}
          readOnly
        />
        <PatientField
          label="Drug Allergies"
          value={editedData.drug_allergies || 'None'}
          readOnly
        />
      </div>

      <div className="actions">
        <button onClick={() => onProceed(patient)}>
          Proceed to Consultation
        </button>
        <button onClick={() => setIsEditing(!isEditing)}>
          {isEditing ? 'Cancel Edit' : 'Edit Patient Info'}
        </button>
      </div>
    </div>
  );
}

function PatientField({ label, value, readOnly = false, onChange }) {
  return (
    <div className="field">
      <label>{label}</label>
      {readOnly ? (
        <p className="value">{value}</p>
      ) : (
        <input type="text" value={value} onChange={onChange} />
      )}
    </div>
  );
}
```

#### Response Format

```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "full_name": "Ahmed Khan",
  "phone": "03109876543",
  "gender": "male",
  "cnic": "TEMP-A1B2C3D4E5",
  "is_temp_cnic": true,
  "date_of_birth": null,
  "email": "ahmed@example.com",
  "city": "Karachi",
  "medical_history": null,
  "drug_allergies": null,
  "family_history": null,
  "current_medications": null,
  "created_date": "2026-03-05",
  "is_active": true
}
```

---

## UI Components

### Component Hierarchy

```
OnSiteConsultationPage
├── Header
├── StepIndicator (1: Search, 2: Register, 3: Review)
├── MainContent
│   ├── Step 1: SearchPatientForm
│   │   └── PatientResultsList
│   │       └── PatientCard
│   │
│   ├── Step 2: QuickRegisterForm
│   │   └── FormInputs
│   │
│   └── Step 3: PatientReviewPanel
│       └── PatientDetails
│       └── ProceedButton
│
└── ActionButtons (Back, Next, Submit)
```

### Component List

#### 1. SearchPatientForm
- Inputs: phone, full_name
- Actions: Search, Clear
- States: loading, error, results

#### 2. SearchResultsList
- Displays: Patient matches (up to 10)
- Shows: Match score, match type badges
- Actions: Select patient → go to review

#### 3. QuickRegisterForm
- Required: full_name, phone
- Optional: gender, city, email, etc.
- Actions: Register, Cancel
- Validation: Phone format, name length

#### 4. PatientReviewPanel
- Display: All patient details
- State: Read-only or editable
- Actions: Edit, Proceed to consultation

#### 5. StepIndicator
- Shows: Current step (1/2/3)
- Progress: Visual indicator
- Names: "Search" → "Register" → "Review"

---

## Form Implementation

### Validation Rules

```javascript
const validationRules = {
  full_name: {
    required: true,
    minLength: 2,
    maxLength: 100,
    pattern: /^[a-zA-Z\s'-]+$/,
    message: 'Full name must be 2-100 characters, letters only'
  },

  phone: {
    required: true,
    pattern: /^03\d{9}$/, // Pakistan format (0301)*
    message: 'Phone must be valid (e.g., 03001234567)'
  },

  email: {
    required: false,
    pattern: /^[^\s@]+@[^\s@]+\.[^\s@]+$/,
    message: 'Invalid email format'
  },

  date_of_birth: {
    required: false,
    type: 'date',
    maxDate: 'today', // Can't be future date
    message: 'Birth date cannot be in the future'
  },

  cnic: {
    required: false,
    pattern: /^\d{5}-\d{7}-\d{1}$/, // Format: 12345-1234567-1
    message: 'CNIC format: 12345-1234567-1'
  }
};
```

### Form Validation Helper

```javascript
// formValidator.js
export function validateField(fieldName, value, rules) {
  const rule = rules[fieldName];
  if (!rule) return null;

  // Check required
  if (rule.required && !value) {
    return 'This field is required';
  }

  // Check pattern
  if (value && rule.pattern && !rule.pattern.test(value)) {
    return rule.message;
  }

  // Check length
  if (value && rule.minLength && value.length < rule.minLength) {
    return `Minimum ${rule.minLength} characters required`;
  }
  if (value && rule.maxLength && value.length > rule.maxLength) {
    return `Maximum ${rule.maxLength} characters allowed`;
  }

  // Check date
  if (value && rule.type === 'date') {
    const date = new Date(value);
    if (date > new Date()) {
      return rule.message;
    }
  }

  return null;
}

export function validateForm(formData, rules) {
  const errors = {};
  
  Object.keys(formData).forEach(field => {
    const error = validateField(field, formData[field], rules);
    if (error) {
      errors[field] = error;
    }
  });

  return {
    isValid: Object.keys(errors).length === 0,
    errors
  };
}
```

---

## State Management

### Redux Example

```javascript
// patientSlice.js
import { createSlice, createAsyncThunk } from '@reduxjs/toolkit';
import { apiService } from './apiService';

export const searchPatients = createAsyncThunk(
  'patient/searchPatients',
  async ({ phone, fullName }, { rejectWithValue }) => {
    try {
      const results = await apiService.searchPatients(phone, fullName);
      return results;
    } catch (error) {
      return rejectWithValue(error.message);
    }
  }
);

export const quickRegisterPatient = createAsyncThunk(
  'patient/quickRegister',
  async (patientData, { rejectWithValue }) => {
    try {
      const patient = await apiService.quickRegisterPatient(patientData);
      return patient;
    } catch (error) {
      return rejectWithValue(error.message);
    }
  }
);

export const getPatientDetails = createAsyncThunk(
  'patient/getDetails',
  async (patientId, { rejectWithValue }) => {
    try {
      const patient = await apiService.getPatientDetails(patientId);
      return patient;
    } catch (error) {
      return rejectWithValue(error.message);
    }
  }
);

const patientSlice = createSlice({
  name: 'patient',
  initialState: {
    currentPatient: null,
    searchResults: [],
    isLoading: false,
    error: null,
    step: 'search' // 'search' | 'register' | 'review'
  },
  reducers: {
    setStep: (state, action) => {
      state.step = action.payload;
    },
    selectPatient: (state, action) => {
      state.currentPatient = action.payload;
      state.step = 'review';
    },
    clearSearch: (state) => {
      state.searchResults = [];
      state.currentPatient = null;
      state.error = null;
    },
    reset: (state) => {
      state.currentPatient = null;
      state.searchResults = [];
      state.isLoading = false;
      state.error = null;
      state.step = 'search';
    }
  },
  extraReducers: (builder) => {
    // Search patients
    builder
      .addCase(searchPatients.pending, (state) => {
        state.isLoading = true;
        state.error = null;
      })
      .addCase(searchPatients.fulfilled, (state, action) => {
        state.isLoading = false;
        state.searchResults = action.payload;
      })
      .addCase(searchPatients.rejected, (state, action) => {
        state.isLoading = false;
        state.error = action.payload;
      });

    // Quick register
    builder
      .addCase(quickRegisterPatient.pending, (state) => {
        state.isLoading = true;
        state.error = null;
      })
      .addCase(quickRegisterPatient.fulfilled, (state, action) => {
        state.isLoading = false;
        state.currentPatient = action.payload;
        state.step = 'review';
      })
      .addCase(quickRegisterPatient.rejected, (state, action) => {
        state.isLoading = false;
        state.error = action.payload;
      });

    // Get details
    builder
      .addCase(getPatientDetails.pending, (state) => {
        state.isLoading = true;
        state.error = null;
      })
      .addCase(getPatientDetails.fulfilled, (state, action) => {
        state.isLoading = false;
        state.currentPatient = action.payload;
      })
      .addCase(getPatientDetails.rejected, (state, action) => {
        state.isLoading = false;
        state.error = action.payload;
      });
  }
});

export const { setStep, selectPatient, clearSearch, reset } = patientSlice.actions;
export default patientSlice.reducer;
```

### Using Redux in Component

```javascript
// OnSiteConsultation.jsx
import { useDispatch, useSelector } from 'react-redux';
import { searchPatients, quickRegisterPatient, selectPatient } from './patientSlice';

export function OnSiteConsultationPage() {
  const dispatch = useDispatch();
  const { currentPatient, step, isLoading, error } = useSelector(state => state.patient);

  const handleSearch = async (phone, fullName) => {
    dispatch(searchPatients({ phone, fullName }));
  };

  const handleRegister = async (patientData) => {
    dispatch(quickRegisterPatient(patientData));
  };

  const handleSelectPatient = (patient) => {
    dispatch(selectPatient(patient));
  };

  return (
    <div className="onsite-consultation">
      <h1>Walk-In Patient Intake</h1>

      {step === 'search' && (
        <SearchPatientForm onSearch={handleSearch} isLoading={isLoading} error={error} />
      )}

      {step === 'register' && (
        <QuickRegisterForm onRegister={handleRegister} isLoading={isLoading} error={error} />
      )}

      {step === 'review' && currentPatient && (
        <PatientReviewForm patient={currentPatient} />
      )}
    </div>
  );
}
```

---

## Error Handling

### Common Errors and Solutions

```javascript
const ERROR_RESPONSES = {
  400: {
    title: 'Validation Error',
    suggestion: 'Please check your input and try again',
    userMessage: 'Invalid data provided'
  },
  401: {
    title: 'Not Authenticated',
    suggestion: 'Please login again',
    userMessage: 'You need to login to continue'
  },
  403: {
    title: 'Not Authorized',
    suggestion: 'You do not have permission to perform this action',
    userMessage: 'Access denied'
  },
  404: {
    title: 'Not Found',
    suggestion: 'The patient or resource was not found',
    userMessage: 'Patient not found'
  },
  409: {
    title: 'Conflict',
    suggestion: 'This phone number is already registered',
    userMessage: 'Patient already exists'
  },
  500: {
    title: 'Server Error',
    suggestion: 'Please try again later',
    userMessage: 'An error occurred on the server'
  }
};

export function getErrorMessage(error) {
  const errorInfo = ERROR_RESPONSES[error.status];
  
  // Use backend's detail message if available
  if (error.data?.detail) {
    return error.data.detail;
  }

  // Fallback to generic message
  return errorInfo?.userMessage || 'An error occurred';
}
```

### Error Boundary Component

```javascript
// ErrorBoundary.jsx
import React from 'react';

export class ErrorBoundary extends React.Component {
  constructor(props) {
    super(props);
    this.state = { hasError: false, error: null };
  }

  static getDerivedStateFromError(error) {
    return { hasError: true, error };
  }

  componentDidCatch(error, errorInfo) {
    console.error('Error caught:', error, errorInfo);
  }

  render() {
    if (this.state.hasError) {
      return (
        <div className="error-boundary">
          <h2>Something went wrong</h2>
          <p>{this.state.error?.message}</p>
          <button onClick={() => window.location.reload()}>
            Reload Page
          </button>
        </div>
      );
    }

    return this.props.children;
  }
}
```

### Network Error Handling

```javascript
// Handle network timeouts, offline, etc.
async function fetchWithRetry(endpoint, options, maxRetries = 2) {
  let lastError;

  for (let i = 0; i < maxRetries; i++) {
    try {
      return await fetch(endpoint, options);
    } catch (error) {
      lastError = error;
      
      // Wait before retrying (exponential backoff)
      await new Promise(resolve => 
        setTimeout(resolve, Math.pow(2, i) * 1000)
      );
    }
  }

  throw lastError;
}
```

---

## Complete Workflow Example

### Full Patient Intake Flow

```javascript
// OnSitePatientIntake.jsx
import React, { useState } from 'react';
import { apiService } from './apiService';

export function OnSitePatientIntake() {
  const [step, setStep] = useState(1); // 1: Search, 2: Register, 3: Review
  const [selectedPatient, setSelectedPatient] = useState(null);
  
  // Step 1: Search
  const [searchPhone, setSearchPhone] = useState('');
  const [searchResults, setSearchResults] = useState([]);
  const [isSearching, setIsSearching] = useState(false);
  
  // Step 2: Register
  const [registerData, setRegisterData] = useState({ full_name: '', phone: '' });
  const [isRegistering, setIsRegistering] = useState(false);
  
  // Global
  const [error, setError] = useState(null);

  // ========== STEP 1: SEARCH ==========
  const handleSearch = async (e) => {
    e.preventDefault();
    setError(null);
    setIsSearching(true);

    try {
      const results = await apiService.searchPatients(searchPhone);
      
      if (results.length > 0) {
        setSearchResults(results);
      } else {
        setError('No patients found. Proceed to register new patient?');
        setStep(2); // Auto-move to register
      }
    } catch (err) {
      setError(err.message);
    } finally {
      setIsSearching(false);
    }
  };

  const handleSelectExistingPatient = (patient) => {
    setSelectedPatient(patient);
    setStep(3); // Go to review
  };

  // ========== STEP 2: REGISTER ==========
  const handleRegister = async (e) => {
    e.preventDefault();
    setError(null);
    setIsRegistering(true);

    try {
      const newPatient = await apiService.quickRegisterPatient(registerData);
      setSelectedPatient(newPatient);
      setStep(3); // Go to review
    } catch (err) {
      if (err.status === 409) {
        setError('Patient already exists! Go back to search.');
      } else {
        setError(err.message);
      }
    } finally {
      setIsRegistering(false);
    }
  };

  // ========== STEP 3: REVIEW ==========
  const handleProceedToConsultation = () => {
    // Navigate to consultation creation with patient ID
    window.location.href = `/consultations/onsite?patient_id=${selectedPatient.id}`;
  };

  return (
    <div className="onsite-intake-container">
      {/* HEADER */}
      <header>
        <h1>Walk-In Patient Intake</h1>
        <StepIndicator currentStep={step} />
      </header>

      {/* ERROR MESSAGE */}
      {error && (
        <div className="error-banner" onClick={() => setError(null)}>
          {error}
        </div>
      )}

      {/* CONTENT */}
      <main className="intake-content">
        {/* ===== STEP 1: SEARCH ===== */}
        {step === 1 && (
          <div className="step-content">
            <h2>Step 1: Search for Patient</h2>
            <form onSubmit={handleSearch}>
              <div className="form-group">
                <label>Phone Number</label>
                <input
                  type="tel"
                  value={searchPhone}
                  onChange={(e) => setSearchPhone(e.target.value)}
                  placeholder="03001234567"
                  disabled={isSearching}
                />
              </div>
              <button type="submit" disabled={isSearching}>
                {isSearching ? 'Searching...' : 'Search'}
              </button>
            </form>

            {searchResults.length > 0 && (
              <div className="search-results">
                <h3>Results ({searchResults.length})</h3>
                {searchResults.map((patient) => (
                  <div key={patient.id} className="result-item">
                    <div>
                      <strong>{patient.full_name}</strong> ({patient.phone})
                      {patient.is_match_by_phone && <badge>Phone Match</badge>}
                    </div>
                    <button onClick={() => handleSelectExistingPatient(patient)}>
                      Select
                    </button>
                  </div>
                ))}
              </div>
            )}

            <p className="hint">Not found? Click "Next" to register new patient</p>
            <div className="actions">
              <button onClick={() => setStep(2)} className="secondary">
                Next: Register New Patient
              </button>
            </div>
          </div>
        )}

        {/* ===== STEP 2: REGISTER ===== */}
        {step === 2 && (
          <div className="step-content">
            <h2>Step 2: Register New Patient</h2>
            <form onSubmit={handleRegister}>
              <div className="form-group">
                <label>Full Name *</label>
                <input
                  type="text"
                  value={registerData.full_name}
                  onChange={(e) => setRegisterData({ ...registerData, full_name: e.target.value })}
                  placeholder="Ahmed Khan"
                  required
                  disabled={isRegistering}
                />
              </div>
              <div className="form-group">
                <label>Phone Number *</label>
                <input
                  type="tel"
                  value={registerData.phone}
                  onChange={(e) => setRegisterData({ ...registerData, phone: e.target.value })}
                  placeholder="03001234567"
                  required
                  disabled={isRegistering}
                />
              </div>
              <button type="submit" disabled={isRegistering}>
                {isRegistering ? 'Registering...' : 'Register Patient'}
              </button>
            </form>

            <div className="actions">
              <button onClick={() => setStep(1)} className="secondary">
                Back: Search Again
              </button>
            </div>
          </div>
        )}

        {/* ===== STEP 3: REVIEW ===== */}
        {step === 3 && selectedPatient && (
          <div className="step-content">
            <h2>Step 3: Review Patient</h2>
            <PatientSummary patient={selectedPatient} />
            <div className="actions">
              <button onClick={() => setStep(2)} className="secondary">
                Back
              </button>
              <button onClick={handleProceedToConsultation} className="primary">
                Proceed to Consultation
              </button>
            </div>
          </div>
        )}
      </main>
    </div>
  );
}

function StepIndicator({ currentStep }) {
  const steps = ['Search', 'Register', 'Review'];
  return (
    <div className="step-indicator">
      {steps.map((label, index) => (
        <div
          key={index}
          className={`step ${currentStep === index + 1 ? 'active' : ''}`}
        >
          <span className="step-number">{index + 1}</span>
          <span className="step-label">{label}</span>
        </div>
      ))}
    </div>
  );
}

function PatientSummary({ patient }) {
  return (
    <div className="patient-summary">
      <table>
        <tbody>
          <tr>
            <td><strong>Name</strong></td>
            <td>{patient.full_name}</td>
          </tr>
          <tr>
            <td><strong>Phone</strong></td>
            <td>{patient.phone}</td>
          </tr>
          <tr>
            <td><strong>Gender</strong></td>
            <td>{patient.gender || 'Not specified'}</td>
          </tr>
          <tr>
            <td><strong>CNIC</strong></td>
            <td>
              {patient.cnic}
              {patient.is_temp_cnic && <badge>Temporary</badge>}
            </td>
          </tr>
          <tr>
            <td><strong>Created</strong></td>
            <td>{new Date(patient.created_date).toLocaleDateString()}</td>
          </tr>
        </tbody>
      </table>
    </div>
  );
}
```

---

## Code Examples

### Minimal Vue.js Implementation

```vue
<!-- PatientSearch.vue -->
<template>
  <div class="patient-search">
    <form @submit.prevent="searchPatients">
      <input v-model="phone" placeholder="Phone number" type="tel" />
      <button type="submit" :disabled="isLoading">
        {{ isLoading ? 'Searching...' : 'Search' }}
      </button>
    </form>

    <div v-if="error" class="error">{{ error }}</div>
    <div v-if="results.length > 0" class="results">
      <div v-for="patient in results" :key="patient.id">
        <div>{{ patient.full_name }} - {{ patient.phone }}</div>
        <button @click="selectPatient(patient)">Select</button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue';
import { apiService } from './apiService';

const phone = ref('');
const results = ref([]);
const isLoading = ref(false);
const error = ref(null);

const searchPatients = async () => {
  isLoading.value = true;
  error.value = null;

  try {
    const data = await apiService.searchPatients(phone.value);
    results.value = data;
  } catch (err) {
    error.value = err.message;
  } finally {
    isLoading.value = false;
  }
};

const selectPatient = (patient) => {
  emit('patientSelected', patient);
};
</script>
```

### Angular Implementation

```typescript
// patient.service.ts
import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';

@Injectable({
  providedIn: 'root'
})
export class PatientService {
  private baseURL = 'http://localhost:8000/api/v1';

  constructor(private http: HttpClient) {}

  searchPatients(phone?: string, fullName?: string): Observable<any[]> {
    let url = `${this.baseURL}/patients/onsite/search`;
    if (phone || fullName) {
      const params = new URLSearchParams();
      if (phone) params.append('phone', phone);
      if (fullName) params.append('full_name', fullName);
      url += `?${params}`;
    }
    return this.http.get<any[]>(url);
  }

  quickRegisterPatient(data: any): Observable<any> {
    return this.http.post(`${this.baseURL}/patients/onsite/quick-register`, data);
  }

  getPatientDetails(id: string): Observable<any> {
    return this.http.get(`${this.baseURL}/patients/onsite/${id}`);
  }
}

// patient-search.component.ts
import { Component } from '@angular/core';
import { PatientService } from './patient.service';

@Component({
  selector: 'app-patient-search',
  template: `
    <form (ngSubmit)="search()">
      <input [(ngModel)]="phone" name="phone" />
      <button type="submit" [disabled]="isLoading">Search</button>
    </form>
    <div *ngIf="error">{{ error }}</div>
    <div *ngFor="let patient of results">
      {{ patient.full_name }}
      <button (click)="select(patient)">Select</button>
    </div>
  `
})
export class PatientSearchComponent {
  phone = '';
  results = [];
  isLoading = false;
  error = '';

  constructor(private patientService: PatientService) {}

  search() {
    this.isLoading = true;
    this.patientService.searchPatients(this.phone).subscribe(
      (data) => {
        this.results = data;
        this.isLoading = false;
      },
      (error) => {
        this.error = error.message;
        this.isLoading = false;
      }
    );
  }

  select(patient: any) {
    // Navigate to review step
  }
}
```

---

## Testing Guide

### Unit Tests

```javascript
// apiService.test.js
import { apiService } from './apiService';

describe('PatientAPI', () => {
  beforeEach(() => {
    localStorage.setItem('auth_token', 'test_token');
  });

  test('searchPatients - returns list of patients', async () => {
    const results = await apiService.searchPatients('03001234567');
    expect(Array.isArray(results)).toBe(true);
    expect(results[0]).toHaveProperty('id');
    expect(results[0]).toHaveProperty('full_name');
  });

  test('searchPatients - with no results returns empty array', async () => {
    const results = await apiService.searchPatients('00000000000');
    expect(results).toEqual([]);
  });

  test('quickRegisterPatient - creates new patient', async () => {
    const newPatient = await apiService.quickRegisterPatient({
      full_name: 'Test Patient',
      phone: '03009999999'
    });
    expect(newPatient).toHaveProperty('id');
    expect(newPatient.full_name).toBe('Test Patient');
  });

  test('quickRegisterPatient - throws error if phone exists', async () => {
    await expect(
      apiService.quickRegisterPatient({
        full_name: 'Duplicate',
        phone: '03001234567' // Existing phone
      })
    ).rejects.toHaveProperty('status', 409);
  });
});
```

### Integration Tests

```javascript
// onsite-intake.integration.test.js
describe('OnSite Patient Intake - Full Flow', () => {
  test('Complete flow: search -> not found -> register -> review', async () => {
    // Step 1: Search (not found)
    const searchResults = await apiService.searchPatients('03119999999');
    expect(searchResults).toEqual([]);

    // Step 2: Register
    const newPatient = await apiService.quickRegisterPatient({
      full_name: 'Integration Test Patient',
      phone: '03119999999'
    });
    expect(newPatient.is_temp_cnic).toBe(true);

    // Step 3: Get details
    const details = await apiService.getPatientDetails(newPatient.id);
    expect(details.full_name).toBe('Integration Test Patient');
    expect(details.phone).toBe('03119999999');
  });
});
```

### Manual Testing Checklist

- [ ] Search form loads
- [ ] Can search by phone
- [ ] Can search by name
- [ ] No results shows appropriate message
- [ ] Results display with match score
- [ ] Can select existing patient
- [ ] Register form loads
- [ ] Required fields validated
- [ ] Phone format validation works
- [ ] Can register new patient
- [ ] Duplicate phone shows error
- [ ] Review step shows patient info
- [ ] Can proceed to consultation
- [ ] Error messages are clear
- [ ] Loading states work
- [ ] Back buttons work
- [ ] Temp CNIC displays correctly

---

## Performance Tips

### Optimize API Calls

```javascript
// Debounce search to reduce API calls
function debounce(func, delay) {
  let timeoutId;
  return function(...args) {
    clearTimeout(timeoutId);
    timeoutId = setTimeout(() => func(...args), delay);
  };
}

const handleSearchWithDebounce = debounce((phone) => {
  apiService.searchPatients(phone);
}, 500); // Wait 500ms after user stops typing
```

### Cache Results

```javascript
// Simple cache for patient lookups
const patientCache = new Map();

async function searchPatientsCached(phone) {
  if (patientCache.has(phone)) {
    return patientCache.get(phone);
  }
  
  const results = await apiService.searchPatients(phone);
  patientCache.set(phone, results);
  return results;
}

// Clear cache after registration
function clearCache() {
  patientCache.clear();
}
```

### Lazy Loading

```javascript
// Load patient details only when needed
const [patientDetails, setPatientDetails] = useState(null);

useEffect(() => {
  if (step === 'review' && selectedPatient && !patientDetails) {
    loadPatientDetails();
  }
}, [step, selectedPatient]);

const loadPatientDetails = async () => {
  const details = await apiService.getPatientDetails(selectedPatient.id);
  setPatientDetails(details);
};
```

---

## Accessibility

### ARIA Labels

```html
<!-- Form accessibility -->
<form>
  <label htmlFor="phone-input">Phone Number</label>
  <input
    id="phone-input"
    type="tel"
    aria-label="Enter patient phone number"
    aria-describedby="phone-hint"
  />
  <small id="phone-hint">Format: 03001234567</small>

  <label htmlFor="name-input">Full Name</label>
  <input
    id="name-input"
    type="text"
    aria-label="Enter patient full name"
  />
</form>

<!-- Results accessibility -->
<div role="region" aria-live="polite" aria-label="Search results">
  {/* Results go here */}
</div>

<!-- Loading accessibility -->
<button aria-busy={isLoading} disabled={isLoading}>
  {isLoading ? 'Loading...' : 'Search'}
</button>
```

### Keyboard Navigation

```javascript
// Handle Enter key in search form
function handleKeyDown(e) {
  if (e.key === 'Enter') {
    handleSearch();
  }
  if (e.key === 'Escape') {
    closeModal();
  }
}

// Make buttons focusable
<button
  tabIndex="0"
  onKeyDown={(e) => {
    if (e.key === ' ' || e.key === 'Enter') {
      onClick();
    }
  }}
>
  Click me
</button>
```

---

## Summary

### Quick Checklist for Frontend Developers

- [ ] **Setup API Service** with authentication
- [ ] **Implement Search** endpoint (GET)
- [ ] **Implement Register** endpoint (POST)
- [ ] **Implement Get Details** endpoint (GET)
- [ ] **Create UI Components** for 3-step flow
- [ ] **Add Form Validation** for all inputs
- [ ] **Handle Errors** with user-friendly messages
- [ ] **Manage State** (Redux, Context, etc.)
- [ ] **Add Loading States** and disabled buttons
- [ ] **Test All Flows** manually and with unit tests
- [ ] **Optimize Performance** (caching, debouncing)
- [ ] **Ensure Accessibility** (ARIA labels, keyboard nav)
- [ ] **Style UI** for mobile and desktop
- [ ] **Document Code** with comments
- [ ] **Deploy and Test** in staging

---

## Additional Resources

| Resource | Link |
|----------|------|
| **Backend API Reference** | `docs/ONSITE_PATIENT_ENDPOINTS.md` |
| **Visual Brief** | `docs/ONSITE_PATIENT_VISUAL_BRIEF.md` |
| **Quick Start** | `docs/ONSITE_QUICK_START.md` |
| **Full Implementation Details** | `docs/ONSITE_IMPLEMENTATION_SUMMARY.md` |

---

## Need Help?

**Common Questions**:
- **"Where do I get the auth token?"** → Login endpoint returns it
- **"Can I search by both phone and name?"** → Yes, both parameters work together
- **"What if phone is in use?"** → Endpoint returns 409 Conflict
- **"Can patients edit their own info after?"** → Mobile app or patient portal can do this
- **"How long does search take?"** → Usually 100-300ms depending on DB size

**Support**:
- Check error messages from endpoints
- Review backend documentation
- Test with curl before implementing in frontend
- Use browser DevTools Network tab to debug

---

**Last Updated**: March 6, 2026  
**Version**: 1.0  
**Status**: Ready for Implementation
