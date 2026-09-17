# Logical Data Model

**Project:** BTS Aviation Delay Intelligence Platform

Version: 1.0 | Status: Complete — Azure Validated
Last updated: September 2026

---

## 1. Purpose

This document describes the logical data model for the
BTS Aviation Delay Intelligence Platform.

It defines the analytical grain, fact and dimension tables,
SCD type decisions, NULL handling rules, and key modeling
decisions used to build the Gold layer.

All decisions are documented through ADRs in docs/decisions/.

---

## 2. Analytical Grain

### Grain — Locked

> "One record in fact_delays represents one scheduled
> flight on one calendar day as published by BTS."

**What this means:**

- Flight AA-101 on January 15 2024 = ONE row
- Flight AA-101 on January 16 2024 = DIFFERENT row
- Same flight number, different date = always different rows
- One flight with one origin and one destination per row

**Grain key (verified GCG 03 — 0 duplicates):**
flight_date + carrier_code + flight_number +
origin_airport + dest_airport

---

## 3. Star Schema Overview

```text
                    dim_date
                       │
                       │
dim_carrier ──── fact_delays ──── dim_airport (Origin)
                       │    ──── dim_airport (Destination)
                       │
                  dim_aircraft
                       │
              bridge_flight_delay_reason
                       │
              dim_delay_reason

Separate modeled layer:
fact_delays ──── model_delay_cost ──── model_cost_scenario
```

**Notes:**

- dim_airport appears TWICE in fact_delays
  (origin_airport_key and dest_airport_key)
  Conformed dimension — role-playing (ADR-002)
- fact_delays has NO delay_reason_key
  Multi-cause delays handled via bridge table (ADR-002)
- Cost model is separate from fact (ADR-GOLD-005)
  Observed delay minutes ≠ modeled financial exposure

---

## 4. SCD Type Decisions

| Dimension        | v1 Decision | Reason                                       |
| ---------------- | ----------- | -------------------------------------------- |
| dim_carrier      | Snapshot    | BTS has no attribute change events (ADR-003) |
| dim_airport      | Snapshot    | BTS has no attribute change events (ADR-003) |
| dim_date         | Static      | Calendar dates never change                  |
| dim_delay_reason | Type 1      | BTS delay categories are stable definitions  |
| dim_aircraft     | Snapshot    | Tail number only. No change history in BTS.  |

**Note on SCD2:**
SCD2 was deliberately deferred to Azure v2.
BTS does not provide attribute change events.
Claiming SCD2 without version detection is
architecturally dishonest. See ADR-003.

---

## 5. Fact Table — fact_delays

**Grain:** One scheduled flight per calendar day
**Rows:** 20,928,599 (verified GCG 02)
**Partitioned by:** flight_year + flight_month (36 partitions)
**Format:** Parquet on ADLS Gen2

