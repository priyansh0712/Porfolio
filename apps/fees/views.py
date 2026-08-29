"""
View Controllers for School Fees Management.

Includes:
  - Admin Views: Dashboard, Structures, Categories, Student Roster, Student Details, Collect Payment, Receipts, Reports.
  - Student Portal Views: StudentFeesView (own fees, schedules, payments, receipts).
"""
import csv
from decimal import Decimal
from django.contrib import messages
from django.core.exceptions import ValidationError
from django.db import models
from django.http import HttpResponse, HttpResponseForbidden, JsonResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.utils import timezone
from django.views import View
from django.views.generic import TemplateView

from apps.accounts.permissions import SchoolAdminRequiredMixin
from apps.students.views import StudentRequiredMixin
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
from apps.fees.services import FeeService


# ══════════════════════════════════════════════════════════════════════════════
# 1. School Admin Fee Dashboard
# ══════════════════════════════════════════════════════════════════════════════

class AdminFeeDashboardView(SchoolAdminRequiredMixin, View):
    """
    High-level Fee Overview dashboard with KPI cards, quick actions, and recent activities.
    """
    def get(self, request):
        school = request.tenant
        current_year = AcademicYear.objects.filter(school=school, is_current=True).first()
        if not current_year:
            current_year = AcademicYear.objects.filter(school=school).first()

        metrics = FeeService.get_school_fee_metrics(school=school, academic_year=current_year)

        # Recent 10 payments
        recent_payments = FeePayment.objects.filter(
            school=school,
            academic_year=current_year,
            status=FeePayment.Status.SUCCESS,
        ).select_related('student', 'student__division', 'student__standard').order_by('-payment_date', '-created_at')[:10]

        # Overdue installments sample
        today = timezone.localdate()
        overdue_installments = FeeInstallment.objects.filter(
            school=school,
            academic_year=current_year,
        ).filter(
            models.Q(status=FeeInstallment.Status.OVERDUE) |
            models.Q(due_date__lt=today, amount_paid__lt=models.F('amount_due'))
        ).select_related('student', 'student__standard', 'student__division', 'student_fee__fee_structure').order_by('due_date')[:10]

        return render(request, 'fees/dashboard.html', {
            'metrics': metrics,
            'current_year': current_year,
            'recent_payments': recent_payments,
            'overdue_installments': overdue_installments,
        })


# ══════════════════════════════════════════════════════════════════════════════
# 2. Fee Categories Management
# ══════════════════════════════════════════════════════════════════════════════

class FeeCategoryListView(SchoolAdminRequiredMixin, View):
    """
    List and create custom fee categories for the school.
    """
    def get(self, request):
        school = request.tenant
        categories = FeeCategory.objects.filter(school=school).order_by('name')
        if not categories.exists():
            FeeService.ensure_default_categories(school)
            categories = FeeCategory.objects.filter(school=school).order_by('name')

        return render(request, 'fees/fee_categories.html', {
            'categories': categories,
        })

    def post(self, request):
        school = request.tenant
        name = request.POST.get('name', '').strip()
        code = request.POST.get('code', '').strip().upper()
        description = request.POST.get('description', '').strip()

        if not name:
            messages.error(request, "Category name is required.")
            return redirect('fees:categories')

        if FeeCategory.objects.filter(school=school, name__iexact=name).exists():
            messages.error(request, f"Category '{name}' already exists.")
            return redirect('fees:categories')

        FeeCategory.objects.create(
            school=school,
            name=name,
            code=code or name[:10].upper(),
            description=description,
        )
        messages.success(request, f"Fee Category '{name}' created successfully.")
        return redirect('fees:categories')


# ══════════════════════════════════════════════════════════════════════════════
# 3. Fee Structures Management
# ══════════════════════════════════════════════════════════════════════════════

