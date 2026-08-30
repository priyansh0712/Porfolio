"""
School Fees Management Models.

Defines:
  - FeeCategory: Master categories for fees (Tuition, Transport, Activity, Exam, etc.)
  - FeeStructure: School fee policies per academic year, standard, category, and frequency.
  - StudentFee: Student-specific fee assignment with custom amounts, discounts, and waivers.
  - FeeInstallment: Generated payment schedule periods (Monthly, Quarterly, Half-Yearly, Full-Year).
  - FeePayment: Immutable payment ledger records with unique per-school receipt numbers.
  - FeeAuditLog: Financial audit trail for tracking adjustments, waivers, payments, and reversals.
"""
from decimal import Decimal
from django.conf import settings
from django.db import models
from django.utils import timezone

from apps.tenants.models import TenantModel


class FeeCategory(TenantModel):
    """
    Configurable fee category master (e.g., Tuition Fee, Transport Fee, Activity Fee, Exam Fee).
    """
    name = models.CharField(
        max_length=100,
        help_text='Name of the fee category (e.g. Tuition Fee, Transport Fee, Lab Fee)',
    )
    code = models.CharField(
        max_length=50,
        blank=True,
        help_text='Short code / identifier (e.g. TUITION, TRANSPORT)',
    )
    description = models.TextField(
        blank=True,
        help_text='Optional description of what this category covers',
    )
    is_active = models.BooleanField(
        default=True,
        help_text='Whether this category is available for new fee structures',
    )

    class Meta:
        ordering = ['name']
        verbose_name = 'Fee Category'
        verbose_name_plural = 'Fee Categories'
        constraints = [
            models.UniqueConstraint(
                fields=['school', 'name'],
                name='unique_fee_category_name_per_school',
            ),
        ]

    def __str__(self):
        return self.name


class FeeStructure(TenantModel):
    """
    Configurable fee structure per academic session, standard/division, category, and frequency.
    """
    class Frequency(models.TextChoices):
        MONTHLY = 'MONTHLY', 'Monthly'
        QUARTERLY = 'QUARTERLY', 'Quarterly'
        HALF_YEARLY = 'HALF_YEARLY', 'Half-Yearly'
        FULL_YEAR = 'FULL_YEAR', 'Full-Year'

    name = models.CharField(
        max_length=255,
        help_text='Display name (e.g. Class 10 Tuition Fee 2026-27)',
    )
    academic_year = models.ForeignKey(
        'academics.AcademicYear',
        on_delete=models.PROTECT,
        related_name='fee_structures',
        help_text='Academic session this fee structure applies to',
    )
    fee_category = models.ForeignKey(
        FeeCategory,
        on_delete=models.PROTECT,
        related_name='fee_structures',
        help_text='Associated fee category',
    )
    standard = models.ForeignKey(
        'academics.Standard',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='fee_structures',
        help_text='Target grade/standard (leave blank for all grades)',
    )
    division = models.ForeignKey(
        'academics.Division',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='fee_structures',
        help_text='Specific division (optional)',
    )
    amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        help_text='Total base annual fee amount for this structure',
    )
    payment_frequency = models.CharField(
        max_length=20,
        choices=Frequency.choices,
        default=Frequency.MONTHLY,
        help_text='Installment frequency (Monthly, Quarterly, Half-Yearly, Full-Year)',
    )
    due_day = models.PositiveSmallIntegerField(
        default=10,
        help_text='Day of the month/period when payment becomes due (1 to 28)',
    )
    description = models.TextField(
        blank=True,
        help_text='Optional internal notes or policy description',
    )
    is_active = models.BooleanField(
        default=True,
        help_text='Whether this fee structure is actively assigned',
    )

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Fee Structure'
        verbose_name_plural = 'Fee Structures'

    def __str__(self):
        grade_str = f" - {self.standard.name}" if self.standard else " - All Grades"
        return f"{self.name} ({self.get_payment_frequency_display()}){grade_str}"


