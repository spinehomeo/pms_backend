# Frontend Developer Guide - Dynamic Enum System

## 🚀 Quick Start (5 minutes)

The backend now provides fully dynamic enums via API. You don't need to hardcode dropdowns anymore.

---

## 📦 Installation & Setup

### 1. Install Dependencies
```bash
npm install @tanstack/react-query @tanstack/react-query-devtools
# or
yarn add @tanstack/react-query @tanstack/react-query-devtools
```

### 2. Setup API Client
```typescript
// lib/api-client.ts
const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000/api/v1'

export const api = {
  get: async (path: string, params?: any) => {
    const url = new URL(`${API_BASE_URL}${path}`)
    if (params) {
      Object.entries(params).forEach(([key, value]) => {
        url.searchParams.append(key, String(value))
      })
    }
    const response = await fetch(url.toString(), {
      headers: { 'Authorization': `Bearer ${getToken()}` }
    })
    return response.json()
  },
  
  post: async (path: string, body: any) => {
    const response = await fetch(`${API_BASE_URL}${path}`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${getToken()}`
      },
      body: JSON.stringify(body)
    })
    return response.json()
  },
  
  patch: async (path: string, body: any) => {
    const response = await fetch(`${API_BASE_URL}${path}`, {
      method: 'PATCH',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${getToken()}`
      },
      body: JSON.stringify(body)
    })
    return response.json()
  },
  
  delete: async (path: string) => {
    const response = await fetch(`${API_BASE_URL}${path}`, {
      method: 'DELETE',
      headers: { 'Authorization': `Bearer ${getToken()}` }
    })
    return response.json()
  }
}
```

---

## 🎯 Core Hook - Use This Everywhere

This single hook replaces ALL hardcoded dropdowns:

```typescript
// hooks/useEnumOptions.ts
import { useQuery } from '@tanstack/react-query'
import { api } from '@/lib/api-client'

/**
 * Get enum options for a dropdown
 * @param enumTypeKey - e.g., "AppointmentStatus", "PrescriptionType"
 * @param doctorId - Optional: filter by specific doctor's preferences
 * @returns Query with loading, error, and data states
 */
export function useEnumOptions(
  enumTypeKey: string,
  doctorId?: string | null
) {
  return useQuery({
    queryKey: ['enum', enumTypeKey, doctorId],
    queryFn: () => {
      if (doctorId) {
        return api.get(`/enums/staff/${enumTypeKey}`, { doctor_id: doctorId })
      }
      return api.get(`/enums/doctor/${enumTypeKey}`)
    },
    staleTime: 30_000, // Cache for 30 seconds
    enabled: !!enumTypeKey, // Don't fetch if no key provided
  })
}
```

---

## 🔧 Reusable Select Component

Create once, use everywhere:

```typescript
// components/EnumSelect.tsx
import { useEnumOptions } from '@/hooks/useEnumOptions'

interface EnumSelectProps {
  enumTypeKey: string
  value: string
  onChange: (value: string) => void
  label?: string
  placeholder?: string
  disabled?: boolean
  required?: boolean
  doctorId?: string | null
  className?: string
  error?: string
}

export function EnumSelect({
  enumTypeKey,
  value,
  onChange,
  label,
  placeholder = '-- Select --',
  disabled = false,
  required = false,
  doctorId = null,
  className = '',
  error = '',
}: EnumSelectProps) {
  const { data: options, isLoading, error: fetchError } = useEnumOptions(enumTypeKey, doctorId)

  return (
    <div className="form-group">
      {label && (
        <label className="block text-sm font-medium mb-1">
          {label}
          {required && <span className="text-red-500">*</span>}
        </label>
      )}
      
      <select
        value={value}
        onChange={(e) => onChange(e.target.value)}
        disabled={disabled || isLoading}
        required={required}
        className={`
          w-full px-3 py-2 border rounded-md
          disabled:bg-gray-100 disabled:cursor-not-allowed
          ${error ? 'border-red-500' : 'border-gray-300'}
          ${className}
        `}
      >
        <option value="">{placeholder}</option>
        {options?.map((opt) => (
          <option key={opt.id} value={opt.value}>
            {opt.label}
          </option>
        ))}
      </select>

      {isLoading && <p className="text-xs text-gray-500 mt-1">Loading...</p>}
      {fetchError && <p className="text-xs text-red-500 mt-1">Error loading options</p>}
      {error && <p className="text-xs text-red-500 mt-1">{error}</p>}
    </div>
  )
}
```

---

## ✨ Usage Examples

### Example 1: Appointment Form
```typescript
import { useState } from 'react'
import { EnumSelect } from '@/components/EnumSelect'

export function AppointmentForm() {
  const [status, setStatus] = useState('')
  const [error, setError] = useState('')

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!status) {
      setError('Status is required')
      return
    }
    // Submit form with status...
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      <EnumSelect
        enumTypeKey="AppointmentStatus"
        value={status}
        onChange={(value) => {
          setStatus(value)
          setError('')
        }}
        label="Appointment Status"
        placeholder="Select a status..."
        required
        error={error}
      />
      
      <button type="submit" className="btn btn-primary">
        Create Appointment
      </button>
    </form>
  )
}
```

### Example 2: Prescription Form with Multiple Enums
```typescript
export function PrescriptionForm() {
  const [type, setType] = useState('')
  const [frequency, setFrequency] = useState('')

  return (
    <form className="space-y-4">
      <EnumSelect
        enumTypeKey="PrescriptionType"
        value={type}
        onChange={setType}
        label="Prescription Type"
        required
      />

      <EnumSelect
        enumTypeKey="RepetitionEnum"
        value={frequency}
        onChange={setFrequency}
        label="Frequency"
        required
      />

      <button type="submit" className="btn btn-primary">
        Create Prescription
      </button>
    </form>
  )
}
```

### Example 3: Doctor-Specific Filtering
```typescript
interface DoctorFormProps {
  doctorId: string
}

export function StaffAppointmentForm({ doctorId }: DoctorFormProps) {
  const [status, setStatus] = useState('')

  return (
    <form className="space-y-4">
      <p className="text-sm text-gray-600">
        Creating appointment for doctor {doctorId}
      </p>

      {/* Shows only statuses that THIS doctor has enabled */}
      <EnumSelect
        enumTypeKey="AppointmentStatus"
        value={status}
        onChange={setStatus}
        label="Status"
        doctorId={doctorId}  {/* ← Filter by doctor */}
        required
      />

      <button type="submit">Create</button>
    </form>
  )
}
```

---

## 👨‍💼 Admin Panel - Manage Dropdowns

```typescript
// pages/admin/EnumManagement.tsx
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { useState } from 'react'
import { api } from '@/lib/api-client'

export function AdminEnumManagement() {
  const queryClient = useQueryClient()
  const [selectedType, setSelectedType] = useState<string | null>(null)

  // Load all enum types
  const { data: enumTypes, isLoading } = useQuery({
    queryKey: ['admin', 'enum-types'],
    queryFn: () => api.get('/enums/admin/types'),
  })

  // Create new enum type
  const createEnumType = useMutation({
    mutationFn: (data: { key: string; label: string; description?: string }) =>
      api.post('/enums/admin/types', data),
    onSuccess: () => {
      queryClient.invalidateQueries(['admin', 'enum-types'])
    },
  })

  return (
    <div className="space-y-6">
      <div className="flex justify-between items-center">
        <h1 className="text-2xl font-bold">Manage Dropdowns</h1>
        <button
          onClick={() => {
            const key = prompt('Enum type key (e.g., VisitType):')
            if (key) {
              const label = prompt('Display label (e.g., Visit Type):')
              if (label) {
                createEnumType.mutate({ key, label })
              }
            }
          }}
          className="btn btn-primary"
        >
          + New Dropdown
        </button>
      </div>

      {isLoading ? (
        <div>Loading...</div>
      ) : (
        <div className="space-y-2">
          {enumTypes?.map((type) => (
            <div
              key={type.id}
              className="flex justify-between items-center p-4 border rounded-lg hover:bg-gray-50"
            >
              <div>
                <div className="font-semibold">{type.label}</div>
                <div className="text-xs text-gray-500">{type.key}</div>
                {type.description && (
                  <div className="text-sm text-gray-600 mt-1">{type.description}</div>
                )}
              </div>

              <div className="flex items-center gap-2">
                <span className="badge">
                  {type.is_system ? '🔒 System' : '✏️ Custom'}
                </span>
                <button
                  onClick={() => setSelectedType(type.key)}
                  className="btn btn-sm"
                >
                  Manage →
                </button>
              </div>
            </div>
          ))}
        </div>
      )}

      {selectedType && <EnumOptionsManager enumTypeKey={selectedType} />}
    </div>
  )
}

function EnumOptionsManager({ enumTypeKey }: { enumTypeKey: string }) {
  const queryClient = useQueryClient()
  const [newValue, setNewValue] = useState('')
  const [newLabel, setNewLabel] = useState('')

  // Load options for this type
  const { data: options = [] } = useQuery({
    queryKey: ['admin', 'enum-options', enumTypeKey],
    queryFn: () => api.get(`/enums/admin/${enumTypeKey}`),
  })

  // Create new option
  const createOption = useMutation({
    mutationFn: (data: { value: string; label: string }) =>
      api.post(`/enums/admin/${enumTypeKey}`, data),
    onSuccess: () => {
      queryClient.invalidateQueries(['admin', 'enum-options', enumTypeKey])
      setNewValue('')
      setNewLabel('')
    },
  })

  // Delete option
  const deleteOption = useMutation({
    mutationFn: (optionId: string) =>
      api.delete(`/enums/admin/option/${optionId}`),
    onSuccess: () => {
      queryClient.invalidateQueries(['admin', 'enum-options', enumTypeKey])
    },
  })

  return (
    <div className="border-t pt-6 mt-6 space-y-4">
      <h2 className="text-lg font-semibold">Options for {enumTypeKey}</h2>

      <div className="bg-gray-50 p-4 rounded-lg space-y-3">
        <input
          type="text"
          placeholder="Value (e.g., 'Confirmed')"
          value={newValue}
          onChange={(e) => setNewValue(e.target.value)}
          className="w-full px-3 py-2 border rounded"
        />
        <input
          type="text"
          placeholder="Label (e.g., 'Confirmed (appointment confirmed)')"
          value={newLabel}
          onChange={(e) => setNewLabel(e.target.value)}
          className="w-full px-3 py-2 border rounded"
        />
        <button
          onClick={() =>
            createOption.mutate({
              value: newValue,
              label: newLabel,
            })
          }
          disabled={!newValue || !newLabel}
          className="btn btn-primary w-full"
        >
          Add Option
        </button>
      </div>

      <div className="space-y-2">
        {options.map((opt) => (
          <div
            key={opt.id}
            className="flex justify-between items-center p-3 bg-gray-50 rounded"
          >
            <div>
              <div className="font-medium">{opt.label}</div>
              <div className="text-xs text-gray-500">Value: {opt.value}</div>
            </div>
            <button
              onClick={() => deleteOption.mutate(opt.id)}
              disabled={opt.is_system}
              className="btn btn-xs btn-danger"
            >
              {opt.is_system ? '🔒' : '🗑️'}
            </button>
          </div>
        ))}
      </div>
    </div>
  )
}
```

---

## 👥 Doctor Preferences - Customize Dropdowns

```typescript
// pages/DoctorSettings.tsx
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { api } from '@/lib/api-client'

const ENUM_TYPES = [
  'AppointmentStatus',
  'PrescriptionType',
  'DayOfWeek',
  'ExceptionType',
  'RepetitionEnum',
]

export function DoctorSettings() {
  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold">My Dropdown Preferences</h1>
      <p className="text-gray-600">
        Toggle options you want to use. Disabled options won't appear in your dropdowns.
      </p>

      {ENUM_TYPES.map((type) => (
        <EnumPreferenceGroup key={type} enumTypeKey={type} />
      ))}
    </div>
  )
}

function EnumPreferenceGroup({ enumTypeKey }: { enumTypeKey: string }) {
  const queryClient = useQueryClient()

  // Load doctor's preferences for this type
  const { data: preferences } = useQuery({
    queryKey: ['doctor', 'enum-preferences', enumTypeKey],
    queryFn: () =>
      api.get(`/enums/doctor/preferences/list/${enumTypeKey}`),
  })

  // Toggle option on/off
  const toggle = useMutation({
    mutationFn: (data: { optionId: string; isEnabled: boolean }) =>
      api.post(`/enums/doctor/preferences/${data.optionId}`, {
        is_enabled: data.isEnabled,
      }),
    onSuccess: () => {
      queryClient.invalidateQueries(['doctor', 'enum-preferences', enumTypeKey])
    },
  })

  const enabledOptions = preferences?.enabled_options || []
  const disabledOptions = preferences?.disabled_options || []

  return (
    <div className="border rounded-lg p-4 space-y-3">
      <h2 className="font-semibold text-lg">{enumTypeKey}</h2>

      <div className="space-y-2">
        {/* Enabled options */}
        {enabledOptions.map((opt) => (
          <label
            key={opt.id}
            className="flex items-center gap-3 p-2 hover:bg-gray-50 rounded cursor-pointer"
          >
            <input
              type="checkbox"
              checked={true}
              onChange={(e) => {
                toggle.mutate({
                  optionId: opt.id,
                  isEnabled: e.target.checked,
                })
              }}
            />
            <span>{opt.label}</span>
          </label>
        ))}

        {/* Disabled options */}
        {disabledOptions.map((opt) => (
          <label
            key={opt.id}
            className="flex items-center gap-3 p-2 hover:bg-gray-50 rounded cursor-pointer opacity-60"
          >
            <input
              type="checkbox"
              checked={false}
              onChange={(e) => {
                toggle.mutate({
                  optionId: opt.id,
                  isEnabled: e.target.checked,
                })
              }}
            />
            <span className="text-gray-600">{opt.label}</span>
          </label>
        ))}
      </div>
    </div>
  )
}
```

---

## 📋 Available Enum Types

Use these in `<EnumSelect enumTypeKey="...">`:

| Key | Label | Use Cases |
|-----|-------|-----------|
| `AppointmentStatus` | Appointment Status | Appointment form, appointment list |
| `PrescriptionType` | Prescription Type | Prescription creation |
| `RepetitionEnum` | Repetition | Dosage frequency |
| `DayOfWeek` | Day of Week | Doctor scheduling, availability |
| `ExceptionType` | Exception Type | Doctor availability exceptions |
| `FormEnum` | Medicine Form | Medicine form selection |
| `ScaleEnum` | Scale | Medicine potency scale |
| `UserRole` | User Role | User role selection |
| `PatientGender` | Patient Gender | Patient form |
| `ManufacturerEnum` | Manufacturer | Medicine manufacturer |

---

## 🎨 Tailwind Examples

### With Tailwind CSS Classes

```typescript
<EnumSelect
  enumTypeKey="AppointmentStatus"
  value={status}
  onChange={setStatus}
  label="Status"
  className="
    focus:ring-2 focus:ring-blue-500 focus:border-transparent
    shadow-sm
  "
  required
/>
```

### With Bootstrap Classes

```typescript
<EnumSelect
  enumTypeKey="AppointmentStatus"
  value={status}
  onChange={setStatus}
  label="Status"
  className="form-select"
  required
/>
```

---

## 🔍 Validation Pattern

```typescript
const handleSubmit = async (e: React.FormEvent<HTMLFormElement>) => {
  e.preventDefault()
  const errors: Record<string, string> = {}

  // Validate required fields
  if (!status) errors.status = 'Status is required'
  if (!type) errors.type = 'Type is required'

  if (Object.keys(errors).length > 0) {
    setErrors(errors)
    return
  }

  // Valid - submit form
  try {
    await api.post('/appointments', { status, type, ... })
  } catch (err) {
    console.error('Failed to create appointment:', err)
  }
}
```

---

## 🚀 Loading States

```typescript
const { data, isLoading, error } = useEnumOptions('AppointmentStatus')

return (
  <>
    {isLoading && <Spinner />}
    {error && <ErrorAlert message="Failed to load options" />}
    {data && <EnumSelect enumTypeKey="AppointmentStatus" ... />}
  </>
)
```

---

## 💾 React Query Setup (App.tsx)

```typescript
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 1000 * 60 * 5, // 5 minutes
      gcTime: 1000 * 60 * 10,    // 10 minutes
      retry: 1,
    },
  },
})

export function App() {
  return (
    <QueryClientProvider client={queryClient}>
      {/* Your app routes */}
    </QueryClientProvider>
  )
}
```

---

## 🎯 Step-by-Step Integration

### Step 1: Copy the Hook
Copy `useEnumOptions.ts` to your hooks folder

### Step 2: Create EnumSelect Component
Copy `EnumSelect.tsx` to your components folder

### Step 3: Replace All Hardcoded Dropdowns
Find any `<select>` with hardcoded `<option>` children and replace with `<EnumSelect>`

**Before:**
```html
<select value={status} onChange={(e) => setStatus(e.target.value)}>
  <option>Pending</option>
  <option>Confirmed</option>
  <option>Completed</option>
</select>
```

**After:**
```tsx
<EnumSelect
  enumTypeKey="AppointmentStatus"
  value={status}
  onChange={setStatus}
  label="Status"
  required
/>
```

### Step 4: Test
- Login as doctor
- Create an appointment/prescription
- Verify dropdown loads options from API
- Go to Settings → Dropdown Preferences
- Toggle some options off
- Refresh the form
- Verify disabled options don't appear

---

## 🐛 Debugging

### Check API Response
```typescript
const { data } = useEnumOptions('AppointmentStatus')
console.log('Enum options:', data)
// Should log: [
//   { id: '...', value: 'Pending', label: 'Pending', ... },
//   { id: '...', value: 'Confirmed', label: 'Confirmed', ... },
// ]
```

### Check Query Cache
```typescript
// In React DevTools, go to React Query tab
// You should see queries like:
// - enum, AppointmentStatus, null
// - enum, PrescriptionType, null
// - admin, enum-types
```

### Common Issues

| Issue | Fix |
|-------|-----|
| "Enum type not found" | Check the `enumTypeKey` spelling (case-sensitive) |
| Blank dropdown | Check React Query is set up correctly |
| Doctor sees all options | Doctor hasn't set preferences yet (all ON by default) |
| Options won't toggle | Check doctor is logged in, not admin |

---

## 📚 Full API Reference

### Get Doctor's Options
```
GET /api/v1/enums/doctor/{enum_type_key}
```
Returns options filtered by current doctor's preferences.

### Get All Global Options
```
GET /api/v1/enums/admin/{enum_type_key}
```
Returns all active options (admin only).

### Toggle Preference
```
POST /api/v1/enums/doctor/preferences/{option_id}
Body: { is_enabled: boolean }
```
Enable/disable an option for current doctor.

### Get Doctor's Preferences
```
GET /api/v1/enums/doctor/preferences/list/{enum_type_key}
```
Returns separated enabled/disabled options for detailed UI.

---

## ✅ What You've Accomplished

✅ One reusable hook for all enum dropdowns  
✅ One reusable component for all select fields  
✅ Admin can create new enum types at runtime  
✅ Doctors can customize their preferences  
✅ Staff sees options filtered by assigned doctor  
✅ No hardcoded enums anywhere  
✅ Changes apply immediately  

---

## 📞 Questions?

- Check `docs/DYNAMIC_ENUM_SYSTEM.md` in repo for comprehensive guide
- All endpoints are documented in Swagger at `/docs`
- Backend validation ensures only valid values are saved
- React Query handles caching and refetching automatically
