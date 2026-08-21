# Phase 4 Research — Faculty Dashboards, Password Security & Integration Polish

## 1. Faculty Views Specifications

### A. "My Class" Dashboard (`MyClassView`)
- **Route**: `/faculty/my-class/`
- **Access**: Faculty role with active Class Teacher assignment in current Academic Year.
- **Data Query**:
  ```python
  curr_ay = AcademicYear.objects.filter(school=request.tenant, is_current=True).first()
  allocation = ClassTeacherAllocation.objects.filter(
      school=request.tenant,
      academic_year=curr_ay,
      faculty=request.user.faculty_profile
  ).select_related('division', 'division__standard').first()
  ```
- **Roster Query**:
  ```python
  students = Student.objects.filter(
      school=request.tenant,
      academic_year=curr_ay,
      division=allocation.division,
      is_active=True
  ).order_index()
  ```

### B. "My Subjects" View (`MySubjectsView`)
- **Route**: `/faculty/my-subjects/`
- **Access**: Faculty role.
- **Data Query**:
  ```python
  curr_ay = AcademicYear.objects.filter(school=request.tenant, is_current=True).first()
  allocations = SubjectTeacherAllocation.objects.filter(
      school=request.tenant,
      academic_year=curr_ay,
      faculty=request.user.faculty_profile
  ).select_related('division', 'division__standard', 'subject')
  ```

---

## 2. Password Security Specifications

### Self-Service Password Change (`SelfPasswordChangeView`)
- **Route**: `/accounts/password/change/`
- **Form**: Built-in `django.contrib.auth.forms.PasswordChangeForm(user=request.user, data=request.POST)`
- **Success Action**:
  ```python
  from django.contrib.auth import update_session_auth_hash
  update_session_auth_hash(request, form.user)
  messages.success(request, 'Your password was successfully updated!')
  ```

---

## 3. Plan Decomposition

- **`04-01-PLAN.md`**: Faculty Dashboards ("My Class" and "My Subjects" views, templates, navigation links).
- **`04-02-PLAN.md`**: Self-service Password Change view, templates, permission decorators, and full project security test suite.