| Column                         | Type      | Evidence  | Notes                                                |
| ------------------------------ | --------- | --------- | ---------------------------------------------------- |
| flight_id                      | string    | OBSERVED  | Composite grain key. monotonically_increasing_id()   |
| date_key                       | integer   | OBSERVED  | FK → dim_date.date_key (YYYYMMDD format)             |
| carrier_key                    | long      | OBSERVED  | FK → dim_carrier.carrier_key                         |
| origin_airport_key             | long      | OBSERVED  | FK → dim_airport.airport_key (origin role)           |
| dest_airport_key               | long      | OBSERVED  | FK → dim_airport.airport_key (destination role)      |
| aircraft_key                   | long      | OBSERVED  | FK → dim_aircraft.aircraft_key (-1 = Unknown)        |
| flight_date                    | date      | OBSERVED  | Calendar date of scheduled flight                    |
| carrier_code                   | string    | OBSERVED  | IATA carrier code. Denormalized.                     |
| flight_number                  | integer   | OBSERVED  | Carrier-assigned flight number                       |
| origin_airport                 | string    | OBSERVED  | Origin IATA code. Denormalized.                      |
| dest_airport                   | string    | OBSERVED  | Destination IATA code. Denormalized.                 |
| tail_number                    | string    | OBSERVED  | Aircraft registration. NULL for 48,139 flights.      |
| arr_delayed_flag               | integer   | OBSERVED  | 1=delayed. 0=not delayed. NULL=cancelled.            |
| dep_delayed_flag               | integer   | OBSERVED  | 1=delayed. 0=not delayed. NULL=cancelled.            |
| is_cancelled                   | integer   | OBSERVED  | 1=cancelled. 0=operated.                             |
| is_diverted                    | integer   | OBSERVED  | 1=diverted to different airport.                     |
| arr_delay_mins                 | double    | OBSERVED  | Signed. Negative=early. NULL=cancelled.              |
| dep_delay_mins                 | double    | OBSERVED  | Signed. Negative=early. NULL=cancelled.              |
| arr_delay_abs_mins             | double    | DERIVED   | ABS(arr_delay_mins). Used in cost model only.        |
| dep_delay_abs_mins             | double    | DERIVED   | ABS(dep_delay_mins). Magnitude only.                 |
| carrier_delay_mins             | double    | OBSERVED  | BTS-reported. NULL≠zero. Carrier self-reporting.     |
| weather_delay_mins             | double    | OBSERVED  | BTS-reported. NULL≠zero.                             |
| nas_delay_mins                 | double    | OBSERVED  | BTS-reported. NULL≠zero.                             |
| security_delay_mins            | double    | OBSERVED  | BTS-reported. NULL≠zero.                             |
| late_aircraft_delay_mins       | double    | OBSERVED  | BTS-reported. NULL≠zero. Propagation indicator.      |
| efficiency_attributed_mins     | double    | DERIVED   | carrier_delay_mins + late_aircraft_delay_mins        |
| safety_attributed_mins         | double    | DERIVED   | weather_delay_mins. Project IOC mapping.             |
| legality_attributed_mins       | double    | DERIVED   | nas_delay_mins + security_delay_mins.                |
| dominant_delay_pillar          | string    | DERIVED   | Safety/Legality/Efficiency/None. Project-defined.    |
| dominant_pillar_tie            | boolean   | DERIVED   | True if ≥2 pillars tied for max minutes.             |
| operational_influence_class    | string    | DERIVED   | INTERNAL/EXTERNAL/MIXED/UNKNOWN. Not controllable.   |
| dominant_influence_class       | string    | DERIVED   | Dominant influence when internal≠external.           |
| has_mixed_influence            | boolean   | DERIVED   | True when both internal and external present.        |
| cancellation_code              | string    | OBSERVED  | A=Carrier B=Weather C=NAS D=Security. NULL if not.   |
| cancellation_pillar            | string    | DERIVED   | IOC pillar from cancellation_code. Project-defined.  |
| scheduled_elapsed_mins         | double    | OBSERVED  | Scheduled flight duration in minutes.                |
| actual_elapsed_mins            | double    | OBSERVED  | Actual flight duration. NULL if cancelled.           |
| schedule_elapsed_variance_mins | double    | DERIVED   | scheduled - actual. Positive=shorter than scheduled. |
| air_time_mins                  | double    | OBSERVED  | Wheels-off to wheels-on. Excludes taxi.              |
| distance_miles                 | double    | OBSERVED  | Route distance in statute miles.                     |
| silver_processed_ts            | timestamp | TECHNICAL | Pipeline metadata. Do not expose in BI or AI.        |
| gold_processed_ts              | timestamp | TECHNICAL | Pipeline metadata. Do not expose in BI or AI.        |
| flight_year                    | integer   | TECHNICAL | Partition column. Use dim_date.year for analysis.    |
| flight_month                   | integer   | TECHNICAL | Partition column. Use dim_date.month for analysis.   |

**Critical business rule:**

> When arr_delayed_flag = 0, all five delay cause columns
> MUST be NULL. Validated across 20,928,599 rows: 0 violations.
> NULL means BTS did not report a cause. NOT the same as zero.
> Never fill delay cause NULLs with zero. See ADR-005.

---

## 6. Dimension Tables

### dim_carrier (Snapshot v1)

| Column            | Type      | Notes                                       |
| ----------------- | --------- | ------------------------------------------- |
| carrier_key       | long      | Surrogate PK. monotonically_increasing_id() |
| carrier_code      | string    | IATA 2-letter code e.g. "AA"                |
| carrier_name      | string    | Full airline name                           |
| record_type       | string    | SNAPSHOT_V1 or UNKNOWN_MEMBER               |
| is_current        | boolean   | Always true in v1. SCD2 deferred.           |
| gold_processed_ts | timestamp | Pipeline metadata                           |

**Rows:** 16 (15 real carriers + 1 UNKNOWN member)
**UNKNOWN member:** carrier_key = -1

---

### dim_airport (Snapshot v1 — Conformed)

