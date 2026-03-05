# Doctor Enum Preferences - Frontend Implementation Guide

This guide helps frontend developers implement the enum preferences feature, allowing doctors to customize dropdown options they see in forms.

---

## 📋 What is This Feature?

Doctors can:
1. ✅ **View** dropdown options filtered to their preferences
2. ✅ **Toggle** options on/off (show/hide from their dropdowns)
3. ✅ **Add** custom options to enums (like "Rescheduled" to appointment status)
4. ✅ **Manage** preferences from a settings page

---

## 🎯 Three Main Workflows

### **Workflow 1: Display Dropdown in Form**
Show doctor only their enabled options

### **Workflow 2: Settings Page**
Let doctor toggle options on/off

### **Workflow 3: Add Custom Option**
Let doctor create new enum values

---

## 🔌 API Endpoints Quick Reference

| Purpose | Method | Endpoint | Use Case |
|---------|--------|----------|----------|
| Get options for dropdown | GET | `/enums/doctor/{enum_type_key}` | Load form dropdowns |
| Get all options at once | GET | `/enums/doctor/all` | Page load - all dropdowns |
| View toggle preferences | GET | `/enums/doctor/preferences/list/{enum_type_key}` | Settings page |
| Toggle option on/off | POST | `/enums/doctor/preferences/{option_id}` | Click toggle switch |
| Add custom option | POST | `/enums/doctor/{enum_type_key}` | "Add option" button |

---

## 💻 Implementation Examples

### **Setup: API Helper Functions**

Create a file `src/api/enumService.ts` (or `.js`):

```typescript
const API_BASE = 'http://localhost:8000';
const token = localStorage.getItem('authToken');

const apiHeaders = {
  'Authorization': `Bearer ${token}`,
  'Content-Type': 'application/json'
};

// Get options for a specific dropdown
export async function getEnumOptions(enumType: string) {
  const response = await fetch(
    `${API_BASE}/enums/doctor/${enumType}`,
    { headers: apiHeaders }
  );
  if (!response.ok) throw new Error('Failed to load options');
  return response.json();
}

// Get all enums at once
export async function getAllEnums() {
  const response = await fetch(
    `${API_BASE}/enums/doctor/all`,
    { headers: apiHeaders }
  );
  if (!response.ok) throw new Error('Failed to load enums');
  return response.json();
}

// Get toggle preferences for an enum type
export async function getEnumPreferences(enumType: string) {
  const response = await fetch(
    `${API_BASE}/enums/doctor/preferences/list/${enumType}`,
    { headers: apiHeaders }
  );
  if (!response.ok) throw new Error('Failed to load preferences');
  return response.json();
}

// Toggle an option on/off
export async function toggleEnumOption(optionId: string, isEnabled: boolean) {
  const response = await fetch(
    `${API_BASE}/enums/doctor/preferences/${optionId}`,
    {
      method: 'POST',
      headers: apiHeaders,
      body: JSON.stringify({ is_enabled: isEnabled })
    }
  );
  if (!response.ok) throw new Error('Failed to toggle option');
  return response.json();
}

// Add custom option
export async function addCustomOption(
  enumType: string,
  value: string,
  label: string,
  sortOrder?: number
) {
  const response = await fetch(
    `${API_BASE}/enums/doctor/${enumType}`,
    {
      method: 'POST',
      headers: apiHeaders,
      body: JSON.stringify({
        value,
        label,
        sort_order: sortOrder || 999
      })
    }
  );
  if (!response.ok) throw new Error('Failed to add option');
  return response.json();
}
```

---

### **Workflow 1: Dropdown in Form**

**React Component Example**:

```jsx
import React, { useEffect, useState } from 'react';
import { getEnumOptions } from '../api/enumService';

function AppointmentForm() {
  const [status, setStatus] = useState('');
  const [options, setOptions] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    loadOptions();
  }, []);

  async function loadOptions() {
    try {
      setLoading(true);
      const data = await getEnumOptions('AppointmentStatus');
      setOptions(data);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  if (loading) return <div>Loading...</div>;
  if (error) return <div>Error: {error}</div>;

  return (
    <form>
      <label>
        Appointment Status
        <select value={status} onChange={(e) => setStatus(e.target.value)}>
          <option value="">-- Select --</option>
          {options.map((opt) => (
            <option key={opt.id} value={opt.value}>
              {opt.label}
            </option>
          ))}
        </select>
      </label>
    </form>
  );
}

export default AppointmentForm;
```

