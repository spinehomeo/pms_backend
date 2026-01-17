# Schema Changes & Migration Guide

## Summary of Changes

All schema changes have been made to support the new doctor availability system and enhanced patient management.

### 1. Patient Schema Updates (`20260117_update_patient_schema`)

#### New Fields Added:
- `cnic` (String, 15 chars) - National ID card number, unique per doctor
- `phone_secondary` (String, optional) - Secondary contact number
- `residential_address` (String, optional) - Primary residence address
- `postal_address` (String, optional) - Mailing address
- `city` (String, optional, 100 chars) - City of residence
- `payment_status` (Boolean, default=false) - Payment tracking (paid/unpaid)
- `current_medications` (String, optional) - Current medications list
- `is_active` (Boolean, default=true) - Soft delete flag

#### Modified Fields:
- `phone` - Remains required
- `address` - Replaced by `residential_address`

#### New Indexes:
- `idx_patient_cnic` - For CNIC lookups
- `idx_patient_city` - For city-based filtering
- `idx_patient_payment_status` - For payment filtering
- `idx_patient_doctor_city` - Composite index for doctor's patients by city

---

### 2. Doctor Availability Schema (`20260117_add_doctor_availability`)

#### New Table: `doctor_availability`

Stores doctor's working hours and availability for each day of the week.

**Columns:**
- `id` (UUID) - Primary key
- `doctor_id` (UUID) - Foreign key to `user.id`
- `day_of_week` (Enum: monday-sunday) - Day of week
- `start_time` (Time) - Work shift start time
- `end_time` (Time) - Work shift end time
- `is_available` (Boolean, default=true) - Enable/disable this slot
- `max_patients_per_slot` (Integer, optional) - Capacity limit
- `notes` (String, optional) - Additional notes

**Enum Type:** `dayofweek`
- Values: monday, tuesday, wednesday, thursday, friday, saturday, sunday

**Indexes:**
- `idx_doctor_day` - (doctor_id, day_of_week)
- `idx_doctor_availability` - (doctor_id, day_of_week, is_available)
- `idx_doctor_id` - (doctor_id)

---

## Migration Execution

### Prerequisites
- PostgreSQL database running
- Alembic configured with database connection
- Database credentials in `alembic.ini`

### Running Migrations

```bash
# Navigate to project directory
cd f:\2_PROJECTS\B_PMS\pms_backend

# Show current migration status
alembic current

# Show all pending migrations
alembic heads

# Apply all pending migrations
alembic upgrade head

# Apply specific migration
alembic upgrade 20260117_update_patient_schema
alembic upgrade 20260117_add_doctor_availability
```

### Migration Order
Migrations will automatically run in order:
1. `72b5e3eba95c_add_audit_log_model` (existing)
2. `20260117_add_doctor_availability` (NEW)
3. `20260117_update_patient_schema` (NEW)

---

## Updated Models

### Patient Model Changes

**Before:**
```python
class PatientBase(SQLModel):
    full_name: str
    gender: PatientGender
    phone: Optional[str]
    email: Optional[str]
    address: Optional[str]
    # ... other fields
```

**After:**
```python
class PatientBase(SQLModel):
    full_name: str
    gender: PatientGender
    phone: str  # NOW REQUIRED
    cnic: str  # NEW - Required, unique
    email: Optional[str]
    phone_secondary: Optional[str]  # NEW
    
    # Addresses - REORGANIZED
    residential_address: Optional[str]  # Was 'address'
    postal_address: Optional[str]  # NEW
    city: Optional[str]  # NEW
    
    # Payment & Status - NEW
    payment_status: bool  # NEW
    is_active: bool  # NEW (soft delete)
    
    # Medical - Added new field
    current_medications: Optional[str]  # NEW
    # ... existing medical fields
```

### New DoctorAvailability Model

