---
title: "UX Spec — Customer Authentication"
surface: "Customer Mobile App (iOS + Android)"
flow: "Registration and Login (OTP)"
prd-refs: "FR-C-AUTH-01, FR-C-AUTH-02, FR-C-AUTH-03, NFR-SEC-02, NFR-SEC-03"
created: 2026-09-05
---

# Customer Authentication Flow

## Overview

Authentication gates booking creation and booking management. Browsing (discovery
list and salon detail) is unauthenticated. The gate is enforced at the point the
customer taps "Book" — not at app launch.

PRD FR-C-AUTH-02 permits either OTP-SMS or email/password; the Architect selects
the method(s) at launch. This spec covers both methods so that either or both can
be implemented without a UX redesign. Screens that are method-specific are
labelled accordingly.

Decision note: the authentication entry point is deferred — customers can browse
without an account. This is intentional (PRD FR-C-AUTH-01) and reduces friction
for the discovery use case. The prompt appears only when a booking action is
initiated. The alternative (requiring login on app open) was rejected because it
conflicts with Priya's persona need: she wants to see salon options before
committing to creating an account.

---

## Screen: AuthGate (Modal)

**Entry point:** Customer taps "Book This Service" on any service in the Salon
Detail view and is not authenticated. Also accessible if customer taps "My
Bookings" from the bottom navigation while unauthenticated.

### Components

- `modal_sheet`: Bottom sheet overlay, half-screen, dismissible by swipe down or
  tapping outside.
- `headline_text`: "Sign in to book" (single line, large body text).
- `subtext`: "You need an account to make or manage bookings. Browsing is always
  free." (2 lines max).
- `phone_otp_button`: Primary CTA — "Continue with phone number" (full-width,
  height 52pt, accessible tap target).
- `email_button`: Secondary CTA — "Continue with email" (full-width, outlined
  style, height 52pt). Shown only if the Architect enables email/password auth.
- `dismiss_link`: "Maybe later" (text button, bottom of sheet). Dismisses modal
  and returns customer to the screen that triggered it.

### Interactions

- Tap `phone_otp_button` → navigate to PhoneEntry screen (OTP flow).
- Tap `email_button` → navigate to EmailLogin screen (email/password flow).
- Tap `dismiss_link` or swipe down → dismiss modal; customer remains on the
  originating screen, unauthenticated. The booking action that triggered the gate
  is cancelled (not queued).
- After successful auth via either path → return customer to the originating
  screen with the booking action resumed automatically (the service selection
  context is preserved in transient BLoC state during the auth flow).

### Error / Edge States

- App opened while a valid JWT is still in `flutter_secure_storage`: AuthGate is
  never shown; the booking action proceeds directly.
- JWT expired: AuthGate is shown with the same copy. The expired token is cleared
  before showing the gate.

### Privacy / Accessibility

- No customer data is displayed on this screen.
- All buttons meet 44pt minimum tap target (buttons are 52pt height).
- `phone_otp_button` is the first focusable element for screen-reader navigation
  order.
- Modal is announced as a dialog to screen readers
  (`Semantics(explicitChildNodes: true)`).

---

## Screen: PhoneEntry

**Entry point:** Tapping `phone_otp_button` on AuthGate.

### Components

- `back_button`: Chevron left, top-left corner (44pt tap target). Returns to AuthGate.
- `screen_title`: "Enter your phone number".
- `subtext`: "We'll send a one-time code to verify your number."
- `country_code_selector`: Tappable field showing flag + "+91" (India fixed for
  MVP, single locale). Displays "+91" as a non-editable prefix inside the number
  field. No country picker needed for MVP (single city launch).
- `phone_number_field`: Numeric keyboard, 10-digit input (Indian mobile format),
  placeholder "00000 00000". Max length: 10 digits. No spaces or dashes accepted
  in the stored value (formatting is display-only).
- `send_otp_button`: "Send code" — primary CTA, full-width, 52pt height. Disabled
  until `phone_number_field` contains exactly 10 digits.
- `terms_note`: "By continuing, you agree to our Terms of Service and Privacy
  Policy." (small caption text, links to external web views).

### Interactions

- Customer types phone number → `send_otp_button` becomes enabled when 10 digits
  are entered.
- Tap `send_otp_button` → show inline loading spinner inside button, disable
  button. POST to auth/otp/send. On success → navigate to OTPVerification screen,
  passing the phone number (masked display).
- Tap `back_button` → return to AuthGate modal.

### Error / Edge States

- `send_otp_button` disabled: fewer than 10 digits entered (enforced by maxLength,
  no explicit error message needed — the disabled state is self-explanatory).
- API error (network failure): show inline error below field —
  "Couldn't send the code. Check your connection and try again." Button re-enabled.
- API error (invalid number / non-mobile): "That number doesn't look right. Please
  check and try again." Button re-enabled.
