# api/routes/reports.py
import uuid
from typing import Any, List, Optional
from datetime import date, datetime, timedelta, timezone
from collections import defaultdict

from fastapi import APIRouter, HTTPException, Query
from sqlmodel import func, select, and_, desc, asc

from api.deps import CurrentUser, SessionDep
from utils.time import utc_isoformat

from models.patients_model import Patient
from models.cases_model import PatientCase
from models.prescriptions_model import Prescription, PrescriptionMedicine, PrescriptionType
from models.appointments_model import Appointment, AppointmentStatus
from models.followups_model import FollowUp
from models.medicines_model import DoctorMedicineStock, MedicineUsageLog, MedicineMaster

from models.login_model import Message

router = APIRouter(prefix="/reports", tags=["📊 Reports"])


@router.get("/patient-history/{patient_id}")
def get_patient_history(
    session: SessionDep,
    current_user: CurrentUser,
    patient_id: uuid.UUID,
    from_date: Optional[date] = None,
    to_date: Optional[date] = None
) -> Any:
    """
    Get complete treatment history for a patient.
    """
    if not current_user.is_doctor:
        raise HTTPException(status_code=403, detail="Only doctors can access reports")
    
    # Verify patient belongs to doctor
    patient = session.get(Patient, patient_id)
    if not patient or patient.doctor_id != current_user.id:
        raise HTTPException(status_code=404, detail="Patient not found")
    
    # Date range
    if not from_date:
        from_date = date.today() - timedelta(days=365)  # Last year
    if not to_date:
        to_date = date.today()
    
    # Get cases
    cases = session.exec(
        select(PatientCase)
        .where(
            PatientCase.patient_id == patient_id,
            PatientCase.case_date.between(from_date, to_date)
        )
        .order_by(PatientCase.case_date.desc())
    ).all()
    
    # Get prescriptions with medicines
    prescriptions_data = []
    for case in cases:
        prescriptions = session.exec(
            select(Prescription)
            .where(Prescription.case_id == case.id)
            .order_by(Prescription.prescription_date.desc())
        ).all()
        
        for prescription in prescriptions:
            # Get prescription medicines
            prescription_medicines = session.exec(
                select(PrescriptionMedicine)
                .where(PrescriptionMedicine.prescription_id == prescription.id)
            ).all()
            
            medicines_info = []
            for pm in prescription_medicines:
                stock = session.get(DoctorMedicineStock, pm.stock_used_id)
                if stock:
                    medicines_info.append({
                        "medicine_name": stock.medicine.name,
                        "potency": stock.potency,
                        "form": stock.form,
                        "quantity_used": pm.quantity_used
                    })
            
            prescriptions_data.append({
                "prescription": prescription,
                "medicines": medicines_info,
                "case": case
            })
    
    # Get appointments
    appointments = session.exec(
        select(Appointment)
        .where(
            Appointment.patient_id == patient_id,
            Appointment.appointment_date.between(from_date, to_date)
        )
        .order_by(Appointment.appointment_date.desc())
    ).all()
    
    # Get follow-ups
    followups = []
    for case in cases:
        case_followups = session.exec(
            select(FollowUp)
            .where(FollowUp.case_id == case.id)
            .order_by(FollowUp.follow_up_date.desc())
        ).all()
        followups.extend(case_followups)
    
    # Calculate statistics
    total_visits = len(appointments)
    total_prescriptions = len(prescriptions_data)
    total_medicines = sum(len(p['medicines']) for p in prescriptions_data)
    
    # Get most prescribed medicines
    medicine_counts = defaultdict(int)
    for prescription_info in prescriptions_data:
        for medicine in prescription_info["medicines"]:
            medicine_counts[medicine["medicine_name"]] += 1
    
    top_medicines = sorted(
        medicine_counts.items(),
        key=lambda x: x[1],
        reverse=True
    )[:5]
    
    return {
        "patient": patient,
        "date_range": {
            "from": from_date.isoformat(),
            "to": to_date.isoformat()
        },
        "summary": {
            "total_cases": len(cases),
            "total_visits": total_visits,
            "total_prescriptions": total_prescriptions,
            "total_medicines": total_medicines,
            "first_visit": cases[-1].case_date if cases else None,
            "last_visit": cases[0].case_date if cases else None,
            "top_medicines": top_medicines
        },
        "timeline": {
            "cases": cases,
            "prescriptions": prescriptions_data,
            "appointments": appointments,
            "followups": followups
        },
        "generated_at": utc_isoformat()
    }


