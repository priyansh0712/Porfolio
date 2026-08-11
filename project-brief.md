I want you to initialize a production-minded SaaS startup project using the GSD workflow.

Act as:
- Senior Product Architect
- Senior Django Architect
- Senior SaaS/Multi-Tenant Architect
- Senior Face Recognition System Architect
- Senior Security Engineer
- Senior UX/UI Architect
- Senior GSD Engineer
- Senior Prompt Engineer

Do NOT rush into implementation.
First understand the product completely, challenge weak assumptions, identify missing requirements, research critical technical/domain questions where useful, then produce a clean V1 scope and phased roadmap.

==================================================
PRODUCT VISION
==================================================

We are building a SaaS platform for schools.

The initial product is a FACE-BASED FACULTY ATTENDANCE SYSTEM.

The first version must solve ONE core problem extremely well:

"Allow school faculty to mark accurate check-in and check-out attendance using face recognition through a webcam, while giving the school's authorized administrator complete attendance management and reporting."

This is a startup product, not a college demo.

The architecture must therefore be designed so that multiple independent schools can use the same SaaS platform without exposing one school's data to another.

==================================================
IMPORTANT PRODUCT SCOPE
==================================================

V1 ONLY focuses on faculty attendance.

DO NOT implement or plan detailed V1 functionality for:
- Student attendance
- Student management
- School bus tracking
- Parent notifications
- Fees
- Payroll
- LMS
- Exams
- Chatbot
- Mobile applications
- Unnecessary AI features

These may be future product directions, but they are OUT OF SCOPE for V1.

Do, however, keep the architecture extensible enough that future modules can be added without rewriting the core system.

==================================================
USER JOURNEY / WEBSITE STRUCTURE
==================================================

There are two major experiences.

1. OUR COMPANY / PUBLIC PLATFORM

When someone opens the main website:

ourapp.com

they should see the company's public landing page.

The landing page should communicate:
- What the product does
- Why schools need it
- Face-based faculty attendance
- Benefits
- How it works
- Security/privacy positioning
- Product features
- Pricing area or pricing-ready structure
- FAQ
- Contact/CTA

Primary CTA:
"Register Your School"

There should also be a school/admin login entry point.

--------------------------------------------------

2. SCHOOL-SPECIFIC EXPERIENCE

After a school registers, it gets its own tenant-specific environment.

Preferred URL model:

schoolname.ourapp.com

The exact subdomain implementation should be researched and planned properly.

Each school's environment must be isolated from every other school's environment.

Example:

schoola.ourapp.com
schoolb.ourapp.com

School A must NEVER be able to access School B's:
- Faculty
- Attendance
- Face/biometric data
- Settings
- Reports
- Other private information

==================================================
SCHOOL REGISTRATION
==================================================

A school should be able to register through the public company website.

Initial registration information may include:
- School name
- School email
- School phone
- School address
- Admin name
- Admin email
- Password
- Other fields only if genuinely required

After successful registration:
- Create the school tenant
- Create its authorized school administrator
- Initialize default school settings
- Prepare the school's tenant-specific environment
- Redirect/access the school-specific experience

Do not add unnecessary onboarding complexity.

==================================================
ROLES AND ACCESS CONTROL
==================================================

V1 should have a minimal and strict role model.

ROLE 1: PLATFORM / SUPER ADMIN

The platform's Super Admin manages the SaaS platform and schools at the platform level.

Super Admin MAY manage:
- School registration/account lifecycle
- School activation/deactivation
- Subscription/account status if included
- Basic platform-level school metadata
- Platform configuration/support operations

Super Admin MUST NOT have normal access to:
- Individual faculty records
- Faculty attendance records
- Faculty face data / biometric templates
- School private operational data

This is a deliberate privacy/product requirement.

Do NOT create a Super Admin dashboard that casually exposes customer data.

ROLE 2: SCHOOL ADMIN

Each school has its own administrator.

School Admin can access ONLY their own school's data.

