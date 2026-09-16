---
title: "UX Spec — Salon Partner Authentication"
surface: "Salon Partner Mobile App (iOS + Android)"
flow: "Partner Login"
prd-refs: "FR-P-AUTH-01, FR-P-AUTH-02, NFR-SEC-01, NFR-SEC-02, NFR-SEC-04"
created: 2026-09-05
---

# Salon Partner Authentication Flow

## Overview

The Salon Partner app is gated entirely on authentication (unlike the customer app
where browsing is unauthenticated). All screens in the partner app require a valid
session. FR-P-AUTH-01 specifies email and password as the authentication method
for salon partners. OTP-SMS is not required for the partner flow.

One partner account corresponds to exactly one salon location (FR-P-AUTH-02).
Multi-location accounts are out of scope for MVP.

Partner accounts are created through an off-app onboarding process (go-to-market
decision, PRD Section 10 — Founder to decide). The partner app does not have a
self-serve registration screen at MVP. Account creation is handled by the platform
operator (e.g., via a back-office tool or manual provisioning). This is recorded
as an open UX question (see Design Decisions below).

---

## Screen: PartnerSplash

**Entry point:** App cold start.

### Components

- `app_logo`: Salon platform logo/wordmark, centered.
- `loading_indicator`: Circular progress indicator below logo.

### Interactions

- App cold start → check `flutter_secure_storage` for a valid JWT.
  - Token present and valid → navigate to PartnerDashboard (skip Login).
  - Token present but expired → attempt token refresh. If refresh succeeds →
    navigate to PartnerDashboard. If refresh fails → clear token, navigate to
    PartnerLogin.
  - No token → navigate to PartnerLogin.

### Error / Edge States

- Storage read failure: navigate to PartnerLogin as a safe default.

### Privacy / Accessibility

- No user data is displayed on this screen.
- Screen reader announces: "Loading salon partner app."

---

## Screen: PartnerLogin

**Entry point:**
1. PartnerSplash with no valid token.
2. Explicit logout from within the app.

### Components

- `app_logo`: Platform logo, top-center or top-left (smaller than splash).
- `screen_title`: "Sign in to your salon account".
- `email_field`: Email keyboard type. Placeholder "your@email.com". Required.
- `password_field`: Password keyboard type (obscured). Placeholder "Password".
  Required. Visibility toggle (eye icon, 44pt tap target).
- `sign_in_button`: "Sign in" — primary CTA, full-width, 52pt. Disabled until
  both fields are non-empty (trimmed).
- `forgot_password_link`: "Forgot your password?" — text link, centered below
  button. Navigates to ForgotPassword screen.
- `contact_support_text`: Small caption at bottom — "Don't have an account?
  Contact us at {support_email}." (Account creation is off-app; this note directs
  unregistered partners to the onboarding contact.)

### Interactions

- Fill both fields → `sign_in_button` enabled.
- Tap `sign_in_button` → POST to auth/partner/login with email and password.
  Show loading spinner inside button, disable inputs.
  - Success (200) → JWT stored in `flutter_secure_storage`. Navigate to
    PartnerDashboard. Clear sensitive fields from BLoC state.
  - Error → show error (see below). Re-enable inputs.
- Tap `forgot_password_link` → navigate to ForgotPassword screen.

### Validation

- `email_field`: Non-empty, valid email format. Format validated on field blur
  (not on every keystroke). If invalid: inline error below field —
  "Please enter a valid email address."
- `password_field`: Non-empty. No min-length check at login (only at account
  creation, which is off-app).

### Error / Edge States

- **Invalid credentials (401):** Inline error below `password_field` —
  "Incorrect email or password." Do not specify which field is wrong
  (security practice — do not enumerate registered accounts).
- **Account not found (also returns 401 — do not distinguish from wrong
  password):** Same message as above.
- **Account suspended or deactivated:** "Your account has been suspended.
  Please contact support at {support_email}." (Platform operator action;
  surfaced as a distinct message so the partner knows it is not a password issue.)
- **Network failure:** "Couldn't connect. Check your internet connection and
  try again." `sign_in_button` re-enabled.
- **Server error (5xx):** "Something went wrong on our end. Please try again
  in a moment."
- **Both fields empty on button tap:** This cannot occur because `sign_in_button`
  is disabled until both are non-empty. No error needed.

### Privacy / Accessibility

- Password is never logged or stored in plain text (NFR-SEC-02, base-rules.md
  §1 "Never log PII").
- JWT stored in `flutter_secure_storage` (base-rules.md §2.6).
- `email_field` semantic label: "Email address, required."
- `password_field` semantic label: "Password, required. Tap eye icon to toggle
  visibility."
