"""
Shared query helpers for reporting.

These functions encapsulate joins and filters across multiple apps so that
JSON analytics endpoints and file exports can reuse the same logic.
"""
from datetime import datetime
from typing import Optional, Dict, Any, Literal, List

from django.db.models import QuerySet, Sum, Avg, Count
from django.db.models.functions import TruncDay, TruncWeek, TruncMonth

from admissions.models import Enrollment
from assessment.models import Grade
from payments.models import Payment, PaymentStatus, Invoice, InvoiceStatus
from attendance.models import AttendanceRecord


def _parse_date(value: Optional[str]) -> Optional[datetime]:
    if not value:
        return None
    # Expect ISO 8601 or simple YYYY-MM-DD (Django will usually send this)
    try:
        # First try full datetime
        return datetime.fromisoformat(value)
    except ValueError:
        try:
            return datetime.strptime(value, "%Y-%m-%d")
        except ValueError:
            return None


def build_common_filters(params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Build a dict of ORM filters based on common query parameters.

    Supported keys in `params`:
      - date_from, date_to
      - program_id, cohort_id, student_id, lecturer_id
      - payment_status
    """
    filters: Dict[str, Any] = {}

    date_from = _parse_date(params.get("date_from"))
    date_to = _parse_date(params.get("date_to"))
    if date_from:
        filters["created_at__gte"] = date_from
    if date_to:
        filters["created_at__lte"] = date_to

    if program_id := params.get("program_id"):
        filters["cohort__course__program_id"] = program_id
    if cohort_id := params.get("cohort_id"):
        filters["cohort_id"] = cohort_id
    if student_id := params.get("student_id"):
        filters["student_id"] = student_id

    # Lecturer can be attached via cohort or assessment depending on the model
    if lecturer_id := params.get("lecturer_id"):
        filters["cohort__lecturer_id"] = lecturer_id

    return filters


def get_student_financial_queryset(params: Dict[str, Any]) -> QuerySet:
    """
    Return a queryset of enrollments annotated with financial aggregates.

    Each row represents a student enrollment with:
      - basic enrollment / cohort / program info
      - aggregated payments (total_paid)
    """
    filters = build_common_filters(params)

    qs = (
        Enrollment.objects.select_related("student", "cohort", "cohort__course", "cohort__course__program")
        .filter(**filters)
    )

    # Join payments by student (and optionally cohort/program if modeled that way)
    qs = qs.annotate(
        total_paid=Sum("student__payments__amount"),
    )

    return qs


def get_grades_queryset(params: Dict[str, Any]) -> QuerySet:
    """
    Return a queryset of grades with common filters applied.
    """
    filters = {}
    date_from = _parse_date(params.get("date_from"))
    date_to = _parse_date(params.get("date_to"))
    if date_from:
        filters["graded_at__gte"] = date_from
    if date_to:
        filters["graded_at__lte"] = date_to

    if cohort_id := params.get("cohort_id"):
        filters["assessment__cohort_id"] = cohort_id
    if student_id := params.get("student_id"):
        filters["student_id"] = student_id

    return Grade.objects.select_related("student", "assessment").filter(**filters)


GroupBy = Literal["day", "week", "month"]


def get_timeseries_analytics(params: Dict[str, Any], group_by: GroupBy):
    """
    Return time-series data for enrollments and payments.

    Output structure is a list of dicts with:
      - period: date (start of day/week/month)
      - enrollments: count
      - total_paid: sum of completed payments
    """
    # Map group_by to appropriate trunc function and result key name
    if group_by == "week":
        trunc = TruncWeek
    elif group_by == "month":
        trunc = TruncMonth
    else:
        trunc = TruncDay

    date_from = _parse_date(params.get("date_from"))
    date_to = _parse_date(params.get("date_to"))

    # Enrollments timeseries (use enrolled_at)
    enrollments = Enrollment.objects.all()
    if date_from:
        enrollments = enrollments.filter(enrolled_at__gte=date_from)
    if date_to:
        enrollments = enrollments.filter(enrolled_at__lte=date_to)

    enrollments = (
        enrollments.annotate(period=trunc("enrolled_at"))
        .values("period")
        .order_by("period")
        .annotate(enrollments_count=Sum(1))
    )

    # Payments timeseries (completed payments only)
    payments = Payment.objects.filter(status=PaymentStatus.COMPLETED)
    if date_from:
        payments = payments.filter(payment_date__gte=date_from)
    if date_to:
        payments = payments.filter(payment_date__lte=date_to)

    payments = (
        payments.annotate(period=trunc("payment_date"))
        .values("period")
        .order_by("period")
        .annotate(total_paid=Sum("amount"))
    )

    # Merge the two series on period
    result: Dict[datetime, Dict[str, Any]] = {}

    for row in enrollments:
        period = row["period"]
        bucket = result.setdefault(
            period,
            {"period": period, "enrollments": 0, "total_paid": 0.0},
        )
        bucket["enrollments"] = int(row["enrollments_count"] or 0)

    for row in payments:
        period = row["period"]
        bucket = result.setdefault(
            period,
            {"period": period, "enrollments": 0, "total_paid": 0.0},
        )
        bucket["total_paid"] = float(row["total_paid"] or 0)

    # Sort by period and return as list
    series: List[Dict[str, Any]] = [
        {
            "period": key,
            "enrollments": value["enrollments"],
            "total_paid": value["total_paid"],
        }
        for key, value in sorted(result.items(), key=lambda item: item[0])
    ]

    return series


def get_financial_analytics(params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Aggregate financial metrics using invoices and payments.

    Returns global totals and breakdowns by program, cohort, and invoice status.
    """
    date_from = _parse_date(params.get("date_from"))
    date_to = _parse_date(params.get("date_to"))

    invoices = Invoice.objects.select_related(
        "enrollment", "enrollment__cohort", "enrollment__cohort__course", "enrollment__cohort__course__program"
    )
    payments = Payment.objects.filter(status=PaymentStatus.COMPLETED)

    if date_from:
        invoices = invoices.filter(created_at__gte=date_from)
        payments = payments.filter(payment_date__gte=date_from)
    if date_to:
        invoices = invoices.filter(created_at__lte=date_to)
        payments = payments.filter(payment_date__lte=date_to)

    total_invoiced = invoices.aggregate(total=Sum("total_amount"))["total"] or 0
    total_paid = payments.aggregate(total=Sum("amount"))["total"] or 0

    # Outstanding is based on invoices' outstanding_amount
    outstanding = 0
    for inv in invoices:
        outstanding += float(inv.outstanding_amount)

    # Breakdown by program
    by_program: Dict[str, Dict[str, float]] = {}
    for inv in invoices:
        program = getattr(getattr(getattr(inv.enrollment.cohort, "course", None), "program", None), "name", "Unknown")
        bucket = by_program.setdefault(program, {"total_invoiced": 0.0, "total_paid": 0.0})
        bucket["total_invoiced"] += float(inv.total_amount)
        bucket["total_paid"] += float(inv.paid_amount)

    # Breakdown by cohort
    by_cohort: Dict[str, Dict[str, float]] = {}
    for inv in invoices:
        cohort_name = getattr(inv.enrollment.cohort, "name", "Unknown")
        bucket = by_cohort.setdefault(cohort_name, {"total_invoiced": 0.0, "total_paid": 0.0})
        bucket["total_invoiced"] += float(inv.total_amount)
        bucket["total_paid"] += float(inv.paid_amount)

    # Breakdown by invoice status
    by_status: Dict[str, Dict[str, float]] = {}
    for inv in invoices:
        status = inv.status
        bucket = by_status.setdefault(status, {"count": 0, "total_amount": 0.0})
        bucket["count"] += 1
        bucket["total_amount"] += float(inv.total_amount)

    return {
        "total_invoiced": float(total_invoiced),
        "total_paid": float(total_paid),
        "total_outstanding": float(outstanding),
        "by_program": by_program,
        "by_cohort": by_cohort,
        "by_status": by_status,
    }


def get_cohort_performance(params: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Aggregate academic and financial performance by cohort.
    """
    date_from = _parse_date(params.get("date_from"))
    date_to = _parse_date(params.get("date_to"))

    enrollments = Enrollment.objects.select_related("cohort")
    if date_from:
        enrollments = enrollments.filter(enrolled_at__gte=date_from)
    if date_to:
        enrollments = enrollments.filter(enrolled_at__lte=date_to)

    # Students per cohort
    cohort_counts = (
        enrollments.values("cohort_id", "cohort__name")
        .annotate(student_count=Count("id"))
        .order_by("cohort__name")
    )

    # Attendance and grades are aggregated separately
    attendance = AttendanceRecord.objects.select_related("session", "session__cohort")
    if date_from:
        attendance = attendance.filter(marked_at__gte=date_from)
    if date_to:
        attendance = attendance.filter(marked_at__lte=date_to)

    attendance_stats = (
        attendance.values("session__cohort_id", "session__cohort__name")
        .annotate(total=Count("id"), present=Count("id", filter=AttendanceRecord.objects.filter(status="PRESENT")))
    )

    grades = Grade.objects.select_related("assessment", "assessment__cohort")
    if date_from:
        grades = grades.filter(graded_at__gte=date_from)
    if date_to:
        grades = grades.filter(graded_at__lte=date_to)

    grade_stats = (
        grades.values("assessment__cohort_id", "assessment__cohort__name")
        .annotate(avg_percentage=Avg("percentage"))
    )

    # Financial per cohort via invoices
    invoices = Invoice.objects.select_related("enrollment", "enrollment__cohort")
    if date_from:
        invoices = invoices.filter(created_at__gte=date_from)
    if date_to:
        invoices = invoices.filter(created_at__lte=date_to)

    financial_stats = (
        invoices.values("enrollment__cohort_id", "enrollment__cohort__name")
        .annotate(
            total_invoiced=Sum("total_amount"),
            total_paid=Sum("paid_amount"),
        )
    )

    # Merge all pieces by cohort
    result: Dict[str, Dict[str, Any]] = {}

    for row in cohort_counts:
        cid = str(row["cohort_id"])
        result[cid] = {
            "cohort_id": cid,
            "cohort_name": row["cohort__name"],
            "student_count": row["student_count"],
            "attendance_rate": None,
            "avg_grade": None,
            "total_invoiced": 0.0,
            "total_paid": 0.0,
        }

    for row in attendance_stats:
        # We only stored 'PRESENT' in filter, fallback if not present
        cid = str(row["session__cohort_id"])
        bucket = result.setdefault(
            cid,
            {
                "cohort_id": cid,
                "cohort_name": row["session__cohort__name"],
                "student_count": 0,
                "attendance_rate": None,
                "avg_grade": None,
                "total_invoiced": 0.0,
                "total_paid": 0.0,
            },
        )
        total = row["total"] or 0
        present = row.get("present") or 0
        bucket["attendance_rate"] = float(present) / total if total else None

    for row in grade_stats:
        cid = str(row["assessment__cohort_id"])
        bucket = result.setdefault(
            cid,
            {
                "cohort_id": cid,
                "cohort_name": row["assessment__cohort__name"],
                "student_count": 0,
                "attendance_rate": None,
                "avg_grade": None,
                "total_invoiced": 0.0,
                "total_paid": 0.0,
            },
        )
        bucket["avg_grade"] = float(row["avg_percentage"] or 0)

    for row in financial_stats:
        cid = str(row["enrollment__cohort_id"])
        bucket = result.setdefault(
            cid,
            {
                "cohort_id": cid,
                "cohort_name": row["enrollment__cohort__name"],
                "student_count": 0,
                "attendance_rate": None,
                "avg_grade": None,
                "total_invoiced": 0.0,
                "total_paid": 0.0,
            },
        )
        bucket["total_invoiced"] = float(row["total_invoiced"] or 0)
        bucket["total_paid"] = float(row["total_paid"] or 0)

    return list(result.values())
