# ADR-009: Parquet over CSV for All Layers

## Decision

All Bronze, Silver and Gold data stored as Parquet. Raw source CSVs preserved in raw/ only.

## Why we chose this

Column pruning: Parquet reads only required columns. CSV reads entire row.
Predicate pushdown: Parquet skips row groups that don't match filter conditions.
Compression: Snappy compression can substantially reduce storage compared with raw CSV.
Actual reduction depends on data characteristics — not a universal guarantee.
Schema enforcement: Parquet stores schema in file footer. CSV has no schema.
Spark native: Parquet is Spark's preferred format. No parsing overhead.
Partition pruning: Parquet + Hive-style partitions enable month-level skipping.

## Why we rejected alternatives

CSV: no schema, no compression efficiency, full row scan always required.
ORC: Parquet was selected for ecosystem compatibility, portability, and alignment
with the project's Spark/Databricks/Power BI analytical workload.
Both ORC and Parquet are legitimate columnar formats — this is a workload-specific choice.
Delta Lake: deferred to Azure v2. Requires Delta engine. Adds ACID complexity.

## What this enables

Silver reads only required columns for Gold build — memory efficient on 20.9M rows.
Power BI Import mode reads Parquet efficiently via Databricks connector.
GCG partition checks work via Hive-style directory structure.

## What this constrains

Parquet is binary — not human-readable. Requires Spark or Parquet reader to inspect.
Schema changes require full rewrite of affected partitions.

## Future state

Azure v2: migrate to Delta Lake format for ACID transactions and time travel.
Parquet remains the fallback export format for external consumers.
