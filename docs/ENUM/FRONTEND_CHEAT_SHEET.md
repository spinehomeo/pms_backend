# Frontend Developer - Cheat Sheet

## One-Line Summaries

| What | How |
|------|-----|
| **Get dropdown options** | `const { data } = useEnumOptions('AppointmentStatus')` |
| **Use in form** | `<EnumSelect enumTypeKey="AppointmentStatus" value={x} onChange={setX} />` |
| **Dr filter** | `<EnumSelect ... doctorId={doctorId} />` |
| **Admin panel** | See `FRONTEND_QUICK_START.md` for full example |
| **Doctor prefs** | See `FRONTEND_QUICK_START.md` for full example |

---

## The Hook (Copy-Paste)

```typescript
// hooks/useEnumOptions.ts
import { useQuery } from '@tanstack/react-query'
import { api } from '@/lib/api-client'

export function useEnumOptions(enumTypeKey: string, doctorId?: string | null) {
  return useQuery({
    queryKey: ['enum', enumTypeKey, doctorId],
    queryFn: () => doctorId
      ? api.get(`/enums/staff/${enumTypeKey}`, { doctor_id: doctorId })
      : api.get(`/enums/doctor/${enumTypeKey}`),
    staleTime: 30_000,
  })
}
```

---

## The Component (Copy-Paste)

```typescript
// components/EnumSelect.tsx
import { useEnumOptions } from '@/hooks/useEnumOptions'

export function EnumSelect({
  enumTypeKey, value, onChange, label, placeholder = '-- Select --',
  disabled, required, doctorId = null, className, error
}) {
  const { data: options = [], isLoading } = useEnumOptions(enumTypeKey, doctorId)

  return (
    <div className="form-group">
      {label && <label>{label}{required && <span className="text-red-500">*</span>}</label>}
      <select value={value} onChange={(e) => onChange(e.target.value)} 
              disabled={disabled || isLoading} required={required} className={className}>
        <option value="">{placeholder}</option>
        {options?.map((opt) => (
          <option key={opt.id} value={opt.value}>{opt.label}</option>
        ))}
      </select>
      {error && <p className="text-xs text-red-500">{error}</p>}
    </div>
  )
}
```

---

## Usage

```typescript
// Simple form
function MyForm() {
  const [status, setStatus] = useState('')
  
  return (
    <EnumSelect
      enumTypeKey="AppointmentStatus"
      value={status}
      onChange={setStatus}
      label="Status"
      required
    />
  )
}

// Staff filtering by doctor
<EnumSelect
  enumTypeKey="AppointmentStatus"
  value={status}
  onChange={setStatus}
  label="Status"
  doctorId={doctorId}  // ← Doctor filter
/>
```

---

## 10 Enum Type Keys

```
AppointmentStatus  | PrescriptionType   | RepetitionEnum
DayOfWeek          | ExceptionType      | FormEnum
ScaleEnum          | UserRole           | PatientGender
ManufacturerEnum
```

---

## API Calls Reference

```typescript
import { api } from '@/lib/api-client'

// Get options (already in useEnumOptions)
api.get('/enums/doctor/AppointmentStatus')

// Get all options (admin)
api.get('/enums/admin/AppointmentStatus')

// Toggle doctor preference
api.post('/enums/doctor/preferences/{optionId}', { is_enabled: true })

// Get doctor preferences
api.get('/enums/doctor/preferences/list/AppointmentStatus')

// Create enum type (admin)
api.post('/enums/admin/types', { key: 'VisitType', label: 'Visit Type' })

// Add option (admin)
api.post('/enums/admin/AppointmentStatus', { value: 'Rescheduled', label: 'Rescheduled' })
```

---

## Query Invalidation (After Mutations)

```typescript
import { useQueryClient } from '@tanstack/react-query'

const queryClient = useQueryClient()

// After creating/updating/deleting an enum
queryClient.invalidateQueries(['enum', 'AppointmentStatus'])
queryClient.invalidateQueries(['admin', 'enum-options', 'AppointmentStatus'])
queryClient.invalidateQueries(['doctor', 'enum-preferences', 'AppointmentStatus'])
```

---

## React Query Setup

```typescript
// main.tsx
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'

const queryClient = new QueryClient()

ReactDOM.createRoot(document.getElementById('root')!).render(
  <QueryClientProvider client={queryClient}>
    <App />
  </QueryClientProvider>
)
```

---

## Examples by Use Case

### Form Submission
```typescript
const handleSubmit = async (e) => {
  e.preventDefault()
  if (!status) { setError('Required'); return }
  
  await api.post('/appointments', { status, ... })
  // Success!
}
```

### Dependent Selects
```typescript
function Form() {
  const [type, setType] = useState('')
  const [subtype, setSubtype] = useState('')
  
  // First dropdown
  <EnumSelect enumTypeKey="PrescriptionType" value={type} onChange={setType} />
  
  // Second depends on first  
  {type && <EnumSelect enumTypeKey={`${type}SubType`} value={subtype} onChange={setSubtype} />}
}
```

### Table Column Rendering
```typescript
function AppointmentTable({ appointments }) {
  const { data: statusOptions } = useEnumOptions('AppointmentStatus')
  const statusMap = Object.fromEntries(statusOptions?.map(o => [o.value, o.label]) ?? [])
  
  return (
    <table>
      {appointments.map(apt => (
        <tr>
          <td>{statusMap[apt.status]}</td>
        </tr>
      ))}
    </table>
  )
}
```

---

## Styling Examples

