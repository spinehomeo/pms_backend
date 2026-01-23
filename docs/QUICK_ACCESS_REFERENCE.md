# Quick-Access Appointment Booking - API Quick Reference

## 📱 New Streamlined API Flow

### Option 1: Two-Step Flow (Recommended for Frontend)
Perfect for apps that need both login token and appointment confirmation.

#### Step 1: Quick-Access (Registration + Login)
```bash
POST /users/patients/quick-access
Content-Type: application/json

{
  "full_name": "Ahmed Ali",
  "phone": "03001234567",
  "gender": "male"
}
```

**Response:**
```json
{
  "access_token": "eyJhbGc...",
  "token_type": "bearer",
  "expires_in": 2592000,
  "patient": {
    "id": "550e8400-e29b-41d4-a716-446655440000",
    "full_name": "Ahmed Ali",
    "phone": "03001234567",
    "gender": "male",
    "doctor": {
      "id": "660e8400-e29b-41d4-a716-446655441111",
      "full_name": "Dr. Fatima Khan",
      "specialization": "General Practitioner"
    }
  },
  "message": "Patient registered and logged in successfully"
}
```

#### Step 2: Book Appointment
```bash
POST /public/appointments/book
Content-Type: application/json

{
  "doctor_id": "660e8400-e29b-41d4-a716-446655441111",
  "full_name": "Ahmed Ali",
  "phone": "03001234567",
  "gender": "male",
  "appointment_date": "2025-02-01",
  "appointment_time": "14:30",
  "reason": "General checkup"
}
```

**Response:**
```json
{
  "success": true,
  "appointment_id": "770e8400-e29b-41d4-a716-446655442222",
  "message": "Appointment booked successfully for 2025-02-01 at 14:30"
}
```

---

### Option 2: One-Step Flow (For Direct Booking)
Use this if you only need appointment confirmation, no patient login.

```bash
POST /public/appointments/book
Content-Type: application/json

{
  "doctor_id": "660e8400-e29b-41d4-a716-446655441111",
  "full_name": "Ahmed Ali",
  "phone": "03001234567",
  "gender": "male",
  "appointment_date": "2025-02-01",
  "appointment_time": "14:30",
  "reason": "General checkup"
}
```

**Response:**
```json
{
  "success": true,
  "appointment_id": "770e8400-e29b-41d4-a716-446655442222",
  "message": "Appointment booked successfully for 2025-02-01 at 14:30"
}
```

If patient already registered: Auto-detects and books directly.
If patient new: Auto-registers and books in one call.

---

## 🔍 Additional Endpoints

### Check Doctor Availability
```bash
GET /public/availability/{doctor_id}/{date}
# Example: GET /public/availability/660e8400-e29b-41d4-a716-446655441111/2025-02-01

Response:
{
  "doctor_id": "660e8400-e29b-41d4-a716-446655441111",
  "date": "2025-02-01",
  "available_slots": [
    {
      "start_time": "09:00",
      "end_time": "09:30"
    },
    {
      "start_time": "09:30",
      "end_time": "10:00"
    },
    {
      "start_time": "14:00",
      "end_time": "14:30"
    },
    {
      "start_time": "14:30",
      "end_time": "15:00"
    }
  ]
}
```

### List All Doctors
```bash
GET /public/doctors?skip=0&limit=100

Response:
{
  "doctors": [
    {
      "id": "660e8400-e29b-41d4-a716-446655441111",
      "full_name": "Dr. Fatima Khan",
      "specialization": "General Practitioner",
      "clinic_name": "Khan Medical Clinic",
      "clinic_address": "123 Main Street, Islamabad",
      "consultation_fee": 1500.0
    },
    {
      "id": "770e8400-e29b-41d4-a716-446655442222",
      "full_name": "Dr. Ali Ahmed",
      "specialization": "Cardiologist",
      "clinic_name": "Heart Care Center",
      "clinic_address": "456 Park Road, Lahore",
      "consultation_fee": 2500.0
    }
  ]
}
```

---

## 📋 Request/Response Field Reference

### PublicBookingRequest
```
doctor_id (string, required)
  - UUID of the doctor
  - Example: "660e8400-e29b-41d4-a716-446655441111"

full_name (string, required)
  - Patient's full name
  - Example: "Ahmed Ali"

phone (string, required)
  - Patient's phone number (Pakistan format)
  - Example: "03001234567"

gender (string, optional, default: "other")
  - Options: "male", "female", "other", "child"
  - Example: "male"

appointment_date (date, required)
  - ISO 8601 date format
  - Example: "2025-02-01"

appointment_time (time, required)
  - 24-hour format HH:MM
  - Example: "14:30"

reason (string, optional)
  - Reason for appointment
  - Example: "General checkup"
```

