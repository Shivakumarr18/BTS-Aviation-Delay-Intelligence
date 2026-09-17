# ADR-003: Carrier Dimension — Snapshot Strategy

## Decision

Snapshot v1 for all dimensions. SCD2 deferred to Azure v2.

## Why we chose this

BTS does not provide carrier attribute change events.
Without a change log we cannot build genuine SCD2.
Claiming SCD2 without version detection is architecturally dishonest.

## Why we rejected alternatives

Fake SCD2 (all records 2023-01-01 to 9999-12-31) gives appearance of history
without substance.
SCD1 (overwrite) loses history permanently — acceptable for v1 but not long-term.

## What this enables

Simple, honest snapshot. Full reload on every pipeline run.
GCG verifies dimension row counts and key uniqueness per run.

## What this constrains

No carrier attribute history. If a carrier changes name, the old name is overwritten.
Cannot track "what was the carrier's name on this date" queries.

## Future state

Azure v2: Delta Lake MERGE INTO enables genuine SCD2 with real change detection.
