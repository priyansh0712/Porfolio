"""
Simplified School Fees Management Views.

Provides:
  - AdminFeesHubView: Unified School Admin fees dashboard (structures, student roster with quick payment, and receipts ledger).
  - FeeExcelTemplateDownloadView: Downloadable .xlsx template generator.
  - FeeExcelUploadView: Bulk class fee structure Excel importer.
  - RecordPaymentView: 1-Click payment recording endpoint.
  - FeeReceiptDetailView: Official printable / downloadable payment slip.
  - StudentPortalFeesView: Clean student portal fee overview with slip download.
"""
from decimal import Decimal, InvalidOperation
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import PermissionDenied, ValidationError
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views import View
from django.views.generic import TemplateView

from apps.accounts.models import User
from apps.accounts.permissions import SchoolAdminRequiredMixin
from apps.academics.models import AcademicYear, Standard, Division
from apps.academics.services import AcademicService
from apps.students.models import Student
from apps.students.views import StudentRequiredMixin
from apps.tenants.features import FeatureService
from apps.fees.models import FeeCategory, FeeStructure, StudentFee, FeePayment
from apps.fees.services import FeeService, FeeExcelService


class FeesFeatureRequiredMixin:
    """
    Enforces that the 'fees' feature is enabled for the current school tenant.
    """
    def dispatch(self, request, *args, **kwargs):
        if hasattr(request, 'tenant') and request.tenant:
            if not FeatureService.is_enabled(request.tenant, 'fees'):
                raise PermissionDenied("The Fees Management feature is disabled for this school.")
        return super().dispatch(request, *args, **kwargs)