class FeeStructureListView(SchoolAdminRequiredMixin, View):
    """
    List, filter, and create fee structures.
    """
    def get(self, request):
        school = request.tenant
        academic_years = AcademicYear.objects.filter(school=school).order_by('-start_date')
        standards = Standard.objects.filter(school=school, is_active=True).order_by('order_index')
        categories = FeeCategory.objects.filter(school=school, is_active=True).order_by('name')
        if not categories.exists():
            FeeService.ensure_default_categories(school)
            categories = FeeCategory.objects.filter(school=school, is_active=True).order_by('name')

        selected_year_id = request.GET.get('academic_year_id')
        if selected_year_id:
            structures = FeeStructure.objects.filter(school=school, academic_year_id=selected_year_id)
        else:
            current_year = AcademicYear.objects.filter(school=school, is_current=True).first()
            if current_year:
                structures = FeeStructure.objects.filter(school=school, academic_year=current_year)
                selected_year_id = str(current_year.id)
            else:
                structures = FeeStructure.objects.filter(school=school)

        structures = structures.select_related('academic_year', 'fee_category', 'standard').order_by('-created_at')

        return render(request, 'fees/fee_structures.html', {
            'structures': structures,
            'academic_years': academic_years,
            'standards': standards,
            'categories': categories,
            'selected_year_id': selected_year_id,
            'frequencies': FeeStructure.Frequency.choices,
        })

    def post(self, request):
        school = request.tenant
        name = request.POST.get('name', '').strip()
        academic_year_id = request.POST.get('academic_year')
        fee_category_id = request.POST.get('fee_category')
        standard_id = request.POST.get('standard') or None
        amount_raw = request.POST.get('amount', '0').strip()
        payment_frequency = request.POST.get('payment_frequency', FeeStructure.Frequency.MONTHLY)
        due_day_raw = request.POST.get('due_day', '10').strip()
        description = request.POST.get('description', '').strip()

        try:
            amount = Decimal(amount_raw)
            if amount <= Decimal('0.00'):
                raise ValueError
        except Exception:
            messages.error(request, "Please provide a valid positive fee amount.")
            return redirect('fees:structures')

        try:
            due_day = int(due_day_raw)
            if not (1 <= due_day <= 28):
                due_day = 10
        except ValueError:
            due_day = 10

        academic_year = get_object_or_404(AcademicYear, school=school, pk=academic_year_id)
        fee_category = get_object_or_404(FeeCategory, school=school, pk=fee_category_id)
        standard = Standard.objects.filter(school=school, pk=standard_id).first() if standard_id else None

        auto_assign = request.POST.get('auto_assign') in ['1', 'true', 'on', 'yes']

        fs = FeeStructure.objects.create(
            school=school,
            name=name,
            academic_year=academic_year,
            fee_category=fee_category,
            standard=standard,
            amount=amount,
            payment_frequency=payment_frequency,
            due_day=due_day,
            description=description,
        )

        assigned_msg = ""
        if auto_assign:
            count = FeeService.assign_fee_to_class(
                school=school,
                academic_year=academic_year,
                fee_structure=fs,
                standard=standard,
                performed_by=request.user,
                ip_address=request.META.get('REMOTE_ADDR'),
            )
            if standard:
                assigned_msg = f" and automatically assigned to {count} students in {standard.name}"
            else:
                assigned_msg = f" and automatically assigned to {count} enrolled students across all grades"

        messages.success(request, f"Fee Structure '{name}' created successfully{assigned_msg}!")
        return redirect('fees:structures')


# ══════════════════════════════════════════════════════════════════════════════
# 4. Student Fee Roster & Bulk Class Assignment
# ══════════════════════════════════════════════════════════════════════════════

