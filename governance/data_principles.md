# Data Engineering Principles

**Project:** BTS Aviation Delay Intelligence Platform
**Author:** Narsing Shiva Kumar
**Version:** 1.0
**Date:** September 2026

---

## Core Philosophy

> "The value is not the analytics itself. The value comes from
> whether the intelligence improves how people plan, decide,
> and operate."
> — Peter J. Bruce, Airline Operations Control

Data engineering is not about moving data.
It is about building trusted foundations that
organizations can rely on for real decisions.

---

## 1. Errors as a UI

Every failure must explain:

- WHAT broke
- WHERE it broke
- WHY it broke
- HOW TO FIX it

Silent failures are not acceptable.
A pipeline that fails quietly is more dangerous
than one that fails loudly.

---

## 2. Trust is Designed, Not Added

Governance, audit trails, and data quality checks
are Day 1 architecture decisions — not afterthoughts.

A trusted system:

- Validates before it transforms
- Proves before it serves
- Documents before it claims

---

## 3. Preserve, Never Fabricate

NULLs carry business meaning.
Never substitute values without documented reasoning.

In this system:

- NULL delay cause = BTS did not report a cause
- NULL arrival delay = flight was cancelled
- NULL tail number = airline did not report

These are not missing data. They are facts.

---

## 4. Evidence Over Adjectives

Every claim must be classified:

| State    | Meaning                                         |
| -------- | ----------------------------------------------- |
| OBSERVED | Directly present in source data                 |
| DERIVED  | Calculated from observed fields                 |
| MODELED  | Based on explicit external assumption           |
| INFERRED | Reasonable interpretation, not established fact |
| UNKNOWN  | Evidence is insufficient                        |

Never say "carrier caused the delay."
Say "carrier delay was reported by the carrier to BTS."

Never say "this is the cost of delays."
Say "this is a modeled estimate using $45/min assumption
(Ferguson et al. FAA/NEXTOR 2010)."

---

## 5. Read Before You Build

Domain knowledge informs every schema decision.

Sources used in this project:

- Peter J. Bruce — Airline Operations Control
  (Chapters 1, 3, 4, 5)
- Ferguson et al. — Total Delay Impact Study
  (FAA/NEXTOR 2010)
- BTS TranStats documentation

Every IOC pillar mapping, every NULL rule,
every grain decision was grounded in domain
understanding before any code was written.

---

## 6. Idempotency is Non-Negotiable

Any layer can be safely rerun without corrupting
downstream data or creating duplicates.

- Bronze: partition check → skip if exists
- Silver: DELETE + INSERT → clean rerun
- Gold: full overwrite → safe rerun

If you cannot safely rerun, you cannot safely recover.

---

## 7. Test Cheap, Prove Correctness, Scale Deliberately

Do not scale before you have proven correctness
at a representative sample.

In this project:

- Local TEST_MODE: 99,972 rows (stratified 36/36 partitions)
- 8/8 TCG checks passed locally
- Then Azure full run: 20,928,599 rows
- 10/10 GCG checks passed on Azure

Increasing compute does not improve a bad test.
Improving the test design does.

---

## 8. Document Why, Not Just What

Every architecture decision must record:

- WHY this approach was chosen
- WHY alternatives were rejected
- What this enables
- What this constrains
- Future state

A decision without a WHY is a liability.
When the system is challenged, only the WHY survives.

---

## 9. Honest Scope

State clearly what the system does and does not do.
No inflated claims. No fabricated metrics.

This system:

- CAN: historical delay analysis, carrier/airport patterns,
  cost sensitivity modeling (cited assumptions)
- CANNOT: real-time IOC, live crew legality,
  passenger impact, prescriptive recommendations

The platform boundary is a feature, not a limitation.
It prevents the system from being used for claims
it cannot support.

---

## 10. The Sachin Standard

Every function in this codebase follows:

- Type hints on every function signature
- Docstrings explaining WHY, not just WHAT
- Structured logging: WHAT / WHERE / WHY / FIX
- No silent failures
- Evidence boundary labeling on every derived field

Code that cannot be explained cannot be trusted.
Code that cannot be trusted cannot be used in production.

---

## The Statement This System Is Built Toward

> "I built a governed analytical data foundation on
> 20.9 million US flight records spanning 3 years.
> The Gold layer passed 10 explicit completion gates
> on Azure Databricks including grain uniqueness,
> referential integrity, metric reconciliation, and
> bridge attribution verification.
> I can show you the evidence."

Evidence. Not claims.
Proof. Not performance.
