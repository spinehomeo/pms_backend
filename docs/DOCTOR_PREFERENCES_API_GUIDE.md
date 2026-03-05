# Doctor Preferences API Guide

This guide explains how to use the Doctor Preferences endpoints for managing custom fields in both **Cases** and **Follow-ups**.

---

## 📋 Overview

Doctors can customize which fields they use for:
- **Cases**: Patient case documentation (chief complaints, physical examination, etc.)
- **Follow-ups**: Follow-up notes (subjective improvement, objective findings, etc.)

Each doctor can:
- ✅ Enable/disable standard fields
- ✅ Create custom fields with their own names and types
- ✅ Edit custom field properties
- ✅ Delete custom fields
- ✅ Organize fields with positioning

---

## 🔑 Key Concept: `form_type` Parameter

All endpoints support a `form_type` query parameter to distinguish between field types:

```
?form_type=cases     # Work with case field preferences (default)
?form_type=followups # Work with follow-up field preferences
```

---

## 📡 Endpoints Overview

### 1. Initialize Standard Fields
**Initialize all standard fields for a doctor**

```http
POST /doctor-preferences/initialize-standard-fields?form_type=cases
```

**Purpose**: Set up standard fields when doctor first creates account

**Response**:
```json
{
  "message": "Standard cases fields initialized successfully"
}
```

**Standard Fields for Cases**:
- chief_complaint_patient (required)
- chief_complaint_duration (required)
- physicals
- noted_complaint_doctor
- peculiar_symptoms
- causation
- lab_reports

**Standard Fields for Follow-ups**:
- subjective_improvement
- objective_findings
- aggravation
- amelioration
- new_symptoms
- general_state
- plan

---

### 2. Get Enabled Fields Only
**Fetch only the fields that are enabled for this doctor**

```http
GET /doctor-preferences/fields?form_type=cases
```

**Response**:
```json
[
  {
    "field_name": "chief_complaint_patient",
    "display_name": "Chief Complaint (Patient's Words)",
    "field_type": "textarea",
    "is_required": true,
    "position": 0,
    "config": {}
  },
  {
    "field_name": "chief_complaint_duration",
    "display_name": "Chief Complaint Duration",
    "field_type": "text",
    "is_required": true,
    "position": 1,
    "config": {}
  },
  {
    "field_name": "treatment_response",
    "display_name": "Treatment Response",
    "field_type": "textarea",
    "is_required": false,
    "position": 2,
    "config": {}
  }
]
```

**Use this for**: Displaying the form to a doctor

---

### 3. Get All Fields (With Toggle Status)
**Fetch all fields including disabled ones + custom fields**

```http
GET /doctor-preferences/fields/all?form_type=cases
```

**Response**:
```json
[
  {
    "field_name": "chief_complaint_patient",
    "display_name": "Chief Complaint (Patient's Words)",
    "field_type": "textarea",
    "is_required": true,
    "is_enabled": true,
    "position": 0,
    "is_custom": false,
    "config": {}
  },
  {
    "field_name": "physicals",
    "display_name": "Physical Examination",
    "field_type": "textarea",
    "is_required": false,
    "is_enabled": false,        // <-- Disabled
    "position": 3,
    "is_custom": false,
    "config": {}
  },
  {
    "field_name": "treatment_response",
    "display_name": "Treatment Response",
    "field_type": "textarea",
    "is_required": false,
    "is_enabled": true,
    "position": 4,
    "is_custom": true,          // <-- Custom field
    "config": {}
  }
]
```

**Use this for**: 
- Settings page showing all available fields
- Toggle switches to enable/disable fields
- Custom field management interface

---

### 4. Toggle Standard Field On/Off
**Enable or disable a standard field**

```http
POST /doctor-preferences/fields/{field_name}/toggle?form_type=cases&enabled=true
```

**Parameters**:
- `field_name`: Name of the field (path parameter)
- `enabled`: true to enable, false to disable (query parameter)
- `form_type`: "cases" or "followups" (query parameter)

**Example**:
```http
POST /doctor-preferences/fields/physicals/toggle?form_type=cases&enabled=true
```

**Response**:
```json
{
  "message": "Field 'physicals' enabled"
}
```

**Rules**:
- ✅ Only works for standard fields
- ✅ Cannot use toggle on custom fields (delete them instead)
- ✅ Creates preference record if doesn't exist

---

### 5. Add Custom Field
**Create a new custom field for the doctor**

```http
POST /doctor-preferences/fields/custom?form_type=cases&field_name=treatment_response&display_name=Treatment+Response&field_type=textarea&is_required=false
```

**Query Parameters**:
- `field_name`: Internal field identifier (alphanumeric + underscores only)
- `display_name`: Display name for UI
- `field_type`: Type of field (text, textarea, number, date, select, etc.)
- `is_required`: Whether field is required (default: false)
- `form_type`: "cases" or "followups"

