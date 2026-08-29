"""
Core Business Services for School Fees Management.

Includes:
  - FrequencyEngine: Calculates installment dates, periods, and penny-accurate payment schedules.
  - FeeService: High-level transactional operations for fee structures, assignments, payments,
                partial payments, adjustments, and receipts.
"""
from datetime import date, timedelta
from decimal import Decimal, ROUND_DOWN
from typing import List, Dict, Any, Optional, Tuple

from django.db import transaction, models
from django.utils import timezone
from django.core.exceptions import ValidationError

from apps.fees.models import (
    FeeCategory,
    FeeStructure,
    StudentFee,
    FeeInstallment,
    FeePayment,
    FeeAuditLog,
)
from apps.academics.models import AcademicYear, Standard, Division
from apps.students.models import Student
from apps.notifications.models import InAppNotification


class FrequencyEngine:
    """
    Calculates installment schedules with exact dates and penny-accurate decimal distribution.
    Supports MONTHLY (12), QUARTERLY (4), HALF_YEARLY (2), and FULL_YEAR (1).
    """

    @staticmethod
    def _clamp_day_for_month(year: int, month: int, day: int) -> date:
        """Returns a valid date for given year, month, and day (clamping to last day of month if necessary)."""
        import calendar
        _, last_day = calendar.monthrange(year, month)
        clamped_day = min(day, last_day)
        return date(year, month, clamped_day)

    @classmethod
    def generate_schedule_periods(
        cls,
        academic_year: AcademicYear,
        payment_frequency: str,
        total_amount: Decimal,
        due_day: int = 10,
    ) -> List[Dict[str, Any]]:
        """
        Generates list of installment period specifications:
        [
            {
                'period_number': 1,
                'period_name': 'April 2026',
                'due_date': date(2026, 4, 10),
                'amount_due': Decimal('5000.00'),
            }, ...
        ]
        """
        start_date = academic_year.start_date
        end_date = academic_year.end_date

        start_year = start_date.year
        start_month = start_date.month

        # Determine number of installments and labels
        periods_meta = []
        if payment_frequency == FeeStructure.Frequency.MONTHLY:
            num_installments = 12
            month_cursor = start_month
            year_cursor = start_year
            for i in range(1, 13):
                due_d = cls._clamp_day_for_month(year_cursor, month_cursor, due_day)
                month_name = date(year_cursor, month_cursor, 1).strftime("%B %Y")
                periods_meta.append({
                    'period_number': i,
                    'period_name': month_name,
                    'due_date': due_d,
                })
                month_cursor += 1
                if month_cursor > 12:
                    month_cursor = 1
                    year_cursor += 1

        elif payment_frequency == FeeStructure.Frequency.QUARTERLY:
            num_installments = 4
            quarters = [
                ("Q1 (Apr - Jun)", 4, start_year),
                ("Q2 (Jul - Sep)", 7, start_year),
                ("Q3 (Oct - Dec)", 10, start_year),
                ("Q4 (Jan - Mar)", 1, start_year + 1 if start_month >= 4 else start_year),
            ]
            for i, (q_name, q_month, q_year) in enumerate(quarters, start=1):
                due_d = cls._clamp_day_for_month(q_year, q_month, due_day)
                periods_meta.append({
                    'period_number': i,
                    'period_name': q_name,
                    'due_date': due_d,
                })

        elif payment_frequency == FeeStructure.Frequency.HALF_YEARLY:
            num_installments = 2
            terms = [
                ("Term 1 (First Half)", start_month, start_year),
                ("Term 2 (Second Half)", (start_month + 6 - 1) % 12 + 1, start_year if start_month <= 6 else start_year + 1),
            ]
            for i, (t_name, t_month, t_year) in enumerate(terms, start=1):
                due_d = cls._clamp_day_for_month(t_year, t_month, due_day)
                periods_meta.append({
                    'period_number': i,
                    'period_name': t_name,
                    'due_date': due_d,
                })

        elif payment_frequency == FeeStructure.Frequency.FULL_YEAR:
            num_installments = 1
            due_d = cls._clamp_day_for_month(start_year, start_month, due_day)
            periods_meta.append({
                'period_number': 1,
                'period_name': f"Full Session ({academic_year.name})",
                'due_date': due_d,
            })
        else:
            raise ValidationError(f"Unsupported payment frequency: {payment_frequency}")

        # Distribute amounts with penny-exact rounding (no fractions lost)
        total_dec = Decimal(str(total_amount))
        base_inst_amount = (total_dec / Decimal(str(num_installments))).quantize(Decimal('0.01'), rounding=ROUND_DOWN)
        allocated_so_far = base_inst_amount * Decimal(str(num_installments))
        remainder = total_dec - allocated_so_far

        results = []
        for i, meta in enumerate(periods_meta):
            amt = base_inst_amount
            # Add remainder cents to the final installment
            if i == len(periods_meta) - 1:
                amt += remainder
            results.append({
                'period_number': meta['period_number'],
                'period_name': meta['period_name'],
                'due_date': meta['due_date'],
                'amount_due': amt,
            })

        return results


