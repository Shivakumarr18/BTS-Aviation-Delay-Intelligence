# SQL Engineering Standards

**Author:** Narsing Shiva Kumar
**Version:** 1.0
**Date:** September 2026

---

## Engineering Philosophy

> SQL should be correct before fast,
> readable before clever,
> and scalable before necessary.
>
> Every query should preserve business meaning
> while remaining understandable, maintainable,
> and efficient at production scale.

---

## 1. Scale Mindset

Write every query as if it will run on 100M+ rows.

Design for scalability from the first draft,
not after performance issues appear.

---

## 2. Filter Early

Reduce data as early as possible before expensive
operations such as:

- JOIN
- GROUP BY
- WINDOW FUNCTIONS
- SORT

Filter only when business logic allows.

---

## 3. Write SARGable Predicates

Never wrap indexed columns in functions inside
the WHERE clause.

❌ Avoid:

```sql
WHERE YEAR(order_date) = 2024
```

✅ Prefer:

```sql
WHERE order_date >= '2024-01-01'
  AND order_date < '2025-01-01'
```

Enable index usage and partition pruning
whenever possible.

---

## 4. Analyze Distributions, Not Just Averages

Average alone can hide important variation.

When variability matters, accompany AVG() with:

- STDDEV()
- PERCENTILE_CONT()
- MIN()
- MAX()

Always understand the distribution before
drawing conclusions.

In this project: AVG(arr_delay_mins) is always
reported with STDDEV and median for delayed flights.

---

## 5. Respect NULLs

Every NULL should have a documented business meaning.

- Never replace NULL with 0 without justification
- Document what NULL represents for each column
- Preserve business semantics throughout the pipeline

In this project: NULL delay cause ≠ zero delay.
79.11% of flights have NULL delay causes.
Imputing zero would corrupt the majority of the dataset.

---

## 6. Window Functions

Use window functions intentionally.

- Define window frames explicitly for aggregate windows
- Build complete date spines before calculating
  moving averages
- Partition by business logic — not convenience

---

## 7. Prefer Readable SQL

Use CTEs whenever they improve readability
and maintainability.

Good SQL should be easy to:

- Read
- Debug
- Review
- Modify

Validate execution plans instead of assuming
CTEs improve performance.

---

## 8. Select Only Required Columns

Never use:

```sql
SELECT *
```

in analytical or production queries.

Return only the columns required by downstream consumers.

---

## 9. COUNT with Intention

Use the appropriate COUNT for the question:

```sql
COUNT(*)          -- Total rows including NULLs
COUNT(column)     -- Non-NULL values only
COUNT(DISTINCT x) -- Unique values only
```

In this project:

- Delay Rate denominator = operated flights only
  (cancelled excluded from COUNT)
- This is a certified measure definition,
  not an arbitrary choice

---

## 10. Meaningful Aliases

Aliases should communicate business meaning.

✅ Good:

```sql
total_delayed_flights
average_arrival_delay_minutes
carrier_delay_percentage
```

❌ Avoid:

```sql
col1
avg1
temp
```

---

## 11. JOIN Discipline

Choose JOIN types deliberately.

Always understand why the query requires:

- INNER JOIN
- LEFT JOIN
- RIGHT JOIN
- FULL OUTER JOIN

In this project: fact_delays uses LEFT JOIN for all
dimension lookups. Must never drop a flight due to
dimension lookup failure. Unmatched rows route to
UNKNOWN member (-1), never NULL.

Avoid unintended Cartesian products.

---

## 12. Validate Execution Plans

Before production execution:

- Use EXPLAIN
- Use EXPLAIN ANALYZE where appropriate

Understand:

- Join strategy
- Scan type
- Index usage
- Partition pruning
- Estimated vs actual rows

Never optimize blindly.

---

## 13. Deterministic Ordering

Never rely on implicit row ordering.

Whenever result order matters:

```sql
ORDER BY flight_date, flight_id;
```

---

## 14. Respect Data Types

Avoid unnecessary implicit conversions.

- Join compatible data types
- Cast explicitly when required
- Prevent unnecessary full table scans
  caused by implicit casting

---

## 15. Validate Transformations

Every transformation should be verifiable.

Examples:

- Row counts before and after
- Duplicate counts
- NULL counts
- Business rule validation
- Aggregate sanity checks

Trust results only after validation.

In this project: Silver Completion Gate (12 checks)
and Gold Completion Gate (10 checks) enforce this
principle at scale across 20.9M rows.

---

## BTS Project SQL Examples

### Delay Rate (certified measure definition)

```sql
-- Delay Rate = Delayed / Operated (cancelled excluded)
SELECT
    c.carrier_name,
    COUNT(*) AS operated_flights,
    SUM(f.arr_delayed_flag) AS delayed_flights,
    ROUND(
        100.0 * SUM(f.arr_delayed_flag) / COUNT(*), 2
    ) AS delay_rate_pct
FROM fact_delays f
JOIN dim_carrier c ON f.carrier_key = c.carrier_key
WHERE f.is_cancelled = 0  -- operated flights only
GROUP BY c.carrier_name
ORDER BY delay_rate_pct DESC;
```

### Bridge Query (avoid double count)

```sql
-- Delay minutes by cause — filter by ONE delay_code
-- Never sum attributed_mins across all codes
-- without filtering — double counts per flight
SELECT
    b.delay_code,
    SUM(b.attributed_mins) AS total_delay_mins
FROM bridge_flight_delay_reason b
WHERE b.delay_code = 'CARRIER'  -- one code at a time
GROUP BY b.delay_code;
```

### Seasonal Pattern

```sql
SELECT
    d.season,
    d.month_name,
    COUNT(*) AS total_flights,
    ROUND(
        100.0 * SUM(f.arr_delayed_flag) / COUNT(*), 2
    ) AS delay_rate_pct
FROM fact_delays f
JOIN dim_date d ON f.date_key = d.date_key
WHERE f.is_cancelled = 0
GROUP BY d.season, d.month_name, d.month
ORDER BY d.month;
```