@router.get("/medicine-usage")
def get_medicine_usage_report(
    session: SessionDep,
    current_user: CurrentUser,
    from_date: Optional[date] = None,
    to_date: Optional[date] = None,
    medicine_id: Optional[uuid.UUID] = None,
    group_by: str = Query("month", regex="^(day|week|month|year)$")
) -> Any:
    """
    Generate medicine usage report.
    """
    if not current_user.is_doctor:
        raise HTTPException(status_code=403, detail="Only doctors can access reports")
    
    # Date range
    if not from_date:
        from_date = date.today() - timedelta(days=90)  # Last 90 days
    if not to_date:
        to_date = date.today()
    
    # Get usage logs
    statement = (
        select(MedicineUsageLog)
        .join(DoctorMedicineStock)
        .where(
            DoctorMedicineStock.doctor_id == current_user.id,
            MedicineUsageLog.used_date.between(from_date, to_date)
        )
    )
    
    if medicine_id:
        statement = statement.where(DoctorMedicineStock.medicine_id == medicine_id)
    
    # Aggregate usage via SQL to avoid loading entire table into memory
    # Map group_by to postgres date_trunc precision
    if group_by == "day":
        trunc = 'day'
    elif group_by == "week":
        trunc = 'week'
    elif group_by == "month":
        trunc = 'month'
    else:
        trunc = 'year'

    period_expr = func.date_trunc(trunc, MedicineUsageLog.used_date).label('period')

    stmt = (
        select(
            period_expr,
            MedicineMaster.name.label('medicine_name'),
            func.sum(MedicineUsageLog.quantity_used).label('quantity'),
            func.count(func.distinct(MedicineUsageLog.patient_id)).label('unique_patients')
        )
        .join(DoctorMedicineStock, DoctorMedicineStock.id == MedicineUsageLog.stock_item_id)
        .join(MedicineMaster, MedicineMaster.id == DoctorMedicineStock.medicine_id)
        .where(
            DoctorMedicineStock.doctor_id == current_user.id,
            MedicineUsageLog.used_date.between(from_date, to_date)
        )
        .group_by(period_expr, MedicineMaster.name)
        .order_by(period_expr)
    )

    results = session.exec(stmt).all()

    if not results:
        return {
            "message": "No usage data found for the selected period",
            "date_range": {"from": from_date.isoformat(), "to": to_date.isoformat()},
            "summary": {},
            "detailed_data": []
        }

    detailed = []
    total_usage = 0
    patient_set = set()
    medicine_set = set()
    trend_map: dict[str, float] = {}
    top_map: dict[str, float] = {}

    for row in results:
        period_val = row.period.date().isoformat() if hasattr(row.period, 'date') else str(row.period)
        medicine_name = row.medicine_name
        qty = float(row.quantity or 0)
        unique_patients = int(row.unique_patients or 0)

        detailed.append({
            'period': period_val,
            'medicine_name': medicine_name,
            'quantity': qty,
            'unique_patients': unique_patients
        })

        total_usage += qty
        medicine_set.add(medicine_name)
        # We don't have patient ids here; unique patient count per period is aggregated
        top_map[medicine_name] = top_map.get(medicine_name, 0) + qty
        trend_map[period_val] = trend_map.get(period_val, 0) + qty

    total_patients = sum(r.unique_patients for r in results)

    # Prepare top medicines and trend lists
    top_medicines = dict(sorted(top_map.items(), key=lambda x: x[1], reverse=True)[:10])
    trend_data = [{'period': k, 'quantity': v} for k, v in sorted(trend_map.items())]

    return {
        "date_range": {"from": from_date.isoformat(), "to": to_date.isoformat()},
        "group_by": group_by,
        "summary": {
            "total_usage": float(total_usage),
            "total_patients": int(total_patients),
            "total_medicines": int(len(medicine_set)),
            "average_daily_usage": float(total_usage / max((to_date - from_date).days, 1)),
            "top_medicines": top_medicines
        },
        "detailed_data": detailed,
        "trend_data": trend_data,
        "generated_at": utc_isoformat()
    }


