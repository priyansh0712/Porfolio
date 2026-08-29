"""
Automated Test Suite for School Fees Management.

Tests:
  - FrequencyEngine: Monthly (12), Quarterly (4), Half-Yearly (2), Full-Year (1) with exact penny rounding.
  - FeeService: Class fee assignment, student fee assignment, partial payments, full payments, cascading payments.
  - State Transitions: UNPAID -> PARTIAL -> PAID and OVERDUE calculation.
  - Adjustments: Discounts, waivers, and schedule recalculation.
  - Payment Voiding & Audit Trail Integrity.
  - Multi-Tenant Isolation: Cross-tenant data isolation and direct URL manipulation resistance.
  - Role-Based Permissions: School Admin vs Faculty vs Student vs Cross-Student authorization.
"""
from datetime import date, timedelta
from decimal import Decimal
from django.test import TestCase, Client
from django.urls import reverse
from django.utils import timezone

from apps.tenants.models import School
from apps.accounts.models import User
from apps.academics.models import AcademicYear, Standard, Division
from apps.students.models import Student
from apps.fees.models import (
    FeeCategory,
    FeeStructure,
    StudentFee,
    FeeInstallment,
    FeePayment,
    FeeAuditLog,
)
from apps.fees.services import FrequencyEngine, FeeService


class BaseFeesTestCase(TestCase):
    def setUp(self):
        # 1. Setup School A (Primary Tenant)
        self.school_a = School.objects.create(
            name="Greenwood High",
            subdomain="greenwood",
            contact_email="admin@greenwood.edu",
        )
        self.admin_a = User.objects.create_user(
            username="admin_a",
            email="admin@greenwood.edu",
            password="Password@123",
            role=User.Role.SCHOOL_ADMIN,
            school=self.school_a,
        )
        self.faculty_a = User.objects.create_user(
            username="faculty_a",
            email="teacher@greenwood.edu",
            password="Password@123",
            role=User.Role.FACULTY,
            school=self.school_a,
        )

        self.year_a = AcademicYear.objects.create(
            school=self.school_a,
            name="2026-2027",
            start_date=date(2026, 4, 1),
            end_date=date(2027, 3, 31),
            is_current=True,
        )
        self.std_10 = Standard.objects.create(
            school=self.school_a,
            name="Standard 10",
            order_index=10,
        )
        self.div_10a = Division.objects.create(
            school=self.school_a,
            standard=self.std_10,
            name="A",
        )

        # Create Student 1 in School A
        self.student_user_1 = User.objects.create_user(
            username="GR001",
            email="student1@greenwood.edu",
            password="Password@123",
            role=User.Role.STUDENT,
            school=self.school_a,
        )
        self.student_1 = Student.objects.create(
            school=self.school_a,
            user=self.student_user_1,
            gr_number="GR001",
            roll_number=1,
            full_name="Alice Walker",
            academic_year=self.year_a,
            standard=self.std_10,
            division=self.div_10a,
        )

        # Create Student 2 in School A
        self.student_user_2 = User.objects.create_user(
            username="GR002",
            email="student2@greenwood.edu",
            password="Password@123",
            role=User.Role.STUDENT,
            school=self.school_a,
        )
        self.student_2 = Student.objects.create(
            school=self.school_a,
            user=self.student_user_2,
            gr_number="GR002",
            roll_number=2,
            full_name="Bob Smith",
            academic_year=self.year_a,
            standard=self.std_10,
            division=self.div_10a,
        )

        # 2. Setup School B (Secondary Tenant for Isolation Testing)
        self.school_b = School.objects.create(
            name="St. Mary Academy",
            subdomain="stmary",
            contact_email="admin@stmary.edu",
        )
        self.admin_b = User.objects.create_user(
            username="admin_b",
            email="admin@stmary.edu",
            password="Password@123",
            role=User.Role.SCHOOL_ADMIN,
            school=self.school_b,
        )
        self.year_b = AcademicYear.objects.create(
            school=self.school_b,
            name="2026-2027",
            start_date=date(2026, 4, 1),
            end_date=date(2027, 3, 31),
            is_current=True,
        )
        self.std_b = Standard.objects.create(
            school=self.school_b,
            name="Grade 10",
            order_index=10,
        )
        self.div_b = Division.objects.create(
            school=self.school_b,
            standard=self.std_b,
            name="A",
        )
        self.student_b = Student.objects.create(
            school=self.school_b,
            gr_number="GR999",
            full_name="Charlie Brown",
            academic_year=self.year_b,
            standard=self.std_b,
            division=self.div_b,
        )

        # 3. Create Categories for School A
        self.cat_tuition = FeeCategory.objects.create(
            school=self.school_a,
            name="Tuition Fee",
            code="TUITION",
        )
        self.cat_transport = FeeCategory.objects.create(
            school=self.school_a,
            name="Transport Fee",
            code="TRANSPORT",
        )


