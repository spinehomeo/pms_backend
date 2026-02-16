**Homeopathic Patient Management System** designed specifically for homeopathic doctors.

---

## 🏥 **Overview**
This software is a **full-stack clinic management system** for homeopathic practitioners. It manages everything from patient registration to case-taking, prescription management, medicine stock, follow-ups, and reporting. It is secure, role-based, and tailored to homeopathic practice needs.

---

## 🔄 **Complete Workflow (Step-by-Step)**

### 1. **User Registration & Login**
- **Doctors/Staff** register via `/users/signup` or are added by an admin.
- **Patients** do not log in—they are managed by the doctor/staff.
- **Login** is done via email/password, with token-based authentication for all subsequent requests.

### 2. **Patient Registration**
- A new patient is added via `/patients/` (POST).
- Details captured: name, DOB, gender, contact, medical history, allergies, etc.
- Each patient gets a unique ID and is linked to the doctor.

### 3. **Case Taking (Case Entry)**
- For each visit, a **case** is created via `/cases/` (POST).
- Includes:
  - Chief complaint
  - Duration, onset, location, sensation
  - Modalities, concomitants
  - Mental/general/physical symptoms
  - Miasm assessment
  - Vitality assessment
- This forms the **homeopathic case record**.

### 4. **Appointment Scheduling**
- Appointments are booked via `/appointments/` (POST).
- Options for:
  - Date/time selection
  - Consultation type (first/follow-up)
  - Status tracking (scheduled → confirmed → in progress → completed)
- Doctors can view today’s and upcoming appointments.

### 5. **Prescription & Medicine Management**
- After case analysis, the doctor creates a **prescription** via `/prescriptions/` (POST).
- Includes:
  - Medicine selection (from master list)
  - Potency, dosage, duration
  - Dietary restrictions, avoidance instructions
- Prescription is linked to the case and patient.

### 6. **Medicine Stock Management**
- Doctors maintain their **medicine stock** via `/medicines/stock` (POST/GET).
- Track:
  - Potency (X, C, LM, etc.)
  - Form (globules, pills, drops, etc.)
  - Quantity, expiry, batch number
- System alerts for low stock and expiring medicines.

### 7. **Follow-up Management**
- After prescription, a **follow-up** is scheduled via `/followups/` (POST).
- Record:
  - Subjective/objective improvement
  - Aggravation/amelioration
  - New symptoms
  - Next follow-up date
- Helps in case progression tracking.

### 8. **Reporting & Analytics**
- Various reports available under `/reports/`:
  - Patient history
  - Medicine usage
  - Appointment statistics
  - Prescription analysis
  - Financial summary (consultation fees, medicine costs)
  - Expiry alerts

### 9. **Admin & System Management**
- Admin can manage users, send verification emails, test emails, view system info.
- Health check and system monitoring endpoints.

---

## 📋 **Areas Covered by the System**

| Area | Description | Key Endpoints |
|------|-------------|----------------|
| **Authentication & Users** | Login, token management, user CRUD, password reset | `/login/*`, `/users/*` |
| **Patient Management** | Patient registration, updating, search, stats | `/patients/*` |
| **Case Management** | Homeopathic case recording, symptoms, miasm | `/cases/*` |
| **Appointment Management** | Scheduling, status updates, availability check | `/appointments/*` |
| **Prescription Management** | Creating prescriptions, linking medicines, printing | `/prescriptions/*` |
| **Medicine Master** | Homeopathic medicine database (kingdom, symptoms, rubrics) | `/medicines/master/*` |
| **Medicine Stock** | Doctor’s personal stock, potency, expiry tracking | `/medicines/stock/*` |
| **Follow-up Tracking** | Recording follow-up visits, scheduling next visits | `/followups/*` |
| **Reporting & Analytics** | Patient history, medicine usage, financial reports | `/reports/*` |
| **Utilities** | Email testing, system health, verification emails | `/utils/*` |

---

## 🧑‍⚕️ **Doctor’s Perspective**
- **Dashboard**: See stats (total patients, appointments, low stock alerts).
- **Workflow**: Register patient → take case → prescribe → schedule follow-up.
- **Stock Management**: Keep track of homeopathic medicines, potencies, expiry.
- **Case Continuity**: View full patient history across visits.
- **Prescription Archive**: All past prescriptions are stored and retrievable.

---

## 👤 **Patient’s Perspective (Indirect)**
- **Record Keeping**: All their case details, prescriptions, and follow-ups are digitally stored.
- **Continuity of Care**: Doctor has full history for better treatment.
- **Reminders**: Follow-up dates can be tracked (though patient-facing reminders are not explicit in this API).
- **Print Prescription**: Option to print prescription for pharmacy/dispensary.

---

## 🧠 **Special Homeopathic Features**
- **Miasm Assessment** in cases.
- **Potency Scale** tracking (X, C, LM, etc.).
- **Medicine Kingdom** classification (plant, mineral, animal).
- **Modalities & Concomitants** recording.
- **Prescription Types**: Constitutional, Classical, Inter Current, Pure Bio Chemic, Mother Tincture, Patent.
- **Medicine Forms**: Diskettes, SOM, Blankets, Bio Chemic, Homoeo Tabs, Globules, Dilutions.
- **Manufacturers**: Schwabe, Reckweg, Lemasar, Dolisos, Kamal, Masood, BM, Kent, Brooks, Waris Shah, Self Packing.
- **Dosage Repetition**: OD, BD, TDS, Once Weekly, Once in 10 Days, Fortnightly, Monthly.

---

## 🔐 **Security & Access Control**
- Role-based access (`doctor`, `staff`, `admin`, `patient`).
- OAuth2 token-based authentication.
- Sensitive endpoints require valid tokens.
- Password encryption and secure session management.

---

## ✅ **Summary**
This is a **professional-grade, specialized practice management system** for homeopathic doctors. It covers the entire workflow from patient intake to follow-up, with special attention to homeopathic case-taking and medicine management. It is **not a patient portal**—it’s a doctor-facing clinic management tool that ensures organized, secure, and efficient practice operations.