- Rate limit (too many OTP requests): "Too many attempts. Please wait 60 seconds
  before trying again." Button disabled for 60 seconds with a visible countdown.

### Privacy / Accessibility

- Phone number is PII. The field uses `obscureText: false` (it is not a password)
  but the number is masked on the OTPVerification screen (see below).
- Keyboard type: `TextInputType.phone` — numeric input, reduces error.
- `send_otp_button` semantic label: "Send one-time code to your phone number".
- `country_code_selector` announces "+91 India" to screen readers.

---

## Screen: OTPVerification

**Entry point:** After OTP is successfully sent from PhoneEntry.

### Components

- `back_button`: Top-left. Returns to PhoneEntry (allows customer to correct
  their number).
- `screen_title`: "Enter the code".
- `subtext`: "We sent a 6-digit code to +91 XXXXX XX{last 4 digits}." (phone
  number partially masked — first 6 digits replaced with X).
- `otp_field`: Single 6-cell inline code input (each cell accepts one digit).
  Numeric keyboard auto-appears on screen entry. Auto-advances focus to next
  cell on digit entry. Auto-submits when 6th digit is entered.
- `verify_button`: "Verify" — primary CTA, full-width, 52pt height. Disabled
  until all 6 cells are filled. Enabled and auto-triggers on 6th digit entry
  (customer does not need to tap separately if using the numeric keyboard).
- `resend_link`: "Didn't get the code? Resend" — text button. Disabled for 30
  seconds after the OTP is sent (countdown displayed: "Resend in 28s").
- `resend_countdown`: Inline text below `resend_link` during the 30-second
  cooldown: "Resend in {N}s".

### Interactions

- Enter all 6 digits → `verify_button` auto-triggers. POST to auth/otp/verify
  with phone and OTP. Show loading state (spinner replaces button label).
  - Success (new user): navigate to RegistrationName screen.
  - Success (returning user): dismiss AuthGate, resume booking action.
- Tap `verify_button` manually → same as above.
- Tap `resend_link` (when enabled) → POST to auth/otp/send again. Reset
  countdown to 30 seconds. Show brief inline confirmation: "Code resent."
- Tap `back_button` → return to PhoneEntry with phone number pre-filled.

### Error / Edge States

- Wrong OTP code: inline error below `otp_field` — "That code is incorrect.
  Please check and try again." OTP field is cleared (all cells reset). Customer
  retries. (NFR-SEC-03: OTP invalidated on first successful use; incorrect
  submissions do not consume the OTP.)
- Expired OTP (10-minute expiry, NFR-SEC-03): "This code has expired. Request
  a new one." `resend_link` becomes immediately enabled regardless of countdown.
- OTP already used: treat as expired — same message.
- Network failure during verify: "Verification failed. Check your connection and
  try again." Cells retain the entered value (customer does not need to re-type).
- Maximum incorrect attempts (5 per OTP — Architect to confirm limit): "Too many
  incorrect attempts. Please request a new code." OTP field locked, `resend_link`
  enabled.

### Privacy / Accessibility

- Phone number displayed in masked form (NFR-PRIV-05: minimise PII exposure).
- OTP field cells use `autofillHints: [AutofillHints.oneTimeCode]` so Android and
  iOS can auto-fill from SMS.
- Screen reader announces "Enter 6-digit code. Cell 1 of 6." on focus.
- Each cell has minimum 44pt tap target.

---

## Screen: RegistrationName (New Users Only)

**Entry point:** First successful OTP verification for a phone number not yet
registered. Skipped for returning users.

### Components

- `screen_title`: "What's your name?".
- `subtext`: "This is how your bookings will be identified."
- `name_field`: Text input, placeholder "Your full name". Max length: 100
  characters. Required. No character class restrictions (supports Indian
  names with various scripts — but input is stored as entered, display is UTF-8).
- `continue_button`: "Create account" — primary CTA, full-width, 52pt height.
  Disabled until `name_field` is non-empty (trimmed).
- `terms_note`: "By creating an account, you agree to our Terms of Service and
  Privacy Policy." (caption, links to web views).

### Interactions

- Customer types name → `continue_button` enabled when trimmed value is non-empty.
- Tap `continue_button` → POST to auth/register with phone and name. On success
  → account created, JWT issued, stored in `flutter_secure_storage`. AuthGate
  dismissed. Booking action resumes on originating screen.
- No back navigation here (the customer has already verified their phone; going
  back would leave a dangling verified state). The screen cannot be dismissed.

### Error / Edge States

- Empty name (only whitespace): `continue_button` remains disabled. No error
  message needed — disabled state is sufficient.
- Name exceeding 100 chars: `name_field` enforces maxLength, no further action
  needed.
- API error creating account: "Something went wrong. Please try again." with a
  "Try again" button. The phone number and OTP flow does not need to be restarted —
  retry with the same token.

### Privacy / Accessibility

