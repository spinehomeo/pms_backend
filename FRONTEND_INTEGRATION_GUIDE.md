# Backend Fixes - Frontend Integration Guide

## Quick Summary
All three integration issues have been fixed with **production-grade safety**:

| Issue | Status | Impact |
|-------|--------|--------|
| 1️⃣ Patient auth (400 "user not found") | ✅ **FIXED** | `/appointments/patient/book` now works with patient tokens |
| 2️⃣ Booked slots not marked | ✅ **FIXED** | Availability API now includes `booked` flag on each slot |
| 3️⃣ Race condition double booking | ✅ **FIXED** | Database constraint prevents concurrent bookings |

---

## 1️⃣ Patient Authentication Fix

### What Changed
- Patient tokens now include `entity: "patient"` field
- Backend resolves patients from Patient table (not User table)
- `/appointments/patient/book` uses `get_current_patient()` dependency

### Frontend Impact ✅
```
Patient Token Structure (NEW):
{
  "sub": "patient-uuid",
  "entity": "patient",      ← NEW FIELD
  "role": "patient",        ← NEW FIELD
  "exp": 1730000000
}
```

**Testing:**
1. Login via `/login/patient-simple` ✅ (works as before)
2. Book appointment via `POST /appointments/patient/book` ✅ (no more 400 errors)

### Expected Response
**Before:** `400 Bad Request - "user not found"`
**After:** `200 OK - Appointment created`

---

## 2️⃣ Booked Slots Status Fix

### What Changed
- `AvailableSlot` model now includes `booked: bool` field
- Available slots endpoint marks booked slots with `booked: true`

### Frontend Impact ✅
```json
GET /public/availability/{doctor_id}/{check_date}

Response (NEW structure):
{
  "available_slots": [
    {
      "start": "14:00",
      "end": "14:30",
      "duration_minutes": 30,
      "booked": false    ← NEW FIELD
    },
    {
      "start": "14:30",
      "end": "15:00",
      "duration_minutes": 30,
      "booked": true     ← NEW FIELD
    }
  ]
}
```

### Frontend Changes Needed
```javascript
// Can now disable booked slots in UI
slots.forEach(slot => {
  if (slot.booked) {
    disableSlot(slot);  // Disable in UI
    hideSlot(slot);     // Or hide from user
  }
});
```

### Testing
1. Get availability: `GET /public/availability/{doctor_id}/{date}`
2. Verify `booked` field exists on each slot ✅
3. Book an appointment manually
4. Get availability again
5. Verify previously booked slot now has `booked: true` ✅

---

## 3️⃣ Race Condition Prevention

### What Changed
- Database constraint prevents two appointments at same time
- Application returns clear error if slot is already booked

### Frontend Impact ✅
```
Request 1: Book slot 14:00 → SUCCESS (409)
Request 2: Book same slot 14:00 (concurrent) → CONFLICT (409)
```

### Expected Error Handling
```json
{
  "detail": "This time slot is no longer available. Please choose another time."
}
```

**Status Code:** `409 Conflict` (instead of unclear 400 error)

### Testing
```bash
# Make two concurrent requests for same slot
curl -X POST /appointments/patient/book \
  -H "Authorization: Bearer $TOKEN" \
  -d '{doctor_id, appointment_date, appointment_time}' &

curl -X POST /appointments/patient/book \
  -H "Authorization: Bearer $TOKEN" \
  -d '{doctor_id, appointment_date, appointment_time}' &

# Expected: One succeeds, one fails with 409
```

---

## Deployment Checklist

### 1. Database Migration (Required)
```bash
# Run pending migration for unique constraint
alembic upgrade head

# Verify constraint was created
SELECT * FROM pg_indexes 
WHERE indexname = 'idx_appointment_no_double_booking';
```

### 2. Restart Backend
```bash
# Reload FastAPI app to get new dependencies
docker-compose restart pms_backend
# OR
systemctl restart pms-backend
```

### 3. Test All Flows
- [ ] Test patient login `/login/patient-simple`
- [ ] Test patient booking `/appointments/patient/book`
- [ ] Test availability check `/public/availability/{doctor_id}/{date}`
- [ ] Verify `booked` field appears in response
- [ ] Test concurrent bookings (should see 409 error)

---

## API Changes Summary

### No Breaking Changes ✅
- All endpoints remain at same URLs
- All request parameters unchanged
- Response structure backward compatible (only new optional field added)

### New/Updated Endpoints
| Endpoint | Change | Impact |
|----------|--------|--------|
| `POST /appointments/patient/book` | Fixed auth | Now works with patient tokens |
| `GET /public/availability/{doctor_id}/{date}` | Added `booked` field | Frontend can disable booked slots |

---

## Error Handling

### Previous Errors (Now Fixed)
```
❌ 400 Bad Request: "user not found"
   → Caused by patient token auth issue
   → NOW FIXED ✅

❌ Double-booked appointments
   → Possible with concurrent requests
   → NOW PREVENTED by DB constraint ✅
```

### New Error Handling
```
409 Conflict: "This time slot is no longer available"
  → Slot was just booked by another user
  → Frontend should: Refresh availability and retry
```

---

## Frontend Recommendations

### 1. Handle 409 Conflict Gracefully
```javascript
try {
  await bookAppointment(slotData);
} catch (error) {
  if (error.status === 409) {
    // Slot was just booked
    showMessage("That slot was just booked. Please choose another time.");
    refreshAvailability();
  }
}
```

### 2. Disable Booked Slots in UI
```javascript
// Now possible with new 'booked' field
availableSlots.forEach(slot => {
  const slotElement = getSlotElement(slot);
  
  if (slot.booked) {
    slotElement.classList.add('disabled');
    slotElement.setAttribute('disabled', true);
  } else {
    slotElement.classList.remove('disabled');
    slotElement.removeAttribute('disabled');
  }
});
```

### 3. Verify Patient Token
```javascript
// Patient token now includes 'entity' field for verification
const token = localStorage.getItem('access_token');
const decoded = jwt_decode(token);

console.log(decoded.entity);  // Should be 'patient'
console.log(decoded.role);    // Should be 'patient'

if (decoded.entity !== 'patient') {
  // Not a patient token - don't use for /appointments/patient/book
}
```

---

## Troubleshooting

### Issue: Still getting 404 "Patient not found"
**Solution:**
1. Verify token includes `entity: "patient"` (decode JWT)
2. Verify patient exists in database
3. Restart backend after migration

### Issue: Availability slots don't show `booked` field
**Solution:**
1. Verify you're using latest API version
2. Clear browser cache
3. Check response from `/public/availability/{doctor_id}/{date}`

### Issue: Can't book appointment (409 Conflict)
**Solution:**
1. Slot was just booked by another user
2. Refresh availability with `GET /public/availability/...`
3. Choose a different slot with `booked: false`

---

## Success Criteria ✅

All three issues are resolved when:

1. ✅ Patient can book appointment without 400 error
2. ✅ Availability endpoint returns `booked` field
3. ✅ Concurrent bookings return 409 (not duplicates)
4. ✅ Frontend can disable booked slots in UI
5. ✅ All error messages are clear and actionable

---

## Questions?

For backend questions, refer to:
- [BACKEND_INTEGRATION_FIXES.md](BACKEND_INTEGRATION_FIXES.md) - Technical details
- [api/deps.py](api/deps.py) - Authentication logic
- [routes/public.py](routes/public.py) - Availability endpoint
- [routes/appointments.py](routes/appointments.py) - Booking endpoints