**Vue Component Example**:

```vue
<template>
  <div>
    <label>
      Appointment Status
      <select v-model="status" @change="onStatusChange">
        <option value="">-- Select --</option>
        <option v-for="opt in options" :key="opt.id" :value="opt.value">
          {{ opt.label }}
        </option>
      </select>
    </label>
  </div>
</template>

<script>
import { getEnumOptions } from '../api/enumService';

export default {
  data() {
    return {
      status: '',
      options: [],
      loading: true,
      error: null
    };
  },
  mounted() {
    this.loadOptions();
  },
  methods: {
    async loadOptions() {
      try {
        const data = await getEnumOptions('AppointmentStatus');
        this.options = data;
      } catch (err) {
        this.error = err.message;
      } finally {
        this.loading = false;
      }
    },
    onStatusChange() {
      // Handle status change
    }
  }
};
</script>
```

---

### **Load All Dropdowns at Once**

For pages with multiple dropdowns, load all enums:

```javascript
async function loadAllDropdowns() {
  try {
    const allEnums = await getAllEnums();
    
    // allEnums is an object like:
    // {
    //   "AppointmentStatus": [...],
    //   "PatientGender": [...],
    //   "CaseStatus": [...]
    // }
    
    return {
      appointmentStatuses: allEnums['AppointmentStatus'] || [],
      genders: allEnums['PatientGender'] || [],
      caseStatuses: allEnums['CaseStatus'] || [],
      // ... more enums
    };
  } catch (error) {
    console.error('Failed to load dropdowns:', error);
    return {};
  }
}
```

---

### **Workflow 2: Settings Page - Toggle Options**

**React Component Example**:

```jsx
import React, { useEffect, useState } from 'react';
import { getEnumPreferences, toggleEnumOption } from '../api/enumService';

function EnumSettingsPage() {
  const [preferences, setPreferences] = useState(null);
  const [loading, setLoading] = useState(true);
  const [enumType, setEnumType] = useState('AppointmentStatus');

  useEffect(() => {
    loadPreferences();
  }, [enumType]);

  async function loadPreferences() {
    try {
      setLoading(true);
      const data = await getEnumPreferences(enumType);
      setPreferences(data);
    } catch (error) {
      console.error('Failed to load preferences:', error);
    } finally {
      setLoading(false);
    }
  }

  async function handleToggle(optionId, newState) {
    try {
      await toggleEnumOption(optionId, newState);
      // Reload preferences
      loadPreferences();
    } catch (error) {
      alert(`Failed to toggle: ${error.message}`);
    }
  }

  if (loading) return <div>Loading preferences...</div>;
  if (!preferences) return <div>No data</div>;

  return (
    <div className="settings-page">
      <h2>Enum Preferences</h2>

      <div>
        <label>
          Select Enum Type:
          <select value={enumType} onChange={(e) => setEnumType(e.target.value)}>
            <option value="AppointmentStatus">Appointment Status</option>
            <option value="PatientGender">Patient Gender</option>
            <option value="CaseStatus">Case Status</option>
            <option value="FollowupStatus">Followup Status</option>
          </select>
        </label>
      </div>

      <div className="preferences">
        <h3>Enabled Options</h3>
        <div className="option-list">
          {preferences.enabled_options.map((opt) => (
            <label key={opt.id} className="option-item">
              <input
                type="checkbox"
                checked={true}
                onChange={() => handleToggle(opt.id, false)}
              />
              <span>{opt.label}</span>
            </label>
          ))}
        </div>

        <h3>Disabled Options</h3>
        <div className="option-list">
          {preferences.disabled_options.map((opt) => (
            <label key={opt.id} className="option-item">
              <input
                type="checkbox"
                checked={false}
                onChange={() => handleToggle(opt.id, true)}
              />
              <span>{opt.label}</span>
            </label>
          ))}
        </div>
      </div>
    </div>
  );
}

export default EnumSettingsPage;
```