**Example - Using JSON body**:
```http
POST /doctor-preferences/fields/custom?form_type=cases&field_name=imaging_results&display_name=Imaging+Results&field_type=textarea&is_required=false
```

**Response**:
```json
{
  "message": "Custom field added",
  "field": {
    "field_name": "imaging_results",
    "display_name": "Imaging Results",
    "field_type": "textarea",
    "is_required": false
  }
}
```

**Validation**:
- Field name must be alphanumeric + underscores only
- Cannot contain spaces
- Must be unique per doctor per form type

---

### 6. Edit Custom Field
**Update properties of an existing custom field**

```http
PUT /doctor-preferences/fields/custom/{field_name}?form_type=cases&display_name=New+Display+Name&field_type=text&is_required=true
```

**Parameters**:
- `field_name`: Internal field name (path parameter)
- `display_name`: New display name (optional)
- `field_type`: New field type (optional)
- `is_required`: New required status (optional)
- `config`: Custom configuration as JSON (optional)
- `form_type`: "cases" or "followups"

**Example**:
```http
PUT /doctor-preferences/fields/custom/treatment_response?form_type=cases&display_name=Patient+Treatment+Response&is_required=true
```

**Response**:
```json
{
  "message": "Custom field updated successfully",
  "field": {
    "field_name": "treatment_response",
    "display_name": "Patient Treatment Response",
    "field_type": "textarea",
    "is_required": true,
    "config": null
  }
}
```

**Rules**:
- ✅ Only custom fields can be edited
- ❌ Cannot edit standard fields (toggle instead)

---

### 7. Delete Custom Field
**Remove a custom field**

```http
DELETE /doctor-preferences/fields/{field_name}?form_type=cases
```

**Parameters**:
- `field_name`: Field to delete (path parameter)
- `form_type`: "cases" or "followups"

**Example**:
```http
DELETE /doctor-preferences/fields/imaging_results?form_type=cases
```

**Response**:
```json
{
  "message": "Custom field deleted"
}
```

**Rules**:
- ✅ Only custom fields can be deleted
- ❌ Cannot delete standard fields (use toggle to disable instead)

---

## 🎯 Frontend Implementation Examples

### 1. Initialize Doctor Account

When a doctor creates their account, initialize all standard fields:

```javascript
// Initialize cases fields
fetch('/doctor-preferences/initialize-standard-fields?form_type=cases', {
  method: 'POST',
  headers: { 'Authorization': `Bearer ${token}` }
})

// Initialize followup fields
fetch('/doctor-preferences/initialize-standard-fields?form_type=followups', {
  method: 'POST',
  headers: { 'Authorization': `Bearer ${token}` }
})
```

### 2. Display Dynamic Case Form

Get enabled fields and render form dynamically:

```javascript
async function renderCaseForm(token) {
  const response = await fetch('/doctor-preferences/fields?form_type=cases', {
    headers: { 'Authorization': `Bearer ${token}` }
  })
  const fields = await response.json()
  
  // Render form with these fields
  fields.forEach(field => {
    const inputType = field.field_type === 'textarea' ? 'textarea' : 'input'
    const className = field.is_required ? 'required' : ''
    
    console.log(`<${inputType} name="${field.field_name}" 
                           placeholder="${field.display_name}"
                           class="${className}" />`)
  })
}
```

### 3. Settings Page - Field Management

Show toggle switches for all fields:

```javascript
async function renderFieldSettings(token) {
  const response = await fetch('/doctor-preferences/fields/all?form_type=cases', {
    headers: { 'Authorization': `Bearer ${token}` }
  })
  const allFields = await response.json()
  
  allFields.forEach(field => {
    const isStandard = !field.is_custom
    
    if (isStandard) {
      // Show toggle switch
      console.log(`
        <label>
          <input type="checkbox" 
                 ${field.is_enabled ? 'checked' : ''}
                 onChange={() => toggleField('${field.field_name}')} />
          ${field.display_name}
        </label>
      `)
    } else {
      // Show edit/delete buttons for custom fields
      console.log(`
        <div>
          ${field.display_name}
          <button onClick={() => editField('${field.field_name}')}>Edit</button>
          <button onClick={() => deleteField('${field.field_name}')}>Delete</button>
        </div>
      `)
    }
  })
}

async function toggleField(fieldName) {
  const enabled = // ... get new state
  await fetch(`/doctor-preferences/fields/${fieldName}/toggle?form_type=cases&enabled=${enabled}`, {
    method: 'POST',
    headers: { 'Authorization': `Bearer ${token}` }
  })
}
```

### 4. Add Custom Field