class StudentFeeRosterView(SchoolAdminRequiredMixin, View):
    """
    Roster of students with fee balances, statuses, and quick assignment actions.
    """
    def get(self, request):
        school = request.tenant
        academic_years = AcademicYear.objects.filter(school=school).order_by('-start_date')
        standards = Standard.objects.filter(school=school, is_active=True).order_by('order_index')
        divisions = Division.objects.filter(school=school, is_active=True).select_related('standard').order_by('standard__order_index', 'name')

        selected_year_id = request.GET.get('academic_year_id')
        selected_standard_id = request.GET.get('standard_id')
        selected_division_id = request.GET.get('division_id')
        search_query = request.GET.get('q', '').strip()

        current_year = None
        if selected_year_id:
            current_year = AcademicYear.objects.filter(school=school, pk=selected_year_id).first()
        if not current_year:
            current_year = AcademicYear.objects.filter(school=school, is_current=True).first()
        if not current_year:
            current_year = academic_years.first()

        students_qs = Student.objects.filter(
            school=school,
            is_active=True,
        )
        if current_year:
            students_qs = students_qs.filter(academic_year=current_year)
        if selected_standard_id:
            students_qs = students_qs.filter(standard_id=selected_standard_id)
        if selected_division_id:
            students_qs = students_qs.filter(division_id=selected_division_id)
        if search_query:
            students_qs = students_qs.filter(
                models.Q(full_name__icontains=search_query) |
                models.Q(gr_number__icontains=search_query)
            )

        students_qs = students_qs.select_related('standard', 'division').order_by('standard__order_index', 'division__name', 'roll_number', 'full_name')

        # Compile summaries for the listed students
        student_rows = []
        for s in students_qs:
            summary = FeeService.get_student_fee_summary(student=s, academic_year=current_year)
            student_rows.append({
                'student': s,
                'total_assigned': summary['total_assigned'],
                'total_paid': summary['total_paid'],
                'total_outstanding': summary['total_outstanding'],
                'total_overdue': summary['total_overdue'],
                'next_due': summary['next_due_installment'],
            })

        fee_structures = FeeStructure.objects.filter(
            school=school,
            academic_year=current_year,
            is_active=True,
        ).select_related('fee_category', 'standard') if current_year else []

        all_fee_structures = FeeStructure.objects.filter(
            school=school,
            is_active=True,
        ).select_related('fee_category', 'standard', 'academic_year').order_by('-created_at')

        return render(request, 'fees/student_fee_roster.html', {
            'student_rows': student_rows,
            'academic_years': academic_years,
            'standards': standards,
            'divisions': divisions,
            'fee_structures': fee_structures,
            'all_fee_structures': all_fee_structures,
            'current_year': current_year,
            'selected_standard_id': selected_standard_id,
            'selected_division_id': selected_division_id,
            'search_query': search_query,
        })

    def post(self, request):
        """
        Assigns a fee structure to a standard/division or single student.
        """
        school = request.tenant
        action = request.POST.get('action')

        if action == 'assign_class':
            academic_year_id = request.POST.get('academic_year')
            fee_structure_id = request.POST.get('fee_structure')
            standard_id = request.POST.get('standard') or None
            division_id = request.POST.get('division') or None

            academic_year = get_object_or_404(AcademicYear, school=school, pk=academic_year_id)
            fee_structure = get_object_or_404(FeeStructure, school=school, pk=fee_structure_id)
            standard = Standard.objects.filter(school=school, pk=standard_id).first() if standard_id else None
            division = Division.objects.filter(school=school, pk=division_id).first() if division_id else None

            assigned_count = FeeService.assign_fee_to_class(
                school=school,
                academic_year=academic_year,
                fee_structure=fee_structure,
                standard=standard,
                division=division,
                performed_by=request.user,
                ip_address=request.META.get('REMOTE_ADDR'),
            )
            messages.success(request, f"Assigned '{fee_structure.name}' to {assigned_count} students.")

        return redirect('fees:student_roster')


# ══════════════════════════════════════════════════════════════════════════════
# 5. Individual Student Fee Detail
# ══════════════════════════════════════════════════════════════════════════════

class StudentFeeDetailView(SchoolAdminRequiredMixin, View):
    """
    Detailed fee ledger for a single student (categories, installments, payment records, adjustments).
    """
    def get(self, request, pk):
        school = request.tenant
        student = get_object_or_404(Student, school=school, pk=pk)
        summary = FeeService.get_student_fee_summary(student=student)

        # Available fee structures that can still be assigned to this student
        assigned_fs_ids = student.assigned_fees.values_list('fee_structure_id', flat=True)
        available_structures = FeeStructure.objects.filter(
            school=school,
            academic_year=student.academic_year,
            is_active=True,
        ).exclude(id__in=assigned_fs_ids).select_related('fee_category')

        return render(request, 'fees/student_fee_detail.html', {
            'student': student,
            'summary': summary,
            'available_structures': available_structures,
            'payment_methods': FeePayment.PaymentMethod.choices,
        })

    def post(self, request, pk):
        school = request.tenant
        student = get_object_or_404(Student, school=school, pk=pk)
        action = request.POST.get('action')

        if action == 'assign_single':
            fee_structure_id = request.POST.get('fee_structure_id')
            fee_structure = get_object_or_404(FeeStructure, school=school, pk=fee_structure_id)
            FeeService.assign_fee_to_student(
                student=student,
                fee_structure=fee_structure,
                performed_by=request.user,
                ip_address=request.META.get('REMOTE_ADDR'),
            )
            messages.success(request, f"Fee '{fee_structure.name}' assigned to {student.full_name}.")

        elif action == 'apply_adjustment':
            student_fee_id = request.POST.get('student_fee_id')
            discount_raw = request.POST.get('discount_amount', '0').strip()
            discount_reason = request.POST.get('discount_reason', '').strip()
            waived_raw = request.POST.get('waived_amount', '0').strip()
            waiver_reason = request.POST.get('waiver_reason', '').strip()

            student_fee = get_object_or_404(StudentFee, school=school, pk=student_fee_id, student=student)
            discount_amt = Decimal(discount_raw) if discount_raw else Decimal('0.00')
            waived_amt = Decimal(waived_raw) if waived_raw else Decimal('0.00')

            FeeService.apply_adjustment(
                student_fee=student_fee,
                discount_amount=discount_amt,
                discount_reason=discount_reason,
                waived_amount=waived_amt,
                waiver_reason=waiver_reason,
                performed_by=request.user,
                ip_address=request.META.get('REMOTE_ADDR'),
            )
            messages.success(request, "Fee adjustment / waiver applied successfully.")

        return redirect('fees:student_detail', pk=student.pk)