| Column            | Type      | Notes                              |
| ----------------- | --------- | ---------------------------------- |
| airport_key       | long      | Surrogate PK                       |
| airport_code      | string    | IATA 3-letter code e.g. "ATL"      |
| city              | string    | City + state label from BTS source |
| state             | string    | 2-letter state code                |
| record_type       | string    | SNAPSHOT_V1 or UNKNOWN_MEMBER      |
| is_current        | boolean   | Always true in v1. SCD2 deferred.  |
| gold_processed_ts | timestamp | Pipeline metadata                  |

**Rows:** 363 (362 real airports + 1 UNKNOWN member)
**UNKNOWN member:** airport_key = -1
**Role-playing:** Used twice in fact_delays as
origin_airport_key and dest_airport_key.

**Note on v1 scope:**
No airport_name column in v1. BTS source provides
city and state only. No invented enrichment data.
See ADR-004. FAA enrichment planned for v2.

---

### dim_date (Static)

| Column                | Type      | Notes                                          |
| --------------------- | --------- | ---------------------------------------------- |
| date_key              | integer   | YYYYMMDD format e.g. 20240115                  |
| full_date             | date      | Calendar date                                  |
| year                  | integer   | Calendar year                                  |
| quarter               | integer   | 1–4                                            |
| month                 | integer   | 1–12                                           |
| month_name            | string    | January–December                               |
| day_of_month          | integer   | 1–31                                           |
| day_of_week           | integer   | 1=Sunday 7=Saturday (Spark F.dayofweek)        |
| day_name              | string    | Sunday–Saturday                                |
| is_weekend            | boolean   | True when day_of_week IN (1,7)                 |
| season                | string    | Winter/Spring/Summer/Fall                      |
| holiday_travel_window | string    | Approximate travel windows. NULL = other days. |
| record_type           | string    | STATIC or UNKNOWN_MEMBER                       |
| gold_processed_ts     | timestamp | Pipeline metadata                              |

**Rows:** 1,097 (Jan 2023 – Dec 2025 + 1 UNKNOWN member)

**holiday_travel_window values (verified from code):**

- Thanksgiving: Nov 20-30
- Christmas: Dec 20-31
- New Year: Jan 1-3
- July 4th: Jul 1-7
- Labor Day: Sep 1-7
- Memorial Day: May 24-31
- NULL = all other dates

**day_of_week encoding (verified from code):**
Spark F.dayofweek() default.
1=Sunday, 2=Monday … 7=Saturday.
is_weekend = isin(1,7) confirms Sunday=1, Saturday=7.

---

### dim_delay_reason (SCD Type 1)

| Column                      | Type      | Notes                                       |
| --------------------------- | --------- | ------------------------------------------- |
| delay_reason_key            | integer   | Hardcoded: 1-5 + UNKNOWN=-1                 |
| delay_code                  | string    | BTS category code                           |
| delay_category              | string    | BTS category name                           |
| ioc_pillar                  | string    | Project-defined: Safety/Legality/Efficiency |
| operational_influence_class | string    | Project-defined: INTERNAL/EXTERNAL/UNKNOWN  |
| bts_source_column           | string    | Source BTS column name                      |
| record_type                 | string    | TYPE1_LOOKUP or UNKNOWN_MEMBER              |
| gold_processed_ts           | timestamp | Pipeline metadata                           |

**Rows:** 6 (5 BTS codes + 1 UNKNOWN member)

**IOC Pillar Mapping (project-defined — not BTS classification):**

| delay_reason_key | delay_code    | ioc_pillar | influence_class     |
| ---------------- | ------------- | ---------- | ------------------- |
| 1                | CARRIER       | Efficiency | INTERNAL_ASSOCIATED |
| 2                | WEATHER       | Safety     | EXTERNAL_ASSOCIATED |
| 3                | NAS           | Legality   | EXTERNAL_ASSOCIATED |
| 4                | SECURITY      | Legality   | EXTERNAL_ASSOCIATED |
| 5                | LATE_AIRCRAFT | Efficiency | INTERNAL_ASSOCIATED |
| -1               | UNKNOWN       | None       | UNKNOWN             |

**Critical note:**
ioc_pillar is PROJECT-DEFINED analytical taxonomy.
Not an FAA classification. Not a BTS classification.
Not a universal IOC standard. See ADR-006.

---

### dim_aircraft (Snapshot v1)

| Column            | Type      | Notes                                |
| ----------------- | --------- | ------------------------------------ |
| aircraft_key      | long      | Surrogate PK                         |
| tail_number       | string    | Aircraft registration. Business key. |
| record_type       | string    | SNAPSHOT_V1 or UNKNOWN_MEMBER        |
| is_current        | boolean   | Always true in v1.                   |
| gold_processed_ts | timestamp | Pipeline metadata                    |

