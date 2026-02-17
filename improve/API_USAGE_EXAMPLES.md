# API Usage Examples - Prescription with Quick-Add Medicine

## Scenario 1: Create Prescription with Existing Medicines

```http
POST /api/prescriptions/
Content-Type: application/json
Authorization: Bearer <doctor-token>

{
  "case_id": "550e8400-e29b-41d4-a716-446655440000",
  "prescription_type": "Constitutional",
  "dosage": "3 globules, 3 times daily",
  "prescription_duration": "1 month",
  "instructions": "Take before meals with water",
  "medicines": [
    {
      "medicine_id": 45,
      "quantity_prescribed": "1 bottle of 100 globules"
    },
    {
      "medicine_id": 67,
      "quantity_prescribed": "2 bottles"
    }
  ]
}
```

**Response:**
```json
{
  "id": "prescription-uuid",
  "prescription_number": "RX-2025-02-001",
  "case_id": "550e8400-e29b-41d4-a716-446655440000",
  "doctor_id": "doctor-uuid",
  "prescription_date": "2025-02-16",
  "prescription_type": "Constitutional",
  "dosage": "3 globules, 3 times daily",
  "prescription_duration": "1 month",
  "instructions": "Take before meals with water",
  "medicines": [
    {
      "id": "pm-uuid-1",
      "medicine_id": 45,
      "quantity_prescribed": "1 bottle of 100 globules",
      "medicine_name": "Arnica Montana",
      "potency": "200C",
      "form": "Globules"
    },
    {
      "id": "pm-uuid-2",
      "medicine_id": 67,
      "quantity_prescribed": "2 bottles",
      "medicine_name": "Belladonna",
      "potency": "30C",
      "form": "Dilutions"
    }
  ]
}
```

---

## Scenario 2: Create Prescription with Mix (Existing + New Medicine)

Doctor searches for "Pulsatilla 200C" but doesn't find it. They can quick-add it during prescription creation.

```http
POST /api/prescriptions/
Content-Type: application/json
Authorization: Bearer <doctor-token>

{
  "case_id": "550e8400-e29b-41d4-a716-446655440000",
  "prescription_type": "Classical",
  "dosage": "4 globules, twice daily",
  "prescription_duration": "2 weeks",
  "instructions": "Take morning and evening",
  "medicines": [
    {
      "medicine_id": 45,
      "quantity_prescribed": "1 bottle"
    },
    {
      "new_medicine": {
        "name": "Pulsatilla",
        "potency": "200",
        "potency_scale": "C",
        "form": "Globules",
        "manufacturer": "Schwabe",
        "description": "For changeable symptoms"
      },
      "quantity_prescribed": "1 bottle of 100 globules"
    }
  ]
}
```

**What Happens:**
1. System checks if "Pulsatilla 200C Globules" already exists in global catalog
2. If exists → Uses existing medicine ID
3. If not exists → Creates new medicine in catalog
4. New medicine marked as "needs verification" (is_verified=false)
5. New medicine added by this doctor (created_by_doctor_id set)
6. Medicine immediately available for use
7. All other doctors can now see and use "Pulsatilla 200C"

**Response:**
```json
{
  "id": "prescription-uuid",
  "prescription_number": "RX-2025-02-002",
  "medicines": [
    {
      "id": "pm-uuid-1",
      "medicine_id": 45,
      "quantity_prescribed": "1 bottle",
      "medicine_name": "Arnica Montana",
      "potency": "200C",
      "form": "Globules"
    },
    {
      "id": "pm-uuid-2",
      "medicine_id": 156,  // <-- Newly created medicine ID
      "quantity_prescribed": "1 bottle of 100 globules",
      "medicine_name": "Pulsatilla",
      "potency": "200C",
      "form": "Globules"
    }
  ]
}
```

---

## Scenario 3: Quick-Add Only (All New Medicines)

```http
POST /api/prescriptions/
Content-Type: application/json
Authorization: Bearer <doctor-token>

{
  "case_id": "550e8400-e29b-41d4-a716-446655440000",
  "prescription_type": "Inter Current",
  "dosage": "5 globules once",
  "prescription_duration": "Single dose",
  "medicines": [
    {
      "new_medicine": {
        "name": "Sulphur",
        "potency": "1M",
        "potency_scale": "C",
        "form": "Globules"
      },
      "quantity_prescribed": "Single dose"
    }
  ]
}
```

---

## Frontend UI Flow

### Option A: Search-First (Recommended)

