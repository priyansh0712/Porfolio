"""
Bulk Onboarding Service Layer — Sample Template Generator, Parsers, Validation Engine & Atomic Committers.
"""
import csv
import io
import re
import logging
from datetime import datetime
import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment

from django.db import transaction
from django.utils import timezone

from apps.accounts.models import User
from apps.faculty.models import Faculty, FacultyCustomField
from apps.academics.models import (
    AcademicYear, Standard, Division, Subject,
    ClassTeacherAllocation, SubjectTeacherAllocation
)
from apps.students.models import Student, StudentCustomField

logger = logging.getLogger(__name__)

# Standard Headers per Step
STEP_HEADERS = {
    1: ['First Name', 'Last Name', 'Email', 'Employee Code', 'Department', 'Designation'],
    2: ['Standard Name', 'Standard Code', 'Division Name', 'Class Teacher Employee Code'],
    3: ['Standard Name', 'Division Name', 'Subject Name', 'Subject Code', 'Subject Teacher Employee Code'],
    4: ['GR Number', 'First Name', 'Last Name', 'Standard Name', 'Division Name', 'Roll Number', 'Gender', 'Date of Birth', 'Parent Phone', 'Parent Email'],
}

STEP_SAMPLE_DATA = {
    1: [
        ['John', 'Smith', 'john.smith@school.edu', 'FAC-001', 'Science', 'Senior Physics Teacher'],
        ['Sarah', 'Connor', 'sarah.c@school.edu', 'FAC-002', 'Mathematics', 'Head of Maths'],
    ],
    2: [
        ['Grade 10', 'STD-10', 'A', 'FAC-001'],
        ['Grade 10', 'STD-10', 'B', 'FAC-002'],
    ],
    3: [
        ['Grade 10', 'A', 'Physics', 'PHY-10', 'FAC-001'],
        ['Grade 10', 'A', 'Algebra', 'ALG-10', 'FAC-002'],
    ],
    4: [
        ['GR-1001', 'Alex', 'Taylor', 'Grade 10', 'A', '1', 'Male', '2010-05-15', '9876543210', 'parent1@gmail.com'],
        ['GR-1002', 'Emily', 'Davis', 'Grade 10', 'A', '2', 'Female', '2010-08-20', '9876543211', 'parent2@gmail.com'],
    ],
}


class SampleTemplateService:
    """Generates pre-formatted downloadable sample templates (.xlsx & .csv)."""

    @classmethod
    def get_template_headers_and_data(cls, step, school=None):
        headers = list(STEP_HEADERS.get(step, []))
        raw_samples = STEP_SAMPLE_DATA.get(step, [])
        sample_rows = [list(row) for row in raw_samples]

        if school and step == 1:
            custom_fields = list(FacultyCustomField.objects.filter(school=school, is_active=True).order_by('order_index', 'created_at'))
            for cf in custom_fields:
                headers.append(cf.label)
                for idx, row in enumerate(sample_rows):
                    if cf.field_type == FacultyCustomField.FieldType.NUMBER:
                        val = '100' if idx == 0 else '101'
                    elif cf.field_type == FacultyCustomField.FieldType.DATE:
                        val = '2026-01-01'
                    elif cf.field_type == FacultyCustomField.FieldType.SELECT:
                        options = [o.strip() for o in cf.options.split(',') if o.strip()]
                        val = options[0] if options else 'Option1'
                    else:
                        val = f"Sample {cf.label}"
                    row.append(val)
        elif school and step == 4:
            custom_fields = list(StudentCustomField.objects.filter(school=school, is_active=True).order_by('order_index', 'created_at'))
            for cf in custom_fields:
                headers.append(cf.label)
                for idx, row in enumerate(sample_rows):
                    if cf.field_type == StudentCustomField.FieldType.NUMBER:
                        val = '100' if idx == 0 else '101'
                    elif cf.field_type == StudentCustomField.FieldType.DATE:
                        val = '2026-01-01'
                    elif cf.field_type == StudentCustomField.FieldType.SELECT:
                        options = [o.strip() for o in cf.options.split(',') if o.strip()]
                        val = options[0] if options else 'Option1'
                    else:
                        val = f"Sample {cf.label}"
                    row.append(val)
        return headers, sample_rows

    @classmethod
    def generate_csv(cls, step, school=None):
        headers, sample_rows = cls.get_template_headers_and_data(step, school)

        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(headers)
        for row in sample_rows:
            writer.writerow(row)
        return output.getvalue().encode('utf-8')

    @classmethod
    def generate_xlsx(cls, step, school=None):
        headers, sample_rows = cls.get_template_headers_and_data(step, school)

        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = f"Step {step} Sample Import"

        # Styled Header Row
        header_font = Font(name='Segoe UI', size=11, bold=True, color='FFFFFF')
        header_fill = PatternFill(start_color='0066CC', end_color='0066CC', fill_type='solid')
        header_align = Alignment(horizontal='center', vertical='center')

        ws.append(headers)
        for col_num in range(1, len(headers) + 1):
            cell = ws.cell(row=1, column=col_num)
            cell.font = header_font
            cell.fill = header_fill
            cell.alignment = header_align
            ws.column_dimensions[openpyxl.utils.get_column_letter(col_num)].width = 22

        # Data Rows
        for row in sample_rows:
            ws.append(row)

        output = io.BytesIO()
        wb.save(output)
        return output.getvalue()