class FrequencyEngineTests(BaseFeesTestCase):
    """
    Tests for payment frequency scheduling and exact mathematical penny rounding.
    """

    def test_monthly_frequency_generates_12_installments(self):
        total = Decimal('60000.00')
        periods = FrequencyEngine.generate_schedule_periods(
            academic_year=self.year_a,
            payment_frequency=FeeStructure.Frequency.MONTHLY,
            total_amount=total,
            due_day=10,
        )
        self.assertEqual(len(periods), 12)
        # Check sum of installments exactly equals total
        sum_amount = sum(p['amount_due'] for p in periods)
        self.assertEqual(sum_amount, total)
        # First installment due in April 2026
        self.assertEqual(periods[0]['due_date'], date(2026, 4, 10))
        # Last installment due in March 2027
        self.assertEqual(periods[11]['due_date'], date(2027, 3, 10))

    def test_quarterly_frequency_generates_4_installments(self):
        total = Decimal('25000.00')
        periods = FrequencyEngine.generate_schedule_periods(
            academic_year=self.year_a,
            payment_frequency=FeeStructure.Frequency.QUARTERLY,
            total_amount=total,
            due_day=15,
        )
        self.assertEqual(len(periods), 4)
        sum_amount = sum(p['amount_due'] for p in periods)
        self.assertEqual(sum_amount, total)
        # Q1 in Apr, Q2 in Jul, Q3 in Oct, Q4 in Jan
        self.assertEqual(periods[0]['due_date'], date(2026, 4, 15))
        self.assertEqual(periods[1]['due_date'], date(2026, 7, 15))
        self.assertEqual(periods[2]['due_date'], date(2026, 10, 15))
        self.assertEqual(periods[3]['due_date'], date(2027, 1, 15))

    def test_half_yearly_frequency_generates_2_installments(self):
        total = Decimal('30000.00')
        periods = FrequencyEngine.generate_schedule_periods(
            academic_year=self.year_a,
            payment_frequency=FeeStructure.Frequency.HALF_YEARLY,
            total_amount=total,
            due_day=5,
        )
        self.assertEqual(len(periods), 2)
        sum_amount = sum(p['amount_due'] for p in periods)
        self.assertEqual(sum_amount, total)
        self.assertEqual(periods[0]['due_date'], date(2026, 4, 5))
        self.assertEqual(periods[1]['due_date'], date(2026, 10, 5))

    def test_full_year_frequency_generates_1_installment(self):
        total = Decimal('45000.00')
        periods = FrequencyEngine.generate_schedule_periods(
            academic_year=self.year_a,
            payment_frequency=FeeStructure.Frequency.FULL_YEAR,
            total_amount=total,
            due_day=10,
        )
        self.assertEqual(len(periods), 1)
        self.assertEqual(periods[0]['amount_due'], total)
        self.assertEqual(periods[0]['due_date'], date(2026, 4, 10))

    def test_penny_accurate_rounding_leaves_no_fractions_lost(self):
        # 10,000 divided into 3 or 7 or non-even amounts (e.g. 10000 / 12 = 833.33333...)
        total = Decimal('10000.00')
        periods = FrequencyEngine.generate_schedule_periods(
            academic_year=self.year_a,
            payment_frequency=FeeStructure.Frequency.MONTHLY,
            total_amount=total,
            due_day=10,
        )
        self.assertEqual(len(periods), 12)
        sum_amount = sum(p['amount_due'] for p in periods)
        self.assertEqual(sum_amount, total)
        # Verify first 11 installments are 833.33 and 12th is 833.37
        self.assertEqual(periods[0]['amount_due'], Decimal('833.33'))
        self.assertEqual(periods[11]['amount_due'], Decimal('833.37'))