**Styling Suggestion** (CSS):

```css
.settings-page {
  max-width: 600px;
  margin: 20px auto;
}

.preferences {
  margin-top: 30px;
}

.option-list {
  display: flex;
  flex-direction: column;
  gap: 10px;
  margin: 15px 0;
  padding: 15px;
  background-color: #f5f5f5;
  border-radius: 4px;
}

.option-item {
  display: flex;
  align-items: center;
  gap: 10px;
  cursor: pointer;
  padding: 8px;
  border-radius: 4px;
  transition: background-color 0.2s;
}

.option-item:hover {
  background-color: #efefef;
}

.option-item input[type="checkbox"] {
  cursor: pointer;
  width: 18px;
  height: 18px;
}
```

---

### **Workflow 3: Add Custom Option**

**React Dialog Component**:

```jsx
import React, { useState } from 'react';
import { addCustomOption } from '../api/enumService';

function AddOptionDialog({ enumType, onSuccess, onCancel }) {
  const [value, setValue] = useState('');
  const [label, setLabel] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  async function handleSubmit(e) {
    e.preventDefault();
    
    if (!value.trim() || !label.trim()) {
      setError('Both value and label are required');
      return;
    }

    try {
      setLoading(true);
      setError(null);
      
      await addCustomOption(enumType, value, label);
      
      // Success - reset form and notify parent
      setValue('');
      setLabel('');
      onSuccess?.();
      
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  return (
    <dialog open className="add-option-dialog">
      <form onSubmit={handleSubmit}>
        <h3>Add New Option to {enumType}</h3>
        
        {error && <div className="error-message">{error}</div>}

        <div className="form-group">
          <label>
            Value (what gets saved):
            <input
              type="text"
              value={value}
              onChange={(e) => setValue(e.target.value)}
              placeholder="e.g., Rescheduled"
              disabled={loading}
            />
          </label>
        </div>

        <div className="form-group">
          <label>
            Display Label (what user sees):
            <input
              type="text"
              value={label}
              onChange={(e) => setLabel(e.target.value)}
              placeholder="e.g., Rescheduled Appointment"
              disabled={loading}
            />
          </label>
        </div>

        <div className="form-actions">
          <button type="submit" disabled={loading}>
            {loading ? 'Adding...' : 'Add Option'}
          </button>
          <button type="button" onClick={onCancel} disabled={loading}>
            Cancel
          </button>
        </div>
      </form>
    </dialog>
  );
}

export default AddOptionDialog;
```

**Usage Example**:

```jsx
function EnumManagementPage() {
  const [showDialog, setShowDialog] = useState(false);
  const [selectedEnumType, setSelectedEnumType] = useState('AppointmentStatus');

  async function handleOptionAdded() {
    setShowDialog(false);
    // Reload enum options
    // loadEnumOptions(selectedEnumType);
  }

  return (
    <div>
      <button onClick={() => setShowDialog(true)}>
        + Add New Option
      </button>

      {showDialog && (
        <AddOptionDialog
          enumType={selectedEnumType}
          onSuccess={handleOptionAdded}
          onCancel={() => setShowDialog(false)}
        />
      )}
    </div>
  );
}
```

---

## 🎨 UI/UX Best Practices

### **1. Loading States**
```jsx
if (loading) {
  return <div className="spinner">Loading dropdowns...</div>;
}
```

### **2. Error Handling**
```jsx
if (error) {
  return (
    <div className="alert alert-error">
      Failed to load options. Please try again.
      <button onClick={() => loadOptions()}>Retry</button>
    </div>
  );
}
```

### **3. Empty State**
```jsx
if (options.length === 0) {
  return (
    <div className="empty-state">
      No options available. 
      <button onClick={addNewOption}>Add one now</button>
    </div>
  );
}
```

### **4. Confirmation for Toggles**
```jsx
async function handleToggleWithConfirmation(optionId, currentState) {
  const action = currentState ? 'hide' : 'show';
  const confirmed = window.confirm(
    `Are you sure you want to ${action} this option?`
  );
  
  if (confirmed) {
    await toggleEnumOption(optionId, !currentState);
  }
}
```