### Tailwind
```typescript
<EnumSelect
  className="focus:ring-2 focus:ring-blue-500 shadow-sm"
  enumTypeKey="AppointmentStatus"
  value={status}
  onChange={setStatus}
/>
```

### Bootstrap
```typescript
<EnumSelect
  className="form-select form-select-lg"
  enumTypeKey="AppointmentStatus"
  value={status}
  onChange={setStatus}
/>
```

### Material-UI Style
```typescript
<EnumSelect
  className="px-4 py-2 border-b-2 border-gray-300 focus:border-blue-500"
  enumTypeKey="AppointmentStatus"
  value={status}
  onChange={setStatus}
/>
```

---

## Loading & Error States

```typescript
const { data, isLoading, error } = useEnumOptions('AppointmentStatus')

{isLoading && <Spinner />}
{error && <Alert type="error">Failed to load options</Alert>}
{data && <p>Loaded {data.length} options</p>}
```

---

## Admin Panel Snippet

```typescript
// Create enum type
const create = useMutation({
  mutationFn: (data) => api.post('/enums/admin/types', data),
  onSuccess: () => queryClient.invalidateQueries(['admin', 'enum-types'])
})

// Add option
const add = useMutation({
  mutationFn: (data) => api.post(`/enums/admin/${typeKey}`, data),
  onSuccess: () => queryClient.invalidateQueries(['admin', 'enum-options', typeKey])
})

// Delete option
const del = useMutation({
  mutationFn: (id) => api.delete(`/enums/admin/option/${id}`),
  onSuccess: () => queryClient.invalidateQueries(['admin', 'enum-options', typeKey])
})
```

---

## Doctor Preferences Snippet

```typescript
// Load preferences
const { data: prefs } = useQuery({
  queryKey: ['doctor', 'enum-preferences', typeKey],
  queryFn: () => api.get(`/enums/doctor/preferences/list/${typeKey}`)
})

// Toggle option
const toggle = useMutation({
  mutationFn: (data) => api.post(`/enums/doctor/preferences/${data.id}`, data),
  onSuccess: () => queryClient.invalidateQueries(['doctor', 'enum-preferences', typeKey])
})

// Usage
<input
  type="checkbox"
  checked={enabled}
  onChange={(e) => toggle.mutate({ id: optId, is_enabled: e.target.checked })}
/>
```

---

## Typescript Types

```typescript
interface EnumOption {
  id: string
  enum_type_id: string
  enum_type: string
  value: string
  label: string
  is_active: boolean
  is_system: boolean
  sort_order: number
  created_at: string
}

interface EnumType {
  id: string
  key: string
  label: string
  description?: string
  is_system: boolean
  is_active: boolean
  created_at: string
}

interface DoctorPreferences {
  enabled_options: EnumOption[]
  disabled_options: EnumOption[]
}
```

---

## Common Mistakes

❌ **Wrong:**
```typescript
// Hardcoded options
<select>
  <option>Pending</option>
  <option>Confirmed</option>
</select>
```

✅ **Right:**
```typescript
<EnumSelect enumTypeKey="AppointmentStatus" value={x} onChange={setX} />
```

---

❌ **Wrong:**
```typescript
// No doctor filter when needed
api.get('/enums/doctor/AppointmentStatus')
```

✅ **Right:**
```typescript
// Pass doctor ID for staff
api.get('/enums/staff/AppointmentStatus', { doctor_id: doctorId })
```

---

## Testing Pattern

```typescript
import { useEnumOptions } from '@/hooks/useEnumOptions'
import { screen, render, waitFor } from '@testing-library/react'

test('loads enum options', async () => {
  render(<EnumSelect enumTypeKey="AppointmentStatus" value="" onChange={() => {}} />)
  
  await waitFor(() => {
    expect(screen.getByText('Pending')).toBeInTheDocument()
  })
})
```

---

## Env Variables

```
VITE_API_URL=http://localhost:8000/api/v1
VITE_AUTH_TOKEN_KEY=access_token
```

---

## File Structure

```
src/
├── hooks/
│   └── useEnumOptions.ts          ← Copy the hook here
├── components/
│   └── EnumSelect.tsx              ← Copy component here
├── pages/
│   ├── appointments/
│   │   └── AppointmentForm.tsx    ← Use EnumSelect
│   ├── prescriptions/
│   │   └── PrescriptionForm.tsx   ← Use EnumSelect
│   └── admin/
│       └── EnumManagement.tsx     ← Manage dropdowns
└── lib/
    └── api-client.ts              ← Your API calls
```

---

## Deployment Checklist

- [ ] Copy `useEnumOptions.ts` hook
- [ ] Copy `EnumSelect.tsx` component
- [ ] Set up React Query in main.tsx
- [ ] Replace hardcoded dropdowns (start with 1)
- [ ] Test form submission
- [ ] Test doctor filter if needed
- [ ] Test in different roles (admin, doctor, staff)
- [ ] Deploy

---

## What's Already Done (Backend)

✅ API endpoints ready  
✅ 10 enum types seeded  
✅ Database tables created  
✅ Doctor filtering logic done  
✅ Admin CRUD endpoints ready  

## What You Need to Do (Frontend)

📝 Copy the hook  
📝 Copy the component  
📝 Replace hardcoded dropdowns  
📝 Test forms  

**That's it! No complicated migration.**

---

## Links

- API Docs: `http://localhost:8000/docs` (Swagger)
- Enum Types Endpoint: `GET /enums/admin/types`
- Read More: `docs/FRONTEND_QUICK_START.md` in repo

---

**Print this sheet and keep it handy! 📋**
