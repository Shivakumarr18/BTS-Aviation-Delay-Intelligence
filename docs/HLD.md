# High-Level Design (HLD)

# BTS Aviation Delay Intelligence Platform

**Version:** 1.0
**Status:** Complete — Azure Validated
**Date:** September 2026
**Author:** Narsing Shiva Kumar

---

## 1. Problem Statement

Airlines generate millions of flight records every year.
The US Bureau of Transportation Statistics (BTS)
publishes this data monthly — raw CSV files with no
structure, no validation, no analytical layer.

**The core question this system answers:**

> "Which flights delayed, why did they delay,
> how much did it cost, and what patterns repeat
> across carriers, airports, and time?"

Without a trusted pipeline, this question cannot be
answered reliably. Raw BTS data has:

- No enforced schema
- No validated business rules
- No analytical model
- No cost context
- No domain knowledge embedded

This system solves all five.

## Why domain knowledge matters:

Every metric in this system is justified
by real IOC operations. The IOC makes
decisions across three pillars -- Safety,
Legality, and Efficiency -- in that exact
priority order. Every delay cause column
in BTS maps to one of these pillars.
CARRIER_DELAY and LATE_AIRCRAFT_DELAY
map to Efficiency (airline-associated).
WEATHER_DELAY maps to Safety (external).
NAS_DELAY and SECURITY_DELAY map to
Legality (regulatory). This mapping
is project-defined -- not a BTS or FAA
classification. It is an analytical
taxonomy inspired by operational concepts.

---

## 2. Design Goals

| Priority | Goal                                                          |
| -------- | ------------------------------------------------------------- |
| 1        | Correctness — every number must be defensible                 |
| 2        | Reliability — silent failures are not acceptable              |
| 3        | Auditability — full lineage from raw CSV to dashboard         |
| 4        | Honesty — no fabricated metrics, no inflated claims           |
| 5        | Clarity — errors must explain what broke, where, and why      |
| 6        | Reliability over speed — correctness first, performance after |

---

## 3. Data Source

| Property | Detail                                                 |
| -------- | ------------------------------------------------------ |
| Source   | US Bureau of Transportation Statistics (BTS TranStats) |
| Dataset  | On-Time Performance — Reporting Carrier                |
| Coverage | January 2023 — December 2025 (3 years)                 |
| Volume   | 20,928,599 rows confirmed across 36 monthly partitions |
| Format   | CSV, one file per month                                |
| Columns  | 37 selected from 43+ available                         |
| Download | transtats.bts.gov                                      |

**Why 2023–2025:**
Post-COVID normal operations baseline. All five delay
cause columns consistently populated. Mature OCC
reporting standards. Valid year-over-year comparison.
Pre-2020 data excluded — inconsistent reporting
standards and fewer delay cause fields.

---

## 4. System Architecture

### Data Flow

BTS CSV Files (36 files, ~4.5 GB raw)
│
▼
┌─────────────────────────────────────┐
│ BRONZE LAYER │
│ PySpark — Append-only ingestion │
│ Partition: year + month │
│ Format: Parquet │
│ Idempotency: partition check │
│ Storage: ADLS Gen2 │
└─────────────────────────────────────┘
│
▼
┌─────────────────────────────────────┐
│ SILVER LAYER │
│ PySpark — Validation + Transform │
│ 12 validation gates per partition │
│ NULL preservation enforced │
│ Deduplication applied │
│ Pattern: DELETE + INSERT │
│ Partition: year + month │
│ Format: Parquet │
│ Storage: ADLS Gen2 │
└─────────────────────────────────────┘
│
▼
┌─────────────────────────────────────┐
│ GOLD LAYER │
│ PySpark → Kimball Star Schema │
│ Surrogate key assignment │
│ Foreign key validation │
│ 10-check Gold Completion Gate │
│ Format: Parquet │
│ Storage: ADLS Gen2 │
│ Compute: Azure Databricks │
└─────────────────────────────────────┘
│
▼
┌─────────────────────────────────────┐
│ SEMANTIC LAYER │
│ Business definitions │
│ Certified measures │
│ Evidence boundaries │
│ OBSERVED / DERIVED / MODELED / │
│ INFERRED / UNKNOWN framework │
└─────────────────────────────────────┘
│
▼
┌─────────────────────────────────────┐
│ ANALYTICS LAYER │
│ Power BI — 5 dashboard pages │
│ Connected via Databricks connector│
│ Import mode — 20.9M rows │
└─────────────────────────────────────┘
│
▼
┌─────────────────────────────────────┐
│ INTELLIGENCE LAYER [PLANNED] │
│ REST API │
│ AI Analyst interface │
│ Text → Semantic → SQL → Evidence │
└─────────────────────────────────────┘