class StudentFee(TenantModel):
    """
    Association of a Student with a FeeStructure in an Academic Year,
    including individual adjustments (custom amounts, discounts, waivers).
    """
    student = models.ForeignKey(
        'students.Student',
        on_delete=models.CASCADE,
        related_name='assigned_fees',
        help_text='Student assigned this fee',
    )
    academic_year = models.ForeignKey(
        'academics.AcademicYear',
        on_delete=models.PROTECT,
        related_name='student_fees',
        help_text='Academic year for this assignment',
    )
    fee_structure = models.ForeignKey(
        FeeStructure,
        on_delete=models.PROTECT,
        related_name='student_assignments',
        help_text='Base fee structure',
    )
    custom_amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        help_text='Custom base amount overriding the standard fee amount (if applicable)',
    )
    discount_amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal('0.00'),
        help_text='Discount amount applied to this student',
    )
    discount_reason = models.CharField(
        max_length=255,
        blank=True,
        help_text='Reason for discount / scholarship',
    )
    waived_amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal('0.00'),
        help_text='Amount waived by administration',
    )
    waiver_reason = models.CharField(
        max_length=255,
        blank=True,
        help_text='Reason for fee waiver',
    )
    is_active = models.BooleanField(
        default=True,
        help_text='Whether this student fee assignment is active',
    )

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Student Fee Assignment'
        verbose_name_plural = 'Student Fee Assignments'
        constraints = [
            models.UniqueConstraint(
                fields=['school', 'student', 'fee_structure'],
                name='unique_student_fee_structure_per_school',
            ),
        ]

    def __str__(self):
        return f"{self.student.full_name} — {self.fee_structure.name}"

    @property
    def base_amount(self) -> Decimal:
        if self.custom_amount is not None:
            return self.custom_amount
        return self.fee_structure.amount

    @property
    def net_payable_amount(self) -> Decimal:
        net = self.base_amount - (self.discount_amount or Decimal('0.00')) - (self.waived_amount or Decimal('0.00'))
        return max(Decimal('0.00'), net)

    @property
    def total_paid(self) -> Decimal:
        paid_sum = self.student.fee_payments.filter(
            school=self.school,
            academic_year=self.academic_year,
            status=FeePayment.Status.SUCCESS,
        ).aggregate(total=models.Sum('amount'))['total']
        return paid_sum or Decimal('0.00')

    @property
    def remaining_balance(self) -> Decimal:
        return max(Decimal('0.00'), self.net_payable_amount - self.total_paid)

    @property
    def overall_status(self) -> str:
        paid = self.total_paid
        net = self.net_payable_amount
        if net == Decimal('0.00') or paid >= net:
            return 'PAID'
        if paid > Decimal('0.00'):
            return 'PARTIALLY PAID'
        return 'PENDING'


class FeeInstallment(TenantModel):
    """
    Individual schedule installment period for a StudentFee (Monthly, Quarterly, Half-Yearly, Full-Year).
    """
    class Status(models.TextChoices):
        UNPAID = 'UNPAID', 'Unpaid'
        PARTIAL = 'PARTIAL', 'Partially Paid'
        PAID = 'PAID', 'Paid'
        OVERDUE = 'OVERDUE', 'Overdue'
        WAIVED = 'WAIVED', 'Waived'

    student_fee = models.ForeignKey(
        StudentFee,
        on_delete=models.CASCADE,
        related_name='installments',
        help_text='Parent student fee assignment',
    )
    student = models.ForeignKey(
        'students.Student',
        on_delete=models.CASCADE,
        related_name='fee_installments',
        help_text='Student reference for direct lookup',
    )
    academic_year = models.ForeignKey(
        'academics.AcademicYear',
        on_delete=models.PROTECT,
        related_name='fee_installments',
        help_text='Academic session',
    )
    period_number = models.PositiveSmallIntegerField(
        help_text='Sequential period index (1..12)',
    )
    period_name = models.CharField(
        max_length=100,
        help_text='Human readable label (e.g., April 2026, Q1 (Apr-Jun), Term 1, Full Year)',
    )
    due_date = models.DateField(
        help_text='Due date for this installment',
    )
    amount_due = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        help_text='Payable amount for this installment',
    )
    amount_paid = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal('0.00'),
        help_text='Total amount collected against this installment',
    )
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.UNPAID,
        db_index=True,
    )

    class Meta:
        ordering = ['period_number', 'due_date']
        verbose_name = 'Fee Installment'
        verbose_name_plural = 'Fee Installments'

    def __str__(self):
        return f"{self.student.full_name} — {self.period_name} ({self.get_status_display()})"

    @property
    def remaining_amount(self) -> Decimal:
        return max(Decimal('0.00'), self.amount_due - self.amount_paid)

    def update_status(self, commit: bool = True):
        today = timezone.localdate()
        if self.amount_paid >= self.amount_due and self.amount_due > Decimal('0.00'):
            self.status = self.Status.PAID
        elif self.amount_paid > Decimal('0.00'):
            self.status = self.Status.PARTIAL
        elif self.amount_paid == Decimal('0.00') and self.due_date < today:
            self.status = self.Status.OVERDUE
        else:
            self.status = self.Status.UNPAID

        if commit:
            self.save(update_fields=['amount_due', 'amount_paid', 'status', 'updated_at'])