class AdminFeesHubView(SchoolAdminRequiredMixin, FeesFeatureRequiredMixin, TemplateView):
    """
    Unified School Admin Fees Management Hub.
    Tabs:
      1. Fee Structures (Class-wise fees, Excel Upload, Template Download)
      2. Student Fee Roster (Search, class filter, Total, Paid, Balance, Record Payment modal)
      3. Payment History & Receipts (All recorded transactions with download links)
    """
    template_name = 'fees/dashboard.html'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        tenant = self.request.tenant
        current_year = AcademicService.get_current_academic_year(tenant)
        ctx['academic_year'] = current_year

        # Active tab
        active_tab = self.request.GET.get('tab', 'students')
        ctx['active_tab'] = active_tab

        # 1. School Fee Metrics
        ctx['metrics'] = FeeService.get_school_fee_metrics(tenant, current_year)

        # 2. Fee Structures
        structures = FeeStructure.objects.filter(
            school=tenant,
            academic_year=current_year,
        ).select_related('standard', 'division').order_by('standard__order_index', 'name')
        ctx['structures'] = structures
        ctx['standards'] = Standard.objects.filter(school=tenant, is_active=True).order_by('order_index')
        ctx['frequencies'] = FeeStructure.Frequency.choices

        # 3. Student Roster with Fee Summaries
        search_q = self.request.GET.get('q', '').strip()
        standard_filter = self.request.GET.get('standard', '').strip()
        status_filter = self.request.GET.get('status', '').strip().upper()

        students_qs = Student.objects.filter(
            school=tenant,
            academic_year=current_year,
            is_active=True,
        ).select_related('standard', 'division', 'user').order_by('standard__order_index', 'division__name', 'roll_number', 'full_name')

        if standard_filter:
            students_qs = students_qs.filter(standard_id=standard_filter)

        if search_q:
            students_qs = students_qs.filter(
                models_q := (
                    from_django_q(search_q)
                )
            )

        student_roster = []
        for s in students_qs:
            summary = FeeService.get_student_fee_summary(student=s, academic_year=current_year)
            if status_filter and summary['status'] != status_filter:
                continue
            student_roster.append({
                'student': s,
                'summary': summary,
            })

        ctx['student_roster'] = student_roster
        ctx['search_query'] = search_q
        ctx['standard_filter'] = standard_filter
        ctx['status_filter'] = status_filter

        # 4. Payment History
        recent_payments = FeePayment.objects.filter(
            school=tenant,
            academic_year=current_year,
            status=FeePayment.Status.SUCCESS,
        ).select_related('student', 'student__standard', 'student__division', 'recorded_by').order_by('-payment_date', '-id')[:100]
        ctx['recent_payments'] = recent_payments
        ctx['payment_methods'] = FeePayment.PaymentMethod.choices

        return ctx

    def post(self, request):
        """
        Handle manual Fee Structure creation or deletion from the admin hub.
        """
        tenant = request.tenant
        current_year = AcademicService.get_current_academic_year(tenant)
        action = request.POST.get('action')

        if action == 'delete_structure':
            struct_id = request.POST.get('structure_id')
            structure = get_object_or_404(FeeStructure, pk=struct_id, school=tenant)
            structure.delete()
            messages.success(request, f"Fee structure '{structure.name}' removed.")
            return redirect(f"{reverse('fees:dashboard')}?tab=structures")

        elif action == 'save_structure':
            standard_id = request.POST.get('standard_id')
            amount_raw = request.POST.get('amount', '0')
            frequency = request.POST.get('payment_frequency', FeeStructure.Frequency.MONTHLY)

            standard = get_object_or_404(Standard, pk=standard_id, school=tenant) if standard_id else None
            try:
                amount = Decimal(amount_raw)
                if amount <= Decimal('0.00'):
                    raise ValueError
            except (InvalidOperation, ValueError):
                messages.error(request, "Please enter a valid positive fee amount.")
                return redirect(f"{reverse('fees:dashboard')}?tab=structures")

            default_cat = FeeService.ensure_default_category(tenant)
            name = f"{standard.name} Annual Fee" if standard else "School Annual Fee"

            structure, _ = FeeStructure.objects.update_or_create(
                school=tenant,
                academic_year=current_year,
                standard=standard,
                defaults={
                    'name': name,
                    'fee_category': default_cat,
                    'amount': amount,
                    'payment_frequency': frequency,
                    'is_active': True,
                }
            )

            # Auto-sync to all enrolled students in class
            FeeService.sync_students_for_structure(tenant, current_year, structure)
            messages.success(request, f"Fee structure for {standard.name if standard else 'All'} saved (₹{amount}).")
            return redirect(f"{reverse('fees:dashboard')}?tab=structures")

        return redirect('fees:dashboard')


def from_django_q(search_term: str):
    from django.db.models import Q
    return (
        Q(full_name__icontains=search_term) |
        Q(gr_number__icontains=search_term) |
        Q(roll_number__icontains=search_term)
    )