- `sign_in_button` disabled state: "Sign in. Enter email and password first."
- `forgot_password_link` semantic label: "Forgot your password? Tap to reset."
- Keyboard: `TextInputAction.next` on `email_field` moves focus to
  `password_field`. `TextInputAction.done` on `password_field` triggers the
  sign-in action.

---

## Screen: ForgotPassword

**Entry point:** Tapping `forgot_password_link` on PartnerLogin.

### Components

- `back_button`: Returns to PartnerLogin.
- `screen_title`: "Reset your password".
- `instruction_text`: "Enter your account email address. We'll send a link to
  reset your password."
- `email_field`: Email keyboard, placeholder "your@email.com". Required.
- `send_button`: "Send reset link" — primary CTA, full-width, 52pt. Disabled
  until `email_field` is non-empty.

### Interactions

- Fill `email_field` → `send_button` enabled.
- Tap `send_button` → POST to auth/partner/forgot-password with email.
  - Always show success state regardless of whether the email is registered
    (prevents account enumeration). Success message:
    "If an account exists for that email, a password reset link has been sent."
  - `send_button` disabled after send to prevent duplicate requests (re-enabled
    after 60 seconds with countdown "Try again in {N}s").
- Tap `back_button` → return to PartnerLogin.

### Error / Edge States

- **Network failure:** "Couldn't send the reset link. Check your connection."
  `send_button` re-enabled.
- **Invalid email format:** Inline error on blur — "Please enter a valid email
  address." `send_button` remains disabled.
- **Rate limit:** "Too many reset attempts. Please wait {N} minutes before trying
  again." `send_button` disabled with countdown.

### Privacy / Accessibility

- Account enumeration is prevented by always showing the same success message.
- `send_button` semantic label: "Send password reset link."
- `email_field` semantic label: "Your account email address, required."

---

## Session Management (Cross-screen rule)

- All protected partner screens check for a valid JWT on mount. If the JWT is
  expired or missing (e.g., after a long background period), the screen navigates
  to PartnerLogin immediately, clearing the navigation stack.
- Session expiry during an active operation (e.g., saving a profile): show a
  bottom sheet — "Your session has expired. Please sign in again." with a "Sign
  in" button. After re-auth via PartnerLogin, the operation is not automatically
  retried (the partner must repeat it). This is the safe default; auto-retry of
  writes after re-auth introduces complexity not justified at MVP.
- Logout action: available from the partner app's settings/profile section
  (exact location defined in partner-profile.md). Logout clears the JWT from
  `flutter_secure_storage` and navigates to PartnerLogin with the navigation
  stack cleared.

---

## Design Decisions

| Decision | Rationale | Alternatives Considered |
|---|---|---|
| Partner app is fully gated on auth (unlike customer app) | The partner app contains all booking data, customer names, and business management functions. None of these should be accessible without authentication. There is no browsing or discovery use case in the partner app that benefits from unauthenticated access. | Partial unauthenticated access — no valid use case for partner; rejected. |
| No self-serve partner registration in the app | PRD Section 10 (Founder to decide): partner onboarding and go-to-market strategy is an open question. The platform operator manages partner account creation. Building a self-serve registration flow before the onboarding policy is decided would likely need to be redone. This is recorded as an open UX question. | Self-serve registration — blocked by unresolved go-to-market decision. Post-MVP candidate if founder decides on self-serve onboarding. |
| Password reset link (email-based) over OTP-SMS | FR-P-AUTH-01 specifies email/password only for partner auth. Email-based reset is consistent with the authentication method. OTP-SMS reset would require a separate phone number collection not defined in the PRD partner account model. | OTP-SMS reset — inconsistent with FR-P-AUTH-01's email/password method; partner account data model has no phone field. |
| Session expiry mid-operation does not auto-retry | Auto-retrying a failed write after re-auth creates a risk of duplicate submissions (e.g., a partner confirms a booking that was already confirmed by a concurrent session). The safe default is to inform and require manual re-submission. | Auto-retry — rejects: duplicate action risk; adds state management complexity not justified at MVP. |

## Open UX Questions

1. **Partner account self-serve registration:** If the founder decides on self-
   serve onboarding (where a salon owner creates their own partner account via
   the app), a PartnerRegistration screen must be designed. Fields would minimally
   include: business email, password, salon name, phone number. This is not
   designed in this spec pending the go-to-market decision (PRD Section 10).

2. **Partner account linking to salon profile:** On first login, if a partner
   account has no associated salon profile (i.e., the account was provisioned
   but the profile was not yet created), the app should route to the PartnerProfile
   creation flow (partner-profile.md) rather than the dashboard. The exact
   first-run logic depends on how accounts are provisioned (off-app vs. self-
   serve) and is flagged for product confirmation.