### Reliability Layer (across all layers)

- Errors as a UI: every failure says WHAT, WHERE,
  WHY, and HOW TO FIX
- Silver Completion Gate: 12 checks per partition
- Gold Completion Gate: 10 checks after full run
- Bronze immutability: append-only, never modified

---

## 5. Technology Stack

| Component       | Technology            | Reason                                   |
| --------------- | --------------------- | ---------------------------------------- |
| Processing      | PySpark 3.5.0         | 20.9M rows exceeds pandas threshold      |
| Storage (raw)   | ADLS Gen2 · Parquet   | Columnar, compressed, partition-aware    |
| Storage (gold)  | ADLS Gen2 · Parquet   | Kimball star schema in Parquet format    |
| Compute         | Azure Databricks      | Managed Spark. Standard_F4. East US.     |
| Dashboard       | Power BI              | Connected via Databricks connector       |
| Language        | Python 3.11           | PySpark, validation logic, pipeline code |
| Version control | Git / GitHub          | All code, docs, ADRs versioned           |
| Environment     | Local → Azure         | Local development validated before cloud |
| Orchestration   | Azure Data Factory    | Planned v2                               |
| Future          | REST API · AI Analyst | Planned after Power BI                   |

### Confirmed Validation Results

> Health check run: August 1, 2026
> Duration: 127 seconds
> Dataset: 20,928,599 rows across 36 files

| Check                    | Result | Detail                         |
| ------------------------ | ------ | ------------------------------ |
| File count               | PASS   | 36 files confirmed             |
| Schema consistency       | PASS   | All 36 identical, 37 columns   |
| Total rows               | PASS   | 20,928,599 confirmed           |
| Mandatory NULL columns   | PASS   | 0 NULLs in 18 identity columns |
| Delay cause NULL pattern | PASS   | 79.11% NULL (expected ~80%)    |
| ARR_DEL15 business rule  | PASS   | 0 violations across 20.9M rows |
| Year distribution        | PASS   | 2023/2024/2025 evenly split    |
| Carrier distribution     | PASS   | 15 unique carriers confirmed   |
| TAIL_NUM NULLs           | PASS   | 48,139 rows (0.23%) — use -1   |
| Full NULL profile        | PASS   | All 37 columns profiled        |
| Total checks             | 12/12  | Zero warnings. Zero failures.  |

---

## 6. Medallion Architecture

### Bronze Layer — Raw Ingestion

- Append-only. Raw BTS CSV data. Never modified.
- Partition: YEAR + MONTH
- Format: Parquet on ADLS Gen2
- Idempotency: partition existence check before write
- Schema enforced on read via defined PySpark StructType
- No transformations. No business logic. Data as-is.
- Status: ✅ COMPLETE — 36/36 partitions. 20,928,599 rows.

### Silver Layer — Validation + Transformation

- 12-dimension data quality validation gates per partition
- Silver Completion Gate after all 36 partitions
- Type casting (FL_DATE string → DateType,
  ARR_DEL15 double → IntegerType)
- NULL preservation per documented policy (ADR-005)
- Column renaming BTS → business names (ADR-008)
- FLIGHTS column dropped (ADR-010)
- Pattern: DELETE partition → INSERT clean records
- Errors fail loudly with WHAT / WHERE / WHY /
  HOW TO FIX — never silent
- Status: ✅ COMPLETE — v4.0 FROZEN. 36/36. 20,928,599 rows.

### Gold Layer — Analytical Model

- Kimball Star Schema: fact_delays + 5 dimensions +
  bridge table + 2 modeled tables
- Surrogate key assignment (monotonically_increasing_id)
- Foreign key validation with UNKNOWN member routing
- 10-check Gold Completion Gate
- Evidence boundary enforcement: OBSERVED / DERIVED /
  MODELED / INFERRED / UNKNOWN
- Status: ✅ COMPLETE — Azure validated September 13, 2026.
  GCG: 10/10 PASSED.

---

## 7. Star Schema

Full design in data_model.md

| Table                      | Type      | SCD      | Actual Rows |
| -------------------------- | --------- | -------- | ----------- |
| fact_delays                | Fact      | N/A      | 20,928,599  |
| dim_carrier                | Dimension | Snapshot | 16          |
| dim_airport                | Dimension | Snapshot | 363         |
| dim_date                   | Dimension | Static   | 1,097       |
| dim_delay_reason           | Dimension | Type 1   | 6           |
| dim_aircraft               | Dimension | Snapshot | 6,685       |
| bridge_flight_delay_reason | Bridge    | N/A      | 7,072,280   |
| model_cost_scenario        | Modeled   | N/A      | 1           |
| model_delay_cost           | Modeled   | N/A      | 20,928,599  |