---

## 🔑 Common Enum Types

Use these enum type keys in your API calls:

```javascript
const ENUM_TYPES = {
  APPOINTMENT_STATUS: 'AppointmentStatus',
  CASE_STATUS: 'CaseStatus',
  FOLLOWUP_STATUS: 'FollowupStatus',
  PATIENT_GENDER: 'PatientGender',
  CONSULTATION_TYPE: 'ConsultationType',
  PRESCRIPTION_TYPE: 'PrescriptionType',
  REPETITION_ENUM: 'RepetitionEnum',
  // Add more as needed
};
```

---

## ⚡ Performance Tips

### **Cache Enum Options**
```javascript
let enumCache = {};
let cacheTime = Date.now();
const CACHE_DURATION = 5 * 60 * 1000; // 5 minutes

async function getEnumOptionsCached(enumType) {
  const now = Date.now();
  
  // Return from cache if fresh
  if (enumCache[enumType] && (now - cacheTime) < CACHE_DURATION) {
    return enumCache[enumType];
  }
  
  // Otherwise fetch fresh
  const data = await getEnumOptions(enumType);
  enumCache[enumType] = data;
  cacheTime = now;
  return data;
}
```

### **Batch Load All Enums on App Start**
```javascript
// Load once when app initializes, not on every page
async function initializeEnums() {
  try {
    const allEnums = await getAllEnums();
    // Store in app state/context
    window.APP_ENUMS = allEnums;
  } catch (error) {
    console.error('Failed to load enums:', error);
  }
}

// Then use from cache
function getEnumFromCache(enumType) {
  return window.APP_ENUMS?.[enumType] || [];
}
```

---

## 🧪 Testing Examples

### **Test Helper for Mocking API**
```javascript
// __mocks__/enumService.js

export const mockOptions = {
  AppointmentStatus: [
    { id: '1', value: 'Scheduled', label: 'Scheduled' },
    { id: '2', value: 'Completed', label: 'Completed' }
  ]
};

export async function getEnumOptions(enumType) {
  return mockOptions[enumType] || [];
}

export async function toggleEnumOption(optionId, isEnabled) {
  return { success: true };
}
```

### **Component Test Example**
```javascript
import { render, screen } from '@testing-library/react';
import AppointmentForm from './AppointmentForm';
import * as enumService from '../api/enumService';

jest.mock('../api/enumService');

test('renders dropdown with options', async () => {
  enumService.getEnumOptions.mockResolvedValue([
    { id: '1', value: 'Scheduled', label: 'Scheduled' }
  ]);

  render(<AppointmentForm />);
  
  expect(await screen.findByText('Scheduled')).toBeInTheDocument();
});
```

---

## 🛠️ Troubleshooting

### **Options not loading?**
1. Check token in localStorage: `localStorage.getItem('authToken')`
2. Verify enum type exists: Check backend enum:seed data
3. Check network tab for 401/403 errors
4. Ensure user is authenticated as doctor

### **Toggle not working?**
1. Verify option ID is correct (check in network tab)
2. Check for error response: `console.log(response.json())`
3. Ensure you're passing `is_enabled` as boolean, not string

### **Added option not showing?**
1. Option is added but might be disabled by default
2. Reload page or call getEnumPreferences() again
3. Check if custom options require admin approval first

---

## 📚 Complete Example: Full Settings Page

