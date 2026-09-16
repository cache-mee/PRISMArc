---
title: "Product Brief: Salon Time-Optimization Platform"
status: draft
created: 2026-09-04
updated: 2026-09-04
source: docs/adr/project-brief.md
---

# Product Brief: Salon Time-Optimization Platform

## Executive Summary

Salon visits routinely consume far more time than they should. People wait, make repeat trips, juggle separate bookings for different services or family members — and have no reliable way to know whether a nearby salon can actually serve them without a long delay. Existing booking apps solve the narrow problem of reserving a slot; none optimize the *whole visit*.

This platform is a two-sided mobile-first marketplace that makes salon visits predictable and efficient for customers, and operationally manageable for salon owners. Customers discover nearby salons, see real pricing and live wait state, and book optimized visits — including multi-service and multi-person (family) bookings in a single coordinated trip. Salon partners maintain their profile, service catalog, staff roster, and live schedule from a web console, and receive bookings they can actually fulfill.

The core differentiator — and long-term moat — is a **scheduling intelligence layer** that reasons about service combinations, staff specialization, per-service duration, and current queue load together, rather than simply checking slot availability. This must be a first-class system from architecture onward, not a retrofit.

## The Problem

Time-conscious customers lose time to: waiting for walk-in slots or delayed appointments, coordinating separate bookings for different services or family members, making repeat trips, and guessing which nearby salon is genuinely available at a reasonable price right now. No current app solves this as a system.

On the supply side, most independent salons run on phone bookings, paper registers, or generic calendar tools — none built for multi-chair, multi-service scheduling. They lack the digital infrastructure to expose their real availability to a smart booking system.

## The Solution

**Customer app (mobile):** discover salons near a chosen location; compare on distance, average service time, and price; view a detailed service/pricing list, ratings, and live queue load; book an optimized single or multi-service, multi-person visit with minimal expected wait.

**Salon Partner console (web, tablet-friendly):** manage salon profile, service catalog and pricing, offers/discounts, staff roster, staff availability, and shift schedules; view and manage incoming bookings and the current queue from a dashboard.

The **scheduling intelligence layer** sits between both sides: it computes recommended slots by combining service durations, staff/provider specialization, and live queue state — giving customers a visit plan that minimizes total time, not just a raw list of open slots.

## What Makes This Different

Existing salon apps are glorified calendar tools — they check availability, they do not optimize visits. This platform treats the scheduling engine as the product's core, not a feature, and exposes it through both sides of the marketplace simultaneously. Salons that maintain accurate data get better utilization; customers who trust the estimates return. The two sides reinforce each other, and the engine's accuracy compounds with historical service-duration data over time.

## Who This Serves

**Customers** — time-conscious individuals and families booking regular salon/grooming services who want to minimize wait and coordination overhead, including parents booking for themselves and children in one trip.

**Salon Partners** — independent salons and small salon chains seeking better chair/staff utilization, fewer scheduling conflicts, a real-time booking pipeline, and a channel to advertise offers and attract customers.

*[ASSUMPTION] Initial launch geography, whether barbershops/unisex salons/spas are in MVP scope alongside hair salons, and target salon size (independent vs. chain) are not yet confirmed.*

## Success Criteria

**Customer success:** measurable reduction in average wait time versus walk-in or naively booked appointment; ability to complete multi-service or multi-family-member visits in a single coordinated trip; confidence in salon choice before arriving.

**Business success:** two-sided liquidity in a launch area (enough salons that customers reliably find options; enough customer demand that salons maintain the console); demonstrated conversion of salon partners from phone/paper to platform scheduling.

**KPIs** *(targets TBD with founder)*: average customer wait time per visit; % of bookings that are multi-service or multi-person; booking completion rate; salon partner active-retention month-over-month; customer repeat-booking rate.

## Scope

**In for MVP:**
- Customer: location selection, salon discovery list (distance/time/price), salon detail view, slot booking (single and combination), live queue/load visibility (anonymized), ratings and reviews, booking management
- Salon Partner: profile management, service and pricing catalog, offers/discounts, staff management, schedule/availability configuration, booking dashboard

**Out of scope for MVP** *(confirm with founder)*:
- In-app payments (pay-at-salon assumed)
- Multi-location chain management
- Loyalty/rewards programs
- Marketing automation for salons
- Inventory/product management
- Full multi-person/multi-service/cross-provider optimizer in its advanced form — MVP may start with single-service smart slot suggestions; phasing to be confirmed with PM/Architect

*[ASSUMPTION] Payment, chain management, and advanced optimizer phasing are inferred from common MVP logic — founder has not confirmed these explicitly.*

## Vision

If the core scheduling intelligence proves out, this platform becomes the default way families book any appointment-based personal service — expanding beyond hair to grooming, spas, and adjacent services. Predictive wait-time estimates using per-staff historical duration data; dynamic demand-based scheduling suggestions; in-app payments, tipping, and receipts; loyalty programs; and multi-branch chain management follow. The scheduling engine's accuracy compounds with data, creating a durable advantage that a calendar-based competitor cannot replicate by adding features.