School Admin can:
- Add faculty
- Edit faculty
- Remove/deactivate faculty
- Register faculty face
- View faculty list
- View today's attendance
- View attendance history
- View attendance reports
- Configure working days
- Configure working hours
- Configure late rules
- Configure half-day rules
- Manage school settings

ROLE 3: FACULTY

Faculty access must be restricted to their own identity and attendance.

Faculty can:
- Use face-based attendance
- Check in
- Check out
- View their own attendance
- View their own attendance history
- View their own profile where appropriate

Faculty MUST NOT:
- View another faculty member's data
- Modify attendance
- Access school administration
- Access face-registration management

==================================================
AUTHENTICATION
==================================================

FACULTY:
The intended attendance interaction is FACE-BASED.

Do not assume a traditional faculty password dashboard is required unless research or architecture identifies a strong reason.

Expected attendance flow:

Camera
→ Face Detection
→ Face Processing
→ Face Recognition / Matching
→ Identify Faculty
→ Check Attendance State
→ Apply Attendance Rules
→ Record Check-in OR Check-out

SCHOOL ADMIN:
Use secure conventional authentication such as:
- Email + password

Do NOT make Admin dependent exclusively on face recognition.

SUPER ADMIN:
Use secure conventional authentication.

Authentication, authorization, session handling, CSRF protection, password security and access control must follow Django security best practices.

==================================================
CAMERA / FACE RECOGNITION
==================================================

Production hardware will be standard webcam devices.

During development/testing:
Use the laptop's built-in webcam.

Browser camera access may require minimal Vanilla JavaScript using browser camera APIs.

Frontend framework:
DO NOT use React.
DO NOT use Vue.
DO NOT use Angular.

Use:
- Django templates
- Tailwind CSS
- Minimal Vanilla JavaScript where browser APIs require it

Backend:
Django.

Database:
PostgreSQL.

Deployment:
Cloud.

No unnecessary frontend framework.

==================================================
FACE REGISTRATION
==================================================

School Admin manually registers each faculty member.

Expected flow:

School Admin
→ Add Faculty
→ Enter faculty information
→ Open face registration
→ Webcam access
→ Capture/process face
→ Generate appropriate face representation/embedding
→ Securely store the biometric representation
→ Associate it with that faculty and school

Do NOT blindly choose a face-recognition library just because it is popular.

Research and evaluate suitable approaches based on:
- Accuracy
- Reliability
- Python/Django compatibility
- CPU requirements
- Cloud deployment practicality
- Licensing
- Privacy implications
- Performance
- Maintainability
- Spoofing/liveness considerations

The selected approach must be justified in the research/architecture.

Avoid storing raw face images permanently unless there is a clearly justified requirement.

Prefer secure biometric representations/embeddings where appropriate.

==================================================
ATTENDANCE RULES
==================================================

Both CHECK-IN and CHECK-OUT are required.

Default conceptual flow:

Faculty arrives
→ Face verification
→ If today's check-in does not exist
→ Create check-in

Later:

Faculty leaves
→ Face verification
→ If check-in exists and check-out does not exist
→ Create check-out

Prevent duplicate attendance.

A faculty member should not be able to create unlimited check-ins/check-outs by repeatedly scanning.

The business rules must explicitly define:
- First valid scan
- Duplicate scan
- Check-in after check-out
- Missing check-out
- Invalid face
- Unknown face
- Multiple matching candidates
- Face recognition failure
- Manual correction
- Late arrival
- Early departure
- Half day
- Holiday
- Non-working day

==================================================
SCHOOL WORKING SCHEDULE
==================================================

Working schedule MUST be configurable independently for each school.

It must support different schedules for different days.

Example:

Monday:
08:00 - 16:00 → Full Day

Tuesday:
08:00 - 16:00 → Full Day

Saturday:
08:00 - 12:30 → Half Day

Sunday:
Holiday

The system must NOT hard-code Monday-Friday as the only working schedule.