```javascript
async function addCustomField(token) {
  const response = await fetch(
    '/doctor-preferences/fields/custom' +
    '?form_type=cases' +
    '&field_name=imaging_results' +
    '&display_name=Imaging Results' +
    '&field_type=textarea' +
    '&is_required=false',
    {
      method: 'POST',
      headers: { 'Authorization': `Bearer ${token}` }
    }
  )
  
  const result = await response.json()
  console.log(result.message) // "Custom field added"
}
```

### 5. Create Case with Custom Fields

```javascript
async function createCase(token, caseData) {
  const response = await fetch('/cases/', {
    method: 'POST',
    headers: {
      'Authorization': `Bearer ${token}`,
      'Content-Type': 'application/json'
    },
    body: JSON.stringify({
      patient_id: caseData.patientId,
      chief_complaint_patient: caseData.chiefComplaint,
      chief_complaint_duration: caseData.duration,
      physicals: caseData.physicals,
      // Custom fields go here
      custom_fields: {
        imaging_results: caseData.imagingResults,
        treatment_response: caseData.treatmentResponse
      }
    })
  })
  
  return await response.json()
}
```

---

## ⚠️ Important Notes

### Case vs Followup Fields

Fields are **completely separate**:
- `?form_type=cases` → Uses `DoctorCaseFieldPreference` table
- `?form_type=followups` → Uses `DoctorFollowUpFieldPreference` table

A custom field named `notes` in cases is **different** from a custom field named `notes` in followups.

### Field Types Supported

Common field types:
- `text` - Single line text
- `textarea` - Multi-line text
- `number` - Numeric input
- `date` - Date picker
- `select` - Dropdown (requires options in config)
- `checkbox` - Boolean
- `email` - Email input
- `phone` - Phone input

### Data Storage

When creating/updating cases or followups:
- **Standard fields** are stored in their respective columns
- **Custom fields** are stored in the `custom_fields` JSONB column
- Only **enabled** custom fields are saved

Example case in database:
```json
{
  "chief_complaint_patient": "Headache",
  "chief_complaint_duration": "3 days",
  "physicals": "Normal",
  "custom_fields": {
    "imaging_results": "MRI shows no abnormalities",
    "treatment_response": "Positive"
  }
}
```

---

## 🔄 Workflow Example

**Step 1: Doctor Creates Account**
```
Initialize standard fields (cases) → Initialize standard fields (followups)
```

**Step 2: Doctor Customizes Preferences**
```
Get all fields → Toggle some off → Add custom fields → Edit custom fields
```

**Step 3: Create Case with Custom Data**
```
Get enabled fields → Show form to doctor → Submit with custom_fields data
```

**Step 4: Create Follow-up with Custom Data**
```
Get enabled followup fields → Show form → Submit with custom_fields data
```

---

## 🛠️ Error Handling

### Common Errors

**400 - Invalid field_name**
```json
{
  "detail": "Field name can only contain letters, numbers, and underscores"
}
```
→ Fix: Use `treatment_response` instead of `treatment response`

**400 - Field already exists**
```json
{
  "detail": "Field already exists"
}
```
→ Fix: Use a different field name or delete existing one first

**400 - Cannot delete standard field**
```json
{
  "detail": "Cannot delete standard fields. Use toggle to disable instead."
}
```
→ Fix: Use toggle endpoint instead

**403 - Only doctors can...**
```json
{
  "detail": "Only doctors can set preferences"
}
```
→ Fix: Ensure user is authenticated as doctor

**404 - Field not found**
```json
{
  "detail": "Field not found"
}
```
→ Fix: Check field name spelling

---

## 📊 Summary Table

| Action | Method | Endpoint | form_type | Standard | Custom |
|--------|--------|----------|-----------|----------|--------|
| Initialize | POST | `/initialize-standard-fields` | ✓ | ✓ | - |
| Get Enabled | GET | `/fields` | ✓ | ✓ | ✓ |
| Get All | GET | `/fields/all` | ✓ | ✓ | ✓ |
| Toggle | POST | `/fields/{name}/toggle` | ✓ | ✓ | - |
| Add Custom | POST | `/fields/custom` | ✓ | - | ✓ |
| Edit Custom | PUT | `/fields/custom/{name}` | ✓ | - | ✓ |
| Delete Custom | DELETE | `/fields/{name}` | ✓ | - | ✓ |

---

## 🔐 Authentication

All endpoints require a valid JWT token:
```javascript
headers: {
  'Authorization': `Bearer ${token}`,
  'Content-Type': 'application/json'
}
```

Token must be from a doctor user account.

---

## 📚 Related Endpoints

- `POST /cases/` - Create case with custom fields
- `PUT /cases/{case_id}` - Update case with custom fields
- `POST /followups/` - Create follow-up with custom fields
- `PUT /followups/{followup_id}` - Update follow-up with custom fields