**Rows:** 6,685 (6,684 real tail numbers + 1 UNKNOWN member)
**UNKNOWN member:** aircraft_key = -1
Handles 48,139 NULL tail number flights (0.23%).

**Key decision (ADR-007):**
Keyed by tail_number ONLY — not carrier_code.
Many-to-one relationship from fact_delays to dim_aircraft.
A physical aircraft can appear under different operators.
Including carrier creates join fan-out. See ADR-007.

**v1 limitation:**
No aircraft type, age, or manufacturer data.
Tail number only. FAA enrichment planned for v2.

---

### bridge_flight_delay_reason

| Column                      | Type      | Evidence  | Notes                                       |
| --------------------------- | --------- | --------- | ------------------------------------------- |
| flight_id                   | string    | OBSERVED  | FK → fact_delays.flight_id                  |
| delay_reason_key            | integer   | OBSERVED  | FK → dim_delay_reason.delay_reason_key      |
| delay_code                  | string    | OBSERVED  | Denormalized BTS delay code                 |
| ioc_pillar                  | string    | DERIVED   | Denormalized from dim_delay_reason          |
| operational_influence_class | string    | DERIVED   | Denormalized from dim_delay_reason          |
| attributed_mins             | double    | OBSERVED  | Delay minutes for this cause on this flight |
| attribution_pct             | double    | DERIVED   | attributed_mins / total for flight × 100    |
| gold_processed_ts           | timestamp | TECHNICAL | Pipeline metadata                           |

**Rows:** 7,072,280 (verified GCG 10)
**Grain:** One flight × one reported BTS delay reason

**Why bridge table (ADR-002):**
One flight can have multiple reported delay causes.
Single FK in fact discards real information.
Bridge preserves all causes without changing fact grain.

**CRITICAL — double count rule:**
Summing attributed_mins across multiple delay_codes
for the same flight double-counts.
Always filter by one delay_code or ioc_pillar
when aggregating bridge delay minutes.

---

### model_cost_scenario

| Column                | Type      | Evidence  | Notes                                     |
| --------------------- | --------- | --------- | ----------------------------------------- |
| cost_scenario_key     | integer   | MODELED   | Surrogate PK (=1 for default)             |
| scenario_name         | string    | MODELED   | REFERENCE_45_USD                          |
| cost_per_delay_minute | double    | MODELED   | $45.00 (Ferguson et al. FAA/NEXTOR 2010)  |
| currency              | string    | MODELED   | USD                                       |
| assumption_note       | string    | MODELED   | Source and limitations documented in data |
| is_default            | boolean   | MODELED   | True for primary scenario                 |
| gold_processed_ts     | timestamp | TECHNICAL | Pipeline metadata                         |

**Rows:** 1
**All values MODELED. See ADR-GOLD-005.**

---

### model_delay_cost

| Column                | Type      | Evidence  | Notes                                      |
| --------------------- | --------- | --------- | ------------------------------------------ |
| flight_id             | string    | OBSERVED  | FK → fact_delays                           |
| cost_scenario_key     | integer   | MODELED   | FK → model_cost_scenario                   |
| scenario_name         | string    | MODELED   | Denormalized                               |
| cost_per_delay_minute | double    | MODELED   | Denormalized assumption value              |
| currency              | string    | MODELED   | USD                                        |
| estimated_delay_cost  | double    | MODELED   | arr_delay_abs_mins × cost_per_delay_minute |
| evidence_state        | string    | MODELED   | Literal "MODELED" stored in every row      |
| gold_processed_ts     | timestamp | TECHNICAL | Pipeline metadata                          |

**Rows:** 20,928,599
**Formula:** arr_delay_abs_mins × $45
**CRITICAL:** Never present estimated_delay_cost as
actual or observed airline cost. Always MODELED.

---

## 7. NULL Handling Rules

### 7.1 Confirmed NULL Statistics (verified August 1, 2026)