School Admin should configure:
- Working/non-working day
- Start time
- End time
- Full day / half day
- Late threshold / grace period
- Other attendance rules genuinely required

There should be a way to handle date-specific exceptions later/where required, such as:
- Holiday
- Special working day
- Different schedule for a particular date

Design this carefully without overengineering V1.

==================================================
LATE ATTENDANCE
==================================================

Late rules are configurable by School Admin.

Example:

Start time = 08:00
Grace period = 10 minutes

07:55 → Present
08:07 → Present
08:11 → Late

Do not hard-code these values.

The exact rule model should be defined during requirements/architecture discussion.

==================================================
ATTENDANCE INTEGRITY
==================================================

Attendance data is business-critical.

Once an attendance record exists, it should not be casually editable.

If School Admin is allowed to correct attendance:
- Preserve original value
- Store corrected value
- Store who changed it
- Store timestamp
- Store reason
- Keep an audit trail

No silent data modification.

Database constraints and application-level business rules should both protect attendance integrity.

==================================================
MULTI-TENANCY
==================================================

This is a CRITICAL architectural requirement.

The application must support multiple schools.

Every tenant-owned entity must be associated with the correct school/tenant.

Examples:
- Faculty
- Attendance
- Face representations
- School settings
- Working schedules
- Audit records
- Reports

Tenant isolation must be enforced at the backend/application/data-access layer.

DO NOT rely only on:
- Hidden UI buttons
- URL patterns
- Frontend filtering

A malicious request must not be able to access another school's records by changing an ID.

Subdomain-based tenant resolution should be evaluated and implemented securely.

==================================================
PRIVACY / SECURITY
==================================================

This system processes biometric/face-related data.

Treat this as a security-critical area.

Research and design for:
- Data minimization
- Secure storage
- Encryption where appropriate
- Access control
- Tenant isolation
- Audit logging
- Secure deletion/deactivation
- Secrets management
- HTTPS
- CSRF
- XSS
- SQL injection prevention
- Authentication security
- Authorization
- Rate limiting where appropriate
- Secure camera/browser handling
- Biometric data retention considerations

Do not make unsupported legal/compliance claims.

Identify privacy/compliance questions that require professional/legal validation before production deployment.

==================================================
UI / UX
==================================================

Use:
- Django Templates
- Tailwind CSS
- Minimal Vanilla JavaScript

Do NOT use React/Vue/Angular.

The UI should feel like a serious modern SaaS product, not a college CRUD project.

Company landing:
- Professional
- Clean
- Modern
- Strong CTA
- Responsive
- Trust-oriented
- Security-conscious

School environment:
- School branding support
- Clean admin dashboard
- Clear attendance states
- Fast camera interaction
- Clear success/failure messages
- Responsive design

Attendance camera screen should clearly communicate:
- Camera status
- Face detected/not detected
- Recognition result
- Check-in/check-out result
- Duplicate attempt
- Failure reason where safe to disclose

Avoid unnecessary animations and decorative complexity.

==================================================
REPORTING
==================================================

V1 should include useful attendance reporting.

At minimum consider:
- Today's attendance
- Faculty-wise attendance
- Date-wise attendance
- Present
- Absent
- Late
- Check-in time
- Check-out time
- Working duration where meaningful
- Monthly summary

Reports should be scoped to the current school.

Export functionality can be included if it provides clear V1 value, but do not overbuild.

==================================================
ARCHITECTURE EXPECTATIONS
==================================================

Use Django properly.

Prefer a maintainable modular architecture.

Avoid:
- Giant views
- Giant models
- Business logic scattered inside templates
- Hard-coded tenant IDs
- Hard-coded school rules
- Duplicate business logic
- Unnecessary microservices
- Premature abstraction

Keep the system as a well-structured Django monolith initially.

Use PostgreSQL.

Use environment variables for secrets/configuration.

Prepare the application for cloud deployment.

==================================================
DEVELOPMENT PRINCIPLES
==================================================

This is a production-minded startup MVP.