```jsx
import React, { useEffect, useState } from 'react';
import { 
  getEnumPreferences, 
  toggleEnumOption,
  addCustomOption 
} from '../api/enumService';

const ENUM_TYPES = [
  { key: 'AppointmentStatus', label: 'Appointment Status' },
  { key: 'CaseStatus', label: 'Case Status' },
  { key: 'FollowupStatus', label: 'Follow-up Status' },
  { key: 'PatientGender', label: 'Patient Gender' }
];

function EnumPreferencesSettings() {
  const [selectedEnum, setSelectedEnum] = useState('AppointmentStatus');
  const [preferences, setPreferences] = useState(null);
  const [loading, setLoading] = useState(false);
  const [showAddDialog, setShowAddDialog] = useState(false);
  const [newOptionValue, setNewOptionValue] = useState('');
  const [newOptionLabel, setNewOptionLabel] = useState('');

  useEffect(() => {
    loadPreferences();
  }, [selectedEnum]);

  async function loadPreferences() {
    setLoading(true);
    try {
      const data = await getEnumPreferences(selectedEnum);
      setPreferences(data);
    } catch (error) {
      console.error('Failed to load preferences:', error);
    } finally {
      setLoading(false);
    }
  }

  async function handleToggle(optionId, newState) {
    try {
      await toggleEnumOption(optionId, newState);
      loadPreferences(); // Reload after toggle
    } catch (error) {
      alert(`Failed to toggle: ${error.message}`);
    }
  }

  async function handleAddOption() {
    if (!newOptionValue || !newOptionLabel) {
      alert('Please fill in both fields');
      return;
    }

    try {
      await addCustomOption(selectedEnum, newOptionValue, newOptionLabel);
      setNewOptionValue('');
      setNewOptionLabel('');
      setShowAddDialog(false);
      loadPreferences(); // Reload after adding
    } catch (error) {
      alert(`Failed to add option: ${error.message}`);
    }
  }

  return (
    <div className="enum-settings">
      <h1>Enum Options Preferences</h1>

      <div className="enum-selector">
        <label>
          Choose Enum Type:
          <select 
            value={selectedEnum} 
            onChange={(e) => setSelectedEnum(e.target.value)}
          >
            {ENUM_TYPES.map(et => (
              <option key={et.key} value={et.key}>
                {et.label}
              </option>
            ))}
          </select>
        </label>
      </div>

      {loading ? (
        <div>Loading...</div>
      ) : preferences ? (
        <>
          <div className="options-section">
            <h3>✓ Enabled Options</h3>
            {preferences.enabled_options.length > 0 ? (
              <div className="option-list">
                {preferences.enabled_options.map(opt => (
                  <label key={opt.id}>
                    <input
                      type="checkbox"
                      checked={true}
                      onChange={() => handleToggle(opt.id, false)}
                    />
                    {opt.label}
                  </label>
                ))}
              </div>
            ) : (
              <p>No enabled options</p>
            )}
          </div>

          <div className="options-section">
            <h3>✗ Disabled Options</h3>
            {preferences.disabled_options.length > 0 ? (
              <div className="option-list">
                {preferences.disabled_options.map(opt => (
                  <label key={opt.id}>
                    <input
                      type="checkbox"
                      checked={false}
                      onChange={() => handleToggle(opt.id, true)}
                    />
                    {opt.label}
                  </label>
                ))}
              </div>
            ) : (
              <p>No disabled options</p>
            )}
          </div>

          <div className="actions">
            <button onClick={() => setShowAddDialog(true)}>
              + Add Custom Option
            </button>
          </div>

          {showAddDialog && (
            <div className="dialog-overlay">
              <div className="dialog">
                <h3>Add New Option</h3>
                <input
                  type="text"
                  placeholder="Value (e.g., Rescheduled)"
                  value={newOptionValue}
                  onChange={(e) => setNewOptionValue(e.target.value)}
                />
                <input
                  type="text"
                  placeholder="Label (e.g., Rescheduled Appointment)"
                  value={newOptionLabel}
                  onChange={(e) => setNewOptionLabel(e.target.value)}
                />
                <div className="dialog-actions">
                  <button onClick={handleAddOption}>Add</button>
                  <button onClick={() => setShowAddDialog(false)}>Cancel</button>
                </div>
              </div>
            </div>
          )}
        </>
      ) : (
        <div>No data available</div>
      )}
    </div>
  );
}

export default EnumPreferencesSettings;
```

---

## 📞 Support

For API issues, check:
- [Full Enum Preferences API Documentation](./ENUM_PREFERENCES_FRONTEND_GUIDE.md)
- [Doctor Preferences Guide](./DOCTOR_PREFERENCES_API_GUIDE.md)
- Backend logs: Check `/enums/validate` endpoint for validation errors

Happy coding! 🚀
