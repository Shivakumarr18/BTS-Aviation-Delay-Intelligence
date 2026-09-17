# BTS Aviation Delay Intelligence System

# Key Analytical Insights

**Author:** Narsing Shiva Kumar
**Date:** September 2026
**Data:** 20,928,599 US domestic flights | Jan 2023 – Dec 2025
**Source:** BTS TranStats — On-Time Performance

---

## Evidence Framework

All insights in this document are classified:

- **OBSERVED** — directly from BTS source data
- **DERIVED** — calculated from observed fields
- **MODELED** — based on external assumption
- **INFERRED** — pattern interpretation, not established fact

---

## 1. Fleet-Level Delay Exposure

**OBSERVED:**

- Total flights: 20,928,599
- Delayed flights: ~4,200,000
- Delay rate: 21.20% (operated flights only, cancelled excluded)
- Cancellation rate: 1.40%
- Total arrival delay minutes: 152,637,336

**MODELED (Ferguson et al. $45/min):**

- Estimated delay cost exposure: $14.95 billion
- Not actual airline financial loss

---

## 2. Delay Cause Distribution

**OBSERVED (via bridge_flight_delay_reason):**

Late Aircraft is the largest single BTS-reported
delay category — larger than carrier delay, weather,
NAS, and security combined.

This pattern is consistent with delay propagation
across aircraft rotations. However, BTS delay
categories alone do not establish the underlying
causal mechanism.

**IOC Pillar Distribution (DERIVED — project-defined):**

- Efficiency pillar (Carrier + Late Aircraft): dominant
- Legality pillar (NAS + Security): second
- Safety pillar (Weather): smallest

**What this means operationally (INFERRED):**
The data suggests the majority of reportable delay
minutes are associated with airline internal operations
rather than external factors. This is an inference
from BTS reporting — not confirmed causation.

---

## 3. Carrier Performance Variation

**OBSERVED:**
Three different definitions of "worst carrier"
produce three different answers:

- Highest delay rate: Frontier Airlines
- Highest cancellation rate: Republic Airways
- Highest average delay per delayed flight: PSA Airlines
- Highest total delay minutes: American Airlines

**Key insight:**
"Worst carrier" is undefined without a metric definition.
This is why the semantic layer requires metric
clarification before answering carrier performance questions.

---

## 4. Seasonal Patterns

**OBSERVED:**

- Summer peak (June-July): highest flight volume
  and highest delay rates
- February dip: fewer days, lower volume
- December spike: holiday travel window
- Labor Day and Thanksgiving windows show
  elevated delay rates

**INFERRED:**
Summer convective weather and higher traffic
density are consistent with the observed pattern.
BTS data does not independently establish causation.

---

## 5. Airport Exposure

**OBSERVED:**

- MDW (Chicago Midway): highest delay minutes
  AND highest cancellation count
- Illinois: highest delay rate by state
- California, Texas, New York: highest volume states

**INFERRED:**
MDW's concentration may reflect Chicago's weather
exposure and Southwest's hub concentration there.
This is an inference — BTS data does not independently
establish the underlying cause.

---

## 6. Cost Sensitivity (MODELED)

Using Ferguson et al. $45/min assumption:

| Carrier           | Modeled Exposure |
| ----------------- | ---------------- |
| American Airlines | Highest          |
| Southwest         | Second           |
| Delta             | Third            |

**Mandatory disclaimer:**
These are modeled estimates. $45/min is a
research-based directional reference — not actual
airline accounting cost. See ADR-GOLD-005.

---

## 7. What This Data Cannot Tell Us

| Question                          | Why                                     | What Can Be Said                                    |
| --------------------------------- | --------------------------------------- | --------------------------------------------------- |
| Why did a specific flight delay?  | BTS reports attribution, not root cause | Carrier reported X minutes carrier-attributed delay |
| Did the carrier cause this delay? | Self-reporting — not proven causation   | Carrier attributed delay to this category           |
| Will this flight be delayed?      | Historical data only                    | Historical pattern shows X% delay rate              |
| What did delays actually cost?    | Cost is modeled, not observed           | Modeled exposure under $45/min assumption           |
| Did tail N123 cause propagation?  | Sequence observed, causation not proven | Subsequent rotations were also delayed              |

---

## 8. Propagation Signal

**OBSERVED:**
Late Aircraft is the #1 BTS-reported delay category.

**INFERRED (not proven):**
This pattern is consistent with delay propagation —
an aircraft delayed on rotation 1 creates a late
inbound for rotation 2, which creates late aircraft
delay on rotation 3.

**What BTS data supports:**
Following an aircraft's initial reported delay,
subsequent rotations on the same tail number
were also delayed.

**What BTS data does NOT support:**
That the propagation was inevitable, unpreventable,
or that any specific intervention would have
broken the cascade.

---

_Built on 20,928,599 US flight records | Jan 2023 – Dec 2025_
_Azure Databricks | Kimball Star Schema | GCG 10/10_
_Domain first. Code second. Evidence always._