- Customer name is PII. It is stored server-side and associated with their
  account (FR-C-AUTH-03). It is visible to the salon partner in the booking
  dashboard (FR-P-DASH-02, NFR-PRIV-03) but not to other customers.
- `name_field` semantic label: "Your full name, required".
- `TextInputAction.done` closes keyboard and triggers continue action.

---

## Screen: EmailLogin (Email/Password — if Architect enables)

**Entry point:** Tapping `email_button` on AuthGate.

### Components

- `back_button`: Returns to AuthGate.
- `screen_title`: "Sign in with email".
- `email_field`: Email keyboard type, placeholder "your@email.com". Required.
- `password_field`: Password keyboard type (obscured), placeholder "Password".
  Required. Min length: 8 characters (enforced only at registration, not login).
  Visibility toggle (eye icon, 44pt tap target) to reveal/hide.
- `sign_in_button`: "Sign in" — primary CTA, full-width, 52pt height. Disabled
  until both fields are non-empty.
- `create_account_link`: "Don't have an account? Create one" — text link below
  button. Navigates to EmailRegistration.
- `forgot_password_link`: "Forgot password?" — text link. Navigates to password
  reset flow (email-based reset — Architect to specify mechanism; this screen is
  a placeholder pointer only).

### Interactions

- Fill email and password → `sign_in_button` enabled.
- Tap `sign_in_button` → POST to auth/email/login. On success → JWT stored,
  AuthGate dismissed, booking action resumed.
- Tap `create_account_link` → navigate to EmailRegistration.

### Error / Edge States

- Invalid credentials: "Incorrect email or password." (single message — do not
  distinguish between wrong email and wrong password, per security practice).
- Email not registered: same message as invalid credentials (do not reveal
  whether the account exists).
- Network failure: "Couldn't sign in. Check your connection."

### Privacy / Accessibility

- Password is never logged (NFR-SEC-02, base-rules.md "Never log PII").
- Passwords stored as bcrypt/Argon2 hash server-side (NFR-SEC-02).
- `password_field` semantic label: "Password. Tap eye icon to show or hide."
- Password visibility toggle does not change the semantic label — announces
  "Password, shown" / "Password, hidden".

---

## Screen: EmailRegistration (Email/Password — if Architect enables)

**Entry point:** Tapping `create_account_link` on EmailLogin.

### Components

- `back_button`: Returns to EmailLogin.
- `screen_title`: "Create an account".
- `name_field`: Same as RegistrationName above.
- `email_field`: Email keyboard, required.
- `phone_field`: Phone number field, 10 digits (same as PhoneEntry). Required
  (needed for booking notifications per FR-C-BOOK-05).
- `password_field`: Password keyboard, obscured, min 8 chars. Visibility toggle.
- `confirm_password_field`: "Confirm password", same controls.
- `create_button`: "Create account" — primary, disabled until all fields are
  valid.
- `terms_note`: Same as RegistrationName.

### Interactions

- Fill all fields → `create_button` enabled when all pass local validation.
- Tap `create_button` → POST to auth/email/register. On success → JWT stored,
  AuthGate dismissed, booking resumed.

### Error / Edge States

- Email already registered: "An account with this email already exists. Sign in
  instead?" with a link to EmailLogin.
- Password too short (< 8 chars): inline error below field — "Password must be at
  least 8 characters."
- Passwords do not match: inline error on `confirm_password_field` — "Passwords
  don't match."
- Invalid email format: "Please enter a valid email address." (client-side format
  check; shown on field blur).

### Privacy / Accessibility

- Phone number collected here to enable SMS notifications (FR-C-BOOK-05). The
  field description reads: "We'll use this for booking confirmations and
  reminders."
- All PII fields have appropriate `autofillHints` for OS password manager
  integration.

---

## Design Decisions

| Decision | Rationale | Alternatives Considered |
|---|---|---|
| Auth gate deferred to booking action, not app launch | PRD FR-C-AUTH-01 explicitly allows unauthenticated browsing. Forcing login at launch would block Priya's discovery use case. | Login on launch — rejected: contradicts FR-C-AUTH-01. |
| Single country code (+91) hardcoded | MVP is single city, single locale, INR. No multi-region logic (PRD Section 2). | Country picker — rejected: post-MVP scope. |
| OTP auto-submit on 6th digit | Reduces taps for a common path. Common mobile pattern. | Manual confirm only — eliminated a tap with no UX downside. |
| Phone number masked on OTPVerification | Minimises PII display surface. Customer can still identify the target number via last 4 digits. | Full display — rejected: unnecessary PII exposure. Fully hidden — rejected: customer cannot verify the correct number was used. |
| Booking action context preserved through auth flow | Priya's persona: she has selected a service and a time; losing that on login is friction she cannot afford (she has children with her). | Send customer back to discovery after auth — rejected: high friction, high abandonment risk. |
