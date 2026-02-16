# Frontend Implementation Guide: Doctor Availability & Exceptions

**Version:** 1.0  
**Last Updated:** February 16, 2025  
**For:** Frontend Developers  

---

## 📋 Table of Contents

1. [Overview](#overview)
2. [API Authentication](#api-authentication)
3. [Core Concepts](#core-concepts)
4. [API Endpoints Reference](#api-endpoints-reference)
5. [UI/UX Recommendations](#uiux-recommendations)
6. [Implementation Flows](#implementation-flows)
7. [Code Examples](#code-examples)
8. [State Management](#state-management)
9. [Validation Rules](#validation-rules)
10. [Error Handling](#error-handling)
11. [Testing Checklist](#testing-checklist)

---

## 🎯 Overview

This system allows doctors to:
1. **Set weekly recurring schedules** (e.g., "Monday 9 AM - 5 PM")
2. **Create date-specific exceptions** (e.g., "Unavailable on March 15th" or "Custom hours on April 3rd")

**Key Rule:** Date-specific exceptions always override weekly schedules.

---

## 🔐 API Authentication

All endpoints require **DoctorOAuth2** authentication (JWT Bearer token).

### Headers Required
```javascript
{
  "Authorization": "Bearer <access_token>",
  "Content-Type": "application/json"
}
```

### Base URL
```
https://your-api-domain.com/doctor_availability
```

---

## 💡 Core Concepts

### 1. Weekly Availability (Recurring Schedule)
- Defines regular working hours for each day of the week
- Multiple time slots per day allowed (e.g., morning & evening shifts)
- Used as the **default** schedule

### 2. Exceptions (Date-Specific Overrides)
- Override weekly schedule for specific dates
- Three types:
  - **`unavailable`**: Doctor completely unavailable (vacation, sick leave)
  - **`custom_hours`**: Different working hours for that day
  - **`holiday`**: Public holidays or personal days off

### 3. Priority Logic
```
Check Date → Has Exception? → YES: Use exception
                            → NO:  Use weekly schedule
```

---

## 📡 API Endpoints Reference

### Base Path: `/doctor_availability`

---

## 1️⃣ WEEKLY AVAILABILITY ENDPOINTS

### 1.1 Create Single Availability Slot

**POST** `/doctor_availability/`

Create one time slot for a specific day of the week.

#### Request Body
```json
{
  "day_of_week": "monday",
  "start_time": "09:00:00",
  "end_time": "17:00:00",
  "is_available": true,
  "max_patients_per_slot": 10,
  "notes": "Regular Monday hours"
}
```

#### Response (200 OK)
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "doctor_id": "650e8400-e29b-41d4-a716-446655440001",
  "day_of_week": "monday",
  "start_time": "09:00:00",
  "end_time": "17:00:00",
  "is_available": true,
  "max_patients_per_slot": 10,
  "notes": "Regular Monday hours"
}
```

#### Error Responses
```json
// 400 - Invalid time range
{
  "detail": "Start time must be before end time"
}

// 409 - Time slot overlap
{
  "detail": "Time slot overlaps with existing slot: 09:00 - 12:00"
}

// 403 - Not a doctor
{
  "detail": "Only doctors can create availability slots"
}
```

---

### 1.2 Bulk Create Availability

**POST** `/doctor_availability/bulk`

Create multiple slots at once (useful for setting up entire weekly schedule).

#### Request Body
```json
{
  "availability_slots": [
    {
      "day_of_week": "monday",
      "start_time": "09:00:00",
      "end_time": "12:00:00",
      "is_available": true,
      "max_patients_per_slot": 10
    },
    {
      "day_of_week": "monday",
      "start_time": "14:00:00",
      "end_time": "17:00:00",
      "is_available": true,
      "max_patients_per_slot": 8
    },
    {
      "day_of_week": "tuesday",
      "start_time": "09:00:00",
      "end_time": "17:00:00",
      "is_available": true
    }
  ]
}
```

#### Response (200 OK)
```json
{
  "data": [
    {
      "id": "550e8400-e29b-41d4-a716-446655440000",
      "doctor_id": "650e8400-e29b-41d4-a716-446655440001",
      "day_of_week": "monday",
      "start_time": "09:00:00",
      "end_time": "12:00:00",
      "is_available": true,
      "max_patients_per_slot": 10,
      "notes": null
    },
    // ... more slots
  ],
  "count": 3
}
```

---

### 1.3 Get Weekly Schedule

**GET** `/doctor_availability/schedule`

Get doctor's complete weekly schedule organized by day.

#### Response (200 OK)
```json
{
  "doctor_id": "650e8400-e29b-41d4-a716-446655440001",
  "schedule": {
    "monday": [
      {
        "id": "550e8400-e29b-41d4-a716-446655440000",
        "start_time": "09:00",
        "end_time": "12:00",
        "is_available": true,
        "max_patients_per_slot": 10,
        "notes": null
      },
      {
        "id": "550e8400-e29b-41d4-a716-446655440002",
        "start_time": "14:00",
        "end_time": "17:00",
        "is_available": true,
        "max_patients_per_slot": 8,
        "notes": "Afternoon shift"
      }
    ],
    "tuesday": [
      {
        "id": "550e8400-e29b-41d4-a716-446655440003",
        "start_time": "09:00",
        "end_time": "17:00",
        "is_available": true,
        "max_patients_per_slot": null,
        "notes": null
      }
    ]
    // ... other days
  }
}
```

---

### 1.4 Get Schedule with Patient Info

**GET** `/doctor_availability/schedule/patient-info`

Get weekly schedule with appointment details (which slots are booked).

#### Response (200 OK)
```json
{
  "doctor_id": "650e8400-e29b-41d4-a716-446655440001",
  "schedule": {
    "monday": [
      {
        "id": "550e8400-e29b-41d4-a716-446655440000",
        "start_time": "09:00",
        "end_time": "12:00",
        "is_available": true,
        "max_patients_per_slot": 10,
        "notes": null,
        "booked_count": 3,
        "appointments": [
          {
            "appointment_id": "750e8400-e29b-41d4-a716-446655440005",
            "patient_name": "John Doe",
            "appointment_time": "09:30",
            "status": "confirmed"
          }
          // ... more appointments
        ]
      }
    ]
  }
}
```

---

### 1.5 Get Available Slots for Specific Day

**GET** `/doctor_availability/slots/{day_of_week}`

Get all available time slots for a specific day (considering current bookings).

#### Path Parameters
- `day_of_week`: monday | tuesday | wednesday | thursday | friday | saturday | sunday

#### Response (200 OK)
```json
{
  "day_of_week": "monday",
  "available_slots": [
    {
      "slot_id": "550e8400-e29b-41d4-a716-446655440000",
      "start_time": "09:00",
      "end_time": "12:00",
      "remaining_capacity": 7,
      "is_full": false
    },
    {
      "slot_id": "550e8400-e29b-41d4-a716-446655440002",
      "start_time": "14:00",
      "end_time": "17:00",
      "remaining_capacity": 8,
      "is_full": false
    }
  ],
  "total_slots": 2,
  "booked_count": 3
}
```

---

### 1.6 List All Availability Slots

**GET** `/doctor_availability/`

Get paginated list of all availability slots.

#### Query Parameters
- `day`: (optional) Filter by day of week
- `skip`: Offset for pagination (default: 0)
- `limit`: Number of items (default: 100, max: 1000)

#### Example Request
```
GET /doctor_availability/?day=monday&skip=0&limit=10
```

#### Response (200 OK)
```json
{
  "data": [
    {
      "id": "550e8400-e29b-41d4-a716-446655440000",
      "doctor_id": "650e8400-e29b-41d4-a716-446655440001",
      "day_of_week": "monday",
      "start_time": "09:00:00",
      "end_time": "12:00:00",
      "is_available": true,
      "max_patients_per_slot": 10,
      "notes": null
    }
    // ... more slots
  ],
  "count": 15
}
```

---

### 1.7 Get Single Availability Slot

**GET** `/doctor_availability/{slot_id}`

Get details of a specific availability slot.

#### Path Parameters
- `slot_id`: UUID of the slot

#### Response (200 OK)
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "doctor_id": "650e8400-e29b-41d4-a716-446655440001",
  "day_of_week": "monday",
  "start_time": "09:00:00",
  "end_time": "12:00:00",
  "is_available": true,
  "max_patients_per_slot": 10,
  "notes": "Regular morning shift"
}
```

---

### 1.8 Update Availability Slot

**PUT** `/doctor_availability/{slot_id}`

Update an existing availability slot.

#### Request Body (all fields optional)
```json
{
  "day_of_week": "tuesday",
  "start_time": "10:00:00",
  "end_time": "18:00:00",
  "is_available": false,
  "max_patients_per_slot": 15,
  "notes": "Updated hours"
}
```

#### Response (200 OK)
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "doctor_id": "650e8400-e29b-41d4-a716-446655440001",
  "day_of_week": "tuesday",
  "start_time": "10:00:00",
  "end_time": "18:00:00",
  "is_available": false,
  "max_patients_per_slot": 15,
  "notes": "Updated hours"
}
```

---

### 1.9 Toggle Availability Status

**PATCH** `/doctor_availability/{slot_id}/toggle`

Quickly enable/disable a slot without updating other fields.

#### Response (200 OK)
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "doctor_id": "650e8400-e29b-41d4-a716-446655440001",
  "day_of_week": "monday",
  "start_time": "09:00:00",
  "end_time": "12:00:00",
  "is_available": false,  // Toggled
  "max_patients_per_slot": 10,
  "notes": null
}
```

---

### 1.10 Delete Availability Slot

**DELETE** `/doctor_availability/{slot_id}`

Delete a specific availability slot.

#### Response (200 OK)
```json
{
  "message": "Availability slot deleted successfully"
}
```

---

### 1.11 Delete All Slots (with optional filter)

**DELETE** `/doctor_availability/`

Delete all availability slots, optionally filtered by day.

#### Query Parameters
- `day`: (optional) Only delete slots for this day

#### Example Request
```
DELETE /doctor_availability/?day=monday
```

#### Response (200 OK)
```json
{
  "message": "Deleted 3 availability slot(s) successfully"
}
```

---

## 2️⃣ EXCEPTION ENDPOINTS

### 2.1 Create Exception

**POST** `/doctor_availability/exceptions`

Create a date-specific exception.

#### Request Body
```json
{
  "exception_date": "2025-03-15",
  "exception_type": "unavailable",
  "reason": "Attending medical conference"
}
```

#### Request Body (Custom Hours)
```json
{
  "exception_date": "2025-04-10",
  "exception_type": "custom_hours",
  "start_time": "10:00:00",
  "end_time": "14:00:00",
  "reason": "Half-day schedule"
}
```

#### Request Body (Holiday)
```json
{
  "exception_date": "2025-12-25",
  "exception_type": "holiday",
  "reason": "Christmas Day"
}
```

#### Response (200 OK)
```json
{
  "id": "850e8400-e29b-41d4-a716-446655440010",
  "doctor_id": "650e8400-e29b-41d4-a716-446655440001",
  "exception_date": "2025-03-15",
  "exception_type": "unavailable",
  "start_time": null,
  "end_time": null,
  "reason": "Attending medical conference",
  "is_active": true,
  "created_at": "2025-02-16T10:30:00Z",
  "updated_at": "2025-02-16T10:30:00Z"
}
```

#### Error Responses
```json
// 400 - Exception already exists
{
  "detail": "Exception already exists for 2025-03-15"
}

// 400 - Date in past
{
  "detail": "Exception date cannot be in the past"
}

// 400 - Invalid custom hours
{
  "detail": "Both start_time and end_time required for custom hours"
}
```

---

### 2.2 List All Exceptions

**GET** `/doctor_availability/exceptions`

Get all availability exceptions for the doctor.

#### Query Parameters
- `start_date`: (optional) Filter from this date (YYYY-MM-DD)
- `end_date`: (optional) Filter until this date (YYYY-MM-DD)
- `skip`: Offset for pagination (default: 0)
- `limit`: Number of items (default: 100)

#### Example Request
```
GET /doctor_availability/exceptions?start_date=2025-03-01&end_date=2025-03-31
```

#### Response (200 OK)
```json
{
  "data": [
    {
      "id": "850e8400-e29b-41d4-a716-446655440010",
      "doctor_id": "650e8400-e29b-41d4-a716-446655440001",
      "exception_date": "2025-03-15",
      "exception_type": "unavailable",
      "start_time": null,
      "end_time": null,
      "reason": "Attending medical conference",
      "is_active": true,
      "created_at": "2025-02-16T10:30:00Z",
      "updated_at": "2025-02-16T10:30:00Z"
    },
    {
      "id": "850e8400-e29b-41d4-a716-446655440011",
      "doctor_id": "650e8400-e29b-41d4-a716-446655440001",
      "exception_date": "2025-03-20",
      "exception_type": "custom_hours",
      "start_time": "10:00:00",
      "end_time": "14:00:00",
      "reason": "Half-day for personal appointment",
      "is_active": true,
      "created_at": "2025-02-16T11:00:00Z",
      "updated_at": "2025-02-16T11:00:00Z"
    }
  ],
  "count": 2
}
```

---

### 2.3 Get Single Exception

**GET** `/doctor_availability/exceptions/{exception_id}`

Get details of a specific exception.

#### Response (200 OK)
```json
{
  "id": "850e8400-e29b-41d4-a716-446655440010",
  "doctor_id": "650e8400-e29b-41d4-a716-446655440001",
  "exception_date": "2025-03-15",
  "exception_type": "unavailable",
  "start_time": null,
  "end_time": null,
  "reason": "Attending medical conference",
  "is_active": true,
  "created_at": "2025-02-16T10:30:00Z",
  "updated_at": "2025-02-16T10:30:00Z"
}
```

---

### 2.4 Update Exception

**PUT** `/doctor_availability/exceptions/{exception_id}`

Update an existing exception.

#### Request Body (all fields optional)
```json
{
  "exception_type": "custom_hours",
  "start_time": "09:00:00",
  "end_time": "13:00:00",
  "reason": "Updated: Half-day morning shift",
  "is_active": true
}
```

#### Response (200 OK)
```json
{
  "id": "850e8400-e29b-41d4-a716-446655440010",
  "doctor_id": "650e8400-e29b-41d4-a716-446655440001",
  "exception_date": "2025-03-15",
  "exception_type": "custom_hours",
  "start_time": "09:00:00",
  "end_time": "13:00:00",
  "reason": "Updated: Half-day morning shift",
  "is_active": true,
  "created_at": "2025-02-16T10:30:00Z",
  "updated_at": "2025-02-16T14:45:00Z"
}
```

---

### 2.5 Delete Exception

**DELETE** `/doctor_availability/exceptions/{exception_id}`

Delete (soft delete) an exception. This restores normal weekly schedule for that date.

#### Response (200 OK)
```json
{
  "message": "Exception deleted successfully"
}
```

---

## 3️⃣ UTILITY ENDPOINTS

### 3.1 Get Availability Calendar

**GET** `/doctor_availability/calendar`

Get a calendar view showing availability for a date range (combines weekly schedule + exceptions).

#### Query Parameters (Required)
- `start_date`: Start date (YYYY-MM-DD)
- `end_date`: End date (YYYY-MM-DD) - Max 365 days from start

#### Example Request
```
GET /doctor_availability/calendar?start_date=2025-03-01&end_date=2025-03-31
```

#### Response (200 OK)
```json
{
  "calendar": {
    "2025-03-01": {
      "available": true,
      "type": "regular",
      "start_time": "09:00:00",
      "end_time": "17:00:00",
      "reason": null
    },
    "2025-03-02": {
      "available": false,
      "type": "not_scheduled",
      "start_time": null,
      "end_time": null,
      "reason": null
    },
    "2025-03-15": {
      "available": false,
      "type": "unavailable",
      "start_time": null,
      "end_time": null,
      "reason": "Attending medical conference"
    },
    "2025-03-20": {
      "available": true,
      "type": "custom_hours",
      "start_time": "10:00:00",
      "end_time": "14:00:00",
      "reason": "Half-day schedule"
    }
    // ... rest of March
  }
}
```

#### Response Types Explained
- `"type": "regular"` - Normal weekly schedule applies
- `"type": "not_scheduled"` - No availability set for this day of week
- `"type": "unavailable"` - Exception: Doctor unavailable
- `"type": "custom_hours"` - Exception: Custom hours for this date
- `"type": "holiday"` - Exception: Marked as holiday

---

## 🎨 UI/UX Recommendations

### 1. Weekly Schedule Setup Page

**Layout:** 7-day week view with time slots for each day

**Components:**
```
┌─────────────────────────────────────────┐
│  Weekly Schedule Setup                   │
├─────────────────────────────────────────┤
│  Monday    [+ Add Time Slot]            │
│    09:00 - 12:00  [Edit] [Delete] [Toggle] │
│    14:00 - 17:00  [Edit] [Delete] [Toggle] │
│                                          │
│  Tuesday   [+ Add Time Slot]            │
│    09:00 - 17:00  [Edit] [Delete] [Toggle] │
│                                          │
│  Wednesday [+ Add Time Slot]            │
│    [No slots set]                       │
│                                          │
│  [Copy Schedule to All Days] [Clear All]│
└─────────────────────────────────────────┘
```

**Features:**
- ✅ Visual time picker (dropdown or slider)
- ✅ Drag-to-create time blocks
- ✅ Color-coded slots (available=green, unavailable=gray)
- ✅ Quick toggle on/off without deleting
- ✅ "Copy to other days" functionality
- ✅ Validation warnings for overlaps

---

### 2. Exception Management Calendar

**Layout:** Monthly calendar with visual indicators

```
┌─────────────────────────────────────────┐
│  << March 2025 >>        [+ Add Exception] │
├───────────────────────────────────────┤
│  Sun  Mon  Tue  Wed  Thu  Fri  Sat   │
│   1    2    3    4    5    6    7    │
│   8    9   10   11   12   13   14    │
│  15🚫 16   17   18   19   20⏰  21    │  
│  22   23   24   25🎉 26   27   28    │
│  29   30   31                         │
└─────────────────────────────────────────┘

Legend:
🚫 Unavailable
⏰ Custom Hours
🎉 Holiday
✅ Normal Schedule
```

**Features:**
- ✅ Click date to add exception
- ✅ Visual indicators for exception types
- ✅ Tooltip on hover showing details
- ✅ Past dates grayed out
- ✅ Highlight dates with appointments (prevent deletion)

---

### 3. Exception Creation Modal

```
┌─────────────────────────────────────────┐
│  Set Exception for March 15, 2025       │
├─────────────────────────────────────────┤
│  Exception Type:                         │
│  ○ Unavailable                           │
│  ○ Custom Hours                          │
│  ○ Holiday                               │
│                                          │
│  [If Custom Hours selected]              │
│  Start Time: [10:00] AM                  │
│  End Time:   [02:00] PM                  │
│                                          │
│  Reason (optional):                      │
│  [Attending medical conference____]      │
│                                          │
│  [Cancel]              [Save Exception]  │
└─────────────────────────────────────────┘
```

---

### 4. Unified Availability Dashboard

Show both weekly schedule AND upcoming exceptions:

```
┌─────────────────────────────────────────┐
│  My Availability Overview                │
├─────────────────────────────────────────┤
│  Regular Weekly Schedule                 │
│  Mon: 09:00-12:00, 14:00-17:00          │
│  Tue: 09:00-17:00                        │
│  Wed: Not working                        │
│  Thu: 09:00-17:00                        │
│  Fri: 09:00-15:00                        │
│                                          │
│  Upcoming Exceptions (Next 30 Days)      │
│  Mar 15  🚫 Unavailable - Conference     │
│  Mar 20  ⏰ Custom (10:00-14:00)         │
│  Mar 25  🎉 Holiday - Christmas          │
│                                          │
│  [Edit Weekly Schedule] [Manage Exceptions] │
└─────────────────────────────────────────┘
```

---

## 🔄 Implementation Flows

### Flow 1: Setting Up Weekly Schedule (First Time)

```
1. Doctor logs in
   ↓
2. Navigate to "Availability Settings"
   ↓
3. Display 7-day template (all empty)
   ↓
4. For each working day:
   - Click "+ Add Time Slot"
   - Select start time (e.g., 09:00)
   - Select end time (e.g., 17:00)
   - Optional: Set max patients
   - Optional: Add notes
   - Click "Save"
   ↓
5. Option: "Copy Monday schedule to Tue-Fri"
   ↓
6. Submit all slots using POST /bulk endpoint
   ↓
7. Show success message
   ↓
8. Display weekly schedule summary
```

---

### Flow 2: Adding an Exception

```
1. Doctor opens Exception Calendar
   ↓
2. Click on future date (e.g., March 15)
   ↓
3. Modal opens with exception form
   ↓
4. Select exception type:
   - Unavailable? → Only need reason
   - Custom Hours? → Need start/end time + reason
   - Holiday? → Only need reason
   ↓
5. Fill in form fields
   ↓
6. Frontend validation:
   - Date must be future
   - Custom hours: start < end
   - No duplicate exceptions for same date
   ↓
7. POST /exceptions
   ↓
8. On success:
   - Update calendar UI
   - Show toast notification
   - Close modal
   ↓
9. On error:
   - Display error message
   - Keep modal open
```

---

### Flow 3: Patient Booking Appointment (Consider Exceptions)

```
1. Patient selects doctor
   ↓
2. Frontend calls:
   GET /calendar?start_date=2025-03-01&end_date=2025-03-31
   ↓
3. Display calendar with:
   - Available dates (green)
   - Unavailable dates (gray/disabled)
   - Custom hours dates (yellow)
   ↓
4. Patient clicks available date
   ↓
5. Fetch available slots for that date:
   GET /slots/{day_of_week}
   ↓
6. Display time slot options
   ↓
7. Patient selects time slot
   ↓
8. Proceed with appointment booking
```

---

## 💻 Code Examples

### React Implementation

#### 1. Fetch Weekly Schedule

```typescript
// hooks/useWeeklySchedule.ts
import { useState, useEffect } from 'react';
import { apiClient } from '@/lib/api';

interface TimeSlot {
  id: string;
  start_time: string;
  end_time: string;
  is_available: boolean;
  max_patients_per_slot: number | null;
  notes: string | null;
}

interface WeeklySchedule {
  doctor_id: string;
  schedule: Record<string, TimeSlot[]>;
}

export const useWeeklySchedule = () => {
  const [schedule, setSchedule] = useState<WeeklySchedule | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchSchedule = async () => {
    try {
      setLoading(true);
      const response = await apiClient.get('/doctor_availability/schedule');
      setSchedule(response.data);
      setError(null);
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to fetch schedule');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchSchedule();
  }, []);

  return { schedule, loading, error, refetch: fetchSchedule };
};
```

---

#### 2. Create Availability Slot

```typescript
// components/AddAvailabilitySlot.tsx
import React, { useState } from 'react';
import { apiClient } from '@/lib/api';

interface AddSlotFormProps {
  onSuccess: () => void;
}

const AddAvailabilitySlot: React.FC<AddSlotFormProps> = ({ onSuccess }) => {
  const [formData, setFormData] = useState({
    day_of_week: 'monday',
    start_time: '09:00:00',
    end_time: '17:00:00',
    is_available: true,
    max_patients_per_slot: 10,
    notes: ''
  });
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setSubmitting(true);
    setError(null);

    try {
      await apiClient.post('/doctor_availability/', formData);
      onSuccess();
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to create slot');
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      {error && (
        <div className="bg-red-100 border border-red-400 text-red-700 px-4 py-3 rounded">
          {error}
        </div>
      )}

      <div>
        <label className="block text-sm font-medium text-gray-700">
          Day of Week
        </label>
        <select
          value={formData.day_of_week}
          onChange={(e) => setFormData({ ...formData, day_of_week: e.target.value })}
          className="mt-1 block w-full rounded-md border-gray-300 shadow-sm"
        >
          <option value="monday">Monday</option>
          <option value="tuesday">Tuesday</option>
          <option value="wednesday">Wednesday</option>
          <option value="thursday">Thursday</option>
          <option value="friday">Friday</option>
          <option value="saturday">Saturday</option>
          <option value="sunday">Sunday</option>
        </select>
      </div>

      <div className="grid grid-cols-2 gap-4">
        <div>
          <label className="block text-sm font-medium text-gray-700">
            Start Time
          </label>
          <input
            type="time"
            value={formData.start_time}
            onChange={(e) => setFormData({ ...formData, start_time: e.target.value + ':00' })}
            className="mt-1 block w-full rounded-md border-gray-300 shadow-sm"
          />
        </div>
        <div>
          <label className="block text-sm font-medium text-gray-700">
            End Time
          </label>
          <input
            type="time"
            value={formData.end_time}
            onChange={(e) => setFormData({ ...formData, end_time: e.target.value + ':00' })}
            className="mt-1 block w-full rounded-md border-gray-300 shadow-sm"
          />
        </div>
      </div>

      <div>
        <label className="block text-sm font-medium text-gray-700">
          Max Patients per Slot
        </label>
        <input
          type="number"
          min="1"
          value={formData.max_patients_per_slot}
          onChange={(e) => setFormData({ ...formData, max_patients_per_slot: parseInt(e.target.value) })}
          className="mt-1 block w-full rounded-md border-gray-300 shadow-sm"
        />
      </div>

      <div>
        <label className="block text-sm font-medium text-gray-700">
          Notes (optional)
        </label>
        <textarea
          value={formData.notes}
          onChange={(e) => setFormData({ ...formData, notes: e.target.value })}
          className="mt-1 block w-full rounded-md border-gray-300 shadow-sm"
          rows={2}
        />
      </div>

      <button
        type="submit"
        disabled={submitting}
        className="w-full bg-blue-600 text-white py-2 px-4 rounded-md hover:bg-blue-700 disabled:opacity-50"
      >
        {submitting ? 'Adding...' : 'Add Availability Slot'}
      </button>
    </form>
  );
};

export default AddAvailabilitySlot;
```

---

#### 3. Exception Calendar Component

```typescript
// components/ExceptionCalendar.tsx
import React, { useState, useEffect } from 'react';
import { apiClient } from '@/lib/api';
import { format, startOfMonth, endOfMonth, eachDayOfInterval, isSameMonth, isBefore, startOfToday } from 'date-fns';

interface Exception {
  id: string;
  exception_date: string;
  exception_type: 'unavailable' | 'custom_hours' | 'holiday';
  start_time: string | null;
  end_time: string | null;
  reason: string | null;
}

const ExceptionCalendar: React.FC = () => {
  const [currentMonth, setCurrentMonth] = useState(new Date());
  const [exceptions, setExceptions] = useState<Exception[]>([]);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    fetchExceptions();
  }, [currentMonth]);

  const fetchExceptions = async () => {
    setLoading(true);
    const start = format(startOfMonth(currentMonth), 'yyyy-MM-dd');
    const end = format(endOfMonth(currentMonth), 'yyyy-MM-dd');

    try {
      const response = await apiClient.get(`/doctor_availability/exceptions`, {
        params: { start_date: start, end_date: end }
      });
      setExceptions(response.data.data);
    } catch (err) {
      console.error('Failed to fetch exceptions:', err);
    } finally {
      setLoading(false);
    }
  };

  const getExceptionForDate = (date: Date) => {
    const dateString = format(date, 'yyyy-MM-dd');
    return exceptions.find(ex => ex.exception_date === dateString);
  };

  const getExceptionIcon = (type: string) => {
    switch (type) {
      case 'unavailable': return '🚫';
      case 'custom_hours': return '⏰';
      case 'holiday': return '🎉';
      default: return '';
    }
  };

  const days = eachDayOfInterval({
    start: startOfMonth(currentMonth),
    end: endOfMonth(currentMonth)
  });

  const isPastDate = (date: Date) => isBefore(date, startOfToday());

  return (
    <div className="bg-white rounded-lg shadow p-6">
      <div className="flex justify-between items-center mb-6">
        <h2 className="text-2xl font-bold">Exception Calendar</h2>
        <div className="flex gap-2">
          <button
            onClick={() => setCurrentMonth(new Date(currentMonth.setMonth(currentMonth.getMonth() - 1)))}
            className="px-4 py-2 bg-gray-200 rounded hover:bg-gray-300"
          >
            ← Prev
          </button>
          <span className="px-4 py-2 font-semibold">
            {format(currentMonth, 'MMMM yyyy')}
          </span>
          <button
            onClick={() => setCurrentMonth(new Date(currentMonth.setMonth(currentMonth.getMonth() + 1)))}
            className="px-4 py-2 bg-gray-200 rounded hover:bg-gray-300"
          >
            Next →
          </button>
        </div>
      </div>

      {loading ? (
        <div className="text-center py-8">Loading...</div>
      ) : (
        <div className="grid grid-cols-7 gap-2">
          {['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'].map(day => (
            <div key={day} className="text-center font-semibold py-2">
              {day}
            </div>
          ))}

          {days.map(day => {
            const exception = getExceptionForDate(day);
            const isDisabled = isPastDate(day) || !isSameMonth(day, currentMonth);

            return (
              <div
                key={day.toISOString()}
                className={`
                  border rounded-lg p-4 text-center cursor-pointer
                  ${isDisabled ? 'bg-gray-100 text-gray-400 cursor-not-allowed' : 'hover:bg-blue-50'}
                  ${exception ? 'bg-yellow-50 border-yellow-300' : 'border-gray-200'}
                `}
                onClick={() => !isDisabled && handleDateClick(day)}
              >
                <div className="text-lg">{format(day, 'd')}</div>
                {exception && (
                  <div className="text-2xl mt-1" title={exception.reason || exception.exception_type}>
                    {getExceptionIcon(exception.exception_type)}
                  </div>
                )}
              </div>
            );
          })}
        </div>
      )}

      <div className="mt-6 flex gap-4 text-sm">
        <div className="flex items-center gap-2">
          <span>🚫</span> Unavailable
        </div>
        <div className="flex items-center gap-2">
          <span>⏰</span> Custom Hours
        </div>
        <div className="flex items-center gap-2">
          <span>🎉</span> Holiday
        </div>
      </div>
    </div>
  );
};

const handleDateClick = (date: Date) => {
  // Open modal to create exception for this date
  console.log('Create exception for:', format(date, 'yyyy-MM-dd'));
};

export default ExceptionCalendar;
```

---

#### 4. Create Exception Modal

```typescript
// components/CreateExceptionModal.tsx
import React, { useState } from 'react';
import { apiClient } from '@/lib/api';
import { format } from 'date-fns';

interface CreateExceptionModalProps {
  isOpen: boolean;
  onClose: () => void;
  selectedDate: Date;
  onSuccess: () => void;
}

const CreateExceptionModal: React.FC<CreateExceptionModalProps> = ({
  isOpen,
  onClose,
  selectedDate,
  onSuccess
}) => {
  const [formData, setFormData] = useState({
    exception_type: 'unavailable' as 'unavailable' | 'custom_hours' | 'holiday',
    start_time: '09:00:00',
    end_time: '17:00:00',
    reason: ''
  });
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  if (!isOpen) return null;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setSubmitting(true);
    setError(null);

    const payload: any = {
      exception_date: format(selectedDate, 'yyyy-MM-dd'),
      exception_type: formData.exception_type,
      reason: formData.reason || null
    };

    // Only include times for custom_hours
    if (formData.exception_type === 'custom_hours') {
      payload.start_time = formData.start_time;
      payload.end_time = formData.end_time;
    }

    try {
      await apiClient.post('/doctor_availability/exceptions', payload);
      onSuccess();
      onClose();
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to create exception');
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
      <div className="bg-white rounded-lg p-6 max-w-md w-full">
        <h2 className="text-2xl font-bold mb-4">
          Set Exception for {format(selectedDate, 'MMMM d, yyyy')}
        </h2>

        {error && (
          <div className="bg-red-100 border border-red-400 text-red-700 px-4 py-3 rounded mb-4">
            {error}
          </div>
        )}

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Exception Type
            </label>
            <div className="space-y-2">
              <label className="flex items-center">
                <input
                  type="radio"
                  value="unavailable"
                  checked={formData.exception_type === 'unavailable'}
                  onChange={(e) => setFormData({ ...formData, exception_type: 'unavailable' })}
                  className="mr-2"
                />
                Unavailable (Not working this day)
              </label>
              <label className="flex items-center">
                <input
                  type="radio"
                  value="custom_hours"
                  checked={formData.exception_type === 'custom_hours'}
                  onChange={(e) => setFormData({ ...formData, exception_type: 'custom_hours' })}
                  className="mr-2"
                />
                Custom Hours (Different schedule)
              </label>
              <label className="flex items-center">
                <input
                  type="radio"
                  value="holiday"
                  checked={formData.exception_type === 'holiday'}
                  onChange={(e) => setFormData({ ...formData, exception_type: 'holiday' })}
                  className="mr-2"
                />
                Holiday
              </label>
            </div>
          </div>

          {formData.exception_type === 'custom_hours' && (
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium text-gray-700">
                  Start Time
                </label>
                <input
                  type="time"
                  value={formData.start_time.slice(0, 5)}
                  onChange={(e) => setFormData({ ...formData, start_time: e.target.value + ':00' })}
                  className="mt-1 block w-full rounded-md border-gray-300 shadow-sm"
                  required
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700">
                  End Time
                </label>
                <input
                  type="time"
                  value={formData.end_time.slice(0, 5)}
                  onChange={(e) => setFormData({ ...formData, end_time: e.target.value + ':00' })}
                  className="mt-1 block w-full rounded-md border-gray-300 shadow-sm"
                  required
                />
              </div>
            </div>
          )}

          <div>
            <label className="block text-sm font-medium text-gray-700">
              Reason (optional)
            </label>
            <textarea
              value={formData.reason}
              onChange={(e) => setFormData({ ...formData, reason: e.target.value })}
              className="mt-1 block w-full rounded-md border-gray-300 shadow-sm"
              rows={3}
              placeholder="e.g., Attending medical conference"
            />
          </div>

          <div className="flex gap-3">
            <button
              type="button"
              onClick={onClose}
              className="flex-1 bg-gray-200 text-gray-700 py-2 px-4 rounded-md hover:bg-gray-300"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={submitting}
              className="flex-1 bg-blue-600 text-white py-2 px-4 rounded-md hover:bg-blue-700 disabled:opacity-50"
            >
              {submitting ? 'Saving...' : 'Save Exception'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};

export default CreateExceptionModal;
```

---

#### 5. API Client Setup

```typescript
// lib/api.ts
import axios from 'axios';

const BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'https://api.example.com';

export const apiClient = axios.create({
  baseURL: BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Request interceptor to add auth token
apiClient.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('access_token');
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => Promise.reject(error)
);

// Response interceptor for error handling
apiClient.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      // Redirect to login
      window.location.href = '/login';
    }
    return Promise.reject(error);
  }
);
```

---

### Vue.js Implementation

#### 1. Composable for Weekly Schedule

```typescript
// composables/useWeeklySchedule.ts
import { ref, onMounted } from 'vue';
import { apiClient } from '@/lib/api';

export const useWeeklySchedule = () => {
  const schedule = ref(null);
  const loading = ref(false);
  const error = ref(null);

  const fetchSchedule = async () => {
    loading.value = true;
    error.value = null;

    try {
      const response = await apiClient.get('/doctor_availability/schedule');
      schedule.value = response.data;
    } catch (err: any) {
      error.value = err.response?.data?.detail || 'Failed to fetch schedule';
    } finally {
      loading.value = false;
    }
  };

  onMounted(() => {
    fetchSchedule();
  });

  return {
    schedule,
    loading,
    error,
    refetch: fetchSchedule
  };
};
```

---

## 🗄️ State Management

### Redux Toolkit Example

```typescript
// store/availabilitySlice.ts
import { createSlice, createAsyncThunk, PayloadAction } from '@reduxjs/toolkit';
import { apiClient } from '@/lib/api';

interface TimeSlot {
  id: string;
  day_of_week: string;
  start_time: string;
  end_time: string;
  is_available: boolean;
  max_patients_per_slot: number | null;
  notes: string | null;
}

interface Exception {
  id: string;
  exception_date: string;
  exception_type: string;
  start_time: string | null;
  end_time: string | null;
  reason: string | null;
  is_active: boolean;
}

interface AvailabilityState {
  weeklySchedule: Record<string, TimeSlot[]> | null;
  exceptions: Exception[];
  loading: boolean;
  error: string | null;
}

const initialState: AvailabilityState = {
  weeklySchedule: null,
  exceptions: [],
  loading: false,
  error: null
};

// Async thunks
export const fetchWeeklySchedule = createAsyncThunk(
  'availability/fetchWeekly',
  async () => {
    const response = await apiClient.get('/doctor_availability/schedule');
    return response.data;
  }
);

export const fetchExceptions = createAsyncThunk(
  'availability/fetchExceptions',
  async ({ startDate, endDate }: { startDate: string; endDate: string }) => {
    const response = await apiClient.get('/doctor_availability/exceptions', {
      params: { start_date: startDate, end_date: endDate }
    });
    return response.data.data;
  }
);

export const createAvailabilitySlot = createAsyncThunk(
  'availability/create',
  async (slotData: Partial<TimeSlot>) => {
    const response = await apiClient.post('/doctor_availability/', slotData);
    return response.data;
  }
);

export const createException = createAsyncThunk(
  'availability/createException',
  async (exceptionData: Partial<Exception>) => {
    const response = await apiClient.post('/doctor_availability/exceptions', exceptionData);
    return response.data;
  }
);

export const deleteException = createAsyncThunk(
  'availability/deleteException',
  async (exceptionId: string) => {
    await apiClient.delete(`/doctor_availability/exceptions/${exceptionId}`);
    return exceptionId;
  }
);

// Slice
const availabilitySlice = createSlice({
  name: 'availability',
  initialState,
  reducers: {
    clearError: (state) => {
      state.error = null;
    }
  },
  extraReducers: (builder) => {
    // Fetch weekly schedule
    builder
      .addCase(fetchWeeklySchedule.pending, (state) => {
        state.loading = true;
        state.error = null;
      })
      .addCase(fetchWeeklySchedule.fulfilled, (state, action) => {
        state.loading = false;
        state.weeklySchedule = action.payload.schedule;
      })
      .addCase(fetchWeeklySchedule.rejected, (state, action) => {
        state.loading = false;
        state.error = action.error.message || 'Failed to fetch schedule';
      });

    // Fetch exceptions
    builder
      .addCase(fetchExceptions.fulfilled, (state, action) => {
        state.exceptions = action.payload;
      });

    // Create exception
    builder
      .addCase(createException.fulfilled, (state, action) => {
        state.exceptions.push(action.payload);
      });

    // Delete exception
    builder
      .addCase(deleteException.fulfilled, (state, action) => {
        state.exceptions = state.exceptions.filter(ex => ex.id !== action.payload);
      });
  }
});

export const { clearError } = availabilitySlice.actions;
export default availabilitySlice.reducer;
```

---

## ✅ Validation Rules

### Frontend Validation (Before API Call)

#### Weekly Availability
```typescript
const validateAvailabilitySlot = (slot: {
  day_of_week: string;
  start_time: string;
  end_time: string;
}) => {
  const errors: string[] = [];

  // Time range validation
  const start = new Date(`2000-01-01T${slot.start_time}`);
  const end = new Date(`2000-01-01T${slot.end_time}`);

  if (start >= end) {
    errors.push('Start time must be before end time');
  }

  // Minimum slot duration (e.g., 30 minutes)
  const duration = (end.getTime() - start.getTime()) / 1000 / 60;
  if (duration < 30) {
    errors.push('Slot duration must be at least 30 minutes');
  }

  // Business hours check (optional)
  const startHour = start.getHours();
  if (startHour < 6 || startHour > 22) {
    errors.push('Start time should be between 6 AM and 10 PM');
  }

  return errors;
};
```

#### Exceptions
```typescript
const validateException = (exception: {
  exception_date: string;
  exception_type: string;
  start_time?: string;
  end_time?: string;
}) => {
  const errors: string[] = [];

  // Date must be in future
  const exceptionDate = new Date(exception.exception_date);
  const today = new Date();
  today.setHours(0, 0, 0, 0);

  if (exceptionDate < today) {
    errors.push('Exception date cannot be in the past');
  }

  // Custom hours validation
  if (exception.exception_type === 'custom_hours') {
    if (!exception.start_time || !exception.end_time) {
      errors.push('Start time and end time required for custom hours');
    } else {
      const start = new Date(`2000-01-01T${exception.start_time}`);
      const end = new Date(`2000-01-01T${exception.end_time}`);

      if (start >= end) {
        errors.push('Start time must be before end time');
      }
    }
  }

  return errors;
};
```

---

## ⚠️ Error Handling

### Common Error Scenarios

#### 1. Overlapping Time Slots
```typescript
try {
  await createAvailabilitySlot(slotData);
} catch (error: any) {
  if (error.response?.status === 409) {
    toast.error('Time slot overlaps with existing schedule. Please choose different times.');
  }
}
```

#### 2. Duplicate Exception
```typescript
try {
  await createException(exceptionData);
} catch (error: any) {
  if (error.response?.status === 400 && error.response.data.detail.includes('already exists')) {
    toast.error('An exception already exists for this date. Edit the existing one instead.');
  }
}
```

#### 3. Unauthorized Access
```typescript
apiClient.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 403) {
      toast.error('You do not have permission to perform this action.');
    } else if (error.response?.status === 401) {
      // Redirect to login
      window.location.href = '/login';
    }
    return Promise.reject(error);
  }
);
```

#### 4. Network Errors
```typescript
const handleApiCall = async (apiFunction: () => Promise<any>) => {
  try {
    return await apiFunction();
  } catch (error: any) {
    if (!error.response) {
      // Network error
      toast.error('Network error. Please check your internet connection.');
    } else if (error.response.status >= 500) {
      // Server error
      toast.error('Server error. Please try again later.');
    } else {
      // Other errors
      toast.error(error.response.data.detail || 'An error occurred');
    }
    throw error;
  }
};
```

---

## 🧪 Testing Checklist

### Weekly Availability Testing

- [ ] Can create single availability slot
- [ ] Can create multiple slots via bulk endpoint
- [ ] Validation prevents start_time >= end_time
- [ ] Cannot create overlapping time slots for same day
- [ ] Can view weekly schedule organized by day
- [ ] Can update existing slot
- [ ] Can toggle slot on/off without deleting
- [ ] Can delete single slot
- [ ] Can delete all slots (with confirmation)
- [ ] Can delete all slots for specific day only
- [ ] UI shows correct time format (12/24 hour based on locale)
- [ ] Past time slots are grayed out or hidden

### Exception Testing

- [ ] Can create 'unavailable' exception
- [ ] Can create 'custom_hours' exception with time range
- [ ] Can create 'holiday' exception
- [ ] Validation prevents exception date in past
- [ ] Validation requires start/end time for custom_hours
- [ ] Cannot create duplicate exception for same date
- [ ] Can view all exceptions in list
- [ ] Can filter exceptions by date range
- [ ] Can update existing exception
- [ ] Can delete exception (restores normal schedule)
- [ ] Calendar view shows exception indicators
- [ ] Tooltip/modal shows exception details on hover/click

### Calendar Integration Testing

- [ ] Calendar API returns correct availability for date range
- [ ] Exceptions properly override weekly schedule
- [ ] Past dates are disabled in UI
- [ ] Future dates show correct availability status
- [ ] Patient booking UI respects exceptions
- [ ] Appointments cannot be booked on exception dates
- [ ] Custom hours show correctly in booking flow

### Edge Cases

- [ ] Doctor with no weekly schedule set
- [ ] Doctor with schedule but all slots disabled
- [ ] Multiple exceptions for same week
- [ ] Exception on day with no regular schedule
- [ ] Updating exception from unavailable to custom_hours
- [ ] Deleting exception while appointments exist
- [ ] Creating exception on day with existing appointments
- [ ] Timezone handling for times

---

## 📚 Additional Resources

### Enum Values Reference

#### Day of Week
```
monday | tuesday | wednesday | thursday | friday | saturday | sunday
```

#### Exception Types
```
unavailable | custom_hours | holiday
```

### Time Format
- API expects: `HH:MM:SS` (24-hour format, e.g., "14:30:00")
- Display to users: Based on locale (12-hour with AM/PM for US, 24-hour for most others)

### Date Format
- API expects: `YYYY-MM-DD` (e.g., "2025-03-15")

---

## 🎯 Quick Start Checklist for Frontend Developers

### Phase 1: Setup (Day 1)
- [ ] Set up API client with authentication
- [ ] Create reusable hooks/composables for API calls
- [ ] Set up state management (Redux/Vuex/Context)
- [ ] Implement error handling interceptors

### Phase 2: Weekly Schedule (Days 2-3)
- [ ] Build weekly schedule view component
- [ ] Build create/edit availability slot form
- [ ] Implement validation
- [ ] Add bulk creation feature
- [ ] Add toggle on/off functionality

### Phase 3: Exceptions (Days 4-5)
- [ ] Build monthly calendar component
- [ ] Build exception creation modal
- [ ] Implement exception list view
- [ ] Add edit/delete functionality
- [ ] Add visual indicators for exception types

### Phase 4: Integration (Day 6)
- [ ] Integrate calendar API for unified view
- [ ] Connect patient booking flow
- [ ] Add loading states and skeletons
- [ ] Implement toast notifications

### Phase 5: Polish (Day 7)
- [ ] Add responsive design
- [ ] Implement accessibility features
- [ ] Add confirmation dialogs for delete actions
- [ ] Write user documentation
- [ ] Conduct testing

---

## 💡 Pro Tips

1. **Caching:** Cache weekly schedule and invalidate only when modified
2. **Optimistic Updates:** Update UI immediately, rollback on API error
3. **Debounce:** Debounce search/filter inputs (300ms recommended)
4. **Lazy Loading:** Load exceptions only for visible month in calendar
5. **Keyboard Navigation:** Add keyboard shortcuts for power users
6. **Mobile First:** Design for mobile, enhance for desktop
7. **Undo Actions:** Consider implementing undo for delete operations
8. **Bulk Operations:** Allow selecting multiple dates for batch exception creation

---

## 🆘 Support & Troubleshooting

### Common Issues

**Issue:** 409 Conflict when creating slot  
**Solution:** Check for overlapping time slots in the same day

**Issue:** 403 Forbidden  
**Solution:** Verify user has doctor role and valid auth token

**Issue:** Calendar showing wrong availability  
**Solution:** Ensure exceptions are fetched for the correct date range

**Issue:** Times displaying incorrectly  
**Solution:** Check timezone handling and time format conversion

---

## 📝 Changelog

### Version 1.0 (Initial Release)
- Complete API documentation
- React code examples
- Vue.js code examples
- State management patterns
- Validation rules
- Error handling strategies
- Testing checklist

---

**Document prepared by:** Backend Team  
**For questions or clarifications:** Contact backend@example.com  
**Last reviewed:** February 16, 2025
