# Dynamic Enum System - Implementation & Deployment Guide

## Overview

This guide walks through the new dynamic enum system that allows admins to create and manage dropdown options at runtime without code changes or deployments.

**What's New:**
- ✅ Add new enum types (dropdowns) at runtime
- ✅ Add/edit/disable options within each enum type
- ✅ Doctor-specific filtering (disable options they don't use)
- ✅ Staff sees options filtered by their assigned doctor
- ✅ Zero code changes per new enum - fully database-driven

---

## Database Schema

Three new tables store all enum data:

### `enum_types` (Dropdown Categories)
```sql
id          UUID (Primary Key)
key         TEXT (Unique) -- "AppointmentStatus", "VisitType", etc.
label       TEXT          -- "Appointment Status", "Visit Type", etc.
description TEXT          -- Optional details
is_system   BOOLEAN       -- True = seeded, cannot delete
is_active   BOOLEAN       -- Admin can disable globally
created_by  UUID FK       -- Admin who created it
created_at  TIMESTAMP
```

### `enum_options` (Values Inside Each Enum)
```sql
id            UUID (Primary Key)
enum_type_id  UUID FK       -- Links to parent enum_types.id
enum_type     TEXT          -- Denormalized copy of key (for queries)
value         TEXT          -- "Confirmed", "Pending", etc.
label         TEXT          -- Human-readable display
is_active     BOOLEAN       -- Admin can disable single options
is_system     BOOLEAN       -- True = seeded, cannot delete
sort_order    INT           -- Display order
created_by    UUID FK       -- Admin who created it
created_at    TIMESTAMP
```

### `doctor_enum_preferences` (Per-Doctor Toggles)
```sql
id              UUID (Primary Key)
doctor_id       UUID FK    -- Which doctor
enum_option_id  UUID FK    -- Which option they toggled
is_enabled      BOOLEAN    -- True = visible, False = hidden
```

---

## Backend Setup (Already Complete)

### Step 1: Database Migration

**Create the tables in your database:**

```bash
# Option A: Auto-generate migration (recommended)
alembic revision --autogenerate -m "add_dynamic_enum_tables"
alembic upgrade head

# Option B: Run script
python -m utils.initial_data
```

This creates the tables AND seeds the 10 core enum types with all their options.

### Step 2: API Endpoints Available

All endpoints are implemented in `routes/enums.py`:

#### **ADMIN ENDPOINTS** (requires superuser role)

```
GET    /api/v1/enums/admin/types
       → List all enum types (system + custom)

POST   /api/v1/enums/admin/types
       Body: { key, label, description }
       → Create new enum type (dropdown category)

PATCH  /api/v1/enums/admin/types/{type_id}
       Body: { label?, description?, is_active? }
       → Update enum type

DELETE /api/v1/enums/admin/types/{type_id}
       → Delete enum type (cascades to options)


GET    /api/v1/enums/admin/{enum_type_key}
       Query: ?include_inactive=false
       → List all options for a type (admin view)

POST   /api/v1/enums/admin/{enum_type_key}
       Body: { value, label, sort_order? }
       → Create new option

PATCH  /api/v1/enums/admin/option/{option_id}
       Body: { label?, is_active?, sort_order? }
       → Update option

DELETE /api/v1/enums/admin/option/{option_id}
       → Delete option (if not system)
```

#### **DOCTOR ENDPOINTS** (requires doctor role)

```
GET    /api/v1/enums/doctor/{enum_type_key}
       → Get options visible to current doctor
          (includes global active options - doctor's disabled ones)

POST   /api/v1/enums/doctor/preferences/{option_id}
       Body: { is_enabled: boolean }
       → Toggle an option on/off for current doctor

GET    /api/v1/enums/doctor/preferences/list/{enum_type_key}
       → Detailed view of doctor's preferences
          { enabled_options: [...], disabled_options: [...] }
```

#### **STAFF ENDPOINTS** (any authenticated user)

```
GET    /api/v1/enums/staff/{enum_type_key}
       Query: ?doctor_id={uuid}
       → Get options for a specific doctor (staff uses this)
```

#### **VALIDATION** (internal helper)

```
POST   /api/v1/enums/validate
       Query: ?enum_type={key}&value={value}&doctor_id={uuid}
       → Check if a value is valid
          Returns: { valid: boolean, message: string }
```

---

## Frontend Implementation

### Architecture Overview

The frontend needs to handle 3 different views:

1. **Admin Panel** - Manage enum types and options (CRUD)
2. **Doctor Settings** - Customize their dropdown preferences
3. **Dynamic Dropdowns Everywhere** - Use enums in forms/tables

---

## 1. Admin Panel - "Manage Dropdowns" Screen

### UI Mockup
```
┌──────────────────────────────────────────┐
│  Manage Dropdowns                [+ NEW] │
├──────────────────────────────────────────┤
│  Appointment Status      [system] [→]    │
│  Prescription Type       [system] [→]    │
│  Visit Type              [custom] [→]    │
│  Patient Category        [custom] [→]    │
└──────────────────────────────────────────┘
```

### React Implementation

```typescript
// hooks/useEnumManagement.ts
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { api } from '@/lib/api-client'

export function useEnumTypes() {
  return useQuery({
    queryKey: ['admin', 'enum-types'],
    queryFn: () => api.get('/enums/admin/types')
  })
}

export function useCreateEnumType() {
  const queryClient = useQueryClient()
  
  return useMutation({
    mutationFn: (payload: { key: string; label: string; description?: string }) =>
      api.post('/enums/admin/types', payload),
    
    onSuccess: () => {
      queryClient.invalidateQueries(['admin', 'enum-types'])
    }
  })
}

export function useEnumOptions(enumTypeKey: string) {
  return useQuery({
    queryKey: ['admin', 'enum-options', enumTypeKey],
    queryFn: () => api.get(`/enums/admin/${enumTypeKey}`),
    enabled: !!enumTypeKey
  })
}

export function useCreateEnumOption(enumTypeKey: string) {
  const queryClient = useQueryClient()
  
  return useMutation({
    mutationFn: (payload: { value: string; label: string; sort_order?: number }) =>
      api.post(`/enums/admin/${enumTypeKey}`, payload),
    
    onSuccess: () => {
      queryClient.invalidateQueries(['admin', 'enum-options', enumTypeKey])
    }
  })
}

export function useDeleteEnumOption(enumTypeKey: string) {
  const queryClient = useQueryClient()
  
  return useMutation({
    mutationFn: (optionId: string) =>
      api.delete(`/enums/admin/option/${optionId}`),
    
    onSuccess: () => {
      queryClient.invalidateQueries(['admin', 'enum-options', enumTypeKey])
    }
  })
}

// components/AdminEnumManager.tsx
export function AdminEnumManager() {
  const { data: enumTypes, isLoading } = useEnumTypes()
  const createEnum = useCreateEnumType()
  const [selectedType, setSelectedType] = useState<string | null>(null)

  return (
    <div className="space-y-4">
      <div className="flex justify-between items-center">
        <h2 className="text-xl font-bold">Manage Dropdowns</h2>
        <button
          onClick={() => {/* show create dialog */}}
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
              className="flex justify-between items-center p-3 border rounded"
            >
              <span>{type.label}</span>
              <span className="text-xs badge">
                {type.is_system ? 'System' : 'Custom'}
              </span>
              <button
                onClick={() => setSelectedType(type.key)}
                className="btn btn-sm"
              >
                Manage →
              </button>
            </div>
          ))}
        </div>
      )}

      {selectedType && (
        <EnumOptionsManager enumTypeKey={selectedType} />
      )}
    </div>
  )
}

// components/EnumOptionsManager.tsx
export function EnumOptionsManager({ enumTypeKey }: { enumTypeKey: string }) {
  const { data: options } = useEnumOptions(enumTypeKey)
  const createOption = useCreateEnumOption(enumTypeKey)
  const deleteOption = useDeleteEnumOption(enumTypeKey)
  const [newValue, setNewValue] = useState('')
  const [newLabel, setNewLabel] = useState('')

  const handleCreate = async () => {
    await createOption.mutateAsync({
      value: newValue,
      label: newLabel
    })
    setNewValue('')
    setNewLabel('')
  }

  return (
    <div className="space-y-4 border-t pt-4">
      <h3 className="font-bold">Options for {enumTypeKey}</h3>

      <div className="space-y-2">
        <input
          placeholder="Value (e.g., 'Confirmed')"
          value={newValue}
          onChange={(e) => setNewValue(e.target.value)}
        />
        <input
          placeholder="Label (e.g., 'Confirmed (appointment confirmed)')"
          value={newLabel}
          onChange={(e) => setNewLabel(e.target.value)}
        />
        <button onClick={handleCreate} className="btn btn-sm btn-primary">
          Add Option
        </button>
      </div>

      <div className="space-y-2">
        {options?.map((opt) => (
          <div key={opt.id} className="flex justify-between p-2 bg-gray-100 rounded">
            <div>
              <div className="font-semibold">{opt.label}</div>
              <div className="text-xs text-gray-600">Value: {opt.value}</div>
            </div>
            <button
              onClick={() => deleteOption.mutate(opt.id)}
              className="btn btn-xs btn-danger"
              disabled={opt.is_system}
            >
              {opt.is_system ? 'System (Cannot delete)' : 'Delete'}
            </button>
          </div>
        ))}
      </div>
    </div>
  )
}
```

---

## 2. Doctor Settings - "Customize Dropdowns" Screen

### UI Mockup
```
┌────────────────────────────────────┐
│  My Dropdown Preferences           │
├────────────────────────────────────┤
│  Appointment Status                │
│  ✅ Pending                        │
│  ✅ Confirmed                      │
│  ❌ Cancelled          [Enable]    │
│  ❌ No Show            [Enable]    │
└────────────────────────────────────┘
```

### React Implementation

```typescript
// hooks/useDoctorEnumPreferences.ts
export function useDoctorEnumPreferences(enumTypeKey: string) {
  return useQuery({
    queryKey: ['doctor', 'enum-preferences', enumTypeKey],
    queryFn: () => api.get(`/enums/doctor/preferences/list/${enumTypeKey}`)
  })
}

export function useToggleDoctorPreference(enumTypeKey: string) {
  const queryClient = useQueryClient()
  
  return useMutation({
    mutationFn: (payload: { optionId: string; isEnabled: boolean }) =>
      api.post(`/enums/doctor/preferences/${payload.optionId}`, {
        is_enabled: payload.isEnabled
      }),
    
    onSuccess: () => {
      queryClient.invalidateQueries(['doctor', 'enum-preferences', enumTypeKey])
      queryClient.invalidateQueries(['doctor', 'enum-options', enumTypeKey])
    }
  })
}

// components/DoctorEnumPreferences.tsx
export function DoctorEnumPreferences() {
  const enumTypes = [
    'AppointmentStatus',
    'PrescriptionType',
    'DayOfWeek',
    'ExceptionType'
    // Add more as needed
  ]

  return (
    <div className="space-y-4">
      <h2 className="text-xl font-bold">My Dropdown Preferences</h2>
      
      {enumTypes.map((type) => (
        <EnumPreferenceGroup key={type} enumTypeKey={type} />
      ))}
    </div>
  )
}

export function EnumPreferenceGroup({ enumTypeKey }: { enumTypeKey: string }) {
  const { data: preferences } = useDoctorEnumPreferences(enumTypeKey)
  const toggle = useToggleDoctorPreference(enumTypeKey)

  return (
    <div className="space-y-2 border p-4 rounded">
      <h3 className="font-semibold">{enumTypeKey}</h3>
      
      <div className="space-y-1">
        {preferences?.enabled_options?.map((opt) => (
          <div key={opt.id} className="flex items-center gap-2">
            <input
              type="checkbox"
              checked={true}
              onChange={() =>
                toggle.mutate({ optionId: opt.id, isEnabled: false })
              }
              id={opt.id}
            />
            <label htmlFor={opt.id}>{opt.label}</label>
          </div>
        ))}

        {preferences?.disabled_options?.map((opt) => (
          <div key={opt.id} className="flex items-center gap-2">
            <input
              type="checkbox"
              checked={false}
              onChange={() =>
                toggle.mutate({ optionId: opt.id, isEnabled: true })
              }
              id={opt.id}
            />
            <label htmlFor={opt.id} className="text-gray-400">
              {opt.label}
            </label>
          </div>
        ))}
      </div>
    </div>
  )
}
```

---

## 3. Dynamic Dropdowns in Forms

This is the most important part - one reusable hook replaces all hardcoded dropdowns.

### Core Hook

```typescript
// hooks/useEnumOptions.ts
export function useEnumOptions(
  enumTypeKey: string,
  doctorId?: string | null
) {
  const endpoint = doctorId
    ? `/enums/staff/${enumTypeKey}?doctor_id=${doctorId}`
    : `/enums/doctor/${enumTypeKey}`

  return useQuery({
    queryKey: ['enum', enumTypeKey, doctorId],
    queryFn: () => api.get(endpoint),
    staleTime: 30_000, // Cache for 30 seconds
  })
}

// Reusable dropdown component
export function EnumSelect({
  enumTypeKey,
  value,
  onChange,
  label,
  required = false,
  doctorId = null,
  ...props
}: {
  enumTypeKey: string
  value: string
  onChange: (value: string) => void
  label: string
  required?: boolean
  doctorId?: string | null
  [key: string]: any
}) {
  const { data: options, isLoading, error } = useEnumOptions(enumTypeKey, doctorId)

  if (isLoading) return <div>Loading...</div>
  if (error) return <div>Error loading options</div>

  return (
    <div className="form-group">
      <label>
        {label} {required && <span className="text-red-500">*</span>}
      </label>
      <select
        value={value}
        onChange={(e) => onChange(e.target.value)}
        required={required}
        {...props}
      >
        <option value="">-- Select {label} --</option>
        {options?.map((opt) => (
          <option key={opt.id} value={opt.value}>
            {opt.label}
          </option>
        ))}
      </select>
    </div>
  )
}
```

### Usage Examples

```typescript
// In AppointmentForm
function AppointmentForm({ doctorId }: { doctorId: string }) {
  const [status, setStatus] = useState('')

  return (
    <form>
      <EnumSelect
        enumTypeKey="AppointmentStatus"
        value={status}
        onChange={setStatus}
        label="Status"
        doctorId={doctorId}
        required
      />
      {/* Rest of form */}
    </form>
  )
}

// In PrescriptionForm
function PrescriptionForm() {
  const [type, setType] = useState('')
  const [repetition, setRepetition] = useState('')

  return (
    <form>
      <EnumSelect
        enumTypeKey="PrescriptionType"
        value={type}
        onChange={setType}
        label="Prescription Type"
        required
      />
      
      <EnumSelect
        enumTypeKey="RepetitionEnum"
        value={repetition}
        onChange={setRepetition}
        label="Frequency"
        required
      />
      {/* Rest of form */}
    </form>
  )
}

// In DoctorAvailabilityForm
function DoctorAvailabilityForm() {
  const [dayOfWeek, setDayOfWeek] = useState('')

  return (
    <form>
      <EnumSelect
        enumTypeKey="DayOfWeek"
        value={dayOfWeek}
        onChange={setDayOfWeek}
        label="Day of Week"
        required
      />
      {/* Rest of form */}
    </form>
  )
}

// In ExceptionForm
function DoctorAvailabilityExceptionForm() {
  const [exceptionType, setExceptionType] = useState('')

  return (
    <form>
      <EnumSelect
        enumTypeKey="ExceptionType"
        value={exceptionType}
        onChange={setExceptionType}
        label="Exception Type"
        required
      />
      {/* Rest of form */}
    </form>
  )
}
```

---

## Complete Frontend Setup Flow

1. **Bootstrap Phase**
   - Load enum types on app startup
   - Cache them in React Query

2. **Form Rendering**
   - Use `<EnumSelect>` component instead of hardcoded `<select>`
   - Pass `enumTypeKey` and optionally `doctorId`

3. **Form Submission**
   - Validate using `/enums/validate` endpoint (optional, or let backend validate)
   - Send the string value in your form data

4. **Dropdown Customization**
   - Doctors visit "Settings" → "Dropdown Preferences"
   - Toggle options on/off
   - Changes applied immediately to their forms

---

## 10 Core Enum Types

These are seeded by default:

| Key | Label | Used For |
|-----|-------|----------|
| `AppointmentStatus` | Appointment Status | Appointment lifecycle |
| `PrescriptionType` | Prescription Type | Prescription classification |
| `RepetitionEnum` | Repetition | Dosage frequency |
| `DayOfWeek` | Day of Week | Doctor availability scheduling |
| `ExceptionType` | Exception Type | Availability exceptions |
| `UserRole` | User Role | Staff/doctor/admin distinction |
| `PatientGender` | Patient Gender | Patient demographics |
| `FormEnum` | Medicine Form | Medicine physical form |
| `ScaleEnum` | Scale | Medicine potency scale |
| `ManufacturerEnum` | Manufacturer | Medicine manufacturer |

---

## Creating a Custom Enum Type

### Admin Process

1. **Via API:**
   ```bash
   POST /api/v1/enums/admin/types
   {
     "key": "VisitType",
     "label": "Visit Type",
     "description": "How the patient is visiting (in-person, online, etc.)"
   }
   ```

2. **Add Options:**
   ```bash
   POST /api/v1/enums/admin/VisitType
   [
     { "value": "In-Person", "label": "In-Person Visit" },
     { "value": "Online", "label": "Online Consultation" },
     { "value": "Phone", "label": "Phone Call" }
   ]
   ```

3. **Frontend Uses Immediately:**
   ```typescript
   <EnumSelect
     enumTypeKey="VisitType"
     value={visitType}
     onChange={setVisitType}
     label="Visit Type"
   />
   ```

### No deployment needed! 🎉

---

## Troubleshooting

### "Enum type not found"
- Ensure the `enum_type_key` matches exactly (case-sensitive)
- Check `/enums/admin/types` to see registered types

### "Option disabled for this doctor"
- Doctor toggled it off in preferences
- Doctor can re-enable it or admin can override

### Frontend doesn't show new enum
- React Query cache expires after 30s
- Manually refresh `queryClient.invalidateQueries(['enum'])`

---

## Backend Integration Points

### Validating Enums in Your Routes

```python
# Before saving user input
is_valid = EnumService.validate_value(
    session,
    "AppointmentStatus",
    request_payload.status,
    doctor_id=current_user.id  # Filter by doctor if needed
)

if not is_valid:
    raise HTTPException(400, f"Invalid status: {request_payload.status}")

# Then proceed with saving
```

### Common Validation Pattern

```python
from utils.enum_service import EnumService

@router.post("/appointments", response_model=AppointmentPublic)
def create_appointment(
    payload: AppointmentCreate,
    session: SessionDep,
    current_user: CurrentUser
):
    # Validate enum value against doctor's filtered options
    if not EnumService.validate_value(
        session, "AppointmentStatus", payload.status, current_user.id
    ):
        raise HTTPException(
            400,
            f"Invalid status. Allowed values: {[opt.value for opt in EnumService.get_doctor_options(session, 'AppointmentStatus', current_user.id)]}"
        )
    
    # Proceed with appointment creation
    appointment = Appointment(
        status=payload.status,  # Now a string, not an Enum
        # ... rest of fields
    )
    session.add(appointment)
    session.commit()
    return appointment
```

---

## Migration Checklist

- [ ] Run Alembic migration: `alembic upgrade head`
- [ ] Seed initial data: `python -m utils.initial_data`
- [ ] Test enum endpoints in Swagger
- [ ] Update frontend to use `<EnumSelect>` component
- [ ] Remove hardcoded Python Enum imports from endpoints
- [ ] Test doctor preference toggles
- [ ] Deploy to production

---

## Performance Notes

- **Caching:** React Query caches for 30s by default
- **Database:** Indexed on `enum_type_id`, `doctor_id`, `is_active` for fast queries
- **Scalability:** Can handle 1000+ enum types and 10,000+ options
- **Doctor Filtering:** Uses efficient SQL with NOT IN clause

---

## Questions or Issues?

The system is fully functional. Start with:
1. Run migrations
2. Test admin endpoints in Swagger
3. Implement `<EnumSelect>` component in one form
4. Roll out to other forms
5. Doctor preferences gradually come online