**Grain:** One row = one scheduled flight per calendar day

**Key GCG results:**

- Grain duplicates: 0
- NULL foreign keys: 0
- Arrival delay minutes (Silver = Gold): 152,637,336
- Cancellations (Silver = Gold): 287,134
- Bridge rows: 7,072,280

---

## 8. Non-Functional Requirements

### Correctness

- Zero silent failures at any layer
- Every pipeline error includes:
  WHAT broke, WHERE it broke,
  WHY it broke, HOW TO FIX it
- Business rules validated in Silver layer
  before Gold layer receives any data

### Auditability

- Bronze layer is immutable — raw data
  preserved exactly as received from BTS
- Full data lineage: CSV → Bronze → Silver
  → Gold → Semantic Layer → Power BI
- Every schema decision recorded in ADRs
- Gold Completion Gate evidence committed
  to GitHub: docs/evidence/

### Idempotency

- Bronze: partition existence check
  (skip if already ingested)
- Silver: DELETE + INSERT
  (safe to rerun — no duplicates)
- Gold: full overwrite per run
  (safe to rerun — partition replaced)
- Any layer can be rerun without corrupting
  downstream data

### CAP Theorem Decisions

- Analytics layer (Gold + Dashboard): AP
  Availability prioritized over strict consistency.
  24-hour batch data — eventual consistency
  is acceptable.

- Silver validation layer: CP
  Consistency required. Validation failures
  reject data rather than allowing stale or
  incorrect records through to Gold.
  System fails loudly. Never serves wrong data.

### Scalability

**Current scale: 20.9M rows — Azure Databricks Standard_F4**

Partitioning:
Partition by year + month = 36 partitions.
Enables partition pruning — queries scan
only relevant months, not full 20.9M rows.

Future scaling decisions documented in ADRs.

---

## 9. Data Quality Rules

### Core Business Rules

**Rule 1 — Delay cause NULL preservation (CRITICAL):**
When ARR_DEL15 = 0, all five delay cause columns
MUST be NULL. Validated across 20,928,599 rows.
0 violations. These NULLs must NEVER be replaced with 0.

**Rule 2 — ARR_DELAY NULL conditions:**
ARR_DELAY is NULL when CANCELLED = 1 OR DIVERTED = 1.
A cancelled flight never arrived.
Preserve NULL. Never substitute 0.

**Rule 3 — CANCELLATION_CODE conditions:**
CANCELLATION_CODE is NULL when CANCELLED = 0.
A = Carrier, B = Weather, C = NAS, D = Security.

**Rule 4 — Uniqueness:**
Each flight on each date must appear exactly once.
Unique key: FL_DATE + OP_UNIQUE_CARRIER +
OP_CARRIER_FL_NUM + ORIGIN + DEST.
GCG 03: 0 grain duplicates confirmed.

**Rule 5 — Completeness:**
Core identity columns must never be NULL.
GCG 04: 0 NULL foreign keys confirmed.

### Silver Validation Gate

12 checks per partition. Silver Completion Gate after all 36.
Any violation raises a structured error:
[ERROR_TYPE] | Layer | Rule | Violations found |
Expected | Likely cause | Recommended action.
Pipeline halts. Gold layer never receives bad data.

---

## 10. Cost Sensitivity Framework

### Approach

MODELED financial exposure using observed delay
patterns + external cost assumption.

**Formula:**
Estimated Cost Exposure =
Total Positive Arrival Delay Minutes (OBSERVED from Gold) ×
$45 per delay minute (MODELED — Ferguson et al.)

### Citation

Ferguson, J. et al. — "Total Delay Impact Study"
(FAA/NEXTOR, 2010).
$45/min used as directional reference only.
Not actual airline accounting cost.

### Honesty Principle

> All cost estimates are MODELED.
> Always labeled as estimates, never as observed costs.
> Separate modeled tables (ADR-GOLD-005) enforce
> the observed ≠ modeled boundary structurally.

---

## 11. What This System Does

- Ingests 3 years of US domestic flight delay data
- Validates data quality across 12 dimensions per partition
- Preserves all NULL values with documented reasoning
- Builds a Kimball star schema analytical model on Azure
- Surfaces delay patterns by carrier, airport,
  route, time, and delay cause
- Provides cost exposure estimates using
  real delay patterns and Ferguson et al. assumption
- Maps delay causes to IOC operational pillars
  (project-defined: Safety, Legality, Efficiency)
- Delivers 5 Power BI dashboard pages with
  explicit evidence boundaries

---

## 12. What This System Does NOT Do

