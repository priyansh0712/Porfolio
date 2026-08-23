Act as a Senior Django SaaS Architect, Senior Backend Engineer, and Senior GSD Engineer.

Implement ONLY a dynamic Feature Management / Feature Flag system in the EXISTING project.

DO NOT rebuild the project.
DO NOT change or redesign existing functionality.
DO NOT refactor unrelated code.
DO NOT modify existing attendance, leave, authentication, notification, branding, dashboard, or other features except where required to make them respect the feature flags.

==================================================
GOAL
==================================================

Different schools may need different features.

The Super Admin must be able to enable/disable features for each individual school.

When a feature is OFF for a school:

1. It must NOT appear in that school's portal navigation.
2. Its pages/routes must NOT be accessible.
3. Its backend functionality must be blocked.
4. Its related dashboard cards/widgets should not be shown.
5. Direct URL/API access must also be denied.

When a feature is ON:

1. It should appear normally in the school's portal.
2. Its existing functionality should work normally.

==================================================
SUPER ADMIN
==================================================

When Super Admin creates or manages a school, provide a dynamic Feature Management section.

Example:

School: ABC School

Features:

[ON]  Faculty Attendance
[ON]  Faculty Leave
[ON]  Attendance Reports
[ON]  Notifications
[OFF] Student Attendance
[OFF] Bus Management
[OFF] Parent Portal

Super Admin should be able to:

- Enable a feature
- Disable a feature
- View current feature status
- Update feature configuration for an existing school

The feature configuration must be stored per school/tenant.

Do NOT hard-code feature availability in templates.

==================================================
CURRENT FEATURES
==================================================

At minimum, make the existing relevant modules compatible with feature flags:

- Faculty Attendance
- Faculty Leave
- Attendance Reports
- Notifications
- School Branding if applicable

Future features should be easy to add without redesigning the entire feature-management system.

Do not implement Student Attendance, Bus Management, or Parent Portal functionality now.

Only make the architecture ready for them to become feature flags later.

==================================================
DYNAMIC SCHOOL PORTAL
==================================================

The school portal must dynamically display features based on the current school's configuration.

Example:

School A:

Faculty Attendance = ON
Faculty Leave = OFF
Reports = OFF

Portal:

Dashboard
Faculty Attendance

School B:

Faculty Attendance = ON
Faculty Leave = ON
Reports = ON

Portal:

Dashboard
Faculty Attendance
Leave Management
Reports

Do not show disabled features anywhere in the school portal navigation.

==================================================
BACKEND SECURITY
==================================================

IMPORTANT:

Hiding navigation items is NOT sufficient.

If a feature is disabled, direct access must also be blocked.

Example:

If Faculty Leave is OFF:

/leave/
/leave/apply/
/leave/requests/

must not be accessible for that school.

The backend must check the current school's feature configuration before allowing access.

Do not rely only on frontend JavaScript or template conditions.

Use a reusable feature-checking mechanism appropriate for Django, such as middleware, decorators, mixins, permissions, or a clean combination where appropriate.

Do not duplicate the same feature-checking logic across every view.

==================================================
MULTI-TENANCY
==================================================

Feature configuration is tenant-specific.

School A's feature settings must never affect School B.

Example:

ABC School:
Faculty Leave = OFF

XYZ School:
Faculty Leave = ON

ABC must not be able to access XYZ's enabled feature by changing:

- URL
- School ID
- Request parameters
- API parameters

All feature checks must use the authenticated/current tenant.

==================================================
DATABASE DESIGN
==================================================

Inspect the existing School/Tenant architecture first.

Do not create a duplicate School model.

Design the feature configuration in a scalable way.

Prefer a structure that allows future features to be added without repeatedly modifying many unrelated database models.

Avoid unnecessary hard-coded boolean fields if a scalable feature-key/configuration approach fits the existing architecture better.

However, do not overengineer it.

Use the simplest production-appropriate design.

Create proper migrations.

Existing schools must receive sensible default feature settings.

DO NOT unexpectedly disable existing V1/V2 functionality for existing schools.

==================================================
ADMIN EXPERIENCE
==================================================

Super Admin should have a clean feature-management UI for each school.

Example:

---------------------------------
School: ABC School

Feature Management

Faculty Attendance       [ON]
Faculty Leave            [ON]
Attendance Reports       [OFF]
Notifications            [ON]
---------------------------------

Changes should be saved reliably.

If appropriate, show confirmation after updating.

Do not redesign the entire Super Admin dashboard.

Only add the required feature-management UI.

==================================================
EXISTING FUNCTIONALITY
==================================================

Existing functionality must remain unchanged when its feature is ON.

For example:

Faculty Attendance ON
→ Existing attendance system works exactly as before.

Faculty Leave ON
→ Existing leave system works exactly as before.

Notifications ON
→ Existing notifications work exactly as before.

Do NOT rewrite these modules.

Only add the feature-access control around them.

==================================================
DEFAULTS / SAFETY
==================================================

For existing features already being used in V1/V2:

Default to ON for existing schools unless the current product configuration explicitly says otherwise.

Do not accidentally lock existing schools out of their current functionality after migration.

For new schools, feature defaults should be explicitly defined.

==================================================
TESTING
==================================================

Add focused tests for:

1. Super Admin can enable/disable a feature.
2. Feature configuration is stored per school.
3. School A's configuration does not affect School B.
4. Enabled feature appears in the portal.
5. Disabled feature disappears from navigation.
6. Disabled feature cannot be accessed through direct URL.
7. Disabled feature cannot be accessed through backend/API requests.
8. Existing functionality still works when feature is ON.
9. Existing schools continue working after migration.
10. Unauthorized users cannot modify feature configuration.

Test with at least two schools having different feature configurations.

==================================================
STRICT SCOPE
==================================================

ONLY implement dynamic Feature Management / Feature Flags.

DO NOT:

- Add new business features
- Build Student Attendance
- Build Bus Management
- Build Parent Portal
- Change existing UI unnecessarily
- Redesign dashboards
- Rewrite existing modules
- Change authentication
- Change face recognition
- Change attendance logic
- Change leave logic
- Change notifications
- Change school branding
- Refactor unrelated code

If you discover unrelated bugs, DO NOT fix them.

Mention them in the final report only.

==================================================
GSD WORKFLOW
==================================================

First inspect the existing codebase and understand:

- Current School/Tenant model
- Super Admin
- School Admin
- Existing portal navigation
- Existing URL/view structure
- Existing V1/V2 modules
- Existing permission system
- Existing database structure

Then create a focused implementation plan.

Implement ONLY this feature.

Run migrations and relevant tests.

Finally verify:

Super Admin
→ School A
→ Feature configuration
→ School A portal dynamically changes

and:

Super Admin
→ School B
→ Different feature configuration
→ School B portal dynamically changes independently.

Do not use /gsd-new-project because this is an existing project.