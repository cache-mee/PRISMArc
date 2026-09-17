---
title: Agentic Appointment Management Engine — Salon Edition
status: draft
created: 2026-09-17T00:00:00+00:00
updated: 2026-09-17T00:00:00+00:00
---

# Product Brief: Agentic Appointment Management Engine — Salon Edition

## Document Note — Full Pivot

This brief **replaces** the prior marketplace-scope salon-app brief, PRD, UX artifacts, and epics (all deleted by the user prior to this run). It is a clean slate, not a revision. The product is no longer a multi-salon discovery marketplace; it is a single-business, conversational appointment-management engine, seeded with one salon for a 24-hour hackathon demo. Source: user-finalized project brief document, supplied verbatim for this run, plus a prior-session architecture discussion (both reproduced in full in `addendum.md`).

## Executive Summary

The product is a conversational appointment-management engine that a single business — here, a salon — plugs into its own customer channels: a web chat widget and WhatsApp, both fronted by one shared agent core. Customers request appointments in natural language ("I need a haircut Thursday afternoon, prefer Rahul") and a **Booking Agent** parses intent, checks live availability, and confirms or negotiates a time. On the business side, staff state availability changes and the owner manages the service/pricing catalog through the same conversational paradigm — a **Manager Agent** parses natural-language changes and reconciles them against existing bookings. A read-only **dashboard** gives the owner a live view of staff and bookings. All three read from (and the agents write to) one shared data store, so a change on one surface is immediately visible on the others — this shared-state behavior is the core technical proof point of the demo.

This is framed as a B2B, plug-into-any-business engine; the salon is the seeded demo vertical, not the ceiling of the idea.

## The Problem

Salons, and appointment-based businesses generally, run scheduling through phone calls, paper registers, or generic calendar tools not built for multi-chair, multi-staff booking. This produces double-bookings, idle chair time, manual "is this slot free" back-and-forth, no easy way for staff to signal last-minute availability changes short of editing a calendar grid, and customers left uncertain of availability until they call or walk in. Existing booking apps solve "reserve a slot" through rigid UI flows; none let a customer simply say what they want and have the system reason about availability, staff preference, and timing on their behalf — nor let staff manage their own schedule the same conversational way.

## The Solution

A single-business, two-agent conversational system:

1. **Booking Agent (customer-facing)** — browse services & pricing, book, reschedule, cancel, and view booking history in natural language, via web chat or WhatsApp, both fronting the same agent core.
2. **Manager Agent (staff/owner-facing)** — staff state availability changes (block/unblock) in natural language; the owner manages the service/pricing catalog (add/edit/delete) in natural language and views the staff list and bookings via the dashboard.
3. **Calendar/Dashboard (owner-facing)** — a read-only view of the staff list and current bookings, reflecting the same shared data store in real time.

A change made by the Manager Agent is immediately reflected in what the Booking Agent can offer a customer and in what the dashboard displays — the shared-state proof point noted above.

**[HACKATHON SCOPE]** Multi-service, multi-person (family), and cross-provider optimization — the differentiator in the original marketplace-era brief — is deferred to the post-MVP vision. The happy-flow demo covers single-person, single-service, single-provider booking only, with no handling built for non-happy-path cases (ambiguous intent, zero availability, etc.) beyond noting them as known limitations.

## What Makes This Different

Conversational reasoning about availability, staff preference, and timing replaces a rigid slot-picker UI, on both the customer side and the staff/owner side. One agent core sits behind multiple channels (web chat, WhatsApp) rather than duplicating booking logic per surface. The differentiator being demonstrated is agentic orchestration and shared live state across three surfaces — not a novel booking algorithm at this stage; the honest moat, for the hackathon, is that it is a working, functioning system, not a slide.

## Who This Serves

- **Customer (primary)** — wants to book a salon appointment in plain language, on whichever channel they're already on, without a slot-picker UI.
- **Ramesh — Owner/Admin (secondary)** — runs a 4-chair unisex salon with 3 staff; manages the service/pricing catalog and views staff/bookings via the dashboard. **[ASSUMPTION]** Admin-only for this demo — does not take appointments himself or manage his own availability; open for confirmation (see Open Items).
- **Meena and Arjun — Staff (secondary)** — provide services; their only system action is managing their own availability (block/unblock) via the Manager Agent.

Full persona depth, including the role-permission matrix, is in `addendum.md`.

## Goals & Success Metrics (Hackathon Context)

Against the stated evaluation weighting (Agentic SDLC 40 / Human Verification 40 / Output Credibility 20):

- Demonstrate real agent orchestration across the SDLC (requirements → design → build → test → deploy), not a single mega-prompt.
- Produce at least one clear, evidenced human-verification moment — a human catching or correcting an agent's parsed intent or scheduling logic before it is treated as final. **[ASSUMPTION — open]** The specific moment to showcase is not yet chosen; see Open Items.
- Ship a working, functioning chat-based booking flow — not a mockup or a slide.