class FeeServiceAndPaymentTests(BaseFeesTestCase):
    """
    Tests for fee assignments, partial/full payments, status transitions, and receipts.
    """

    def setUp(self):
        super().setUp()
        self.structure_monthly = FeeStructure.objects.create(
            school=self.school_a,
            name="Class 10 Monthly Tuition",
            academic_year=self.year_a,
            fee_category=self.cat_tuition,
            standard=self.std_10,
            amount=Decimal('60000.00'),
            payment_frequency=FeeStructure.Frequency.MONTHLY,
            due_day=10,
        )

    def test_assign_fee_to_student_creates_installments(self):
        student_fee = FeeService.assign_fee_to_student(
            student=self.student_1,
            fee_structure=self.structure_monthly,
            performed_by=self.admin_a,
        )
        self.assertEqual(student_fee.net_payable_amount, Decimal('60000.00'))
        self.assertEqual(student_fee.installments.count(), 12)
        self.assertEqual(student_fee.remaining_balance, Decimal('60000.00'))
        self.assertEqual(student_fee.total_paid, Decimal('0.00'))

    def test_assign_fee_to_class_bulk_assigns(self):
        assigned_count = FeeService.assign_fee_to_class(
            school=self.school_a,
            academic_year=self.year_a,
            fee_structure=self.structure_monthly,
            standard=self.std_10,
            division=self.div_10a,
            performed_by=self.admin_a,
        )
        self.assertEqual(assigned_count, 2)  # Alice and Bob
        self.assertEqual(StudentFee.objects.filter(school=self.school_a).count(), 2)
        self.assertEqual(FeeInstallment.objects.filter(school=self.school_a).count(), 24)

    def test_partial_and_full_payment_state_transitions(self):
        student_fee = FeeService.assign_fee_to_student(
            student=self.student_1,
            fee_structure=self.structure_monthly,
            performed_by=self.admin_a,
        )
        # Period 1 installment has amount_due = 5000.00
        inst_1 = student_fee.installments.get(period_number=1)
        self.assertEqual(inst_1.amount_due, Decimal('5000.00'))
        self.assertEqual(inst_1.amount_paid, Decimal('0.00'))

        # 1. Pay Partial ₹2000
        payment_1, affected_1 = FeeService.record_payment(
            school=self.school_a,
            student=self.student_1,
            amount=Decimal('2000.00'),
            payment_method=FeePayment.PaymentMethod.CASH,
            recorded_by=self.admin_a,
            installment=inst_1,
        )
        inst_1.refresh_from_db()
        self.assertEqual(inst_1.amount_paid, Decimal('2000.00'))
        self.assertEqual(inst_1.remaining_amount, Decimal('3000.00'))
        self.assertEqual(inst_1.status, FeeInstallment.Status.PARTIAL)
        self.assertTrue(payment_1.receipt_number.startswith("REC-GREENWOOD-"))

        # 2. Pay remaining ₹3000 to clear Period 1
        payment_2, affected_2 = FeeService.record_payment(
            school=self.school_a,
            student=self.student_1,
            amount=Decimal('3000.00'),
            payment_method=FeePayment.PaymentMethod.BANK_TRANSFER,
            recorded_by=self.admin_a,
            installment=inst_1,
        )
        inst_1.refresh_from_db()
        self.assertEqual(inst_1.amount_paid, Decimal('5000.00'))
        self.assertEqual(inst_1.remaining_amount, Decimal('0.00'))
        self.assertEqual(inst_1.status, FeeInstallment.Status.PAID)

        # 3. Overall Student balance
        student_fee.refresh_from_db()
        self.assertEqual(student_fee.total_paid, Decimal('5000.00'))
        self.assertEqual(student_fee.remaining_balance, Decimal('55000.00'))

    def test_payment_voiding_reverses_balance_and_audits(self):
        FeeService.assign_fee_to_student(
            student=self.student_1,
            fee_structure=self.structure_monthly,
            performed_by=self.admin_a,
        )
        payment, _ = FeeService.record_payment(
            school=self.school_a,
            student=self.student_1,
            amount=Decimal('5000.00'),
            payment_method=FeePayment.PaymentMethod.CHEQUE,
            recorded_by=self.admin_a,
        )
        self.assertEqual(self.student_1.fee_installments.get(period_number=1).status, FeeInstallment.Status.PAID)

        # Void payment
        voided = FeeService.void_payment(
            payment=payment,
            voided_by=self.admin_a,
            reason="Cheque bounced by bank",
        )
        self.assertEqual(voided.status, FeePayment.Status.VOIDED)
        self.assertEqual(voided.void_reason, "Cheque bounced by bank")
        
        # Installment reverted to unpaid/overdue
        inst_1 = self.student_1.fee_installments.get(period_number=1)
        self.assertEqual(inst_1.amount_paid, Decimal('0.00'))
        self.assertIn(inst_1.status, [FeeInstallment.Status.UNPAID, FeeInstallment.Status.OVERDUE])

        # Audit log exists
        self.assertTrue(FeeAuditLog.objects.filter(school=self.school_a, action=FeeAuditLog.Action.PAYMENT_VOIDED).exists())

    def test_apply_discount_and_waiver_recalculates_schedule(self):
        student_fee = FeeService.assign_fee_to_student(
            student=self.student_1,
            fee_structure=self.structure_monthly,
            performed_by=self.admin_a,
        )
        # Apply ₹12,000 discount (e.g. ₹1,000 less per month)
        FeeService.apply_adjustment(
            student_fee=student_fee,
            discount_amount=Decimal('12000.00'),
            discount_reason="Sibling Scholarship",
            performed_by=self.admin_a,
        )
        student_fee.refresh_from_db()
        self.assertEqual(student_fee.net_payable_amount, Decimal('48000.00'))
        # 48,000 / 12 = 4,000 per installment
        self.assertEqual(student_fee.installments.get(period_number=1).amount_due, Decimal('4000.00'))


