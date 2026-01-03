# models/report_models.py
from datetime import date, datetime
from typing import List, Dict, Any, Optional
from sqlmodel import SQLModel
from pydantic import BaseModel


# ========== RESPONSE MODELS (API Output) ==========
class DateRange(SQLModel):
    """API OUTPUT MODEL for date ranges"""
    from_date: date
    to_date: date


class PatientHistoryResponse(SQLModel):
    """API OUTPUT MODEL for patient history report"""
    patient: Dict[str, Any]
    date_range: DateRange
    summary: Dict[str, Any]
    timeline: Dict[str, List[Dict[str, Any]]]
    generated_at: datetime


class MedicineUsageResponse(SQLModel):
    """API OUTPUT MODEL for medicine usage report"""
    date_range: DateRange
    group_by: str
    summary: Dict[str, Any]
    detailed_data: List[Dict[str, Any]]
    trend_data: List[Dict[str, Any]]
    generated_at: datetime


class AppointmentStatisticsResponse(SQLModel):
    """API OUTPUT MODEL for appointment statistics"""
    date_range: DateRange
    group_by: str
    summary: Dict[str, Any]
    distributions: Dict[str, Dict[str, Any]]
    trend_data: List[Dict[str, Any]]
    generated_at: datetime


class PrescriptionAnalysisResponse(SQLModel):
    """API OUTPUT MODEL for prescription analysis"""
    date_range: DateRange
    summary: Dict[str, Any]
    distributions: Dict[str, Dict[str, Any]]
    trends: Dict[str, List[Dict[str, Any]]]
    generated_at: datetime


class FinancialSummaryResponse(SQLModel):
    """API OUTPUT MODEL for financial summary"""
    date_range: DateRange
    revenue: Dict[str, float]
    costs: Dict[str, float]
    profitability: Dict[str, float]
    key_metrics: Dict[str, Any]
    generated_at: datetime


class ExpiryAlertsResponse(SQLModel):
    """API OUTPUT MODEL for expiry alerts"""
    check_date: str
    threshold_days: int
    summary: Dict[str, int]
    alerts: Dict[str, List[Dict[str, Any]]]
    recommendations: List[str]
    generated_at: datetime