# ══════════════════════════════════════════════════════════════════════════════
# 6. Payment Collection
# ══════════════════════════════════════════════════════════════════════════════

class FeePaymentCollectView(SchoolAdminRequiredMixin, View):
    """
    Record an in-person or direct fee collection and generate a receipt.
    """
    def get(self, request):
        school = request.tenant
        student_id = request.GET.get('student_id')
        installment_id = request.GET.get('installment_id')

        student = None
        unpaid_installments = []
        if student_id:
            student = get_object_or_404(Student, school=school, pk=student_id)
            unpaid_installments = FeeInstallment.objects.filter(
                school=school,
                student=student,
            ).exclude(status=FeeInstallment.Status.PAID).order_by('due_date', 'period_number')

        all_students = Student.objects.filter(school=school, is_active=True).select_related('standard', 'division').order_by('full_name')

        return render(request, 'fees/collect_payment.html', {
            'selected_student': student,
            'selected_installment_id': installment_id,
            'unpaid_installments': unpaid_installments,
            'all_students': all_students,
            'payment_methods': FeePayment.PaymentMethod.choices,
        })

    def post(self, request):
        school = request.tenant
        student_id = request.POST.get('student_id')
        installment_id = request.POST.get('installment_id') or None
        amount_raw = request.POST.get('amount', '').strip()
        payment_method = request.POST.get('payment_method', FeePayment.PaymentMethod.CASH)
        transaction_reference = request.POST.get('transaction_reference', '').strip()
        remarks = request.POST.get('remarks', '').strip()

        student = get_object_or_404(Student, school=school, pk=student_id)

        try:
            amount = Decimal(amount_raw)
            if amount <= Decimal('0.00'):
                raise ValueError
        except Exception:
            messages.error(request, "Please enter a valid positive payment amount.")
            return redirect(f"{request.path}?student_id={student.pk}")

        installment = None
        if installment_id:
            installment = FeeInstallment.objects.filter(school=school, student=student, pk=installment_id).first()

        try:
            payment, affected = FeeService.record_payment(
                school=school,
                student=student,
                amount=amount,
                payment_method=payment_method,
                recorded_by=request.user,
                installment=installment,
                transaction_reference=transaction_reference,
                remarks=remarks,
                ip_address=request.META.get('REMOTE_ADDR'),
            )
            messages.success(request, f"Payment of ₹{amount} recorded successfully. Receipt #{payment.receipt_number}")
            return redirect('fees:receipt_detail', pk=payment.pk)
        except ValidationError as e:
            messages.error(request, str(e.message if hasattr(e, 'message') else e))
            return redirect(f"{request.path}?student_id={student.pk}")


# ══════════════════════════════════════════════════════════════════════════════
# 7. Printable Fee Receipt View
# ══════════════════════════════════════════════════════════════════════════════

