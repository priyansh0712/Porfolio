from django import forms
from django.core.exceptions import ValidationError
from django.db.models import Q
from datetime import date

from apps.leaves.models import LeaveRequest, LeaveAllocation, LeaveType


class LeaveRequestForm(forms.ModelForm):
    """
    Form for Faculty members to apply for leaves.
    Includes custom validation for date bounds, conflicts/overlaps, and balance checks.
    """
    class Meta:
        model = LeaveRequest
        fields = ['leave_type', 'from_date', 'to_date', 'reason']
        widgets = {
            'leave_type': forms.Select(attrs={
                'class': 'w-full px-4 py-2.5 rounded-xl border border-gray-200/80 bg-white text-[#1d1d1f] text-sm focus:outline-none focus:ring-2 focus:ring-[#0066cc]/30 focus:border-[#0066cc] transition-all',
            }),
            'from_date': forms.DateInput(attrs={
                'class': 'w-full px-4 py-2.5 rounded-xl border border-gray-200/80 bg-white text-[#1d1d1f] text-sm focus:outline-none focus:ring-2 focus:ring-[#0066cc]/30 focus:border-[#0066cc] transition-all',
                'type': 'date',
            }),
            'to_date': forms.DateInput(attrs={
                'class': 'w-full px-4 py-2.5 rounded-xl border border-gray-200/80 bg-white text-[#1d1d1f] text-sm focus:outline-none focus:ring-2 focus:ring-[#0066cc]/30 focus:border-[#0066cc] transition-all',
                'type': 'date',
            }),
            'reason': forms.Textarea(attrs={
                'class': 'w-full px-4 py-2.5 rounded-xl border border-gray-200/80 bg-white text-[#1d1d1f] text-sm focus:outline-none focus:ring-2 focus:ring-[#0066cc]/30 focus:border-[#0066cc] transition-all placeholder:text-[#86868b]',
                'rows': 3,
                'placeholder': 'Provide a brief reason for your leave request...',
            }),
        }

    def __init__(self, *args, **kwargs):
        self.faculty = kwargs.pop('faculty', None)
        self.school = kwargs.pop('school', None)
        super().__init__(*args, **kwargs)

        if self.faculty and self.school:
            choices = [('', '---------')]
            for l_type, l_label in LeaveType.choices:
                alloc = LeaveAllocation.objects.filter(
                    school=self.school,
                    faculty=self.faculty,
                    leave_type=l_type
                ).first()
                allocated = alloc.allocated if alloc else 0

                approved_requests = LeaveRequest.objects.filter(
                    school=self.school,
                    faculty=self.faculty,
                    leave_type=l_type,
                    status=LeaveRequest.Status.APPROVED
                )
                used = sum(r.used_days for r in approved_requests)
                remaining = max(0, allocated - used)
                choices.append((l_type, f"{l_label} ({remaining} remaining)"))

            self.fields['leave_type'].choices = choices

    def clean(self):
        cleaned_data = super().clean()
        from_date = cleaned_data.get('from_date')
        to_date = cleaned_data.get('to_date')
        leave_type = cleaned_data.get('leave_type')

        if not from_date or not to_date or not leave_type:
            return cleaned_data

        # 1. Date order validation
        if from_date > to_date:
            raise ValidationError({
                'from_date': "From Date cannot be after To Date."
            })

        # 2. Overlap validation
        # Find any other pending or approved requests that intersect this date range
        overlap_query = LeaveRequest.objects.filter(
            school=self.school,
            faculty=self.faculty,
            status__in=[LeaveRequest.Status.PENDING, LeaveRequest.Status.APPROVED]
        ).filter(
            Q(from_date__lte=to_date, to_date__gte=from_date)
        )

        if self.instance and self.instance.pk:
            overlap_query = overlap_query.exclude(pk=self.instance.pk)

        if overlap_query.exists():
            raise ValidationError(
                "This leave request overlaps with another pending or approved request."
            )

        # 3. Leave balance validation
        # Find total allocated
        alloc = LeaveAllocation.objects.filter(
            school=self.school,
            faculty=self.faculty,
            leave_type=leave_type
        ).first()
        allocated = alloc.allocated if alloc else 0

        # Calculate used balance: sum of duration in days for approved leaves
        approved_requests = LeaveRequest.objects.filter(
            school=self.school,
            faculty=self.faculty,
            leave_type=leave_type,
            status=LeaveRequest.Status.APPROVED
        )
        if self.instance and self.instance.pk:
            approved_requests = approved_requests.exclude(pk=self.instance.pk)

        used = sum(r.used_days for r in approved_requests)
        remaining = allocated - used

        # Create temporary instance to calculate requested working days count
        temp_req = LeaveRequest(
            school=self.school,
            faculty=self.faculty,
            from_date=from_date,
            to_date=to_date
        )
        requested = temp_req.used_days

        if requested == 0:
            raise ValidationError(
                "The selected date range does not contain any scheduled working days."
            )

        if requested > remaining:
            raise ValidationError(
                f"Insufficient leave balance for {dict(LeaveType.choices).get(leave_type)}. "
                f"Requested: {requested} days. Remaining: {remaining} days (Allocated: {allocated}, Used: {used})."
            )

        return cleaned_data
