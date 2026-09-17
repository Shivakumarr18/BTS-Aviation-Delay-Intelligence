"# ADR-004: Aviation Domain Columns in dim_airport"

# ADR-004: Airport Domain Columns — city and state only

## Decision

dim_airport contains: airport_key, airport_code, city, state.
No airport_name column in v1.

## Why we chose this

BTS source data provides city and state but not a separate airport_name field.
city column contains the full display label (e.g. "Allentown/Bethlehem/Easton, PA").
Adding an unmaintained airport_name lookup risks introducing stale or incorrect data.

## Why we rejected alternatives

Hardcoded airport name lookup: maintenance burden. 362 airports. Names change.
External API enrichment: out of scope for v1. Introduces dependency.

## What this enables

Clean, source-faithful dimension. Every column is OBSERVED or DERIVED from BTS.
No invented data in the dimension.

## What this constrains

Power BI displays airport_code + city rather than a clean airport name.
Analysts must know IATA codes or use city for display.

## Future state

Azure v2: enrich dim_airport with FAA airport name lookup.
Add airport_name, airport_type, latitude, longitude.