- Does not predict future delays (descriptive only)
- Does not process non-US or international flights
- Does not connect to live airline systems
- Does not ingest real-time data (batch only, v1)
- Does not store personally identifiable information
- Does not fabricate or impute missing delay values
- Does not present modeled costs as observed airline loss
- Does not claim IOC pillar mapping is a BTS classification

---

## 13. Completed Milestones

| Milestone            | Date               | Evidence                          |
| -------------------- | ------------------ | --------------------------------- |
| Bronze complete      | August 2026        | 36/36 partitions. 20,928,599 rows |
| Silver v4.0 frozen   | August 2026        | 36/36. 12 gates. Brother: 9.5/10  |
| Gold local TEST_MODE | August 2026        | 8/8 TCG. Stratified 100K sample   |
| Gold Azure complete  | September 13, 2026 | GCG 10/10. Azure Databricks.      |
| Semantic Layer v1.0  | September 15, 2026 | Code-verified. Brother: 9.2/10    |
| Power BI — 5 pages   | September 17, 2026 | Innovate theme. DAX certified.    |

---

## 14. Planned Next Steps

| Stage                | Status     |
| -------------------- | ---------- |
| REST API             | 🔲 Planned |
| AI Analyst interface | 🔲 Planned |
| Azure Data Factory   | 🔲 Planned |
| CI/CD pipeline       | 🔲 Planned |

---

## 15. Repository Structure

BTS-Aviation-Delay-Intelligence/
│
├── README.md
│
├── docs/
│ ├── HLD.md
│ ├── data_model.md
│ ├── ai_response_contract.md
│ ├── evidence/
│ │ └── gold_azure_evidence_2026_09_13.txt
│ ├── semantic/
│ │ └── BTS_SemanticLayer_v1_CodeVerified.docx
│ └── decisions/
│ ├── ADR-001-surrogate-keys.md
│ ├── ADR-002-star-schema.md
│ ├── ADR-003-scd-type2-carriers.md
│ ├── ADR-004-airport-domain-columns.md
│ ├── ADR-005-null-preservation.md
│ ├── ADR-006-ioc-pillar-mapping.md
│ ├── ADR-007-scd-type4-aircraft.md
│ ├── ADR-008-column-renaming-strategy.md
│ ├── ADR-009-parquet-over-csv.md
│ └── ADR-010-flights-column-dropped.md
│
├── governance/
│ └── data_principles.md
│
├── pipeline/
│ ├── bronze/
│ │ └── bronze_ingestion.py
│ ├── silver/
│ │ └── silver_transform.py
│ └── gold/
│ └── gold_star_schema.py
│
├── reports/
│ ├── screenshots/
│ └── powerbi/
│
├── config/
│ └── pipeline_config.py
│
├── data/
│ └── raw/ ← gitignored
│
├── .gitignore
└── requirements.txt

---

## 16. Engineering Principles

1. **Errors as a UI** — every failure explains
   WHAT broke, WHERE, WHY, and HOW TO FIX.
   Silent failures are not acceptable.

2. **Trust is designed, not added** — governance,
   audit trail, and data quality checks are
   Day 1 architecture decisions.

3. **Preserve, never fabricate** — NULLs carry
   business meaning. Never substitute values
   without documented reasoning.

4. **Read before you build** — domain knowledge
   from Peter J. Bruce's Airline Operations Control
   informed every schema decision in this system.

5. **Idempotency is non-negotiable** — any layer
   can be safely rerun without corrupting
   downstream data or creating duplicates.

6. **Honest scope** — this document states clearly
   what the system does and does not do.
   No inflated claims. No fabricated metrics.

7. **Evidence over adjectives** — every claim is
   classified as OBSERVED, DERIVED, MODELED,
   INFERRED, or UNKNOWN. Never assume.

---

## 17. Platform Boundaries

### What This Platform Demonstrates

- Historical delay patterns (2023-2025)
- Operational relationships between
  carriers, airports, routes, and aircraft
- Delay-driver analysis by IOC pillar (project-defined)
- Aircraft delay-propagation patterns
  via tail number tracking
- Historical decision-support intelligence

### What This Platform Does Not Claim

- Real-time IOC optimization
- Live crew legality assessment
- Live aircraft or maintenance status
- Live weather or ATC constraint handling
- Passenger connection impact analysis
- Causal claims beyond BTS reported attribution

### The Honest Positioning

We are building the trusted data and
intelligence foundation upon which
richer operational decision systems
could eventually be built.

Not pretending to build a complete
airline operational control system.

---

> Version 1.0 — Azure Validated — September 2026
> Gold layer complete: September 13, 2026
> Power BI complete: September 17, 2026
> Semantic Layer v1.0 complete: September 15, 2026
> Next: REST API → AI Analyst interface