class FeeService:
    """
    High-level business operations for managing fee structures, student fee assignments,
    payment collections, partial allocations, receipts, and audit trails.
    """

    @classmethod
    def ensure_default_categories(cls, school) -> List[FeeCategory]:
        """
        Auto-provisions standard fee categories (Tuition, Transport, Activity, Exam, Library, Laboratory)
        for a school if none exist yet.
        """
        defaults = [
            ("Tuition Fee", "TUITION", "Core academic instruction and curriculum fee"),
            ("Transport Fee", "TRANSPORT", "Daily school bus and transit commute fee"),
            ("Activity Fee", "ACTIVITY", "Sports, cultural, and extracurricular activity fee"),
            ("Exam Fee", "EXAM", "Term examinations and assessment fee"),
            ("Library Fee", "LIBRARY", "Library access and books maintenance fee"),
            ("Laboratory Fee", "LAB", "Science, Computer, and Language laboratory fee"),
        ]
        created_cats = []
        for name, code, desc in defaults:
            cat, _ = FeeCategory.objects.get_or_create(
                school=school,
                name=name,
                defaults={
                    'code': code,
                    'description': desc,
                    'is_active': True,
                }
            )
            created_cats.append(cat)
        return created_cats

    @classmethod
    def generate_next_receipt_number(cls, school) -> str:
        """
        Generates a unique sequential receipt number for the school:
        Format: RCPT-{SUBDOMAIN}-{YEAR}-{SEQUENCE:05d}
        """
        current_year = timezone.localdate().year
        prefix = f"REC-{school.subdomain.upper()}-{current_year}-"
        
        last_payment = FeePayment.objects.filter(
            school=school,
            receipt_number__startswith=prefix,
        ).order_by('-id').first()

        if last_payment and last_payment.receipt_number:
            try:
                last_seq = int(last_payment.receipt_number.split('-')[-1])
                next_seq = last_seq + 1
            except (ValueError, IndexError):
                next_seq = 1
        else:
            next_seq = 1

        return f"{prefix}{next_seq:05d}"

    @classmethod
    @transaction.atomic
    def assign_fee_to_student(
        cls,
        student: Student,
        fee_structure: FeeStructure,
        custom_amount: Optional[Decimal] = None,
        discount_amount: Decimal = Decimal('0.00'),
        discount_reason: str = '',
        waived_amount: Decimal = Decimal('0.00'),
        waiver_reason: str = '',
        performed_by=None,
        ip_address: Optional[str] = None,
    ) -> StudentFee:
        """
        Assigns a FeeStructure to an individual student and generates all installment records.
        """
        school = student.school
        academic_year = fee_structure.academic_year

        student_fee, created = StudentFee.objects.get_or_create(
            school=school,
            student=student,
            fee_structure=fee_structure,
            defaults={
                'academic_year': academic_year,
                'custom_amount': custom_amount,
                'discount_amount': discount_amount,
                'discount_reason': discount_reason,
                'waived_amount': waived_amount,
                'waiver_reason': waiver_reason,
            }
        )

        if not created:
            student_fee.custom_amount = custom_amount
            student_fee.discount_amount = discount_amount
            student_fee.discount_reason = discount_reason
            student_fee.waived_amount = waived_amount
            student_fee.waiver_reason = waiver_reason
            student_fee.is_active = True
            student_fee.save()
            # Remove existing unpaid installments to regenerate schedule
            student_fee.installments.filter(amount_paid=Decimal('0.00')).delete()

        # Calculate installments schedule based on net payable amount
        net_amount = student_fee.net_payable_amount
        schedule_periods = FrequencyEngine.generate_schedule_periods(
            academic_year=academic_year,
            payment_frequency=fee_structure.payment_frequency,
            total_amount=net_amount,
            due_day=fee_structure.due_day,
        )

        installments_to_create = []
        today = timezone.localdate()
        for p in schedule_periods:
            due_d = p['due_date']
            status = FeeInstallment.Status.OVERDUE if due_d < today else FeeInstallment.Status.UNPAID
            installments_to_create.append(
                FeeInstallment(
                    school=school,
                    student_fee=student_fee,
                    student=student,
                    academic_year=academic_year,
                    period_number=p['period_number'],
                    period_name=p['period_name'],
                    due_date=due_d,
                    amount_due=p['amount_due'],
                    amount_paid=Decimal('0.00'),
                    status=status,
                )
            )

        FeeInstallment.objects.bulk_create(installments_to_create)

        # Record audit log
        FeeAuditLog.objects.create(
            school=school,
            action=FeeAuditLog.Action.FEE_ASSIGNED,
            student=student,
            performed_by=performed_by,
            ip_address=ip_address,
            details={
                'fee_structure_id': fee_structure.id,
                'fee_structure_name': fee_structure.name,
                'amount': str(student_fee.net_payable_amount),
                'frequency': fee_structure.payment_frequency,
                'installments_count': len(installments_to_create),
            }
        )

        return student_fee

    @classmethod
    @transaction.atomic
    def assign_fee_to_class(
        cls,
        school,
        academic_year: AcademicYear,
        fee_structure: FeeStructure,
        standard: Optional[Standard] = None,
        division: Optional[Division] = None,
        performed_by=None,
        ip_address: Optional[str] = None,
    ) -> int:
        """
        Assigns a fee structure to all enrolled active students in a standard/division.
        Returns count of assigned students.
        """
        students_qs = Student.objects.filter(
            school=school,
            academic_year=academic_year,
            is_active=True,
        )
        if standard:
            students_qs = students_qs.filter(standard=standard)
        if division:
            students_qs = students_qs.filter(division=division)

        assigned_count = 0
        for student in students_qs:
            cls.assign_fee_to_student(
                student=student,
                fee_structure=fee_structure,
                performed_by=performed_by,
                ip_address=ip_address,
            )
            assigned_count += 1

        return assigned_count

    @classmethod
    @transaction.atomic
    def record_payment(
        cls,
        school,
        student: Student,
        amount: Decimal,
        payment_method: str,
        recorded_by,
        installment: Optional[FeeInstallment] = None,
        transaction_reference: str = '',
        remarks: str = '',
        payment_date: Optional[date] = None,
        ip_address: Optional[str] = None,
    ) -> Tuple[FeePayment, List[FeeInstallment]]:
        """
        Records a fee payment transaction, automatically allocates funds across unpaid/partial
        installments, updates installment statuses, and issues an atomic sequential receipt.
        """
        if amount <= Decimal('0.00'):
            raise ValidationError("Payment amount must be greater than zero.")

        if payment_date is None:
            payment_date = timezone.localdate()

        receipt_number = cls.generate_next_receipt_number(school)

        # Determine target installments for allocation
        if installment is not None:
            # Targeted installment allocation
            target_installments = [installment]
        else:
            # Chronological allocation across all active unpaid/partial installments for this student
            target_installments = list(
                FeeInstallment.objects.filter(
                    school=school,
                    student=student,
                ).exclude(
                    status=FeeInstallment.Status.PAID
                ).order_by('due_date', 'period_number')
            )

        if not target_installments:
            raise ValidationError("No outstanding fee installments found for this student.")

        remaining_to_allocate = Decimal(str(amount))
        affected_installments = []

        for inst in target_installments:
            if remaining_to_allocate <= Decimal('0.00'):
                break

            inst_balance = inst.remaining_amount
            if inst_balance <= Decimal('0.00'):
                continue

            alloc_amount = min(remaining_to_allocate, inst_balance)
            inst.amount_paid += alloc_amount
            inst.update_status(commit=True)
            affected_installments.append(inst)

            remaining_to_allocate -= alloc_amount

        # Create the Payment Ledger Record
        payment = FeePayment.objects.create(
            school=school,
            student=student,
            academic_year=student.academic_year,
            installment=installment if installment else (affected_installments[0] if affected_installments else None),
            amount=amount,
            payment_date=payment_date,
            payment_method=payment_method,
            transaction_reference=transaction_reference,
            receipt_number=receipt_number,
            recorded_by=recorded_by,
            remarks=remarks,
            status=FeePayment.Status.SUCCESS,
        )

        # Create Financial Audit Log
        FeeAuditLog.objects.create(
            school=school,
            action=FeeAuditLog.Action.PAYMENT_RECORDED,
            student=student,
            performed_by=recorded_by,
            ip_address=ip_address,
            details={
                'payment_id': payment.id,
                'receipt_number': receipt_number,
                'amount': str(amount),
                'payment_method': payment_method,
                'transaction_reference': transaction_reference,
                'affected_installments': [
                    {'id': i.id, 'period': i.period_name, 'paid': str(i.amount_paid), 'status': i.status}
                    for i in affected_installments
                ]
            }
        )

        # Dispatch In-App Notification if user is linked to student
        if student.user:
            try:
                InAppNotification.objects.create(
                    school=school,
                    user=student.user,
                    title="Fee Payment Received",
                    message=f"Payment of ₹{amount} has been successfully recorded. Receipt #{receipt_number} is now available in your portal.",
                )
            except Exception:
                pass  # Notifications shouldn't break payment flow

        return payment, affected_installments

    @classmethod
    @transaction.atomic
    def void_payment(
        cls,
        payment: FeePayment,
        voided_by,
        reason: str,
        ip_address: Optional[str] = None,
    ) -> FeePayment:
        """
        Reverses a recorded payment, reduces installment paid balances, and updates audit records.
        """
        if payment.status == FeePayment.Status.VOIDED:
            raise ValidationError("This payment has already been voided.")

        if not reason.strip():
            raise ValidationError("A reason is required to void a payment.")

        school = payment.school
        student = payment.student
        amount_to_reverse = payment.amount

        # Revert paid amount from student's most recently paid installments
        installments = list(
            FeeInstallment.objects.filter(
                school=school,
                student=student,
                amount_paid__gt=Decimal('0.00'),
            ).order_by('-due_date', '-period_number')
        )

        rem = amount_to_reverse
        for inst in installments:
            if rem <= Decimal('0.00'):
                break
            deduct = min(rem, inst.amount_paid)
            inst.amount_paid -= deduct
            inst.update_status(commit=True)
            rem -= deduct

        payment.status = FeePayment.Status.VOIDED
        payment.void_reason = reason
        payment.voided_by = voided_by
        payment.voided_at = timezone.now()
        payment.save(update_fields=['status', 'void_reason', 'voided_by', 'voided_at', 'updated_at'])

        # Audit log
        FeeAuditLog.objects.create(
            school=school,
            action=FeeAuditLog.Action.PAYMENT_VOIDED,
            student=student,
            performed_by=voided_by,
            ip_address=ip_address,
            details={
                'payment_id': payment.id,
                'receipt_number': payment.receipt_number,
                'amount_reversed': str(amount_to_reverse),
                'reason': reason,
            }
        )

        return payment

    @classmethod
    @transaction.atomic
    def apply_adjustment(
        cls,
        student_fee: StudentFee,
        discount_amount: Optional[Decimal] = None,
        discount_reason: Optional[str] = None,
        waived_amount: Optional[Decimal] = None,
        waiver_reason: Optional[str] = None,
        performed_by=None,
        ip_address: Optional[str] = None,
    ) -> StudentFee:
        """
        Applies a discount or waiver adjustment to a student fee and recalculates remaining schedule.
        """
        old_discount = student_fee.discount_amount
        old_waived = student_fee.waived_amount

        if discount_amount is not None:
            student_fee.discount_amount = discount_amount
        if discount_reason is not None:
            student_fee.discount_reason = discount_reason
        if waived_amount is not None:
            student_fee.waived_amount = waived_amount
        if waiver_reason is not None:
            student_fee.waiver_reason = waiver_reason

        student_fee.save()

        # Recalculate unpaid installments based on new net payable
        net_total = student_fee.net_payable_amount
        total_already_paid = student_fee.total_paid
        remaining_to_schedule = max(Decimal('0.00'), net_total - total_already_paid)

        unpaid_installments = list(student_fee.installments.filter(amount_paid=Decimal('0.00')).order_by('period_number'))
        if unpaid_installments:
            n_unpaid = len(unpaid_installments)
            base_amt = (remaining_to_schedule / Decimal(str(n_unpaid))).quantize(Decimal('0.01'), rounding=ROUND_DOWN)
            rem = remaining_to_schedule - (base_amt * Decimal(str(n_unpaid)))

            for i, inst in enumerate(unpaid_installments):
                amt = base_amt + (rem if i == n_unpaid - 1 else Decimal('0.00'))
                inst.amount_due = amt
                inst.update_status(commit=True)

        # Audit log
        FeeAuditLog.objects.create(
            school=student_fee.school,
            action=FeeAuditLog.Action.DISCOUNT_APPLIED if discount_amount is not None else FeeAuditLog.Action.WAIVER_APPLIED,
            student=student_fee.student,
            performed_by=performed_by,
            ip_address=ip_address,
            details={
                'student_fee_id': student_fee.id,
                'old_discount': str(old_discount),
                'new_discount': str(student_fee.discount_amount),
                'old_waived': str(old_waived),
                'new_waived': str(student_fee.waived_amount),
                'net_payable': str(student_fee.net_payable_amount),
            }
        )

        return student_fee

    @classmethod
    def get_student_fee_summary(cls, student: Student, academic_year: Optional[AcademicYear] = None) -> Dict[str, Any]:
        """
        Compiles complete fee balance, schedules, categories, and payment history for a student.
        """
        school = student.school
        if academic_year is None:
            academic_year = student.academic_year

        student_fees = StudentFee.objects.filter(
            school=school,
            student=student,
            academic_year=academic_year,
            is_active=True,
        ).select_related('fee_structure', 'fee_structure__fee_category')

        total_assigned = Decimal('0.00')
        total_paid = Decimal('0.00')

        categories_summary = []
        for sf in student_fees:
            sf_net = sf.net_payable_amount
            sf_paid = sf.total_paid
            total_assigned += sf_net
            total_paid += sf_paid

            categories_summary.append({
                'id': sf.id,
                'fee_name': sf.fee_structure.name,
                'category_name': sf.fee_structure.fee_category.name,
                'frequency': sf.fee_structure.get_payment_frequency_display(),
                'base_amount': sf.base_amount,
                'discount_amount': sf.discount_amount,
                'waived_amount': sf.waived_amount,
                'net_amount': sf_net,
                'paid_amount': sf_paid,
                'balance': sf.remaining_balance,
                'status': sf.overall_status,
            })

        total_outstanding = max(Decimal('0.00'), total_assigned - total_paid)

        # Installments
        installments = list(
            FeeInstallment.objects.filter(
                school=school,
                student=student,
                academic_year=academic_year,
            ).select_related('student_fee__fee_structure').order_by('due_date', 'period_number')
        )

        today = timezone.localdate()
        total_overdue = Decimal('0.00')
        next_due_installment = None

        for inst in installments:
            if inst.status == FeeInstallment.Status.OVERDUE or (inst.due_date < today and inst.remaining_amount > Decimal('0.00')):
                total_overdue += inst.remaining_amount
            if next_due_installment is None and inst.remaining_amount > Decimal('0.00'):
                next_due_installment = inst

        # Payments
        payments = list(
            FeePayment.objects.filter(
                school=school,
                student=student,
                academic_year=academic_year,
                status=FeePayment.Status.SUCCESS,
            ).select_related('installment').order_by('-payment_date', '-created_at')
        )

        return {
            'student': student,
            'academic_year': academic_year,
            'total_assigned': total_assigned,
            'total_paid': total_paid,
            'total_outstanding': total_outstanding,
            'total_overdue': total_overdue,
            'next_due_installment': next_due_installment,
            'categories': categories_summary,
            'installments': installments,
            'payments': payments,
        }

    @classmethod
    def get_school_fee_metrics(
        cls,
        school,
        academic_year: Optional[AcademicYear] = None,
        standard_id: Optional[int] = None,
        division_id: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        Aggregates school-wide fee metrics (Expected, Collected, Outstanding, Overdue).
        """
        if academic_year is None:
            academic_year = AcademicYear.objects.filter(school=school, is_current=True).first()
            if not academic_year:
                academic_year = AcademicYear.objects.filter(school=school).first()

        if not academic_year:
            return {
                'total_expected': Decimal('0.00'),
                'total_collected': Decimal('0.00'),
                'total_outstanding': Decimal('0.00'),
                'total_overdue': Decimal('0.00'),
                'collection_rate': 0.0,
                'total_students_enrolled': 0,
                'total_students_with_dues': 0,
            }

        students_qs = Student.objects.filter(
            school=school,
            academic_year=academic_year,
            is_active=True,
        )
        if standard_id:
            students_qs = students_qs.filter(standard_id=standard_id)
        if division_id:
            students_qs = students_qs.filter(division_id=division_id)

        student_ids = list(students_qs.values_list('id', flat=True))

        # Total Paid
        payments_qs = FeePayment.objects.filter(
            school=school,
            academic_year=academic_year,
            student_id__in=student_ids,
            status=FeePayment.Status.SUCCESS,
        )
        total_collected = payments_qs.aggregate(t=models.Sum('amount'))['t'] or Decimal('0.00')

        # Total Expected (Net payable)
        student_fees = StudentFee.objects.filter(
            school=school,
            academic_year=academic_year,
            student_id__in=student_ids,
            is_active=True,
        ).select_related('fee_structure')

        total_expected = Decimal('0.00')
        for sf in student_fees:
            total_expected += sf.net_payable_amount

        total_outstanding = max(Decimal('0.00'), total_expected - total_collected)

        # Overdue
        today = timezone.localdate()
        overdue_installments = FeeInstallment.objects.filter(
            school=school,
            academic_year=academic_year,
            student_id__in=student_ids,
        ).filter(
            models.Q(status=FeeInstallment.Status.OVERDUE) |
            models.Q(due_date__lt=today, amount_paid__lt=models.F('amount_due'))
        )
        
        total_overdue = Decimal('0.00')
        for oi in overdue_installments:
            total_overdue += oi.remaining_amount

        collection_rate = 0.0
        if total_expected > Decimal('0.00'):
            collection_rate = round(float((total_collected / total_expected) * 100), 1)

        return {
            'academic_year': academic_year,
            'total_expected': total_expected,
            'total_collected': total_collected,
            'total_outstanding': total_outstanding,
            'total_overdue': total_overdue,
            'collection_rate': collection_rate,
            'total_students_enrolled': len(student_ids),
        }
