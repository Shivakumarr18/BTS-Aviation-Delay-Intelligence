# ✈️ BTS Aviation Delay Intelligence System

**20.9M flight records · 3 years · 36 monthly partitions · Azure**

 "The value is not the analytics itself. The value comes from whether the intelligence improves how people plan, decide, and operate."

An end-to-end aviation data engineering platform built using US Bureau of Transportation Statistics flight data. The system transforms raw flight records into a validated analytical model designed for downstream BI, APIs and eventually an AI interface..

[![GitHub](https://img.shields.io/badge/GitHub-Shivakumarr18-181717?style=flat&logo=github)](https://github.com/Shivakumarr18)
[![LinkedIn](https://img.shields.io/badge/LinkedIn-Connect-0A66C2?style=flat&logo=linkedin)](https://www.linkedin.com/)

---

## 🏗️ Architecture

| Stage                     | Status      |
| ------------------------- | ----------- |
| Source validation         | ✅ Complete |
| Bronze layer              | ✅ Complete |
| Silver layer              | ✅ Complete |
| Gold dimensional model    | ✅ Complete |
| Azure validation          | ✅ Complete |
| Semantic / business layer | ✅ Complete |
| Power BI analytics        | ✅ Complete |
| REST API                  | ✅ Complete |
| AI Analyst interface      | ✅ Complete |

### Data Flow

BTS TranStats — US Bureau of Transportation Statistics
January 2023 → December 2025 | 36 CSV files | ~4GB raw
│
▼
┌──────────────────────────────────────────────────────┐
│ BRONZE │
│ 36/36 partitions · 20,928,599 rows │
│ Immutable · Append-only · Parquet · YEAR/MONTH │
└──────────────────────┬───────────────────────────────┘
│
▼
┌──────────────────────────────────────────────────────┐
│ SILVER v4.0 · FROZEN │
│ 12 validation gates per partition │
│ 20,928,599 rows · NULLs preserved. Never filled. │
└──────────────────────┬───────────────────────────────┘
│
▼
┌──────────────────────────────────────────────────────┐
│ GOLD · Kimball Star Schema │
│ fact_delays + 5 dimensions + bridge table │
│ Cost model separated · IOC pillars mapped │
│ Azure Full Run: ✅ COMPLETE — Sep 13, 2026 │
│ GCG: 10/10 PASSED │
└──────────────────────────────────────────────────────┘
│
▼
┌──────────────────────────────────────────────────────┐
│ SEMANTIC LAYER v1.0 · Code-Verified │
│ Evidence boundaries · Certified measures │
│ OBSERVED / DERIVED / MODELED / INFERRED / UNKNOWN │
└──────────────────────────────────────────────────────┘
│
▼
┌──────────────────────────────────────────────────────┐
│ POWER BI · 5 Dashboard Pages │
│ Connected via Azure Databricks · Import mode │
│ 20.9M rows · Innovate theme │
└──────────────────────────────────────────────────────┘
│
▼
REST API · AI Analyst Interface [PLANNED]

---

## 📊 Scale

| Metric             |               Value |
| ------------------ | ------------------: |
| Source period      | Jan 2023 – Dec 2025 |
| Silver records     |      **20,928,599** |
| Monthly partitions |              **36** |
| Raw data           |               ~4 GB |
| Carriers           |                  15 |
| Airports           |                 362 |

---

## 🏆 Gold Layer — Azure Validation

The Gold layer was completed on Azure Databricks with 10 explicit completion gates.

| Validation                |           Result |
| ------------------------- | ---------------: |
| Gold artifacts            |   **9 / 9 PASS** |
| Completion gates          | **10 / 10 PASS** |
| Grain duplicates          |            **0** |
| NULL foreign keys         |            **0** |
| Unknown dimension members |    **Validated** |
| Surrogate-key uniqueness  |    **Validated** |
| Partitions                |      **36 / 36** |
| Arrival-delay minutes     |  **152,637,336** |
| Cancellations             |      **287,134** |
| Bridge records            |    **7,072,280** |

**Azure evidence captured:** September 13, 2026
**Evidence log:** [docs/evidence/Gold_Azure_Evidence](docs/evidence/Gold_Azure_Evidence)

---

## 🧱 Gold Model

| Artifact                     | Purpose                         |
| ---------------------------- | ------------------------------- |
| `dim_date`                   | Date analysis                   |
| `dim_carrier`                | Carrier analysis                |
| `dim_airport`                | Airport analysis (role-playing) |
| `dim_aircraft`               | Aircraft / tail-number analysis |
| `dim_delay_reason`           | Delay-cause analysis            |
| `fact_delays`                | Core flight-delay facts         |
| `bridge_flight_delay_reason` | Multi-cause delay relationships |
| `model_cost_scenario`        | Cost sensitivity assumptions    |
| `model_delay_cost`           | Modeled delay-cost outputs      |

---

## 📊 Power BI Dashboard — 5 Pages

**Connected via:** Azure Databricks · Unity Catalog · Import mode · 20.9M rows

### Page 1 — Operations Overview

![Operations Overview](tests/Screenshots/Operations_Overview.png)

### Page 2 — Carrier Performance

![Carrier Performance](tests/Screenshots/Carrier_Performance.png)

### Page 3 — Delay Cause Analysis

![Delay Cause Analysis](tests/Screenshots/Delay_Cause_Analysis.png)

### Page 4 — Airport Exposure

![Airport Exposure](tests/Screenshots/Aiport_Exposure.png)

### Page 5 — Cost Sensitivity (Estimated)

![Cost Sensitivity](tests/Screenshots/Modeled_delay_Cost.png)

> ⚠ Page 5 cost figures are MODELED estimates.
> $45/min assumption — Ferguson et al. FAA/NEXTOR 2010.
> Not actual airline financial loss.

---

## 🧠 Engineering Principles

### Evidence boundaries

The system explicitly separates:

**OBSERVED → DERIVED → MODELED → INFERRED → UNKNOWN**

This prevents analytical assumptions from being presented as source facts.

### Key architecture decisions

| Decision                      | Reason                                                     |
| ----------------------------- | ---------------------------------------------------------- |
| Snapshot dimensions           | BTS does not provide sufficient history for justified SCD2 |
| Bridge table                  | A flight can have multiple reported delay causes           |
| `operational_influence_class` | Avoids unsupported claims about controllability            |
| Separate cost models          | Observed metrics and modeled assumptions remain distinct   |
| Tail-number aircraft key      | Avoids unnecessary fan-out across carriers                 |

**Full decisions:** [docs/decisions/](docs/decisions/)

---

## 🗂️ The 5 Delay Columns — Domain Decoded

> _Before writing a single line of code, I studied the IOC — the nerve centre of every airline._

| Column                      | What Generated It                                       | Domain Source                |
| --------------------------- | ------------------------------------------------------- | ---------------------------- |
| `CARRIER_DELAY`             | MEL faults · crew duty breaches · aircraft swaps        | Ch 4 — Engineering + Crewing |
| `WEATHER_DELAY`             | Fog · crosswinds · thunderstorms · snow                 | Ch 4 — Weather               |
| `NAS_DELAY`                 | ATC ground stops · GDPs · runway closures               | Ch 4 — Air Traffic           |
| `SECURITY_DELAY`            | Terminal evacuations · re-screening                     | Ch 1 — Safety pillar         |
| `LATE_AIRCRAFT_DELAY`       | Propagation signal. Previous rotation was late.         | Ch 3 — Robustness            |
| **`NULL (79.11% of rows)`** | ← **SUCCESS.** IOC recovered on time. Not missing data. | Ch 1 — Efficiency pillar     |

---

## 🛠️ Technical Stack

| Area             | Technologies                 |
| ---------------- | ---------------------------- |
| Languages        | Python · SQL                 |
| Processing       | PySpark                      |
| Cloud            | Microsoft Azure              |
| Compute          | Azure Databricks             |
| Storage          | ADLS Gen2 · Parquet          |
| Architecture     | Medallion Architecture       |
| Data Modeling    | Kimball Star Schema          |
| Visualization    | Power BI                     |
| Orchestration    | Azure Data Factory (planned) |
| Future Interface | REST API · AI Interface      |

---

## 🎯 Platform Boundary

### Currently supported

- Historical delay analysis (Jan 2023 – Dec 2025)
- Carrier performance analysis
- Airport and route exposure analysis
- Tail-number cascade analysis
- Delay-cause distribution
- Cost sensitivity modeling (cited assumptions)

### Not currently supported

- Real-time IOC control
- Live crew legality
- Live weather / ATC feeds
- Passenger-level impact
- Real-time disruption prediction
- Prescriptive operational recommendations

---

## 🚀 Roadmap

| Stage                     | Status      |
| ------------------------- | ----------- |
| Source validation         | ✅ Complete |
| Bronze layer              | ✅ Complete |
| Silver layer              | ✅ Complete |
| Gold dimensional model    | ✅ Complete |
| Azure validation          | ✅ Complete |
| Semantic / business layer | ✅ Complete |
| Power BI analytics        | ✅ Complete |
| REST API                  | ✅ Complete |
| AI Analyst interface      | ✅ Complete |

### Long-term direction

**Trusted Data → Semantic Understanding → AI Analysis → Business Decision Support**

The objective is not simply to add AI to a data pipeline.
The objective is to build the **trusted data foundation that makes AI analysis defensible.**

---

## 📁 Repository Structure

BTS-Aviation-Delay-Intelligence/
│
├── docs/
│ ├── HLD.md
│ ├── data_model.md
│ ├── ai_response_contract.md
│ ├── evidence/
│ ├── semantic/
│ └── decisions/ ← 10 ADRs
│
├── governance/
│ ├── data_principles.md
│ └── sql_standards.md
│
├── pipeline/
│ ├── bronze/
│ ├── silver/
│ └── gold/
│
├── analysis/
│ ├── bts_insights.md
│ └── gold_analytics.sql
│
└── tests/
└── Screenshots/ ← Power BI dashboard screenshots

---

<div align="center">

### Building in public.

**Domain first. Code second. Evidence always.**

✈️ Aviation · Data Engineering · Cloud · AI Platforms

**Industry Advisors:** Luis R. Meza (Aviation Director) · Jack Yang (Airlines CEO)

</div>
