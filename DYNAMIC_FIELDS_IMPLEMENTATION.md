# Dynamic Case Fields Implementation - Summary

## Overview
Successfully implemented a comprehensive solution for dynamic case fields that allows doctors to customize their case forms while maintaining a consolidated database. Each doctor can have their own set of enabled/disabled standard fields and custom fields.

## Implementation Details

### 1. **Updated Models**

#### [models/cases_model.py](models/cases_model.py)
Added support for dynamic fields with the following changes:

**New Fields Added to PatientCaseBase:**
- `chief_complaint_patient`: Patient's own description of their complaint
- `noted_complaint_doctor`: Doctor's interpretation of the complaint
- `peculiar_symptoms`: Unique/unusual symptoms (fixed typo from "peculier")
- `causation`: Root cause information
- `lab_reports`: Laboratory test results
- `custom_fields`: JSONB column for doctor-specific dynamic fields

**Model Changes:**
- `PatientCaseCreate`: Now includes all new standard fields plus `custom_fields`
- `PatientCaseUpdate`: All fields optional for partial updates, includes `custom_fields`
- `PatientCasePublic`: Response model includes all fields with `patient_name` for reference

### 2. **New Doctor Preferences Model**

#### [models/doctor_preferences_model.py](models/doctor_preferences_model.py) (NEW)
Created `DoctorCaseFieldPreference` model to store doctor's field preferences:

**Key Features:**
- Tracks which fields each doctor has enabled/disabled
- Stores field metadata (display name, type, required status)
- Supports field configuration via JSONB
- Maintains field ordering/position
- Composite unique constraint: `(doctor_id, field_name)`

**Standard Field Types:**
- text, textarea, number, date, select

### 3. **Enhanced Cases Router**

#### [routes/cases.py](routes/cases.py)
Implemented key functions:

**`generate_case_number(doctor_id, case_date, session)`**
- New format: `C-MMMYY-001` (e.g., `C-JAN26-001`)
- Month abbreviated (JAN, FEB, etc.)
- Last 2 digits of year
- Sequential number per doctor per month
- Replaces old format: `CASE-YYYY-MM-001`

**`validate_custom_fields(doctor_id, custom_fields, session)`**
- Validates custom fields against doctor's preferences
- Checks for required fields
- Filters out fields not enabled for the doctor
- Raises HTTPException if required fields missing

**Updated Endpoints:**
- `POST /cases/`: Creates case with dynamic field validation
- `PUT /cases/{case_id}`: Updates case with optional custom fields
- Existing endpoints remain compatible

### 4. **New Doctor Preferences Router**

#### [routes/doctor_preferences.py](routes/doctor_preferences.py) (NEW)
Comprehensive field preference management:

**Endpoints:**
- `POST /doctor-preferences/initialize-standard-fields`: Set up standard fields for doctor
- `GET /doctor-preferences/fields`: Get all enabled fields for doctor
- `POST /doctor-preferences/fields/{field_name}/toggle`: Enable/disable a field
- `POST /doctor-preferences/fields/custom`: Add custom field
- `DELETE /doctor-preferences/fields/{field_name}`: Delete custom field

**Standard Fields (16 total):**
- physicals, chief_complaint_patient, noted_complaint_doctor
- peculiar_symptoms, causation, lab_reports
- onset, location, sensation
- modalities, concomitants
- generals, mentals
- miasm_assessment, vitality_assessment, case_notes

### 5. **Database Integration**

#### [models/__init__.py](models/__init__.py)
Updated to include:
- `DoctorCaseFieldPreference`
- `DoctorCaseTemplate`

#### [api/router.py](api/router.py)
Registered new `doctor_preferences` router in API

### 6. **Migration Script**

#### [utils/migrate_case_fields.py](utils/migrate_case_fields.py) (NEW)
Automated migration script:

**Features:**
- Adds new columns to `patient_case` table if they don't exist
- Initializes standard fields for all existing doctors
- Safe for repeated execution (checks for existing columns)
- Provides progress feedback

**Usage:**
```bash
python -m utils.migrate_case_fields
```

## API Usage Examples

### Initialize Doctor's Standard Fields
```http
POST /doctor-preferences/initialize-standard-fields
Authorization: Bearer {token}
```

### Get Doctor's Enabled Fields
```http
GET /doctor-preferences/fields
Authorization: Bearer {token}

Response:
[
  {
    "field_name": "physicals",
    "display_name": "Physical Examination",
    "field_type": "textarea",
    "is_required": false,
    "position": 0,
    "config": {}
  },
  ...
]
```

### Create Case with Custom Fields
```http
POST /cases/
Authorization: Bearer {token}

{
  "patient_id": "uuid",
  "chief_complaint": "Headache",
  "duration": "2 days",
  "physicals": "Normal",
  "chief_complaint_patient": "Severe head pain",
  "custom_fields": {
    "blood_pressure": "120/80",
    "temperature": "98.6"
  }
}
```

### Add Custom Field
```http
POST /doctor-preferences/fields/custom?field_name=blood_pressure&display_name=Blood Pressure&field_type=text&is_required=true
Authorization: Bearer {token}
```

### Toggle Field Visibility
```http
POST /doctor-preferences/fields/physicals/toggle?enabled=true
Authorization: Bearer {token}
```

## Database Schema

### New Columns in `patient_case`
- `chief_complaint_patient` (VARCHAR)
- `noted_complaint_doctor` (VARCHAR)
- `peculiar_symptoms` (TEXT)
- `causation` (TEXT)
- `lab_reports` (TEXT)
- `custom_fields` (JSONB)

### New Table: `doctor_case_field_preference`
```
id (UUID, PRIMARY KEY)
doctor_id (UUID, FOREIGN KEY -> user.id)
field_name (VARCHAR, INDEXED)
display_name (VARCHAR)
field_type (VARCHAR)
is_required (BOOLEAN)
is_enabled (BOOLEAN)
position (INTEGER)
config (JSONB, nullable)
created_at (TIMESTAMP)
updated_at (TIMESTAMP, nullable)
UNIQUE CONSTRAINT: (doctor_id, field_name)
```

## Benefits

✅ **Single Consolidated Database**: All doctors' data in one database
✅ **Dynamic Customization**: Each doctor can customize their form
✅ **Backward Compatible**: Existing cases continue to work
✅ **Scalable**: Add custom fields without database changes
✅ **Flexible**: Supports field ordering, requirements, and metadata
✅ **Type-Safe**: JSONB validation and type hints
✅ **Extensible**: Easy to add new features (e.g., field validation rules)

## Future Enhancements

1. **Field Validation Rules**: Add regex patterns, min/max values, etc.
2. **Field Groups**: Organize fields into sections
3. **Preset Templates**: Save and reuse field configurations
4. **Field Versioning**: Track changes to field definitions
5. **Audit Trail**: Log who changed which fields
6. **Import/Export**: Migrate field configs between doctors
7. **Field Dependencies**: Make fields conditional based on others

## Testing Recommendations

1. Test case creation with standard fields
2. Test case creation with custom fields
3. Test field preference toggling
4. Test custom field creation/deletion
5. Test case number generation format
6. Test validation of required custom fields
7. Test filtering of disabled fields
8. Test migration script on existing database

## Running the Migration

Before deploying, run:

```bash
# Run the migration
python -m utils.migrate_case_fields

# Or if using alembic, create a new migration:
alembic revision --autogenerate -m "add_dynamic_case_fields"
alembic upgrade head
```