class FeeExcelTemplateDownloadView(SchoolAdminRequiredMixin, FeesFeatureRequiredMixin, View):
    """
    Streams downloadable sample Fee Structure Excel template (.xlsx).
    """
    def get(self, request):
        tenant = request.tenant
        current_year = AcademicService.get_current_academic_year(tenant)
        excel_bytes = FeeExcelService.generate_sample_template(tenant, current_year)

        response = HttpResponse(
            excel_bytes,
            content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
        response['Content-Disposition'] = 'attachment; filename="fee_structure_template.xlsx"'
        return response


class FeeExcelUploadView(SchoolAdminRequiredMixin, FeesFeatureRequiredMixin, View):
    """
    POST: Parses and imports the uploaded Fee Structure Excel spreadsheet.
    """
    def post(self, request):
        tenant = request.tenant
        current_year = AcademicService.get_current_academic_year(tenant)

        uploaded_file = request.FILES.get('excel_file')
        if not uploaded_file:
            messages.error(request, "Please select an Excel file (.xlsx or .xls) to upload.")
            return redirect(f"{reverse('fees:dashboard')}?tab=structures")

        result = FeeExcelService.import_fee_structure_excel(
            school=tenant,
            academic_year=current_year,
            file_obj=uploaded_file,
            user=request.user,
        )

        if result['errors']:
            if result['successful'] > 0:
                messages.warning(
                    request,
                    f"Import completed with warnings: {result['successful']} class structures saved, {result['failed']} failed out of {result['total_processed']} rows."
                )
            else:
                messages.error(
                    request,
                    f"Excel import failed ({result['failed']} errors out of {result['total_processed']} rows)."
                )
            for err in result['errors'][:6]:
                messages.error(request, f"• {err}")
            if len(result['errors']) > 6:
                messages.error(request, f"...and {len(result['errors']) - 6} more errors.")
        else:
            messages.success(
                request,
                f"Excel imported successfully! All {result['successful']} class fee structures were created/updated and students synced."
            )

        return redirect(f"{reverse('fees:dashboard')}?tab=structures")


class RecordPaymentView(SchoolAdminRequiredMixin, FeesFeatureRequiredMixin, View):
    """
    POST: Records a fee payment for a student and generates an official receipt.
    """
    def post(self, request):
        tenant = request.tenant
        student_id = request.POST.get('student_id')
        amount_raw = request.POST.get('amount', '0')
        payment_date_raw = request.POST.get('payment_date')
        payment_method = request.POST.get('payment_method', FeePayment.PaymentMethod.CASH)
        transaction_reference = request.POST.get('transaction_reference', '').strip()

        student = get_object_or_404(Student, pk=student_id, school=tenant)

        try:
            amount = Decimal(amount_raw)
            if amount <= Decimal('0.00'):
                raise ValueError
        except (InvalidOperation, ValueError):
            messages.error(request, "Please enter a valid positive payment amount.")
            return redirect('fees:dashboard')

        payment_date = None
        if payment_date_raw:
            try:
                payment_date = timezone.datetime.strptime(payment_date_raw, '%Y-%m-%d').date()
            except ValueError:
                payment_date = timezone.localdate()

        try:
            payment, _ = FeeService.record_payment(
                school=tenant,
                student=student,
                amount=amount,
                payment_date=payment_date,
                payment_method=payment_method,
                transaction_reference=transaction_reference,
                recorded_by=request.user,
            )
            messages.success(
                request,
                f"Payment of ₹{amount:,.2f} recorded for {student.full_name}. Receipt #{payment.receipt_number} generated."
            )
            # Redirect to the printable receipt slip
            return redirect('fees:receipt_detail', pk=payment.pk)
        except ValidationError as e:
            messages.error(request, str(e))
            return redirect('fees:dashboard')


class FeeReceiptDetailView(LoginRequiredMixin, FeesFeatureRequiredMixin, View):
    """
    Displays the official printable / downloadable payment slip.
    Accessible to School Admins and the specific student who made the payment.
    """
    def get(self, request, pk):
        tenant = request.tenant
        payment = get_object_or_404(FeePayment, pk=pk, school=tenant)

        # Enforce Student Privacy
        if request.user.role == User.Role.STUDENT:
            student_profile = getattr(request.user, 'student_profile', None)
            if not student_profile or payment.student_id != student_profile.id:
                raise PermissionDenied("You can only view and download your own payment receipts.")
        elif request.user.role not in [User.Role.SUPER_ADMIN, User.Role.SCHOOL_ADMIN]:
            raise PermissionDenied("You do not have authorization to view this receipt.")

        summary = FeeService.get_student_fee_summary(payment.student, payment.academic_year)

        return render(request, 'fees/receipt_detail.html', {
            'payment': payment,
            'summary': summary,
            'school': tenant,
        })


class StudentPortalFeesView(StudentRequiredMixin, FeesFeatureRequiredMixin, TemplateView):
    """
    Student Portal Fees Dashboard: Total Fee, Paid, Remaining, Frequency, Status, and Payment History with Slip Download.
    """
    template_name = 'fees/student_fees.html'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        student = getattr(self.request.user, 'student_profile', None)
        ctx['student'] = student

        if student:
            summary = FeeService.get_student_fee_summary(student)
            ctx['summary'] = summary

        return ctx