**[ASSUMPTION]** No traditional business KPIs (retention, conversion, wait-time reduction) are tracked for the demo itself.

## Scope — Hackathon MVP (Happy Flow Only)

**Booking Agent (customer, web chat + WhatsApp):** browse services/pricing at any point; state a booking intent (service, optionally date/time and/or staff preference); the agent resolves it one of three ways — exact time available → confirm directly; day given, no time → list that day's available slots (salon-wide or filtered to a named staff member); exact time unavailable → suggest the nearest alternative(s) with brief reasoning. Confirm → booking created. View booking history (upcoming/past) on request. Cancel a booking on request. Reschedule = cancel-the-old-slot + re-run the normal booking flow. Identity is phone-number lookup only (no password/OTP/session): not found → also ask name → create record → proceed; found → greet by name → proceed. WhatsApp already has the number, so it skips that question and only asks for a name if new.

**Manager Agent (staff/owner, web chat + WhatsApp):** Staff (Meena, Arjun) state availability changes in natural language; the agent checks conflicts against existing bookings, confirms, and applies the change — immediately visible to the Booking Agent next. Owner/Admin (Ramesh) adds/edits/deletes services and pricing in natural language, confirmed and applied to the live catalog; views the staff list and bookings via the dashboard (read-only, not conversational). Identity is pre-seeded phone-number lookup (no signup); web chat asks for the number, WhatsApp already has it. Role determines permitted actions — see the permission matrix in `addendum.md`.

**Dashboard (owner-facing):** simple, read-only web view of the staff list and current bookings (today's or the week's) per staff member. No editing from the dashboard.

**Out of scope for this demo:** multi-salon discovery/comparison; multi-person/family booking optimization (deferred to post-MVP vision, not dropped); multi-service combination booking in one visit; ratings & reviews; offers & discounts; payments/POS; Owner/Admin managing their own availability or acting as a bookable provider; Owner/Admin adding/removing/editing staff accounts (view-only); staff overriding another staff member's schedule; defensive handling of non-happy-path input.

## Demo Success Criteria

A judge can watch: (1) a customer browse, book, reschedule, cancel, and view booking history via natural-language chat on both web chat and WhatsApp; (2) Meena or Arjun block/unblock their own availability from either channel, with the change immediately reflected in what the Booking Agent offers next; (3) Ramesh add/edit/delete a service/price via natural language, and view the staff list and bookings on the dashboard; (4) the dashboard updating live as bookings and availability change; and (5) at least one clearly evidenced point where a human reviewed or corrected the agent's behavior during the build.

## Constraints

24-hour build window, happy-flow-only, single seeded business (Ramesh's 4-chair unisex salon, staffed by Ramesh, Meena, and Arjun) — all confirmed by the user. This repository's `CLAUDE.md` additionally fixes application code into a `B2B_BE/` (backend) / `B2B_FE/` (frontend) top-level split, which the technical direction below must reconcile with (see Open Items).

## Key Open Items (full depth and resolution log in `addendum.md`)

- **[ASSUMPTION]** Ramesh is admin-only, not a bookable provider — the source brief's own open question, still unconfirmed.
- **[ASSUMPTION]** No business KPIs tracked for this demo.
- **[ASSUMPTION]** The Section-8-equivalent technical considerations (interface, agents, intent parsing, data model) are Architect-phase starting points, not locked decisions.
- **[ASSUMPTION — CONFLICT, high priority]** A stack pivot toward Flutter + FastAPI (Python) + Postgres is under discussion, but this repository's `stack/stack-proposal.md` (status: approved) records Node.js/Express + Flutter mobile + Postgres as **"fixed by founder decision... not open for re-evaluation at MVP."** This is a direct conflict between a standing, approved, founder-locked decision and a new pivot direction — it needs explicit human/founder resolution, not just Architect evaluation, before the Architect proceeds.
- **[ASSUMPTION]** MCP tool-layer vs. direct in-process function registration for the agent-to-tool boundary — flagged as a real architecture choice for the Architect, not a given.
- **[ASSUMPTION]** The sketched `backend/app/...` package layout is not directly compatible with the authoritative `B2B_BE/` / `B2B_FE/` split in `CLAUDE.md` and needs to be nested accordingly — an Architect-phase item.
- **[OPEN]** What specific human-verification moment will be showcased during the build — not yet chosen.
- **[OPEN]** Whether "web chat" is a Flutter-web build of the same chat frontend used elsewhere, or a separate web technology from the owner dashboard — surfaced during this discovery pass, not in the source brief; for the Architect.

## Vision (Post-MVP)

Multi-service, multi-person, and cross-provider scheduling optimization; voice as a fully-supported channel; payments, ratings/reviews, offers; per-staff service specialization matching; Owner/Admin as a bookable provider with their own availability, if confirmed as needed; Owner/Admin managing staff accounts (not just viewing); stronger authentication (OTP/password) if phone-number-only identity proves insufficient at scale; domain-agnostic packaging so any appointment-based business can plug in with a config change.
