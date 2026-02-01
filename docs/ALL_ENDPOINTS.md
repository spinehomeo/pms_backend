METHOD     PATH                                          TAGS
------------------------------------------------------------------------------------------
GET,HEAD   /openapi.json                                 -
GET,HEAD   /docs                                         -
GET,HEAD   /docs/oauth2-redirect                         -
GET,HEAD   /redoc                                        -
POST       /login/access-token                           🔑 Authentication
POST       /login                                        🔑 Authentication
POST       /login/patient-simple                         🔑 Authentication
POST       /login/test-token                             🔑 Authentication
POST       /password-recovery                            🔑 Authentication
POST       /reset-password/                              🔑 Authentication
POST       /verify-email/{token}                         🔑 Authentication
POST       /resend-verification                          🔑 Authentication
GET        /session                                      🔑 Authentication
POST       /password-recovery-html-content/{email}       🔑 Authentication
GET        /users/                                       👥 User Management
POST       /users/                                       👥 User Management
PATCH      /users/me                                     👥 User Management
PATCH      /users/me/password                            👥 User Management
GET        /users/me                                     👥 User Management
GET        /users/me/stats                               👥 User Management
DELETE     /users/me                                     👥 User Management
POST       /users/signup                                 👥 User Management
POST       /users/patients/register-simple               👥 User Management
POST       /users/patients/quick-access                  👥 User Management
GET        /users/{user_id}                              👥 User Management
PATCH      /users/{user_id}                              👥 User Management
DELETE     /users/{user_id}                              👥 User Management
GET        /users/doctors/list                           👥 User Management
POST       /doctor_availability/                         ⏰ Doctor Availability
POST       /doctor_availability/bulk                     ⏰ Doctor Availability
GET        /doctor_availability/schedule                 ⏰ Doctor Availability
GET        /doctor_availability/schedule/patient-info    ⏰ Doctor Availability
GET        /doctor_availability/{slot_id}                ⏰ Doctor Availability
GET        /doctor_availability/                         ⏰ Doctor Availability
PUT        /doctor_availability/{slot_id}                ⏰ Doctor Availability
PATCH      /doctor_availability/{slot_id}/toggle         ⏰ Doctor Availability
DELETE     /doctor_availability/{slot_id}                ⏰ Doctor Availability
DELETE     /doctor_availability/                         ⏰ Doctor Availability
GET        /doctor_availability/check/{day_name}         ⏰ Doctor Availability
GET        /public/doctors                               🌍 Public
GET        /public/doctors/{doctor_id}                   🌍 Public
GET        /public/availability/{doctor_id}/{check_date} 🌍 Public
POST       /public/appointments/book-public              🌍 Public
POST       /utils/test-email/                            🛠️ Utilities
POST       /utils/send-verification-email/               🛠️ Utilities
GET        /utils/health-check/                          🛠️ Utilities
GET        /utils/system-info/                           🛠️ Utilities
POST       /appointments/validate-availability           📅 Appointments
GET        /appointments/                                📅 Appointments
GET        /appointments/today                           📅 Appointments
GET        /appointments/upcoming                        📅 Appointments
GET        /appointments/{appointment_id}                📅 Appointments
POST       /appointments/                                📅 Appointments
PUT        /appointments/{appointment_id}                📅 Appointments
PATCH      /appointments/{appointment_id}/status         📅 Appointments
DELETE     /appointments/{appointment_id}                📅 Appointments
GET        /appointments/availability/{check_date}       📅 Appointments
POST       /appointments/patient/book                    📅 Appointments
GET        /cases/                                       📋 Cases
GET        /cases/{case_id}                              📋 Cases
POST       /cases/                                       📋 Cases
PUT        /cases/{case_id}                              📋 Cases
DELETE     /cases/{case_id}                              📋 Cases
GET        /cases/{case_id}/prescription                 📋 Cases
POST       /doctor-preferences/initialize-standard-fields ⚙️ Doctor Preferences
GET        /doctor-preferences/fields                    ⚙️ Doctor Preferences
POST       /doctor-preferences/fields/{field_name}/toggle ⚙️ Doctor Preferences
POST       /doctor-preferences/fields/custom             ⚙️ Doctor Preferences
DELETE     /doctor-preferences/fields/{field_name}       ⚙️ Doctor Preferences
GET        /followups/                                   🔔 Follow-ups
GET        /followups/{followup_id}                      🔔 Follow-ups
POST       /followups/                                   🔔 Follow-ups
PUT        /followups/{followup_id}                      🔔 Follow-ups
DELETE     /followups/{followup_id}                      🔔 Follow-ups
GET        /followups/case/{case_id}                     🔔 Follow-ups
GET        /followups/upcoming/due                       🔔 Follow-ups
POST       /followups/{followup_id}/schedule-next        🔔 Follow-ups
GET        /medicines/master                             💊 Medicines
GET        /medicines/master/{medicine_id}               💊 Medicines
GET        /medicines/stock                              💊 Medicines
GET        /medicines/stock/{stock_id}                   💊 Medicines
POST       /medicines/stock                              💊 Medicines
PUT        /medicines/stock/{stock_id}                   💊 Medicines
DELETE     /medicines/stock/{stock_id}                   💊 Medicines
GET        /medicines/stock/{stock_id}/usage             💊 Medicines
GET        /medicines/alerts/low-stock                   💊 Medicines
GET        /medicines/alerts/expiring                    💊 Medicines
GET        /patients/me                                  🧍 Patient
PATCH      /patients/me/update                           🧍 Patient
PATCH      /patients/me/password                         🧍 Patient
GET        /patients/me/appointments                     🧍 Patient
GET        /patients/me/appointments/upcoming            🧍 Patient
GET        /patients/me/appointments/{appointment_id}    🧍 Patient
POST       /patients/me/appointments/{appointment_id}/cancel 🧍 Patient
GET        /patients/                                    🧑‍⚕️ Doctor / Staff / Admin
GET        /patients/{patient_id}                        🧑‍⚕️ Doctor / Staff / Admin      
POST       /patients/                                    🧑‍⚕️ Doctor / Staff / Admin      
PUT        /patients/{patient_id}                        🧑‍⚕️ Doctor / Staff / Admin      
DELETE     /patients/{patient_id}                        🧑‍⚕️ Doctor / Staff / Admin      
GET        /patients/{patient_id}/stats                  🧑‍⚕️ Doctor / Staff / Admin      
GET        /prescriptions/                               📝 Prescriptions
GET        /prescriptions/{prescription_id}              📝 Prescriptions
POST       /prescriptions/                               📝 Prescriptions
PUT        /prescriptions/{prescription_id}              📝 Prescriptions
DELETE     /prescriptions/{prescription_id}              📝 Prescriptions
GET        /prescriptions/{prescription_id}/print        📝 Prescriptions
GET        /reports/patient-history/{patient_id}         📊 Reports
GET        /reports/medicine-usage                       📊 Reports
GET        /reports/appointment-statistics               📊 Reports
GET        /reports/prescription-analysis                📊 Reports
GET        /reports/financial-summary                    📊 Reports
GET        /reports/expiry-alerts                        📊 Reports
GET        /                                             -
GET        /doc                                          -