@router.get("/appointment-statistics")
def get_appointment_statistics(
    session: SessionDep,
    current_user: CurrentUser,
    from_date: Optional[date] = None,
    to_date: Optional[date] = None,
    group_by: str = Query("month", regex="^(day|week|month|year)$")
) -> Any:
    """
    Generate appointment statistics report.
    """
    if not current_user.is_doctor:
        raise HTTPException(status_code=403, detail="Only doctors can access reports")
    
    # Date range
    if not from_date:
        from_date = date.today() - timedelta(days=90)
    if not to_date:
        to_date = date.today()
    
    # Get appointments
    # Use SQL aggregations to compute appointment statistics
    # Total appointments and total hours
    total_stmt = (
        select(
            func.count().label('total_appointments'),
            func.coalesce(func.sum(Appointment.duration_minutes), 0).label('total_minutes'),
            func.count(func.distinct(Appointment.patient_id)).label('unique_patients')
        )
        .where(
            Appointment.doctor_id == current_user.id,
            Appointment.appointment_date.between(from_date, to_date)
        )
    )

    totals = session.exec(total_stmt).one()
    total_appointments = int(totals.total_appointments or 0)
    total_hours = float((totals.total_minutes or 0)) / 60.0
    unique_patients = int(totals.unique_patients or 0)

    if total_appointments == 0:
        return {
            "message": "No appointment data found for the selected period",
            "date_range": {"from": from_date.isoformat(), "to": to_date.isoformat()},
            "summary": {},
            "detailed_data": []
        }

    # Status distribution
    status_stmt = (
        select(Appointment.status, func.count().label('count'))
        .where(
            Appointment.doctor_id == current_user.id,
            Appointment.appointment_date.between(from_date, to_date)
        )
        .group_by(Appointment.status)
    )
    status_distribution = {row.status: int(row.count) for row in session.exec(status_stmt).all()}

    # Consultation type distribution
    consult_stmt = (
        select(Appointment.consultation_type, func.count().label('count'))
        .where(
            Appointment.doctor_id == current_user.id,
            Appointment.appointment_date.between(from_date, to_date)
        )
        .group_by(Appointment.consultation_type)
    )
    consultation_distribution = {row.consultation_type: int(row.count) for row in session.exec(consult_stmt).all()}

    # Trend data: group by period
    if group_by == "day":
        trunc = 'day'
    elif group_by == "week":
        trunc = 'week'
    elif group_by == "month":
        trunc = 'month'
    else:
        trunc = 'year'

    period_expr = func.date_trunc(trunc, Appointment.appointment_date).label('period')
    trend_stmt = (
        select(
            period_expr,
            func.count().label('appointments'),
            func.count(func.distinct(Appointment.patient_id)).label('unique_patients'),
            func.coalesce(func.sum(Appointment.duration_minutes), 0).label('total_minutes')
        )
        .where(
            Appointment.doctor_id == current_user.id,
            Appointment.appointment_date.between(from_date, to_date)
        )
        .group_by(period_expr)
        .order_by(period_expr)
    )

    trend_rows = session.exec(trend_stmt).all()
    trend_data = []
    for r in trend_rows:
        period_val = r.period.date().isoformat() if hasattr(r.period, 'date') else str(r.period)
        trend_data.append({
            'period': period_val,
            'appointments': int(r.appointments),
            'unique_patients': int(r.unique_patients),
            'total_minutes': float(r.total_minutes)
        })

    # Weekday distribution (by appointment_date)
    weekday_stmt = (
        select(func.to_char(Appointment.appointment_date, 'Day').label('weekday'), func.count().label('count'))
        .where(
            Appointment.doctor_id == current_user.id,
            Appointment.appointment_date.between(from_date, to_date)
        )
        .group_by('weekday')
    )
    try:
        weekday_distribution = {row.weekday.strip(): int(row.count) for row in session.exec(weekday_stmt).all()}
    except Exception:
        # Fallback if DB doesn't support to_char/date formatting
        weekday_distribution = {}

    # Cancellation and no-show rates
    cancelled = status_distribution.get(AppointmentStatus.CANCELLED, 0)
    no_shows = status_distribution.get(AppointmentStatus.NO_SHOW, 0)
    cancellation_rate = (cancelled / total_appointments * 100) if total_appointments > 0 else 0
    no_show_rate = (no_shows / total_appointments * 100) if total_appointments > 0 else 0

    average_duration = None
    if total_appointments > 0:
        avg_stmt = (
            select(func.avg(Appointment.duration_minutes).label('avg_dur'))
            .where(
                Appointment.doctor_id == current_user.id,
                Appointment.appointment_date.between(from_date, to_date)
            )
        )
        avg_row = session.exec(avg_stmt).one()
        average_duration = float(avg_row.avg_dur) if avg_row and avg_row.avg_dur is not None else 0.0

    return {
        "date_range": {"from": from_date.isoformat(), "to": to_date.isoformat()},
        "group_by": group_by,
        "summary": {
            "total_appointments": total_appointments,
            "total_hours": round(total_hours, 2),
            "average_duration_minutes": round(average_duration or 0, 2),
            "unique_patients": unique_patients,
            "cancellation_rate": round(cancellation_rate, 2),
            "no_show_rate": round(no_show_rate, 2)
        },
        "distributions": {
            "status": status_distribution,
            "consultation_type": consultation_distribution,
            "weekday": weekday_distribution
        },
        "trend_data": trend_data,
        "generated_at": utc_isoformat()
    }