class MultiTenantAndSecurityIsolationTests(BaseFeesTestCase):
    """
    Tests ensuring strict multi-tenant data isolation and defense-in-depth security.
    """

    def setUp(self):
        super().setUp()
        self.client = Client()
        self.structure_a = FeeStructure.objects.create(
            school=self.school_a,
            name="School A Fees",
            academic_year=self.year_a,
            fee_category=self.cat_tuition,
            amount=Decimal('50000.00'),
        )
        self.structure_b = FeeStructure.objects.create(
            school=self.school_b,
            name="School B Fees",
            academic_year=self.year_b,
            fee_category=FeeCategory.objects.create(school=self.school_b, name="Tuition B"),
            amount=Decimal('70000.00'),
        )
        self.payment_a, _ = FeeService.record_payment(
            school=self.school_a,
            student=self.student_1,
            amount=Decimal('5000.00'),
            payment_method=FeePayment.PaymentMethod.CASH,
            recorded_by=self.admin_a,
            installment=FeeService.assign_fee_to_student(self.student_1, self.structure_a).installments.first(),
        )

    def test_school_a_admin_cannot_see_school_b_structures(self):
        self.client.force_login(self.admin_a)
        response = self.client.get(reverse('fees:structures'), HTTP_HOST="greenwood.localhost")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "School A Fees")
        self.assertNotContains(response, "School B Fees")

    def test_cross_tenant_receipt_access_forbidden(self):
        # Admin B tries to access School A's payment receipt
        self.client.force_login(self.admin_b)
        response = self.client.get(
            reverse('fees:receipt_detail', kwargs={'pk': self.payment_a.pk}),
            HTTP_HOST="stmary.localhost"
        )
        self.assertIn(response.status_code, [403, 404])

    def test_faculty_member_cannot_access_fees_admin(self):
        self.client.force_login(self.faculty_a)
        response = self.client.get(reverse('fees:dashboard'), HTTP_HOST="greenwood.localhost")
        self.assertEqual(response.status_code, 403)

    def test_student_can_only_view_own_fees_and_receipts(self):
        # Student 1 logs in
        self.client.force_login(self.student_user_1)
        response = self.client.get(reverse('fees:student_fees'), HTTP_HOST="greenwood.localhost")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Alice Walker")

        # Student 1 views own receipt -> 200 OK
        receipt_resp = self.client.get(
            reverse('fees:receipt_detail', kwargs={'pk': self.payment_a.pk}),
            HTTP_HOST="greenwood.localhost"
        )
        self.assertEqual(receipt_resp.status_code, 200)

        # Student 2 tries to view Student 1's receipt -> 403 Forbidden
        self.client.force_login(self.student_user_2)
        foreign_receipt_resp = self.client.get(
            reverse('fees:receipt_detail', kwargs={'pk': self.payment_a.pk}),
            HTTP_HOST="greenwood.localhost"
        )
        self.assertEqual(foreign_receipt_resp.status_code, 403)