class BulkImportParser:
    """Parses .xlsx and .csv files into raw row dictionaries."""

    @classmethod
    def parse(cls, file_obj, filename):
        filename_lower = filename.lower()
        if filename_lower.endswith('.xlsx') or filename_lower.endswith('.xls'):
            return cls._parse_xlsx(file_obj)
        else:
            return cls._parse_csv(file_obj)

    @classmethod
    def _parse_xlsx(cls, file_obj):
        wb = openpyxl.load_workbook(file_obj, data_only=True)
        ws = wb.active
        rows = list(ws.iter_rows(values_only=True))
        if not rows or len(rows) < 2:
            return []

        raw_headers = [str(h).strip() for h in rows[0] if h is not None]
        data_rows = []
        for r_idx, row in enumerate(rows[1:], start=2):
            if not any(row):
                continue
            row_dict = {}
            for h_idx, h in enumerate(raw_headers):
                val = row[h_idx] if h_idx < len(row) else ''
                row_dict[h] = str(val).strip() if val is not None else ''
            data_rows.append((r_idx, row_dict))
        return data_rows

    @classmethod
    def _parse_csv(cls, file_obj):
        content = file_obj.read()
        try:
            text = content.decode('utf-8-sig')
        except UnicodeDecodeError:
            text = content.decode('latin-1')

        reader = csv.reader(io.StringIO(text))
        rows = list(reader)
        if not rows or len(rows) < 2:
            return []

        headers = [h.strip() for h in rows[0] if h.strip()]
        data_rows = []
        for r_idx, row in enumerate(rows[1:], start=2):
            if not any(row):
                continue
            row_dict = {}
            for h_idx, h in enumerate(headers):
                val = row[h_idx] if h_idx < len(row) else ''
                row_dict[h] = val.strip()
            data_rows.append((r_idx, row_dict))
        return data_rows