@router.get("/prescription-analysis")
def get_prescription_analysis(
    session: SessionDep,
    current_user: CurrentUser,
    from_date: Optional[date] = None,
    to_date: Optional[date] = None
) -> Any:
    """
    Analyze prescription patterns.
    """
    if not current_user.is_doctor:
        raise HTTPException(status_code=403, detail="Only doctors can access reports")
    
    # Date range
    if not from_date:
        from_date = date.today() - timedelta(days=180)
    if not to_date:
        to_date = date.today()
    
    # Use SQL aggregations to analyze prescriptions and prescribed medicines
    # Total prescriptions
    total_prescriptions_stmt = (
        select(func.count()).where(
            Prescription.doctor_id == current_user.id,
            Prescription.prescription_date.between(from_date, to_date)
        )
    )
    total_prescriptions = int(session.exec(total_prescriptions_stmt).one() or 0)

    # Join prescription medicines -> stock -> medicine master
    stmt = (
        select(
            Prescription.prescription_date.label('prescription_date'),
            Prescription.prescription_type.label('prescription_type'),
            MedicineMaster.name.label('medicine_name'),
            DoctorMedicineStock.potency.label('potency'),
            DoctorMedicineStock.form.label('form')
        )
        .join(PrescriptionMedicine, PrescriptionMedicine.prescription_id == Prescription.id)
        .join(DoctorMedicineStock, DoctorMedicineStock.id == PrescriptionMedicine.stock_used_id)
        .join(MedicineMaster, MedicineMaster.id == DoctorMedicineStock.medicine_id)
        .where(
            Prescription.doctor_id == current_user.id,
            Prescription.prescription_date.between(from_date, to_date)
        )
    )

    rows = session.exec(stmt).all()

    if not rows and total_prescriptions == 0:
        return {
            "message": "No prescription data found for the selected period",
            "date_range": {"from": from_date.isoformat(), "to": to_date.isoformat()},
            "summary": {}
        }

    # Aggregations
    top_medicines_map: dict[str, int] = {}
    potency_map: dict[str, int] = {}
    form_map: dict[str, int] = {}
    monthly_map: dict[str, int] = {}
    total_medicines_prescribed = 0

    for r in rows:
        med = r.medicine_name
        pot = r.potency
        form = r.form
        total_medicines_prescribed += 1

        top_medicines_map[med] = top_medicines_map.get(med, 0) + 1
        potency_map[pot] = potency_map.get(pot, 0) + 1
        form_map[form] = form_map.get(form, 0) + 1

        # monthly trend
        month_key = r.prescription_date.strftime('%Y-%m') if hasattr(r.prescription_date, 'strftime') else str(r.prescription_date)
        monthly_map[month_key] = monthly_map.get(month_key, 0) + 1

    medicines_per_prescription = (total_medicines_prescribed / total_prescriptions) if total_prescriptions > 0 else 0

    return {
        "date_range": {"from": from_date.isoformat(), "to": to_date.isoformat()},
        "summary": {
            "total_prescriptions": total_prescriptions,
            "total_medicines_prescribed": total_medicines_prescribed,
            "average_medicines_per_prescription": round(medicines_per_prescription, 2),
            "most_common_prescription_type": None  # could be added with another aggregate if needed
        },
        "distributions": {
            "prescription_type": {},
            "top_medicines": dict(sorted(top_medicines_map.items(), key=lambda x: x[1], reverse=True)[:10]),
            "potency": potency_map,
            "form": form_map
        },
        "trends": {
            "monthly": [{"month": k, "count": v} for k, v in sorted(monthly_map.items())]
        },
        "generated_at": utc_isoformat()
    }


