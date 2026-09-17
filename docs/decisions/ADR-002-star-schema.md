# ADR-002: Star Schema over Flat Table

## Decision

Kimball Star Schema — fact_delays + 5 dimensions + bridge table.

## Why we chose this

Flat tables force repeated scanning of all columns for every query.
Star schema enables reusable dimension filtering and simpler analytical joins.
Physical partitioning and partition pruning are handled separately in the storage design —
these are not inherent properties of the star schema itself.
Conformed dimensions (dim_airport) can be reused across multiple fact relationships.
Kimball is the industry standard for analytical data warehouses.

## Why we rejected alternatives

Wide flat table: no reusability, poor query performance, no role-playing dimensions.
Snowflake schema: unnecessary joins for this dataset size and query pattern.

## What this enables

Power BI relationships follow the star directly.
AI Analyst can traverse certified join paths without freestyle SQL.
Bridge table handles multi-cause delay attribution without grain distortion.

## What this constrains

Requires explicit relationship management in Power BI.
dim_airport role-playing requires USERELATIONSHIP() DAX for destination queries.

## Future state

SCD2 dimensions via Delta Lake MERGE INTO in Azure v2.