### AppointmentBookingResponse
```
success (boolean)
  - Whether booking was successful
  - Example: true

appointment_id (string)
  - UUID of the created appointment
  - Example: "770e8400-e29b-41d4-a716-446655442222"

message (string)
  - Confirmation message with date/time
  - Example: "Appointment booked successfully for 2025-02-01 at 14:30"
```

### PatientQuickAccessResponse
```
access_token (string)
  - JWT token for patient authentication
  - Valid for 30 days

token_type (string)
  - Always "bearer"

expires_in (integer)
  - Token expiration in seconds
  - Example: 2592000 (30 days)

patient (object)
  - Patient details including doctor info
  - Contains: id, full_name, phone, gender, doctor (nested)

message (string)
  - Status message
  - Example: "Patient registered and logged in successfully"
```

---

## ⚠️ Error Responses

### Invalid Doctor ID
```json
{
  "detail": "Invalid doctor ID format"
}
```

### Doctor Not Found
```json
{
  "detail": "Doctor not found"
}
```

### No Availability
```json
{
  "detail": "Doctor has no available slots on Saturdays"
}
```

### Time Not Available
```json
{
  "detail": "Appointment time not within doctor's availability. Available: 09:00-12:00, 14:00-18:00"
}
```

---

## 🔐 Patient Re-Use Logic

When you call `/public/appointments/book`, the system:

1. **Checks if patient exists** by matching:
   - Phone number
   - Doctor ID
   
2. **If patient exists**:
   - Reuses the existing patient record
   - Creates appointment immediately
   
3. **If patient NOT exists**:
   - Auto-generates email: `patient_{phone}@system.local`
   - Creates User account (PATIENT role)
   - Creates Patient record
   - Hashes phone as password
   - Creates appointment

This means **the same phone number for the same doctor = same patient record**.

---

## 💡 Use Cases

### Mobile App - Instant Booking
User fills form → Hit `/public/appointments/book` → Instant confirmation
- No intermediate steps
- No login screen
- Direct booking

### Web App - With Token Management
1. Hit `/users/patients/quick-access` → Get token
2. Store token in localStorage/sessionStorage
3. Hit `/public/appointments/book` → Auto-detects patient

### Multi-Doctor Clinic
- Same patient can register with multiple doctors
- Each doctor has separate patient records
- System handles isolation automatically

---

## 📱 Sample Frontend Code (JavaScript)

```javascript
// Step 1: Get quick access token
async function getQuickAccessToken(fullName, phone, gender) {
  const response = await fetch('/users/patients/quick-access', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      full_name: fullName,
      phone: phone,
      gender: gender || 'other'
    })
  });
  
  const data = await response.json();
  localStorage.setItem('access_token', data.access_token);
  return data;
}

// Step 2: Book appointment
async function bookAppointment(doctorId, fullName, phone, date, time, gender) {
  const response = await fetch('/public/appointments/book', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      doctor_id: doctorId,
      full_name: fullName,
      phone: phone,
      gender: gender || 'other',
      appointment_date: date,
      appointment_time: time
    })
  });
  
  return await response.json();
}

// Usage
const token = await getQuickAccessToken('Ahmed Ali', '03001234567', 'male');
const appointment = await bookAppointment(
  '660e8400-e29b-41d4-a716-446655441111',
  'Ahmed Ali',
  '03001234567',
  '2025-02-01',
  '14:30',
  'male'
);

console.log('Appointment ID:', appointment.appointment_id);
```

---

## 🔄 Migration from Old API

### Old Endpoints (Deprecated)
- ❌ `POST /patients/register` - Use `/users/patients/register-simple`
- ❌ `POST /patients/register-phone` - Use `/users/patients/quick-access` 
- ❌ `GET /patients/me` - Use authenticated endpoints with token

### New Recommended Flow
```
Old:  Register → Login → Check Availability → Book (4 calls)
New:  Quick-Access → Book (2 calls)
```

---

## 📞 Support & Documentation

- Full API docs: Visit `/docs` endpoint
- Doctor availability: `GET /public/availability/{doctor_id}/{date}`
- Doctor list: `GET /public/doctors`
- Manual registration: `POST /users/patients/register-simple`
- Manual login: `POST /login/patient-simple`
