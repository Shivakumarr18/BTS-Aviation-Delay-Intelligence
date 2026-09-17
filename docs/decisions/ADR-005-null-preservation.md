"# ADR-005: NULL Preservation Policy"

# ADR-005: NULL Preservation — Never Impute Delay Cause NULLs

## Decision

NULL values in delay cause columns are preserved exactly as received from BTS.
NULLs are never filled with zero or any other value.

## Why we chose this

NULL in BTS delay cause columns means the carrier did not report a cause.
It does NOT mean zero delay minutes.
Imputing NULL with zero would convert "unknown" into "no delay" — a false claim.
79.11% of flights have NULL delay causes. Imputing would corrupt the majority of the dataset.

## Why we rejected alternatives

Zero imputation: converts UNKNOWN to OBSERVED(0). Analytically dishonest.
Mean imputation: statistically unjustifiable for categorical delay attribution.
Forward fill: no temporal ordering logic applicable at flight grain.

## What this enables

Certified measure definitions can explicitly handle NULLs.
Bridge table only contains flights with at least one non-NULL cause.
AI Analyst can correctly state "delay cause unknown" rather than "no delay cause."

## What this constrains

SUM(delay_cause_mins) must always filter IS NOT NULL explicitly.
Aggregate measures must document NULL exclusion in semantic layer.

## Future state

NULL handling rules locked. Will not change in Azure v2.
