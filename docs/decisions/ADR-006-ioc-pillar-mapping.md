# ADR-006: IOC Pillar Mapping — Project-Defined Classification

## Decision

BTS delay categories mapped to IOC pillars using project-defined logic:

- Safety → WEATHER_DELAY
- Legality → NAS_DELAY + SECURITY_DELAY
- Efficiency → CARRIER_DELAY + LATE_AIRCRAFT_DELAY

Priority order for tie-breaking: Safety > Legality > Efficiency.

## Why we chose this

IOC operations broadly prioritize Safety > Legality > Efficiency.
Mapping delay categories to pillars enables operational framing of BTS data.
Single source of truth in dim_delay_reason — not CASE WHEN in every query.

## Why we rejected alternatives

Direct BTS categories only: loses operational framing value.
Custom ML classification: overclaims what BTS data can prove.

## Critical disclaimer

This mapping is a PROJECT-DEFINED analytical taxonomy inspired by operational concepts.
It is NOT an FAA classification.
It is NOT a BTS classification.
It is NOT a universal IOC standard.
Weather delay creating a Safety classification is an analytical abstraction —
the source dataset does not establish this mapping.
All downstream consumers must label pillar-attributed measures as DERIVED,
never as OBSERVED BTS fact.

## What this enables

dominant_delay_pillar DERIVED column in fact_delays.
IOC pillar aggregation in bridge_flight_delay_reason.
Power BI Delay Cause Analysis page by pillar.

## What this constrains

Must be labeled DERIVED in all downstream consumption.
Never present pillar mapping as BTS-established fact.
Changing the mapping in future requires full Gold rebuild.

## Future state

Pillar mapping locked v1. May extend with sub-pillar classifications in v2.
