# ADR-001: Surrogate Key Strategy

## Decision

monotonically_increasing_id() for v1. SHA-256 deterministic keys deferred to Azure v2.

## Why we chose this

SHA-256 via Python UDF causes worker crashes on Windows local machine with 20.9M rows.
monotonically_increasing_id() is Spark-native and memory-safe for local development.

## Why we rejected alternatives

SHA-256 is deterministic — the same canonical input always produces the same hash.
The problem is that we cannot currently guarantee a stable canonical business-key
representation across pipeline runs, and the Python UDF implementation caused
worker failures on local Windows with 20.9M rows.
monotonically_increasing_id() produces unique IDs within a single DataFrame execution,
but values are run-specific and will differ across pipeline rebuilds.

## What this enables

Unique surrogate keys per run. GCG 06 verifies key uniqueness on every pipeline execution.

## What this constrains

Keys are NOT stable across pipeline rebuilds.
Joining Gold artifacts from two separate pipeline runs is unsafe.
Cross-run key references must not be assumed.

## Future state

Azure v2: persistent key management in Delta Lake.
Stable deterministic keys using SHA-256 over canonical business key columns.