| Column              | NULLs      | NULL % | Status   |
| ------------------- | ---------- | ------ | -------- |
| YEAR                | 0          | 0.00%  | OK       |
| MONTH               | 0          | 0.00%  | OK       |
| FL_DATE             | 0          | 0.00%  | OK       |
| OP_UNIQUE_CARRIER   | 0          | 0.00%  | OK       |
| TAIL_NUM            | 48,139     | 0.23%  | LOW      |
| ORIGIN              | 0          | 0.00%  | OK       |
| DEST                | 0          | 0.00%  | OK       |
| ARR_DELAY           | 340,445    | 1.63%  | EXPECTED |
| ARR_DEL15           | 340,445    | 1.63%  | EXPECTED |
| CANCELLED           | 0          | 0.00%  | OK       |
| CANCELLATION_CODE   | 20,641,465 | 98.63% | EXPECTED |
| CARRIER_DELAY       | 16,557,293 | 79.11% | EXPECTED |
| WEATHER_DELAY       | 16,557,293 | 79.11% | EXPECTED |
| NAS_DELAY           | 16,557,293 | 79.11% | EXPECTED |
| SECURITY_DELAY      | 16,557,293 | 79.11% | EXPECTED |
| LATE_AIRCRAFT_DELAY | 16,557,293 | 79.11% | EXPECTED |

### 7.2 NULL Business Rules

| Column              | NULL Meaning            | Rule                                |
| ------------------- | ----------------------- | ----------------------------------- |
| TAIL_NUM            | Not reported by airline | aircraft_key = -1 (UNKNOWN member)  |
| ARR_DELAY           | Cancelled or diverted   | NULL when CANCELLED=1 or DIVERTED=1 |
| ARR_DEL15           | Cancelled or diverted   | NULL when CANCELLED=1 or DIVERTED=1 |
| CANCELLATION_CODE   | Flight not cancelled    | NULL when CANCELLED = 0             |
| CARRIER_DELAY       | Flight on time          | NULL when ARR_DEL15 = 0             |
| WEATHER_DELAY       | Flight on time          | NULL when ARR_DEL15 = 0             |
| NAS_DELAY           | Flight on time          | NULL when ARR_DEL15 = 0             |
| SECURITY_DELAY      | Flight on time          | NULL when ARR_DEL15 = 0             |
| LATE_AIRCRAFT_DELAY | Flight on time          | NULL when ARR_DEL15 = 0             |

### 7.3 Principle

> NULL values are preserved whenever they carry business meaning.
> Never replaced with 0 or any substitute value.
> Every NULL in this dataset has a documented operational reason.
> See ADR-005.

---

## 8. Partitioning Strategy

**Partition key:** flight_year + flight_month
**Number of partitions:** 36 (Jan 2023 → Dec 2025)
**Rows per partition:** ~581,000 average
**Format:** Parquet on ADLS Gen2

**Why year + month (not day, not carrier):**

| Option          | Partitions | Rows/partition | Decision      |
| --------------- | ---------- | -------------- | ------------- |
| By day          | 1,095      | ~19,000        | Too small     |
| By year + month | 36         | ~581,000       | ✅ Correct    |
| By carrier      | ~15        | ~1,395,000     | Hot-spot risk |
| No partitioning | 1          | 20,928,599     | Too large     |

---

## 9. Gold Completion Gate Results

All 10 checks passed on Azure Databricks — September 13, 2026.

| Check                         | Result | Value          |
| ----------------------------- | ------ | -------------- |
| GCG 01 — Artifacts exist      | PASS   | 9/9            |
| GCG 02 — Row count            | PASS   | 20,928,599     |
| GCG 03 — Grain uniqueness     | PASS   | 0 duplicates   |
| GCG 04 — NULL foreign keys    | PASS   | 0 NULLs        |
| GCG 05 — UNKNOWN members      | PASS   | All 5 dims     |
| GCG 06 — Surrogate key unique | PASS   | All dims       |
| GCG 07 — Partition count      | PASS   | 36/36          |
| GCG 08 — arr_delay_mins       | PASS   | 152,637,336    |
| GCG 09 — Cancellation count   | PASS   | 287,134        |
| GCG 10 — Bridge integrity     | PASS   | 7,072,280 rows |

---

## 10. Modeling Decisions

All major decisions documented in ADRs:

- ADR-001: Surrogate key strategy
- ADR-002: Star schema + bridge table
- ADR-003: Snapshot dimensions — not SCD2
- ADR-004: Airport domain columns — no invented data
- ADR-005: NULL preservation policy
- ADR-006: IOC pillar mapping — project-defined
- ADR-007: Aircraft keyed by tail_number only
- ADR-008: Column renaming BTS → business names
- ADR-009: Parquet over CSV
- ADR-010: FLIGHTS column dropped

---

> Version 1.0 — Azure Validated — September 2026
> Gold layer complete: September 13, 2026
> GCG: 10/10 PASSED
> All decisions tracked through ADRs.
> Every decision has a WHY. No decision is arbitrary.