class BulkValidationService:
    """Multi-tenant scoped row-by-row validation engine."""

    @classmethod
    def validate(cls, school, step, raw_rows):
        if step == 1:
            return cls._validate_step_1_faculty(school, raw_rows)
        elif step == 2:
            return cls._validate_step_2_classes(school, raw_rows)
        elif step == 3:
            return cls._validate_step_3_subjects(school, raw_rows)
        elif step == 4:
            return cls._validate_step_4_students(school, raw_rows)
        return []

    @classmethod
    def _validate_step_1_faculty(cls, school, raw_rows):
        existing_emails = set(Faculty.objects.filter(school=school).values_list('email', flat=True))
        existing_codes = set(Faculty.objects.filter(school=school).values_list('employee_code', flat=True))
        custom_fields = list(FacultyCustomField.objects.filter(school=school, is_active=True))

        seen_emails = set()
        seen_codes = set()
        results = []

        for r_idx, row in raw_rows:
            errors = []
            first_name = row.get('First Name', '')
            last_name = row.get('Last Name', '')
            email = row.get('Email', '').lower()
            code = row.get('Employee Code', '').upper()

            if not first_name:
                errors.append("First Name is required")
            if not last_name:
                errors.append("Last Name is required")
            if not email or '@' not in email:
                errors.append("Valid Email is required")
            elif email in existing_emails:
                errors.append(f"Email '{email}' already registered")
            elif email in seen_emails:
                errors.append(f"Duplicate email '{email}' in import file")

            if not code:
                errors.append("Employee Code is required")
            elif code in existing_codes:
                errors.append(f"Employee Code '{code}' already exists")
            elif code in seen_codes:
                errors.append(f"Duplicate Employee Code '{code}' in import file")

            # Custom Field Validation for required fields
            for cf in custom_fields:
                val = row.get(cf.label)
                if cf.is_required and (val is None or str(val).strip() == ''):
                    errors.append(f"Custom Field '{cf.label}' is required")

            if email:
                seen_emails.add(email)
            if code:
                seen_codes.add(code)

            results.append({
                'row_index': r_idx,
                'data': row,
                'status': 'ERROR' if errors else 'VALID',
                'errors': errors,
            })
        return results

    @classmethod
    def _validate_step_2_classes(cls, school, raw_rows):
        curr_ay = AcademicYear.objects.filter(school=school, is_current=True).first()
        faculty_map = {f.employee_code.upper(): f for f in Faculty.objects.filter(school=school, is_active=True)}
        assigned_teachers = set(
            ClassTeacherAllocation.objects.filter(school=school, academic_year=curr_ay)
            .values_list('faculty__employee_code', flat=True)
        ) if curr_ay else set()

        results = []
        for r_idx, row in raw_rows:
            errors = []
            std_name = row.get('Standard Name', '')
            div_name = row.get('Division Name', '')
            teacher_code = row.get('Class Teacher Employee Code', '').upper()

            if not std_name:
                errors.append("Standard Name is required")
            if not div_name:
                errors.append("Division Name is required")

            if teacher_code:
                if teacher_code not in faculty_map:
                    errors.append(f"Teacher Code '{teacher_code}' not found in school faculty roster")
                elif teacher_code in assigned_teachers:
                    errors.append(f"Teacher '{teacher_code}' is already assigned as Class Teacher elsewhere")

            results.append({
                'row_index': r_idx,
                'data': row,
                'status': 'ERROR' if errors else 'VALID',
                'errors': errors,
            })
        return results

    @classmethod
    def _validate_step_3_subjects(cls, school, raw_rows):
        divisions = {
            (d.standard.name.upper(), d.name.upper()): d
            for d in Division.objects.filter(school=school).select_related('standard')
        }

        faculty_map = {f.employee_code.upper(): f for f in Faculty.objects.filter(school=school, is_active=True)}

        results = []
        for r_idx, row in raw_rows:
            errors = []
            std_name = row.get('Standard Name', '').upper()
            div_name = row.get('Division Name', '').upper()
            sub_name = row.get('Subject Name', '')
            teacher_code = row.get('Subject Teacher Employee Code', '').upper()

            if not std_name or not div_name:
                errors.append("Standard Name and Division Name are required")
            elif (std_name, div_name) not in divisions:
                errors.append(f"Class '{std_name} {div_name}' does not exist. Please run Step 2 first.")

            if not sub_name:
                errors.append("Subject Name is required")

            if not teacher_code:
                errors.append("Subject Teacher Employee Code is required")
            elif teacher_code not in faculty_map:
                errors.append(f"Subject Teacher Code '{teacher_code}' not found in faculty roster")

            results.append({
                'row_index': r_idx,
                'data': row,
                'status': 'ERROR' if errors else 'VALID',
                'errors': errors,
            })
        return results

    @classmethod
    def _validate_step_4_students(cls, school, raw_rows):
        existing_grs = set(Student.objects.filter(school=school).values_list('gr_number', flat=True))
        divisions = {
            (d.standard.name.upper(), d.name.upper()): d
            for d in Division.objects.filter(school=school).select_related('standard')
        }
        custom_fields = list(StudentCustomField.objects.filter(school=school, is_active=True))

        seen_grs = set()
        seen_rolls = set()
        results = []

        for r_idx, row in raw_rows:
            errors = []
            gr_number = str(row.get('GR Number', '') or '').strip().upper()
            first_name = str(row.get('First Name', '') or '').strip()
            last_name = str(row.get('Last Name', '') or '').strip()
            std_name = str(row.get('Standard Name', '') or '').strip().upper()
            div_name = str(row.get('Division Name', '') or '').strip().upper()
            roll_number = str(row.get('Roll Number', '') or '').strip()

            if not gr_number:
                errors.append("GR Number is required")
            elif gr_number in existing_grs:
                errors.append(f"GR Number '{gr_number}' already exists in school")
            elif gr_number in seen_grs:
                errors.append(f"Duplicate GR Number '{gr_number}' in file")

            if not first_name or not last_name:
                errors.append("First Name and Last Name are required")

            if not std_name or not div_name:
                errors.append("Standard Name and Division Name are required")
            elif (std_name, div_name) not in divisions:
                errors.append(f"Class '{std_name} {div_name}' does not exist. Please run Step 2 first.")
            else:
                div_obj = divisions[(std_name, div_name)]
                if roll_number:
                    roll_key = (div_obj.id, roll_number)
                    if roll_key in seen_rolls:
                        errors.append(f"Duplicate Roll Number '{roll_number}' in Class {std_name} {div_name}")
                    seen_rolls.add(roll_key)

            # Custom Field Validation for required fields
            for cf in custom_fields:
                val = row.get(cf.label)
                if cf.is_required and (val is None or str(val).strip() == ''):
                    errors.append(f"Custom Field '{cf.label}' is required")

            if gr_number:
                seen_grs.add(gr_number)

            results.append({
                'row_index': r_idx,
                'data': row,
                'status': 'ERROR' if errors else 'VALID',
                'errors': errors,
            })
        return results