Follow:
- Clean architecture where useful, but do not overengineer
- DRY
- SOLID where applicable
- Secure defaults
- Explicit business rules
- Database constraints
- Automated tests for critical logic
- Unit tests
- Integration tests
- Permission/tenant isolation tests
- Attendance rule tests
- Face recognition integration boundaries
- Error handling
- Logging
- Clear documentation

Do not generate fake functionality just to make a UI look complete.

Do not use mock data in production paths unless explicitly required for testing.

==================================================
TESTING REQUIREMENTS
==================================================

Testing must cover at minimum:

AUTH:
- Admin login
- Faculty identity access
- Unauthorized access
- Cross-tenant access attempts

MULTI-TENANCY:
- School A cannot access School B
- IDs cannot be manipulated to bypass tenant isolation
- Subdomain resolution works correctly

FACULTY:
- Create
- Update
- Deactivate
- Face registration

ATTENDANCE:
- Valid check-in
- Duplicate check-in
- Valid check-out
- Duplicate check-out
- Invalid face
- Unknown face
- Non-working day
- Holiday
- Half-day
- Late rule
- Missing check-out
- Admin correction
- Audit trail

SECURITY:
- CSRF
- Permission checks
- Session security
- Sensitive data handling
- Secret configuration

==================================================
GSD WORKFLOW REQUIREMENTS
==================================================

Use GSD as the project's execution framework.

Do NOT attempt to build the entire application in one giant implementation step.

First:
1. Gather requirements
2. Challenge assumptions
3. Identify unknowns
4. Research critical technical decisions
5. Produce V1 requirements
6. Separate V1 / V2 / Out of Scope
7. Design the architecture
8. Create a phased roadmap
9. Define verification criteria for every phase

Each phase must be independently understandable and testable.

For implementation:
Discuss phase
→ UI design contract where appropriate
→ Plan phase
→ Verify plan
→ Execute phase
→ Test
→ Verify work
→ Review
→ Continue

Do not skip verification simply because the code appears to work.

==================================================
PHASE PLANNING GUIDANCE
==================================================

The roadmap will likely contain phases similar to:

Phase 1:
Project foundation, Django setup, PostgreSQL, configuration, base architecture

Phase 2:
Company landing page and school registration

Phase 3:
Multi-tenant school subdomain resolution and school environment

Phase 4:
Authentication and role-based authorization

Phase 5:
Faculty management

Phase 6:
Face registration and biometric representation pipeline

Phase 7:
Face-based check-in/check-out engine

Phase 8:
Working schedules, late rules, half-days, holidays and attendance business rules

Phase 9:
Admin dashboard, attendance history and reports

Phase 10:
Security hardening, automated testing, performance checks and cloud deployment

You may change this phase structure if research shows a better dependency order.

Do NOT blindly follow this suggested roadmap.

==================================================
QUALITY BAR
==================================================

Think like a senior engineer reviewing the project before production.

Whenever there is a weak assumption:
- Call it out.
- Explain the risk.
- Recommend a better approach.

Whenever a requirement is ambiguous:
- Ask a focused question.

Whenever a technology decision is uncertain:
- Research it before locking it.

Whenever a shortcut could create future security/data problems:
- Reject the shortcut.

Do not optimize for "more features".
Optimize for:
- Correctness
- Security
- Privacy
- Maintainability
- Tenant isolation
- Reliable attendance
- Good UX
- Fast MVP delivery

==================================================
IMPORTANT CONSTRAINT
==================================================

Do NOT add future modules such as bus tracking or student attendance into V1 implementation.

Keep them only as future extensibility considerations.

The current startup MVP is:

"Multi-tenant SaaS platform for school faculty face-based attendance with configurable schedules, check-in/check-out, admin management, reporting, and strict tenant/privacy isolation."

Start by deeply understanding this product and then run the normal GSD new-project process.

Do not start writing application code during project initialization.

First produce the project context, requirements, research findings where necessary, and roadmap through the GSD workflow.