@router.get("/financial-summary")
def get_financial_summary(
    session: SessionDep,
    current_user: CurrentUser,
    from_date: Optional[date] = None,
    to_date: Optional[date] = None
) -> Any:
    """
    Generate financial summary (consultation fees, medicine costs, etc.).
    Note: This requires additional fee/cost fields in your models.
    """
    if not current_user.is_doctor:
        raise HTTPException(status_code=403, detail="Only doctors can access reports")
    
    # Date range
    if not from_date:
        from_date = date.today().replace(day=1)  # Current month
    if not to_date:
        to_date = date.today()
    
    # Get appointments (consultation fees)
    appointments = session.exec(
        select(Appointment)
        .where(
            Appointment.doctor_id == current_user.id,
            Appointment.appointment_date.between(from_date, to_date),
            Appointment.status == AppointmentStatus.COMPLETED
        )
    ).all()
    
    # Get medicine usage (medicine costs)
    # Note: You would need to add cost fields to your models for accurate calculation
    
    # Calculate consultation revenue
    # Assuming each consultation has a fee (you need to add this field)
    consultation_revenue = len(appointments) * 500  # Example: ₹500 per consultation
    
    # Calculate medicine costs
    # This would require cost tracking in your stock system
    
    # Calculate profit/loss
    total_revenue = consultation_revenue
    total_costs = 0  # Calculate from medicine costs
    
    return {
        "date_range": {
            "from": from_date.isoformat(),
            "to": to_date.isoformat()
        },
        "revenue": {
            "consultation_fees": consultation_revenue,
            "total_revenue": total_revenue
        },
        "costs": {
            "medicine_costs": total_costs,
            "total_costs": total_costs
        },
        "profitability": {
            "gross_profit": total_revenue - total_costs,
            "profit_margin": ((total_revenue - total_costs) / total_revenue * 100) if total_revenue > 0 else 0
        },
        "key_metrics": {
            "completed_appointments": len(appointments),
            "average_daily_revenue": total_revenue / max((to_date - from_date).days, 1)
        },
        "generated_at": utc_isoformat()
    }


@router.get("/expiry-alerts")
def get_expiry_alerts_report(
    session: SessionDep,
    current_user: CurrentUser,
    days_threshold: int = 30
) -> Any:
    """
    Get detailed expiry alerts for medicines.
    """
    if not current_user.is_doctor:
        raise HTTPException(status_code=403, detail="Only doctors can access reports")
    
    today = date.today()
    expiry_date = today + timedelta(days=days_threshold)
    
    # Get expiring medicines
    expiring_medicines = session.exec(
        select(DoctorMedicineStock)
        .where(
            DoctorMedicineStock.doctor_id == current_user.id,
            DoctorMedicineStock.is_active == True,
            DoctorMedicineStock.expiry_date != None,
            DoctorMedicineStock.expiry_date <= expiry_date,
            DoctorMedicineStock.expiry_date >= today
        )
        .order_by(DoctorMedicineStock.expiry_date.asc())
    ).all()
    
    # Categorize by urgency
    expiring_soon = []  # 1-7 days
    expiring_later = []  # 8-30 days
    
    for stock in expiring_medicines:
        days_until_expiry = (stock.expiry_date - today).days
        
        stock_info = {
            "stock_item": stock,
            "days_until_expiry": days_until_expiry,
            "urgency": "high" if days_until_expiry <= 7 else "medium"
        }
        
        if days_until_expiry <= 7:
            expiring_soon.append(stock_info)
        else:
            expiring_later.append(stock_info)
    
    # Get already expired medicines
    expired_medicines = session.exec(
        select(DoctorMedicineStock)
        .where(
            DoctorMedicineStock.doctor_id == current_user.id,
            DoctorMedicineStock.expiry_date != None,
            DoctorMedicineStock.expiry_date < today
        )
        .order_by(DoctorMedicineStock.expiry_date.asc())
    ).all()
    
    # Calculate total value at risk (requires cost field)
    total_items = len(expiring_medicines) + len(expired_medicines)
    
    return {
        "check_date": today.isoformat(),
        "threshold_days": days_threshold,
        "summary": {
            "expiring_soon_count": len(expiring_soon),
            "expiring_later_count": len(expiring_later),
            "expired_count": len(expired_medicines),
            "total_items_at_risk": total_items
        },
        "alerts": {
            "expiring_soon": expiring_soon,
            "expiring_later": expiring_later,
            "expired": expired_medicines
        },
        "recommendations": [
            "Consider using expiring medicines first in prescriptions",
            "Review and update stock ordering schedule",
            "Check for alternative medicines if needed",
            "Consider discounting or special promotions for near-expiry stock"
        ],
        "generated_at": utc_isoformat()
    }