class BulkCommitService:
    """Executes atomic database transactions for validated rows."""

    @classmethod
    @transaction.atomic
    def commit_step_1_faculty(cls, school, valid_rows, default_password='Admin@123'):
        custom_fields = list(FacultyCustomField.objects.filter(school=school, is_active=True))

        count = 0
        for item in valid_rows:
            row = item['data']
            email = str(row['Email']).strip().lower()
            code = str(row['Employee Code']).strip().upper()

            # Extract Custom Field Values
            custom_data = {}
            for cf in custom_fields:
                val = row.get(cf.label)
                if val is not None and str(val).strip() != '':
                    custom_data[cf.field_name] = str(val).strip()

            faculty = Faculty.objects.create(
                school=school,
                first_name=str(row['First Name']).strip(),
                last_name=str(row['Last Name']).strip(),
                email=email,
                employee_code=code,
                department=str(row.get('Department', '')).strip(),
                designation=str(row.get('Designation', '')).strip(),
                custom_fields=custom_data,
                is_active=True,
            )

            # Auto-create User account
            user = User.objects.create_user(
                username=email,
                email=email,
                password=default_password,
                first_name=str(row['First Name']).strip(),
                last_name=str(row['Last Name']).strip(),
                role=User.Role.FACULTY,
                school=school,
            )
            faculty.user = user
            faculty.save()
            count += 1
        return count

    @classmethod
    @transaction.atomic
    def commit_step_2_classes(cls, school, valid_rows):
        curr_ay, _ = AcademicYear.objects.get_or_create(
            school=school,
            is_current=True,
            defaults={'name': 'Current Academic Year', 'start_date': timezone.now().date(), 'end_date': timezone.now().date()}
        )
        faculty_map = {f.employee_code.upper(): f for f in Faculty.objects.filter(school=school, is_active=True)}
        count = 0

        for item in valid_rows:
            row = item['data']
            std_name = row['Standard Name']
            std_code = row.get('Standard Code') or std_name.upper().replace(' ', '-')
            div_name = row['Division Name']
            teacher_code = row.get('Class Teacher Employee Code', '').upper()

            standard, _ = Standard.objects.get_or_create(
                school=school,
                name=std_name
            )

            division, _ = Division.objects.get_or_create(
                school=school,
                standard=standard,
                name=div_name
            )

            if teacher_code and teacher_code in faculty_map:
                faculty = faculty_map[teacher_code]
                ClassTeacherAllocation.objects.update_or_create(
                    school=school,
                    academic_year=curr_ay,
                    division=division,
                    defaults={'faculty': faculty}
                )
            count += 1
        return count

    @classmethod
    @transaction.atomic
    def commit_step_3_subjects(cls, school, valid_rows):
        curr_ay = AcademicYear.objects.filter(school=school, is_current=True).first()
        faculty_map = {f.employee_code.upper(): f for f in Faculty.objects.filter(school=school, is_active=True)}
        divisions = {
            (d.standard.name.upper(), d.name.upper()): d
            for d in Division.objects.filter(school=school).select_related('standard')
        }

        count = 0
        for item in valid_rows:
            row = item['data']
            std_name = row['Standard Name'].upper()
            div_name = row['Division Name'].upper()
            sub_name = row['Subject Name']
            sub_code = row.get('Subject Code') or sub_name.upper()[:6]
            teacher_code = row['Subject Teacher Employee Code'].upper()

            div_obj = divisions.get((std_name, div_name))
            if not div_obj:
                continue

            subject, _ = Subject.objects.get_or_create(
                school=school,
                code=sub_code,
                defaults={'name': sub_name}
            )

            faculty = faculty_map[teacher_code]
            SubjectTeacherAllocation.objects.update_or_create(
                school=school,
                academic_year=curr_ay,
                division=div_obj,
                subject=subject,
                faculty=faculty,
            )
            count += 1
        return count

    @classmethod
    @transaction.atomic
    def commit_step_4_students(cls, school, valid_rows, default_password='Admin@123'):
        curr_ay = AcademicYear.objects.filter(school=school, is_current=True).first()
        divisions = {
            (d.standard.name.upper(), d.name.upper()): d
            for d in Division.objects.filter(school=school).select_related('standard')
        }
        custom_fields = list(StudentCustomField.objects.filter(school=school, is_active=True))

        count = 0
        for item in valid_rows:
            row = item['data']
            gr_number = str(row.get('GR Number', '') or '').strip().upper()
            std_name = str(row.get('Standard Name', '') or '').strip().upper()
            div_name = str(row.get('Division Name', '') or '').strip().upper()

            div_obj = divisions.get((std_name, div_name))
            if not div_obj:
                continue

            dob = None
            if row.get('Date of Birth'):
                try:
                    dob = datetime.strptime(str(row['Date of Birth']).strip(), '%Y-%m-%d').date()
                except ValueError:
                    pass

            roll_num = int(row['Roll Number']) if row.get('Roll Number') and str(row['Roll Number']).isdigit() else None

            # Extract Custom Field Values
            custom_data = {}
            for cf in custom_fields:
                val = row.get(cf.label)
                if val is not None and str(val).strip() != '':
                    custom_data[cf.field_name] = str(val).strip()

            student = Student.objects.create(
                school=school,
                academic_year=curr_ay,
                standard=div_obj.standard,
                division=div_obj,
                gr_number=gr_number,
                full_name=f"{row.get('First Name', '')} {row.get('Last Name', '')}".strip(),
                roll_number=roll_num,
                gender=str(row.get('Gender', 'MALE')).strip().upper(),
                dob=dob,
                guardian_phone=str(row.get('Parent Phone', '')).strip(),
                custom_fields=custom_data,
                is_active=True,
            )

            # Auto-create Student User login
            user = User.objects.create_user(
                username=gr_number,
                email=str(row.get('Parent Email') or f"{gr_number.lower()}@student.school").strip(),
                password=default_password,
                first_name=str(row.get('First Name', '')).strip(),
                last_name=str(row.get('Last Name', '')).strip(),
                role=User.Role.STUDENT,
                school=school,
            )
            student.user = user
            student.save()
            count += 1
        return count