```python
class DoctorAvailability(SQLModel, table=True):
    id: UUID
    doctor_id: UUID  # FK -> User.id
    day_of_week: DayOfWeek  # Enum
    start_time: time
    end_time: time
    is_available: bool
    max_patients_per_slot: Optional[int]
    notes: Optional[str]
```

---

## Route Changes

### Patients Route Updates

**GET /patients/** - Enhanced filtering:
- `search` - Now searches CNIC and city in addition to name/phone/email
- `payment_status` (NEW) - Filter by payment status
- `gender` (NEW) - Filter by gender

**POST /patients/** - New validation:
- `cnic` uniqueness check per doctor
- `phone` is now required

**PUT /patients/{id}** - Enhanced validation:
- `cnic` uniqueness check (exclude self)

**GET /patients/{id}/stats** - Enhanced response:
- Now includes `payment_status`, `gender`, `city`

### Setup Route (Doctor Availability)

**Base URL:** `/api/setup/`

**CREATE Endpoints:**
- `POST /setup/availability` - Create single slot
- `POST /setup/availability/bulk` - Create multiple slots

**READ Endpoints:**
- `GET /setup/availability` - List all slots
- `GET /setup/availability/{slot_id}` - Get specific slot
- `GET /setup/schedule` - Get weekly schedule
- `GET /setup/schedule/patient-info` - Schedule with patient data
- `GET /setup/availability/check/{day_name}` - Check available slots

**UPDATE Endpoints:**
- `PUT /setup/availability/{slot_id}` - Update slot
- `PATCH /setup/availability/{slot_id}/toggle` - Enable/disable slot

**DELETE Endpoints:**
- `DELETE /setup/availability/{slot_id}` - Delete single slot
- `DELETE /setup/availability` - Delete all (optionally filter by day)

---

## Integration Points

### Appointments with Doctor Availability

When creating/updating appointments (`/appointments`), the system:
1. Checks doctor's availability in `doctor_availability` table
2. Validates appointment time falls within available slot
3. Prevents overlapping appointments
4. Updates patient's `last_visit_date`

### Patients with Payment Tracking

- Doctors can filter patients by `payment_status`
- Quick view of payment status in patient stats
- Search functionality includes payment-related fields

---

## Files Modified

1. **Models:**
   - `models/patients_model.py` - Updated schema
   - `models/doctor_availability_model.py` - NEW file
   - `models/users_model.py` - Added relationship
   - `models/__init__.py` - Updated imports

2. **Routes:**
   - `routes/setup.py` - NEW file (moved from doctor_availability)
   - `routes/patients.py` - Enhanced filtering & validation

3. **API:**
   - `api/router.py` - Includes new setup router

4. **Migrations:**
   - `alembic/versions/20260117_add_doctor_availability.py` - NEW
   - `alembic/versions/20260117_update_patient_schema.py` - NEW

---

## Rollback Procedure

If needed, rollback migrations in reverse order:

```bash
# Rollback all migrations
alembic downgrade base

# Rollback specific migration
alembic downgrade 20260117_update_patient_schema
alembic downgrade 20260117_add_doctor_availability
```

---

## Testing Checklist

After running migrations:

- [ ] Database connects successfully
- [ ] Patient table has all new columns
- [ ] Doctor availability table created
- [ ] Existing patients can be queried
- [ ] Create new patient with CNIC (unique validation)
- [ ] Search patients by city
- [ ] Filter patients by payment_status
- [ ] Doctor can set availability
- [ ] Multiple slots per day work
- [ ] Availability check endpoint returns correct slots
- [ ] Create appointment validates against availability
- [ ] Patient stats includes payment_status

---

## Notes

- Migrations use idempotent SQL (handles duplicate object creation gracefully)
- All new columns have sensible defaults for existing data
- Enum types handled carefully for PostgreSQL compatibility
- Indexes created for optimal query performance
- Doctor availability can be toggled without deletion
- Patient `is_active` flag allows soft deletes
