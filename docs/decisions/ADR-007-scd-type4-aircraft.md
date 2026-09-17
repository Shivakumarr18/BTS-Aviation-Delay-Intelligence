"# ADR-007: SCD Type 4 for dim_aircraft"

# ADR-007: Aircraft Dimension — Tail Number Only Key

## Decision

dim_aircraft keyed by tail_number ONLY. carrier_code excluded from business key.

## Why we chose this

One physical aircraft can appear under different operators across its lifetime.
Including carrier_code in the key creates one-to-many join risk on fact table.
ADR-GOLD-006 confirms: carrier relationship belongs in fact via carrier_key, not in dim_aircraft.

## Why we rejected alternatives

Composite key (tail_number + carrier_code): causes join fan-out.
One row per tail+carrier combination: duplicates physical aircraft across carriers.

## What this enables

Clean one-to-one join from fact_delays to dim_aircraft on aircraft_key.
Tail number cascade analysis across carriers without duplication.
48,139 NULL tail flights safely routed to UNKNOWN member (aircraft_key = -1).

## What this constrains

Cannot track "which carrier operated this tail on this date" from dim_aircraft alone.
Carrier context must be joined via fact_delays.carrier_key → dim_carrier.

## Future state

Azure v2: enrich dim_aircraft with FAA registration data.
Add aircraft_type, manufacturer, year_of_manufacture, fleet_size.