```
Step 1: Search for medicine
┌─────────────────────────────────────┐
│ Search medicines:                   │
│ [Arnica 200_______________] [🔍]   │
└─────────────────────────────────────┘

Step 2: Results shown
┌─────────────────────────────────────┐
│ Results:                            │
│ • Arnica Montana 200C (Globules)    │
│ • Arnica Montana 30C (Globules)     │
│ • Arnica Montana 200C (Dilutions)   │
│                                     │
│ Not found? [+ Add New Medicine]     │
└─────────────────────────────────────┘

Step 3a: Select from results
→ Medicine added to prescription form

Step 3b: Click "Add New Medicine"
┌─────────────────────────────────────┐
│ Quick Add Medicine                  │
│                                     │
│ Name: [________________]            │
│ Potency: [____] Scale: [C ▼]       │
│ Form: [Globules ▼]                  │
│ Manufacturer: [Schwabe ▼] (optional)│
│                                     │
│ [Cancel] [Add Medicine]             │
└─────────────────────────────────────┘
→ Medicine added to catalog AND prescription form
```

### Option B: Add-During-Prescription

```
Prescription Form:
┌─────────────────────────────────────┐
│ Medicines:                          │
│ 1. [Select Medicine ▼] [Qty_____]  │
│    └─ Or [+ Add New]                │
│                                     │
│ [+ Add Another Medicine]            │
└─────────────────────────────────────┘
```

---

## Medicine Search API

### Quick Search (Autocomplete)
```http
GET /api/medicines/search?q=arnica&limit=10
Authorization: Bearer <doctor-token>
```

**Response:**
```json
{
  "data": [
    {
      "id": 45,
      "name": "Arnica Montana",
      "potency": "200",
      "potency_scale": "C",
      "form": "Globules",
      "is_verified": true,
      "is_favorite": true
    },
    {
      "id": 46,
      "name": "Arnica Montana",
      "potency": "30",
      "potency_scale": "C",
      "form": "Globules",
      "is_verified": true,
      "is_favorite": false
    }
  ],
  "count": 2
}
```

### Advanced Search with Filters
```http
GET /api/medicines/?search=arnica&only_favorites=true&limit=20
Authorization: Bearer <doctor-token>
```

---

## Direct Medicine Add API (Pre-build Catalog)

If doctor wants to add medicines to their catalog BEFORE prescribing:

```http
POST /api/medicines/
Content-Type: application/json
Authorization: Bearer <doctor-token>

{
  "name": "Calcarea Carbonica",
  "potency": "200",
  "potency_scale": "C",
  "form": "Globules",
  "manufacturer": "Schwabe",
  "description": "Constitutional remedy for calcium metabolism"
}
```

**Response:**
```json
{
  "id": 157,
  "name": "Calcarea Carbonica",
  "potency": "200",
  "potency_scale": "C",
  "form": "Globules",
  "manufacturer": "Schwabe",
  "is_verified": false,
  "created_by_doctor_id": "doctor-uuid",
  "created_at": "2025-02-16T10:30:00Z"
}
```

---

## Error Handling

### Error 1: Neither medicine_id nor new_medicine provided
```json
{
  "detail": "Either medicine_id or new_medicine must be provided"
}
```

### Error 2: Both medicine_id and new_medicine provided
```json
{
  "detail": "Provide either medicine_id OR new_medicine, not both"
}
```

### Error 3: Medicine_id doesn't exist
```json
{
  "detail": "Medicine with ID 999 not found"
}
```

### Error 4: Duplicate medicine (handled automatically)
If you try to quick-add "Arnica 200C Globules" but it already exists:
- System finds existing medicine
- Uses existing medicine_id
- No duplicate created
- No error thrown

---

## Admin Verification Workflow

### Admin Dashboard Shows:
```
Recently Added Medicines (Pending Verification):

┌──────────────────────────────────────────────────────┐
│ Medicine Name      │ Added By    │ Date       │      │
├────────────────────┼─────────────┼────────────┼──────┤
│ Pulsatilla 200C    │ Dr. Smith   │ 2025-02-16 │ [✓]  │
│ Calcarea Carb 1M   │ Dr. Jones   │ 2025-02-15 │ [✓]  │
│ Sulphur 30C        │ Dr. Brown   │ 2025-02-14 │ [✓]  │
└──────────────────────────────────────────────────────┘
```

### Admin Verification API:
```http
PATCH /api/medicines/157/verify
Content-Type: application/json
Authorization: Bearer <admin-token>

{
  "is_verified": true
}
```

---

## Benefits Summary

✅ **For Doctors:**
- Don't have to leave prescription form to add medicine
- No friction in workflow
- Can prescribe immediately
- Medicine saved for future use

✅ **For System:**
- No duplicate medicines (auto-detection)
- Global catalog grows organically
- Quality control via verification
- Audit trail (who added what)

✅ **For All Users:**
- Rich, comprehensive medicine catalog
- Medicines added by one doctor benefit all
- Standardized naming and details
- Searchable and filterable