class FeePayment(TenantModel):
    """
    Immutable ledger entry recording an approved fee transaction.
    """
    class PaymentMethod(models.TextChoices):
        CASH = 'CASH', 'Cash'
        BANK_TRANSFER = 'BANK_TRANSFER', 'Bank Transfer'
        CHEQUE = 'CHEQUE', 'Cheque'
        ONLINE = 'ONLINE', 'Online'

    class Status(models.TextChoices):
        SUCCESS = 'SUCCESS', 'Success'
        VOIDED = 'VOIDED', 'Voided'

    student = models.ForeignKey(
        'students.Student',
        on_delete=models.PROTECT,
        related_name='fee_payments',
        help_text='Student who paid',
    )
    academic_year = models.ForeignKey(
        'academics.AcademicYear',
        on_delete=models.PROTECT,
        related_name='fee_payments',
        help_text='Academic session',
    )
    installment = models.ForeignKey(
        FeeInstallment,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='payments',
        help_text='Specific installment this payment applies to (if single period)',
    )
    amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        help_text='Payment amount collected',
    )
    payment_date = models.DateField(
        default=timezone.now,
        help_text='Date payment was received',
    )
    payment_method = models.CharField(
        max_length=20,
        choices=PaymentMethod.choices,
        default=PaymentMethod.CASH,
        help_text='Mode of payment',
    )
    transaction_reference = models.CharField(
        max_length=100,
        blank=True,
        help_text='Cheque number, UTR, Bank transaction ref, or receipt reference',
    )
    receipt_number = models.CharField(
        max_length=64,
        db_index=True,
        help_text='Unique sequential receipt number per school',
    )
    recorded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='recorded_fee_payments',
        help_text='Staff member / Admin who recorded the payment',
    )
    remarks = models.TextField(
        blank=True,
        help_text='Additional notes or comments',
    )
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.SUCCESS,
        db_index=True,
    )
    void_reason = models.TextField(
        blank=True,
        help_text='Reason for voiding/reversing this payment',
    )
    voided_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='voided_fee_payments',
        help_text='Staff member who voided the transaction',
    )
    voided_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text='Timestamp when voided',
    )

    class Meta:
        ordering = ['-payment_date', '-created_at']
        verbose_name = 'Fee Payment'
        verbose_name_plural = 'Fee Payments'
        constraints = [
            models.UniqueConstraint(
                fields=['school', 'receipt_number'],
                name='unique_receipt_number_per_school',
            ),
        ]

    def __str__(self):
        return f"Receipt #{self.receipt_number} — ₹{self.amount} ({self.student.full_name})"


class FeeAuditLog(TenantModel):
    """
    Audit log tracking financial adjustments, waivers, payment receipts, and reversals.
    """
    class Action(models.TextChoices):
        PAYMENT_RECORDED = 'PAYMENT_RECORDED', 'Payment Recorded'
        PAYMENT_VOIDED = 'PAYMENT_VOIDED', 'Payment Voided'
        FEE_ASSIGNED = 'FEE_ASSIGNED', 'Fee Assigned'
        DISCOUNT_APPLIED = 'DISCOUNT_APPLIED', 'Discount Applied'
        WAIVER_APPLIED = 'WAIVER_APPLIED', 'Waiver Applied'
        SCHEDULE_REGENERATED = 'SCHEDULE_REGENERATED', 'Schedule Regenerated'

    action = models.CharField(
        max_length=50,
        choices=Action.choices,
        db_index=True,
    )
    student = models.ForeignKey(
        'students.Student',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='fee_audit_logs',
    )
    performed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='fee_audit_actions',
    )
    details = models.JSONField(
        default=dict,
        blank=True,
        help_text='JSON metadata of before/after financial state',
    )
    ip_address = models.GenericIPAddressField(
        null=True,
        blank=True,
    )

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Fee Audit Log'
        verbose_name_plural = 'Fee Audit Logs'

    def __str__(self):
        user_str = self.performed_by.username if self.performed_by else 'System'
        return f"{self.get_action_display()} by {user_str} at {self.created_at}"