class FeeReceiptDetailView(View):
    """
    Printable and downloadable official fee receipt (Accessible to Admin and Student owner).
    """
    def get(self, request, pk):
        user = request.user
        school = getattr(request, 'tenant', None)

        if not user.is_authenticated:
            return redirect('accounts:login')

        payment = get_object_or_404(FeePayment, pk=pk)

        # Multi-Tenant & Role Authorization Guard
        if payment.school != school:
            return HttpResponseForbidden("Access denied: Cross-tenant receipt access is prohibited.")

        if user.role == 'STUDENT':
            # Verify student owns this payment
            if not hasattr(user, 'student_profile') or user.student_profile != payment.student:
                return HttpResponseForbidden("Access denied: You can only view your own receipts.")
        elif user.role != 'SCHOOL_ADMIN':
            return HttpResponseForbidden("Access denied: Insufficient permissions to view fee receipt.")

        # Compute remaining balance after this payment
        summary = FeeService.get_student_fee_summary(student=payment.student, academic_year=payment.academic_year)

        return render(request, 'fees/receipt_detail.html', {
            'payment': payment,
            'student': payment.student,
            'school': payment.school,
            'total_balance_remaining': summary['total_outstanding'],
        })


# ══════════════════════════════════════════════════════════════════════════════
# 8. Fee Financial Reports & CSV Export
# ══════════════════════════════════════════════════════════════════════════════

class FeeReportsView(SchoolAdminRequiredMixin, View):
    """
    Comprehensive financial collection report with filtering and CSV export.
    """
    def get(self, request):
        school = request.tenant
        academic_years = AcademicYear.objects.filter(school=school).order_by('-start_date')
        standards = Standard.objects.filter(school=school, is_active=True).order_by('order_index')

        selected_year_id = request.GET.get('academic_year_id')
        selected_standard_id = request.GET.get('standard_id')
        selected_method = request.GET.get('payment_method')
        start_date = request.GET.get('start_date')
        end_date = request.GET.get('end_date')

        current_year = None
        if selected_year_id:
            current_year = AcademicYear.objects.filter(school=school, pk=selected_year_id).first()
        if not current_year:
            current_year = AcademicYear.objects.filter(school=school, is_current=True).first()

        payments = FeePayment.objects.filter(school=school, status=FeePayment.Status.SUCCESS)
        if current_year:
            payments = payments.filter(academic_year=current_year)
        if selected_standard_id:
            payments = payments.filter(student__standard_id=selected_standard_id)
        if selected_method:
            payments = payments.filter(payment_method=selected_method)
        if start_date:
            payments = payments.filter(payment_date__gte=start_date)
        if end_date:
            payments = payments.filter(payment_date__lte=end_date)

        payments = payments.select_related('student', 'student__standard', 'student__division', 'recorded_by').order_by('-payment_date', '-created_at')

        # CSV Export
        if request.GET.get('export') == 'csv':
            response = HttpResponse(content_type='text/csv')
            response['Content-Disposition'] = f'attachment; filename="fee_report_{timezone.localdate()}.csv"'
            writer = csv.writer(response)
            writer.writerow(['Receipt No', 'Date', 'GR Number', 'Student Name', 'Class', 'Amount', 'Payment Method', 'Reference', 'Recorded By'])
            for p in payments:
                writer.writerow([
                    p.receipt_number,
                    p.payment_date.strftime('%Y-%m-%d'),
                    p.student.gr_number,
                    p.student.full_name,
                    f"{p.student.standard.name} - {p.student.division.name}",
                    str(p.amount),
                    p.get_payment_method_display(),
                    p.transaction_reference,
                    p.recorded_by.get_full_name() or p.recorded_by.username,
                ])
            return response

        total_collected = payments.aggregate(t=models.Sum('amount'))['t'] or Decimal('0.00')

        return render(request, 'fees/fee_reports.html', {
            'payments': payments,
            'total_collected': total_collected,
            'academic_years': academic_years,
            'standards': standards,
            'payment_methods': FeePayment.PaymentMethod.choices,
            'current_year': current_year,
            'selected_standard_id': selected_standard_id,
            'selected_method': selected_method,
            'start_date': start_date,
            'end_date': end_date,
        })


# ══════════════════════════════════════════════════════════════════════════════
# 9. Student Portal Fees View
# ══════════════════════════════════════════════════════════════════════════════

class StudentFeePortalView(StudentRequiredMixin, View):
    """
    Student-facing view for checking own fee balance, schedule, breakdown, and receipts.
    """
    def get(self, request):
        user = request.user
        student = getattr(user, 'student_profile', None)

        if not student:
            messages.error(request, "No student profile is linked with this account.")
            return redirect('students:portal')

        summary = FeeService.get_student_fee_summary(student=student)

        return render(request, 'fees/student_fees.html', {
            'student': student,
            'summary': summary,
        })
